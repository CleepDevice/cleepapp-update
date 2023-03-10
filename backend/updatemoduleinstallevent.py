#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class UpdateModuleInstallEvent(Event):
    """
    Update.module.install event
    """

    EVENT_NAME = "update.module.install"
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ["module", "status"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
