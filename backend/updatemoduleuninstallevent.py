#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class UpdateModuleUninstallEvent(Event):
    """
    Update.module.uninstall event
    """

    EVENT_NAME = u'update.module.uninstall'
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ['module', 'status']

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

