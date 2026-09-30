#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CleepOs update catalog (local JSON for Phase 0).

Shape::

    {
      "latest_by_suite": {
        "bullseye": "bullseye20250831"
      },
      "releases": {
        "bullseye20250831": {
          "suite": "bullseye",
          "min_cleep_version": "0.1.2",
          "blocks_cleep_update": false,
          "playbook_url": null,
          "playbook_sha256": null,
          "changelog": "..."
        }
      }
    }
"""

import json
import os

try:
    from .os_identity import parse_cleepos_version
except ImportError:  # pragma: no cover - flat import in tests / module loader
    from os_identity import parse_cleepos_version

DEFAULT_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "os-catalog.json")


def load_os_catalog(path=DEFAULT_CATALOG_PATH):
    """
    Load OS catalog from JSON file.

    Args:
        path (str): catalog file path

    Returns:
        dict: catalog content
    """
    with open(path, "r", encoding="utf8") as catalog_file:
        return json.load(catalog_file)


def is_cleepos_newer(current_version, candidate_version):
    """
    Return True if candidate CleepOs version is strictly newer than current.

    Both versions must share the same suite; comparison uses the YYYYMMDD build.
    """
    current = parse_cleepos_version(current_version)
    candidate = parse_cleepos_version(candidate_version)
    if current["suite"] != candidate["suite"]:
        return False
    return int(candidate["build"]) > int(current["build"])


def _is_cleep_newer(old_version, new_version):
    """
    Return True if new_version is strictly greater than old_version (x.y.z).
    """
    old_parts = tuple(int(part) for part in old_version.split("."))
    new_parts = tuple(int(part) for part in new_version.split("."))
    if len(old_parts) != 3 or len(new_parts) != 3:
        raise ValueError("Cleep versions must use 3 digits (x.y.z)")
    return new_parts > old_parts


def evaluate_os_update(identity, catalog, cleep_version):
    """
    Compare device identity against catalog and Cleep core version.

    Args:
        identity (dict): from get_os_identity()
        catalog (dict): loaded catalog
        cleep_version (str): running Cleep core version (x.y.z)

    Returns:
        dict::

            {
                updatable (bool),
                version (str|None): latest available for suite,
                current (str),
                suite (str),
                changelog (str|None),
                playbook_url (str|None),
                playbook_sha256 (str|None),
                min_cleep_version (str|None),
                blocks_cleep_update (bool),
                cleep_too_old (bool): True if OS update exists but Cleep is below min
            }
    """
    suite = identity["suite"]
    current = identity["version"]
    latest = catalog.get("latest_by_suite", {}).get(suite)
    empty = {
        "updatable": False,
        "version": None,
        "current": current,
        "suite": suite,
        "changelog": None,
        "playbook_url": None,
        "playbook_sha256": None,
        "min_cleep_version": None,
        "blocks_cleep_update": False,
        "cleep_too_old": False,
    }
    if not latest:
        return empty

    release = catalog.get("releases", {}).get(latest, {})
    min_cleep = release.get("min_cleep_version")
    cleep_too_old = False
    if min_cleep:
        # True when installed Cleep is strictly older than required min
        cleep_too_old = _is_cleep_newer(cleep_version, min_cleep)

    newer = is_cleepos_newer(current, latest)
    updatable = newer and not cleep_too_old

    return {
        "updatable": updatable,
        "version": latest if newer else None,
        "current": current,
        "suite": suite,
        "changelog": release.get("changelog") if newer else None,
        "playbook_url": release.get("playbook_url") if newer else None,
        "playbook_sha256": release.get("playbook_sha256") if newer else None,
        "min_cleep_version": min_cleep,
        "blocks_cleep_update": bool(release.get("blocks_cleep_update")) if newer else False,
        "cleep_too_old": bool(cleep_too_old and newer),
    }
