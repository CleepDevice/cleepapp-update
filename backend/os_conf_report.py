#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Inventory of config leftovers after a CleepOs playbook upgrade.

Path-only report (no file contents / no diffs) — safe to display and to send to Sentry.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Optional

CLEEPOS_VERSION_PATH = "/etc/cleepos_version"
DEFAULT_REPORT_PATH = "/tmp/cleep/os-upgrade-conf-report.txt"

LEFTOVER_SUFFIXES = (
    ".dpkg-dist",
    ".dpkg-old",
    ".dpkg-new",
    ".dpkg-tmp",
    ".ucf-dist",
    ".ucf-old",
    ".ucf-new",
)

HIGH_INTEREST_PATHS = (
    "/etc/wpa_supplicant/wpa_supplicant.conf",
    "/etc/wpa_supplicant/wpa_supplicant-wlan0.conf",
    "/etc/dhcpcd.conf",
    "/etc/ssh/sshd_config",
    "/etc/systemd/journald.conf",
    "/etc/nsswitch.conf",
    "/etc/hosts",
    "/etc/hostname",
    "/etc/timezone",
    "/boot/config.txt",
    "/boot/cmdline.txt",
)

_SCAN_ROOTS = ("/etc", "/boot")
_APT_ACTION_RE = re.compile(
    r"Installing new version of config file|Not replacing|existing configuration|"
    r"conffile|dpkg-dist|\.dpkg-|\.ucf-",
    re.IGNORECASE,
)


def _safe_read_line(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf8", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return None


def find_leftover_paths(roots: tuple[str, ...] = _SCAN_ROOTS) -> list[str]:
    """Return sorted leftover conffile paths (absolute)."""
    found: set[str] = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if any(name.endswith(suffix) for suffix in LEFTOVER_SUFFIXES):
                    found.add(os.path.join(dirpath, name))
    return sorted(found)


def collect_apt_conf_actions(limit: int = 100) -> list[str]:
    """Return recent apt/dpkg log lines about conffile actions (paths/messages only)."""
    candidates = ("/var/log/apt/term.log", "/var/log/dpkg.log")
    lines: list[str] = []
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf8", errors="replace") as handle:
                for line in handle:
                    if _APT_ACTION_RE.search(line):
                        lines.append(line.rstrip())
        except OSError:
            continue
        if lines:
            break
    if len(lines) > limit:
        return lines[-limit:]
    return lines


def high_interest_status() -> list[dict[str, Any]]:
    """Presence of known Cleep-touched paths + leftover siblings."""
    rows = []
    for path in HIGH_INTEREST_PATHS:
        entry = {
            "path": path,
            "exists": os.path.exists(path),
            "leftovers": [],
        }
        for suffix in (".dpkg-dist", ".dpkg-old", ".dpkg-new", ".ucf-dist"):
            leftover = path + suffix
            if os.path.exists(leftover):
                entry["leftovers"].append(leftover)
        rows.append(entry)
    return rows


def build_os_conf_report(
    *,
    from_version: Optional[str] = None,
    to_version: Optional[str] = None,
    report_path: str = DEFAULT_REPORT_PATH,
    scan_roots: tuple[str, ...] = _SCAN_ROOTS,
    cleepos_version_path: str = CLEEPOS_VERSION_PATH,
) -> dict[str, Any]:
    """
    Build a path-only OS upgrade conf report.

    Returns:
        dict with leftover_paths, leftover_count, apt_conf_actions, high_interest,
        text, generated_at, from_version, to_version, report_path
    """
    current = _safe_read_line(cleepos_version_path)
    if not to_version:
        to_version = current
    leftovers = find_leftover_paths(roots=scan_roots)
    apt_actions = collect_apt_conf_actions()
    interest = high_interest_status()
    generated_at = int(time.time())

    lines = [
        "=== CleepOs upgrade conf report ===",
        "privacy: paths and apt action lines only — no file contents",
        "from_version=%s" % (from_version or "?"),
        "to_version=%s" % (to_version or "?"),
        "cleepos_version_now=%s" % (current or "(missing)"),
        "generated_at=%s" % generated_at,
        "",
        "--- dpkg / ucf leftover conffiles ---",
        "# .dpkg-dist = package version kept aside (local file retained)",
        "# .dpkg-old  = previous local file when package version was installed",
        "# .dpkg-new  = package version not installed yet",
        "# .ucf-*     = ucf-managed conf conflicts",
    ]
    if not leftovers:
        lines.append("(none found)")
    else:
        for path in leftovers:
            lines.append(path)

    lines.extend(["", "--- apt log: config file actions ---"])
    if not apt_actions:
        lines.append("(no matching lines)")
    else:
        lines.extend(apt_actions)

    lines.extend(["", "--- high-interest paths ---"])
    for row in interest:
        if row["exists"]:
            extra = ""
            if row["leftovers"]:
                extra = " leftovers=" + ",".join(row["leftovers"])
            lines.append("present %s%s" % (row["path"], extra))
        else:
            lines.append("missing %s" % row["path"])

    lines.extend(
        [
            "",
            "--- leftover count ---",
            str(len(leftovers)),
            "",
        ]
    )
    text = "\n".join(lines) + "\n"

    parent = os.path.dirname(report_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(report_path, "w", encoding="utf8") as handle:
        handle.write(text)

    return {
        "generated_at": generated_at,
        "from_version": from_version,
        "to_version": to_version,
        "leftover_paths": leftovers,
        "leftover_count": len(leftovers),
        "apt_conf_actions": apt_actions,
        "high_interest": interest,
        "text": text,
        "report_path": report_path,
        "sent": False,
        "sent_at": None,
    }


def sentry_extra_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Subset safe for Sentry extras (no file bodies)."""
    return {
        "from_version": report.get("from_version"),
        "to_version": report.get("to_version"),
        "leftover_count": report.get("leftover_count", 0),
        "leftover_paths": list(report.get("leftover_paths") or []),
        "apt_conf_actions": list(report.get("apt_conf_actions") or [])[:50],
        "high_interest_with_leftovers": [
            row["path"]
            for row in (report.get("high_interest") or [])
            if row.get("leftovers")
        ],
    }
