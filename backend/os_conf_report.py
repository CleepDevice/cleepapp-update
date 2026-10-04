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

IMPORTANT_PATHS = (
    "/etc/wpa_supplicant/wpa_supplicant.conf",
    "/etc/wpa_supplicant/wpa_supplicant-wlan0.conf",
    "/etc/dhcpcd.conf",
    "/etc/ssh/sshd_config",
    "/etc/systemd/journald.conf",
    "/etc/nsswitch.conf",
    "/etc/hosts",
    "/etc/hostname",
    "/etc/timezone",
    "/etc/localtime",
    "/boot/config.txt",
    "/boot/cmdline.txt",
)

_SCAN_ROOTS = ("/etc", "/boot")
_NEW_CONF_RE = re.compile(r"Installing new version of config file (.+) \.\.\.")
_KEPT_CONF_RE = re.compile(
    r"Not replacing|existing configuration",
    re.IGNORECASE,
)


def _safe_read_line(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf8", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return None


def _leftover_kind(path: str) -> str:
    if path.endswith(".dpkg-dist"):
        return "local-kept (package aside)"
    if path.endswith(".dpkg-old"):
        return "package-installed (old aside)"
    if path.endswith(".dpkg-new"):
        return "package-pending"
    if ".ucf-" in os.path.basename(path):
        return "ucf-conflict"
    return "leftover"


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


def collect_new_config_paths(limit: int = 100) -> list[str]:
    """Paths from apt 'Installing new version of config file' lines."""
    candidates = ("/var/log/apt/term.log", "/var/log/dpkg.log")
    found: list[str] = []
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf8", errors="replace") as handle:
                for line in handle:
                    match = _NEW_CONF_RE.search(line)
                    if match:
                        found.append(match.group(1).strip())
        except OSError:
            continue
        if found:
            break
    # unique preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[-limit:]


def collect_apt_conf_actions(limit: int = 100) -> list[str]:
    """Legacy helper: raw apt conf-related lines (paths/messages only)."""
    candidates = ("/var/log/apt/term.log", "/var/log/dpkg.log")
    lines: list[str] = []
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf8", errors="replace") as handle:
                for line in handle:
                    if _NEW_CONF_RE.search(line) or _KEPT_CONF_RE.search(line):
                        lines.append(line.rstrip())
        except OSError:
            continue
        if lines:
            break
    return lines[-limit:]


def important_paths_status() -> list[dict[str, Any]]:
    """Presence of known Cleep-touched paths + leftover siblings."""
    rows = []
    for path in IMPORTANT_PATHS:
        entry = {
            "path": path,
            "exists": os.path.exists(path) or os.path.islink(path),
            "leftovers": [],
        }
        for suffix in (".dpkg-dist", ".dpkg-old", ".dpkg-new", ".ucf-dist"):
            leftover = path + suffix
            if os.path.exists(leftover):
                entry["leftovers"].append(leftover)
        rows.append(entry)
    return rows


# Back-compat alias
high_interest_status = important_paths_status
HIGH_INTEREST_PATHS = IMPORTANT_PATHS


def build_os_conf_report(
    *,
    from_version: Optional[str] = None,
    to_version: Optional[str] = None,
    report_path: str = DEFAULT_REPORT_PATH,
    scan_roots: tuple[str, ...] = _SCAN_ROOTS,
    cleepos_version_path: str = CLEEPOS_VERSION_PATH,
    apt_summary: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build a path-only OS upgrade conf report.

    Returns:
        dict with leftover_paths, leftover_count, new_config_paths, important paths,
        text, generated_at, from_version, to_version, report_path
    """
    current = _safe_read_line(cleepos_version_path)
    if not to_version:
        to_version = current
    leftovers = find_leftover_paths(roots=scan_roots)
    new_configs = collect_new_config_paths()
    apt_actions = collect_apt_conf_actions()
    important = important_paths_status()
    generated_at = int(time.time())
    if apt_summary is None:
        apt_summary = "(unavailable)"

    lines = [
        "=============================================",
        "CleepOs upgrade conf report",
        "source_cleepos_seed=%s" % (from_version or "?"),
        "target_cleepos=%s" % (to_version or "?"),
        "cleepos_version_now=%s" % (current or "(missing)"),
        "generated_at=%s" % generated_at,
        "privacy: paths only — no file contents / no diffs",
        "=============================================",
        "",
        "--- apt summary ---",
        apt_summary,
        "",
        "--- new config files ---",
        "# Package version installed (no local customization detected by dpkg)",
    ]
    if not new_configs:
        lines.append("(none)")
    else:
        lines.extend(new_configs)

    lines.extend(
        [
            "",
            "--- existing config files ---",
            "# Leftover siblings after upgrade (paths only — no file contents / no diffs)",
            "# .dpkg-dist = local file kept; package version saved aside",
            "# .dpkg-old  = package version installed; previous local saved aside",
            "# .dpkg-new  = package version not applied yet",
            "# .ucf-*     = ucf-managed conflict",
        ]
    )
    if not leftovers:
        lines.append("(none)")
    else:
        for path in leftovers:
            lines.append("%s  [%s]" % (path, _leftover_kind(path)))

    lines.extend(
        [
            "",
            "--- important config files ---",
            "# Watchlist of paths typically owned/touched by CleepOs / Cleep",
        ]
    )
    for row in important:
        if row["exists"]:
            lines.append("present %s" % row["path"])
            for leftover in row["leftovers"]:
                lines.append("  leftover: %s" % leftover)
        else:
            lines.append("missing %s" % row["path"])

    lines.extend(["", "--- summary ---"])
    attention = False
    if current and to_version and current != to_version:
        lines.append(
            "ERROR: /etc/cleepos_version is '%s' (expected %s)" % (current, to_version)
        )
        attention = True
    else:
        lines.append("OK: /etc/cleepos_version=%s" % (current or "(missing)"))
    lines.append("INFO: apt → %s" % apt_summary)
    if new_configs:
        lines.append(
            "INFO: %s new config file(s) installed from packages" % len(new_configs)
        )
    else:
        lines.append("INFO: no new config files installed from packages")
    if leftovers:
        lines.append(
            "WARN: %s leftover conf sibling(s) — review --- existing config files ---"
            % len(leftovers)
        )
        for path in leftovers:
            lines.append("  - %s" % path)
        attention = True
    else:
        lines.append("OK: no .dpkg-*/.ucf-* leftovers under /etc and /boot")
    for row in important:
        if not row["exists"] and row["path"] != "/etc/localtime":
            lines.append("WARN: important path missing: %s" % row["path"])
            attention = True
        elif not row["exists"] and row["path"] == "/etc/localtime":
            lines.append(
                "NOTE: missing /etc/localtime (often expected if tzdata symlink absent)"
            )
        for leftover in row["leftovers"]:
            lines.append("WARN: important path has leftover: %s" % leftover)
            attention = True
    if attention:
        lines.append("RESULT: manual review recommended (see WARN/ERROR above)")
    else:
        lines.append(
            "RESULT: nothing critical for manual investigation "
            "(beyond routine package conf installs)"
        )
    lines.append("")
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
        "new_config_paths": new_configs,
        "apt_conf_actions": apt_actions,
        "high_interest": important,
        "important": important,
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
        "new_config_paths": list(report.get("new_config_paths") or [])[:50],
        "high_interest_with_leftovers": [
            row["path"]
            for row in (report.get("high_interest") or report.get("important") or [])
            if row.get("leftovers")
        ],
    }
