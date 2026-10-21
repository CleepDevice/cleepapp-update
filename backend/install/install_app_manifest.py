#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Declarative module install/uninstall manifests (scripts/*.json).

Phases:
  preinst.json / postinst.json / preuninst.json / postuninst.json

Allowlisted actions only. Paths constrained to APP_BIN / APP_ASSET / APP_STORAGE.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import zipfile
from typing import Any

from cleep.libs.internals.console import Console

SUPPORTED_VERSION = 1

PHASE_PREINST = "preinst"
PHASE_POSTINST = "postinst"
PHASE_PREUNINST = "preuninst"
PHASE_POSTUNINST = "postuninst"
INSTALL_PHASES = frozenset({PHASE_PREINST, PHASE_POSTINST})
UNINSTALL_PHASES = frozenset({PHASE_PREUNINST, PHASE_POSTUNINST})
ALL_PHASES = INSTALL_PHASES | UNINSTALL_PHASES

MODE_INSTALL = "install"
MODE_UNINSTALL = "uninstall"

ROOT_BIN = "bin"
ROOT_ASSET = "asset"
ROOT_STORAGE = "storage"
ALLOWED_ROOTS = frozenset({ROOT_BIN, ROOT_ASSET, ROOT_STORAGE})

# Allowlisted install modes only (no setuid/setgid/sticky, no free octal).
_MODE_EXEC = (
    stat.S_IRUSR
    | stat.S_IWUSR
    | stat.S_IXUSR
    | stat.S_IRGRP
    | stat.S_IXGRP
    | stat.S_IROTH
    | stat.S_IXOTH
)  # 0755
_MODE_READ = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH  # 0644
_MODE_PRIVATE = stat.S_IRUSR | stat.S_IWUSR  # 0600
ALLOWED_CHMOD_MODES = {
    "+x": _MODE_EXEC,
    "0755": _MODE_EXEC,
    "755": _MODE_EXEC,
    "+r": _MODE_READ,
    "0644": _MODE_READ,
    "644": _MODE_READ,
    "0600": _MODE_PRIVATE,
    "600": _MODE_PRIVATE,
}


class InstallManifestError(Exception):
    """Invalid manifest or failed action."""

    def __init__(self, message, stdout=None, stderr=None, returncode=None):
        """
        Args:
            message (str): error message
            stdout (list): optional console stdout lines
            stderr (list): optional console stderr lines
            returncode (int): optional command return code
        """
        super().__init__(message)
        self.stdout = list(stdout or [])
        self.stderr = list(stderr or [])
        self.returncode = returncode


class InstallManifest:
    """
    Load and execute a phase JSON manifest.
    """

    def __init__(
        self,
        module_name: str,
        app_paths: dict[str, str],
        cleep_filesystem,
        logger: logging.Logger | None = None,
    ):
        """
        Args:
            module_name (str): module name
            app_paths (dict): APP_STORAGE_PATH / APP_TMP_PATH / APP_ASSET_PATH / APP_BIN_PATH
            cleep_filesystem: CleepFilesystem instance
            logger: optional logger
        """
        self.module_name = module_name
        self.app_paths = app_paths
        self.cleep_filesystem = cleep_filesystem
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._root_map = {
            ROOT_BIN: app_paths["APP_BIN_PATH"],
            ROOT_ASSET: app_paths["APP_ASSET_PATH"],
            ROOT_STORAGE: app_paths["APP_STORAGE_PATH"],
        }

    @staticmethod
    def phase_filename(phase: str) -> str:
        """
        Return ``<phase>.json`` filename for a phase name.
        """
        if phase not in ALL_PHASES:
            raise InstallManifestError('Invalid phase "%s"' % phase)
        return "%s.json" % phase

    @staticmethod
    def phase_path(base_dir: str, phase: str, in_scripts: bool = True) -> str:
        """
        Return path to a phase manifest.

        Args:
            base_dir: package extract root or ``PATH_INSTALL/<module>``
            phase: preinst / postinst / preuninst / postuninst
            in_scripts: True → ``base_dir/scripts/<phase>.json`` (package tree);
                False → ``base_dir/<phase>.json`` (install backup dir)
        """
        filename = InstallManifest.phase_filename(phase)
        if in_scripts:
            return os.path.join(base_dir, "scripts", filename)
        return os.path.join(base_dir, filename)

    @staticmethod
    def load(path: str) -> dict[str, Any]:
        """Load and validate manifest JSON."""
        with open(path, "r", encoding="utf-8") as fd:
            data = json.load(fd)
        if not isinstance(data, dict):
            raise InstallManifestError("manifest must be an object")
        version = data.get("version")
        if version != SUPPORTED_VERSION:
            raise InstallManifestError(
                "Unsupported manifest version %s (expected %s)"
                % (version, SUPPORTED_VERSION)
            )
        return data

    def run(self, data: dict[str, Any], mode: str = MODE_INSTALL) -> None:
        """
        Execute declared actions.

        Args:
            data: loaded manifest
            mode: ``install`` (apt install / pip install / bin / chmod) or
                  ``uninstall`` (apt purge / pip uninstall only)
        """
        if mode not in (MODE_INSTALL, MODE_UNINSTALL):
            raise InstallManifestError('Invalid manifest mode "%s"' % mode)
        if data.get("services") is not None:
            raise InstallManifestError(
                '"services" is not supported '
                "(manage systemd units in the app module)"
            )
        if data.get("pip_wheels") is not None:
            raise InstallManifestError(
                '"pip_wheels" is not supported; put package specs or wheel '
                'URLs in ordered "pip" list'
            )

        if mode == MODE_UNINSTALL:
            if data.get("bin") is not None or data.get("chmod") is not None:
                raise InstallManifestError(
                    'uninstall manifests must not declare "bin" or "chmod"'
                )
            self._run_apt_purge(data.get("apt") or [])
            self._run_pip_uninstall(data.get("pip") or [])
            return

        self._run_apt_install(data.get("apt") or [])
        self._run_pip_install(data.get("pip") or [])
        self._run_bin_entries(data.get("bin") or [])
        self._run_chmod(data.get("chmod") or {})

    def _resolve_under_root(self, root: str, rel_path: str) -> str:
        if root not in ALLOWED_ROOTS:
            raise InstallManifestError('Invalid root "%s"' % root)
        base = os.path.realpath(self._root_map[root])
        target = os.path.realpath(os.path.join(base, rel_path))
        prefix = base if base.endswith(os.sep) else base + os.sep
        if target != base and not target.startswith(prefix):
            raise InstallManifestError(
                'Path escapes allowed root: "%s" (root=%s)' % (rel_path, root)
            )
        return target

    @staticmethod
    def _fail_command(label: str, resp: dict) -> None:
        """
        Raise InstallManifestError with console stdout/stderr attached.

        Args:
            label (str): command label (e.g. apt-get install)
            resp (dict): Console.command result
        """
        raise InstallManifestError(
            "%s failed (rc=%s)" % (label, resp.get("returncode")),
            stdout=resp.get("stdout") or [],
            stderr=resp.get("stderr") or [],
            returncode=resp.get("returncode"),
        )

    def _run_apt_install(self, packages: list) -> None:
        if not packages:
            return
        packages = self._validate_package_list(packages, "apt")
        console = Console()
        self.logger.info("manifest apt install: %s", packages)
        update = console.command(
            "DEBIAN_FRONTEND=noninteractive apt-get update", timeout=600
        )
        if update["returncode"] != 0:
            self._fail_command("apt-get update", update)
        cmd = (
            "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends %s"
            % (" ".join(packages))
        )
        resp = console.command(cmd, timeout=600)
        if resp["returncode"] != 0:
            self._fail_command("apt-get install", resp)

    def _run_apt_purge(self, packages: list) -> None:
        if not packages:
            return
        packages = self._validate_package_list(packages, "apt")
        console = Console()
        cmd = "DEBIAN_FRONTEND=noninteractive apt-get purge -y %s" % (
            " ".join(packages)
        )
        self.logger.info("manifest apt purge: %s", packages)
        resp = console.command(cmd, timeout=600)
        if resp["returncode"] != 0:
            self._fail_command("apt-get purge", resp)

    def _run_pip_install(self, packages: list) -> None:
        if not packages:
            return
        packages = self._validate_package_list(packages, "pip")
        console = Console()
        cmd = "python3 -m pip install --root-user-action=ignore %s" % " ".join(packages)
        self.logger.info("manifest pip install: %s", packages)
        resp = console.command(cmd, timeout=600)
        if resp["returncode"] != 0:
            self._fail_command("pip install", resp)

    def _run_pip_uninstall(self, packages: list) -> None:
        if not packages:
            return
        packages = self._validate_package_list(packages, "pip")
        console = Console()
        cmd = "python3 -m pip uninstall -y %s" % " ".join(packages)
        self.logger.info("manifest pip uninstall: %s", packages)
        resp = console.command(cmd, timeout=600)
        if resp["returncode"] != 0:
            self._fail_command("pip uninstall", resp)

    @staticmethod
    def _validate_package_list(packages: list, field: str) -> list:
        if not isinstance(packages, list):
            raise InstallManifestError('"%s" must be a list' % field)
        for pkg in packages:
            if not isinstance(pkg, str) or not pkg.strip():
                raise InstallManifestError("Invalid %s entry: %s" % (field, pkg))
        return packages

    def _run_bin_entries(self, entries: list) -> None:
        if not entries:
            return
        if not isinstance(entries, list):
            raise InstallManifestError('"bin" must be a list')
        for entry in entries:
            if not isinstance(entry, dict) or "src" not in entry:
                raise InstallManifestError("Invalid bin entry: %s" % entry)
            src = entry["src"]
            archive_path = self._resolve_under_root(ROOT_BIN, src)
            if entry.get("extract"):
                if not os.path.isfile(archive_path):
                    raise InstallManifestError(
                        'bin archive not found: "%s"' % archive_path
                    )
                dest_dir = self._root_map[ROOT_BIN]
                self.logger.info("Extract %s into %s", archive_path, dest_dir)
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        out = self._resolve_under_root(ROOT_BIN, info.filename)
                        if info.is_dir():
                            self.cleep_filesystem.mkdirs(out)
                            continue
                        self.cleep_filesystem.mkdirs(os.path.dirname(out))
                        with zf.open(info) as src_fd:
                            data = src_fd.read()
                        fd = self.cleep_filesystem.open(out, "wb")
                        try:
                            fd.write(data)
                        finally:
                            self.cleep_filesystem.close(fd)
                self.cleep_filesystem.rm(archive_path)
            if "chmod" in entry:
                raise InstallManifestError(
                    'bin entry must not contain "chmod"; use top-level '
                    '"chmod": {"bin": {"path": "+x"}}'
                )

    def _run_chmod(self, by_root: dict) -> None:
        if not by_root:
            return
        if not isinstance(by_root, dict):
            raise InstallManifestError(
                '"chmod" must be an object keyed by root (bin/asset/storage)'
            )
        for root, paths in by_root.items():
            if root not in ALLOWED_ROOTS:
                raise InstallManifestError('Invalid chmod root "%s"' % root)
            if not isinstance(paths, dict):
                raise InstallManifestError(
                    '"chmod.%s" must be an object of path -> mode' % root
                )
            for rel_path, mode in paths.items():
                if not isinstance(rel_path, str) or not rel_path.strip():
                    raise InstallManifestError(
                        "Invalid chmod path under %s: %s" % (root, rel_path)
                    )
                if not isinstance(mode, str):
                    raise InstallManifestError(
                        "Invalid chmod mode for %s/%s: %s" % (root, rel_path, mode)
                    )
                self._chmod_path(root, rel_path.strip(), mode)

    def _chmod_path(self, root: str, rel_path: str, mode: str) -> None:
        rel = rel_path[2:] if rel_path.startswith("./") else rel_path
        if not rel or rel.startswith("/") or rel.startswith("\\"):
            raise InstallManifestError('Invalid chmod path: "%s"' % rel_path)
        mode_key = str(mode)
        if mode_key not in ALLOWED_CHMOD_MODES:
            raise InstallManifestError(
                'Unsupported chmod mode "%s" (allowed: %s)'
                % (mode, ", ".join(sorted(ALLOWED_CHMOD_MODES)))
            )
        path = self._resolve_under_root(root, rel)
        if not os.path.exists(path):
            raise InstallManifestError('chmod target missing: "%s"' % path)
        if os.path.isdir(path):
            raise InstallManifestError(
                'chmod target must be a file, not a directory: "%s"' % path
            )
        os.chmod(path, ALLOWED_CHMOD_MODES[mode_key])
        self.logger.info("chmod %s %s", mode_key, path)
