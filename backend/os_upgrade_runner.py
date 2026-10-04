#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run a CleepOs playbook on-device (minor suite upgrade).
"""

import os
import threading
import logging
from cleep.libs.internals.console import EndlessConsole

__all__ = ["OsUpgradeRunner"]


class OsUpgradeRunner(threading.Thread):
    """
    Execute an OS playbook script and report progress via callback.
    """

    STATUS_IDLE = 0
    STATUS_RUNNING = 1
    STATUS_SUCCESS = 2
    STATUS_ERROR = 3

    PHASE_PROGRESS = {
        "preflight": 10,
        "prepare-rw": 25,
        "apt": 55,
        "finalize-version": 85,
        "prepare-ro": 95,
    }

    LOG_PATH = "/tmp/cleep/os-upgrade.log"
    DRY_RUN_LOG_PATH = "/tmp/cleep/os-upgrade-dry-run.log"

    def __init__(
        self,
        target_version,
        status_callback,
        playbook_path,
        env=None,
        dry_run=False,
    ):
        """
        Args:
            target_version (str): TARGET_CLEEPOS_VERSION for the playbook
            status_callback (function): callback(status_dict)
            playbook_path (str): path to run.sh (downloaded/cached from cleep-os)
            env (dict): extra environment variables for the playbook
            dry_run (bool): when True, set CLEEPOS_DRY_RUN=1 (apt simulate, no stamp)
        """
        threading.Thread.__init__(self, name="OsUpgradeRunner")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.target_version = target_version
        self.status_callback = status_callback
        self.playbook_path = playbook_path
        self.extra_env = env or {}
        self.dry_run = bool(dry_run)
        self.__console = None
        self.__status = self.STATUS_IDLE
        self.__progress = 0
        self.__phase = None
        self.__stdout = []
        self.__stderr = []
        self.__error = None
        self.daemon = True

    def run(self):
        """Thread entry: run playbook."""
        self.__status = self.STATUS_RUNNING
        self.__progress = 5
        self.__emit()

        if not self.playbook_path:
            self.__fail("Playbook path is missing")
            return

        log_path = self.DRY_RUN_LOG_PATH if self.dry_run else self.LOG_PATH
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        try:
            with open(log_path, "w", encoding="utf8") as log_file:
                mode = "dry-run" if self.dry_run else "apply"
                log_file.write(
                    f"CleepOs upgrade ({mode}) to {self.target_version}\n"
                    f"playbook={self.playbook_path}\n"
                )
        except OSError:
            self.logger.warning("Unable to truncate OS upgrade log", exc_info=True)

        if not os.path.isfile(self.playbook_path):
            self.__fail(f"Playbook not found: {self.playbook_path}")
            return

        playbook_env = {
            "TARGET_CLEEPOS_VERSION": self.target_version,
            "DEBIAN_FRONTEND": "noninteractive",
        }
        if self.dry_run:
            playbook_env["CLEEPOS_DRY_RUN"] = "1"
        playbook_env.update(self.extra_env)

        cmd = ["/bin/bash", self.playbook_path]
        self.__console = EndlessConsole(
            cmd,
            self.__on_message,
            self.__on_end,
            opts={
                "exec_dir": None,
                "delay": 0.2,
                "env": playbook_env,
            },
        )
        self.__console.start()

    def __on_message(self, stdout, stderr):
        if stdout:
            line = stdout.rstrip("\n")
            self.__stdout.append(line)
            self.__append_log(line)
            self.__handle_phase_line(line)
            self.__handle_playbook_fail_detail(line)
        if stderr:
            line = stderr.rstrip("\n")
            self.__stderr.append(line)
            self.__append_log(f"ERR: {line}")

    def __handle_playbook_fail_detail(self, line):
        # e.g. [cleepos-playbook] phase apt: fail — apt-get dist-upgrade failed
        marker = "phase "
        if "[cleepos-playbook]" not in line or ": fail" not in line:
            return
        idx = line.find(marker)
        if idx < 0:
            return
        detail = line[idx:].strip()
        self.__error = detail

    def __handle_phase_line(self, line):
        if not line.startswith("PHASE "):
            return
        parts = line.split()
        if len(parts) < 3:
            return
        phase = parts[1]
        action = parts[2]
        self.__phase = phase
        if action == "begin" and phase in self.PHASE_PROGRESS:
            self.__progress = self.PHASE_PROGRESS[phase]
            self.__emit()
        elif action == "end" and phase == "prepare-ro":
            self.__progress = 100
            self.__emit()
        elif action == "fail":
            self.__error = f"Playbook phase '{phase}' failed"
            self.__emit()

    def __on_end(self, return_code, killed):
        if return_code == 0 and not killed:
            self.__status = self.STATUS_SUCCESS
            self.__progress = 100
        else:
            self.__status = self.STATUS_ERROR
            if killed:
                self.__stderr.append("Playbook was killed")
                self.__error = self.__error or "Playbook was killed"
            elif not self.__error:
                self.__error = f"Playbook exited with code {return_code}"
        self.__emit()

    def __fail(self, message):
        self.logger.error(message)
        self.__stderr.append(message)
        self.__append_log(f"ERR: {message}")
        self.__error = message
        self.__status = self.STATUS_ERROR
        self.__emit()

    def __append_log(self, line):
        log_path = self.DRY_RUN_LOG_PATH if self.dry_run else self.LOG_PATH
        try:
            with open(log_path, "a", encoding="utf8") as log_file:
                log_file.write(line + "\n")
        except OSError:
            pass

    def __emit(self):
        if not self.status_callback:
            return
        self.status_callback(
            {
                "status": self.__status,
                "progress": self.__progress,
                "phase": self.__phase,
                "dry_run": self.dry_run,
                "error": self.__error,
                "log_path": self.DRY_RUN_LOG_PATH if self.dry_run else self.LOG_PATH,
                "stdout": list(self.__stdout),
                "stderr": list(self.__stderr),
            }
        )
