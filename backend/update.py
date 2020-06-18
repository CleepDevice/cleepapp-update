#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.exception import MissingParameter, InvalidParameter, CommandError
from cleep.core import CleepModule

class Update(CleepModule):
    """
    Update application
    """
    MODULE_AUTHOR = u'TODO'
    MODULE_VERSION = u'0.0.0'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'TODO'
    MODULE_LONGDESCRIPTION = u'TODO'
    MODULE_TAGS = []
    MODULE_CATEGORY = u'TODO'
    MODULE_COUNTRY = None
    MODULE_URLINFO = None
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = None

    MODULE_CONFIG_FILE = u'update.conf'
    DEFAULT_CONFIG = {}

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Params:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

    def _configure(self):
        """
        Configure module
        """
        # launch here custom thread or action that takes time to process
        pass

    def _stop(self):
        """
        Stop module
        """
        # stop here your custom threads or close external connections
        pass

    def event_received(self, event):
        """
        Event received

        Params:
            event (MessageRequest): event data
        """
        # execute here actions when you receive an event:
        #  - on time event => cron task
        #  - on alert event => send email or push message
        #  - ...
        pass
    
