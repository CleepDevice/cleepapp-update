#!/usr/bin/env python
# -*- coding: utf-8 -*-

def compare_versions(old_version, new_version, strict=True): # pragma: no cover
    """
    Compare specified version and return True if new version is strictly greater than old one

    Args:
        old_version (string): old version
        new_version (string): new version
        strict (bool): True to perform strict check (<). False to perform a permissive check (<=)

    Returns:
        bool: True if new version available
    """
    # check versions
    old_vers = tuple(map(int, (old_version.split('.'))))
    if len(old_vers)!=3:
        raise Exception('Invalid version "%s" format, only 3 digits format allowed' % old_version)

    new_vers = tuple(map(int, (new_version.split('.'))))
    if len(new_vers)!=3:
        raise Exception('Invalid version "%s" format, only 3 digits format allowed' % new_version)

    # compare version
    if (strict and old_vers < new_vers) or (not strict and old_vers <= new_vers):
        return True

    return False

