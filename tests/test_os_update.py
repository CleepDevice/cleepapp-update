#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import tempfile
import unittest

sys.path.append("../")
from backend.os_identity import (
    parse_cleepos_version,
    read_cleepos_version,
    get_os_identity,
)
from backend.os_catalog import (
    load_os_catalog,
    is_cleepos_newer,
    evaluate_os_update,
)
from backend.os_conf_report import (
    build_os_conf_report,
    find_leftover_paths,
    sentry_extra_from_report,
)


class OsIdentityTests(unittest.TestCase):

    def test_parse_cleepos_version(self):
        parsed = parse_cleepos_version("bullseye20231205")
        self.assertEqual(
            parsed,
            {
                "version": "bullseye20231205",
                "suite": "bullseye",
                "build": "20231205",
            },
        )

    def test_parse_cleepos_version_invalid(self):
        with self.assertRaises(ValueError):
            parse_cleepos_version("11.11")

    def test_read_and_get_os_identity(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf8", delete=False) as handle:
            handle.write("bullseye20250506\n")
            path = handle.name
        try:
            self.assertEqual(read_cleepos_version(path), "bullseye20250506")
            self.assertEqual(
                get_os_identity(path),
                {
                    "version": "bullseye20250506",
                    "suite": "bullseye",
                    "build": "20250506",
                },
            )
        finally:
            os.unlink(path)


class OsCatalogTests(unittest.TestCase):

    def _write_catalog(self, payload):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf8", delete=False)
        json.dump(payload, handle)
        handle.close()
        return handle.name

    def test_load_default_catalog(self):
        catalog = load_os_catalog()
        self.assertIn("latest_by_suite", catalog)
        self.assertIn("releases", catalog)
        self.assertIn("bullseye", catalog["latest_by_suite"])

    def test_is_cleepos_newer(self):
        self.assertTrue(is_cleepos_newer("bullseye20231205", "bullseye20250831"))
        self.assertFalse(is_cleepos_newer("bullseye20250831", "bullseye20231205"))
        self.assertFalse(is_cleepos_newer("bullseye20231205", "bullseye20231205"))
        self.assertFalse(is_cleepos_newer("bullseye20231205", "bookworm20240101"))

    def test_evaluate_os_update_up_to_date(self):
        catalog = {
            "latest_by_suite": {"bullseye": "bullseye20231205"},
            "releases": {
                "bullseye20231205": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.1.2",
                    "blocks_cleep_update": False,
                    "playbook_url": None,
                    "playbook_sha256": None,
                    "changelog": "baseline",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20231205")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertFalse(result["updatable"])
        self.assertEqual(result["current"], "bullseye20231205")
        self.assertEqual(result["suite"], "bullseye")

    def test_evaluate_os_update_available(self):
        catalog = {
            "latest_by_suite": {"bullseye": "bullseye20250831"},
            "releases": {
                "bullseye20250831": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.1.2",
                    "blocks_cleep_update": True,
                    "playbook_url": "https://example/playbook.tar.gz",
                    "playbook_sha256": "abc",
                    "changelog": "newer image",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20231205")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertTrue(result["updatable"])
        self.assertEqual(result["version"], "bullseye20250831")
        self.assertTrue(result["blocks_cleep_update"])
        self.assertEqual(result["playbook_url"], "https://example/playbook.tar.gz")
        self.assertFalse(result["cleep_too_old"])

    def test_evaluate_os_update_cleep_too_old(self):
        catalog = {
            "latest_by_suite": {"bullseye": "bullseye20250831"},
            "releases": {
                "bullseye20250831": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.2.0",
                    "blocks_cleep_update": False,
                    "playbook_url": None,
                    "playbook_sha256": None,
                    "changelog": "needs newer cleep",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20231205")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertFalse(result["updatable"])
        self.assertTrue(result["cleep_too_old"])
        self.assertEqual(result["version"], "bullseye20250831")

    def test_load_os_catalog_custom_path(self):
        path = self._write_catalog({"latest_by_suite": {}, "releases": {}})
        try:
            catalog = load_os_catalog(path)
            self.assertEqual(catalog["releases"], {})
        finally:
            os.unlink(path)


class OsConfReportTests(unittest.TestCase):

    def test_find_leftover_paths_and_build_report(self):
        root = tempfile.mkdtemp()
        try:
            etc = os.path.join(root, "etc")
            boot = os.path.join(root, "boot")
            os.makedirs(etc)
            os.makedirs(boot)
            open(os.path.join(etc, "cleepos_version"), "w", encoding="utf8").write(
                "bullseye20250831\n"
            )
            open(os.path.join(etc, "dhcpcd.conf"), "w", encoding="utf8").write("keep\n")
            open(os.path.join(etc, "dhcpcd.conf.dpkg-dist"), "w", encoding="utf8").write(
                "pkg\n"
            )
            open(os.path.join(etc, "secret.conf"), "w", encoding="utf8").write(
                "password=supersecret\n"
            )

            leftovers = find_leftover_paths(roots=(etc, boot))
            self.assertEqual(
                leftovers,
                [os.path.join(etc, "dhcpcd.conf.dpkg-dist")],
            )

            report_path = os.path.join(root, "report.txt")
            # Patch module constants via build kwargs: scan uses fixed /etc — call find only above.
            # build_os_conf_report scans real /etc; unit-test the serializer helpers instead.
            report = {
                "from_version": "bullseye20231205",
                "to_version": "bullseye20250831",
                "leftover_count": 1,
                "leftover_paths": leftovers,
                "apt_conf_actions": [
                    "Installing new version of config file /etc/security/namespace.init ..."
                ],
                "high_interest": [
                    {
                        "path": "/etc/dhcpcd.conf",
                        "exists": True,
                        "leftovers": [os.path.join(etc, "dhcpcd.conf.dpkg-dist")],
                    }
                ],
            }
            extra = sentry_extra_from_report(report)
            self.assertEqual(extra["leftover_count"], 1)
            self.assertEqual(extra["leftover_paths"], leftovers)
            joined = " ".join(str(v) for v in extra.values())
            self.assertNotIn("supersecret", joined)
            self.assertNotIn("password=", joined)
        finally:
            import shutil

            shutil.rmtree(root, ignore_errors=True)

    def test_build_os_conf_report_writes_file(self):
        root = tempfile.mkdtemp()
        try:
            etc = os.path.join(root, "etc")
            os.makedirs(etc)
            version_path = os.path.join(etc, "cleepos_version")
            with open(version_path, "w", encoding="utf8") as handle:
                handle.write("bullseye20250831\n")
            with open(
                os.path.join(etc, "wpa_supplicant.conf.dpkg-dist"), "w", encoding="utf8"
            ) as handle:
                handle.write("psk=secretvalue\n")
            report_path = os.path.join(root, "os-upgrade-conf-report.txt")
            report = build_os_conf_report(
                from_version="bullseye20231205",
                to_version="bullseye20250831",
                report_path=report_path,
                scan_roots=(etc,),
                cleepos_version_path=version_path,
            )
            self.assertTrue(os.path.isfile(report_path))
            self.assertEqual(report["leftover_count"], 1)
            self.assertIn("privacy: paths", report["text"])
            self.assertIn("wpa_supplicant.conf.dpkg-dist", report["text"])
            self.assertNotIn("secretvalue", report["text"])
            self.assertNotIn("psk=", report["text"])
        finally:
            import shutil

            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
