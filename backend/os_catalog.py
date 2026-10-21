#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CleepOs update catalog (remote os-versions.json from CleepDevice/cleep-os).

Remote source of truth: ``os-versions.json``.
Playbooks live under ``playbooks/<suite>-minor/run.sh`` on the same repo.

Shape::

    {
      "min_suite": "bullseye",
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

import hashlib
import json
import logging
import os

try:
    from .os_identity import parse_cleepos_version
except ImportError:  # pragma: no cover - flat import in tests / module loader
    from os_identity import parse_cleepos_version

__all__ = [
    "CACHE_CATALOG_PATH",
    "PLAYBOOK_CACHE_DIR",
    "REMOTE_OS_VERSIONS_URL",
    "SUITE_ORDER",
    "default_playbook_url",
    "ensure_os_playbook",
    "evaluate_os_update",
    "fetch_os_catalog",
    "is_cleepos_newer",
    "is_suite_older_than",
    "load_os_catalog",
    "resolve_playbook_url",
]

# Debian / Raspberry Pi OS suite order (major OS generations)
SUITE_ORDER = (
    "buster",
    "bullseye",
    "bookworm",
    "trixie",
    "forky",
)

logger = logging.getLogger("OsCatalog")

# Cached copy of remote os-versions.json (tmpfs; always writable)
CACHE_CATALOG_PATH = "/tmp/cleep/os-versions.json"

# Remote catalog on CleepDevice/cleep-os (default branch is master)
REMOTE_OS_VERSIONS_URL = (
    "https://raw.githubusercontent.com/CleepDevice/cleep-os/master/os-versions.json"
)

# Default playbook when release.playbook_url is null
PLAYBOOK_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/CleepDevice/cleep-os/master/"
    "playbooks/%(suite)s-minor/run.sh"
)
PLAYBOOK_CACHE_DIR = "/tmp/cleep/os-playbooks"


def load_os_catalog(path):
    """
    Load OS catalog from a local JSON file.

    Args:
        path (str): catalog file path

    Returns:
        dict: catalog content
    """
    with open(path, "r", encoding="utf8") as catalog_file:
        return json.load(catalog_file)


def _is_valid_catalog(catalog):
    return isinstance(catalog, dict) and "latest_by_suite" in catalog and "releases" in catalog


def _write_cache(path, text):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf8") as handle:
        handle.write(text)


def fetch_os_catalog(download_content=None, *, remote_url=None, cache_path=None):
    """
    Load catalog from remote os-versions.json, falling back to the last downloaded cache.

    Args:
        download_content (callable|None): ``download_content(url) -> str|None``
            When None, only the cache is used (no network).
        remote_url (str|None): override remote URL
        cache_path (str|None): override cache path

    Returns:
        dict: catalog content

    Raises:
        Exception: if remote and cache are both unavailable/invalid
    """
    remote_url = remote_url or REMOTE_OS_VERSIONS_URL
    cache_path = cache_path or CACHE_CATALOG_PATH

    if download_content is not None:
        try:
            raw = download_content(remote_url)
            if raw:
                catalog = json.loads(raw)
                if _is_valid_catalog(catalog):
                    try:
                        _write_cache(
                            cache_path,
                            raw if isinstance(raw, str) else raw.decode("utf8"),
                        )
                    except OSError:
                        logger.warning("Unable to cache os-versions.json", exc_info=True)
                    logger.info("Loaded OS catalog from remote %s", remote_url)
                    return catalog
                logger.warning("Remote OS catalog has invalid format")
        except Exception:
            logger.warning("Unable to fetch remote OS catalog", exc_info=True)

    if os.path.isfile(cache_path):
        try:
            catalog = load_os_catalog(cache_path)
            if _is_valid_catalog(catalog):
                logger.info("Loaded OS catalog from cache %s", cache_path)
                return catalog
        except Exception:
            logger.warning("Unable to read cached OS catalog", exc_info=True)

    raise Exception(
        "Unable to load OS catalog (remote os-versions.json unavailable and no local cache)"
    )


def default_playbook_url(suite):
    """Return default remote playbook URL for a Debian suite."""
    return PLAYBOOK_URL_TEMPLATE % {"suite": suite}


def resolve_playbook_url(suite, playbook_url=None):
    """
    Resolve playbook URL: explicit catalog value, else suite default on cleep-os.
    """
    if playbook_url:
        return playbook_url
    if not suite:
        return None
    return default_playbook_url(suite)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_os_playbook(
    suite,
    playbook_url=None,
    playbook_sha256=None,
    download_content=None,
    *,
    cache_dir=None,
):
    """
    Ensure a local ``run.sh`` playbook is available (download + cache).

    Args:
        suite (str): Debian suite (e.g. bullseye)
        playbook_url (str|None): remote URL (resolved from suite if None)
        playbook_sha256 (str|None): optional hex digest to verify
        download_content (callable|None): ``download_content(url) -> str|None``
        cache_dir (str|None): directory for cached playbooks

    Returns:
        str: absolute path to local run.sh

    Raises:
        Exception: if remote download fails and no valid cache exists
    """
    cache_dir = cache_dir or PLAYBOOK_CACHE_DIR
    url = resolve_playbook_url(suite, playbook_url)
    if not url:
        raise Exception("OS playbook URL is missing (suite=%s)" % suite)

    local_dir = os.path.join(cache_dir, "%s-minor" % suite)
    local_path = os.path.join(local_dir, "run.sh")

    if download_content is not None:
        try:
            raw = download_content(url)
            if raw:
                text = raw if isinstance(raw, str) else raw.decode("utf8")
                if not text.lstrip().startswith("#!"):
                    raise Exception(
                        "Downloaded playbook does not look like a shell script"
                    )
                os.makedirs(local_dir, exist_ok=True)
                with open(local_path, "w", encoding="utf8") as handle:
                    handle.write(text)
                os.chmod(local_path, 0o755)
                if playbook_sha256:
                    digest = _sha256_file(local_path)
                    if digest.lower() != playbook_sha256.lower():
                        os.unlink(local_path)
                        raise Exception(
                            "Playbook sha256 mismatch (got %s, expected %s)"
                            % (digest, playbook_sha256)
                        )
                logger.info("Cached OS playbook from %s -> %s", url, local_path)
                return local_path
        except Exception:
            logger.warning("Unable to download OS playbook from %s", url, exc_info=True)

    if os.path.isfile(local_path):
        if playbook_sha256:
            try:
                digest = _sha256_file(local_path)
                if digest.lower() == playbook_sha256.lower():
                    logger.info("Using cached OS playbook %s", local_path)
                    return local_path
            except OSError:
                pass
        else:
            logger.info("Using cached OS playbook %s", local_path)
            return local_path

    raise Exception(
        "Unable to load OS playbook (remote unavailable and no local cache for %s)"
        % url
    )


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


def is_suite_older_than(suite, min_suite):
    """
    Return True if ``suite`` is strictly older than ``min_suite`` (major OS generation).

    Unknown suites are treated as not older (no block).
    """
    if not suite or not min_suite or suite == min_suite:
        return False
    try:
        return SUITE_ORDER.index(suite) < SUITE_ORDER.index(min_suite)
    except ValueError:
        return False


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
                min_suite (str|None): catalog minimum suite for new Cleep installs,
                changelog (str|None),
                playbook_url (str|None),
                playbook_sha256 (str|None),
                min_cleep_version (str|None),
                blocks_cleep_update (bool): True if Cleep update must wait (major suite
                    too old, or optional per-release same-suite flag),
                os_suite_too_old (bool): True when device suite < catalog min_suite,
                cleep_too_old (bool): True if OS update exists but Cleep is below min
            }
    """
    suite = identity["suite"]
    current = identity["version"]
    min_suite = catalog.get("min_suite") or None
    suite_too_old = is_suite_older_than(suite, min_suite) if min_suite else False
    latest = catalog.get("latest_by_suite", {}).get(suite)
    empty = {
        "updatable": False,
        "version": None,
        "current": current,
        "suite": suite,
        "min_suite": min_suite,
        "changelog": None,
        "playbook_url": None,
        "playbook_sha256": None,
        "min_cleep_version": None,
        "blocks_cleep_update": suite_too_old,
        "os_suite_too_old": suite_too_old,
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

    playbook_url = None
    playbook_sha256 = None
    if newer:
        playbook_url = resolve_playbook_url(suite, release.get("playbook_url"))
        playbook_sha256 = release.get("playbook_sha256")

    # Major: suite behind catalog min_suite. Minor same-suite: optional release flag.
    blocks = suite_too_old or (
        bool(release.get("blocks_cleep_update")) if newer else False
    )

    return {
        "updatable": updatable,
        "version": latest if newer else None,
        "current": current,
        "suite": suite,
        "min_suite": min_suite,
        "changelog": release.get("changelog") if newer else None,
        "playbook_url": playbook_url,
        "playbook_sha256": playbook_sha256,
        "min_cleep_version": min_cleep,
        "blocks_cleep_update": blocks,
        "os_suite_too_old": suite_too_old,
        "cleep_too_old": bool(cleep_too_old and newer),
    }
