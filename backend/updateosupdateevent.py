#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class UpdateOsUpdateEvent(Event):
    """
    update.os.update event
    """

    EVENT_NAME = "update.os.update"
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ["status", "progress", "phase"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
