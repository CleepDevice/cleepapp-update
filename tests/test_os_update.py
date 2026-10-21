#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import shutil
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
    fetch_os_catalog,
    is_cleepos_newer,
    is_suite_older_than,
    evaluate_os_update,
    resolve_playbook_url,
    ensure_os_playbook,
    default_playbook_url,
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
        path = self._write_catalog(
            {
                "latest_by_suite": {"bullseye": "bullseye20250831"},
                "releases": {"bullseye20250831": {"suite": "bullseye"}},
            }
        )
        try:
            catalog = load_os_catalog(path)
            self.assertIn("latest_by_suite", catalog)
            self.assertIn("releases", catalog)
            self.assertIn("bullseye", catalog["latest_by_suite"])
        finally:
            os.unlink(path)

    def test_is_cleepos_newer(self):
        self.assertTrue(is_cleepos_newer("bullseye20231205", "bullseye20250831"))
        self.assertFalse(is_cleepos_newer("bullseye20250831", "bullseye20231205"))
        self.assertFalse(is_cleepos_newer("bullseye20231205", "bullseye20231205"))
        self.assertFalse(is_cleepos_newer("bullseye20231205", "bookworm20240101"))

    def test_is_suite_older_than(self):
        self.assertTrue(is_suite_older_than("bullseye", "bookworm"))
        self.assertFalse(is_suite_older_than("bookworm", "bullseye"))
        self.assertFalse(is_suite_older_than("bullseye", "bullseye"))
        self.assertFalse(is_suite_older_than("unknown", "bookworm"))

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

    def test_evaluate_os_update_suite_too_old_blocks_cleep(self):
        """Major OS: bullseye device blocked when catalog min_suite is bookworm."""
        catalog = {
            "min_suite": "bookworm",
            "latest_by_suite": {"bullseye": "bullseye20250831"},
            "releases": {
                "bullseye20250831": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.1.2",
                    "blocks_cleep_update": False,
                    "changelog": "still listed",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20250831")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertFalse(result["updatable"])
        self.assertTrue(result["os_suite_too_old"])
        self.assertTrue(result["blocks_cleep_update"])
        self.assertEqual(result["min_suite"], "bookworm")

    def test_evaluate_os_update_minor_same_suite_does_not_block(self):
        catalog = {
            "min_suite": "bullseye",
            "latest_by_suite": {"bullseye": "bullseye20250831"},
            "releases": {
                "bullseye20250831": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.1.2",
                    "blocks_cleep_update": False,
                    "changelog": "newer stamp",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20231205")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertTrue(result["updatable"])
        self.assertFalse(result["os_suite_too_old"])
        self.assertFalse(result["blocks_cleep_update"])

    def test_assert_os_allows_cleep_update_blocks(self):
        from cleep.exception import CommandInfo

        class FakeUpdate:
            def __init__(self):
                self._os_updates = {
                    "updatable": False,
                    "blocks_cleep_update": True,
                    "os_suite_too_old": True,
                    "suite": "bullseye",
                    "min_suite": "bookworm",
                }
                self.logger = type(
                    "L", (), {"warning": staticmethod(lambda *a, **k: None)}
                )()

            def check_os_updates(self):
                return self._os_updates

        from backend.update import Update

        fake = FakeUpdate()
        with self.assertRaises(CommandInfo) as cm:
            Update._assert_os_allows_cleep_update(fake)
        self.assertIn("bookworm", str(cm.exception))

    def test_evaluate_os_update_resolves_default_playbook_url(self):
        catalog = {
            "latest_by_suite": {"bullseye": "bullseye20250831"},
            "releases": {
                "bullseye20250831": {
                    "suite": "bullseye",
                    "min_cleep_version": "0.1.2",
                    "blocks_cleep_update": False,
                    "playbook_url": None,
                    "playbook_sha256": None,
                    "changelog": "newer image",
                }
            },
        }
        identity = parse_cleepos_version("bullseye20231205")
        result = evaluate_os_update(identity, catalog, "0.1.2")
        self.assertTrue(result["updatable"])
        self.assertEqual(result["playbook_url"], default_playbook_url("bullseye"))
        self.assertIn("playbooks/bullseye-minor/run.sh", result["playbook_url"])

    def test_fetch_os_catalog_prefers_remote(self):
        remote = {
            "latest_by_suite": {"bullseye": "bullseye20990101"},
            "releases": {"bullseye20990101": {"suite": "bullseye"}},
        }
        cache = tempfile.NamedTemporaryFile("w", encoding="utf8", delete=False)
        cache.close()
        os.unlink(cache.name)
        try:
            catalog = fetch_os_catalog(
                lambda _url: json.dumps(remote),
                cache_path=cache.name,
            )
            self.assertEqual(catalog["latest_by_suite"]["bullseye"], "bullseye20990101")
            self.assertTrue(os.path.isfile(cache.name))
        finally:
            if os.path.isfile(cache.name):
                os.unlink(cache.name)

    def test_fetch_os_catalog_falls_back_to_cache(self):
        cached = {
            "latest_by_suite": {"bullseye": "bullseye20240101"},
            "releases": {"bullseye20240101": {"suite": "bullseye"}},
        }
        cache_path = self._write_catalog(cached)
        try:
            catalog = fetch_os_catalog(
                lambda _url: None,
                cache_path=cache_path,
            )
            self.assertEqual(catalog["latest_by_suite"]["bullseye"], "bullseye20240101")
        finally:
            os.unlink(cache_path)

    def test_fetch_os_catalog_raises_without_remote_or_cache(self):
        missing_cache = os.path.join(
            tempfile.gettempdir(), "no-os-cache-%s.json" % os.getpid()
        )
        if os.path.isfile(missing_cache):
            os.unlink(missing_cache)
        with self.assertRaises(Exception):
            fetch_os_catalog(
                lambda _url: None,
                cache_path=missing_cache,
            )

    def test_ensure_os_playbook_downloads_and_caches(self):
        cache_root = tempfile.mkdtemp()
        script = "#!/bin/bash\necho ok\n"
        try:
            path = ensure_os_playbook(
                "bullseye",
                playbook_url="https://example/run.sh",
                download_content=lambda _url: script,
                cache_dir=cache_root,
            )
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf8") as handle:
                self.assertEqual(handle.read(), script)
        finally:
            shutil.rmtree(cache_root, ignore_errors=True)

    def test_ensure_os_playbook_falls_back_to_cache(self):
        cache_root = tempfile.mkdtemp()
        suite_dir = os.path.join(cache_root, "bullseye-minor")
        os.makedirs(suite_dir)
        cached_run = os.path.join(suite_dir, "run.sh")
        with open(cached_run, "w", encoding="utf8") as handle:
            handle.write("#!/bin/bash\necho cached\n")
        try:
            path = ensure_os_playbook(
                "bullseye",
                download_content=lambda _url: None,
                cache_dir=cache_root,
            )
            self.assertEqual(path, cached_run)
        finally:
            shutil.rmtree(cache_root, ignore_errors=True)

    def test_ensure_os_playbook_raises_without_remote_or_cache(self):
        cache_root = tempfile.mkdtemp()
        try:
            with self.assertRaises(Exception):
                ensure_os_playbook(
                    "bullseye",
                    download_content=lambda _url: None,
                    cache_dir=cache_root,
                )
        finally:
            shutil.rmtree(cache_root, ignore_errors=True)

    def test_resolve_playbook_url(self):
        self.assertEqual(
            resolve_playbook_url("bullseye", "https://custom/run.sh"),
            "https://custom/run.sh",
        )
        self.assertEqual(
            resolve_playbook_url("bullseye", None),
            default_playbook_url("bullseye"),
        )

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
            self.assertIn("--- existing config files ---", report["text"])
            self.assertIn("--- summary ---", report["text"])
            self.assertNotIn("secretvalue", report["text"])
            self.assertNotIn("psk=", report["text"])
            self.assertNotIn("diff vs live", report["text"])
        finally:
            import shutil

            shutil.rmtree(root, ignore_errors=True)


class OsDryRunAnalysisTests(unittest.TestCase):

    SAMPLE = (
        "Inst foo [1] (2 amd64)\n"
        "Conf foo (2 amd64)\n"
        "Need to get 12.3 MB of archives.\n"
        "After this operation, 150 MB of additional disk space will be used.\n"
        "12 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n"
    )

    def test_parse_disk_and_summary(self):
        from backend.os_dry_run_analysis import (
            parse_apt_disk_delta_bytes,
            parse_apt_summary_counts,
        )

        self.assertEqual(parse_apt_disk_delta_bytes(self.SAMPLE), 150 * 1024 * 1024)
        counts = parse_apt_summary_counts(self.SAMPLE)
        self.assertEqual(counts["upgraded"], 12)
        self.assertEqual(counts["newly_installed"], 1)
        self.assertEqual(counts["to_remove"], 0)

    def test_verdict_ok_with_enough_disk(self):
        from backend.os_dry_run_analysis import analyze_os_dry_run

        result = analyze_os_dry_run(
            self.SAMPLE,
            free_bytes=2 * 1024 * 1024 * 1024,
        )
        self.assertEqual(result["verdict"], "ok")
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("disk_ok", codes)

    def test_verdict_ko_insufficient_disk(self):
        from backend.os_dry_run_analysis import analyze_os_dry_run

        result = analyze_os_dry_run(
            self.SAMPLE,
            free_bytes=20 * 1024 * 1024,
        )
        self.assertEqual(result["verdict"], "ko")
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("disk_insufficient", codes)

    def test_sentry_excludes_user_disk_findings(self):
        from backend.os_dry_run_analysis import (
            analyze_os_dry_run,
            dry_run_errors_reportable_to_sentry,
        )

        analysis = analyze_os_dry_run(self.SAMPLE, free_bytes=20 * 1024 * 1024)
        self.assertEqual(dry_run_errors_reportable_to_sentry(analysis), [])

    def test_verdict_ko_critical_removal(self):
        from backend.os_dry_run_analysis import analyze_os_dry_run

        text = (
            "Remv python3 [3.9.2]\n"
            "After this operation, 1 MB of additional disk space will be used.\n"
            "0 upgraded, 0 newly installed, 1 to remove and 0 not upgraded.\n"
        )
        result = analyze_os_dry_run(text, free_bytes=500 * 1024 * 1024)
        self.assertEqual(result["verdict"], "ko")
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("critical_removal", codes)

    def test_format_analysis_section(self):
        from backend.os_dry_run_analysis import (
            analyze_os_dry_run,
            format_analysis_section,
        )

        analysis = analyze_os_dry_run(self.SAMPLE, free_bytes=2 * 1024 * 1024 * 1024)
        section = format_analysis_section(analysis)
        self.assertIn("verdict=OK", section)
        self.assertIn("=== findings ===", section)


class OsUpgradeRunnerDryRunTests(unittest.TestCase):

    def test_dry_run_env_passed_to_console(self):
        from unittest import mock

        fake_console_mod = mock.MagicMock()
        captured = {}

        class FakeConsole:
            def __init__(self, cmd, on_message, on_end, opts=None):
                captured["cmd"] = cmd
                captured["opts"] = opts or {}
                self.on_end = on_end

            def start(self):
                self.on_end(0, False)

        playbook = tempfile.NamedTemporaryFile(
            "w", encoding="utf8", suffix=".sh", delete=False
        )
        playbook.write("#!/bin/bash\n")
        playbook.close()

        fake_console_mod.EndlessConsole = FakeConsole
        try:
            with mock.patch.dict(
                sys.modules,
                {
                    "cleep": mock.MagicMock(),
                    "cleep.libs": mock.MagicMock(),
                    "cleep.libs.internals": mock.MagicMock(),
                    "cleep.libs.internals.console": fake_console_mod,
                },
            ):
                # Force re-import with stubbed EndlessConsole
                sys.modules.pop("backend.os_upgrade_runner", None)
                from backend.os_upgrade_runner import OsUpgradeRunner

                statuses = []
                runner = OsUpgradeRunner(
                    target_version="bullseye20990101",
                    status_callback=statuses.append,
                    playbook_path=playbook.name,
                    dry_run=True,
                )
                runner.run()
        finally:
            os.unlink(playbook.name)

        env = captured["opts"].get("env") or {}
        self.assertEqual(env.get("CLEEPOS_DRY_RUN"), "1")
        self.assertEqual(env.get("TARGET_CLEEPOS_VERSION"), "bullseye20990101")
        self.assertTrue(any(s.get("dry_run") for s in statuses))
        self.assertEqual(statuses[-1].get("status"), OsUpgradeRunner.STATUS_SUCCESS)


if __name__ == "__main__":
    unittest.main()
