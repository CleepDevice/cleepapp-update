#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
import copy
sys.path.append('../')
from backend.update import Update
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized, CommandInfo
from cleep.libs.tests import session
from cleep.libs.internals.installcleep import InstallCleep
from cleep.libs.internals.install import Install
from mock import Mock, patch, MagicMock, call, PropertyMock

MODULES_JSON = {
    "list": {
        "actions":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"Interact with other modules to trigger custom actions","download":"https://github.com/tangb/cleepmod-actions/releases/download/v1.0.1/cleepmod_actions_1.0.1.zip","icon":"play-box-outline","longdescription":"","note":-1,"price":0,"sha256":"d2d38835c193fa9bd37311d5ec08f780d053ff4879e8a7b05c7d773ca1f25a81","tags":["action","skill","script","trigger","python","cron"],"urls":{"bugs":"https://github.com/tangb/cleepmod-actions/issues","help":"https://github.com/tangb/cleepmod-actions/wiki","info":"https://github.com/tangb/cleepmod-actions","site": None},"version":"1.0.1"},
        "audio":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"Configure audio on your device","download":"https://github.com/tangb/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip","icon":"speaker","longdescription":"","note":-1,"price":0,"sha256":"cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab","tags":["audio","sound"],"urls":{"bugs":"https://github.com/tangb/cleepmod-audio/issues","help":"https://github.com/tangb/cleepmod-audio/wiki","info":"https://github.com/tangb/cleepmod-audio","site": None},"version":"1.1.0"},
        "charts":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-charts/releases/download/v1.0.0/cleepmod_charts_1.0.0.zip","icon":"chart-areaspline","longdescription":"","note":-1,"price":0,"sha256":"00625651423636e7087a3cfa422929440858781585138d273120e87c61bea46c","tags":["sensors","graphs","charts","database"],"urls":{"bugs":"https://github.com/tangb/cleepmod-charts/issues","help":"https://github.com/tangb/cleepmod-charts/wiki","info":"https://github.com/tangb/cleepmod-charts","site": None},"version":"1.0.0"},
        "cleepbus":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-cleepbus/releases/download/v1.1.1/cleepmod_cleepbus_1.1.1.zip","icon":"bus","longdescription":"","note":-1,"price":0,"sha256":"55b435169af8bac7cc06446d4f0ffcadb49ef2118d5eeaa04eaffa77f68f4b9c","tags":["bus","communication"],"urls":{"bugs":"https://github.com/tangb/cleepmod-cleepbus/issues","help": None,"info":"https://github.com/tangb/cleepmod-cleepbus/wiki/CleepBus-module","site": None},"version":"1.1.1"},
        "developer":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-developer/releases/download/v2.2.0/cleepmod_developer_2.2.0.zip","icon":"worker","longdescription":"","note":-1,"price":0,"sha256":"8550046516ece9d61446590fa9d96dc2ac88334adadcc15a7605ac3654b6d1f4","tags":["developer","python","cleepos","module","angularjs","cleep","cli","test","documentation"],"urls":{"bugs":"https://github.com/tangb/cleepmod-developer/issues","help":"https://github.com/tangb/cleepmod-developer/wiki","info":"https://github.com/tangb/cleepmod-developer","site": None},"version":"2.2.0"},
        "gpios":{"author":"Cleep","category":"DRIVER","certified": False,"changelog":"","country": None,"deps":[],"description":"Configure your raspberry pins","download":"https://github.com/tangb/cleepmod-gpios/releases/download/v1.1.0/cleepmod_gpios_1.1.0.zip","icon":"drag-horizontal","longdescription":"","note":-1,"price":0,"sha256":"6479489e78d4f67c98e649989cf7d1d71c82dd17162155b56e646c4dac4b6bbe","tags":["gpios","inputs","outputs"],"urls":{"bugs":"https://github.com/tangb/cleepmod-gpios/issues","help":"https://github.com/tangb/cleepmod-gpios/wiki","info":"https://github.com/tangb/cleepmod-gpios","site": None},"version":"1.1.0"},
        "network":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-network/releases/download/v1.1.0/cleepmod_network_1.1.0.zip","icon":"ethernet","longdescription":"","note":-1,"price":0,"sha256":"862f6cc74340667baf688336ed2b6b07a4ac0fc2da9a9f6802648d3d5edb8ff1","tags":["wireless","wifi","ethernet"],"urls":{"bugs":"https://github.com/tangb/cleepmod-network/issues","help":"https://github.com/tangb/cleepmod-network/wiki/Help","info":"https://github.com/tangb/cleepmod-network/wiki","site": None},"version":"1.1.0"},
        "openweathermap":{"author":"Cleep","category":"SERVICE","certified": False,"changelog":"","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-openweathermap/releases/download/v1.1.0/cleepmod_openweathermap_1.1.0.zip","icon":"cloud","longdescription":"","note":-1,"price":0,"sha256":"a2a8726363b290978322bcabb3c85bbd6fe8a370e3cab4db2a3a4661ea1fa47a","tags":["weather","forecast"],"urls":{"bugs":"https://github.com/tangb/cleepmod-openweathermap/issues","help":"https://github.com/tangb/cleepmod-openweathermap/wiki","info":"https://github.com/tangb/cleepmod-openweathermap","site":"https://openweathermap.org/"},"version":"1.1.0"},
        "parameters":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-parameters/releases/download/v1.1.0/cleepmod_parameters_1.1.0.zip","icon":"settings","longdescription":"","note":-1,"price":0,"sha256":"efac9fa4d4bb8c5ef1a97f2d42ba916afdc4721a6f892eb21d18612164af2465","tags":["configuration","date","time","locale","lang"],"urls":{"bugs":"https://github.com/tangb/cleepmod-parameters/issues","help": None,"info":"https://github.com/tangb/cleepmod-parameters","site": None},"version":"1.1.0"},
        "respeaker2mic":{"author":"Cleep","category":"DRIVER","certified": False,"changelog":"First release","country": None,"deps":["gpios"],"description":"","download":"https://github.com/tangb/cleepmod-respeaker2mic/releases/download/v1.0.0/cleepmod_respeaker2mic_1.0.0.zip","icon":"microphone-settings","longdescription":"","note":-1,"price":0,"sha256":"236c981b6bf128168fa357b89ca94564b10817ac6ed7e1491daad0ef33793375","tags":["audio","mic","led","button","soundcard","grove"],"urls":{"bugs":"https://github.com/tangb/cleepmod-respeaker2mic/issues","help":"https://github.com/tangb/cleepmod-respeaker2mic/wiki","info":"https://github.com/tangb/cleepmod-respeaker2mic","site":"https://respeaker.io/2_mic_array/"},"version":"1.0.0"},
        "sensors":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["gpios"],"description":"","download":"https://github.com/tangb/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/tangb/cleepmod-sensors/issues","help": None,"info":"https://github.com/tangb/cleepmod-sensors","site": None},"version":"1.0.0"},
        "smtp":{"author":"Cleep","category":"SERVICE","certified": False,"changelog":"Update after core changes","country": None,"deps":[],"description":"","download":"https://github.com/tangb/cleepmod-smtp/releases/download/v1.1.0/cleepmod_smtp_1.1.0.zip","icon":"email","longdescription":"","note":-1,"price":0,"sha256":"ee5b88d028c7fb345abaa6711b3e2f36ec7b2285d81bf6219bcd9079e6dad359","tags":["email","smtp","alert"],"urls":{"bugs":"https://github.com/tangb/cleepmod-smtp/issues","help":"https://github.com/tangb/cleepmod-smtp/wiki","info":"https://github.com/tangb/cleepmod-smtp","site": None},"version":"1.1.0"},
        "system":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"","country":"","deps":[],"description":"","download":"https://github.com/tangb/cleepmod-system/releases/download/v1.1.0/cleepmod_system_1.1.0.zip","icon":"heart-pulse","longdescription":"","note":-1,"price":0,"sha256":"15e7eb805f55200a7d4627d4ddc77d138f9a04700713bc60b064e8420d22635e","tags":["troubleshoot","locale","events","monitoring","update","log"],"urls":{"bugs":"https://github.com/tangb/cleepmod-system/issues","help": None,"info":"https://github.com/tangb/cleepmod-system","site": None},"version":"1.1.0"},
        "circular1":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["circular2"],"description":"","download":"https://github.com/tangb/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/tangb/cleepmod-sensors/issues","help": None,"info":"https://github.com/tangb/cleepmod-sensors","site": None},"version":"1.0.0"},
        "circular2":{"author":"Cleep","category":"APPLICATION","certified": False,"changelog":"First release","country": None,"deps":["circular1"],"description":"","download":"https://github.com/tangb/cleepmod-sensors/releases/download/v1.0.0/cleepmod_sensors_1.0.0.zip","icon":"chip","longdescription":"","note":-1,"price":0,"sha256":"1af2b840a514fae3936e5b2715e7c5416bbfaa865a2baa432cf40cd97a4cfb2f","tags":["sensors","temperature","motiononewire","1wire"],"urls":{"bugs":"https://github.com/tangb/cleepmod-sensors/issues","help": None,"info":"https://github.com/tangb/cleepmod-sensors","site": None},"version":"1.0.0"},
    },
    "update": 1571561176
}

INVENTORY_GETMODULES = {
    "data": {
        "system": {"tags": ["troubleshoot", "locale", "events", "monitoring", "update", "log"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-system/releases/download/v1.1.0/cleepmod_system_1.1.0.zip", "longdescription": "Application that helps you to configure your system", "sha256": "15e7eb805f55200a7d4627d4ddc77d138f9a04700713bc60b064e8420d22635e", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-system/issues", "info": "https://github.com/tangb/cleepmod-system", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "system", "note": -1, "description": "Helps updating, controlling and monitoring the device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "heart-pulse", "events": ["system.device.delete", "system.system.halt", "system.system.reboot", "system.system.restart", "system.system.needrestart", "system.monitoring.cpu", "system.monitoring.memory", "system.alert.memory", "system.alert.disk", "system.module.install", "system.module.uninstall", "system.module.update", "system.cleep.update", "system.driver.install", "system.driver.uninstall"], "changelog": "", "processing": None, "local": False, "updatable": ""},
        "parameters": {"tags": ["configuration", "date", "time", "locale", "lang"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-parameters/releases/download/v1.1.0/cleepmod_parameters_1.1.0.zip", "longdescription": "Application that helps you to configure generic parameters of your device", "sha256": "efac9fa4d4bb8c5ef1a97f2d42ba916afdc4721a6f892eb21d18612164af2465", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-parameters/issues", "info": "https://github.com/tangb/cleepmod-parameters", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "parameters", "note": -1, "description": "Configure generic parameters of your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "settings", "events": ["system.device.delete", "parameters.time.now", "parameters.time.sunrise", "parameters.time.sunset", "parameters.hostname.update", "parameters.country.update"], "changelog": "new version", "processing": None, "local": False, "updatable": ""},
        "cleepbus": {"tags": ["bus", "communication"], "version": "1.1.1", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-cleepbus/releases/download/v1.1.1/cleepmod_cleepbus_1.1.1.zip", "longdescription": "Application that enables communication between devices", "sha256": "55b435169af8bac7cc06446d4f0ffcadb49ef2118d5eeaa04eaffa77f68f4b9c", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-cleepbus/issues", "info": "https://github.com/tangb/cleepmod-cleepbus/wiki/CleepBus-module", "help": None, "site": None}, "pending": False, "screenshots": [], "installed": False, "category": "APPLICATION", "certified": False, "name": "cleepbus", "note": -1, "description": "Enables communications between all your Cleep devices through your home network", "core": False, "started": True, "loadedby": [], "library": False, "icon": "bus", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
        "network": {"tags": ["wireless", "wifi", "ethernet"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-network/releases/download/v1.1.0/cleepmod_network_1.1.0.zip", "longdescription": "Application that helps you to configure device network connection", "sha256": "862f6cc74340667baf688336ed2b6b07a4ac0fc2da9a9f6802648d3d5edb8ff1", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-network/issues", "info": "https://github.com/tangb/cleepmod-network/wiki", "help": "https://github.com/tangb/cleepmod-network/wiki/Help", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "network", "note": -1, "description": "Configure how your device connect to your network", "core": False, "started": True, "loadedby": [], "library": False, "icon": "ethernet", "events": ["system.device.delete", "network.status.up", "network.status.down", "network.status.update"], "changelog": "", "processing": None, "local": False, "updatable": ""},
        "audio": {"tags": ["audio", "sound"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip", "longdescription": "Application that helps you to configure audio on your device", "sha256": "cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-audio/issues", "info": "https://github.com/tangb/cleepmod-audio", "help": "https://github.com/tangb/cleepmod-audio/wiki", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "audio", "note": -1, "description": "Configure audio on your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "speaker", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
        "sensors": {"tags": ["audio", "sound"], "version": "1.1.0", "author": "Cleep", "deps": [], "country": "", "download": "https://github.com/tangb/cleepmod-audio/releases/download/v1.1.0/cleepmod_audio_1.1.0.zip", "longdescription": "Application that helps you to configure audio on your device", "sha256": "cdeda05a87cc78fc2b14a6dbd63f9a2e2063062d010f84bdbff9497ac9f93fab", "price": 0, "urls": {"bugs": "https://github.com/tangb/cleepmod-audio/issues", "info": "https://github.com/tangb/cleepmod-audio", "help": "https://github.com/tangb/cleepmod-audio/wiki", "site": None}, "pending": False, "screenshots": [], "installed": True, "category": "APPLICATION", "certified": False, "name": "audio", "note": -1, "description": "Configure audio on your device", "core": False, "started": True, "loadedby": [], "library": False, "icon": "speaker", "events": ["system.device.delete"], "changelog": "", "processing": None, "local": False, "updatable": ""},
    },
    "message": "",
    "error": False
}

GITHUB_SAMPLE = [{
  'upload_url': 'https://uploads.github.com/repos/tangb/cleep/releases/20639478/assets{?name,label}',
  'draft': False,
  'assets': [{
    'content_type': 'application/octet-stream',
    'size': 85,
    'node_id': 'MDEyOlJlbGVhc2VBc3NldDE1NDI1NTMx',
    'uploader': {
      'repos_url': 'https://api.github.com/users/tangb/repos',
      'gravatar_id': '',
      'id': 2676511,
      'url': 'https://api.github.com/users/tangb',
      'site_admin': False,
      'html_url': 'https://github.com/tangb',
      'login': 'tangb',
    },
    'updated_at': '2019-10-11T12:48:41Z',
    'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/15425531',
    'id': 15425531,
    'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.20/cleep_0.0.20.sha256',
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
      'repos_url': 'https://api.github.com/users/tangb/repos',
      'id': 2676511,
      'url': 'https://api.github.com/users/tangb',
      'site_admin': False,
      'html_url': 'https://github.com/tangb',
      'login': 'tangb',
    },
    'updated_at': '2019-10-11T12:48:40Z',
    'url': 'https://api.github.com/repos/tangb/cleep/releases/assets/15425504',
    'id': 15425504,
    'browser_download_url': 'https://github.com/tangb/cleep/releases/download/v0.0.20/cleep_0.0.20.zip',
    'download_count': 6,
    'state': 'uploaded',
    'name': 'cleep_0.0.20.zip',
    'created_at': '2019-10-11T12:48:15Z',
    'label': ''
  }],
  'html_url': 'https://github.com/tangb/cleep/releases/tag/v0.0.20',
  'url': 'https://api.github.com/repos/tangb/cleep/releases/20639478',
  'id': 20639478,
  'published_at': '2019-10-11T12:48:14Z',
  'created_at': '2019-10-05T09:33:26Z',
  'assets_url': 'https://api.github.com/repos/tangb/cleep/releases/20639478/assets',
  'body': '* Migrate raven lib to sentry-sdk lib (raven is deprecated)\n* Fix issue during module update\n* Add way to install Cleep draft release (for authorized developers only)',
  'tag_name': 'v0.0.20',
  'name': '0.0.20',
  'target_commitish': 'master',
  'prerelease': False,
  'tarball_url': 'https://api.github.com/repos/tangb/cleep/tarball/v0.0.20',
  'zipball_url': 'https://api.github.com/repos/tangb/cleep/zipball/v0.0.20'
}]

class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.session = session.TestSession()
        logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        self.session.clean()

    def init_context(self, mock_sendcommand=None, mock_getconfig=None):
        self.module = self.session.setup(Update, start_module=False)
        if mock_sendcommand:
            self.module.send_command = mock_sendcommand
        else:
            self.module.send_command = Mock(return_value=INVENTORY_GETMODULES)
        if mock_getconfig:
            self.module._get_config = mock_getconfig
        self.session.start_module(self.module)

    @patch('backend.update.Task')
    def test_configure(self, mock_task):
        mock_task.return_value = Mock()
        mock_task.return_value.start = Mock()
        mock_getconfig = Mock(return_value={'modulesupdateenabled': True})
        self.init_context(mock_getconfig=mock_getconfig)

        self.module.send_command.assert_called_with('get_modules', 'inventory', timeout=20)

        self.assertTrue(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_configure_dont_start_module_update_task(self, mock_task):
        mock_task.return_value = Mock()
        mock_task.return_value.start = Mock()
        mock_getconfig = Mock(return_value={'modulesupdateenabled': False})
        self.init_context(mock_getconfig=mock_getconfig)

        self.module.send_command.assert_called_with('get_modules', 'inventory', timeout=20)

        self.assertFalse(mock_task.return_value.start.called)

    def test_event_received_updates_allowed(self):
        self.init_context()
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

        self.module._event_received(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertTrue(self.module.update_cleep.called)
        self.assertFalse(self.module.update_modules.called)

    def test_event_received_updates_not_allowed(self):
        self.init_context()
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

        self.module._event_received(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertFalse(self.module.update_cleep.called)
        self.assertFalse(self.module.update_modules.called)

    def test_event_received_update_modules(self):
        self.init_context()
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

        self.module._event_received(event)

        self.assertTrue(self.module.check_cleep_updates.called)
        self.assertTrue(self.module.check_modules_updates.called)
        self.assertFalse(self.module.update_cleep.called)
        self.assertTrue(self.module.update_modules.called)

    def test_restart_cleep(self):
        mock_sendcommand = Mock(side_effect=[
            {'error': False, 'data': {}, 'msg': ''},
            {'error': False, 'data': None, 'msg': ''}
        ])
        self.init_context(mock_sendcommand=mock_sendcommand)
        self.module._restart_cleep()
        self.assertTrue(mock_sendcommand.called)

    def test_restart_cleep_failed(self):
        mock_sendcommand = Mock(side_effect=[
            {'error': False, 'data': {}, 'msg': ''},
            {'error': True, 'data': None, 'msg': ''}
        ])
        self.init_context(mock_sendcommand=mock_sendcommand)
        self.module._restart_cleep()
        self.assertTrue(mock_sendcommand.called)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_update_available(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertTrue('cleeplastcheck' in update)
        self.assertEqual(update['cleepupdate']['version'], '0.0.20')
        self.assertEqual(update['cleepupdate']['changelog'], 'hello world')
        self.assertEqual(update['cleepupdate']['packageurl'], 'https://api.github.com/repos/tangb/cleep/releases/assets/15425504')
        self.assertEqual(update['cleepupdate']['checksumurl'], 'https://api.github.com/repos/tangb/cleep/releases/assets/15425531')

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.20')
    def test_check_cleep_updates_no_update_available(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertTrue('cleeplastcheck' in update)
        self.assertEqual(update['cleepupdate']['version'], None)
        self.assertEqual(update['cleepupdate']['changelog'], None)
        self.assertEqual(update['cleepupdate']['packageurl'], None)
        self.assertEqual(update['cleepupdate']['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_no_release_found(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = []
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertTrue('cleeplastcheck' in update)
        self.assertEqual(update['cleepupdate']['version'], None)
        self.assertEqual(update['cleepupdate']['changelog'], None)
        self.assertEqual(update['cleepupdate']['packageurl'], None)
        self.assertEqual(update['cleepupdate']['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_invalid_package_asset(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = [a for a in GITHUB_SAMPLE[0]['assets'] if a['name'] != 'cleep_0.0.20.zip']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertTrue('cleeplastcheck' in update)
        self.assertEqual(update['cleepupdate']['version'], None)
        self.assertEqual(update['cleepupdate']['changelog'], None)
        self.assertEqual(update['cleepupdate']['packageurl'], None)
        self.assertEqual(update['cleepupdate']['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_invalid_checksum_asset(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = [a for a in GITHUB_SAMPLE[0]['assets'] if a['name'] != 'cleep_0.0.20.sha256']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        self.assertTrue('cleeplastcheck' in update)
        self.assertEqual(update['cleepupdate']['version'], None)
        self.assertEqual(update['cleepupdate']['changelog'], None)
        self.assertEqual(update['cleepupdate']['packageurl'], None)
        self.assertEqual(update['cleepupdate']['checksumurl'], None)

    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_exception(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.side_effect = Exception('Test exception')
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_context()

        with self.assertRaises(CommandError) as cm:
            self.module.check_cleep_updates()
        self.assertEqual(str(cm.exception), 'Error occured during cleep update check')

    @patch('os.environ', {'GITHUB_TOKEN': 'mysupertoken'})
    @patch('backend.update.CleepGithub')
    @patch('backend.update.VERSION', '0.0.19')
    def test_check_cleep_updates_with_github_token(self, mock_cleepgithub):
        mock_cleepgithub.return_value.get_releases.return_value = GITHUB_SAMPLE
        mock_cleepgithub.return_value.get_release_version.return_value = '0.0.20'
        mock_cleepgithub.return_value.get_release_changelog.return_value = 'hello world'
        mock_cleepgithub.return_value.get_release_assets_infos.return_value = GITHUB_SAMPLE[0]['assets']
        self.init_context()

        update = self.module.check_cleep_updates()
        logging.debug('update: %s' % update)
        mock_cleepgithub.assert_called_with('token mysupertoken')

    def test_fill_modules_updates(self):
        self.init_context()
        self.module._fill_modules_updates()
        modules_updates = self.module.get_modules_updates()
        logging.debug('Modules updates: %s' % modules_updates)

        inventory_keys = list(INVENTORY_GETMODULES['data'].keys())
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
        mock_sendcommand = Mock(return_value={'error': True, 'msg': '', 'data': None})
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            self.module._fill_modules_updates()
        self.assertEqual(str(cm.exception), 'Unable to get modules list from inventory')

    @patch('backend.update.Task')
    def test_execute_main_action_task_install(self, mock_task):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertTrue(action_install['processing'])
                self.assertFalse(action_uninstall['processing'])
                self.assertFalse(action_update['processing'])
                self.assertTrue(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_execute_main_action_task_update(self, mock_task):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_update]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertFalse(action_install['processing'])
                self.assertFalse(action_uninstall['processing'])
                self.assertTrue(action_update['processing'])
                self.assertTrue(mock_task.return_value.start.called)

    @patch('backend.update.Task')
    def test_execute_main_action_task_uninstall(self, mock_task):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_mod1])
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [action_uninstall]) as mock_main_actions:
                self.module._execute_main_action_task()
                self.assertFalse(action_install['processing'])
                self.assertTrue(action_uninstall['processing'])
                self.assertFalse(action_update['processing'])
                self.assertTrue(mock_task.return_value.start.called)

    def test_execute_main_action_task_running_action(self):
        self.init_context()
        self.module.logger.debug = Mock()
        with patch.object(self.module, '_Update__sub_actions', ['dummy']) as mock_subactions:
            self.assertIsNone(self.module._execute_main_action_task())
            self.module.logger.debug.assert_has_calls([
                call('Main action is already processing, stop here.'),
            ], any_order=True)

    def test_execute_main_action_task_last_action_terminated_no_more_after(self):
        self.init_context()
        self.module.logger.debug = Mock()
        main_action = {
            'processing': True
        }
        with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
            with patch.object(self.module, '_Update__main_actions', [main_action]) as mock_main_actions:
                with patch.object(self.module, '_Update__sub_actions_task') as mock_subactionstask:
                    self.assertIsNone(self.module._execute_main_action_task())
                    # logging.debug('logs: %s' % self.module.logger.debug.call_args_list)
                    self.assertTrue(mock_subactionstask.stop.called)
                    self.module.logger.debug.assert_has_calls([
                        call('No more main action to execute, stop here'),
                    ], any_order=True)

    def test_execute_main_action_task_set_processstep_single_sub_action(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(return_value=infos_mod1)
        with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_mainactions:
            with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
                self.module._execute_main_action_task()

                self.module._set_module_process.assert_called_once_with(progress=0)
                self.assertEqual(mock_subactions[0]['progressstep'], 100)

    def test_execute_main_action_task_set_processstep_three_sub_actions(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_mod1, infos_mod2, infos_mod3])
        with patch.object(self.module, '_Update__main_actions', [action_install]) as mock_mainactions:
            with patch.object(self.module, '_Update__sub_actions', []) as mock_subactions:
                self.module._execute_main_action_task()

                self.module._set_module_process.assert_called_once_with(progress=0)
                self.assertEqual(mock_subactions[0]['progressstep'], 33)
                self.assertEqual(mock_subactions[1]['progressstep'], 33)
                self.assertEqual(mock_subactions[2]['progressstep'], 33)

    def test_execute_sub_action_task_install(self):
        self.init_context()
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
        self.init_context()
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
        self.init_context()
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
        self.init_context()
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
        self.init_context()
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

    def test_get_processing_module_name(self):
        self.init_context()
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
        self.init_context()

        with patch.object(self.module, '_Update__main_actions', []) as mock_main_actions:
            self.assertEqual(self.module._get_processing_module_name(), None)

    def test_get_processing_module_name_no_main_action_processing(self):
        self.init_context()
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
        self.init_context()
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
        self.init_context()
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
        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)

    def test_set_module_process_update_inc_progress(self):
        self.init_context()
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
        self.init_context()
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
                    'progress': 90,
                    'failed': False,
                }
            },
        }
        self.module._set_module_process(inc_progress=30)
        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)

    def test_set_module_process_update_failed(self):
        self.init_context()
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
                    'progress': 90,
                    'failed': False,
                }
            },
        }
        self.module._set_module_process(failed=True)
        self.assertEqual(self.module._modules_updates['mod1']['processing'], True)
        self.assertEqual(self.module._modules_updates['mod1']['update']['progress'], 100)
        self.assertEqual(self.module._modules_updates['mod1']['update']['failed'], True)

    def test_set_module_process_update_no_action_running(self):
        self.init_context()
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
        self.init_context()
        self.module._get_processing_module_name = Mock(return_value='mod1')
        self.module._get_module_infos_from_modules_json = Mock(return_value=MODULES_JSON['list']['system'])
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
        self.init_context()
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
                    'progress': 90,
                    'failed': False,
                }
            },
        }
        self.assertFalse(self.module._is_module_process_failed())

    def test_is_module_process_failed_return_true(self):
        self.init_context()
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
                    'progress': 90,
                    'failed': True,
                }
            },
        }
        self.assertTrue(self.module._is_module_process_failed())

    def test_is_module_process_failed_no_processing_action(self):
        self.init_context()
        self.module._get_processing_module_name = Mock(return_value=None)
        self.assertTrue(self.module._is_module_process_failed())

    def test_set_automatic_update(self):
        self.init_context()

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
        self.init_context()

        with patch.object(self.module, '_Update__main_actions_task') as mock_task:
            self.module.set_automatic_update(True, True)
            self.assertFalse(mock_task.stop.called)

        with patch.object(self.module, '_Update__main_actions_task') as mock_task:
            self.module.set_automatic_update(False, False)
            self.assertTrue(mock_task.stop.called)

    def test_set_automatic_update_invalid_parameters(self):
        self.init_context()

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

    def test_get_module_infos_from_modules_json(self):
        self.init_context()
        self.module.modules_json = Mock()
        content = {
            'list': {
                'dummy': {
                    'hello': 'world'
                }
            }
        }
        self.module.modules_json.get_json = Mock(return_value=content)

        infos = self.module._get_module_infos_from_modules_json('dummy')
        self.assertEqual(infos, content['list']['dummy'])

    def test_get_module_infos_from_modules_json_unknown_module(self):
        self.init_context()
        self.module.modules_json = Mock()
        content = {
            'list': {
                'other': {
                    'hello': 'world'
                }
            }
        }
        self.module.modules_json.get_json = Mock(return_value=content)

        infos = self.module._get_module_infos_from_modules_json('dummy')
        self.assertIsNone(infos)

    @patch('backend.update.ModulesJson')
    def test_check_modules_updates_modules_json_not_updated(self, mock_modulesjson):
        mock_modulesjson.return_value.get_json.return_value = MODULES_JSON
        mock_modulesjson.return_value.update.return_value = False
        self.init_context()

        updates = self.module.check_modules_updates()
        
        self.assertFalse(updates['modulesupdates'])
        self.assertFalse(updates['modulesjsonupdated'])
        self.assertTrue('moduleslastcheck' in updates)

    @patch('backend.update.ModulesJson')
    def test_check_modules_updates_modules_json_updated_with_no_module_update(self, mock_modulesjson):
        mock_modulesjson.return_value.get_json.return_value = MODULES_JSON
        mock_modulesjson.return_value.update.return_value = True
        self.init_context()
        # self.module._get_inventory_modules = Mock(return_value=INVENTORY_GETMODULES['data'])

        updates = self.module.check_modules_updates()
        
        self.assertFalse(updates['modulesupdates'])
        self.assertTrue(updates['modulesjsonupdated'])
        self.assertTrue('moduleslastcheck' in updates)

    @patch('backend.update.ModulesJson')
    def test_check_modules_updates_modules_json_updated_with_module_update(self, mock_modulesjson):
        modules_json = copy.deepcopy(MODULES_JSON)
        version = '6.6.6'
        changelog = 'new version changelog'
        modules_json['list']['system']['version'] = version
        modules_json['list']['system']['changelog'] = changelog
        mock_modulesjson.return_value.get_json.return_value = modules_json
        mock_modulesjson.return_value.update.return_value = True
        self.init_context()

        updates = self.module.check_modules_updates()
        logging.debug('updates: %s' % updates)
        modules_updates = self.module.get_modules_updates()
        logging.debug('modules updates: %s' % modules_updates)
        
        self.assertTrue(updates['modulesupdates'])
        self.assertTrue(updates['modulesjsonupdated'])
        self.assertTrue(modules_updates['system']['updatable'])
        self.assertFalse(modules_updates['audio']['updatable'])
        self.assertFalse(modules_updates['sensors']['updatable'])
        self.assertFalse(modules_updates['network']['updatable'])
        self.assertFalse(modules_updates['parameters']['updatable'])
        self.assertEqual(modules_updates['system']['update']['changelog'], changelog)
        self.assertEqual(modules_updates['system']['update']['version'], version)
        
    @patch('backend.update.ModulesJson')
    def test_check_modules_updates_modules_json_exception(self, mock_modulesjson):
        mock_modulesjson.return_value.get_json.return_value = MODULES_JSON
        mock_modulesjson.return_value.update.side_effect = Exception('Test exception')
        self.init_context()

        with self.assertRaises(CommandError) as cm:
           self.module.check_modules_updates()
        self.assertEqual(str(cm.exception), 'Unable to refresh modules list from internet')

    @patch('backend.update.ModulesJson')
    @patch('backend.update.Tools')
    def test_check_modules_updates_check_failed(self, mock_tools, mock_modulesjson):
        mock_modulesjson.return_value.get_json.return_value = MODULES_JSON
        mock_modulesjson.return_value.update.return_value = True
        mock_tools.compare_versions.side_effect = Exception('Test exception')
        self.init_context()

        # should continue event if exception occured during single module check
        updates = self.module.check_modules_updates()
        logging.debug('Updates: %s' % updates)

        self.assertEqual(updates['modulesjsonupdated'], True)
        self.assertEqual(updates['modulesupdates'], False)

    def test_update_cleep_no_update_available(self):
        self.init_context()
        self.module.cleep_filesystem = MagicMock()
        self.module._get_config_field = Mock(return_value={'version': None, 'changelog': None})

        with self.assertRaises(CommandInfo) as cm:
            self.module.update_cleep()
        self.assertEqual(str(cm.exception), 'No Cleep update available, please launch update check first')
        self.assertFalse(self.module.cleep_filesystem.enable_write.called)
    
    @patch('backend.update.InstallCleep')
    def test_update_cleep_update_available(self, mock_installcleep):
        mock_installcleep.return_value.install = Mock()
        self.init_context()
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
        self.init_context()
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
        
        self.assertEqual(self.session.get_event_calls('update.cleep.update'), 1)
        self.assertEqual(self.session.get_event_last_params('update.cleep.update'), {'status': status['status']})
        self.module._store_process_status.assert_called_with(status, success=True)
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertTrue(self.module._restart_cleep.called)

    def test_update_cleep_callback_failed(self):
        self.init_context()
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
        
        self.assertEqual(self.session.get_event_calls('update.cleep.update'), 1)
        self.assertEqual(self.session.get_event_last_params('update.cleep.update'), {'status': status['status']})
        self.module._store_process_status.assert_called_with(status, success=False)
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertFalse(self.module._restart_cleep.called)

    def test_get_module_infos_from_inventory(self):
        mock_sendcommand = Mock(side_effect=[
            {'error': False, 'data': {}, 'msg': ''},
            {'error': False, 'msg': '', 'data': INVENTORY_GETMODULES['data']['audio']}
        ])
        self.init_context(mock_sendcommand=mock_sendcommand)

        infos = self.module._get_module_infos_from_inventory('audio')
        logging.debug('Infos: %s' % infos)

        self.assertEqual(infos, INVENTORY_GETMODULES['data']['audio'])

    def test_get_module_infos_from_inventory_failed(self):
        mock_sendcommand = Mock(side_effect=[
            {'error': False, 'data': {}, 'msg': ''},
            {'error': True, 'msg': '', 'data': INVENTORY_GETMODULES['data']['audio']}
        ])
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'Unable to get module "audio" infos')

    def test_get_module_infos_from_inventory_unknown_module(self):
        mock_sendcommand = Mock(side_effect=[
            {'error': False, 'data': {}, 'msg': ''},
            {'error': False, 'msg': '', 'data': None}
        ])
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'Module "audio" not found in installable modules list')

    def test_store_process_status_module(self):
        self.init_context()
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
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/dummy/process.log', status)

    def test_store_process_status_cleep(self):
        self.init_context()
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
            cleep_filesystem.write_json.assert_called_with('/opt/cleep/install/cleep/process.log', status)

    def test_store_process_status_create_log_dir(self):
        self.init_context()
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
        self.init_context()
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

    def test_install_module(self):
        self.init_context()
        self.module._postpone_main_action = Mock(return_value=True)

        self.assertTrue(self.module.install_module('dummy'))
        self.module._postpone_main_action.assert_called_with(self.module.ACTION_MODULE_INSTALL, 'dummy')

    def test_install_module_already_installed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is already installed')

    def test_install_main_module_circular_deps(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy'),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy'),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_main_module_with_deps(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        main_module = 'dummy'
        self.module._install_main_module(main_module)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, main_module),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, main_module),
            call(self.module.ACTION_MODULE_INSTALL, 'dep2', infos_dep2, main_module),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_main_module_with_deps_already_installed(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy'),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_install_main_module_with_dependency_update(self):
        self.init_context()
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
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module._install_main_module('dummy')

        # logging.debug('Calls: %s' % self.module._postpone_sub_action.call_args_list)
        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_INSTALL, 'dummy', infos_dummy, 'dummy'),
            call(self.module.ACTION_MODULE_INSTALL, 'dep1', infos_dep1, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep2', infos_dep2, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_install_module_check_params(self):
        self.init_context()

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
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.install'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.install'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.install'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.install_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True)

    @patch('backend.update.Install')
    def test_final_install_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_context()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._install_module(module_name, infos)

        mock_install.return_value.install_module.assert_called_with(module_name, infos)
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        self.assertFalse(mock_install.return_value.update_module.called)

    def test_get_modules_to_uninstall(self):
        self.init_context()
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

        modules = self.module._get_modules_to_uninstall(modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent', 'child2', 'child3'])

    def test_get_modules_to_uninstall_orphan(self):
        self.init_context()
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

        modules = self.module._get_modules_to_uninstall(modules_to_uninstall, modules_infos)

        self.assertEqual(modules, ['parent', 'child3'])

    def test_get_module_dependencies(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy2'] }, # dummy1 deps
            { 'deps': ['dummy3'] }, # dummy2 deps
            { 'deps': ['dummy4'] }, # dummy3 deps
            { 'deps': [] }, # dummy4 deps
        ])
        self.init_context()

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
        self.init_context()

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
        self.init_context()

        modules_infos = {}
        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(sorted(deps), ['dummy1', 'dummy2', 'dummy3'])
        self.assertCountEqual(deps, list(modules_infos.keys()))

    def test_uninstall_module(self):
        self.init_context()
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

    def test_uninstall_main_module_with_deps(self):
        self.init_context()
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

        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep1', infos_dep1, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_uninstall_main_module_with_circular_deps(self):
        self.init_context()
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
            'deps': ['dummy']
        }
        extra = {'force': False}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        self.module._postpone_sub_action = Mock()

        self.module.uninstall_module('dummy')
        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep1', infos_dep1, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 3)

    def test_uninstall_main_module_with_uninstallable_deps(self):
        self.init_context()
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
        self.module._postpone_sub_action = Mock()

        self.module.uninstall_module('dummy')
        self.module._uninstall_main_module('dummy', extra)

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2, 'dummy', extra),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_uninstall_main_module_forced(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        extra = {'force': True}
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        self.module._postpone_sub_action = Mock()
        self.module._postpone_main_action = Mock()

        self.module._uninstall_main_module('dummy', extra)
        self.module._postpone_sub_action.assert_called_once_with(self.module.ACTION_MODULE_UNINSTALL, 'dummy', infos_dummy, 'dummy', extra)

        self.module.uninstall_module('dummy', force=True)
        self.module._postpone_main_action.assert_called_once_with(self.module.ACTION_MODULE_UNINSTALL, 'dummy', extra=extra)

    def test_uninstall_module_check_params(self):
        self.init_context()
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

    def test_uninstall_module_not_installed_module(self):
        self.init_context()

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is not installed')

    def test_uninstall_module_already_postponed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dummy2'])
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])

        self.assertTrue(self.module.uninstall_module('dummy'))
        self.assertFalse(self.module.uninstall_module('dummy'))

    @patch('backend.update.CleepConf')
    def test_uninstall_module_callback_processing(self, mock_cleepconf):
        status = {
            'status': Install.STATUS_PROCESSING,
            'module': 'dummy',
            'stdout': ['hello'],
            'stderr': ['world'],
        }
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.uninstall'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.uninstall'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.uninstall'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.uninstall_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True)

    @patch('backend.update.Install')
    def test_final_uninstall_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_context()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        extra = {'force': True}
        self.module._uninstall_module(module_name, infos, extra)

        self.assertFalse(mock_install.return_value.install_module.called)
        mock_install.return_value.uninstall_module.assert_called_with(module_name, infos, extra['force'])
        self.assertFalse(mock_install.return_value.update_module.called)

    def test_update_module(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy'])
        self.module._postpone_main_action = Mock(return_value=True)

        self.assertTrue(self.module.update_module('dummy'))
        self.module._postpone_main_action.assert_called_with(self.module.ACTION_MODULE_UPDATE, 'dummy')

    def test_update_module_not_installed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=[])

        with self.assertRaises(InvalidParameter) as cm:
            self.module.update_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is not installed')

    def test_update_module_check_params(self):
        self.init_context()

        with self.assertRaises(MissingParameter) as cm:
            self.module.update_module(None)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.module.update_module('')
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

    def __generate_module_infos(self, loadedby, deps, version):
        return {
            'loadedby': loadedby,
            'deps': deps,
            'version': version
        }

    def test_update_main_module_all_deps_updated_none_uninstalled_none_installed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
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
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dummy', infos_dummy_json, 'dummy'),
            call(self.module.ACTION_MODULE_UPDATE, 'dep2', infos_dep2_json, 'dummy'),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_update_main_module_all_deps_updated_some_uninstalled_none_installed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
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
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], ['dep2'], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_inv, infos_dep1_inv, infos_dep2_inv])
        self.module._postpone_sub_action = Mock()

        self.module._update_main_module('dummy')

        self.module._postpone_sub_action.assert_has_calls([
            call(self.module.ACTION_MODULE_UPDATE, 'dep1', infos_dep1_json, 'dummy'),
            call(self.module.ACTION_MODULE_UNINSTALL, 'dep2', infos_dep2_inv, 'dummy', extra={'force': True}),
        ], any_order=True)
        self.assertEqual(self.module._postpone_sub_action.call_count, 2)

    def test_update_main_module_all_deps_updated_none_uninstalled_some_installed(self):
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep1'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], ['dep2'], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep1_json, infos_dep2_json])
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
        self.init_context()
        self.module._get_installed_modules_names = Mock(return_value=['dummy', 'dep1', 'dep2'])
        infos_dummy_inv = self.__generate_module_infos([], ['dep1'], '0.0.0')
        infos_dep1_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dep2_inv = self.__generate_module_infos([], [], '0.0.0')
        infos_dummy_json = self.__generate_module_infos([], ['dep2'], '1.0.0')
        infos_dep1_json = self.__generate_module_infos([], [], '0.1.0')
        infos_dep2_json = self.__generate_module_infos([], [], '0.0.1')
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_json, infos_dep2_json])
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
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__update_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.update'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()

        self.module._Update__update_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.update'), 1)
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
        self.init_context()
        self.module._store_process_status = Mock()
        self.module._set_module_process = Mock()

        self.module._Update__update_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.update'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.update_module.called)
        self.module._set_module_process.assert_called_once_with(failed=True)

    @patch('backend.update.Install')
    def test_final_update_module(self, mock_install):
        mock_install.return_value.install_module = Mock()
        mock_install.return_value.uninstall_module = Mock()
        mock_install.return_value.update_module = Mock()
        self.init_context()
        infos = {'version': '0.0.0'}
        module_name = 'dummy'
        self.module._update_module(module_name, infos)

        self.assertFalse(mock_install.return_value.install_module.called)
        self.assertFalse(mock_install.return_value.uninstall_module.called)
        mock_install.return_value.update_module.assert_called_with(module_name, infos)



if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_update.py; coverage report -m -i
    unittest.main()
    
