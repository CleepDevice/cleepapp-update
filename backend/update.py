#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import random
import copy
import importlib
import re
import shutil
import tempfile
import json
import fcntl
from zipfile import ZipFile
import cleep.libs.internals.tools as Tools
from cleep.exception import (
    MissingParameter,
    InvalidParameter,
    CommandError,
    CommandInfo,
)
from cleep.core import CleepModule
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.internals.download import Download
from cleep.common import CORE_MODULES
from cleep import __version__ as CLEEP_VERSION

try:
    from .install.install_app import PATH_INSTALL
    from .install.appssources import AppsSources
    from .install.cleepgithub import CleepGithub
    from .install.installcleep import InstallCleep
    from .install.install import Install
except ImportError:  # pragma: no cover - flat import in tests / module loader
    from install.install_app import PATH_INSTALL
    from install.appssources import AppsSources
    from install.cleepgithub import CleepGithub
    from install.installcleep import InstallCleep
    from install.install import Install

try:
    from .os_identity import get_os_identity
    from .os_catalog import (
        evaluate_os_update,
        ensure_os_playbook,
        fetch_os_catalog,
    )
    from .os_upgrade_runner import OsUpgradeRunner
    from .os_conf_report import (
        DEFAULT_REPORT_PATH,
        build_os_conf_report,
        sentry_extra_from_report,
    )
    from .os_dry_run_analysis import (
        analyze_os_dry_run,
        dry_run_errors_reportable_to_sentry,
        format_analysis_section,
        sentry_extra_from_dry_run_analysis,
    )
except ImportError:  # pragma: no cover - flat import in tests / module loader
    from os_identity import get_os_identity
    from os_catalog import (
        evaluate_os_update,
        ensure_os_playbook,
        fetch_os_catalog,
    )
    from os_upgrade_runner import OsUpgradeRunner
    from os_conf_report import (
        DEFAULT_REPORT_PATH,
        build_os_conf_report,
        sentry_extra_from_report,
    )
    from os_dry_run_analysis import (
        analyze_os_dry_run,
        dry_run_errors_reportable_to_sentry,
        format_analysis_section,
        sentry_extra_from_dry_run_analysis,
    )


class Update(CleepModule):
    """
    Update application: market apps, Cleep core, and minor CleepOs upgrades.
    """

    MODULE_AUTHOR = "Cleep"
    MODULE_VERSION = "1.6.0"
    MODULE_DEPS = []
    MODULE_DESCRIPTION = "Applications, Cleep and CleepOs updater"
    MODULE_LONGDESCRIPTION = (
        "Keep your device up to date: applications from the market, the Cleep core, "
        "and minor CleepOs system upgrades. "
        "On the OS tab, check for updates, optionally run a dry-run then apply the upgrade. "
        "After a successful OS apply, use the device reboot button in the top bar. "
        "You can review the last attempt log and optionally send a path-only "
        "leftover conf report to help improve future migrations."
    )
    MODULE_TAGS = ["update", "application", "module", "cleep", "os", "cleepos"]
    MODULE_CATEGORY = "APPLICATION"
    MODULE_COUNTRY = None
    MODULE_URLINFO = "https://github.com/CleepDevice/cleepapp-update"
    MODULE_URLHELP = (
        "https://github.com/CleepDevice/cleepapp-update/blob/master/README.md"
    )
    MODULE_URLSITE = None
    MODULE_URLBUGS = "https://github.com/CleepDevice/cleepapp-update/issues"

    MODULE_CONFIG_FILE = "update.conf"
    DEFAULT_CONFIG = {
        "cleepupdateenabled": False,
        "modulesupdateenabled": False,
        "cleepversion": "0.0.0",
        "cleeplastcheck": None,
        "moduleslastcheck": None,
        "oslastcheck": None,
        # Last OS apply attempt (survives Cleep restart); dry-run is stored separately
        "oslastattempt": None,
        "oslastdryrun": None,
        # OS conf leftover report (paths only) after playbook upgrade
        "osconfreportenabled": False,
        "osconfreportautosend": False,
        "osconfreport": None,
        # Target CleepOs version for which a post-discovery dry-run was already started
        "osdiscovereddryrunfor": None,
    }

    CLEEP_GITHUB_OWNER = "CleepDevice"
    CLEEP_GITHUB_REPO = "cleep"
    PROCESS_STATUS_SUCCESS_FILENAME = "process_success.log"
    PROCESS_STATUS_FAILURE_FILENAME = "process_failure.log"
    CLEEP_STATUS_FILEPATH = ""
    ACTION_MODULE_INSTALL = "install"
    ACTION_MODULE_UPDATE = "update"
    ACTION_MODULE_UNINSTALL = "uninstall"

    MAIN_ACTIONS_TASK_INTERVAL = 1.0
    SUB_ACTIONS_TASK_INTERVAL = 1.0

    PYTHON_CLEEP_IMPORT_PATH = "cleep.modules."
    PACKAGE_BASE_PATH = "/tmp/%(module_name)s.zip"
    # /tmp is always writable (rootfs may be RO); flock is released on process death
    UPDATE_LOCK_PATH = "/tmp/cleep/update.lock"
    # Minimum free space before downloading/installing Cleep .deb
    CLEEP_UPDATE_MIN_FREE_BYTES = 150 * 1024 * 1024

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Params:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)
        # self.logger.setLevel(logging.TRACE)

        # members
        self.apps_sources = AppsSources(self.cleep_filesystem, self.task_factory)
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self._modules_updates = {}
        self._cleep_updates = {
            "updatable": False,
            "processing": False,
            "pending": False,
            "failed": False,
            "version": None,
            "changelog": None,
            "packageurl": None,
            "checksumurl": None,
        }
        self._os_updates = {
            "updatable": False,
            "processing": False,
            "pending": False,
            "failed": False,
            "version": None,
            "current": None,
            "suite": None,
            "changelog": None,
            "playbook_url": None,
            "playbook_sha256": None,
            "min_cleep_version": None,
            "min_suite": None,
            "blocks_cleep_update": False,
            "os_suite_too_old": False,
            "cleep_too_old": False,
            "dry_run": False,
            "status": 0,
            "progress": 0,
            "phase": None,
            "error": None,
            "log_path": None,
        }
        self._os_upgrade_dry_run = False
        self._os_dry_run_preview = None
        self._check_update_time = {
            "hour": int(random.uniform(0, 24)),
            "minute": int(random.uniform(0, 60)),
        }
        self.logger.info(
            "Software updates will be checked every day at %(hour)02d:%(minute)02d"
            % self._check_update_time
        )
        self.__processor = None
        self.__lock_fd = None
        self._need_restart = False
        # contains main actions (install/uninstall/update)
        self.__main_actions = []
        self.__main_actions_task = None
        # contains sub actions of mains actions (to perform action on dependencies)
        self.__sub_actions = []
        self.__sub_actions_task = None
        self.compat_pattern = r"(.*?)([><=]{1,2})(\d+\.\d+\.\d+)"

        # events
        self.module_install_event = self._get_event("update.module.install")
        self.module_uninstall_event = self._get_event("update.module.uninstall")
        self.module_update_event = self._get_event("update.module.update")
        self.cleep_update_event = self._get_event("update.cleep.update")
        self.os_update_event = self._get_event("update.os.update")
        self.cleep_need_restart_event = self._get_event("system.cleep.needrestart")
        self.device_need_reboot_event = self._get_event("system.device.needreboot")
        self.__os_runner = None

    def _configure(self):
        """
        Configure module
        """
        self._set_config_field("cleepversion", CLEEP_VERSION)

    def _on_start(self):
        """
        Module is started
        """
        self._migrate_os_attempt_split()
        self._reconcile_os_last_attempt_after_restart()
        # init installed modules
        self._fill_modules_updates()
        # Restore top-bar *reboot* button only if a successful OS apply still needs
        # a device reboot (cleared above when the device already rebooted).
        last = self._get_config_field("oslastattempt") or {}
        if (
            last.get("state") == "success"
            and not last.get("dry_run")
            and last.get("reboot_needed")
        ):
            self.device_need_reboot_event.send()
            self.logger.info("Restored device reboot toolbar button after OS upgrade")

    def _get_system_boot_time(self):
        """
        Return unix timestamp of last device boot, or None if unknown.
        """
        try:
            with open("/proc/uptime", encoding="utf8") as handle:
                uptime = float(handle.read().split()[0])
            return time.time() - uptime
        except (OSError, ValueError, IndexError):
            return None

    def _device_rebooted_since(self, timestamp):
        """
        Return True when the device boot time is strictly after timestamp.

        Used to clear OS reboot reminders after a real reboot (manual or triggered),
        without clearing them on a Cleep-only process restart.
        """
        if timestamp is None:
            return False
        try:
            stamp = float(timestamp)
        except (TypeError, ValueError):
            return False
        boot_time = self._get_system_boot_time()
        if boot_time is None:
            return False
        return boot_time > stamp

    def _migrate_os_attempt_split(self):
        """
        Move legacy dry-run records out of oslastattempt into oslastdryrun.

        Older builds stored apply and dry-run in the same config key; that made
        Show log point at the wrong file after an Apply.
        """
        last = self._get_config_field("oslastattempt") or {}
        if not last.get("dry_run"):
            return
        if not self._get_config_field("oslastdryrun"):
            migrated = dict(last)
            migrated["log_path"] = (
                migrated.get("log_path") or OsUpgradeRunner.DRY_RUN_LOG_PATH
            )
            self._set_config_field("oslastdryrun", migrated)
            self.logger.info("Migrated legacy dry-run attempt into oslastdryrun")
        self._set_config_field("oslastattempt", None)

    def _reconcile_os_last_attempt_after_restart(self):
        """Mark stale in-progress OS attempts as failed after Cleep restart."""
        self._reconcile_os_attempt_field("oslastattempt", apply_side=True)
        self._reconcile_os_attempt_field("oslastdryrun", apply_side=False)

    def _reconcile_os_attempt_field(self, field_name, *, apply_side):
        last = self._get_config_field(field_name)
        if not last:
            return
        if last.get("state") == "running":
            default_log = (
                OsUpgradeRunner.LOG_PATH
                if apply_side
                else OsUpgradeRunner.DRY_RUN_LOG_PATH
            )
            log_path = last.get("log_path") or default_log
            record = dict(last)
            record.update(
                {
                    "state": "failed",
                    "finished_at": int(time.time()),
                    "error": "Interrupted (Cleep restarted while update was running)",
                    "reboot_needed": False,
                    "reboot_triggered": False,
                }
            )
            excerpt = self._read_os_upgrade_log_excerpt(log_path)
            if excerpt:
                record["log_excerpt"] = excerpt
            self._set_config_field(field_name, record)
            self.logger.warning(
                "Previous OS %s was still running at shutdown — marked as failed",
                "apply" if apply_side else "dry-run",
            )
            return
        if not apply_side:
            return
        # Clear reboot reminder after a real device reboot (or after we triggered one).
        # Do not clear on Cleep-only restart: boot time stays older than finished_at.
        if (
            last.get("state") == "success"
            and not last.get("dry_run")
            and last.get("reboot_needed")
        ):
            finished_at = last.get("finished_at") or last.get("started_at")
            rebooted = self._device_rebooted_since(finished_at)
            if last.get("reboot_triggered") or rebooted:
                record = dict(last)
                record["reboot_needed"] = False
                record["reboot_triggered"] = False
                self._set_config_field(field_name, record)
                self.logger.info(
                    "Cleared OS reboot reminder after device restart (rebooted=%s)",
                    rebooted,
                )

    def _on_stop(self):
        """
        Module stopped
        """
        self.__stop_actions_tasks()
        self._release_update_lock()

    def _acquire_update_lock(self):
        """
        Acquire exclusive non-blocking file lock for update operations.

        Raises:
            CommandInfo: if another process already holds the lock
        """
        if self.__lock_fd is not None:
            return

        lock_dir = os.path.dirname(self.UPDATE_LOCK_PATH)
        os.makedirs(lock_dir, exist_ok=True)
        lock_fd = open(self.UPDATE_LOCK_PATH, "a+", encoding="utf8")
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            lock_fd.close()
            raise CommandInfo(
                "An update operation is already in progress. Please wait for end of it"
            ) from error
        except OSError as error:
            lock_fd.close()
            self.logger.error("Unable to acquire update lock: %s", error)
            raise CommandError("Unable to acquire update lock") from error

        self.__lock_fd = lock_fd
        self.logger.debug("Update lock acquired (%s)", self.UPDATE_LOCK_PATH)

    def _release_update_lock(self):
        """
        Release update file lock if held.
        """
        if self.__lock_fd is None:
            return

        try:
            fcntl.flock(self.__lock_fd.fileno(), fcntl.LOCK_UN)
            self.__lock_fd.close()
        except OSError:
            self.logger.warning("Error releasing update lock", exc_info=True)
        finally:
            self.__lock_fd = None
            self.logger.debug("Update lock released")

    def get_module_config(self):
        """
        Return module configuration

        Returns:
            dict: configuration including runtime OS status for frontend reload
        """
        config = self._get_config()
        os_info = None
        try:
            os_info = get_os_identity()
        except (ValueError, OSError):
            self.logger.debug(
                "Unable to read CleepOs identity for module config", exc_info=True
            )

        config.update(
            {
                "cleepupdatelogs": self._get_last_update_logs("cleep"),
                # Runtime fields (not persisted): restored on websocket reconnect via config push
                "osinfo": os_info,
                "osupdates": self._enrich_os_updates(self._os_updates),
            }
        )

        return config

    def on_event(self, event):
        """
        Event received

        Params:
            event (MessageRequest): event data
        """
        if event["event"] == "parameters.time.now":
            # update
            if (
                event["params"]["hour"] == self._check_update_time["hour"]
                and event["params"]["minute"] == self._check_update_time["minute"]
            ):
                # check updates
                self.check_cleep_updates()
                self.check_modules_updates()
                try:
                    self.check_os_updates()
                except Exception:  # pragma: no cover
                    self.crash_report.report_exception()

                # and perform updates if allowed
                # update in priority cleep then modules
                config = self._get_config()
                if config["cleepupdateenabled"]:
                    try:
                        self.update_cleep()
                    except Exception:  # pragma: no cover
                        self.crash_report.report_exception()
                if config["modulesupdateenabled"]:
                    try:
                        self.update_modules()
                    except Exception:  # pragma: no cover
                        self.crash_report.report_exception()

    def get_modules_logs(self):
        """
        Return all modules logs

        Returns:
            dict: list of log files::

            {
                module name: {
                    timestamp (int)
                    path (string)
                    failed (bool)
                }
                ...
            }

        """
        out = {}

        if not os.path.exists(PATH_INSTALL):
            return out

        installed_modules = self._get_installed_modules_names()
        module_names = os.listdir(PATH_INSTALL)
        for module_name in module_names:
            if module_name == "cleep":
                continue

            infos = self._get_last_update_logs(module_name)
            if not infos:
                continue

            infos.update(
                {
                    "name": module_name,
                    "installed": module_name in installed_modules,
                }
            )
            out[module_name] = infos

        return out

    def _get_last_update_logs(self, module_name):
        """
        Return infos about last cleep update logs

        Args:
            module_name (string): module name to search log for. If it is cleep last update
                                  log, specify "cleep" as module name.

        Returns:
            dict: last cleep update logs or None if no logs::

            {
                timestamp (int): logs file timestamp
                path (string): log file path
                failed (bool): True if last update failed
            }

        """
        path_success = os.path.join(
            PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME
        )
        timestamp_success = 0
        if os.path.exists(path_success):
            timestamp_success = int(os.path.getmtime(path_success))
        path_failure = os.path.join(
            PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME
        )
        timestamp_failure = 0
        if os.path.exists(path_failure):
            timestamp_failure = int(os.path.getmtime(path_failure))

        if timestamp_success == 0 and timestamp_failure == 0:
            return None

        # keep most recent one
        if timestamp_success > timestamp_failure:
            return {
                "timestamp": timestamp_success,
                "path": path_success,
                "failed": False,
            }

        return {
            "timestamp": timestamp_failure,
            "path": path_failure,
            "failed": True,
        }

    def get_logs(self, module_name):
        """
        Get logs content for specified module or cleep

        Args:
            module_name (string): module name. Specify "cleep" to retrieve logs for cleep
        """
        path_success = os.path.join(
            PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME
        )
        timestamp_success = 0
        if os.path.exists(path_success):
            timestamp_success = int(os.path.getmtime(path_success))
        path_failure = os.path.join(
            PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME
        )
        timestamp_failure = 0
        if os.path.exists(path_failure):
            timestamp_failure = int(os.path.getmtime(path_failure))

        if timestamp_success == 0 and timestamp_failure == 0:
            raise CommandError(f'There is no logs for app "{module_name}"')

        path = path_failure
        if timestamp_success > timestamp_failure:
            path = path_success

        lines = self.cleep_filesystem.read_data(path, encoding="utf8")
        if lines is None:
            raise CommandError(f'Error reading app "{module_name}" logs file')

        return "".join(lines)

    def get_modules_updates(self):
        """
        Return list of modules updates

        Returns:
            dict: list of modules updates::

            {
                module name (string): {
                },
                ...
            }

        """
        return self._modules_updates

    def get_market(self):
        """
        Return cached market catalog (does not force a remote refresh).

        Returns:
            dict: market content ``{ update (int), list (dict) }``
        """
        return self.apps_sources.get_market()

    def get_installable_modules(self):
        """
        Return market applications that can be installed (or are libraries).

        Returns:
            dict: installable modules keyed by name (market metadata + runtime flags)
        """
        market = self.apps_sources.get_market()
        resp = self.send_command("get_modules", "inventory", timeout=20)
        installed = {} if resp.error or not resp.data else resp.data

        modules_versions = {
            name: mod.get("version", "0.0.0") for name, mod in installed.items()
        }
        modules_versions["cleep"] = CLEEP_VERSION

        result = {}
        for module_name, module_data in market.get("list", {}).items():
            runtime = installed.get(module_name) or {}
            is_installed = bool(runtime.get("installed"))
            is_library = bool(runtime.get("library"))
            # Keep libraries and not-installed apps in the installable catalog
            if is_installed and not is_library:
                continue
            entry = copy.deepcopy(module_data)
            compat = entry.get("compat", "")
            entry.update(
                {
                    "name": module_name,
                    "installed": is_installed,
                    "library": is_library,
                    "local": bool(runtime.get("local")),
                    "core": module_name in CORE_MODULES,
                    "compat": compat,
                    "compatible": Tools.compare_compat_string(compat, modules_versions),
                    "version": entry.get("version", "0.0.0"),
                    "deps": entry.get("deps", []),
                }
            )
            result[module_name] = entry
        return result

    def get_cleep_updates(self):
        """
        Return cleep update infos

        Returns:
            dict: Cleep update infos::

            {
                updatable (bool): true if new version available
                processing (bool): true if cleep update is running
                pending (bool): true if cleep update has been done and a restart is required
                failed (bool): True if last update failed
                version (string): new available version (format x.x.x) (None if no update)
                changelog (string): update changelog (None if no update)
                packageurl (string): package url (None if no update)
                checksumurl (string): package checksum url (None if no update)
            }

        """
        return self._cleep_updates

    def get_os_info(self):
        """
        Return current CleepOs identity from /etc/cleepos_version.

        Returns:
            dict: current CleepOs identity::

                {
                    version (str): e.g. bullseye20231205
                    suite (str): e.g. bullseye
                    build (str): YYYYMMDD
                }

        Raises:
            CommandError: if /etc/cleepos_version is missing or invalid
        """
        try:
            return get_os_identity()
        except FileNotFoundError as error:
            raise CommandError(
                "Missing /etc/cleepos_version — this file is required for OS updates"
            ) from error
        except OSError as error:
            raise CommandError(
                f"Unable to read /etc/cleepos_version: {error}"
            ) from error
        except ValueError as error:
            raise CommandError(str(error)) from error

    def get_os_updates(self):
        """
        Return last OS update check result (cached in memory, enriched with last attempt).

        Returns:
            dict: OS updates infos (same shape as check_os_updates), plus::

                {
                    updatable (bool): True if a newer CleepOs is available
                    processing (bool): True if an OS upgrade or dry-run is running
                    pending (bool): True if apply succeeded and reboot is still recommended
                    failed (bool): True if last attempt failed
                    version (str): target CleepOs version when updatable (None otherwise)
                    current (str): installed CleepOs version
                    suite (str): Debian suite name
                    changelog (str): target changelog (None if not updatable)
                    playbook_url (str): playbook URL from catalog / default remote
                    playbook_sha256 (str): optional playbook checksum (None if none)
                    min_cleep_version (str): minimum Cleep version required (None if none)
                    blocks_cleep_update (bool): True if Cleep update must wait for OS
                    cleep_too_old (bool): True if OS update exists but Cleep is too old
                    dry_run (bool): True while a dry-run is running
                    status (int): runner status (0 idle, 1 running, 2 success, 3 error)
                    progress (int): 0-100 progress while processing
                    phase (str): current playbook phase name (None if idle)
                    error (str): last failure message (None if none)
                    log_path (str): path to upgrade or dry-run log (None if none)
                    reboot_needed (bool): True if reboot is still recommended after apply
                    reboot_triggered (bool): True if a reboot was already requested
                    last_attempt (dict): persisted last attempt from module config (None if none)
                }
        """
        return self._enrich_os_updates(self._os_updates)

    def _enrich_os_updates(self, update):
        """Merge persisted last attempt and in-memory processing state."""
        out = dict(update)
        last = self._get_config_field("oslastattempt")
        last_dry = self._get_config_field("oslastdryrun")
        if last:
            out["last_attempt"] = last
            if not out.get("processing"):
                state = last.get("state")
                if state == "failed":
                    out["failed"] = True
                    out["error"] = last.get("error")
                    out["log_path"] = last.get("log_path") or OsUpgradeRunner.LOG_PATH
                    out["pending"] = False
                    out["reboot_needed"] = False
                elif state == "success" and last.get("dry_run"):
                    # Legacy mixed record; prefer apply-only semantics after migration
                    out["failed"] = False
                elif state == "success" and not last.get("dry_run"):
                    out["failed"] = False
                    # Apply succeeded: keep "reboot recommended" until cleared
                    reboot_needed = bool(last.get("reboot_needed", True))
                    out["reboot_needed"] = reboot_needed
                    out["pending"] = reboot_needed
                    out["reboot_triggered"] = bool(last.get("reboot_triggered", False))
                    out["log_path"] = last.get("log_path") or OsUpgradeRunner.LOG_PATH
                    if last.get("to_version"):
                        out["current"] = last.get("to_version")
                        out["updatable"] = False
        if last_dry:
            out["last_dry_run"] = last_dry
        return out

    def _download_url_content(self, url):
        """
        Download small remote content (UTF-8 text).

        Args:
            url (str): remote URL

        Returns:
            str|None: content or None on failure
        """
        download = Download(self.cleep_filesystem, self.task_factory)
        _status, content = download.download_content(url)
        return content

    def check_os_updates(self):
        """
        Check for CleepOs updates using remote ``os-versions.json`` (cleep-os),
        with a local cache of the last successful download.

        Stores the check timestamp in module config and returns the evaluation result.

        Returns:
            dict: OS updates infos::

                {
                    updatable (bool): True if a newer CleepOs is available
                    processing (bool): True if an OS upgrade or dry-run is running
                    pending (bool): True if apply succeeded and reboot is still recommended
                    failed (bool): True if last attempt failed
                    version (str): target CleepOs version when updatable (None otherwise)
                    current (str): installed CleepOs version
                    suite (str): Debian suite name
                    changelog (str): target changelog (None if not updatable)
                    playbook_url (str): playbook URL (remote default when catalog leaves it null)
                    playbook_sha256 (str): optional playbook checksum (None if none)
                    min_cleep_version (str): minimum Cleep version required (None if none)
                    blocks_cleep_update (bool): True if Cleep update must wait for OS
                    cleep_too_old (bool): True if OS update exists but Cleep is too old
                    dry_run (bool): True while a dry-run is running
                    status (int): runner status (0 idle, 1 running, 2 success, 3 error)
                    progress (int): 0-100 progress while processing
                    phase (str): current playbook phase name (None if idle)
                    error (str): last failure message (None if none)
                    log_path (str): path to upgrade or dry-run log (None if none)
                    last_attempt (dict): persisted last attempt from module config (None if none)
                }

        Raises:
            CommandError: if current CleepOs release cannot be read or check fails
        """
        try:
            identity = get_os_identity()
            catalog = fetch_os_catalog(self._download_url_content)
            update = evaluate_os_update(identity, catalog, CLEEP_VERSION)
        except ValueError as error:
            raise CommandError("Unable to read current CleepOs release") from error
        except Exception as error:
            self.logger.exception("Error occured during OS updates checking:")
            self.crash_report.report_exception()
            raise CommandError("Error occured during OS update check") from error

        self._set_config_field("oslastcheck", int(time.time()))
        update["processing"] = self._os_updates.get("processing", False)
        update["pending"] = self._os_updates.get("pending", False)
        update["failed"] = self._os_updates.get("failed", False)
        update["dry_run"] = self._os_updates.get("dry_run", False)
        update["status"] = self._os_updates.get("status", 0)
        update["progress"] = self._os_updates.get("progress", 0)
        update["phase"] = self._os_updates.get("phase")
        update["error"] = self._os_updates.get("error")
        update["log_path"] = self._os_updates.get("log_path")
        self._os_updates = update
        self.logger.info(
            "CleepOs version status: latest %s - installed %s (suite %s, updatable=%s)",
            update.get("version") or update.get("current"),
            update.get("current"),
            update.get("suite"),
            update.get("updatable"),
        )
        self._maybe_trigger_discovery_os_dry_run(update)
        return self._enrich_os_updates(self._os_updates)

    def _maybe_trigger_discovery_os_dry_run(self, update):
        """
        Run one dry-run when a new target CleepOs version is discovered (not on every daily check).
        """
        if not update.get("updatable"):
            return
        target_version = update.get("version")
        if not target_version:
            return
        if update.get("cleep_too_old"):
            self.logger.info(
                "Skip auto OS dry-run: Cleep too old for target %s", target_version
            )
            return
        if self._get_config_field("osdiscovereddryrunfor") == target_version:
            return
        if self._os_updates.get("processing"):
            return
        if self._cleep_updates.get("processing") or self._cleep_updates.get("pending"):
            self.logger.info("Skip auto OS dry-run: Cleep update in progress")
            return
        if len(self.__main_actions) != 0:
            self.logger.info("Skip auto OS dry-run: module updates in progress")
            return
        self.logger.info(
            "New CleepOs update discovered (%s) — starting one-shot dry-run",
            target_version,
        )
        try:
            self.update_os(dry_run=True)
        except CommandInfo as error:
            self.logger.info("Auto OS dry-run not started: %s", error)
        except Exception:  # pragma: no cover
            self.logger.exception("Auto OS dry-run failed to start")
            self.crash_report.report_exception()

    def _assert_os_allows_cleep_update(self):
        """
        Soft gate: block Cleep update when catalog marks OS update as required first.

        Refreshes the OS catalog check so the gate is not based on a stale in-memory state.
        """
        try:
            self.check_os_updates()
        except CommandError:
            self.logger.warning(
                "OS update check failed before Cleep update gate; using last known state",
                exc_info=True,
            )
        if self._os_updates.get("blocks_cleep_update"):
            if self._os_updates.get("os_suite_too_old"):
                raise CommandInfo(
                    "CleepOs suite %s is no longer supported for new Cleep installs "
                    "(minimum suite: %s). Upgrade CleepOs (major) or reflash before "
                    "updating Cleep."
                    % (
                        self._os_updates.get("suite") or "?",
                        self._os_updates.get("min_suite") or "?",
                    )
                )
            raise CommandInfo(
                "A system update (CleepOs) is required before updating Cleep. "
                "Please update CleepOs first."
            )

    def update_os(self, dry_run=False):
        """
        Start a CleepOs minor suite upgrade using the remote playbook (cached locally).

        Runs asynchronously. Progress is reported with the ``update.os.update`` event.
        After a successful apply (not dry-run), ``system.device.needreboot`` is emitted
        so the top-bar device reboot button appears (not a Cleep-only restart).

        Args:
            dry_run (bool, optional): Simulate apt only without installing packages or stamping version. Defaults to False.

        Raises:
            InvalidParameter: if dry_run is not a boolean
            CommandInfo: if no OS update is available, Cleep is too old, or another update runs
            CommandError: if the OS update target version is missing or playbook cannot be prepared
        """
        if not isinstance(dry_run, bool):
            raise InvalidParameter('Parameter "dry_run" is invalid')
        if not self._os_updates.get("updatable"):
            raise CommandInfo(
                "No OS update available, please launch OS update check first"
            )
        if self._os_updates.get("cleep_too_old"):
            raise CommandInfo("Please update Cleep before applying this OS update")
        if self._cleep_updates["processing"] or self._cleep_updates["pending"]:
            raise CommandInfo("Cleep update is in progress. Please wait for end of it")
        if self._os_updates.get("processing"):
            raise CommandInfo("OS update is in progress. Please wait for end of it")
        if len(self.__main_actions) != 0:
            raise CommandInfo(
                "Applications updates are in progress. Please wait for end of it"
            )

        target_version = self._os_updates.get("version")
        if not target_version:
            raise CommandError("OS update target version is missing")

        try:
            self._os_upgrade_from_version = get_os_identity().get("version")
        except ValueError:
            self._os_upgrade_from_version = self._os_updates.get("current")

        self._os_upgrade_dry_run = dry_run
        log_path = (
            OsUpgradeRunner.DRY_RUN_LOG_PATH if dry_run else OsUpgradeRunner.LOG_PATH
        )
        self._persist_os_last_attempt(
            state="running",
            dry_run=dry_run,
            from_version=self._os_upgrade_from_version,
            to_version=target_version,
            log_path=log_path,
            phase=None,
            progress=0,
            error=None,
            finished=False,
        )
        self._acquire_update_lock()
        try:
            self.cleep_filesystem.enable_write(True, True)
            suite = self._os_updates.get("suite") or "bullseye"
            try:
                playbook_path = ensure_os_playbook(
                    suite,
                    playbook_url=self._os_updates.get("playbook_url"),
                    playbook_sha256=self._os_updates.get("playbook_sha256"),
                    download_content=self._download_url_content,
                )
            except Exception as error:
                raise CommandError("Unable to prepare OS playbook") from error

            self._os_updates.update(
                {
                    "failed": False,
                    "pending": False,
                    "processing": True,
                    "dry_run": dry_run,
                    "status": OsUpgradeRunner.STATUS_RUNNING,
                    "progress": 0,
                    "phase": None,
                    "error": None,
                    "log_path": (
                        OsUpgradeRunner.DRY_RUN_LOG_PATH
                        if dry_run
                        else OsUpgradeRunner.LOG_PATH
                    ),
                }
            )
            self.__os_runner = OsUpgradeRunner(
                target_version=target_version,
                status_callback=self._update_os_callback,
                playbook_path=playbook_path,
                dry_run=dry_run,
            )
            self.__os_runner.start()
            if dry_run:
                self._set_config_field("osdiscovereddryrunfor", target_version)
        except Exception:
            self._os_updates["processing"] = False
            self._os_updates["dry_run"] = False
            self._os_upgrade_dry_run = False
            self._release_update_lock()
            raise

    OS_UPGRADE_LOG_EXCERPT_BYTES = 12000

    def _os_attempt_config_field(self, dry_run):
        """Return config key used to persist apply vs dry-run attempts."""
        return "oslastdryrun" if dry_run else "oslastattempt"

    def _persist_os_last_attempt(
        self,
        *,
        state,
        dry_run,
        from_version,
        to_version,
        log_path,
        phase=None,
        progress=None,
        error=None,
        finished=True,
        log_excerpt=None,
        reboot_needed=None,
        reboot_triggered=None,
    ):
        """Save last OS apply or dry-run attempt in module config (persists across Cleep restart)."""
        dry_run = bool(dry_run)
        field = self._os_attempt_config_field(dry_run)
        previous = self._get_config_field(field) or {}
        now = int(time.time())
        if not log_path:
            log_path = (
                OsUpgradeRunner.DRY_RUN_LOG_PATH
                if dry_run
                else OsUpgradeRunner.LOG_PATH
            )
        record = {
            "state": state,
            "dry_run": dry_run,
            "from_version": from_version,
            "to_version": to_version,
            "phase": phase,
            "progress": progress,
            "error": error,
            "log_path": log_path,
            "started_at": previous.get("started_at") or now,
            "finished_at": now if finished else None,
            "reboot_needed": (
                previous.get("reboot_needed", False) if not dry_run else False
            ),
            "reboot_triggered": (
                previous.get("reboot_triggered", False) if not dry_run else False
            ),
        }
        if state == "running":
            record["started_at"] = now
            record["finished_at"] = None
            record["reboot_needed"] = False
            record["reboot_triggered"] = False
        if not dry_run:
            if reboot_needed is not None:
                record["reboot_needed"] = bool(reboot_needed)
            if reboot_triggered is not None:
                record["reboot_triggered"] = bool(reboot_triggered)
        if log_excerpt is None and finished and log_path:
            log_excerpt = self._read_os_upgrade_log_excerpt(log_path)
        if log_excerpt:
            record["log_excerpt"] = log_excerpt
        elif finished and previous.get("log_excerpt"):
            # Keep previous excerpt only when reading the same kind of log failed
            record["log_excerpt"] = previous.get("log_excerpt")
        self._set_config_field(field, record)

    def _read_os_upgrade_log_excerpt(self, log_path, max_bytes=None):
        """Return tail of OS upgrade log for config persistence."""
        max_bytes = max_bytes or self.OS_UPGRADE_LOG_EXCERPT_BYTES
        if not log_path or not os.path.isfile(log_path):
            return None
        try:
            with open(log_path, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - max_bytes))
                data = handle.read()
            return data.decode("utf8", errors="replace")
        except OSError:
            self.logger.warning("Unable to read OS upgrade log excerpt", exc_info=True)
            return None

    def _finalize_os_last_attempt_from_callback(
        self, status, *, dry_run, success, reboot_needed=None, reboot_triggered=None
    ):
        """Persist terminal OS upgrade attempt state."""
        log_path = status.get("log_path") or (
            OsUpgradeRunner.DRY_RUN_LOG_PATH if dry_run else OsUpgradeRunner.LOG_PATH
        )
        if success:
            state = "success"
            error = None
            if dry_run:
                reboot_needed = False
                reboot_triggered = False
            elif reboot_needed is None:
                reboot_needed = True
        else:
            state = "failed"
            error = status.get("error") or "unknown error"
            reboot_needed = False
            reboot_triggered = False
        self._persist_os_last_attempt(
            state=state,
            dry_run=dry_run,
            from_version=getattr(self, "_os_upgrade_from_version", None)
            or self._os_updates.get("current"),
            to_version=self._os_updates.get("version"),
            log_path=log_path,
            phase=status.get("phase"),
            progress=status.get("progress"),
            error=error,
            finished=True,
            reboot_needed=reboot_needed,
            reboot_triggered=reboot_triggered,
        )

    def request_os_reboot(self):
        """
        Trigger a device reboot after a successful OS upgrade.

        Prefer the top-bar reboot button (``system.device.needreboot``); this RPC is a fallback.

        Returns:
            dict: reboot request result::

                {
                    reboot_triggered (bool): True when reboot was accepted
                }

        Raises:
            CommandInfo: if there is no successful OS apply pending a reboot
            CommandError: if the system reboot command fails
        """
        last = self._get_config_field("oslastattempt") or {}
        if last.get("state") != "success" or last.get("dry_run"):
            raise CommandInfo("No successful OS upgrade pending a reboot")
        resp = self.send_command("reboot_device", "system", {"delay": 5.0})
        if resp.error:
            raise CommandError("Unable to reboot device")
        record = dict(last)
        record["reboot_triggered"] = True
        record["reboot_needed"] = True
        self._set_config_field("oslastattempt", record)
        self._os_updates.update(
            {
                "pending": True,
                "reboot_needed": True,
                "reboot_triggered": True,
            }
        )
        return {"reboot_triggered": True}

    def show_os_reboot_button(self):
        """
        Re-emit ``system.device.needreboot`` so the top-bar device reboot button is shown.

        Returns:
            dict: display result::

                {
                    shown (bool): True when the event was sent
                }

        Raises:
            CommandInfo: if no OS reboot is currently required
        """
        last = self._get_config_field("oslastattempt") or {}
        if (
            last.get("state") != "success"
            or last.get("dry_run")
            or not last.get("reboot_needed")
        ):
            raise CommandInfo("No OS reboot is currently required")
        self.device_need_reboot_event.send()
        return {"shown": True}

    def get_os_upgrade_logs(self, dry_run=False):
        """
        Return OS apply or dry-run log contents for UI display.

        Prefers the live log file under /tmp; falls back to the excerpt saved in
        module config if the file is gone (for example after reboot).

        Args:
            dry_run (bool): True to read the dry-run log, False for apply log

        Returns:
            dict: log payload::

                {
                    text (str): full log or saved excerpt
                    path (str): log file path
                    from_excerpt (bool): True when content comes from saved config
                    dry_run (bool): True when this is the dry-run log
                }

        Raises:
            CommandError: if the path is invalid or no log is available
            InvalidParameter: if dry_run is not a boolean
        """
        if not isinstance(dry_run, bool):
            raise InvalidParameter('Parameter "dry_run" is invalid')
        dry_run = bool(dry_run)
        field = self._os_attempt_config_field(dry_run)
        last = self._get_config_field(field) or {}
        path = OsUpgradeRunner.DRY_RUN_LOG_PATH if dry_run else OsUpgradeRunner.LOG_PATH
        allowed = (
            OsUpgradeRunner.LOG_PATH,
            OsUpgradeRunner.DRY_RUN_LOG_PATH,
        )
        if path not in allowed:
            raise CommandError("Invalid OS upgrade log path")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf8", errors="replace") as handle:
                    return {
                        "text": handle.read(),
                        "path": path,
                        "from_excerpt": False,
                        "dry_run": dry_run,
                    }
            except OSError as error:
                raise CommandError("Unable to read OS upgrade log") from error
        excerpt = last.get("log_excerpt")
        if excerpt:
            return {
                "text": excerpt,
                "path": path,
                "from_excerpt": True,
                "dry_run": dry_run,
            }
        raise CommandError(
            "No OS dry-run log available on this device"
            if dry_run
            else "No OS upgrade log available on this device"
        )

    def get_os_dry_run_preview(self):
        """
        Return the last OS upgrade dry-run preview (apt simulation + assessment).

        Returns:
            dict: preview payload::

                {
                    available (bool): True when summary or text is present
                    summary (str): apt summary line (None if missing)
                    text (str): preview text including assessment section
                    target_version (str): catalog target version (None if unknown)
                    log_path (str): dry-run log path
                    verdict (str): "ok" or "ko" (None if nothing to analyze)
                    findings (list): assessment findings
                    disk (dict): free/needed disk details
                    analysis (dict): full analyze_os_dry_run result
                }
        """
        preview_path = "/tmp/cleepos-playbook/dry-run-preview.txt"
        summary_path = "/tmp/cleepos-playbook/apt-summary.txt"
        simulate_path = "/tmp/cleepos-playbook/apt-simulate.log"
        text = None
        summary = None
        simulate_text = None
        if os.path.isfile(preview_path):
            try:
                with open(preview_path, encoding="utf8") as handle:
                    text = handle.read()
            except OSError:
                self.logger.warning("Unable to read dry-run preview", exc_info=True)
        if os.path.isfile(summary_path):
            try:
                with open(summary_path, encoding="utf8") as handle:
                    summary = handle.read().strip() or None
            except OSError:
                pass
        if os.path.isfile(simulate_path):
            try:
                with open(simulate_path, encoding="utf8") as handle:
                    simulate_text = handle.read()
            except OSError:
                self.logger.warning("Unable to read apt simulate log", exc_info=True)
        if self._os_dry_run_preview and not text:
            text = self._os_dry_run_preview.get("text")
            summary = summary or self._os_dry_run_preview.get("summary")
            simulate_text = simulate_text or self._os_dry_run_preview.get(
                "simulate_text"
            )

        analysis_source = simulate_text or text or summary or ""
        analysis = None
        if analysis_source:
            try:
                analysis = analyze_os_dry_run(analysis_source)
            except Exception:
                self.logger.warning("OS dry-run analysis failed", exc_info=True)
                analysis = {
                    "verdict": "ko",
                    "findings": [
                        {
                            "severity": "error",
                            "code": "analysis_failed",
                            "message": "Internal error while analyzing dry-run preview",
                        }
                    ],
                    "disk": {},
                    "counts": None,
                }

        display_text = text
        if analysis and text and "=== assessment ===" not in text:
            display_text = text.rstrip() + "\n\n" + format_analysis_section(analysis)
        elif analysis and not text and summary:
            display_text = "=== apt summary ===\n%s\n\n%s" % (
                summary,
                format_analysis_section(analysis),
            )

        cached = self._os_dry_run_preview or {}
        return {
            "available": bool(display_text or summary),
            "summary": summary,
            "text": display_text,
            "target_version": cached.get("target_version")
            or self._os_updates.get("version"),
            "log_path": OsUpgradeRunner.DRY_RUN_LOG_PATH,
            "verdict": (analysis or {}).get("verdict") or cached.get("verdict"),
            "findings": (analysis or {}).get("findings")
            or cached.get("findings")
            or [],
            "disk": (analysis or {}).get("disk") or cached.get("disk") or {},
            "analysis": analysis or cached.get("analysis"),
        }

    def _load_os_dry_run_preview(self):
        """Cache dry-run preview files into memory after a successful simulation."""
        payload = self.get_os_dry_run_preview()
        self._os_dry_run_preview = {
            "summary": payload.get("summary"),
            "text": payload.get("text"),
            "simulate_text": None,
            "target_version": self._os_updates.get("version"),
            "verdict": payload.get("verdict"),
            "findings": payload.get("findings") or [],
            "disk": payload.get("disk") or {},
            "analysis": payload.get("analysis"),
        }
        # Keep raw simulate log in memory if present (disk may be cleaned later)
        simulate_path = "/tmp/cleepos-playbook/apt-simulate.log"
        if os.path.isfile(simulate_path):
            try:
                with open(simulate_path, encoding="utf8") as handle:
                    self._os_dry_run_preview["simulate_text"] = handle.read()
            except OSError:
                pass
        return payload

    def _update_os_callback(self, status):
        """
        Callback from OsUpgradeRunner.

        Args:
            status (dict): runner status
        """
        runner_status = status.get("status")
        progress = status.get("progress") or 0
        phase = status.get("phase")
        dry_run = bool(status.get("dry_run") or self._os_upgrade_dry_run)
        error = status.get("error")
        log_path = status.get("log_path") or (
            OsUpgradeRunner.DRY_RUN_LOG_PATH if dry_run else OsUpgradeRunner.LOG_PATH
        )

        # Keep last known progress for UI restore after page reload
        self._os_updates.update(
            {
                "status": runner_status,
                "progress": progress,
                "phase": phase,
                "dry_run": dry_run,
                "processing": runner_status < OsUpgradeRunner.STATUS_SUCCESS,
                "error": error,
                "log_path": log_path,
            }
        )

        self.os_update_event.send(
            params={
                "status": runner_status,
                "progress": progress,
                "phase": phase,
                "dry_run": dry_run,
            }
        )

        if runner_status < OsUpgradeRunner.STATUS_SUCCESS:
            return

        self._release_update_lock()
        try:
            self.cleep_filesystem.disable_write(True, True)
        except Exception:
            self.logger.warning(
                "Unable to remount filesystem read-only after OS update",
                exc_info=True,
            )

        if runner_status == OsUpgradeRunner.STATUS_SUCCESS:
            if dry_run:
                self._load_os_dry_run_preview()
                self._os_updates.update(
                    {
                        "processing": False,
                        "pending": False,
                        "failed": False,
                        "dry_run": False,
                        "status": runner_status,
                        "progress": 100,
                        "error": None,
                    }
                )
                self._os_upgrade_dry_run = False
                self._finalize_os_last_attempt_from_callback(
                    status, dry_run=True, success=True
                )
                summary = (self._os_dry_run_preview or {}).get(
                    "summary"
                ) or "see preview"
                verdict = (self._os_dry_run_preview or {}).get("verdict") or "?"
                self.logger.info(
                    "OS update dry-run succeeded (%s, verdict=%s)",
                    summary,
                    verdict,
                )
                self._maybe_autosend_os_dry_run_report(
                    analysis=(self._os_dry_run_preview or {}).get("analysis"),
                    runner_error=None,
                    from_version=getattr(self, "_os_upgrade_from_version", None)
                    or self._os_updates.get("current"),
                    to_version=self._os_updates.get("version"),
                )
                return

            from_version = getattr(
                self, "_os_upgrade_from_version", None
            ) or self._os_updates.get("current")
            to_version = self._os_updates.get("version")
            self._maybe_build_os_conf_report(
                from_version=from_version,
                to_version=to_version,
                allow_autosend=True,
            )
            self._os_updates.update(
                {
                    "processing": False,
                    "pending": True,
                    "failed": False,
                    "updatable": False,
                    "dry_run": False,
                    "status": runner_status,
                    "progress": 100,
                    "error": None,
                    "current": self._os_updates.get("version"),
                    "reboot_needed": True,
                    "reboot_triggered": False,
                }
            )
            self._os_upgrade_dry_run = False
            self._finalize_os_last_attempt_from_callback(
                status,
                dry_run=False,
                success=True,
                reboot_needed=True,
                reboot_triggered=False,
            )
            self.logger.info(
                "OS update succeeded — device reboot recommended (toolbar button)"
            )
            # Device reboot (not Cleep restart) — packages need a full reboot
            self.device_need_reboot_event.send()
        else:
            self._os_updates.update(
                {
                    "processing": False,
                    "pending": False,
                    "failed": True,
                    "dry_run": False,
                    "status": runner_status,
                    "error": error,
                    "log_path": log_path,
                }
            )
            self._os_upgrade_dry_run = False
            self._finalize_os_last_attempt_from_callback(
                status, dry_run=dry_run, success=False
            )
            self._log_os_upgrade_failure(status, dry_run=dry_run, log_path=log_path)
            if dry_run:
                self._maybe_autosend_os_dry_run_report(
                    analysis=None,
                    runner_error=error,
                    from_version=getattr(self, "_os_upgrade_from_version", None)
                    or self._os_updates.get("current"),
                    to_version=self._os_updates.get("version"),
                )

    def _maybe_autosend_os_dry_run_report(
        self, *, analysis, runner_error, from_version, to_version
    ):
        """
        Send dry-run assessment or playbook failure to Sentry when report auto-send is enabled.

        User-side disk space KO is logged locally but not reported as a product error.
        """
        if not self._get_config_field("osconfreportenabled"):
            return
        if not self._get_config_field("osconfreportautosend"):
            return
        if not self.crash_report or not self.crash_report.is_enabled():
            return

        reportable = dry_run_errors_reportable_to_sentry(analysis)
        if runner_error:
            pass
        elif not analysis or (analysis.get("verdict") != "ko" and not reportable):
            return
        elif not reportable and analysis.get("verdict") == "ko":
            self.logger.info(
                "OS dry-run KO due to user disk space only — not sending to Sentry "
                "(%s → %s)",
                from_version,
                to_version,
            )
            return

        try:
            extra = sentry_extra_from_dry_run_analysis(
                analysis,
                from_version=from_version,
                to_version=to_version,
                runner_error=runner_error,
            )
            if runner_error:
                message = "CleepOs upgrade dry-run playbook failed (%s → %s)" % (
                    from_version or "?",
                    to_version or "?",
                )
            else:
                message = "CleepOs upgrade dry-run assessment KO (%s → %s)" % (
                    from_version or "?",
                    to_version or "?",
                )
            self.crash_report.manual_report(message, extra=extra)
            self.logger.info("OS dry-run report sent to Sentry")
        except Exception:  # pragma: no cover
            self.logger.exception("Unable to send OS dry-run report to Sentry")

    def _log_os_upgrade_failure(self, status, *, dry_run, log_path):
        """Log playbook failure with phase, error and trailing output."""
        phase = status.get("phase")
        error = status.get("error") or "unknown error"
        mode = "dry-run" if dry_run else "apply"
        self.logger.error(
            "OS update %s failed (phase=%s): %s — details in %s",
            mode,
            phase or "?",
            error,
            log_path,
        )
        # Prefer playbook fail lines from stdout (apt is tee'd there)
        stdout = status.get("stdout") or []
        stderr = status.get("stderr") or []
        interesting = [
            line
            for line in stdout
            if "fail" in line.lower()
            or line.startswith("ERR:")
            or "[cleepos-playbook]" in line
        ]
        if not interesting:
            interesting = stdout[-40:]
        for line in interesting[-40:]:
            self.logger.error("OS playbook: %s", line)
        for line in stderr[-20:]:
            self.logger.error("OS playbook stderr: %s", line)

    def _maybe_build_os_conf_report(
        self, *, from_version=None, to_version=None, allow_autosend=False
    ):
        """Generate path-only conf leftover report when the option is enabled."""
        if not self._get_config_field("osconfreportenabled"):
            return None
        try:
            report = build_os_conf_report(
                from_version=from_version,
                to_version=to_version,
                report_path=DEFAULT_REPORT_PATH,
            )
            summary = {
                "generated_at": report["generated_at"],
                "from_version": report.get("from_version"),
                "to_version": report.get("to_version"),
                "leftover_count": report.get("leftover_count", 0),
                "leftover_paths": report.get("leftover_paths") or [],
                "apt_conf_actions": report.get("apt_conf_actions") or [],
                "high_interest": report.get("high_interest") or [],
                "report_path": report.get("report_path"),
                "sent": False,
                "sent_at": None,
            }
            self._set_config_field("osconfreport", summary)
            self.logger.info(
                "OS conf report ready: %s leftover(s)",
                summary["leftover_count"],
            )
            if allow_autosend and self._get_config_field("osconfreportautosend"):
                try:
                    self._send_os_conf_report_to_sentry(report)
                except Exception as error:
                    self.logger.warning(
                        "Auto-send OS conf report to Sentry failed: %s",
                        error,
                    )
            return report
        except Exception:
            self.logger.exception("Unable to build OS conf leftover report")
            return None

    def set_os_conf_report_options(self, enabled, autosend):
        """
        Enable or disable OS conf leftover reporting and optional auto-send to Sentry.

        Args:
            enabled (bool): generate and show report after OS upgrade
            autosend (bool): send report to Sentry automatically after generation

        Returns:
            dict: saved options::

                {
                    osconfreportenabled (bool): reporting enabled
                    osconfreportautosend (bool): auto-send enabled
                }

        Raises:
            InvalidParameter: if enabled or autosend is not a boolean
        """
        if not isinstance(enabled, bool):
            raise InvalidParameter('Parameter "enabled" is invalid')
        if not isinstance(autosend, bool):
            raise InvalidParameter('Parameter "autosend" is invalid')
        if autosend and not enabled:
            # Auto-send only makes sense when reporting is enabled
            autosend = False
        self._update_config(
            {
                "osconfreportenabled": enabled,
                "osconfreportautosend": autosend,
            }
        )
        return {
            "osconfreportenabled": enabled,
            "osconfreportautosend": autosend,
        }

    def get_os_conf_report(self):
        """
        Return last OS conf leftover report (paths and apt action lines only).

        Returns:
            dict: report options and content::

                {
                    enabled (bool): reporting option enabled
                    autosend (bool): auto-send option enabled
                    report (dict): summary fields plus text (None if no report yet)
                }
        """
        enabled = bool(self._get_config_field("osconfreportenabled"))
        autosend = bool(self._get_config_field("osconfreportautosend"))
        summary = self._get_config_field("osconfreport")
        report = None
        if isinstance(summary, dict):
            report = dict(summary)
            text = ""
            path = summary.get("report_path") or DEFAULT_REPORT_PATH
            try:
                with open(path, "r", encoding="utf8") as handle:
                    text = handle.read()
            except OSError:
                text = ""
            report["text"] = text
        return {
            "enabled": enabled,
            "autosend": autosend,
            "report": report,
        }

    def generate_os_conf_report(self):
        """
        Manually rescan the filesystem and refresh the OS conf leftover report.

        Requires reporting to be enabled in Options.

        Returns:
            dict: report options and content::

                {
                    enabled (bool): reporting option enabled
                    autosend (bool): auto-send option enabled
                    report (dict): summary fields plus text (None if no report yet)
                }

        Raises:
            CommandInfo: if reporting is disabled
            CommandError: if report generation fails
        """
        if not self._get_config_field("osconfreportenabled"):
            raise CommandInfo(
                "OS conf reporting is disabled. Enable it in Options first."
            )
        from_version = None
        summary = self._get_config_field("osconfreport")
        if isinstance(summary, dict):
            from_version = summary.get("from_version")
        to_version = None
        try:
            to_version = get_os_identity().get("version")
        except ValueError:
            pass
        report = self._maybe_build_os_conf_report(
            from_version=from_version,
            to_version=to_version,
            allow_autosend=False,
        )
        if not report:
            raise CommandError("Unable to generate OS conf report")
        return self.get_os_conf_report()

    def send_os_conf_report(self):
        """
        Send the last OS conf leftover report to Sentry (paths only, no file contents).

        Returns:
            dict: report options and content after send metadata update::

                {
                    enabled (bool): reporting option enabled
                    autosend (bool): auto-send option enabled
                    report (dict): summary fields plus text (None if no report yet)
                }

        Raises:
            CommandInfo: if reporting is disabled or no report is available
            CommandError: if sending fails
        """
        if not self._get_config_field("osconfreportenabled"):
            raise CommandInfo(
                "OS conf reporting is disabled. Enable it in Options first."
            )
        summary = self._get_config_field("osconfreport")
        if not isinstance(summary, dict) or not summary.get("generated_at"):
            raise CommandInfo(
                "No OS conf report available. Run an OS update or refresh."
            )
        path = summary.get("report_path") or DEFAULT_REPORT_PATH
        text = ""
        try:
            with open(path, "r", encoding="utf8") as handle:
                text = handle.read()
        except OSError as error:
            raise CommandError("OS conf report file is missing") from error
        report = dict(summary)
        report["text"] = text
        self._send_os_conf_report_to_sentry(report)
        return self.get_os_conf_report()

    def _send_os_conf_report_to_sentry(self, report):
        """Push path-only leftover inventory to Sentry via crash_report."""
        if not self.crash_report or not self.crash_report.is_enabled():
            raise CommandInfo("Crash report / Sentry is disabled on this device")
        extra = sentry_extra_from_report(report)
        message = "CleepOs upgrade conf leftovers (%s → %s, %s path(s))" % (
            report.get("from_version") or "?",
            report.get("to_version") or "?",
            report.get("leftover_count") or 0,
        )
        self.crash_report.manual_report(message, extra=extra)
        summary = self._get_config_field("osconfreport")
        if isinstance(summary, dict):
            summary = dict(summary)
            summary["sent"] = True
            summary["sent_at"] = int(time.time())
            self._set_config_field("osconfreport", summary)
        self.logger.info(
            "OS conf report sent to Sentry (%s leftovers)", extra.get("leftover_count")
        )

    def _get_installed_modules_names(self):
        """
        Return installed modules names

        Returns:
            list: list of modules names
        """
        # modules updates dict can contains module that are installing,
        # but there are not yet so we must filter them
        return [
            module["name"]
            for module in self._modules_updates.values()
            if module["version"] is not None
        ]

    def __start_actions_tasks(self):
        """
        Start actions tasks.

        Tasks are not started if there are already running.
        Main actions and sub actions tasks are correlated, start them at the same time.
        """
        self._acquire_update_lock()

        # main actions task
        if not self.__main_actions_task:
            self.logger.debug("Start main actions task")
            self.__main_actions_task = self.task_factory.create_task(
                Update.MAIN_ACTIONS_TASK_INTERVAL,
                self._execute_main_action_task,
            )
            self.__main_actions_task.start()

        # sub actions task
        if not self.__sub_actions_task:
            self.logger.debug("Start sub actions task")
            self.__sub_actions_task = self.task_factory.create_task(
                Update.SUB_ACTIONS_TASK_INTERVAL,
                self._execute_sub_actions_task,
            )
            self.__sub_actions_task.start()

    def __stop_actions_tasks(self):
        """
        Stop actions tasks.
        """
        had_actions_tasks = bool(self.__main_actions_task or self.__sub_actions_task)

        if self.__main_actions_task:
            self.logger.debug("Stop main actions task")
            self.__main_actions_task.stop()
            self.__main_actions_task = None

        if self.__sub_actions_task:
            self.logger.debug("Stop sub actions task")
            self.__sub_actions_task.stop()
            self.__sub_actions_task = None

        # Only release when this path held the lock for module actions.
        # Cleep updates acquire/release the lock independently.
        if had_actions_tasks:
            self._release_update_lock()

    def _execute_main_action_task(self):
        """
        Function triggered regularly to process main actions (only one running at a time)
        """
        action = {}
        try:
            self.logger.debug(
                "Main actions in progress: %s (sub actions: %s)",
                len(self.__main_actions),
                len(self.__sub_actions),
            )

            # check if action is already processing
            if len(self.__sub_actions) != 0 or self.__processor:
                self.logger.debug(
                    "Main action is processing, stop main action task here."
                )
                return

            # remove previous action if necessary
            if (
                len(self.__main_actions) > 0
                and self.__main_actions[len(self.__main_actions) - 1]["processing"]
            ):
                self.__main_actions.pop()

            # is there main action to run ?
            if (
                len(self.__main_actions) == 0
                and len(self.__sub_actions) == 0
                and not self.__processor
            ):
                self.logger.debug("No more main action to execute, stop all tasks.")

                # send need restart event
                if self._need_restart:
                    self.cleep_need_restart_event.send()
                    self._need_restart = False

                self.__stop_actions_tasks()
                return

            # compute sub actions
            action = self.__main_actions[len(self.__main_actions) - 1]
            self.logger.debug("Processing action %s", action)
            action["processing"] = True
            if action["action"] == Update.ACTION_MODULE_INSTALL:
                self._install_main_module(action["module"], action["extra"])
            elif action["action"] == Update.ACTION_MODULE_UNINSTALL:
                self._uninstall_main_module(action["module"], action["extra"])
            elif action["action"] == Update.ACTION_MODULE_UPDATE:
                self._update_main_module(action["module"])

            # if no action postponed it means process can be terminated here
            self.logger.debug("%d sub actions postponed", len(self.__sub_actions))
            if len(self.__sub_actions) == 0:
                self.logger.debug(
                    "Stop current action here because no subaction to execute"
                )
                # _postpone_main_action set processing=True; clear it when there
                # is nothing to run (uninstall "library only" already cleared it).
                module_name = action.get("module")
                module_update = self._modules_updates.get(module_name)
                if module_update and module_update["processing"]:
                    module_update["processing"] = False
                    module_update["update"]["progress"] = 100
                    params = {
                        "module": module_name,
                        "status": Install.STATUS_DONE,
                    }
                    if action["action"] == Update.ACTION_MODULE_INSTALL:
                        self.module_install_event.send(params)
                    elif action["action"] == Update.ACTION_MODULE_UNINSTALL:
                        self.module_uninstall_event.send(params)
                    elif action["action"] == Update.ACTION_MODULE_UPDATE:
                        self.module_update_event.send(params)
                return

            # update main action and module infos
            action["processing"] = True
            self._set_module_process(progress=0)

            # update progress step for all sub actions
            # this is done after all sub actions are stored to compute valid progress step
            # remainder goes on index 0 (executed last: insert(0)+pop) so total reaches 100
            n_sub_actions = len(self.__sub_actions)
            progress_step = 100 // n_sub_actions
            progress_remainder = 100 % n_sub_actions
            for i, sub_action in enumerate(self.__sub_actions):
                sub_action["progressstep"] = progress_step + (
                    progress_remainder if i == 0 else 0
                )

        except Exception as error:
            self.logger.exception("Error occured executing action: %s", action)
            if action:
                self._set_module_process(
                    failed=True, forced_module_name=action["module"]
                )
                # store action error
                self._store_process_status(
                    status={"module": action["module"], "error": str(error)},
                    success=False,
                )

                # and send error event
                params = {"module": action["module"], "status": Install.STATUS_ERROR}
                if action["action"] == Update.ACTION_MODULE_INSTALL:
                    self.module_install_event.send(params)
                elif action["action"] == Update.ACTION_MODULE_UNINSTALL:
                    self.module_uninstall_event.send(params)
                elif action["action"] == Update.ACTION_MODULE_UPDATE:
                    self.module_update_event.send(params)

    def _execute_sub_actions_task(self):
        """
        Function triggered regularly to perform sub actions
        """
        self.logger.debug("Executing sub action")
        # check if sub action is being processed
        if self.__processor:
            self.logger.trace("Sub action is processing, stop sub action task here")
            return

        # return if no sub action in pipe
        if len(self.__sub_actions) == 0:
            self.logger.debug(
                "No more sub actions to process, stop sub action task here"
            )
            return

        # no running sub action, run next one
        sub_action = self.__sub_actions.pop()
        self.logger.debug("Poped sub action: %s", sub_action)

        # is last sub actions execution failed ?
        if self._is_module_process_failed():
            self.logger.debug(
                'One of previous sub action failed during "%s" module process, stop here',
                sub_action["main"],
            )
            return

        # update module process progress
        self._set_module_process(inc_progress=sub_action["progressstep"])

        # launch sub action
        if sub_action["action"] == Update.ACTION_MODULE_INSTALL:
            extra = sub_action.get("extra", {}) or {}
            extra["isdependency"] = sub_action["module"] != sub_action["main"]
            self._install_module(sub_action["module"], sub_action["infos"], extra)
        elif sub_action["action"] == Update.ACTION_MODULE_UNINSTALL:
            self._uninstall_module(
                sub_action["module"], sub_action["infos"], sub_action.get("extra")
            )
        elif sub_action["action"] == Update.ACTION_MODULE_UPDATE:
            self._update_module(sub_action["module"], sub_action["infos"])

    def _get_processing_module_name(self):
        """
        Return processing module name

        Returns:
            string: processing module name or None if no module is processing
        """
        if len(self.__main_actions) == 0:
            return None

        action = self.__main_actions[len(self.__main_actions) - 1]
        return action["module"] if action["processing"] else None

    def _set_module_process(
        self,
        progress=None,
        inc_progress=None,
        failed=None,
        pending=None,
        forced_module_name=None,
    ):
        """
        Set module process infos. Nothing is updated if no module is processing.

        Args:
            progress (int): set progress value to specified value (0-100)
            inc_progress (int): increase progress value with specified value
            failed (bool): action process failed if set to False
            pending (bool): True if module action termined successfully and module needs to be restarted
            forced_module_name (string): Force module name instead of getting it from currently processing one
        """
        # get processing module name
        module_name = (
            forced_module_name
            if forced_module_name is not None
            else self._get_processing_module_name()
        )
        if not module_name:
            self.logger.debug("Can't update module infos when no module is processing")
            return
        self.logger.debug(
            "set_module_process [%s]: progress=%s inc_progress=%s failed=%s pending=%s forced_module_name=%s",
            module_name,
            progress,
            inc_progress,
            failed,
            pending,
            forced_module_name,
        )

        # make sure entry exists in modules updates (case when installing new module)
        if module_name not in self._modules_updates:
            module_infos = self._get_module_infos_from_market(module_name)
            new_module_version = module_infos["version"] if module_infos else "0.0.0"
            self._modules_updates[module_name] = self.__get_module_update_data(
                module_name, None, new_module_version
            )

        # get module
        module = self._modules_updates[module_name]

        # handle process flags
        module["processing"] = True
        if progress is not None:
            module["update"]["progress"] = progress
        elif inc_progress is not None:
            module["update"]["progress"] += inc_progress
        if module["update"]["progress"] > 100:
            module["update"]["progress"] = 100
            module["processing"] = False
        if failed is not None:
            module["update"]["failed"] = failed
            module["update"]["progress"] = 100
            module["processing"] = False
        if pending is not None:
            module["pending"] = pending
            module["processing"] = not pending

    def _is_module_process_failed(self):
        """
        Return True if module process failed

        Returns:
            bool: True if module process failed
        """
        module_name = self._get_processing_module_name()
        if not module_name:
            self.logger.debug("Can't get process status while no module is processing")
            return True

        return self._modules_updates[module_name]["update"]["failed"]

    def _fill_modules_updates(self):
        """
        Get modules from inventory and fill useful data for updates.
        Note that only installed modules are used to fill dict

        Notes:
            modules_updates format:

                {
                    module name (string): dict returned by __get_module_update_data
                    ...
                }

        Raises:
            Exception if send command failed
        """
        # retrieve modules from inventory
        resp = self.send_command("get_modules", "inventory", timeout=20)
        if resp.error:
            raise Exception("Unable to get modules list from inventory")

        # save modules
        modules = {}
        installed_modules = {k: v for (k, v) in resp.data.items() if v["installed"]}
        for module_name, module in installed_modules.items():
            modules[module_name] = self.__get_module_update_data(
                module_name, module.get("version", "0.0.0")
            )
        self._modules_updates = modules

    def __get_module_update_data(
        self, module_name, installed_module_version, new_module_version=None
    ):
        """
        Get module update data

        Args:
            module_name (string): module name
            installed_module_version (string): installed module version
            new_module_version (string): new module version after update

        Returns:
            dict: module update data::

                {
                    updatable (bool): True if module is updatable
                    processing (bool): True if module has action in progress
                    pending (bool): True if module has been updated/uninstalled/installed
                    name (string): module name
                    version (string): installed module version, None if module is not installed yet
                    update (dict): update data::

                        {
                            progress (int): progress percentage (0-100)
                            failed (bool): True if process has failed
                            version (string): update version
                            changelog (string): update changelog
                        }

                }

        """
        return {
            "updatable": False,
            "processing": False,
            "pending": False,
            "name": module_name,
            "version": installed_module_version,
            "update": {
                "progress": 0,
                "failed": False,
                "version": new_module_version,
                "changelog": None,
            },
        }

    def __reset_module_update_data(self, module_name):
        """
        Reset module update data in _modules_updates dict.
        It reset some flags (processing, progress...) to make sure current action can be performed correctly

        Args:
            module_name (string): module name
        """
        if module_name not in self._modules_updates:
            return

        self._modules_updates[module_name]["processing"] = False
        self._modules_updates[module_name]["update"]["progress"] = 0
        self._modules_updates[module_name]["update"]["failed"] = False

    def _restart_cleep(self, delay=10.0):
        """
        Restart cleep sending command to system module

        Args:
            delay (float): delay before restarting (default 10.0 seconds)
        """
        self.logger.info("Restart Cleep in %s seconds)", delay)
        resp = self.send_command("restart_cleep", "system", {"delay": delay})
        if resp.error:
            self.logger.error("Unable to restart Cleep")

    def check_cleep_updates(self):
        """
        Check for available cleep updates

        Notes:
            If GITHUB_TOKEN is referenced in env vars, it will also check pre-releases

        Returns:
            dict: last update infos::

                {
                    version (string): latest update version
                    changelog (string): latest update changelog
                    packageurl (string): latest update package url
                    checksumurl (string): latest update checksum url
                }

        """
        update = copy.deepcopy(self._cleep_updates)

        try:
            # get beta release if GITHUB_TOKEN env variable registered
            auth_string = None
            only_released = True
            if "GITHUB_TOKEN" in os.environ:
                auth_string = f'token {os.environ["GITHUB_TOKEN"]}'
                only_released = False  # used to get beta release

            github = CleepGithub(auth_string)
            releases = github.get_releases(
                self.CLEEP_GITHUB_OWNER,
                self.CLEEP_GITHUB_REPO,
                only_latest=True,
                only_released=only_released,
            )
            if len(releases) > 0:
                # get latest version available
                latest_version = github.get_release_version(releases[0])
                latest_changelog = github.get_release_changelog(releases[0])
                self.logger.debug(
                    "Found latest update: %s - %s", latest_version, latest_changelog
                )

                self.logger.info(
                    "Cleep version status: latest %s - installed %s",
                    latest_version,
                    CLEEP_VERSION,
                )
                if Tools.compare_versions(CLEEP_VERSION, latest_version):
                    # new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])
                    self.logger.trace("assets: %s", assets)

                    # search for deb file
                    package_asset = None
                    for asset in assets:
                        if asset["name"].startswith("cleep_") and asset[
                            "name"
                        ].endswith(".deb"):
                            self.logger.debug("Found Cleep package asset: %s", asset)
                            package_asset = asset
                            update["packageurl"] = asset["url"]
                            break

                    # search for checksum file
                    if package_asset:
                        package_name = os.path.splitext(package_asset["name"])[0]
                        checksum_name = f"{package_name}.sha256"
                        self.logger.debug(
                            "Checksum filename to search: %s", checksum_name
                        )
                        for asset in assets:
                            if asset["name"] == checksum_name:
                                self.logger.debug("Found checksum asset: %s", asset)
                                update["checksumurl"] = asset["url"]
                                break

                    if update["packageurl"] and update["checksumurl"]:
                        update["updatable"] = True
                        update["version"] = latest_version
                        update["changelog"] = latest_changelog
                    else:
                        self.logger.warning(
                            "Cleep update is available but is was impossible to retrieve all needed data"
                        )
                        update["packageurl"] = None
                        update["checksumurl"] = None

                else:
                    # already up-to-date
                    self.logger.info("Cleep is already up-to-date")

            else:
                # no release found
                self.logger.warning("No Cleep release found during check")

        except Exception as error:
            self.logger.exception("Error occured during updates checking:")
            self.crash_report.report_exception()
            raise CommandError("Error occured during cleep update check") from error

        # update config
        self._set_config_field("cleeplastcheck", int(time.time()))
        self._cleep_updates = update

        return self._cleep_updates

    def check_modules_updates(self):
        """
        Check for modules updates.

        Returns:
            dict: last modules update infos::

                {
                    modulesupdates (bool): True if at least one module has an update
                    moduleslastcheck (int): last modules update check timestamp
                    marketupdated (bool): True if market updated (front needs to force modules update)
                }

        """
        # update market
        try:
            market_updated = self.apps_sources.update_market()
            new_market = self.apps_sources.get_market()
        except Exception as error:
            self.logger.exception("Unable to update market")
            raise CommandError("Unable to update market") from error

        update_available = False
        # request inventory to update its modules list
        resp = self.send_command("reload_modules", "inventory")
        if resp.error:
            self.logger.error(
                "Error occured during inventory modules reloading: %s", resp.message
            )

        # check for modules updates available
        for module_name, module in self._modules_updates.items():
            try:
                new_version = (
                    new_market["list"][module_name]["version"]
                    if module_name in new_market["list"]
                    else "0.0.0"
                )
                if Tools.compare_versions(module["version"], new_version):
                    # new version available for current module
                    update_available = True
                    module["updatable"] = True
                    module["update"].update(
                        {
                            "version": new_version,
                            "changelog": new_market["list"][module_name]["changelog"],
                        }
                    )
                    self.logger.info(
                        'New version available for app "%s" (v%s => v%s)',
                        module_name,
                        module["version"],
                        new_version,
                    )
                else:
                    # force module infos update in case of version revert in modules.json
                    module["updatable"] = False
                    module["update"].update(
                        {
                            "version": module["version"],
                            "changelog": "",
                        }
                    )
                    self.logger.debug(
                        'No new version available for app "%s" (v%s => v%s)',
                        module_name,
                        module["version"],
                        new_version,
                    )

            except Exception:
                self.logger.exception('Invalid "%s" app infos from market', module_name)

        # update config
        config = {
            "modulesupdates": update_available,
            "moduleslastcheck": int(time.time()),
        }
        self._update_config(config)

        return {
            "modulesupdates": update_available,
            "marketupdated": market_updated,
            "moduleslastcheck": config["moduleslastcheck"],
        }

    def _update_cleep_callback(self, status):
        """
        Cleep update callback

        Args:
            status (dict): update status
        """
        self.logger.debug("Cleep update callback status: %s", status)

        # send process status (status + coarse progress from InstallCleep phases)
        self.cleep_update_event.send(
            params={
                "status": status["status"],
                "progress": status.get("progress", 0),
            }
        )

        # store final status when update terminated (successfully or not)
        if status["status"] >= InstallCleep.STATUS_UPDATED:
            # lock filesystem
            self.cleep_filesystem.disable_write(True, True)
            self._release_update_lock()

        # handle end of cleep update
        if status["status"] == InstallCleep.STATUS_UPDATED:
            # update successful
            self.logger.info("Cleep update installed successfully. Restart now")
            self._store_process_status(status, success=True)

            # reset cleep update
            self._cleep_updates.update(
                {
                    "updatable": False,
                    "processing": False,
                    "pending": True,
                    "failed": False,
                    "version": None,
                    "changelog": None,
                    "packageurl": None,
                    "checksumurl": None,
                }
            )

            # restart cleep
            self._restart_cleep()

        elif status["status"] > InstallCleep.STATUS_UPDATED:
            # error occured
            self._store_process_status(status, success=False)
            self.logger.error("Cleep update failed. Please check process outpout")

            # reset cleep update
            self._cleep_updates.update(
                {
                    "processing": False,
                    "pending": False,
                    "failed": True,
                }
            )

    def update_cleep(self):
        """
        Update Cleep installing debian package
        """
        # check
        if not self._cleep_updates["updatable"]:
            raise CommandInfo(
                "No Cleep update available, please launch update check first"
            )
        if len(self.__main_actions) != 0:
            raise CommandInfo(
                "Applications updates are in progress. Please wait for end of it"
            )
        self._assert_os_allows_cleep_update()
        if self._os_updates.get("processing"):
            raise CommandInfo("OS update is in progress. Please wait for end of it")
        self._check_cleep_update_disk_space()

        self._acquire_update_lock()

        try:
            # unlock filesystem
            self.cleep_filesystem.enable_write(True, True)

            # reset flags
            self._cleep_updates.update(
                {
                    "failed": False,
                    "pending": False,
                    "processing": True,
                }
            )

            # launch update
            package_url = self._cleep_updates["packageurl"]
            checksum_url = self._cleep_updates["checksumurl"]
            self.logger.debug(
                "Update Cleep: package_url=%s checksum_url=%s",
                package_url,
                checksum_url,
            )
            update = InstallCleep(
                self.cleep_filesystem, self.crash_report, self.task_factory
            )
            update.install(package_url, checksum_url, self._update_cleep_callback)
        except Exception:
            self._release_update_lock()
            raise

    def _check_cleep_update_disk_space(self):
        """
        Ensure enough free disk space before downloading/installing Cleep package.

        Raises:
            CommandInfo: if free space is below CLEEP_UPDATE_MIN_FREE_BYTES
        """
        try:
            usage = shutil.disk_usage("/")
        except OSError as error:
            self.logger.warning("Unable to check disk space: %s", error)
            return

        if usage.free < self.CLEEP_UPDATE_MIN_FREE_BYTES:
            needed_mb = self.CLEEP_UPDATE_MIN_FREE_BYTES // (1024 * 1024)
            free_mb = usage.free // (1024 * 1024)
            raise CommandInfo(
                f"Not enough free disk space to update Cleep "
                f"(need at least {needed_mb} MB, only {free_mb} MB available)"
            )

    def update_modules(self):
        """
        Update modules that can be updated. It consists of processing postponed main actions filled
        during module updates check.
        """
        if self._cleep_updates["processing"] or self._cleep_updates["pending"]:
            raise CommandInfo("Cleep update is in progress. Please wait for end of it")

        # fill main actions with upgradable modules
        self._acquire_update_lock()
        for module in [
            module
            for module in self._modules_updates.values()
            if module["updatable"]
            and not module["processing"]
            and not module["pending"]
        ]:
            self._postpone_main_action(Update.ACTION_MODULE_UPDATE, module["name"])

        # start main actions task
        self.__start_actions_tasks()

    def _postpone_main_action(self, action, module_name, extra=None):
        """
        Postpone main action (module install/update/uninstall) in a FIFO list.

        Args:
            action (string): action name (see ACTION_XXX constants)
            module_name (string): module name concerned by action
            extra (any): extra data to send to action

        Returns:
            bool: True if new action postponed, False if action was already postponed
        """
        # search if similar action for same module already exists
        existing_actions = [
            action_obj
            for action_obj in self.__main_actions
            if action_obj["module"] == module_name and action_obj["action"] == action
        ]
        self.logger.trace("Existing_actions: %s", existing_actions)
        if len(existing_actions) > 0:
            self.logger.debug(
                'Same action "%s" for "%s" module already exists, drop it',
                action,
                module_name,
            )
            return False

        self.logger.trace(
            'Postpone main action "%s" for module "%s" (extra: %s)',
            action,
            module_name,
            extra,
        )
        # set module is processing
        self._set_module_process(forced_module_name=module_name)

        # store main action
        self.__main_actions.insert(
            0,
            {
                "action": action,
                "module": module_name,
                "extra": extra,
                "processing": False,
            },
        )

        # send event before it really starts to warn api clients
        params = {
            "status": Install.STATUS_PROCESSING,
            "module": module_name,
        }
        if action == self.ACTION_MODULE_INSTALL:
            self.module_install_event.send(params)
        elif action == self.ACTION_MODULE_UNINSTALL:
            self.module_uninstall_event.send(params)
        elif action == self.ACTION_MODULE_UPDATE:
            self.module_update_event.send(params)

        return True

    def _postpone_sub_action(
        self, action, module_name, module_infos, main_module_name, extra=None
    ):
        """
        Postpone sub action (module install/update/uninstall) in a stand alone list.

        Args:
            action (string): action name (see ACTION_XXX constants)
            module_name (string): module name concerned by action
            module_infos (dict): module informations
            main_module_name (string): main module name
            extra (any): any extra data
        """
        self.__sub_actions.insert(
            0,
            {
                "action": action,
                "module": module_name,
                "main": main_module_name,
                "infos": module_infos,
                "extra": extra,
                "progressstep": None,  # will be set after all sub actions are computed
            },
        )

    def set_automatic_update(self, cleep_update_enabled, modules_update_enabled):
        """
        Set automatic update values

        Args:
            cleep_update_enabled (bool): enable cleep automatic update
            modules_update_enabled (bool): enable modules automatic update

        Returns:
            dict: update flags::

                {
                    cleepupdateenabled (bool): True if cleep update enabled
                    modulesupdateenabled (bool): True if module update enabled
                }

        """
        if not isinstance(cleep_update_enabled, bool):
            raise InvalidParameter('Parameter "cleep_update_enabled" is invalid')
        if not isinstance(modules_update_enabled, bool):
            raise InvalidParameter('Parameter "modules_update_enabled" is invalid')

        # Action tasks are shared with manual install/update/uninstall.
        # When disabling modules auto-update, stop them properly (null refs)
        # so a later __start_actions_tasks can recreate them.
        if not modules_update_enabled:
            self.__stop_actions_tasks()

        return self._update_config(
            {
                "cleepupdateenabled": cleep_update_enabled,
                "modulesupdateenabled": modules_update_enabled,
            }
        )

    def _get_module_infos_from_package(self, module_name):
        """
        Return module infos from local package

        Args:
            module_name (string): module name

        Returns:
            dict: module infos

        Raises:
            Exception if market is invalid
        """
        package_path = self.PACKAGE_BASE_PATH % {"module_name": module_name}
        if not os.path.exists(package_path):
            raise Exception(
                f'Package "{package_path}" for app "{module_name}" does not exists'
            )

        package_dir = tempfile.mkdtemp()
        try:
            try:
                with ZipFile(package_path) as archive:
                    archive.extract("module.json", path=package_dir)
            except Exception as error:
                raise Exception(
                    f'Package "{package_path}" is not a valid application archive'
                ) from error

            try:
                with open(
                    os.path.join(package_dir, "module.json"), encoding="utf8"
                ) as file_obj:
                    return json.load(file_obj)
            except Exception as error:
                raise Exception(
                    f'Package "{package_path}" has invalid content'
                ) from error
        finally:
            shutil.rmtree(package_dir, ignore_errors=True)

    def _cleanup_module_package(self, module_name):
        """
        Remove local package copy under PACKAGE_BASE_PATH if it exists.

        Args:
            module_name (string): module name
        """
        package_path = self.PACKAGE_BASE_PATH % {"module_name": module_name}
        try:
            if os.path.exists(package_path):
                os.remove(package_path)
                self.logger.debug('Removed local package "%s"', package_path)
        except OSError:
            self.logger.warning(
                'Unable to remove local package "%s"', package_path, exc_info=True
            )

    def _get_module_infos_from_market(self, module_name):
        """
        Return application infos from market

        Args:
            module_name (string): module name

        Returns:
            dict: module infos or None if module not found

        Raises:
            Exception if market is invalid
        """
        market = self.apps_sources.get_market()
        if module_name in market["list"]:
            return market["list"][module_name]

        return None

    def _get_module_infos_from_inventory(self, module_name):
        """
        Return module infos from market

        Args:
            module_name (string): module name

        Returns:
            dict: module infos

        Raises:
            Exception if unknown module or error
        """
        # get infos from inventory
        resp = self.send_command(
            "get_module_infos", "inventory", {"module_name": module_name}
        )
        if resp.error:
            self.logger.error(
                'Unable to get app "%s" infos: %s', module_name, resp.message
            )
            raise Exception(f'Unable to get app "{module_name}" infos')
        if not resp.data:
            self.logger.error('App "%s" not found in apps list', module_name)
            raise Exception(f'App "{module_name}" not found in installable apps list')

        return resp.data

    def __extract_compat(self, compat_str):
        """
        Extract parts from compat string

        Args:
            compat_str (string): compat string

        Returns:
            dict: compat string parts::

                {
                    module_name (string)
                    operator (string)
                    version (string)
                }

        """
        try:
            match = re.search(self.compat_pattern, compat_str)
            module_name = match.group(1)
            operator = match.group(2)
            version = match.group(3)
            return {
                "module_name": module_name,
                "operator": operator,
                "version": version,
            }
        except Exception as error:
            self.logger.debug("Exception occured during compat parsing: %s", str(error))
            return {
                "module_name": None,
                "operator": None,
                "version": None,
            }

    def __check_dependencies_compatibility(
        self,
        module_name,
        dependencies,
        modules_infos_json,
        no_compatibility_check=False,
    ):
        """
        Check dependencies compatibility

        Args:
            module_name (string): main module name
            dependencies (list): list of dependencies
            modules_infos_json (dict): modules informations
            no_compatibility_check (bool): do not check module compatibility but only its dependencies compats

        Raises:
            Exception if one of dependencies if not compatible. It should breaks installation
        """
        for dependency in dependencies:
            self.logger.info("Checking app %s compatibility", dependency)
            if no_compatibility_check and dependency == module_name:
                self.logger.info(" -> Main app dependency check disabled")
                continue
            module_infos = modules_infos_json.get(dependency) or {}
            compat_str = module_infos.get("compat", f"cleep<={CLEEP_VERSION}")
            compat = self.__extract_compat(compat_str)
            self.logger.info(
                ' -> Checking compatibility for "%s" app: %s', dependency, compat
            )
            if any(val is None for val in compat.values()):
                raise Exception(f'Invalid compat string for "{dependency}" application')
            if compat["module_name"].lower() != "cleep":
                raise Exception(
                    f'Invalid compat string (invalid app name) for "{dependency}" application'
                )
            if compat["operator"] not in ("<", "=", "<="):
                raise Exception(
                    f'Invalid compat string (invalid operator) for "{dependency}" application'
                )

            compare_strict = compat["operator"] == "<"
            if (compat["operator"] == "=" and CLEEP_VERSION != compat["version"]) or (
                compat["operator"] != "="
                and not Tools.compare_versions(
                    CLEEP_VERSION, compat["version"], compare_strict
                )
            ):
                raise Exception(
                    f'App "{module_name}" is not installable due to version incompatibility of app dependency "{dependency}" that requires {compat_str} to be installed'
                )

    def __get_local_module_dependencies(self, module_name):
        """
        Install local application.
        This function loads dynamically app and get MODULE_DEPS member content

        Args:
            module_name (string): module name

        Returns:
            list: list of local module dependencies::

                ['dep1', 'dep2', ...]

        """
        module_deps = []
        try:
            module_path = f"{self.PYTHON_CLEEP_IMPORT_PATH}{module_name}"
            module_ = importlib.import_module(module_path)
            module_filename = getattr(module_, "APP_FILENAME", module_name)
            del module_
            class_path = (
                f"{self.PYTHON_CLEEP_IMPORT_PATH}{module_name}.{module_filename}"
            )
            self.logger.trace('Importing module "%s"', class_path)
            module_ = importlib.import_module(class_path)
            module_class_ = getattr(module_, module_filename.capitalize())
            module_deps = getattr(module_class_, "MODULE_DEPS", [])
        except Exception:
            self.logger.exception(
                'Error loading locally installed application "%s". Dependencies may not be installed.',
                module_name,
            )

        return module_deps

    def _get_module_dependencies(
        self, module_name, modules_infos, get_module_infos_callback, context=None
    ):
        """
        Get module dependencies. Specified module will be also returned in result.
        Returned items are ordered by descent with first item as deepest leaf.

        Args:
            module_name (string): module name
            module_infos (dict): module infos (as returned by _get_module_infos). It must contains
                                 infos of module_name to allow dependencies search.
            get_module_infos_callback (function|array): callback to get module infos.
                                                        If function is specified, same callback is used during
                                                        recursivity.
                                                        If array is specified, callback is popped until last one that
                                                        is used until end of recursivity.
                                                        Can be either _get_module_infos_from_inventory,
                                                        _get_module_infos_from_market or _get_module_infos_from_package
            context (None): internal context for recursive call. Do not set.

        Returns:
            list: list of dependencies
        """
        if context is None:
            # initiate recursive process
            context = {
                "dependencies": [],
                "visited": [],
            }

        # already visited: circular dependency or diamond shared leaf
        if module_name in context["visited"]:
            return None
        context["visited"].append(module_name)

        # get module infos if needed
        callback = get_module_infos_callback
        if module_name not in modules_infos:
            if isinstance(get_module_infos_callback, list):
                callback = get_module_infos_callback.pop(0)
            infos = callback(module_name)
            modules_infos[module_name] = infos

        # get list of dependencies
        if not modules_infos[module_name]:
            # no infos available, surely a locally installed module
            module_dependencies = self.__get_local_module_dependencies(module_name)
        else:
            # info available get dependencies from meta
            module_dependencies = modules_infos[module_name].get("deps", [])

        # get dependencies (recursive call)
        for dependency_name in module_dependencies:
            if dependency_name == module_name:
                # avoid infinite loop
                continue
            if (
                isinstance(get_module_infos_callback, list)
                and len(get_module_infos_callback) > 0
            ):
                next_callback = get_module_infos_callback
            else:
                # reuse last (or only) infos callback for remaining recursion
                next_callback = callback
            self._get_module_dependencies(
                dependency_name, modules_infos, next_callback, context
            )

        context["dependencies"].append(module_name)
        return context["dependencies"]

    def _store_process_status(self, status, success=True):
        """
        Store last module process status in filesystem

        Args:
            status (dict): process status
        """
        # if no module name specified in status, it means it's cleep process
        module_name = "cleep" if "module" not in status else status["module"]

        # build and check path
        if success:
            fullpath = os.path.join(
                PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME
            )
        else:
            fullpath = os.path.join(
                PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME
            )
        path = os.path.join(PATH_INSTALL, module_name)
        if not os.path.exists(path):
            self.cleep_filesystem.mkdir(path, True)

        # store status
        self.logger.info('Storing process status in "%s"', fullpath)
        if not self.cleep_filesystem.write_json(fullpath, status):
            self.logger.error(
                'Error storing module "%s" process status into "%s"',
                module_name,
                fullpath,
            )

    def __install_module_callback(self, status):
        """
        Module install callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug("Module install callback status: %s", status)
        is_dependency = "extra" in status and status["extra"].get("isdependency", False)

        # handle install success
        if status["status"] == Install.STATUS_DONE:
            # need to restart
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status["module"])
            self._store_process_status(status, success=True)

            # update cleep.conf only for main module not dependencies
            if not is_dependency:
                self.cleep_conf.install_module(status["module"])

        elif status["status"] == Install.STATUS_ERROR:
            # set main action failed (prefer main module over failing dependency)
            self._store_process_status(status, success=False)
            self._set_module_process(
                failed=True,
                forced_module_name=(
                    self._get_processing_module_name() or status["module"]
                ),
            )

        # handle end of install to finalize install
        if status["status"] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None
            # drop local package copy: after main module ends, or when process
            # fails (dependency failure would otherwise leave /tmp/<main>.zip)
            if status["status"] == Install.STATUS_ERROR:
                main_name = self._get_processing_module_name() or status["module"]
                self._cleanup_module_package(main_name)
            elif not is_dependency:
                self._cleanup_module_package(status["module"])

        # send process status
        self.module_install_event.send(
            params={
                "status": status["status"],
                "module": status["module"],
            }
        )

    def _install_module(self, module_name, module_infos, extra=None):
        """
        Execute specified module installation

        Args:
            module_name (string): module name
            module_infos (dict): module infos
            extra (dict): extra data to use during module installation
        """
        if module_infos is None:
            # surely locally installed module, no need to perform complete install, just run final callback
            self.__install_module_callback(
                {
                    "process": ["Locally installed application"],
                    "stdout": [],
                    "stderr": [],
                    "status": Install.STATUS_DONE,
                    "module": module_name,
                }
            )
            return

        # non blocking, end of process handled in specified callback
        try:
            self.__processor = Install(
                self.cleep_filesystem,
                self.crash_report,
                self.task_factory,
                self.__install_module_callback,
            )
            self.__processor.install_module(module_name, module_infos, extra)
        except Exception as error:
            self.crash_report.manual_report(
                f'Error installing module "{module_name}"',
                extra={"module_infos": module_infos},
            )
            error_msg = str(error)
            self.__install_module_callback(
                {
                    "process": [f"Internal error during installation: {error_msg}"],
                    "stdout": [],
                    "stderr": [],
                    "status": Install.STATUS_ERROR,
                    "module": module_name,
                }
            )

    def _install_main_module(self, module_name, extra=None):
        """
        Install main module. This function will install all dependencies and update modules
        if necessary.

        Args:
            module_name (string): module name to install
            extra (dict): extra installation parameters
        """
        self.logger.trace('_install_main_module "%s"', module_name)
        installed_modules = self._get_installed_modules_names()
        package = extra.get("package") if extra is not None else None
        no_compatibility_check = (
            extra.get("no_compatibility_check") if extra is not None else False
        )
        package_copied = False

        try:
            # handle package
            if package and not os.path.exists(package):
                raise Exception(f'Specified package "{package}" does not exists')
            if package:
                # copy file to known path for next process and update new package path
                new_package = self.PACKAGE_BASE_PATH % {"module_name": module_name}
                shutil.copyfile(package, new_package)
                extra["package"] = new_package
                package_copied = True

            # compute dependencies to install
            modules_infos_json = {}
            dependencies = self._get_module_dependencies(
                module_name,
                modules_infos_json,
                (
                    self._get_module_infos_from_market
                    if not package
                    else [
                        self._get_module_infos_from_package,
                        self._get_module_infos_from_market,
                    ]
                ),
            )
            self.logger.debug('Module "%s" dependencies: %s', module_name, dependencies)

            # check dependencies compatibility
            self.__check_dependencies_compatibility(
                module_name, dependencies, modules_infos_json, no_compatibility_check
            )

            # schedule module + dependencies installations
            for dependency_name in dependencies:
                # reset previous update status
                self.__reset_module_update_data(dependency_name)
                self.logger.debug(
                    'Module "%s" update status: %s',
                    dependency_name,
                    self._modules_updates.get(dependency_name),
                )
                if dependency_name not in installed_modules:
                    # install dependency
                    self._postpone_sub_action(
                        Update.ACTION_MODULE_INSTALL,
                        dependency_name,
                        modules_infos_json[dependency_name],
                        module_name,
                        extra=extra if dependency_name == module_name else None,
                    )
                else:
                    # check if already installed module needs to be updated
                    module_infos_inventory = self._get_module_infos_from_inventory(
                        dependency_name
                    )
                    if Tools.compare_versions(
                        module_infos_inventory["version"],
                        modules_infos_json[dependency_name]["version"],
                    ):
                        self._postpone_sub_action(
                            Update.ACTION_MODULE_UPDATE,
                            dependency_name,
                            modules_infos_json[dependency_name],
                            module_name,
                        )
        except Exception:
            # drop copied package if scheduling failed before install started
            if package_copied:
                self._cleanup_module_package(module_name)
            raise

    def register_local_module(self, module_name):
        """
        Register a locally developed module already present on disk.

        Used by the developer application after scaffolding a new app. Does not
        download or unpack a package — only adds the module to CleepConf and
        requests a Cleep restart.

        Args:
            module_name (str): module name

        Returns:
            bool: True if module was registered
        """
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if self.cleep_conf.is_module_installed(module_name):
            raise InvalidParameter(f'Module "{module_name}" is already installed')

        try:
            importlib.import_module(f"{self.PYTHON_CLEEP_IMPORT_PATH}{module_name}")
        except ImportError as error:
            raise InvalidParameter(
                f'Module "{module_name}" was not found on disk'
            ) from error

        if not self.cleep_conf.install_module(module_name):
            raise CommandError(f'Unable to register module "{module_name}"')

        if module_name not in self._modules_updates:
            self._modules_updates[module_name] = self.__get_module_update_data(
                module_name, "0.0.0"
            )
        self._set_module_process(
            progress=100, failed=False, pending=True, forced_module_name=module_name
        )
        self.module_install_event.send(
            params={
                "status": Install.STATUS_DONE,
                "module": module_name,
            }
        )
        self.cleep_need_restart_event.send()
        return True

    def install_module(self, module_name, package=None, no_compatibility_check=False):
        """
        Install specified module.
        If package is not specified, installation will use infos from modules.json
        If package is specified, module will be installed using specified file.
        The package must be a valid application archive built by Cleep.

        Args:
            module_name (str): module name to install
            package (str, optional): module package path. Defaults to None.
            no_compatibility_check (bool, optional): do not check module compatibility (but only deps compat). Defaults to False.

        Returns:
            bool: True if installation will start
        """
        # check params
        if self._cleep_updates["processing"] or self._cleep_updates["pending"]:
            raise CommandInfo("Cleep update is in progress. Please wait for end of it")
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if self.cleep_conf.is_module_installed(module_name):
            raise InvalidParameter(f'Module "{module_name}" is already installed')

        # check if module is not already installed as library
        installed_modules = self._get_installed_modules_names()
        if module_name in installed_modules:
            self.logger.debug(
                'Module "%s" is already installed as library, just enable it in cleep.conf',
                module_name,
            )
            self.cleep_conf.install_module(module_name)
            self._set_module_process(
                progress=100, failed=False, pending=True, forced_module_name=module_name
            )
            self.module_install_event.send(
                params={
                    "status": Install.STATUS_DONE,
                    "module": module_name,
                }
            )
            self.cleep_need_restart_event.send()
            return True

        # postpone module installation
        self._acquire_update_lock()
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_INSTALL,
            module_name,
            extra={
                "package": package,
                "no_compatibility_check": no_compatibility_check,
            },
        )

        # start main actions task
        if postponed:
            self.__start_actions_tasks()
        elif not (self.__main_actions_task or self.__sub_actions_task):
            self._release_update_lock()

        return postponed

    def __uninstall_module_callback(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug("Module uninstall callback status: %s", status)

        # handle process success
        if status["status"] == Install.STATUS_DONE:
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status["module"])
            self._store_process_status(status, success=True)

            # update cleep.conf
            self.cleep_conf.uninstall_module(status["module"])

        elif status["status"] == Install.STATUS_ERROR:
            # set main action failed
            self._set_module_process(failed=True, forced_module_name=status["module"])
            self._store_process_status(status, success=False)

        # handle end of process
        if status["status"] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None

        # send process status to ui
        self.module_uninstall_event.send(
            params={
                "status": status["status"],
                "module": status["module"],
            }
        )

    def _uninstall_module(self, module_name, module_infos, extra=None):
        """
        Execute specified module uninstallation

        Args:
            module_name (string): module name
            module_infos (dict): module infos
            extra (any): extra data (not used here)
        """
        try:
            self.__processor = Install(
                self.cleep_filesystem,
                self.crash_report,
                self.task_factory,
                self.__uninstall_module_callback,
            )
            self.__processor.uninstall_module(module_name, module_infos, extra["force"])
        except Exception as error:
            self.crash_report.manual_report(
                f'Error uninstalling module "{module_name}"',
                extra={"module_infos": module_infos},
            )
            error_msg = str(error)
            self.__uninstall_module_callback(
                {
                    "process": [f"Internal error during uninstallation: {error_msg}"],
                    "stdout": [],
                    "stderr": [],
                    "status": Install.STATUS_ERROR,
                    "module": module_name,
                }
            )

    def _uninstall_main_module(self, module_name, extra=None):
        """
        Uninstall module. This function will uninstall useless dependencies.

        Args:
            module_name (string): module name
            extra (any): extra data
        """
        self.logger.trace('_uninstall_main_module "%s"', module_name)
        # compute dependencies to uninstall
        modules_infos = {}
        dependencies = self._get_module_dependencies(
            module_name, modules_infos, self._get_module_infos_from_inventory
        )
        self.logger.debug('Module "%s" dependencies: %s', module_name, dependencies)
        modules_to_uninstall = self._get_modules_to_uninstall(
            module_name, dependencies, modules_infos
        )
        self.logger.info(
            'Module "%s" uninstallation will remove "%s"',
            module_name,
            modules_to_uninstall,
        )

        if len(modules_to_uninstall) == 0:
            # nothing to uninstall, stop process
            self.logger.debug(
                'Module "%s" is surely still needed as library, just disable it in cleep.conf',
                module_name,
            )
            self.cleep_conf.uninstall_module(module_name)
            self._set_module_process(
                progress=100, failed=False, pending=True, forced_module_name=module_name
            )
            self.module_uninstall_event.send(
                params={
                    "status": Install.STATUS_DONE,
                    "module": module_name,
                }
            )
            self.cleep_need_restart_event.send()
            return

        # schedule module + dependencies uninstalls
        for module_to_uninstall in modules_to_uninstall:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UNINSTALL,
                module_to_uninstall,
                modules_infos[module_to_uninstall],
                module_name,
                extra,
            )

    def uninstall_module(self, module_name, force=False):
        """
        Uninstall specified module

        Args:
            module_name (string): module name to uninstall
            force (bool, optional): True to force uninstall even if error occured. Defaults to False.
        """
        # check params
        if self._cleep_updates["processing"] or self._cleep_updates["pending"]:
            raise CommandInfo("Cleep update is in progress. Please wait for end of it")
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        installed_modules = self._get_installed_modules_names()
        if module_name not in installed_modules:
            raise InvalidParameter(f'Module "{module_name}" is not installed')
        module_state = self._modules_updates.get(module_name) or {}
        if module_state.get("processing"):
            raise CommandInfo(
                f'Module "{module_name}" uninstall or update is already in progress'
            )

        # postpone uninstall
        self._acquire_update_lock()
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_UNINSTALL,
            module_name,
            extra={"force": force},
        )

        # start main actions task
        if postponed:
            self.__start_actions_tasks()
        elif not (self.__main_actions_task or self.__sub_actions_task):
            self._release_update_lock()

        return postponed

    def _get_modules_to_uninstall(
        self, module_name, modules_to_uninstall, modules_infos
    ):
        """
        Look for modules to uninstall list and remove modules that cannot be removed
        due to dependency with other module still needed.

        Args:
            module_name (string): main module to uninstall
            modules_to_uninstall (list): module names to uninstall
            modules_infos (dict): dict of modules infos

        Returns:
            list: modules names to uninstall
        """
        out = modules_to_uninstall[:]

        for module_to_uninstall in modules_to_uninstall:
            # list of modules to uninstall contains the main module itself, drop it
            if module_to_uninstall == module_name:
                continue

            # fix potential missing module_infos
            if module_to_uninstall not in modules_infos:
                self.logger.warning(
                    'Module infos dict should contains "%s" module infos. '
                    "Module won't be removed and can become an orphan.",
                    module_to_uninstall,
                )
                module_infos = {"loadedby": ["orphan"]}
            else:
                module_infos = modules_infos[module_to_uninstall]

            for loaded_by in module_infos["loadedby"]:
                if loaded_by not in modules_to_uninstall:
                    # do not uninstall this module because it is a dependency of another module
                    self.logger.debug(
                        'Do not uninstall module "%s" which is still needed by "%s" module',
                        module_to_uninstall,
                        loaded_by,
                    )
                    out.remove(module_to_uninstall)
                    break

            if (
                self.cleep_conf.is_module_installed(module_to_uninstall)
                and module_to_uninstall in out
            ):
                # do not uninstall module that has been installed by user
                out.remove(module_to_uninstall)

        return out

    def __update_module_callback(self, status):
        """
        Module update callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug("Module update callback status: %s", status)

        # handle process success
        if status["status"] == Install.STATUS_DONE:
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status["module"])
            self._store_process_status(status, success=True)

            # update cleep.conf adding module to updated ones
            self.cleep_conf.update_module(status["module"])

        elif status["status"] == Install.STATUS_ERROR:
            # set main action failed
            self._set_module_process(failed=True, forced_module_name=status["module"])
            self._store_process_status(status, success=False)

        # handle end of process
        if status["status"] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None

        # send process status to ui
        self.module_update_event.send(
            params={
                "status": status["status"],
                "module": status["module"],
            }
        )

    def _update_module(self, module_name, module_infos):
        """
        Execute module update

        Params:
            module_name (string): module name to install
            module_infos (dict): module infos
        """
        try:
            self.__processor = Install(
                self.cleep_filesystem,
                self.crash_report,
                self.task_factory,
                self.__update_module_callback,
            )
            self.__processor.update_module(module_name, module_infos)
        except Exception as error:
            self.crash_report.manual_report(
                f'Error updating module "{module_name}"',
                extra={"module_infos": module_infos},
            )
            error_msg = str(error)
            self.__update_module_callback(
                {
                    "process": [f"Internal error during update: {error_msg}"],
                    "stdout": [],
                    "stderr": [],
                    "status": Install.STATUS_ERROR,
                    "module": module_name,
                }
            )

    def _update_main_module(self, module_name):
        """
        Update main module performing:
            - install of new dependencies
            - uninstall of old dependencies
            - update of modules

        Args:
            module_name (string): module name
        """
        self.logger.trace('_update_main_module "%s"', module_name)
        # compute module dependencies
        modules_infos_inventory = {}
        modules_infos_json = {}
        old_dependencies = self._get_module_dependencies(
            module_name, modules_infos_inventory, self._get_module_infos_from_inventory
        )
        self.logger.debug(
            'Module "%s" old dependencies: %s', module_name, old_dependencies
        )
        new_dependencies = self._get_module_dependencies(
            module_name, modules_infos_json, self._get_module_infos_from_market
        )
        self.logger.debug(
            'Module "%s" new dependencies: %s', module_name, new_dependencies
        )
        dependencies_to_uninstall = [
            mod_name
            for mod_name in old_dependencies
            if mod_name not in new_dependencies
        ]
        self.logger.debug(
            'Module "%s" requires to uninstall modules: %s',
            module_name,
            dependencies_to_uninstall,
        )
        dependencies_to_install = [
            mod_name
            for mod_name in new_dependencies
            if mod_name not in old_dependencies
        ]
        self.logger.debug(
            'Module "%s" requires to install new modules: %s',
            module_name,
            dependencies_to_install,
        )
        dependencies_to_update = [
            mod_name
            for mod_name in new_dependencies
            if mod_name in old_dependencies
            and Tools.compare_versions(
                modules_infos_inventory[mod_name]["version"],
                modules_infos_json[mod_name]["version"],
            )
        ]
        self.logger.debug(
            'Module "%s" requires to update modules: %s',
            module_name,
            dependencies_to_update,
        )

        # postpone old dependencies uninstallations
        for mod_name in dependencies_to_uninstall:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UNINSTALL,
                mod_name,
                modules_infos_inventory[mod_name],
                module_name,
                extra={
                    "force": True
                },  # always force to make sure module is completely uninstalled
            )

        # postpone new dependencies installations
        for mod_name in dependencies_to_install:
            self._postpone_sub_action(
                Update.ACTION_MODULE_INSTALL,
                mod_name,
                modules_infos_json[mod_name],
                module_name,
            )

        # postpone dependencies update
        for mod_name in dependencies_to_update:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UPDATE,
                mod_name,
                modules_infos_json[mod_name],
                module_name,
            )

    def update_module(self, module_name):
        """
        Update specified module

        Args:
            module_name (string): module name to update

        Returns:
            bool: True if module update postponed, False otherwise
        """
        # check params
        if self._cleep_updates["processing"] or self._cleep_updates["pending"]:
            raise CommandInfo("Cleep update is in progress. Please wait for end of it")
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        installed_modules = self._get_installed_modules_names()
        if module_name not in installed_modules:
            raise InvalidParameter(f'Module "{module_name}" is not installed')
        if not self._modules_updates[module_name]["updatable"]:
            self.logger.info('Module "%s" is already up to date', module_name)
            return False
        if self._modules_updates[module_name].get("processing"):
            raise CommandInfo(f'Module "{module_name}" update is already in progress')

        # postpone update
        self._acquire_update_lock()
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_UPDATE,
            module_name,
        )

        # start actions tasks
        if postponed:
            self.__start_actions_tasks()
        elif not (self.__main_actions_task or self.__sub_actions_task):
            self._release_update_lock()

        return postponed
