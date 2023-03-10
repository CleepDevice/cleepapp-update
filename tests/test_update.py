#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
import copy
sys.path.append('../')
from backend.update import Update
from backend.updatecleepupdateevent import UpdateCleepUpdateEvent
from backend.updatemoduleinstallevent import UpdateModuleInstallEvent
from backend.updatemoduleuninstallevent import UpdateModuleUninstallEvent
from backend.updatemoduleupdateevent import UpdateModuleUpdateEvent
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized, CommandInfo
from cleep.libs.tests import session
from cleep.common import MessageResponse
from cleep.libs.internals.installcleep import InstallCleep
from cleep.libs.internals.install import Install
from mock import Mock, patch, MagicMock, call, PropertyMock, mock_open

MODULES_JSON = {
    "list": {
        "actions":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat":"cleep<=1.2.3", "country": None,"deps":[],"description":"Interact with other modules to trigger custom actions","download":"https://github.com/CleepDevice/cleepmod-actions/releases/download/v1.0.1/cleepmod_actions_1.0.1.zip","icon":"play-box-outline","longdescription":"","note":-1,"price":0,"sha256":"d2d38835c193fa9bd37311d5ec08f780d053ff4879e8a7b05c7d773ca1f25a81","tags":["action","skill","script","trigger","python","cron"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-actions/issues","help":"https://github.com/CleepDevice/cleepmod-actions/wiki","info":"https://github.com/CleepDevice/cleepmod-actions","site": None},"version":"1.0.1"},
        "audio":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"Configure audio on your device","download":"https://github.com/CleepDevice/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip","icon":"speaker","longdescription":"","note":-1,"price":0,"sha256":"cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab","tags":["audio","sound"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-audio/issues","help":"https://github.com/CleepDevice/cleepmod-audio/wiki","info":"https://github.com/CleepDevice/cleepmod-audio","site": None},"version":"1.1.0"},
        "charts":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-charts/releases/download/v1.0.0/cleepmod_charts_1.0.0.zip","icon":"chart-areaspline","longdescription":"","note":-1,"price":0,"sha256":"00625651423636e7087a3cfa422929440858781585138d273120e87c61bea46c","tags":["sensors","graphs","charts","database"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-charts/issues","help":"https://github.com/CleepDevice/cleepmod-charts/wiki","info":"https://github.com/CleepDevice/cleepmod-charts","site": None},"version":"1.0.0"},
        "cleepbus":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-cleepbus/releases/download/v1.1.1/cleepmod_cleepbus_1.1.1.zip","icon":"bus","longdescription":"","note":-1,"price":0,"sha256":"55b435169af8bac7cc06446d4f0ffcadb49ef2118d5eeaa04eaffa77f68f4b9c","tags":["bus","communication"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-cleepbus/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-cleepbus/wiki/CleepBus-module","site": None},"version":"1.1.1"},
        "developer":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-developer/releases/download/v2.2.0/cleepmod_developer_2.2.0.zip","icon":"worker","longdescription":"","note":-1,"price":0,"sha256":"8550046516ece9d61446590fa9d96dc2ac88334adadcc15a7605ac3654b6d1f4","tags":["developer","python","cleepos","module","angularjs","cleep","cli","test","documentation"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-developer/issues","help":"https://github.com/CleepDevice/cleepmod-developer/wiki","info":"https://github.com/CleepDevice/cleepmod-developer","site": None},"version":"2.2.0"},
        "gpios":{"author":"Cleep","category":"DRIVER","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"Configure your raspberry pins","download":"https://github.com/CleepDevice/cleepmod-gpios/releases/download/v1.1.0/cleepmod_gpios_1.1.0.zip","icon":"drag-horizontal","longdescription":"","note":-1,"price":0,"sha256":"6479489e78d4f67c98e649989cf7d1d71c82dd17162155b56e646c4dac4b6bbe","tags":["gpios","inputs","outputs"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-gpios/issues","help":"https://github.com/CleepDevice/cleepmod-gpios/wiki","info":"https://github.com/CleepDevice/cleepmod-gpios","site": None},"version":"1.1.0"},
        "network":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-network/releases/download/v1.1.0/cleepmod_network_1.1.0.zip","icon":"ethernet","longdescription":"","note":-1,"price":0,"sha256":"862f6cc74340667baf688336ed2b6b07a4ac0fc2da9a9f6802648d3d5edb8ff1","tags":["wireless","wifi","ethernet"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-network/issues","help":"https://github.com/CleepDevice/cleepmod-network/wiki/Help","info":"https://github.com/CleepDevice/cleepmod-network/wiki","site": None},"version":"1.1.0"},
        "openweathermap":{"author":"Cleep","category":"SERVICE","certified": False,"changelog":"","compat": "cleep<=1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-openweathermap/releases/download/v1.1.0/cleepmod_openweathermap_1.1.0.zip","icon":"cloud","longdescription":"","note":-1,"price":0,"sha256":"a2a8726363b290978322bcabb3c85bbd6fe8a370e3cab4db2a3a4661ea1fa47a","tags":["weather","forecast"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-openweathermap/issues","help":"https://github.com/CleepDevice/cleepmod-openweathermap/wiki","info":"https://github.com/CleepDevice/cleepmod-openweathermap","site":"https://openweathermap.org/"},"version":"1.1.0"},
        "parameters":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<1.2.3","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-parameters/releases/download/v1.1.0/cleepmod_parameters_1.1.0.zip","icon":"settings","longdescription":"","note":-1,"price":0,"sha256":"efac9fa4d4bb8c5ef1a97f2d42ba916afdc4721a6f892eb21d18612164af2465","tags":["configuration","date","time","locale","lang"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-parameters/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-parameters","site": None},"version":"1.1.0"},
        "respeaker2mic":{"author":"Cleep","category":"DRIVER","certified": False,"changelog":"First release","compat": "cleep=1.2.3","country": None,"deps":["gpios"],"description":"","download":"https://github.com/CleepDevice/cleepmod-respeaker2mic/releases/download/v1.0.0/cleepmod_respeaker2mic_1.0.0.zip","icon":"microphone-settings","longdescription":"","note":-1,"price":0,"sha256":"236c981b6bf128168fa357b89ca94564b10817ac6ed7e1491daad0ef33793375","tags":["audio","mic","led","button","soundcard","grove"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-respeaker2mic/issues","help":"https://github.com/CleepDevice/cleepmod-respeaker2mic/wiki","info":"https://github.com/CleepDevice/cleepmod-respeaker2mic","site":"https://respeaker.io/2_mic_array/"},"version":"1.0.0"},
        "sensors":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["gpios"],"description":"","download":"https://github.com/CleepDevice/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-sensors/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-sensors","site": None},"version":"1.0.0"},
        "smtp":{"author":"Cleep","category":"SERVICE","certified": False,"changelog":"Update after core changes","compat":"","country": None,"deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-smtp/releases/download/v1.1.0/cleepmod_smtp_1.1.0.zip","icon":"email","longdescription":"","note":-1,"price":0,"sha256":"ee5b88d028c7fb345abaa6711b3e2f36ec7b2285d81bf6219bcd9079e6dad359","tags":["email","smtp","alert"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-smtp/issues","help":"https://github.com/CleepDevice/cleepmod-smtp/wiki","info":"https://github.com/CleepDevice/cleepmod-smtp","site": None},"version":"1.1.0"},
        "system":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","compat": "cleep<=0.0.1","country":"","deps":[],"description":"","download":"https://github.com/CleepDevice/cleepmod-system/releases/download/v1.1.0/cleepmod_system_1.1.0.zip","icon":"heart-pulse","longdescription":"","note":-1,"price":0,"sha256":"15e7eb805f55200a7d4627d4ddc77d138f9a04700713bc60b064e8420d22635e","tags":["troubleshoot","locale","events","monitoring","update","log"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-system/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-system","site": None},"version":"1.1.0"},
        "circular1":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["circular2"],"description":"","download":"https://github.com/CleepDevice/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-sensors/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-sensors","site": None},"version":"1.0.0"},
        "circular2":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["circular1"],"description":"","download":"https://github.com/CleepDevice/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/CleepDevice/cleepmod-sensors/issues","help": None,"info":"https://github.com/CleepDevice/cleepmod-sensors","site": None},"version":"1.0.0"},
    },
    "update": 1571561176
}

INVENTORY_GETMODULES = {
    "system": {"tags": ["troubleshoot", "locale", "events", "monitoring", "update", "log"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-system/releases/download/v1.1.0/cleepmod_system_1.1.0.zip", "longdescription": "Application that helps you to configure your system", "sha256": "15e7eb805f55200a7d4627d4ddc77d138f9a04700713bc60b064e8420d22635e", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-system/issues", "info": "https://github.com/CleepDevice/cleepmod-system", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "system", "note": -1, "description": "Helps updating, controlling and monitoring the device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "heart-pulse", "events": ["system.device.delete", "system.system.halt", "system.system.reboot", "system.system.restart", "system.system.needrestart", "system.monitoring.cpu", "system.monitoring.memory", "system.alert.memory", "system.alert.disk", "system.module.install", "system.module.uninstall", "system.module.update", "system.cleep.update", "system.driver.install", "system.driver.uninstall"], "changelog": "", "processing": None, "local": False, "updatable": ""},
    "parameters": {"tags": ["configuration", "date", "time", "locale", "lang"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-parameters/releases/download/v1.1.0/cleepmod_parameters_1.1.0.zip", "longdescription": "Application that helps you to configure generic parameters of your device", "sha256": "efac9fa4d4bb8c5ef1a97f2d42ba916afdc4721a6f892eb21d18612164af2465", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-parameters/issues", "info": "https://github.com/CleepDevice/cleepmod-parameters", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "parameters", "note": -1, "description": "Configure generic parameters of your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "settings", "events": ["system.device.delete", "parameters.time.now", "parameters.time.sunrise", "parameters.time.sunset", "parameters.hostname.update", "parameters.country.update"], "changelog": "new version", "processing": None, "local": False, "updatable": ""},
    "cleepbus": {"tags": ["bus", "communication"], "version": "1.1.1", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-cleepbus/releases/download/v1.1.1/cleepmod_cleepbus_1.1.1.zip", "longdescription": "Application that enables communication between devices", "sha256": "55b435169af8bac7cc06446d4f0ffcadb49ef2118d5eeaa04eaffa77f68f4b9c", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-cleepbus/issues", "info": "https://github.com/CleepDevice/cleepmod-cleepbus/wiki/CleepBus-module", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": False, "category": "APPLICATION", "certified": False, "name": "cleepbus", "note": -1, "description": "Enables communications between all your Cleep devices through your home network", "core": False, "started": True, "loadedby": [], "library": False, "icon": "bus", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
    "network": {"tags": ["wireless", "wifi", "ethernet"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-network/releases/download/v1.1.0/cleepmod_network_1.1.0.zip", "longdescription": "Application that helps you to configure device network connection", "sha256": "862f6cc74340667baf688336ed2b6b07a4ac0fc2da9a9f6802648d3d5edb8ff1", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-network/issues", "info": "https://github.com/CleepDevice/cleepmod-network/wiki", "help": "https://github.com/CleepDevice/cleepmod-network/wiki/Help", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "network", "note": -1, "description": "Configure how your device connect to your network", "core": False, "started": True, "loadedby": [], "library": False, "icon": "ethernet", "events": ["system.device.delete", "network.status.up", "network.status.down", "network.status.update"], "changelog": "", "processing": None, "local": False, "updatable": ""},
    "audio": {"tags": ["audio", "sound"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip", "longdescription": "Application that helps you to configure audio on your device", "sha256": "cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-audio/issues", "info": "https://github.com/CleepDevice/cleepmod-audio", "help": "https://github.com/CleepDevice/cleepmod-audio/wiki", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "audio", "note": -1, "description": "Configure audio on your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "speaker", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
    "sensors": {"tags": ["audio", "sound"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/CleepDevice/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip", "longdescription": "Application that helps you to configure audio on your device", "sha256": "cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab", "price": 0, "urls": {"bugs": "https://github.com/CleepDevice/cleepmod-audio/issues", "info": "https://github.com/CleepDevice/cleepmod-audio", "help": "https://github.com/CleepDevice/cleepmod-audio/wiki", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "audio", "note": -1, "description": "Configure audio on your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "speaker", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
}

GITHUB_SAMPLE = [{
  'upload_url': 'https://uploads.github.com/repos/CleepDevice/cleep/releases/20639478/assets{?name,label}',
  'draft': False,
  'assets': [{
    'content_type': 'application/octet-stream',
    'size': 85,
    'node_id': 'MDEyOlJlbGVhc2VBc3NldDE1NDI1NTMx',
    'uploader': {
      'repos_url': 'https://api.github.com/users/CleepDevice/repos',
      'gravatar_id': '',
      'id': 2676511,
      'url': 'https://api.github.com/users/CleepDevice',
      'site_admin': False,
      'html_url': 'https://github.com/CleepDevice',
      'login': 'CleepDevice',
    },
    'updated_at': '2019-10-11T12:48:41Z',
    'url': 'https://api.github.com/repos/CleepDevice/cleep/releases/assets/15425531',
    'id': 15425531,
    'browser_download_url': 'https://github.com/CleepDevice/cleep/releases/download/v0.0.20/cleep_0.0.20.sha256',
    'download_count': 11,
    'state': 'uploaded',
    'name': 'cleep_0.0.20.sha256',
    'created_at': '2019-10-11T12:48:41Z',
    'label': ''
  }, {
    'content_type': 'application/zip',
    'size': 3753481,
    'node_id': 'MDEyOlJlbGVhc2VBc3NldDE1NDI1NTA0',
    'uploader': {
      'repos_url': 'https://api.github.com/users/CleepDevice/repos',
      'id': 2676511,
      'url': 'https://api.github.com/users/CleepDevice',
      'site_admin': False,
      'html_url': 'https://github.com/CleepDevice',
      'login': 'CleepDevice',
    },
    'updated_at': '2019-10-11T12:48:40Z',
    'url': 'https://api.github.com/repos/CleepDevice/cleep/releases/assets/15425504',
    'id': 15425504,
    'browser_download_url': 'https://github.com/CleepDevice/cleep/releases/download/v0.0.20/cleep_0.0.20.deb',
    'download_count': 6,
    'state': 'uploaded',
    'name': 'cleep_0.0.20.deb',
    'created_at': '2019-10-11T12:48:15Z',
    'label': ''
  }],
  'html_url': 'https://github.com/CleepDevice/cleep/releases/tag/v0.0.20',
  'url': 'https://api.github.com/repos/CleepDevice/cleep/releases/20639478',
  'id': 20639478,
  'published_at': '2019-10-11T12:48:14Z',
  'created_at': '2019-10-05T09:33:26Z',
  'assets_url': 'https://api.github.com/repos/CleepDevice/cleep/releases/20639478/assets',
  'body': '* Migrate raven lib to sentry-sdk lib (raven is deprecated)\n* Fix issue during module update\n* Add way to install Cleep draft release (for authorized developers only)',
  'tag_name': 'v0.0.20',
  'name': '0.0.20',
  'target_commitish': 'master',
  'prerelease': False,
  'tarball_url': 'https://api.github.com/repos/CleepDevice/cleep/tarball/v0.0.20',
  'zipball_url': 'https://api.github.com/repos/CleepDevice/cleep/zipball/v0.0.20'
}]

class TestsUpdate(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.session = session.TestSession(self)

    def tearDown(self):
        self.session.clean()
        self.module = None

    def init_session(self, mock_setconfigfield=None, mock_commands=[]):
        # create module instance
        self.module = self.session.setup(Update)

        # add command mocks
        for command in mock_commands:
            self.session.add_mock_command(command)
        if 'get_modules' not in self.session.get_handled_commands():
            self.session.add_mock_command(self.session.make_mock_command('get_modules', data=INVENTORY_GETMODULES))
        if mock_setconfigfield:
            self.module._set_config_field = mock_setconfigfield

        # start module
        self.session.start_module(self.module)

    @patch('backend.update.CLEEP_VERSION', '6.6.6')
    def test_configure(self):
        mock_setconfigfield = Mock()
        self.init_session(mock_setconfigfield=mock_setconfigfield)
        mock_setconfigfield.assert_called_with('cleepversion', '6.6.6')

    def test_get_module_config(self):
        self.init_session()

        before = self.module._get_config()
        config = self.module.get_module_config()
        after = self.module._get_config()

        self.assertFalse('cleepupdatelogs' in before)
        self.assertTrue('cleepupdatelogs' in config)
        self.assertFalse('cleepupdatelogs' in after)

    def test_on_event_updates_allowed(self):
        self.init_session()
        self.module._set_config_field('cleepupdateenabled', True)
        self.module._set_config_field('modulesupdateenabled', True)
        self.module.check_cleep_updates = Mock()
        self.module.check_modules_updates = Mock()
        self.module.update_cleep = Mock()
        self.module.update_modules = Mock()
        event = {
            'event': 'parameters.time.now',
            'params': {
                'hour': self.module._check_update_time['hour'],
                'minute': self.module._check_update_time['minute'],
            },
        }

        self.module.on_event(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertTrue(self.module.update_cleep.called)
        self.assertFalse(self.module.update_modules.called)

    def test_on_event_updates_not_allowed(self):
        self.init_session()
        self.module._set_config_field('cleepupdateenabled', False)
        self.module._set_config_field('modulesupdateenabled', False)
        self.module.check_cleep_updates = Mock()
        self.module.check_modules_updates = Mock()
        self.module.update_cleep = Mock()
        self.module.update_modules = Mock()
        event = {
            'event': 'parameters.time.now',
            'params': {
                'hour': self.module._check_update_time['hour'],
                'minute': self.module._check_update_time['minute'],
            },
        }

        self.module.on_event(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertFalse(self.module.update_cleep.called)
        self.assertFalse(self.module.update_modules.called)

    def test_on_event_update_modules(self):
        self.init_session()
        self.module._set_config_field('cleepupdateenabled', False)
        self.module._set_config_field('modulesupdateenabled', True)
        self.module.check_cleep_updates = Mock()
        self.module.check_modules_updates = Mock()
        self.module.update_cleep = Mock()
        self.module.update_modules = Mock()
        event = {
            'event': 'parameters.time.now',
            'params': {
                'hour': self.module._check_update_time['hour'],
                'minute': self.module._check_update_time['minute'],
            },
        }

        self.module.on_event(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertFalse(self.module.update_cleep.called)
        self.assertTrue(self.module.update_modules.called)

    def test_get_modules_logs(self):
        self.init_session()
        self.module._get_last_update_logs = Mock(side_effect=[{'dummy': 'dummy'}, {'dummy': 'dummy'}])
        self.module._get_installed_modules_names = Mock(return_value=['system'])
        
        with patch('os.listdir', Mock(return_value=['cleep', 'system', 'audio'])):
            with patch('os.path.exists', Mock(return_value=True)):
                logs = self.module.get_modules_logs()
                logging.debug('Logs: %s' % logs)
                self.assertCountEqual(['audio', 'system'], list(logs.keys()))
                self.assertTrue('dummy' in logs['system'])
                self.assertTrue('name' in logs['system'])
                self.assertTrue('installed' in logs['system'])
                self.assertTrue(logs['system']['installed'])
                self.assertFalse(logs['audio']['installed'])

    def test_get_modules_logs_no_file_for_module(self):
        self.init_session()
        self.module._get_last_update_logs = Mock(side_effect=[{'dummy': 'dummy'}, None])
        self.module._get_installed_modules_names = Mock(return_value=['system'])
        
        with patch('os.listdir', Mock(return_value=['cleep', 'system', 'audio'])):
            with patch('os.path.exists', Mock(return_value=True)):
                logs = self.module.get_modules_logs()
                logging.debug('Logs: %s' % logs)
                self.assertCountEqual(['system'], list(logs.keys()))
                self.assertTrue('dummy' in logs['system'])
                self.assertTrue('name' in logs['system'])
                self.assertTrue('installed' in logs['system'])
                self.assertTrue(logs['system']['installed'])
                self.assertFalse('audio' in logs)

    def test_get_modules_logs_no_install_path(self):
        self.init_session()

        with patch('os.path.exists', Mock(return_value=False)):
            logs = self.module.get_modules_logs()
            logging.debug('Logs: %s' % logs)
            self.assertEqual(logs, {})

    def test_get_last_update_logs(self):
        self.init_session()

        # success
        with patch('os.path.exists', Mock(return_value=True)):
            with patch('os.path.getmtime', Mock(side_effect=[666, 665])):
                logs = self.module._get_last_update_logs('module')
                logging.debug('Logs: %s' % logs)
                self.assertEqual(logs['timestamp'], 666)
                self.assertFalse(logs['failed'])
                self.assertEqual(logs['path'], '/opt/cleep/install/module/process_success.log')

        # failure
        with patch('os.path.exists', Mock(side_effect=[False, True])):
            with patch('os.path.getmtime', Mock(return_value=666)):
                logs = self.module._get_last_update_logs('module')
                logging.debug('Logs: %s' % logs)
                self.assertEqual(logs['timestamp'], 666)
                self.assertTrue(logs['failed'])
                self.assertEqual(logs['path'], '/opt/cleep/install/module/process_failure.log')

        # neither success nor failure
        with patch('os.path.exists', Mock(side_effect=[False, False])):
            with patch('os.path.getmtime', Mock(return_value=666)):
                logs = self.module._get_last_update_logs('module')
                logging.debug('Logs: %s' % logs)
                self.assertEqual(logs, None)

    def test_get_logs(self):
        self.init_session()
        self.module.cleep_filesystem.read_data = Mock(return_value='hello world')

        # success
        with patch('os.path.exists', side_effect=[True, False]):
            with patch('os.path.getmtime', Mock(return_value=666)):
                logs = self.module.get_logs('module')
                logging.debug('Logs: %s' % logs)
                self.assertEqual(logs, 'hello world')

        # failure
        with patch('os.path.exists', side_effect=[False, True]):
            with patch('os.path.getmtime', Mock(return_value=666)):
                logs = self.module.get_logs('module')
                logging.debug('Logs: %s' % logs)
                self.assertEqual(logs, 'hello world')

        # neither success nor failure
        with patch('os.path.exists', side_effect=[False, False]):
            with self.assertRaises(CommandError) as cm:
                logs = self.module.get_logs('module')
            self.assertEqual(str(cm.exception), 'There is no logs for app "module"')

    def test_get_logs_error_read(self):
        self.init_session()
        self.module.cleep_filesystem.read_data = Mock(return_value=None)

        # success
        with patch('os.path.exists', side_effect=[True, False]):
            with patch('os.path.getmtime', Mock(return_value=666)):
                with self.assertRaises(CommandError) as cm:
                    logs = self.module.get_logs('module')
                self.assertEqual(str(cm.exception), 'Error reading app "module" logs file')

    def test_reset_module_update_data(self):
        self.init_session()
        self.module._modules_updates['module'] = self.module._Update__get_module_update_data('module', '0.0.0')
        self.module._modules_updates['module']['processing'] = True
        self.module._modules_updates['module']['pending'] = True
        self.module._modules_updates['module']['updatable'] = True
        self.module._modules_updates['module']['update']['progress'] = 55
        self.module._modules_updates['module']['update']['failed'] = True

        self.module._Update__reset_module_update_data('module')

        self.assertFalse(self.module._modules_updates['module']['processing'])
        self.assertTrue(self.module._modules_updates['module']['pending'])
        self.assertTrue(self.module._modules_updates['module']['updatable'])
        self.assertEqual(self.module._modules_updates['module']['update']['progress'], 0)
        self.assertFalse(self.module._modules_updates['module']['update']['failed'])

    def test_restart_cleep(self):
        mock_restart = self.session.make_mock_command('restart_cleep')
        self.init_session(mock_commands=[mock_restart])

        self.module._restart_cleep()
        self.assertEqual(self.session.command_call_count('restart_cleep'), 1)

    def test_restart_cleep_failed(self):
        mock_restart = self.session.make_mock_command('restart_cleep', fail=True)
        self.init_session(mock_commands=[mock_restart])

        self.module._restart_cleep()
        self.assertEqual(self.session.command_call_count('restart_cleep'), 1)

    def test_get_cleep_updates(self):
        self.init_session()

        updates = self.module.get_cleep_updates()
        logging.debug('Cleep updates: %s' % updates)
        self.assertTrue(all([k in updates for k in ['updatable', 'processing', 'pending', 'failed', 'version', 'changelog', 'packageurl', 'checksumurl']]))

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_update_available(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertEqual(update['version'], '0.0.20')
        self.assertEqual(update['changelog'], 'hello world')
        self.assertEqual(update['packageurl'], 'https://api.github.com/repos/CleepDevice/cleep/releases/assets/15425504')
        self.assertEqual(update['checksumurl'], 'https://api.github.com/repos/CleepDevice/cleep/releases/assets/15425531')

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.20')
    def test_check_cleep_updates_no_update_available(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertEqual(update['version'], None)
        self.assertEqual(update['changelog'], None)
        self.assertEqual(update['packageurl'], None)
        self.assertEqual(update['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_no_release_found(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = []
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertEqual(update['version'], None)
        self.assertEqual(update['changelog'], None)
        self.assertEqual(update['packageurl'], None)
        self.assertEqual(update['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_invalid_package_asset(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = [a for a in GITHUB_SAMPLE[0]['assets'] if a['name'] != 'cleep_0.0.20.deb']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertEqual(update['version'], None)
        self.assertEqual(update['changelog'], None)
        self.assertEqual(update['packageurl'], None)
        self.assertEqual(update['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_invalid_checksum_asset(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = [a for a in GITHUB_SAMPLE[0]['assets'] if a['name'] != 'cleep_0.0.20.sha256']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertEqual(update['version'], None)
        self.assertEqual(update['changelog'], None)
        self.assertEqual(update['packageurl'], None)
        self.assertEqual(update['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_exception(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.side_effect = Exception('Test exception')
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_session()

        with self.assertRaises(CommandError) as cm:
            self.module.check_cleep_updates()
        self.assertEqual(str(cm.exception), 'Error occured during cleep update check')

    @patch('os.environ', {'GITHUB_TOKEN': 'mysupertoken'})
    @patch('backend.update.CleepGithub')
    @patch('backend.update.CLEEP_VERSION', '0.0.19')
    def test_check_cleep_updates_with_github_token(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_session()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        mock_cleepgithub.assert_called_with('token mysupertoken')

    def test_fill_modules_updates(self):
        self.init_session()
        self.module._fill_modules_updates()
        modules_updates = self.module.get_modules_updates()
        logging.debug('Modules updates: %s' % modules_updates)

        inventory_keys = list(INVENTORY_GETMODULES.keys())
        inventory_keys.remove('cleepbus')
        self.assertEqual(sorted(inventory_keys), sorted(list(modules_updates.keys())))
        module_name = list(modules_updates.keys())[0]
        module_update = modules_updates[module_name]
        self.assertTrue('updatable' in module_update)
        self.assertTrue('processing' in module_update)
        self.assertTrue('name' in module_update)
        self.assertTrue('version' in module_update)
        self.assertTrue('version' in module_update['update'])
        self.assertTrue('changelog' in module_update['update'])
        self.assertTrue('progress' in module_update['update'])
        self.assertTrue('failed' in module_update['update'])
        self.assertEqual(module_update['name'], module_name)

    def test_fill_modules_updates_exception(self):
        self.init_session()
        self.session.set_mock_command_fail('get_modules')

        with self.assertRaises(Exception) as cm:
            self.module._fill_modules_updates()
        self.assertEqual(str(cm.exception), 'Unable to get modules list from inventory')

    def test_execute_main_action_task_install(self):
        self.init_session()
        self.module._install_main_module = Mock()
        self.module._uninstall_main_module = Mock()
        self.module._update_main_module = Mock()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': {'force': True},
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertTrue(action_install['processing'])
                self.assertFalse(action_uninstall['processing'])
                self.assertFalse(action_update['processing'])

    def test_execute_main_action_task_update(self):
        self.init_session()
        self.module._install_main_module = Mock()
        self.module._uninstall_main_module = Mock()
        self.module._update_main_module = Mock()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': {'force': True},
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_update]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertFalse(action_install['processing'])
                self.assertFalse(action_uninstall['processing'])
                self.assertTrue(action_update['processing'])

    def test_execute_main_action_task_uninstall(self):
        self.init_session()
        self.module._install_main_module = Mock()
        self.module._uninstall_main_module = Mock()
        self.module._update_main_module = Mock()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': {'force': True},
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_uninstall]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertFalse(action_install['processing'])
                self.assertTrue(action_uninstall['processing'])
                self.assertFalse(action_update['processing'])

    def test_execute_main_action_task_running_action(self):
        self.init_session()
        self.module.logger.debug = Mock()
        with patch.object(self.module, '_Update__sub_actions', ['dummy']) as mock_subactions:
            self.assertIsNone(self.module._execute_main_action_task())
            logging.debug('logs: %s' % self.module.logger.debug.call_args_list)
            self.module.logger.debug.assert_any_call(
                'Main action is processing, stop main action task here.'
            )

    def test_execute_main_action_task_running_subaction(self):
        self.init_session()
        self.module.logger.debug = Mock()
        self.module._Update__processor = 'something'
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            self.assertIsNone(self.module._execute_main_action_task())
            logging.debug('logs: %s' % self.module.logger.debug.call_args_list)
            self.module.logger.debug.assert_any_call(
                'Main action is processing, stop main action task here.'
            )

    def test_execute_main_action_task_last_action_terminated_no_more_after(self):
        self.init_session()
        self.module.logger.debug = Mock()
        self.module._need_restart = True
        main_action = {
            'processing': True
        }
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [main_action]) as mock_main_actions:
                with patch.object(self.module, '_Update__sub_actions_task') as mock_subactionstask:
                    self.assertIsNone(self.module._execute_main_action_task())
                    # logging.debug('logs: %s' % self.module.logger.debug.call_args_list)
                    self.assertTrue(mock_subactionstask.stop.called)
                    self.module.logger.debug.assert_any_call(
                        'No more main action to execute, stop all tasks.'
                    )
                    self.session.assert_event_called('system.cleep.needrestart')

    def test_execute_main_action_task_last_action_terminated_no_more_after_no_needrestart_event(self):
        self.init_session()
        self.module.logger.debug = Mock()
        self.module._need_restart = False
        main_action = {
            'processing': True
        }
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [main_action]) as mock_main_actions:
                with patch.object(self.module, '_Update__sub_actions_task') as mock_subactionstask:
                    self.assertIsNone(self.module._execute_main_action_task())
                    # logging.debug('logs: %s' % self.module.logger.debug.call_args_list)
                    self.assertTrue(mock_subactionstask.stop.called)
                    self.module.logger.debug.assert_any_call(
                        'No more main action to execute, stop all tasks.'
                    )
                    self.assertFalse(self.session.event_called('system.cleep.needrestart'))

    def test_execute_main_action_task_set_process_step_single_sub_action(self):
        self.init_session()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._set_module_process = Mock()
        self.module._get_module_infos_from_market = Mock(return_value=infos_mod1)
        with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_mainactions:
            with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
                self.module._execute_main_action_task()

                self.module._set_module_process.assert_called_once_with(progress=0)
                self.assertEqual(mock_subactions[0]['progressstep'], 100)

    def test_execute_main_action_task_set_process_step_three_sub_actions(self):
        self.init_session()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': ['mod2'],
            'version': '1.0.0',
        }
        infos_mod2 = {
            'loadedy': [],
            'deps': ['mod3'],
            'version': '0.0.0',
        }
        infos_mod3 = {
            'loadedy': [],
            'deps': [],
            'version': '0.0.0',
        }
        self.module._set_module_process = Mock()
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_mod1, infos_mod2, infos_mod3])
        with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_mainactions:
            with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
                self.module._execute_main_action_task()

                self.module._set_module_process.assert_called_once_with(progress=0)
                self.assertEqual(mock_subactions[0]['progressstep'], 33)
                self.assertEqual(mock_subactions[1]['progressstep'], 33)
                self.assertEqual(mock_subactions[2]['progressstep'], 33)

    def test_execute_main_action_exception_wo_action(self):
        self.init_session()
        self.module._set_module_process = Mock()

        with patch.object(self.module, '_Update__main_actions', None):
            # cannot pop a None object
            self.module._execute_main_action_task()
            self.module._set_module_process.assert_called_with(failed=True)

    def test_execute_main_action_exception_w_action_install(self):
        self.init_session()
        self.module._set_module_process = Mock()
        self.module._install_main_module = Mock(side_effect=Exception('Test exception'))
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._get_module_infos_from_market = Mock(return_value=[infos_mod1])

        # install
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.module._set_module_process.assert_called_with(failed=True)
                self.assertEqual(self.session.event_call_count('update.module.install'), 1)
                self.assertEqual(self.session.event_call_count('update.module.uninstall'), 0)
                self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_execute_main_action_exception_w_action_update(self):
        self.init_session(mock_commands=[
            self.session.make_mock_command('get_module_infos', fail=True)
        ])
        self.module._set_module_process = Mock()
        self.module._install_main_module = Mock(side_effect=Exception('Test exception'))
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }
        self.module._get_module_infos_from_market = Mock(return_value=[infos_mod1])

        # update
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_update]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.module._set_module_process.assert_called_with(failed=True)
                self.assertEqual(self.session.event_call_count('update.module.install'), 0)
                self.assertEqual(self.session.event_call_count('update.module.uninstall'), 0)
                self.assertEqual(self.session.event_call_count('update.module.update'), 1)

    def test_execute_main_action_exception_w_action_uninstall(self):
        self.init_session(mock_commands=[
            self.session.make_mock_command('get_module_infos', fail=True)
        ])
        self.module._set_module_process = Mock()
        self.module._install_main_module = Mock(side_effect=Exception('Test exception'))
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': { 'force': False },
        }
        infos_mod1 = {
            'loadedby': [],
            'deps': [],
            'version': '1.0.0',
        }

        # uninstall
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_uninstall]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.module._set_module_process.assert_called_with(failed=True)
                self.assertEqual(self.session.event_call_count('update.module.install'), 0)
                self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
                self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_execute_sub_action_task_install(self):
        self.init_session()
        subaction_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'module': 'mod1',
            'main': 'mod1',
            'infos': {},
            'extra': None,
            'progressstep': 12,
        }

        self.module._is_module_process_failed = Mock(return_value=False)
        self.module._set_module_process = Mock()
        self.module._install_module = Mock()
        self.module._uninstall_module = Mock()
        self.module._update_module = Mock()

        with patch.object(self.module, '_Update__sub_actions', [subaction_install]) as mock_sub_actions:
            self.module._execute_sub_actions_task()
            
            self.assertTrue(self.module._install_module.called)
            self.assertFalse(self.module._uninstall_module.called)
            self.assertFalse(self.module._update_module.called)
            self.assertEqual(len(mock_sub_actions), 0)
            self.module._set_module_process.assert_called_once_with(inc_progress=12)

    def test_execute_sub_action_task_uninstall(self):
        self.init_session()
        subaction_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'module': 'mod1',
            'main': 'mod1',
            'infos': {},
            'extra': {'force': True},
            'progressstep': 12,
        }

        self.module._is_module_process_failed = Mock(return_value=False)
        self.module._set_module_process = Mock()
        self.module._install_module = Mock()
        self.module._uninstall_module = Mock()
        self.module._update_module = Mock()

        with patch.object(self.module, '_Update__sub_actions', [subaction_uninstall]) as mock_sub_actions:
            self.module._execute_sub_actions_task()
            
            self.assertFalse(self.module._install_module.called)
            self.assertTrue(self.module._uninstall_module.called)
            self.assertFalse(self.module._update_module.called)
            self.assertEqual(len(mock_sub_actions), 0)
            self.module._set_module_process.assert_called_once_with(inc_progress=12)

    def test_execute_sub_action_task_update(self):
        self.init_session()
        subaction_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'module': 'mod1',
            'main': 'mod1',
            'infos': {},
            'extra': None,
            'progressstep': 12,
        }

        self.module._is_module_process_failed = Mock(return_value=False)
        self.module._set_module_process = Mock()
        self.module._install_module = Mock()
        self.module._uninstall_module = Mock()
        self.module._update_module = Mock()

        with patch.object(self.module, '_Update__sub_actions', [subaction_update]) as mock_sub_actions:
            self.module._execute_sub_actions_task()
            
            self.assertFalse(self.module._install_module.called)
            self.assertFalse(self.module._uninstall_module.called)
            self.assertTrue(self.module._update_module.called)
            self.assertEqual(len(mock_sub_actions), 0)
            self.module._set_module_process.assert_called_once_with(inc_progress=12)

    def test_execute_sub_action_task_already_running(self):
        self.init_session()
        subaction_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'module': 'mod1',
            'main': 'mod1',
            'infos': {},
            'extra': None,
            'progressstep': 100,
        }

        self.module._is_module_process_failed = Mock(return_value=False)
        self.module._set_module_process = Mock()
        self.module._install_module = Mock()
        self.module._uninstall_module = Mock()
        self.module._update_module = Mock()

        with patch.object(self.module, '_Update__sub_actions', [subaction_install]) as mock_sub_actions:
            with patch.object(self.module, '_Update__processor') as mock_processor:
                self.module._execute_sub_actions_task()
            
                self.assertFalse(self.module._install_module.called)
                self.assertFalse(self.module._uninstall_module.called)
                self.assertFalse(self.module._update_module.called)
                self.assertEqual(len(mock_sub_actions), 1)

    def test_execute_sub_action_task_previous_subaction_failed(self):
        self.init_session()
        subaction_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'module': 'mod1',
            'main': 'mod1',
            'infos': {},
            'extra': None,
            'progressstep': 100,
        }

        self.module._is_module_process_failed = Mock(return_value=True)
        self.module._set_module_process = Mock()
        self.module._install_module = Mock()
        self.module._uninstall_module = Mock()
        self.module._update_module = Mock()

        with patch.object(self.module, '_Update__sub_actions', [subaction_install]) as mock_sub_actions:
            self.module._execute_sub_actions_task()
            
            self.assertFalse(self.module._install_module.called)
            self.assertFalse(self.module._uninstall_module.called)
            self.assertFalse(self.module._update_module.called)
            self.assertEqual(len(mock_sub_actions), 0)

    def test_execute_sub_action_no_more_sub_action(self):
        self.init_session()
        self.module._is_module_process_failed = Mock()

        with patch.object(self.module, '_Update__sub_actions',[]) as mock_sub_actions:
            self.module._execute_sub_actions_task()
            self.assertFalse(self.module._is_module_process_failed.called)

    def test_get_processing_module_name(self):
        self.init_session()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod2',
            'extra': {'force': True},
        }
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': True,
            'module': 'mod3',
            'extra': None,
        }

        with patch.object(self.module, '_Update__main_actions', [action_install, action_uninstall, action_update]) as mock_main_actions:
            self.assertEqual(self.module._get_processing_module_name(), 'mod3')

    def test_get_processing_module_name_no_main_action(self):
        self.init_session()

        with patch.object(self.module, '_Update__main_actions', []) as mock_main_actions:
            self.assertEqual(self.module._get_processing_module_name(), None)

    def test_get_processing_module_name_no_main_action_processing(self):
        self.init_session()
        action_install = {
            'action': Update.ACTION_MODULE_INSTALL,
            'processing': False,
            'module': 'mod1',
            'extra': None,
        }
        action_uninstall = {
            'action': Update.ACTION_MODULE_UNINSTALL,
            'processing': False,
            'module': 'mod2',
            'extra': {'force': True},
        }
        action_update = {
            'action': Update.ACTION_MODULE_UPDATE,
            'processing': False,
            'module': 'mod3',
            'extra': None,
        }

        with patch.object(self.module, '_Update__main_actions', [action_install, action_uninstall, action_update]) as mock_main_actions:
            self.assertEqual(self.module._get_processing_module_name(), None)

    def test_set_module_process_update_progress(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 0,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(progress=15)

        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 15)

    def test_set_module_process_update_progress_greater_100(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 0,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(progress=150)

        self.assertEqual(self.module._modules_updates['mod1']['processing'], False)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)

    def test_set_module_process_update_inc_progress(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 10,
                    'failed': False,
                }
            },
        }
        self.module._set_module_process(inc_progress=10)
        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 20)

    def test_set_module_process_update_inc_progress_greater_100(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._get_module_infos_from_market = Mock(return_value=MODULES_JSON['list']['system'])
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 90,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(inc_progress=30)

        self.assertEqual(self.module._modules_updates['mod1']['processing'], False)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)

    def test_set_module_process_update_failed(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._get_module_infos_from_market = Mock(return_value=MODULES_JSON['list']['system'])
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 90,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(failed=True)
        logging.debug('_modules_updates[mod1]=%s' % self.module._modules_updates['mod1'])

        self.assertEqual(self.module._modules_updates['mod1']['processing'], False)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)
        self.assertEqual(self.module._modules_updates['mod1']['update']['failed'], True)

    def test_set_module_process_update_no_action_running(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value=None)
        self.module._modules_updates = {
            'mod1': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 90,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(failed=True)

        self.assertEqual(self.module._modules_updates['mod1']['processing'], False)

    def test_set_module_process_update_new_module_install(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._get_module_infos_from_market = Mock(return_value=MODULES_JSON['list']['system'])
        self.module._modules_updates = {
            'mod2': {
                'processing': False,
                'name': 'mod1',
                'version': '0.0.0',
                'updatable': False,
                'update': {
                    'changelog': 'changelog',
                    'version': None,
                    'progress': 0,
                    'failed': False,
                }
            },
        }

        self.module._set_module_process(inc_progress=15)

        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 15)
        self.assertEqual(self.module._modules_updates['mod1']['update']['version'], MODULES_JSON['list']['system']['version'])

    def test_is_module_process_failed_return_false(self):
        mock_getmodules = self.session.make_mock_command('get_modules', data=INVENTORY_GETMODULES)
        self.init_session(mock_commands=[mock_getmodules])
        self.module._get_processing_module_name = Mock(return_value='system')
        self.module._modules_updates['system']['update']['failed'] = False

        self.assertFalse(self.module._is_module_process_failed())

    def test_is_module_process_failed_return_true(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value='system')
        self.module._modules_updates['system']['update']['failed'] = True

        self.assertTrue(self.module._is_module_process_failed())

    def test_is_module_process_failed_no_processing_action(self):
        self.init_session()
        self.module._get_processing_module_name = Mock(return_value=None)

        self.assertTrue(self.module._is_module_process_failed())

    def test_set_automatic_update(self):
        self.init_session()

        # all True
        self.assertTrue(self.module.set_automatic_update(True, True))
        config = self.module._get_config()
        logging.debug('Config: %s' % config)
        self.assertTrue(config['cleepupdateenabled'])
        self.assertTrue(config['modulesupdateenabled'])

        # all False
        self.assertTrue(self.module.set_automatic_update(False, False))
        config = self.module._get_config()
        logging.debug('Config: %s' % config)
        self.assertFalse(config['cleepupdateenabled'])
        self.assertFalse(config['modulesupdateenabled'])

    def test_set_automatic_update_main_task(self):
        self.init_session()

        with patch.object(self.module, '_Update__main_actions_task') as mock_task:
            self.module.set_automatic_update(True, True)
            self.assertFalse(mock_task.stop.called)

        with patch.object(self.module, '_Update__main_actions_task') as mock_task:
            self.module.set_automatic_update(False, False)
            self.assertTrue(mock_task.stop.called)

    def test_set_automatic_update_invalid_parameters(self):
        self.init_session()

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_automatic_update('hello', False)
        self.assertEqual(str(cm.exception), 'Parameter "cleep_update_enabled" is invalid')
        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_automatic_update(666, False)
        self.assertEqual(str(cm.exception), 'Parameter "cleep_update_enabled" is invalid')
        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_automatic_update(True, 'hello')
        self.assertEqual(str(cm.exception), 'Parameter "modules_update_enabled" is invalid')
        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_automatic_update(True, 666)
        self.assertEqual(str(cm.exception), 'Parameter "modules_update_enabled" is invalid')

    @patch('backend.update.os.path.exists')
    @patch('backend.update.json')
    def test_get_module_infos_from_package(self, json_mock, path_exists_mock):
        open_mock = mock_open()
        path_exists_mock.return_value = True
        json_mock.load.return_value = 'json content'
        self.init_session()

        with patch('backend.update.open', open_mock, create=True):
            with patch('backend.update.ZipFile') as zipfile_mock:
                data = self.module._get_module_infos_from_package('module')

                self.assertEqual(data, 'json content')
                zipfile_mock.return_value.__enter__.return_value.extract.assert_called_with('module.json', path=session.PatternArg('/tmp/.*'))
                json_mock.load.assert_called()

    @patch('backend.update.os.path.exists')
    @patch('backend.update.json')
    def test_get_module_infos_from_package_file_not_exists(self, json_mock, path_exists_mock):
        open_mock = mock_open()
        json_mock.load.return_value = 'json content'
        path_exists_mock.return_value = True
        self.init_session()
        path_exists_mock.return_value = False

        with patch('backend.update.open', open_mock, create=True):
            with patch('backend.update.ZipFile') as zipfile_mock:
                with self.assertRaises(Exception) as cm:
                    data = self.module._get_module_infos_from_package('module')
                self.assertEqual(str(cm.exception), 'Package "/tmp/module.zip" for app "module" does not exists')

    @patch('backend.update.os.path.exists')
    @patch('backend.update.json')
    def test_get_module_infos_from_package_unzip_error(self, json_mock, path_exists_mock):
        open_mock = mock_open()
        path_exists_mock.return_value = True
        json_mock.load.return_value = 'json content'
        self.init_session()

        with patch('backend.update.open', open_mock, create=True):
            with patch('backend.update.ZipFile') as zipfile_mock:
                zipfile_mock.return_value.__enter__.return_value.extract.side_effect = Exception('Test exception')
                with self.assertRaises(Exception) as cm:
                    self.module._get_module_infos_from_package('module')
                self.assertEqual(str(cm.exception), 'Package "/tmp/module.zip" is not a valid application archive')

    @patch('backend.update.os.path.exists')
    @patch('backend.update.json')
    def test_get_module_infos_from_package_content_error(self, json_mock, path_exists_mock):
        open_mock = mock_open()
        path_exists_mock.return_value = True
        json_mock.load.side_effect = Exception('Test exception')
        self.init_session()

        with patch('backend.update.open', open_mock, create=True):
            with patch('backend.update.ZipFile') as zipfile_mock:
                with self.assertRaises(Exception) as cm:
                    self.module._get_module_infos_from_package('module')
                self.assertEqual(str(cm.exception), 'Package "/tmp/module.zip" has invalid content')

    def test_get_module_infos_from_market(self):
        self.init_session()
        self.module.apps_sources = Mock()
        content = {
            'list': {
                'dummy': {
                    'hello': 'world'
                }
            }
        }
        self.module.apps_sources.get_market = Mock(return_value=content)

        infos = self.module._get_module_infos_from_market('dummy')
        self.assertEqual(infos, content['list']['dummy'])

    def test_get_module_infos_from_market_unknown_module(self):
        self.init_session()
        self.module.apps_sources = Mock()
        content = {
            'list': {
                'other': {
                    'hello': 'world'
                }
            }
        }
        self.module.apps_sources.get_market = Mock(return_value=content)

        infos = self.module._get_module_infos_from_market('dummy')
        self.assertIsNone(infos)

    @patch('backend.update.AppsSources')
    def test_check_modules_updates_apps_sources_updated_with_no_app_update(self, mock_appssources):
        mock_appssources.return_value.get_market.return_value = MODULES_JSON
        mock_appssources.return_value.update_market.return_value = True
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('reload_modules'))

        updates = self.module.check_modules_updates()
        
        self.assertFalse(updates['modulesupdates'])
        self.assertTrue(updates['marketupdated'])
        self.assertTrue('moduleslastcheck' in updates)
        self.assertTrue(self.session.command_called('reload_modules'))

        # make sure modules_updates content is correct
        for module_name, update in self.module._modules_updates.items():
            self.assertCountEqual(update.keys(), ['updatable', 'processing', 'pending', 'name', 'version', 'update'])
            self.assertCountEqual(update['update'].keys(), ['progress', 'failed', 'version', 'changelog'])

    @patch('backend.update.AppsSources')
    def test_check_modules_updates_market_updated_with_module_update(self, mock_appssources):
        modules_json = copy.deepcopy(MODULES_JSON)
        version = '6.6.6'
        changelog = 'new version changelog'
        modules_json['list']['system']['version'] = version
        modules_json['list']['system']['changelog'] = changelog
        mock_appssources.return_value.get_market.return_value = modules_json
        mock_appssources.return_value.update_market.return_value = True
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('reload_modules'))

        updates = self.module.check_modules_updates()
        logging.debug('updates: %s' % updates)
        modules_updates = self.module.get_modules_updates()
        logging.debug('modules updates: %s' % modules_updates)
        
        self.assertTrue(updates['modulesupdates'])
        self.assertTrue(updates['marketupdated'])
        self.assertTrue(modules_updates['system']['updatable'])
        self.assertFalse(modules_updates['audio']['updatable'])
        self.assertFalse(modules_updates['sensors']['updatable'])
        self.assertFalse(modules_updates['network']['updatable'])
        self.assertFalse(modules_updates['parameters']['updatable'])
        self.assertEqual(modules_updates['system']['update']['changelog'], changelog)
        self.assertEqual(modules_updates['system']['update']['version'], version)
        self.assertTrue(self.session.command_called('reload_modules'))

        # make sure modules_updates content is correct
        for module_name, update in self.module._modules_updates.items():
            self.assertCountEqual(update.keys(), ['updatable', 'processing', 'pending', 'name', 'version', 'update'])
            self.assertCountEqual(update['update'].keys(), ['progress', 'failed', 'version', 'changelog'])
        
    @patch('backend.update.AppsSources')
    def test_check_modules_updates_market_exception(self, mock_appssources):
        mock_appssources.return_value.get_market.return_value = MODULES_JSON
        mock_appssources.return_value.update_market.side_effect = Exception('Test exception')
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('reload_modules'))

        with self.assertRaises(CommandError) as cm:
           self.module.check_modules_updates()

        self.assertEqual(str(cm.exception), 'Unable to update market')
        self.assertFalse(self.session.command_called('reload_modules'))

    @patch('backend.update.AppsSources')
    @patch('backend.update.Tools')
    def test_check_modules_updates_check_module_version_failed(self, mock_tools, mock_appssources):
        mock_appssources.return_value.get_market.return_value = MODULES_JSON
        mock_appssources.return_value.update_market.return_value = True
        mock_tools.compare_versions.side_effect = Exception('Test exception')
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('reload_modules'))

        # should continue event if exception occured during single module check
        updates = self.module.check_modules_updates()
        logging.debug('Updates: %s' % updates)

        self.assertEqual(updates['marketupdated'], True)
        self.assertEqual(updates['modulesupdates'], False)
        self.assertTrue(self.session.command_called('reload_modules'))

    def test_update_cleep_no_update_available(self):
        self.init_session()
        self.module.cleep_filesystem = MagicMock()
        self.module._get_config_field = Mock(return_value={'version': None, 'changelog': None})

        with self.assertRaises(CommandInfo) as cm:
            self.module.update_cleep()
        self.assertEqual(str(cm.exception), 'No Cleep update available, please launch update check first')
        self.assertFalse(self.module.cleep_filesystem.enable_write.called)

    @patch('backend.update.AppsSources')
    def test_check_modules_updates_reload_modules_fails(self, mock_appssources):
        modules_json = copy.deepcopy(MODULES_JSON)
        version = '6.6.6'
        changelog = 'new version changelog'
        modules_json['list']['system']['version'] = version
        modules_json['list']['system']['changelog'] = changelog
        mock_appssources.return_value.get_market.return_value = modules_json
        mock_appssources.return_value.update_market.return_value = True
        self.init_session()
        self.module.logger.error = Mock()
        self.session.add_mock_command(self.session.make_mock_command('reload_modules', fail=True))

        updates = self.module.check_modules_updates()

        self.assertTrue(self.session.command_called('reload_modules'))
        self.module.logger.error.assert_called_with('Error occured during inventory modules reloading: %s', 'TEST: command "reload_modules" fails for tests')
    
    @patch('backend.update.InstallCleep')
    def test_update_cleep_update_available(self, mock_installcleep):
        mock_installcleep.return_value.install = Mock()
        self.init_session()
        cleep_filesystem = MagicMock()
        crash_report = MagicMock()
        self.module.cleep_filesystem = cleep_filesystem
        self.module.crash_report = crash_report
        self.module._cleep_updates = {
            'updatable': True,
            'processing': False,
            'pending': False,
            'failed': False,
            'version': '1.0.0',
            'changelog': 'changelog',
            'packageurl': 'https://www.cleep.com/packageurl',
            'checksumurl': 'https://www.cleep.com/checksumurl'
        }

        self.module.update_cleep()

        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_installcleep.return_value.install.assert_called_once_with(
            self.module._cleep_updates['packageurl'],
            self.module._cleep_updates['checksumurl'],
            self.module._update_cleep_callback
        )

    def test_update_cleep_callback_success(self):
        self.init_session()
        self.module.cleep_filesystem = Mock()
        self.module._store_process_status = Mock()
        self.module._update_config = Mock()
        self.module._restart_cleep = Mock()
        status = {
            'status': InstallCleep.STATUS_UPDATED,
            'returncode': 0,
            'stdout': ['stdout'],
            'stderr': ['stderr'],
        }

        self.module._update_cleep_callback(status)
        
        self.assertEqual(self.session.event_call_count('update.cleep.update'), 1)
        self.assertEqual(self.session.get_last_event_params('update.cleep.update'), {'status': status['status']})
        self.module._store_process_status.assert_called_with(status, success=True)
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertTrue(self.module._restart_cleep.called)

    def test_update_cleep_callback_failed(self):
        self.init_session()
        self.module.cleep_filesystem = Mock()
        self.module._store_process_status = Mock()
        self.module._update_config = Mock()
        self.module._restart_cleep = Mock()
        status = {
            'status': InstallCleep.STATUS_ERROR_DOWNLOAD_PACKAGE,
            'returncode': 1,
            'stdout': ['stdout'],
            'stderr': ['stderr'],
        }

        self.module._update_cleep_callback(status)
        
        self.assertEqual(self.session.event_call_count('update.cleep.update'), 1)
        self.assertEqual(self.session.get_last_event_params('update.cleep.update'), {'status': status['status']})
        self.module._store_process_status.assert_called_with(status, success=False)
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertFalse(self.module._restart_cleep.called)

    def test_update_cleep_modules_update_running(self):
        self.init_session()
        self.module._cleep_updates = {
            'updatable': True,
        }
        with patch.object(self.module, '_Update__main_actions', [Mock()]):
            with self.assertRaises(CommandInfo) as cm:
                self.module.update_cleep()
            self.assertEqual(str(cm.exception), 'Applications updates are in progress. Please wait for end of it')

    @patch('backend.update.Task')
    def test_update_modules(self, mock_task):
        self.init_session()
        self.module._cleep_updates = {
            'processing': False,
            'pending': False,
        }
        mod1 = {
            'name': 'mod1',
            'updatable': True,
            'processing': True,
            'pending': False,
        }
        mod2 = {
            'name': 'mod2',
            'updatable': True,
            'processing': False,
            'pending': False,
        }
        mod3 = {
            'name': 'mod3',
            'updatable': False,
            'processing': False,
            'pending': False,
        }
        mod4 = {
            'name': 'mod4',
            'updatable': True,
            'processing': False,
            'pending': False,
        }
        mod5 = {
            'name': 'mod5',
            'updatable': True,
            'processing': False,
            'pending': True,
        }
        self.module._modules_updates = {
            'mod1': mod1,
            'mod2': mod2,
            'mod3': mod3,
            'mod4': mod4,
            'mod5': mod5
        }
        self.module._postpone_main_action = Mock()

        self.module.update_modules()
        logging.debug('Calls: %s' % self.module._postpone_main_action.mock_calls)
        self.assertEqual(self.module._postpone_main_action.call_count, 2)
        self.module._postpone_main_action.assert_has_calls([
            call(Update.ACTION_MODULE_UPDATE, 'mod2'),
            call(Update.ACTION_MODULE_UPDATE, 'mod4'),
        ], any_order=True)
        self.assertTrue(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_update_modules_cleep_update_running(self, mock_task):
        self.init_session()
        self.module._cleep_updates = {
            'processing': True,
            'pending': True
        }

        with self.assertRaises(CommandInfo) as cm:
            self.module.update_modules()
        self.assertEqual(str(cm.exception), 'Cleep update is in progress. Please wait for end of it')
        self.assertFalse(mock_task.return_value.start.called)

    def test_postpone_main_action_install(self):
        self.init_session()
        self.module._set_module_process = Mock()

        with patch.object(self.module, '_Update__main_actions') as mock_main_actions:
            self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_INSTALL, 'mod1'))
            self.assertTrue(mock_main_actions.insert.called)
            self.assertEqual(self.session.event_call_count('update.module.install'), 1)
            self.assertEqual(self.session.event_call_count('update.module.uninstall'), 0)
            self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_postpone_main_action_uninstall(self):
        self.init_session()
        self.module._set_module_process = Mock()

        with patch.object(self.module, '_Update__main_actions') as mock_main_actions:
            self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_UNINSTALL, 'mod1'))
            self.assertTrue(mock_main_actions.insert.called)
            self.assertEqual(self.session.event_call_count('update.module.install'), 0)
            self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
            self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_postpone_main_action_update(self):
        self.init_session()
        self.module._set_module_process = Mock()

        with patch.object(self.module, '_Update__main_actions') as mock_main_actions:
            self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_UPDATE, 'mod1'))
            self.assertTrue(mock_main_actions.insert.called)
            self.assertEqual(self.session.event_call_count('update.module.install'), 0)
            self.assertEqual(self.session.event_call_count('update.module.uninstall'), 0)
            self.assertEqual(self.session.event_call_count('update.module.update'), 1)

    def test_postpone_main_action_install_same_module_same_action(self):
        self.init_session()
        self.module._set_module_process = Mock()

        self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_INSTALL, 'mod1'))
        self.assertFalse(self.module._postpone_main_action(Update.ACTION_MODULE_INSTALL, 'mod1'))
        self.assertEqual(self.session.event_call_count('update.module.install'), 1)
        self.assertEqual(self.session.event_call_count('update.module.uninstall'), 0)
        self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_postpone_main_action_install_same_module_other_action(self):
        self.init_session()
        self.module._set_module_process = Mock()

        self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_INSTALL, 'mod1'))
        self.assertTrue(self.module._postpone_main_action(Update.ACTION_MODULE_UNINSTALL, 'mod1'))
        self.assertEqual(self.session.event_call_count('update.module.install'), 1)
        self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
        self.assertEqual(self.session.event_call_count('update.module.update'), 0)

    def test_get_module_infos_from_inventory(self):
        mock_getmodulesinfos = self.session.make_mock_command(
            'get_module_infos',
            data=INVENTORY_GETMODULES['audio'],
        )
        self.init_session(mock_commands=[mock_getmodulesinfos])

        infos = self.module._get_module_infos_from_inventory('audio')
        logging.debug('Infos: %s' % infos)

        self.assertEqual(infos, INVENTORY_GETMODULES['audio'])

    def test_get_module_infos_from_inventory_failed(self):
        mock_getmodulesinfos = self.session.make_mock_command(
            'get_module_infos',
            data=INVENTORY_GETMODULES['audio'],
            fail=True,
        )
        self.init_session(mock_commands=[mock_getmodulesinfos])

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'Unable to get app "audio" infos')

    def test_get_module_infos_from_inventory_unknown_module(self):
        mock_getmodules = self.session.make_mock_command(
            'get_modules',
            data={},
        )
        mock_getmodulesinfos = self.session.make_mock_command(
            'get_module_infos',
            data={},
        )
        self.init_session(mock_commands=[mock_getmodulesinfos, mock_getmodules])

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'App "audio" not found in installable apps list')

    def test_extract_compat(self):
        self.init_session()

        compat = self.module._Update__extract_compat('cleep<0.1.2')

        self.assertDictEqual(compat, {
            'module_name': 'cleep',
            'operator': '<',
            'version': '0.1.2',
        })

    def test_extract_compat_invalid_string(self):
        self.init_session()

        compat = self.module._Update__extract_compat('cleep')

        self.assertDictEqual(compat, {
            'module_name': None,
            'operator': None,
            'version': None,
        })

    def test_extract_compat_invalid_string2(self):
        self.init_session()

        compat = self.module._Update__extract_compat('cleep>test')

        self.assertDictEqual(compat, {
            'module_name': None,
            'operator': None,
            'version': None,
        })

    @patch('backend.update.CLEEP_VERSION', '1.2.3')
    def test_check_dependencies_compatibility(self):
        self.init_session()

        try:
            self.module._Update__check_dependencies_compatibility('charts', ['actions', 'audio', 'charts'], MODULES_JSON['list'])
        except:
            self.fail('Should not throw exception')

    @patch('backend.update.CLEEP_VERSION', '1.2.4')
    def test_check_dependencies_compatibility_should_not_check_module_compat(self):
        self.init_session()

        try:
            self.module._Update__check_dependencies_compatibility('charts', ['charts'], MODULES_JSON['list'], True)
        except:
            self.fail('Should not throw exception')

    @patch('backend.update.CLEEP_VERSION', '1.2.4')
    def test_check_dependencies_compatibility_should_check_module_compat(self):
        self.init_session()

        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['charts'], MODULES_JSON['list'], False)

        self.assertEqual(str(cm.exception), 'Application "charts" is not installable due to version incompatibility of app "charts" that requires cleep<=1.2.3 to be installed')

    @patch('backend.update.CLEEP_VERSION', '1.2.3')
    def test_check_dependencies_compatibility_check_equal_operator(self):
        self.init_session()

        try:
            # equal should pass
            self.module._Update__check_dependencies_compatibility('charts', ['respeaker2mic'], MODULES_JSON['list'])
        except:
            self.fail('Should not throw exception for = operator')

        # equal should not pass
        with self.assertRaises(Exception) as cm:
            self.module._Update__extract_compat = Mock(return_value={'module_name': 'cleep', 'operator': '=', 'version': '1.2.2'})
            self.module._Update__check_dependencies_compatibility('charts', ['respeaker2mic'], MODULES_JSON['list'])
        # message is not valid due to extract_compat mock
        self.assertEqual(str(cm.exception), 'Application "charts" is not installable due to version incompatibility of app "respeaker2mic" that requires cleep=1.2.3 to be installed')

    @patch('backend.update.CLEEP_VERSION', '1.2.2')
    def test_check_dependencies_compatibility_check_inferior_operator(self):
        self.init_session()

        try:
            # inferior should pass (parameters cleep<1.2.3)
            self.module._Update__check_dependencies_compatibility('charts', ['parameters'], MODULES_JSON['list'])
        except:
            self.fail('Should not throw exception for < operator')

        # inferior should not pass
        with self.assertRaises(Exception) as cm:
            self.module._Update__extract_compat = Mock(return_value={'module_name': 'cleep', 'operator': '<', 'version': '1.2.2'})
            self.module._Update__check_dependencies_compatibility('charts', ['parameters'], MODULES_JSON['list'])
        # message is not valid due to extract_compat mock
        self.assertEqual(str(cm.exception), 'Application "charts" is not installable due to version incompatibility of app "parameters" that requires cleep<1.2.3 to be installed')

    @patch('backend.update.CLEEP_VERSION', '1.2.3')
    def test_check_dependencies_compatibility_check_inferior_equal_operator(self):
        self.init_session()

        try:
            # inferior should pass (actions cleep<=1.2.3)
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])

            # action cleep<=1.2.4 should pass
            self.module._Update__extract_compat = Mock(return_value={'module_name': 'cleep', 'operator': '<=', 'version': '1.2.5'})
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        except:
            self.fail('Should not throw exception for <= operator')

        # inferior equal should not pass
        with self.assertRaises(Exception) as cm:
            self.module._Update__extract_compat = Mock(return_value={'module_name': 'cleep', 'operator': '<=', 'version': '1.2.2'})
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        # message is not valid due to extract_compat mock
        self.assertEqual(str(cm.exception), 'Application "charts" is not installable due to version incompatibility of app "actions" that requires cleep<=1.2.3 to be installed')

    @patch('backend.update.CLEEP_VERSION', '1.0.0')
    def test_check_dependencies_compatibility_incompatibility_detected(self):
        self.init_session()

        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions', 'audio', 'system'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Application "charts" is not installable due to version incompatibility of app "system" that requires cleep<=0.0.1 to be installed')

    @patch('backend.update.CLEEP_VERSION', '1.0.0')
    def test_check_dependencies_compatibility_invalid_compat_string(self):
        self.init_session()

        # invalid module name
        self.module._Update__extract_compat = Mock(return_value={'module_name': None, 'operator': '<', 'version': '0.0.0'})
        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Invalid compat string for "actions" application')

        # invalid operator
        self.module._Update__extract_compat = Mock(return_value={'module_name': 'test', 'operator': None, 'version': '0.0.0'})
        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Invalid compat string for "actions" application')

        # invalid version
        self.module._Update__extract_compat = Mock(return_value={'module_name': 'test', 'operator': '<', 'version': None})
        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Invalid compat string for "actions" application')

    @patch('backend.update.CLEEP_VERSION', '1.0.0')
    def test_check_dependencies_compatibility_invalid_module_name(self):
        self.init_session()
        self.module._Update__extract_compat = Mock(return_value={'module_name': 'test', 'operator': '<', 'version': '0.0.0'})

        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Invalid compat string (invalid module name) for "actions" application')

    @patch('backend.update.CLEEP_VERSION', '1.0.0')
    def test_check_dependencies_compatibility_invalid_operator(self):
        self.init_session()
        self.module._Update__extract_compat = Mock(return_value={'module_name': 'cleep', 'operator': '>', 'version': '0.0.0'})

        with self.assertRaises(Exception) as cm:
            self.module._Update__check_dependencies_compatibility('charts', ['actions'], MODULES_JSON['list'])
        self.assertEqual(str(cm.exception), 'Invalid compat string (invalid operator) for "actions" application')

    def test_store_process_status_module(self):
        self.init_session()
        with patch('os.path.exists', return_value=True) as mock_os_path_exists:
            cleep_filesystem = MagicMock()
            cleep_filesystem.mkdir = Mock()
            cleep_filesystem.write_json = Mock()
            self.module.cleep_filesystem = cleep_filesystem
            status = {
                'status': 'testing',
                'module': 'dummy',
                'stdout': ['info'],
                'stderr': ['error'],
            }

            self.module._store_process_status(status)
            self.assertFalse(cleep_filesystem.mkdir.called)
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/dummy/process_success.log', status)

            self.module._store_process_status(status, success=False)
            self.assertFalse(cleep_filesystem.mkdir.called)
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/dummy/process_failure.log', status)

    def test_store_process_status_cleep(self):
        self.init_session()
        with patch('os.path.exists', return_value=True) as mock_os_path_exists:
            cleep_filesystem = MagicMock()
            cleep_filesystem.mkdir = Mock()
            cleep_filesystem.write_json = Mock()
            self.module.cleep_filesystem = cleep_filesystem
            status = {
                'status': 'testing',
                'stdout': ['info'],
                'stderr': ['error'],
            }

            self.module._store_process_status(status)
            self.assertFalse(cleep_filesystem.mkdir.called)
            status.update({'module': 'cleep'})
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/cleep/process_success.log', status)

            self.module._store_process_status(status, success=False)
            self.assertFalse(cleep_filesystem.mkdir.called)
            status.update({'module': 'cleep'})
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/cleep/process_failure.log', status)

    def test_store_process_status_create_log_dir(self):
        self.init_session()
        with patch('os.path.exists', return_value=False) as mock_os_path_exists:
            cleep_filesystem = MagicMock()
            cleep_filesystem.mkdir = Mock()
            cleep_filesystem.write_json = Mock()
            self.module.cleep_filesystem = cleep_filesystem
            status = {
                'status': 'testing',
                'module': 'dummy',
                'stdout': ['info'],
                'stderr': ['error'],
            }

            self.module._store_process_status(status)

            mock_os_path_exists.assert_called_with('/opt/cleep/install/dummy')
            self.assertTrue(cleep_filesystem.mkdir.called)

    def test_store_process_status_handle_write_error(self):
        self.init_session()
        with patch('os.path.exists', return_value=True) as mock_os_path_exists:
            self.module.logger = Mock()
            self.module.logger.error = Mock()
            cleep_filesystem = MagicMock()
            cleep_filesystem.mkdir = Mock()
            cleep_filesystem.write_json = Mock(return_value=False)
            self.module.cleep_filesystem = cleep_filesystem
            status = {
                'status': 'testing',
                'module': 'dummy',
                'stdout': ['info'],
                'stderr': ['error'],
            }

            self.module._store_process_status(status)

            self.assertTrue(self.module.logger.error.called)

    @patch('backend.update.Task')
    @patch('backend.update.CleepConf')
    def test_install_module(self, mock_cleepconf, mock_task):
        self.init_session()
        self.module._postpone_main_action = Mock(return_value=True)
        mock_cleepconf.return_value.is_module_installed.return_value = False

        result= self.module.install_module('dummy')

        self.assertTrue(result)
        self.module._postpone_main_action.assert_called_with(
            self.module.ACTION_MODULE_INSTALL,
            'dummy',
            extra={
                'package': None,
                'no_compatibility_check': False
            }
        )
        self.assertTrue(mock_task.return_value.start.called)

    def test_install_module_cleep_update_running(self):
        self.init_session()
        self.module._cleep_updates = {
            'processing': True,
            'pending': False
        }

        with self.assertRaises(CommandInfo) as cm:
            self.module.install_module('dummy')
        self.assertEqual(str(cm.exception), 'Cleep update is in progress. Please wait for end of it')

    @patch('backend.update.Task')
    @patch('backend.update.CleepConf')
    def test_install_module_already_installed(self, mock_cleepconf, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        mock_cleepconf.return_value.is_module_installed.return_value = True

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is already installed')
        self.assertFalse(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    @patch('backend.update.CleepConf')
    def test_install_module_already_installed_as_library(self, mock_cleepconf, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        mock_cleepconf.return_value.is_module_installed.return_value = False
        self.module._set_module_process = Mock()

        self.module.install_module('dummy')

        mock_cleepconf.return_value.install_module.assert_called_with('dummy')
        self.module._set_module_process.assert_called_with(progress=100, failed=False, pending=True, forced_module_name='dummy')
        self.session.assert_event_called_with('update.module.install', {'status': Install.STATUS_DONE, 'module': 'dummy'})
        self.session.assert_event_called('system.cleep.needrestart')

    @patch('backend.update.os.path.exists')
    def test_install_main_module_from_package_file_not_exists(self, pathexists_mock):
        self.init_session()
        pathexists_mock.return_value = False

        with self.assertRaises(Exception) as cm:
            self.module._install_main_module('dummy', extra={'package': 'dummy.zip'})
        self.assertEqual(str(cm.exception), 'Specified package "dummy.zip" does not exists')

    @patch('backend.update.os.path.exists')
    @patch('backend.update.shutil.copyfile')
    def test_install_main_module_from_package_without_dependencies(self, shutilcopyfile_mock, pathexists_mock):
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.init_session()
        pathexists_mock.return_value = True
        self.module._get_module_infos_from_market = Mock()
        self.module._get_module_infos_from_package = Mock(return_value=infos_dummy)

        self.module._install_main_module('dummy', extra={'package': 'dummy.zip'})

        shutilcopyfile_mock.assert_called_with('dummy.zip', '/tmp/dummy.zip')
        self.module._get_module_infos_from_package.assert_called()
        self.module._get_module_infos_from_market.assert_not_called()

    @patch('backend.update.os.path.exists')
    @patch('backend.update.shutil.copyfile')
    def test_install_main_module_from_package_with_dependencies(self, shutilcopyfile_mock, pathexists_mock):
        infos_dep1 = {
            'loadedby': [],
            'deps': []
        }
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1']
        }
        self.init_session()
        pathexists_mock.return_value = True
        self.module._get_module_infos_from_market = Mock(return_value=infos_dep1)
        self.module._get_module_infos_from_package = Mock(return_value=infos_dummy)

        self.module._install_main_module('dummy', extra={'package': 'dummy.zip'})

        shutilcopyfile_mock.assert_called_with('dummy.zip', '/tmp/dummy.zip')
        self.module._get_module_infos_from_package.assert_called()
        self.module._get_module_infos_from_market.assert_called()

    def test_install_main_module_circular_deps(self):
        self.init_session()
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1']
        }
        infos_dep1 = {
            'loadedby': [],
            'deps': ['dep2']
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': ['dummy']
        }
        self.module._get_installed_modules_names = Mock(return_value=[])
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy', extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy', extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2, 'dummy', extra=None),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_main_module_with_deps(self):
        self.init_session()
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1']
        }
        infos_dep1 = {
            'loadedby': [],
            'deps': ['dep2']
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_installed_modules_names = Mock(return_value=[])
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        main_module = 'dummy'
        self.module._install_main_module(main_module)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, main_module, extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, main_module, extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2, main_module, extra=None),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_main_module_with_deps_already_installed(self):
        self.init_session()
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1'],
            'version': '0.0.0',
        }
        infos_dep1 = {
            'loadedby': [],
            'deps': ['dep2'],
            'version': '0.0.0',
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': [],
            'version': '0.0.0',
        }
        self.module._get_installed_modules_names = Mock(return_value=['dep2'])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dep1])
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy', extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy', extra=None),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_install_main_module_with_dependency_update(self):
        self.init_session()
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1'],
            'version': '0.0.1',
        }
        infos_dep1 = {
            'loadedby': [],
            'deps': ['dep2'],
            'version': '0.0.2',
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': [],
            'version': '0.0.3',
        }
        self.module._get_installed_modules_names = Mock(return_value=['dep2'])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dep1])
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        # logging.debug('Calls: %s' % self.module._postpone_sub_action.call_args_list)
        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy', extra=None),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy', extra=None),
            call(self.module.ACTION_MODULE_UPDATE, 'dep2', infos_dep2, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_module_check_params(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.install_module(None)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.module.install_module('')
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

    @patch('backend.update.CleepConf')
    def test_install_module_callback_processing(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_PROCESSING,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()

        self.module._Update__install_module_callback(status)

        self.assertFalse(self.module._store_process_status.called)
        self.assertEqual(self.session.event_call_count('update.module.install'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.install_module.called)

    @patch('backend.update.CleepConf')
    def test_install_module_callback_done(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_DONE,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        mod_infos = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[mod_infos])

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=True)
        self.assertEqual(self.session.event_call_count('update.module.install'), 1)
        self.assertTrue(self.module._need_restart)
        mock_cleepconf.return_value.install_module.assert_called_with('dummy')

    @patch('backend.update.CleepConf')
    def test_install_module_callback_error(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_ERROR,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=False)
        self.assertEqual(self.session.event_call_count('update.module.install'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.install_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True)

    @patch('backend.update.Install')
    def test_final_install_module_is_not_dependency(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._Update__install_module_callback = Mock()

        self.module._install_module(module_name, infos, {'isdependency': False})

        mock_install.return_value.install_module.assert_called_with(module_name, infos, {'isdependency': False})
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        self.assertFalse(mock_install.return_value.update_module.called)
        self.assertFalse(self.module._Update__install_module_callback.called)

    @patch('backend.update.Install')
    def test_final_install_module_is_dependency(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._Update__install_module_callback = Mock()

        self.module._install_module(module_name, infos, {'isdependency': True})

        mock_install.return_value.install_module.assert_called_with(module_name, infos, {'isdependency': True})
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        self.assertFalse(mock_install.return_value.update_module.called)
        self.assertFalse(self.module._Update__install_module_callback.called)

    @patch('backend.update.Install')
    def test_final_install_module_local_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._Update__install_module_callback = Mock()

        self.module._install_module(module_name, None, False)

        self.assertFalse(mock_install.return_value.install_module.called)
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        self.assertFalse(mock_install.return_value.update_module.called)
        self.assertTrue(self.module._Update__install_module_callback.called)

    @patch('backend.update.Install')
    def test_final_install_module_exception(self, mock_install):
        mock_install.return_value.install_module = Mock(side_effect=Exception('Test exception'))
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._Update__install_module_callback = Mock()

        self.module._install_module(module_name, infos, False)

        self.assertTrue(self.module.crash_report.manual_report.called)
        self.assertTrue(self.module._Update__install_module_callback.called)

    @patch('backend.update.CleepConf')
    def test_get_modules_to_uninstall_with_non_installed_dependencies(self, mock_cleepconf):
        self.init_session()
        modules_to_uninstall = [
            'parent',
            'child1',
            'child2',
            'child3'
        ]
        modules_infos = {
            'parent': {
                'loadedby': []
            },
            'child1': {
                'loadedby': ['parent', 'dummy']
            },
            'child2': {
                'loadedby': ['parent']
            },
            'child3': {
                'loadedby': ['child2']
            },
        }
        mock_cleepconf.return_value.is_module_installed.return_value = False

        modules = self.module._get_modules_to_uninstall('parent', modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent', 'child2', 'child3'])

    @patch('backend.update.CleepConf')
    def test_get_modules_to_uninstall_without_dependencies(self, mock_cleepconf):
        self.init_session()
        modules_to_uninstall = ['parent']
        modules_infos = {
            'parent': {
                'loadedby': []
            },
            'child1': {
                'loadedby': ['dummy']
            },
            'child2': {
                'loadedby': []
            },
            'child3': {
                'loadedby': []
            },
        }
        mock_cleepconf.return_value.is_module_installed.return_value = False

        modules = self.module._get_modules_to_uninstall('parent', modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent'])

    @patch('backend.update.CleepConf')
    def test_get_modules_to_uninstall_with_installed_dependency(self, mock_cleepconf):
        self.init_session()
        modules_to_uninstall = [
            'parent',
            'child1',
            'child2',
            'child3'
        ]
        modules_infos = {
            'parent': {
                'loadedby': []
            },
            'child1': {
                'loadedby': ['parent', 'dummy']
            },
            'child2': {
                'loadedby': ['parent'] # installed by user
            },
            'child3': {
                'loadedby': ['child2']
            },
        }
        mock_cleepconf.return_value.is_module_installed.side_effect = [False, True, False]

        modules = self.module._get_modules_to_uninstall('parent', modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent', 'child3'])

    @patch('backend.update.CleepConf')
    def test_get_modules_to_uninstall_orphan(self, mock_cleepconf):
        self.init_session()
        modules_to_uninstall = [
            'parent',
            'child1',
            'child2',
            'child3'
        ]
        modules_infos = {
            'parent': {
                'loadedby': []
            },
            'child1': {
                'loadedby': ['parent', 'dummy']
            },
            'child3': {
                'loadedby': ['child2']
            },
        }
        mock_cleepconf.return_value.is_module_installed.return_value = False

        modules = self.module._get_modules_to_uninstall('parent', modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent', 'child3'])

    @patch('backend.update.importlib')
    def test_get_local_module_dependencies(self, mock_importlib):
        self.init_session()
        dependencies = ['dummy1', 'dummy2']
        class empty:
            pass
        class dummy:
            class Dummy:
                MODULE_DEPS = dependencies
        mock_importlib.import_module.side_effect = [empty(), dummy()]

        deps = self.module._Update__get_local_module_dependencies('dummy')

        self.assertCountEqual(deps, dependencies)

    @patch('backend.update.importlib')
    def test_get_local_module_dependencies_exception(self, mock_importlib):
        self.init_session()
        mock_importlib.import_module.side_effect = Exception('Test exception')

        deps = self.module._Update__get_local_module_dependencies('dummy')

        self.assertCountEqual(deps, [])

    def test_get_module_dependencies(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy2'] }, # dummy1 deps
            { 'deps': ['dummy3'] }, # dummy2 deps
            { 'deps': ['dummy4'] }, # dummy3 deps
            { 'deps': [] }, # dummy4 deps
        ])
        self.init_session()

        modules_infos = {}
        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(deps, ['dummy4', 'dummy3', 'dummy2', 'dummy1'])
        self.assertCountEqual(deps, list(modules_infos.keys()))

    def test_get_module_dependencies_local_module(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy2'] }, # dummy1 deps
            None,
            { 'deps': ['dummy4'] }, # dummy3 deps
            { 'deps': [] }, # dummy4 deps
        ])
        self.init_session()
        self.module._Update__get_local_module_dependencies = Mock(return_value=['dummy3'])

        modules_infos = {}
        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(deps, ['dummy4', 'dummy3', 'dummy2', 'dummy1'])
        self.assertCountEqual(deps, list(modules_infos.keys()))

    def test_get_module_dependencies_complex(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy2'] }, # dummy1 deps
            { 'deps': ['dummy3', 'dummy4'] }, # dummy2 deps
            { 'deps': ['dummy5'] }, # dummy3 deps
            { 'deps': ['dummy5', 'dummy6'] }, # dummy4 deps
            { 'deps': ['dummy6'] }, # dummy5 deps
            { 'deps': [] }, # dummy6 deps
        ])
        self.init_session()

        modules_infos = {}
        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(deps, ['dummy6', 'dummy5', 'dummy3', 'dummy4', 'dummy2', 'dummy1'])
        self.assertCountEqual(deps, list(modules_infos.keys()))

    def test_get_module_dependencies_circular_deps(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy2'] }, # dummy1 deps
            { 'deps': ['dummy3'] }, # dummy2 deps
            { 'deps': ['dummy1'] }, # dummy3 deps
        ])
        self.init_session()

        modules_infos = {}
        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(sorted(deps), ['dummy1', 'dummy2', 'dummy3'])
        self.assertCountEqual(deps, list(modules_infos.keys()))

    @patch('backend.update.Task')
    def test_uninstall_module(self, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        extra = {'force': False}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        self.module._postpone_main_action = Mock()

        self.assertTrue(self.module.uninstall_module('dummy'))
        self.module._postpone_main_action.assert_called_with(self.module.ACTION_MODULE_UNINSTALL, 'dummy', extra=extra)
        self.assertTrue(mock_task.return_value.start.called)

    def test_uninstall_module_cleep_update_running(self):
        self.init_session()
        self.module._cleep_updates = {
            'processing': True,
            'pending': False
        }

        with self.assertRaises(CommandInfo) as cm:
            self.module.uninstall_module('dummy')
        self.assertEqual(str(cm.exception), 'Cleep update is in progress. Please wait for end of it')

    @patch('backend.update.Task')
    def test_uninstall_module_check_params(self, mock_task):
        self.init_session()
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])

        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_module('')
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_module(None)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        self.assertFalse(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_uninstall_module_not_installed_module(self, mock_task):
        self.init_session()

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is not installed')
        self.assertFalse(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_uninstall_module_already_postponed(self, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dummy2'])
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])

        self.assertTrue(self.module.uninstall_module('dummy'))
        self.assertFalse(self.module.uninstall_module('dummy'))
        self.assertEqual(mock_task.return_value.start.call_count, 2) # called twice for main and sub action tasks

    @patch('backend.update.CleepConf')
    def test_uninstall_main_module_with_deps(self, mock_cleepconf):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1']
        }
        infos_dep1 = {
            'loadedby': [],
            'deps': ['dep2']
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': []
        }
        extra = {'force': False}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()
        mock_cleepconf.return_value.is_module_installed.return_value = False

        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep1', infos_dep1, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    @patch('backend.update.CleepConf')
    def test_uninstall_main_module_with_circular_deps(self, mock_cleepconf):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'version': '1.2.3',
            'deps': ['dep1']
        }
        infos_dep1 = {
            'loadedby': [],
            'version': '1.2.3',
            'deps': ['dep2']
        }
        infos_dep2 = {
            'loadedby': [],
            'version': '1.2.3',
            'deps': ['dummy']
        }
        extra = {'force': False}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._postpone_sub_action = Mock()
        mock_cleepconf.return_value.is_module_installed.return_value = False

        self.module.uninstall_module('dummy')
        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep1', infos_dep1, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    @patch('backend.update.CleepConf')
    def test_uninstall_main_module_with_uninstallable_deps(self, mock_cleepconf):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'deps': ['dep1']
        }
        infos_dep1 = {
            'loadedby': ['system'],
            'deps': ['dep2']
        }
        infos_dep2 = {
            'loadedby': [],
            'deps': ['dummy']
        }
        extra = {'force': False}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._postpone_sub_action = Mock()
        mock_cleepconf.return_value.is_module_installed.return_value = False

        self.module.uninstall_module('dummy')
        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    @patch('backend.update.CleepConf')
    def test_uninstall_main_module_forced(self, mock_cleepconf):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        extra = {'force': True}
        self.module._get_module_infos_from_inventory = Mock(return_value=infos_dummy)
        self.module._postpone_sub_action = Mock()
        self.module._postpone_main_action = Mock()
        mock_cleepconf.return_value.is_module_installed.return_value = False

        self.module._uninstall_main_module('dummy', extra)
        self.module._postpone_sub_action.assert_called_once_with(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra)

        self.module.uninstall_module('dummy', force=True)
        self.module._postpone_main_action.assert_called_once_with(self.module.ACTION_MODULE_UNINSTALL, 'dummy', extra=extra)

    @patch('backend.update.CleepConf')
    def test_uninstall_main_module_no_module_to_uninstall(self, mock_cleepconf):
        self.init_session()
        self.module._get_module_dependencies = Mock()
        self.module._get_modules_to_uninstall = Mock(return_value=[])
        self.module._set_module_process = Mock()

        self.module._uninstall_main_module('dummy0', extra={'force': False})

        mock_cleepconf.return_value.uninstall_module.assert_called_with('dummy0')
        self.module._set_module_process.assert_called_with(progress=100, failed=False, pending=True, forced_module_name='dummy0')
        self.session.assert_event_called_with('update.module.uninstall', {'status': Install.STATUS_DONE, 'module': 'dummy0'})
        self.session.assert_event_called('system.cleep.needrestart')

    @patch('backend.update.CleepConf')
    def test_uninstall_module_callback_processing(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_PROCESSING,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()

        self.module._Update__uninstall_module_callback(status)

        self.assertFalse(self.module._store_process_status.called)
        self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.uninstall_module.called)

    @patch('backend.update.CleepConf')
    def test_uninstall_module_callback_done(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_DONE,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        mod_infos = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[mod_infos])

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=True)
        self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
        self.assertTrue(self.module._need_restart)
        mock_cleepconf.return_value.uninstall_module.assert_called_with('dummy')

    @patch('backend.update.CleepConf')
    def test_uninstall_module_callback_error(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_ERROR,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=False)
        self.assertEqual(self.session.event_call_count('update.module.uninstall'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.uninstall_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True, pending=True)

    @patch('backend.update.Install')
    def test_final_uninstall_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        extra = {'force': True}
        self.module._Update__uninstall_module_callback = Mock()

        self.module._uninstall_module(module_name, infos, extra)

        self.assertFalse(mock_install.return_value.install_module.called)
        mock_install.return_value.uninstall_module.assert_called_with(module_name, infos, extra['force'])
        self.assertFalse(mock_install.return_value.update_module.called)
        self.assertFalse(self.module._Update__uninstall_module_callback.called)

    @patch('backend.update.Install')
    def test_final_uninstall_module_exception(self, mock_install):
        mock_install.return_value.uninstall_module = Mock(side_effect=Exception('Test exception'))
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        extra = {'force': True}
        self.module._Update__uninstall_module_callback = Mock()

        self.module._uninstall_module(module_name, infos, extra)

        self.assertTrue(self.module.crash_report.manual_report.called)
        self.assertTrue(self.module._Update__uninstall_module_callback.called)

    @patch('backend.update.Task')
    def test_update_module(self, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        self.module._postpone_main_action = Mock(return_value=True)
        dummy = {
            'name': 'dummy',
            'updatable': True,
            'processing': False,
            'pending': False,
        }
        self.module._modules_updates = {
            'dummy': dummy
        }

        self.assertTrue(self.module.update_module('dummy'))
        self.module._postpone_main_action.assert_called_with(self.module.ACTION_MODULE_UPDATE, 'dummy')
        self.assertTrue(mock_task.return_value.start.called)

    def test_update_module_cleep_update_running(self):
        self.init_session()
        self.module._cleep_updates = {
            'processing': True,
            'pending': False
        }

        with self.assertRaises(CommandInfo) as cm:
            self.module.update_module('dummy')
        self.assertEqual(str(cm.exception), 'Cleep update is in progress. Please wait for end of it')

    def test_update_module_module_already_uptodate(self):
        self.init_session()
        mod5 = {
            'name': 'mod5',
            'updatable': False,
            'processing': False,
            'pending': False,
        }
        self.module._modules_updates = {
            'mod5': mod5
        }
        self.module._get_installed_modules_names = Mock(return_value=['mod5'])

        self.assertFalse(self.module.update_module('mod5'))

    @patch('backend.update.Task')
    def test_update_module_not_installed(self, mock_task):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=[])

        with self.assertRaises(InvalidParameter) as cm:
            self.module.update_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is not installed')
        self.assertFalse(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_update_module_check_params(self, mock_task):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.update_module(None)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.module.update_module('')
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        self.assertFalse(mock_task.return_value.start.called)

    def __generate_module_infos(self, loadedby, deps, version):
        return {
            'loadedby': loadedby,
            'deps': deps,
            'version': version
        }

    def test_update_main_module_all_deps_updated_none_uninstalled_none_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep1', infos_dep1_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep2', infos_dep2_json, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_update_main_module_some_deps_updated_none_uninstalled_none_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep2', infos_dep2_json, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_update_main_module_all_deps_updated_some_uninstalled_none_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep1', infos_dep1_json, 'dummy'),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2_inv, 'dummy', extra={'force': True}),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_update_main_module_some_deps_updated_some_uninstalled_none_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dep1', infos_dep1_json, 'dummy'),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2_inv, 'dummy', extra={'force': True}),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_update_main_module_all_deps_updated_none_uninstalled_some_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep1', infos_dep1_json, 'dummy'),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2_json, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_update_main_module_all_deps_updated_some_uninstalled_some_installed(self):
        self.init_session()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep2'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[infos_dummy_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep1', infos_dep1_inv, 'dummy', extra={'force': True}),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2_json, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    @patch('backend.update.CleepConf')
    def test_update_module_callback_processing(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_PROCESSING,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()

        self.module._Update__update_module_callback(status)

        self.assertFalse(self.module._store_process_status.called)
        self.assertEqual(self.session.event_call_count('update.module.update'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.update_module.called)

    @patch('backend.update.CleepConf')
    def test_update_module_callback_done(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_DONE,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        mod_infos = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_market = Mock(side_effect=[mod_infos])

        self.module._Update__update_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=True)
        self.assertEqual(self.session.event_call_count('update.module.update'), 1)
        self.assertTrue(self.module._need_restart)
        mock_cleepconf.return_value.update_module.assert_called_with('dummy')

    @patch('backend.update.CleepConf')
    def test_update_module_callback_error(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_ERROR,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_session()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__update_module_callback(status)

        self.module._store_process_status.assert_called_with(status, success=False)
        self.assertEqual(self.session.event_call_count('update.module.update'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.update_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True)

    @patch('backend.update.Install')
    def test_final_update_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_session()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._update_module(module_name, infos)

        self.assertFalse(mock_install.return_value.install_module.called)
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        mock_install.return_value.update_module.assert_called_with(module_name, infos)




class TestUpdateCleepUpdateEvent(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = UpdateCleepUpdateEvent(params)

    def test_event_params(self):
        self.assertEqual(self.event.EVENT_PARAMS, ['status'])




class TestUpdateModuleInstallEvent(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = UpdateModuleInstallEvent(params)

    def test_event_params(self):
        self.assertCountEqual(self.event.EVENT_PARAMS, ['status', 'module'])




class TestUpdateModuleUninstallEvent(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = UpdateModuleUninstallEvent(params)

    def test_event_params(self):
        self.assertCountEqual(self.event.EVENT_PARAMS, ['status', 'module'])




class TestUpdateModuleUpdateEvent(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        params = { 
            'internal_bus': Mock(),
            'formatters_broker': Mock(),
            'get_external_bus_name': None,
        }   
        self.event = UpdateModuleUpdateEvent(params)

    def test_event_params(self):
        self.assertCountEqual(self.event.EVENT_PARAMS, ['status', 'module'])




if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_update.py; coverage report -m -i
    unittest.main()
    
