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

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

