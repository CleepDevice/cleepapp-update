#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import tempfile
import unittest
import zipfile
import logging
from unittest.mock import Mock, patch

from backend.install.install_app_manifest import (
    InstallManifest,
    InstallManifestError,
    MODE_INSTALL,
    MODE_UNINSTALL,
    PHASE_POSTINST,
)


class InstallManifestTests(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.CRITICAL)
        self.tmp = tempfile.mkdtemp()
        self.bin_path = os.path.join(self.tmp, "bin")
        self.asset_path = os.path.join(self.tmp, "asset")
        self.storage_path = os.path.join(self.tmp, "storage")
        os.makedirs(self.bin_path)
        os.makedirs(self.asset_path)
        os.makedirs(self.storage_path)
        self.fs = Mock()
        self.fs.mkdirs = Mock(side_effect=lambda p: os.makedirs(p, exist_ok=True))
        self.fs.rm = Mock(
            side_effect=lambda p: os.remove(p) if os.path.exists(p) else None
        )

        def _open(path, mode, encoding=None):
            return open(path, mode)

        def _close(fd):
            fd.close()

        self.fs.open = _open
        self.fs.close = _close
        self.runner = InstallManifest(
            "ngrok",
            {
                "APP_BIN_PATH": self.bin_path,
                "APP_ASSET_PATH": self.asset_path,
                "APP_STORAGE_PATH": self.storage_path,
                "APP_TMP_PATH": os.path.join(self.tmp, "tmp"),
            },
            self.fs,
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_rejects_bad_version(self):
        path = os.path.join(self.tmp, "postinst.json")
        with open(path, "w", encoding="utf-8") as fd:
            json.dump({"version": 99}, fd)
        with self.assertRaises(InstallManifestError):
            InstallManifest.load(path)

    def test_phase_path_scripts_and_flat(self):
        extract = os.path.join(self.tmp, "pkg")
        os.makedirs(os.path.join(extract, "scripts"))
        self.assertTrue(
            InstallManifest.phase_path(extract, PHASE_POSTINST).endswith(
                "scripts/postinst.json"
            )
        )
        backup = os.path.join(self.tmp, "install", "ngrok")
        os.makedirs(backup)
        self.assertEqual(
            InstallManifest.phase_path(backup, PHASE_POSTINST, in_scripts=False),
            os.path.join(backup, "postinst.json"),
        )

    def test_extract_bin_zip_and_chmod(self):
        zip_path = os.path.join(self.bin_path, "ngrok.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("ngrok", b"#!/bin/sh\necho ok\n")
        self.runner.run(
            {
                "version": 1,
                "bin": [{"src": "ngrok.zip", "extract": True}],
                "chmod": {"bin": {"ngrok": "+x"}},
            },
            mode=MODE_INSTALL,
        )
        out = os.path.join(self.bin_path, "ngrok")
        self.assertTrue(os.path.isfile(out))
        self.assertFalse(os.path.exists(zip_path))
        self.assertTrue(os.access(out, os.X_OK))

    def test_chmod_multiple_paths(self):
        exe = os.path.join(self.bin_path, "tool")
        conf_dir = os.path.join(self.bin_path, "conf")
        os.makedirs(conf_dir)
        conf = os.path.join(conf_dir, "tool.conf")
        with open(exe, "w", encoding="utf-8") as fd:
            fd.write("#!/bin/sh\n")
        with open(conf, "w", encoding="utf-8") as fd:
            fd.write("key=value\n")
        os.chmod(exe, 0o644)
        os.chmod(conf, 0o600)
        self.runner.run(
            {
                "version": 1,
                "chmod": {
                    "bin": {
                        "./tool": "+x",
                        "conf/tool.conf": "+r",
                    }
                },
            }
        )
        self.assertTrue(os.access(exe, os.X_OK))
        self.assertEqual(os.stat(conf).st_mode & 0o777, 0o644)

    def test_chmod_rejects_directory(self):
        os.makedirs(os.path.join(self.bin_path, "subdir"))
        with self.assertRaises(InstallManifestError):
            self.runner.run({"version": 1, "chmod": {"bin": {"subdir": "+x"}}})

    def test_chmod_rejects_unknown_mode(self):
        path = os.path.join(self.bin_path, "f")
        with open(path, "w", encoding="utf-8") as fd:
            fd.write("x")
        with self.assertRaises(InstallManifestError):
            self.runner.run({"version": 1, "chmod": {"bin": {"f": "0777"}}})

    def test_chmod_rejects_nested_in_bin(self):
        with self.assertRaises(InstallManifestError):
            self.runner.run(
                {
                    "version": 1,
                    "bin": [
                        {
                            "src": "ngrok.zip",
                            "extract": False,
                            "chmod": ["ngrok"],
                        }
                    ],
                }
            )

    def test_path_escape_rejected(self):
        with self.assertRaises(InstallManifestError):
            self.runner._resolve_under_root("bin", "../etc/passwd")

    def test_missing_archive_fails(self):
        with self.assertRaises(InstallManifestError):
            self.runner.run(
                {
                    "version": 1,
                    "bin": [{"src": "missing.zip", "extract": True}],
                }
            )

    def test_services_rejected(self):
        with self.assertRaises(InstallManifestError):
            self.runner.run(
                {
                    "version": 1,
                    "services": [{"unit": "ngrok.service", "action": "restart"}],
                }
            )

    def test_pip_wheels_rejected(self):
        with self.assertRaises(InstallManifestError):
            self.runner.run(
                {
                    "version": 1,
                    "pip_wheels": [{"url": "https://example.com/pkg.whl"}],
                }
            )

    @patch("backend.install.install_app_manifest.Console")
    def test_uninstall_apt_purge(self, console_cls):
        console = Mock()
        console_cls.return_value = console
        console.command.return_value = {
            "returncode": 0,
            "stdout": [],
            "stderr": [],
        }
        self.runner.run(
            {"version": 1, "apt": ["python3-gst-1.0"]},
            mode=MODE_UNINSTALL,
        )
        cmd = console.command.call_args[0][0]
        self.assertIn("apt-get purge", cmd)
        self.assertIn("python3-gst-1.0", cmd)

    @patch("backend.install.install_app_manifest.Console")
    def test_apt_install_failure_keeps_console_output(self, console_cls):
        console = Mock()
        console_cls.return_value = console
        console.command.side_effect = [
            {"returncode": 0, "stdout": ["Hit:1"], "stderr": []},
            {
                "returncode": 100,
                "stdout": ["Reading package lists..."],
                "stderr": ["E: Unable to locate package foo"],
            },
        ]
        with self.assertRaises(InstallManifestError) as cm:
            self.runner.run(
                {"version": 1, "apt": ["foo"]},
                mode=MODE_INSTALL,
            )
        self.assertEqual(cm.exception.returncode, 100)
        self.assertEqual(cm.exception.stdout, ["Reading package lists..."])
        self.assertEqual(cm.exception.stderr, ["E: Unable to locate package foo"])
        self.assertIn("apt-get install", str(cm.exception))

    def test_uninstall_rejects_bin(self):
        with self.assertRaises(InstallManifestError):
            self.runner.run(
                {"version": 1, "bin": [{"src": "x.zip", "extract": True}]},
                mode=MODE_UNINSTALL,
            )


if __name__ == "__main__":
    unittest.main()
