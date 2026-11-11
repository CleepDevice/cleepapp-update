#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class UpdateModuleFirmwareEvent(Event):
    """
    Fired after a successful module install when Pico firmwares were installed.

    Propagated on the external bus so cleep-desktop can offer flashing
    (desktop dedupes by firmware hash).

    Params:
        module (str): installed application name
        firmwares (list): firmware descriptors with relative download urls::

            [
                {
                    id, hash, name, app, firmware_version, kind, date,
                    targets, requires_bootsel, description,
                    urls: {zip, manifest}  # paths under /firmware/<app>/
                },
                ...
            ]
    """

    EVENT_NAME = "update.module.firmware"
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ["module", "firmwares"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
