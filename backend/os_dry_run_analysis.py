#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analyze apt dry-run / simulate output and local disk space.

Produces a list of findings and an OK/KO verdict for launching a real OS apply.
"""

import re
import shutil

__all__ = [
    "analyze_os_dry_run",
    "dry_run_errors_reportable_to_sentry",
    "format_analysis_section",
    "parse_apt_disk_delta_bytes",
    "parse_apt_summary_counts",
    "sentry_extra_from_dry_run_analysis",
]

# Insufficient local disk is a user-side constraint, not a CleepOs/playbook defect.
USER_DISK_SPACE_FINDING_CODES = frozenset({"disk_insufficient", "disk_tight"})

# Packages whose removal during a minor suite upgrade is a strong red flag
CRITICAL_PACKAGE_PREFIXES = (
    "cleep",
    "python3",
    "python3.9",
    "systemd",
    "raspberrypi-kernel",
    "raspberrypi-bootloader",
    "raspi-firmware",
    "libc6",
    "apt",
    "dpkg",
)

# Keep this much free space after the upgrade (bytes)
DISK_SAFETY_MARGIN_BYTES = 80 * 1024 * 1024

_DISK_USED_RE = re.compile(
    r"After this operation,\s*([\d.]+)\s*(kB|KB|MB|GB)\s+of additional disk space will be used",
    re.IGNORECASE,
)
_DISK_FREED_RE = re.compile(
    r"After this operation,\s*([\d.]+)\s*(kB|KB|MB|GB)\s+disk space will be freed",
    re.IGNORECASE,
)
_SUMMARY_RE = re.compile(
    r"(\d+)\s+upgraded,\s+(\d+)\s+newly installed,\s+(\d+)\s+to remove(?:,\s+(\d+)\s+not upgraded)?"
)
_NEED_ARCHIVES_RE = re.compile(
    r"Need to get\s+(.+?)\s+of archives",
    re.IGNORECASE,
)


def _unit_to_bytes(value, unit):
    unit = (unit or "").upper()
    amount = float(value)
    if unit in ("KB", "K"):
        return int(amount * 1024)
    if unit == "MB":
        return int(amount * 1024 * 1024)
    if unit == "GB":
        return int(amount * 1024 * 1024 * 1024)
    return int(amount)


def parse_apt_disk_delta_bytes(text):
    """
    Return signed disk delta in bytes from apt simulate text.

    Positive = additional space used; negative = space freed; None if unknown.
    """
    if not text:
        return None
    match = _DISK_USED_RE.search(text)
    if match:
        return _unit_to_bytes(match.group(1), match.group(2))
    match = _DISK_FREED_RE.search(text)
    if match:
        return -_unit_to_bytes(match.group(1), match.group(2))
    return None


def parse_apt_summary_counts(text):
    """
    Parse classic apt summary counts from text.

    Returns:
        dict|None: upgraded, newly_installed, to_remove, not_upgraded
    """
    if not text:
        return None
    match = _SUMMARY_RE.search(text)
    if not match:
        return None
    return {
        "upgraded": int(match.group(1)),
        "newly_installed": int(match.group(2)),
        "to_remove": int(match.group(3)),
        "not_upgraded": int(match.group(4) or 0),
    }


def _format_bytes(num_bytes):
    if num_bytes is None:
        return "unknown"
    sign = "-" if num_bytes < 0 else ""
    value = abs(num_bytes)
    if value >= 1024 * 1024 * 1024:
        return "%s%.1f GB" % (sign, value / (1024 * 1024 * 1024))
    if value >= 1024 * 1024:
        return "%s%.1f MB" % (sign, value / (1024 * 1024))
    if value >= 1024:
        return "%s%.1f kB" % (sign, value / 1024)
    return "%s%d B" % (sign, value)


def _collect_remv_packages(text):
    packages = []
    for line in (text or "").splitlines():
        if line.startswith("Remv "):
            parts = line.split()
            if len(parts) >= 2:
                packages.append(parts[1])
    return packages


def _is_critical_package(name):
    base = name.split(":")[0].lower()
    for prefix in CRITICAL_PACKAGE_PREFIXES:
        if base == prefix or base.startswith(prefix + "-"):
            return True
    return False


def analyze_os_dry_run(text, *, free_bytes=None, path="/"):
    """
    Analyze apt simulate preview and disk free space.

    Args:
        text (str): apt simulate / dry-run preview text
        free_bytes (int|None): free bytes on path (auto-detect if None)
        path (str): filesystem path for disk_usage

    Returns:
        dict::

            {
                verdict (str): "ok" or "ko"
                findings (list): [{severity, code, message}, ...]
                disk (dict): free/needed/after/margin details
                counts (dict|None): apt summary counts
            }
    """
    findings = []
    text = text or ""

    if free_bytes is None:
        try:
            free_bytes = shutil.disk_usage(path).free
        except OSError:
            free_bytes = None
            findings.append(
                {
                    "severity": "warning",
                    "code": "disk_unknown",
                    "message": "Unable to read free disk space on %s" % path,
                }
            )

    needed = parse_apt_disk_delta_bytes(text)
    counts = parse_apt_summary_counts(text)
    disk = {
        "path": path,
        "free_bytes": free_bytes,
        "free_label": _format_bytes(free_bytes),
        "needed_bytes": needed,
        "needed_label": _format_bytes(needed) if needed is not None else None,
        "after_bytes": None,
        "after_label": None,
        "margin_bytes": DISK_SAFETY_MARGIN_BYTES,
    }
    if free_bytes is not None and needed is not None:
        after = free_bytes - max(needed, 0)
        disk["after_bytes"] = after
        disk["after_label"] = _format_bytes(after)
        if needed > 0 and needed > free_bytes:
            findings.append(
                {
                    "severity": "error",
                    "code": "disk_insufficient",
                    "message": (
                        "Not enough free disk space: apt needs %s more but only %s is free on %s"
                        % (disk["needed_label"], disk["free_label"], path)
                    ),
                }
            )
        elif needed > 0 and after < DISK_SAFETY_MARGIN_BYTES:
            findings.append(
                {
                    "severity": "error",
                    "code": "disk_tight",
                    "message": (
                        "Disk space would be critically low after upgrade "
                        "(%s free now, %s needed, ~%s left; safety margin %s)"
                        % (
                            disk["free_label"],
                            disk["needed_label"],
                            disk["after_label"],
                            _format_bytes(DISK_SAFETY_MARGIN_BYTES),
                        )
                    ),
                }
            )
        elif needed > 0:
            findings.append(
                {
                    "severity": "info",
                    "code": "disk_ok",
                    "message": (
                        "Disk space looks OK (%s free, %s needed, ~%s remaining)"
                        % (disk["free_label"], disk["needed_label"], disk["after_label"])
                    ),
                }
            )
        elif needed < 0:
            findings.append(
                {
                    "severity": "info",
                    "code": "disk_freed",
                    "message": "Upgrade would free about %s" % _format_bytes(-needed),
                }
            )
    elif needed is None:
        findings.append(
            {
                "severity": "warning",
                "code": "disk_delta_unknown",
                "message": (
                    'Apt did not report "After this operation, … disk space…" — '
                    "cannot verify free space vs upgrade size"
                ),
            }
        )

    lower = text.lower()
    if "held broken packages" in lower or "unmet dependencies" in lower:
        findings.append(
            {
                "severity": "error",
                "code": "broken_deps",
                "message": "Apt reports broken/unmet dependencies in the simulation",
            }
        )
    if "you have held packages" in lower or "kept back" in lower:
        findings.append(
            {
                "severity": "warning",
                "code": "held_packages",
                "message": "Some packages appear held back — upgrade may be incomplete",
            }
        )
    if re.search(r"^E: ", text, re.MULTILINE):
        findings.append(
            {
                "severity": "error",
                "code": "apt_error_lines",
                "message": "Apt simulation contains error lines (E: …)",
            }
        )

    remv = _collect_remv_packages(text)
    critical_removals = [pkg for pkg in remv if _is_critical_package(pkg)]
    if critical_removals:
        findings.append(
            {
                "severity": "error",
                "code": "critical_removal",
                "message": (
                    "Simulation would remove critical package(s): %s"
                    % ", ".join(critical_removals[:12])
                ),
            }
        )
    elif counts and counts.get("to_remove", 0) >= 20:
        findings.append(
            {
                "severity": "warning",
                "code": "many_removals",
                "message": "Simulation removes %s packages — review Remv lines carefully"
                % counts["to_remove"],
            }
        )

    if counts:
        if (
            counts["upgraded"] == 0
            and counts["newly_installed"] == 0
            and counts["to_remove"] == 0
        ):
            findings.append(
                {
                    "severity": "info",
                    "code": "no_package_changes",
                    "message": (
                        "No package changes vs apt mirrors — Apply would mostly stamp "
                        "/etc/cleepos_version"
                    ),
                }
            )
        else:
            findings.append(
                {
                    "severity": "info",
                    "code": "summary",
                    "message": (
                        "%s upgraded, %s newly installed, %s to remove"
                        % (
                            counts["upgraded"],
                            counts["newly_installed"],
                            counts["to_remove"],
                        )
                    ),
                }
            )

    archives = _NEED_ARCHIVES_RE.search(text)
    if archives:
        findings.append(
            {
                "severity": "info",
                "code": "download_size",
                "message": "Need to download %s of archives" % archives.group(1).strip(),
            }
        )

    has_error = any(item["severity"] == "error" for item in findings)
    verdict = "ko" if has_error else "ok"

    return {
        "verdict": verdict,
        "findings": findings,
        "disk": disk,
        "counts": counts,
    }


def dry_run_errors_reportable_to_sentry(analysis):
    """
    Return error-level findings that should be sent to Sentry (excludes user disk space).
    """
    if not analysis:
        return []
    reportable = []
    for item in analysis.get("findings") or []:
        if item.get("severity") != "error":
            continue
        if item.get("code") in USER_DISK_SPACE_FINDING_CODES:
            continue
        reportable.append(item)
    return reportable


def sentry_extra_from_dry_run_analysis(
    analysis,
    *,
    from_version=None,
    to_version=None,
    runner_error=None,
):
    """Subset safe for Sentry extras (no full apt log)."""
    findings = dry_run_errors_reportable_to_sentry(analysis)
    return {
        "from_version": from_version,
        "to_version": to_version,
        "verdict": (analysis or {}).get("verdict"),
        "runner_error": runner_error,
        "reportable_finding_codes": [item.get("code") for item in findings],
        "reportable_findings": [
            {"code": item.get("code"), "message": item.get("message")}
            for item in findings[:20]
        ],
        "disk": (analysis or {}).get("disk"),
        "counts": (analysis or {}).get("counts"),
    }


def format_analysis_section(analysis):
    """Return a text block to append to the dry-run preview."""
    lines = [
        "=== assessment ===",
        "verdict=%s" % analysis.get("verdict", "?").upper(),
    ]
    disk = analysis.get("disk") or {}
    if disk.get("free_label") or disk.get("needed_label"):
        lines.append(
            "disk: free=%s needed=%s after≈%s"
            % (
                disk.get("free_label") or "?",
                disk.get("needed_label") or "?",
                disk.get("after_label") or "?",
            )
        )
    lines.append("")
    lines.append("=== findings ===")
    findings = analysis.get("findings") or []
    if not findings:
        lines.append("(none)")
    else:
        for item in findings:
            lines.append(
                "[%s] %s" % ((item.get("severity") or "?").upper(), item.get("message"))
            )
    lines.append("")
    lines.append(
        "Note: leftover .dpkg-* / .ucf-* files still cannot be predicted without a real Apply."
    )
    return "\n".join(lines) + "\n"
