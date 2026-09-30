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

    DEFAULT_PLAYBOOK_DIR = os.path.join(
        os.path.dirname(__file__), "playbooks", "bullseye-minor"
    )
    LOG_PATH = "/tmp/cleep/os-upgrade.log"

    def __init__(
        self,
        target_version,
        status_callback,
        playbook_path=None,
        env=None,
    ):
        """
        Args:
            target_version (str): TARGET_CLEEPOS_VERSION for the playbook
            status_callback (function): callback(status_dict)
            playbook_path (str): path to run.sh (default embedded bullseye-minor)
            env (dict): extra environment variables for the playbook
        """
        threading.Thread.__init__(self, name="OsUpgradeRunner")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.target_version = target_version
        self.status_callback = status_callback
        self.playbook_path = playbook_path or os.path.join(
            self.DEFAULT_PLAYBOOK_DIR, "run.sh"
        )
        self.extra_env = env or {}
        self.__console = None
        self.__status = self.STATUS_IDLE
        self.__progress = 0
        self.__phase = None
        self.__stdout = []
        self.__stderr = []
        self.daemon = True

    def run(self):
        """Thread entry: run playbook."""
        self.__status = self.STATUS_RUNNING
        self.__progress = 5
        self.__emit()

        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
        try:
            with open(self.LOG_PATH, "w", encoding="utf8") as log_file:
                log_file.write(
                    f"CleepOs upgrade to {self.target_version}\n"
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
        if stderr:
            line = stderr.rstrip("\n")
            self.__stderr.append(line)
            self.__append_log(f"ERR: {line}")

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

    def __on_end(self, return_code, killed):
        if return_code == 0 and not killed:
            self.__status = self.STATUS_SUCCESS
            self.__progress = 100
        else:
            self.__status = self.STATUS_ERROR
            if killed:
                self.__stderr.append("Playbook was killed")
        self.__emit()

    def __fail(self, message):
        self.logger.error(message)
        self.__stderr.append(message)
        self.__append_log(f"ERR: {message}")
        self.__status = self.STATUS_ERROR
        self.__emit()

    def __append_log(self, line):
        try:
            with open(self.LOG_PATH, "a", encoding="utf8") as log_file:
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
                "stdout": list(self.__stdout),
                "stderr": list(self.__stderr),
            }
        )
