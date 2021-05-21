#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class UpdateCleepUpdateEvent(Event):
    """
    Update.cleep.update event
    """

    EVENT_NAME = 'update.cleep.update'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['status']

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

