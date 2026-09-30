#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CleepOs identity from /etc/cleepos_version (same idea as /etc/debian_version).

Expected file content: one line, suite + image date, e.g.::

    bullseye20231205

Packer (or a manual drop on older devices) must create this file.
"""

import re

CLEEPOS_VERSION_PATH = "/etc/cleepos_version"
# suite name + YYYYMMDD build stamp (matches CleepOs tag suffix style)
_CLEEPOS_VERSION_RE = re.compile(r"^([a-z]+)(\d{8})$")


def read_cleepos_version(path=CLEEPOS_VERSION_PATH):
    """
    Read CleepOs version string from disk.

    Args:
        path (str): path to cleepos_version file

    Returns:
        str: stripped version (e.g. bullseye20231205)
    """
    with open(path, "r", encoding="utf8") as version_file:
        return version_file.read().strip()


def parse_cleepos_version(version):
    """
    Split a CleepOs version into suite and build date.

    Args:
        version (str): e.g. bullseye20231205

    Returns:
        dict: { version, suite, build }

    Raises:
        ValueError: if format is invalid
    """
    match = _CLEEPOS_VERSION_RE.match(version)
    if not match:
        raise ValueError(
            f'Invalid CleepOs version "{version}", expected <suite><YYYYMMDD> '
            f'(e.g. bullseye20231205)'
        )
    return {
        "version": version,
        "suite": match.group(1),
        "build": match.group(2),
    }


def get_os_identity(path=CLEEPOS_VERSION_PATH):
    """
    Return full OS identity from /etc/cleepos_version.

    Returns:
        dict: { version, suite, build }
    """
    return parse_cleepos_version(read_cleepos_version(path))
