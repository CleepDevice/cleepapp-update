#!/usr/bin/env python
# -*- coding: utf-8 -*

# File contains UninstallModule and InstallModule classes
# that are used in install.py file to install and uninstall
# Cleep modules

import logging
import os
import inspect
import stat
from zipfile import ZipFile
import threading
import tempfile
from gevent import sleep
from cleep.core import CleepModule
from cleep.libs.internals.download import Download
import cleep.libs.internals.tools as Tools

from .install_app_manifest import (
    InstallManifest,
    InstallManifestError,
    MODE_INSTALL,
    MODE_UNINSTALL,
    PHASE_PREINST,
    PHASE_POSTINST,
    PHASE_PREUNINST,
    PHASE_POSTUNINST,
    UNINSTALL_PHASES,
)

__all__ = ["UninstallModule", "InstallModule", "UpdateModule"]

PATH_FRONTEND = "/opt/cleep/html"
PATH_SCRIPTS = "/opt/cleep/scripts"
PATH_INSTALL = "/opt/cleep/install"
PATH_APP_BACKEND = "/opt/cleep/"
ARCHIVE_FRONTEND_DIR = "frontend/"
ARCHIVE_BACKEND_DIR = "backend/"
ARCHIVE_ASSET_DIR = "asset/"
ARCHIVE_BIN_DIR = "bin/"
SCRIPTS_DIR = "scripts/"
TESTS_DIR = "tests/"


class ProcessContext:
    """
    Current process context
    """

    def __init__(self):
        pass

    def __str__(self):
        return "%s" % self.to_dict()

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class LocalModuleException(Exception):
    """
    Local module exception. Used to stop module process
    """


class CancelException(Exception):
    """
    Cancel exception. Used to cancel process
    """


class ForcedException(Exception):
    """
    Forced exception. Used to stop process
    """


class CommonProcess(threading.Thread):
    """
    Common process class for install/uninstall/update module
    """

    def __init__(self, status_callback, cleep_filesystem, crash_report, task_factory):
        """
        Constructor

        Args:
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
            task_factory (TaskFactory): TaskFactory instance
        """
        threading.Thread.__init__(
            self,
            daemon=True,
            name="commonprocess-%s" % getattr(status_callback, "__name__", "unamed"),
        )

        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.running = False
        self.status_callback = status_callback
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.task_factory = task_factory
        self._process_status = []
        # Accumulated console output from failed external commands (apt/pip/...)
        self._stdout = []
        self._stderr = []

    def _absorb_console_output(self, stdout=None, stderr=None):
        """
        Keep console command output for process status / failure log.

        Args:
            stdout (list): stdout lines
            stderr (list): stderr lines
        """
        if stdout:
            self._stdout.extend(stdout)
        if stderr:
            self._stderr.extend(stderr)

    def _run_phase_manifest(self, context, phase, base_dir, in_scripts=True):
        """
        Run a declarative phase JSON if present (no-op when missing).

        Args:
            context: process context
            phase (str): preinst / postinst / preuninst / postuninst
            base_dir (str): package extract root or PATH_INSTALL/<module>
            in_scripts (bool): True for package ``scripts/``, False for backup dir

        Returns:
            bool: True if succeed or nothing to run
        """
        if not base_dir:
            self.logger.debug("No base dir for %s.json, skip", phase)
            return True

        path = InstallManifest.phase_path(base_dir, phase, in_scripts=in_scripts)
        if not os.path.exists(path):
            self.logger.debug('No %s.json at "%s"', phase, path)
            return True

        self.logger.info(
            'Running %s.json for module "%s" (%s)', phase, self.module_name, path
        )
        try:
            data = InstallManifest.load(path)
            mode = MODE_UNINSTALL if phase in UNINSTALL_PHASES else MODE_INSTALL
            runner = InstallManifest(
                self.module_name,
                CleepModule.app_paths_for(self.module_name),
                self.cleep_filesystem,
                logger=self.logger,
            )
            runner.run(data, mode=mode)
            return True
        except InstallManifestError as exc:
            self._absorb_console_output(exc.stdout, exc.stderr)
            self._log_process_status(
                context,
                logging.ERROR,
                '%s.json failed for module "%s": %s'
                % (phase, self.module_name, exc),
                force_crash_report=True,
                stdout=exc.stdout,
                stderr=exc.stderr,
            )
            return False
        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception running %s.json for module "%s"'
                % (phase, self.module_name),
            )
            return False

    def _log_process_status(
        self,
        context,
        log_level,
        message,
        force_crash_report=False,
        stdout=None,
        stderr=None,
    ):
        """
        Log exception to stdout and keep track of message in install log file

        Args:
            context (Context): install context
            log_level (int): logging level
            message (string): message to log
            force_crash_report (bool): send crash report if True (default False)
            stdout (list): optional console stdout to attach to crash report
            stderr (list): optional console stderr to attach to crash report
        """
        # logging
        if log_level == logging.NOTSET:
            self.logger.exception(message)
        else:
            self.logger.log(log_level, message)

        # crash report
        if (log_level == logging.NOTSET or force_crash_report) and self.crash_report:
            extra = {"message": message, "context": context.to_dict()}
            if stdout:
                extra["stdout"] = stdout
            if stderr:
                extra["stderr"] = stderr
            self.crash_report.report_exception(extra=extra)

        # save track of error in install process messages
        self._process_status.append(message)

    def _step(self, context, cancel=True):
        """
        Process step, check process is not canceled and send current status

        Args:
            context (Context): install context
            cancel (bool): allow cancel (True) or not (False)
        """
        if cancel and not self.running:
            raise CancelException()

        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except Exception:
                self.logger.exception("Exception occured during status callback call")
                self.status_callback = None

    def get_status(self):  # pragma: no cover
        """
        Get current status
        Must be implemented
        """
        raise NotImplementedError("_get_status method must be implemented")

    def run(self):  # pragma: no cover
        """
        Run process
        Must be implemented
        """
        raise NotImplementedError("_get_status method must be implemented")

    def _create_app_directories(self, module_name):
        """
        Create all application directories (paths from CleepModule.app_paths_for).

        Args:
            module_name (str): module name

        Returns:
            bool: True if all directories created successfully, False otherwise
        """
        error = False
        for directory in CleepModule.app_paths_for(module_name).values():
            if os.path.exists(directory):
                continue

            if not self.cleep_filesystem.mkdirs(directory):
                error = True

        return not error


class UninstallModule(CommonProcess):
    """
    Uninstall module in background task.

    Runs preuninst.json, removes installed files, then postuninst.json.
    """

    STATUS_IDLE = 0
    STATUS_UNINSTALLING = 1
    STATUS_UNINSTALLED = 2
    STATUS_ERROR_INTERNAL = 3
    STATUS_ERROR_PREUNINST = 4
    STATUS_ERROR_REMOVE = 5
    STATUS_ERROR_POSTUNINST = 6

    def __init__(
        self,
        module_name,
        module_infos,
        update_process,
        force_uninstall,
        status_callback,
        cleep_filesystem,
        crash_report,
        task_factory,
    ):
        """
        Constructor

        Args:
            module_name (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module uninstall occured during update process
            force_uninstall (bool): uninstall module and continue if error occured. Process will always succeed
            callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem instance
            crash_report (CrashReport): CrashReport instance
            task_factory (TaskFactory): TaskFactory instance
        """
        CommonProcess.__init__(
            self, status_callback, cleep_filesystem, crash_report, task_factory
        )

        # members
        self.status = self.STATUS_IDLE
        self.update_process = update_process
        self.force_uninstall = force_uninstall
        self.module_name = module_name
        self.module_infos = module_infos

    def is_uninstalling(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return self.status == self.STATUS_UNINSTALLING

    def get_status(self):
        """
        Return current status

        Returns:
            dict: uninstall status::

                {
                    status (int): see STATUS_XXX for available codes
                    module (string): module name
                    updateprocess (bool): uninstall triggered by module update
                    process (list): process status
                    stdout (list): console stdout from failed commands
                    stderr (list): console stderr from failed commands
                }

        """
        return {
            "module": self.module_name,
            "status": self.status,
            "updateprocess": self.update_process,
            "process": self._process_status,
            "stdout": self._stdout,
            "stderr": self._stderr,
        }

    def _remove_installed_files(self, context):
        """
        Remove all installed module files

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        paths = []
        try:
            # read install log file
            self._log_process_status(context, logging.INFO, "Remove installed files")
            context.module_log = os.path.join(
                PATH_INSTALL, self.module_name, "%s.log" % self.module_name
            )
            context.install_dir = os.path.join(PATH_INSTALL, self.module_name)
            self.logger.debug('Open install log file "%s"' % context.module_log)
            if not os.path.exists(context.module_log):
                self._log_process_status(
                    context,
                    logging.WARN,
                    'Install log file "%s" for module "%s" was not found'
                    % (context.module_log, self.module_name),
                )
                return bool(context.force_uninstall)
            install_log_fd = self.cleep_filesystem.open(context.module_log, "r")
            lines = install_log_fd.readlines()
            self.cleep_filesystem.close(install_log_fd)
            self.logger.trace("lines = %s" % lines)

            # remove files
            for line in lines:
                self.logger.trace('Processing file "%s"' % line)
                line = line.strip()
                if len(line) == 0:
                    # empty line, drop it
                    self.logger.trace("Drop empty line")
                    continue

                # check if file exists on filesystem
                if not os.path.exists(line):
                    self._log_process_status(
                        context,
                        logging.ERROR,
                        'Unable to remove file "%s" that does not exist during module "%s" uninstallation'
                        % (line, self.module_name),
                    )
                    continue

                # check if we try to remove system library file (should not happen but we are never too careful)
                if Tools.is_core_lib(line):
                    # it's a core library, log warning and continue
                    self._log_process_status(
                        context,
                        logging.WARN,
                        'Trying to remove core library file "%s" during module "%s" uninstallation. Drop deletion.'
                        % (line, self.module_name),
                    )
                    continue

                # try to delete file
                if not self.cleep_filesystem.rm(line):
                    # just log error and continu processing, we must try to delete as much file as possible
                    self._log_process_status(
                        context,
                        logging.ERROR,
                        'Unable to remove file "%s" during module "%s" uninstallation'
                        % (line, self.module_name),
                    )

                # keep track of file path
                path = os.path.dirname(line)
                if path not in paths:
                    paths.append(path)

            # clear paths
            self.logger.trace("Clearing paths: %s" % paths)
            for path in paths:
                if os.path.exists(path) and not self.cleep_filesystem.rmdir(path):
                    self._log_process_status(
                        context,
                        logging.ERROR,
                        'Unable to remove directory "%s" during module "%s" uninstallation'
                        % (path, self.module_name),
                    )

            return True

        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception occured removing files during "%s" module uninstallation'
                % self.module_name,
            )
            return bool(context.force_uninstall)

    def run(self):
        """
        Run uninstall
        """
        # init
        self.running = True
        self.status = self.STATUS_UNINSTALLING
        context = ProcessContext()
        context.step = "init"
        context.force_uninstall = self.force_uninstall
        context.module_log = None
        context.install_dir = None

        msg = f'Start module "{self.module_name}" uninstallation'
        self._log_process_status(context, logging.INFO, msg)

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # uninstall local module
            if "local" in self.module_infos and self.module_infos["local"] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()

            install_dir = os.path.join(PATH_INSTALL, self.module_name)

            # pre uninstallation manifest
            context.step = "preuninst"
            if not self._run_phase_manifest(
                context, PHASE_PREUNINST, install_dir, in_scripts=False
            ):
                self.status = self.STATUS_ERROR_PREUNINST
                raise ForcedException()
            self._step(context)

            # remove all installed files
            context.step = "remove"
            if not self._remove_installed_files(context):
                self.status = self.STATUS_ERROR_REMOVE
                raise ForcedException()
            self._step(context)

            # post uninstallation manifest
            context.step = "postuninst"
            if not self._run_phase_manifest(
                context, PHASE_POSTUNINST, install_dir, in_scripts=False
            ):
                self.status = self.STATUS_ERROR_POSTUNINST
                raise ForcedException()
            self._step(context)

            # set final status
            self.status = self.STATUS_UNINSTALLED

        except LocalModuleException:
            # local module to uninstall, proper exit
            self.status = self.STATUS_UNINSTALLED

        except ForcedException:
            # error during installation, nothing else to do here
            pass

        except Exception:
            # unexpected error occured, invalid state
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception occured during module "%s" uninstallation'
                % self.module_name,
            )
            self.status = self.STATUS_ERROR_INTERNAL

            # report crash
            self.crash_report.report_exception(extra={"context": context.to_dict()})

        finally:
            # clean stuff
            try:
                # clean backend
                path = os.path.join(PATH_APP_BACKEND, "modules", self.module_name)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                # clean frontend
                path = os.path.join(PATH_FRONTEND, "js/modules/%s" % self.module_name)
                if path and os.path.exists(path):
                    self.cleep_filesystem.rmdir(path)
                # clean install log file
                if context.module_log and os.path.exists(context.module_log):
                    self.cleep_filesystem.rm(context.module_log)
                if context.install_dir:
                    for phase in (PHASE_PREUNINST, PHASE_POSTUNINST):
                        manifest = InstallManifest.phase_path(
                            context.install_dir, phase, in_scripts=False
                        )
                        if os.path.exists(manifest):
                            self.cleep_filesystem.rm(manifest)
            except Exception:
                self._log_process_status(
                    context,
                    logging.NOTSET,
                    'Exception occured during "%s" uninstall cleaning'
                    % self.module_name,
                )

            # disable write mode
            self.cleep_filesystem.disable_write()

        # finalize installation
        success = self.status == self.STATUS_UNINSTALLED
        self._log_process_status(
            context,
            logging.INFO,
            'Module "%s" uninstallation terminated (success:%s, force:%s)'
            % (self.module_name, success, self.force_uninstall),
        )
        self._step(context)


class InstallModule(CommonProcess):
    """
    Install module in background task
    """

    STATUS_IDLE = 0
    STATUS_INSTALLING = 1
    STATUS_INSTALLED = 2
    STATUS_CANCELED = 3
    STATUS_ERROR_INTERNAL = 4
    STATUS_ERROR_DOWNLOAD = 5
    STATUS_ERROR_EXTRACT = 6
    STATUS_ERROR_PREINST = 7
    STATUS_ERROR_BACKUP = 8
    STATUS_ERROR_COPY = 9
    STATUS_ERROR_POSTINST = 10

    def __init__(
        self,
        module_name,
        module_infos,
        update_process,
        status_callback,
        cleep_filesystem,
        crash_report,
        task_factory,
    ):
        """
        Constructor

        Args:
            module_name (string): module name to install
            module_infos (dict): all module infos from modules.json file
            update_process (bool): True if module install occured during update process
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
            task_factory (TaskFactory): TaskFactory instance
        """
        CommonProcess.__init__(
            self, status_callback, cleep_filesystem, crash_report, task_factory
        )

        # members
        self.update_process = update_process
        self.status = self.STATUS_IDLE
        self.module_name = module_name
        self.module_infos = module_infos
        self.error = ""
        self.package = None

        # make sure install paths exist
        if not os.path.exists(PATH_SCRIPTS):
            self.cleep_filesystem.mkdir(PATH_SCRIPTS, True)
        if not os.path.exists(PATH_INSTALL):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

    def set_package(self, package):
        """
        Set package file is exists. It drops archive download step

        Note:
            Package path is not checked, it is the responsability of caller to check if file exists

        Args:
            package (string): package path
        """
        self.package = package

    def cancel(self):
        """
        Cancel installation
        """
        self.logger.trace(
            'Received module "%s" installation cancelation' % self.module_name
        )
        self.running = False

    def is_installing(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return self.status == self.STATUS_INSTALLING

    def get_status(self):
        """
        Return current status

        Returns:
            dict: install status::

                {
                    module (string): module name
                    status (int): see STATUS_XXX for available codes
                    updateprocess (bool): install triggered by module update
                    process (list): process status
                    stdout (list): console stdout from failed commands
                    stderr (list): console stderr from failed commands
                }

        """
        return {
            "module": self.module_name,
            "status": self.status,
            "updateprocess": self.update_process,
            "process": self._process_status,
            "stdout": self._stdout,
            "stderr": self._stderr,
        }

    def _download_archive(self, context):
        """
        Download module archive

        Args:
            context (Context): install context

        Returns:
            bool: True if download succeed
        """
        self.logger.debug('Download file "%s"' % self.module_infos["download"])
        try:
            download = Download(self.cleep_filesystem, self.task_factory)
            download_status, context.archive_path = download.download_file(
                self.module_infos["download"], check_sha256=self.module_infos["sha256"]
            )
            self.logger.trace("archive_path: %s" % context.archive_path)
            if context.archive_path is None:
                self.logger.trace("download_status: %s" % download_status)

                if download_status == download.STATUS_ERROR:
                    self.error = (
                        'Error during "%s" download: internal error'
                        % self.module_infos["download"]
                    )
                elif download_status == download.STATUS_ERROR_INVALIDSIZE:
                    self.error = (
                        'Error during "%s" download: invalid filesize'
                        % self.module_infos["download"]
                    )
                elif download_status == download.STATUS_ERROR_BADCHECKSUM:
                    self.error = (
                        'Error during "%s" download: invalid checksum'
                        % self.module_infos["download"]
                    )
                else:
                    self.error = (
                        'Error during "%s" download: unknown error'
                        % self.module_infos["download"]
                    )

                self._log_process_status(
                    context, logging.ERROR, self.error, force_crash_report=True
                )

                return False

            return True

        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception occured during module "%s" archive download "%s":'
                % (self.module_name, self.module_infos["download"]),
            )
            return False

    def _extract_archive(self, context):
        """
        Extract module archive

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug('Extracting archive "%s"' % context.archive_path)
        try:
            with ZipFile(context.archive_path, "r") as zipfile:
                context.extract_path = tempfile.mkdtemp()
                self.logger.debug('Extract archive to "%s"' % context.extract_path)
                zipfile.extractall(context.extract_path)

            return True

        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception decompressing module "%s" archive "%s" in "%s":'
                % (self.module_name, context.archive_path, context.extract_path),
            )
            return False

    def _backup_scripts(self, context):
        """
        Backup uninstall phase manifests for later uninstall.

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug(
            'Save module "%s" uninstall manifests', self.module_name
        )
        try:
            dst_dir = os.path.join(PATH_INSTALL, self.module_name)
            for phase in (PHASE_PREUNINST, PHASE_POSTUNINST):
                src_path = InstallManifest.phase_path(
                    context.extract_path, phase, in_scripts=True
                )
                dst_path = InstallManifest.phase_path(
                    dst_dir, phase, in_scripts=False
                )
                if os.path.exists(src_path):
                    self.logger.trace('Copying "%s" to "%s"', src_path, dst_path)
                    self.cleep_filesystem.copy(src_path, dst_path)
                else:
                    self.logger.trace("%s.json not found in archive", phase)
            return True

        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception saving module "%s" scripts:' % self.module_name,
            )
            return False

    def _copy_module_files(self, context):
        """
        Install module files

        Args:
            context (Context): install context

        Returns:
            bool: True if operation succeed
        """
        self.logger.debug("Installing module files")
        try:
            # list archive files
            archive_files = []
            for directory, _, files in os.walk(context.extract_path):
                for filename in files:
                    full_path = os.path.join(directory, filename)
                    rel_path = full_path.replace(context.extract_path, "")
                    rel_path = rel_path[1:] if rel_path[0] == "/" else rel_path
                    archive_files.append(rel_path)
            self.logger.trace("archive_files: %s" % archive_files)

            # process them according to their directory
            for archive_file in archive_files:
                self.logger.trace('Processing archive file "%s"' % archive_file)
                copied_filepath = False
                if archive_file.startswith(ARCHIVE_BACKEND_DIR):
                    copied_filepath = self.__copy_backend_file(context, archive_file)
                elif archive_file.startswith(ARCHIVE_FRONTEND_DIR):
                    copied_filepath = self.__copy_frontend_file(context, archive_file)
                elif archive_file.startswith(ARCHIVE_ASSET_DIR):
                    copied_filepath = self.__copy_asset_file(context, archive_file)
                elif archive_file.startswith(ARCHIVE_BIN_DIR):
                    copied_filepath = self.__copy_bin_file(context, archive_file)
                else:
                    self.logger.debug("Drop unhandled archive file: %s" % archive_file)

                # keep track of copied file for later uninstall
                if copied_filepath:
                    context.install_log_fd.write(f"{copied_filepath}\n")
                    context.install_log_fd.flush()

            return True

        except Exception:
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception occured during module "%s" files copy' % self.module_name,
            )
            return False

    def __copy_asset_file(self, context, archive_file):
        """
        Copy asset file

        Args:
            context (Context): install context
            archive_file (str): archive file

        Returns:
            str: copied filepath, None otherwise
        """
        src_path = os.path.join(context.extract_path, archive_file)
        dst_path = os.path.join(
            CleepModule.APP_ASSET_ROOT,
            self.module_name,
            archive_file.replace(ARCHIVE_ASSET_DIR, ""),
        )
        self.logger.trace(f"Copy asset src={src_path} dst={dst_path}")

        # copy file
        self.cleep_filesystem.mkdirs(os.path.dirname(dst_path))
        if not self.cleep_filesystem.copy(src_path, dst_path):
            self._log_process_status(
                context,
                logging.ERROR,
                f'Error copying asset file "{src_path}" to "{dst_path}" during module "{self.module_name}" installation',
                force_crash_report=True,
            )
            raise Exception("NotCopiedFile")

        return dst_path

    def __copy_bin_file(self, context, archive_file):
        """
        Copy asset file

        Args:
            context (Context): install context
            archive_file (str): archive file

        Returns:
            str: copied filepath, None otherwise
        """
        src_path = os.path.join(context.extract_path, archive_file)
        dst_path = os.path.join(
            CleepModule.APP_BIN_ROOT,
            self.module_name,
            archive_file.replace(ARCHIVE_BIN_DIR, ""),
        )
        self.logger.trace(f"Copy bin src={src_path} dst={dst_path}")

        # copy file
        self.cleep_filesystem.mkdirs(os.path.dirname(dst_path))
        if not self.cleep_filesystem.copy(src_path, dst_path):
            self._log_process_status(
                context,
                logging.ERROR,
                f'Error copying bin file "{src_path}" to "{dst_path}" during module "{self.module_name}" installation',
                force_crash_report=True,
            )
            raise Exception("NotCopiedFile")

        # Preserve executable bit from archive when present; otherwise leave as-is
        try:
            src_mode = os.stat(src_path).st_mode
            if src_mode & stat.S_IXUSR:
                os.chmod(dst_path, src_mode)
        except OSError:
            pass

        return dst_path

    def __copy_frontend_file(self, context, archive_file):
        """
        Copy frontend file

        Args:
            context (Context): install context
            archive_file (str): archive file

        Returns:
            str: copied filepath, None otherwise
        """
        src_path = os.path.join(context.extract_path, archive_file)
        dst_path = os.path.join(PATH_FRONTEND, archive_file).replace(
            ARCHIVE_FRONTEND_DIR, ""
        )
        self.logger.trace(f"Copy frontend src={src_path} dst={dst_path}")

        # copy file
        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
        if not self.cleep_filesystem.copy(src_path, dst_path):
            self._log_process_status(
                context,
                logging.ERROR,
                f'Error copying frontend file "{src_path}" to "{dst_path}" during module "{self.module_name}" installation',
                force_crash_report=True,
            )
            raise Exception("NotCopiedFile")

        return dst_path

    def __copy_backend_file(self, context, archive_file):
        """
        Copy backend file

        Args:
            context (Context): install context
            archive_file (str): archive file

        Returns:
            str: copied filepath, None otherwise
        """
        src_path = os.path.join(context.extract_path, archive_file)
        dst_path = os.path.join(PATH_APP_BACKEND, archive_file).replace(
            ARCHIVE_BACKEND_DIR, ""
        )
        self.logger.trace(f"Copy backend src={src_path} dst={dst_path}")

        # check file overwritings
        if os.path.exists(dst_path):
            if Tools.is_core_lib(dst_path):
                # system lib, just drop file install with warning
                self._log_process_status(
                    context,
                    logging.WARNING,
                    f'File "{dst_path}" is a core lib and shouldn\'t be exists in module "{self.module_name}" package. File is dropped.',
                )
                return

            # warning about file overwriting
            self._log_process_status(
                context,
                logging.WARNING,
                f'Application "{self.module_name}" installation overwrites existing file "{dst_path}"',
            )

        # copy file
        self.cleep_filesystem.mkdir(os.path.dirname(dst_path))
        if not self.cleep_filesystem.copy(src_path, dst_path):
            self._log_process_status(
                context,
                logging.ERROR,
                f'Error copying backend file "{src_path}" to "{dst_path}" during module "{self.module_name}" installation',
                force_crash_report=True,
            )
            raise Exception("NotCopiedFile")

        return dst_path

    def _rollback_install(self, context):
        """
        Rollback installation, removing installed files
        """
        self.logger.debug("Rollbacking installation")
        if context.install_log is not None and os.path.exists(context.install_log):
            try:
                # remove installed files
                fdesc = self.cleep_filesystem.open(context.install_log, "r")
                lines = fdesc.readlines()
                for line in lines:
                    self.logger.trace(
                        'Removing "%s" module "%s" file.' % (line, self.module_name)
                    )
                    self.cleep_filesystem.rm(line.strip())

                # remove module install dir
                self.cleep_filesystem.rmdir(os.path.dirname(context.install_log))

            except Exception:
                self._log_process_status(
                    context,
                    logging.NOTSET,
                    'Exception ocurred during "%s" module installation rollback'
                    % self.module_name,
                )

    def run(self):
        """
        Run install
        """
        # init
        self.running = True
        self.status = self.STATUS_INSTALLING
        context = ProcessContext()
        rollback = False
        context.install_log = None
        context.install_log_fd = None
        context.extract_path = None
        context.archive_path = None
        context.step = "init"

        msg = f'Start module "{self.module_name} v{self.module_infos["version"]}" installation'
        self._log_process_status(context, logging.INFO, msg)

        try:
            # enable write mode
            self.cleep_filesystem.enable_write()

            # install local module
            if "local" in self.module_infos and self.module_infos["local"] is True:
                # nothing to process for local modules, quit current process triggering no error
                raise LocalModuleException()

            # init install
            context.install_log = os.path.join(
                PATH_INSTALL, self.module_name, "%s.log" % self.module_name
            )
            self.logger.debug('Create install log file "%s"' % context.install_log)
            self.cleep_filesystem.mkdirs(os.path.join(PATH_INSTALL, self.module_name))
            context.install_log_fd = self.cleep_filesystem.open(
                context.install_log, "w"
            )
            context.install_log_fd.flush()

            # download module package
            if self.package:
                context.archive_path = self.package
            else:
                context.step = "download"
                if not self._download_archive(context):
                    self.status = self.STATUS_ERROR_DOWNLOAD
                    raise ForcedException()
                self._step(context)

            # extract archive
            context.step = "extract"
            if not self._extract_archive(context):
                self.status = self.STATUS_ERROR_EXTRACT
                raise ForcedException()
            self._step(context)

            # copy uninstall scripts to install path (to make them available during uninstallation)
            context.step = "backup"
            if not self._backup_scripts(context):
                self.status = self.STATUS_ERROR_BACKUP
                raise ForcedException()

            # create application directories
            self._create_app_directories(self.module_name)

            # pre installation manifest
            context.step = "preinst"
            if not self._run_phase_manifest(
                context, PHASE_PREINST, context.extract_path, in_scripts=True
            ):
                self.status = self.STATUS_ERROR_PREINST
                raise ForcedException()
            self._step(context)

            # copy module files
            context.step = "copy"
            if not self._copy_module_files(context):
                self.status = self.STATUS_ERROR_COPY
                raise ForcedException()
            self._step(context, cancel=False)

            # post installation manifest
            context.step = "postinst"
            if not self._run_phase_manifest(
                context, PHASE_POSTINST, context.extract_path, in_scripts=True
            ):
                self.status = self.STATUS_ERROR_POSTINST
                raise ForcedException()

            # set final status
            self.status = self.STATUS_INSTALLED

        except LocalModuleException:
            # local module to install, proper exit
            rollback = False
            self.status = self.STATUS_INSTALLED

        except CancelException:
            # install canceled
            self._log_process_status(
                context,
                logging.INFO,
                'Module "%s" installation canceled' % self.module_name,
            )
            rollback = True
            self.status = self.STATUS_CANCELED

        except ForcedException:
            # error during installation
            rollback = True

        except Exception:
            # unexpected error occured, invalid state
            self._log_process_status(
                context,
                logging.NOTSET,
                'Exception occured during module "%s" installation' % self.module_name,
            )
            rollback = True
            self.status = self.STATUS_ERROR_INTERNAL

            # report crash
            self.crash_report.report_exception(extra={"context": context.to_dict()})

        finally:
            # clean stuff
            try:
                if context.install_log_fd:
                    self.cleep_filesystem.close(context.install_log_fd)
                if context.extract_path:
                    self.cleep_filesystem.rmdir(context.extract_path)
                if context.archive_path:
                    self.cleep_filesystem.rm(context.archive_path)
            except Exception:
                self._log_process_status(
                    context,
                    logging.NOTSET,
                    'Exception occured during "%s" install cleaning' % self.module_name,
                )

            if rollback:
                # perform requested rollback
                self._log_process_status(
                    context,
                    logging.INFO,
                    'Rollback module "%s" installation after error' % self.module_name,
                )
                self._rollback_install(context)

            # disable write mode
            self.cleep_filesystem.disable_write()

        # finalize installation
        success = self.status == self.STATUS_INSTALLED
        self._log_process_status(
            context,
            logging.INFO,
            'Module "%s" installation terminated (success:%s, rollback:%s)'
            % (self.module_name, success, rollback),
        )
        self._step(context, cancel=False)


class UpdateModule(threading.Thread):
    """
    Update CleepOS module
    """

    STATUS_IDLE = 0
    STATUS_UPDATING = 1
    STATUS_UPDATED = 2
    STATUS_ERROR = 3

    def __init__(
        self,
        module_name,
        new_module_infos,
        force_uninstall,
        status_callback,
        cleep_filesystem,
        crash_report,
        task_factory,
    ):
        """
        Constructor

        Args:
            module_name (string): module name to update
            new_module_infos (dict): new module infos
            force_uninstall (bool): force module uninstall even if error occured
            status_callback (function): status callback
            cleep_filesystem (CleepFilesystem): CleepFilesystem singleton
            crash_report (CrashReport): Crash report instance
            task_factory (TaskFactory): TaskFactory instance
        """
        threading.Thread.__init__(
            self, daemon=True, name="updatemodule-%s" % module_name
        )

        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.module_name = module_name
        self.new_module_infos = new_module_infos
        self.force_uninstall = force_uninstall
        self.status_callback = status_callback
        self.cleep_filesystem = cleep_filesystem
        self.crash_report = crash_report
        self.task_factory = task_factory
        self.status = self.STATUS_IDLE
        self._is_uninstalling = True
        # initialized when update process starts
        self.__uninstall_status = {}
        self.__install_status = {}

    def is_updating(self):
        """
        Return True is process is running

        Returns:
            bool: True if running
        """
        return self.status == self.STATUS_UPDATING

    def get_status(self):
        """
        Return update status

        Returns:
            dict: current status::

                {
                    status (int): see STATUS_XXX
                    uninstall (dict): dict as returned by uninstall module status
                    install (dict): dict as returned by install module status
                    module (string): module name
                }

        """
        return {
            "module": self.module_name,
            "status": self.status,
            "uninstall": self.__uninstall_status,
            "install": self.__install_status,
        }

    def _status_callback(self, status):
        """
        Install/Uninstall status callback

        Args:
            status (dict): status returned by install/uninstall
        """
        message = (
            "Update callback from uninstall: %s"
            if self._is_uninstalling
            else "Update callback from install: %s"
        )
        update = (
            self.__uninstall_status.update
            if self._is_uninstalling
            else self.__install_status.update
        )

        # callback from uninstall process
        self.logger.debug(message % status)
        update(status)

        self._step()

    def _step(self):
        """
        Process step
        """
        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except Exception:
                self.logger.exception("Exception occured during status callback call")
                self.status_callback = None

    def run(self):
        """
        Run module update
        """
        try:
            # init
            self.logger.info(
                'Start module "%s" update to v%s',
                self.module_name,
                self.new_module_infos["version"],
            )
            self.status = self.STATUS_UPDATING
            uninstall = UninstallModule(
                self.module_name,
                self.new_module_infos,
                True,
                self.force_uninstall,
                self._status_callback,
                self.cleep_filesystem,
                self.crash_report,
                self.task_factory,
            )
            self.__uninstall_status = uninstall.get_status()
            install = InstallModule(
                self.module_name,
                self.new_module_infos,
                True,
                self._status_callback,
                self.cleep_filesystem,
                self.crash_report,
                self.task_factory,
            )
            self.__install_status = install.get_status()

            # run uninstall
            self._is_uninstalling = True
            uninstall.start()
            sleep(0.5)
            while uninstall.is_uninstalling():
                sleep(0.25)
            if uninstall.get_status()["status"] != uninstall.STATUS_UNINSTALLED:
                # uninstall failed
                # TODO implement rollback reinstalling previous module version
                self.logger.warning(
                    'Error uninstalling "%s" module during update. Try to install new version anyway'
                    % self.module_name
                )
            self._step()

            # run new package install
            self._is_uninstalling = False
            install.start()
            sleep(0.5)
            while install.is_installing():
                sleep(0.25)
            if install.get_status()["status"] != install.STATUS_INSTALLED:
                # install failed
                # TODO implement rollback reinstalling previous module version
                self.logger.error(
                    'Error installing new "%s" module version during update'
                    % self.module_name
                )
                raise ForcedException()
            self._step()

            # set final status
            self.status = self.STATUS_UPDATED

        except ForcedException:
            # error during update
            self.status = self.STATUS_ERROR

        except Exception:
            # unexpected error
            self.status = self.STATUS_ERROR
            self.logger.exception(
                'Exception occured during "%s" module update' % self.module_name
            )

        # finalize update
        success = self.status == self.STATUS_UPDATED
        self.logger.info(
            'Module "%s" installation terminated (success:%s)'
            % (self.module_name, success)
        )
        self._step()
