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
from mock import Mock, patch, MagicMock, call

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

    def init_context(self, mock_sendcommand=None):
        self.module = self.session.setup(Update)
        if mock_sendcommand:
            self.module.send_command = mock_sendcommand
        else:
            self.module.send_command = Mock(return_value=INVENTORY_GETMODULES)

    @patch('backend.update.ModulesJson')
    def test_configure(self, mock_modules_json):
        mock_modules_json.return_value.exists.return_value = False
        self.init_context()

        self.assertTrue(mock_modules_json.return_value.update.called)

    def test_restart_cleep(self):
        mock_sendcommand = Mock(return_value={'error': False, 'data': None, 'msg': ''})
        self.init_context(mock_sendcommand=mock_sendcommand)
        self.module._restart_cleep()
        self.assertTrue(mock_sendcommand.called)

    def test_restart_cleep_failed(self):
        mock_sendcommand = Mock(return_value={'error': True, 'data': None, 'msg': ''})
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

    def test_get_installed_modules(self):
        self.init_context()
        self.module._modules_updates = {
            'system': {
                'name': 'system',
                'version': '0.0.0',
                'updatable': False,
                'updating': False,
                'update': {
                    'version': None,
                    'changelog': None,
                },
            },
            'parameters': {
                'name': 'parameters',
                'version': '0.0.9',
                'updatable': True,
                'updating': True,
                'update': {
                    'version': '1.1.2',
                    'changelog': 'some changelog',
                }
            }
        }

        modules = self.module._get_installed_modules()
        logging.debug('Modules list: %s' % modules)

        inventory_keys = list(INVENTORY_GETMODULES['data'].keys())
        inventory_keys.remove('cleepbus')
        self.assertEqual(sorted(inventory_keys), sorted(list(modules.keys())))
        # with previous data and no update
        self.assertEqual(modules['system']['updatable'], False)
        self.assertEqual(modules['system']['updating'], False)
        self.assertEqual(modules['system']['version'], '1.1.0')
        self.assertEqual(modules['system']['update']['version'], None)
        self.assertEqual(modules['system']['update']['changelog'], None)
        # with previous data and update data
        self.assertEqual(modules['parameters']['updatable'], True)
        self.assertEqual(modules['parameters']['updating'], True)
        self.assertEqual(modules['parameters']['version'], '1.1.0')
        self.assertEqual(modules['parameters']['update']['version'], '1.1.2')
        self.assertEqual(modules['parameters']['update']['changelog'], 'some changelog')
        # with no previous info
        self.assertEqual(modules['audio']['updatable'], False)
        self.assertEqual(modules['audio']['updating'], False)
        self.assertEqual(modules['audio']['version'], '1.1.0')
        self.assertEqual(modules['audio']['update']['version'], None)
        self.assertEqual(modules['audio']['update']['changelog'], None)

    def test_get_installed_modules_exception(self):
        mock_sendcommand = Mock(return_value={'error': True, 'msg': '', 'data': None})
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            modules = self.module._get_installed_modules()
        self.assertEqual(str(cm.exception), 'Unable to get modules list from inventory')

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
        modules_json['list']['system']['version'] = '6.6.6'
        modules_json['list']['system']['changelog'] = 'new version'
        mock_modulesjson.return_value.get_json.return_value = modules_json
        mock_modulesjson.return_value.update.return_value = True
        self.init_context()

        updates = self.module.check_modules_updates()
        logging.debug('updates: %s' % updates)
        
        self.assertTrue(updates['modulesupdates'])
        self.assertTrue(updates['modulesjsonupdated'])
        
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
        self.assertEqual(str(cm.exception), 'No Cleep update available, please launch update check')
        self.assertFalse(self.module.cleep_filesystem.enable_write.called)
    
    @patch('backend.update.InstallCleep')
    def test_update_cleep_update_available(self, mock_installcleep):
        self.init_context()
        cleep_filesystem = MagicMock()
        crash_report = MagicMock()
        self.module.cleep_filesystem = cleep_filesystem
        self.module.crash_report = crash_report
        config = {
            'version': '1.0.0',
            'changelog': 'changelog',
            'packageurl': 'https://www.cleep.com/packageurl',
            'checksumurl': 'https://www.cleep.com/checksumurl'
        }
        self.module._get_config_field = Mock(return_value=config)
        self.module.start = Mock()

        self.module.update_cleep()

        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_installcleep.assert_called_once_with(config['packageurl'], config['checksumurl'], self.module._update_cleep_callback, cleep_filesystem, crash_report)
        self.assertTrue(mock_installcleep.return_value.start.called)

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
        self.assertTrue(self.module._store_process_status.called)
        self.module._update_config.assert_called_with({'cleepupdate': {'version': None, 'changelog': None, 'packageurl': None, 'checksumurl': None}})
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertTrue(self.module._restart_cleep.called)

    def test_update_cleep_callback_failed(self):
        self.init_context()
        self.module.cleep_filesystem = Mock()
        self.module._store_process_status = Mock()
        self.module._update_config = Mock()
        self.module._restart_cleep = Mock()
        status = {
            'status': InstallCleep.STATUS_ERROR_DOWNLOAD_ARCHIVE,
            'returncode': 1,
            'stdout': ['stdout'],
            'stderr': ['stderr'],
        }

        self.module._update_cleep_callback(status)
        
        self.assertEqual(self.session.get_event_calls('update.cleep.update'), 1)
        self.assertEqual(self.session.get_event_last_params('update.cleep.update'), {'status': status['status']})
        self.assertTrue(self.module._store_process_status.called)
        self.module._update_config.assert_called_with({'cleepupdate': {'version': None, 'changelog': None, 'packageurl': None, 'checksumurl': None}})
        self.assertTrue(self.module.cleep_filesystem.disable_write.called)
        self.assertFalse(self.module._restart_cleep.called)

    def test_get_module_infos_from_inventory(self):
        mock_sendcommand = Mock(return_value={'error': False, 'msg': '', 'data': INVENTORY_GETMODULES['data']['audio']})
        self.init_context(mock_sendcommand=mock_sendcommand)

        infos = self.module._get_module_infos_from_inventory('audio')
        logging.debug('Infos: %s' % infos)

        self.assertEqual(infos, INVENTORY_GETMODULES['data']['audio'])

    def test_get_module_infos_from_inventory_failed(self):
        mock_sendcommand = Mock(return_value={'error': True, 'msg': '', 'data': None})
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'Unable to get module "audio" infos')

    def test_get_module_infos_from_inventory_unknown_module(self):
        mock_sendcommand = Mock(return_value={'error': False, 'msg': '', 'data': None})
        self.init_context(mock_sendcommand=mock_sendcommand)

        with self.assertRaises(Exception) as cm:
            self.module._get_module_infos_from_inventory('audio')
        self.assertEqual(str(cm.exception), 'Module "audio" not found in installable modules list')

    @patch('backend.update.Install')
    def test_install_module(self, mock_install):
        self.init_context()
        self.module._get_module_infos_from_modules_json = Mock(return_value=MODULES_JSON['list']['audio'])
        mock_install.return_value.install_module = Mock()
        self.assertTrue(self.module.install_module('dummy'))

        self.assertEqual(mock_install.return_value.install_module.call_count, 1)

    @patch('backend.update.Install')
    def test_install_module_circular_deps(self, mock_install):
        self.init_context()
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[
            MODULES_JSON['list']['circular2'],
            MODULES_JSON['list']['circular1'],
        ])
        mock_install.return_value.install_module = Mock()
        self.assertTrue(self.module.install_module('circular1'))

        # self.assertEqual(mock_install.return_value.install_module.call_count, 1)

    @patch('backend.update.Install')
    def test_install_module_with_deps(self, mock_install):
        self.init_context()
        self.module._get_module_infos_from_modules_json = Mock(return_value=MODULES_JSON['list']['sensors'])
        mock_install.return_value.install_module = Mock()
        self.assertTrue(self.module.install_module('dummy'))

        self.assertEqual(mock_install.return_value.install_module.call_count, 2)

    @patch('backend.update.Install')
    def test_install_module_postponed(self, mock_install):
        self.init_context()
        self.module._get_module_infos_from_modules_json = Mock(return_value=MODULES_JSON['list']['sensors'])
        mock_install.return_value.install_module = Mock()
        
        self.assertTrue(self.module.install_module('dummy'))
        self.assertFalse(self.module.install_module('dummy2'))

    @patch('backend.update.Install')
    def test_install_module_already_installed(self, mock_install):
        self.init_context()
        self.module._get_module_infos_from_modules_json = Mock(return_value=MODULES_JSON['list']['sensors'])
        mock_install.return_value.install_module = Mock()
        
        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_module('system')
        self.assertEqual(str(cm.exception), 'Module "system" is already installed')

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
        self.assertFalse(self.module.cleep_filesystem.disable_write.called)

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
        self.module.cleep_filesystem.disable_write.assert_called_with(True, True)

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

        self.module._Update__install_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.install'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.install_module.called)
        self.module.cleep_filesystem.disable_write.assert_called_with(True, True)

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
            { 'deps': ['dummy3'] }, # dummy2 deps
            { 'deps': ['dummy4'] }, # dummy3 deps
            { 'deps': [] }, # dummy4 deps
        ])
        modules_infos = {
            'dummy1': {
                'deps': ['dummy2'],
            }
        }
        self.init_context()

        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(sorted(deps), ['dummy1', 'dummy2', 'dummy3', 'dummy4'])

    def test_get_module_dependencies_complex(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy3', 'dummy4'] }, # dummy2 deps
            { 'deps': ['dummy5'] }, # dummy3 deps
            { 'deps': ['dummy5', 'dummy6'] }, # dummy4 deps
            { 'deps': ['dummy6'] }, # dummy5 deps
            { 'deps': [] }, # dummy6 deps
        ])
        modules_infos = {
            'dummy1': {
                'deps': ['dummy2'],
            }
        }
        self.init_context()

        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(sorted(deps), ['dummy1', 'dummy2', 'dummy3', 'dummy4', 'dummy5', 'dummy6'])

    def test_get_module_dependencies_circular_deps(self):
        callback = Mock(side_effect=[
            { 'deps': ['dummy3'] }, # dummy2 deps
            { 'deps': ['dummy1'] }, # dummy3 deps
        ])
        modules_infos = {
            'dummy1': {
                'deps': ['dummy2'],
            }
        }
        self.init_context()

        deps = self.module._get_module_dependencies('dummy1', modules_infos, callback)
        logging.debug('Deps: %s' % deps)

        self.assertEqual(sorted(deps), ['dummy1', 'dummy2', 'dummy3'])

    @patch('backend.update.Install')
    def test_uninstall_module(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':[], 'loadedby': []}})
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.uninstall_module('dummy'))

        self.assertEqual(mock_install.return_value.uninstall_module.call_count, 1)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.uninstall_module.assert_called_with('dummy', infos_dummy, False)

    @patch('backend.update.Install')
    def test_uninstall_module_with_deps(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':['audio'], 'loadedby': []}})
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
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.uninstall_module('dummy'))

        self.assertEqual(mock_install.return_value.uninstall_module.call_count, 3)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.uninstall_module.assert_has_calls([
            call('dummy', infos_dummy, False),
            call('dep1', infos_dep1, False),
            call('dep2', infos_dep2, False)
        ], any_order=True)

    @patch('backend.update.Install')
    def test_uninstall_module_with_circular_deps(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':['audio'], 'loadedby': []}})
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
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.uninstall_module('dummy'))

        self.assertEqual(mock_install.return_value.uninstall_module.call_count, 3)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.uninstall_module.assert_has_calls([
            call('dummy', infos_dummy, False),
            call('dep1', infos_dep1, False),
            call('dep2', infos_dep2, False),
        ], any_order=True)

    @patch('backend.update.Install')
    def test_uninstall_module_with_uninstallable_deps(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':['audio'], 'loadedby': []}})
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
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy, infos_dep1, infos_dep2])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.uninstall_module('dummy'))

        self.assertEqual(mock_install.return_value.uninstall_module.call_count, 2)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.uninstall_module.assert_has_calls([
            call('dummy', infos_dummy, False),
            call('dep2', infos_dep2, False),
        ], any_order=True)

    @patch('backend.update.Install')
    def test_uninstall_module_forced(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':[], 'loadedby': []}})
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.uninstall_module('dummy', force=True))

        self.assertEqual(mock_install.return_value.uninstall_module.call_count, 1)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.uninstall_module.assert_called_with('dummy', infos_dummy, True)

    @patch('backend.update.Install')
    def test_uninstall_module_check_params(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':[], 'loadedby': []}})
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        mock_install.return_value.uninstall_module = Mock()

        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_module('')
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_module(None)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

    @patch('backend.update.Install')
    def test_uninstall_module_not_installed_module(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={})

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_module('dummy')
        self.assertEqual(str(cm.exception), 'Module "dummy" is not installed')

    @patch('backend.update.Install')
    def test_uninstall_module_postponed(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={
            'dummy': {'deps':[], 'loadedby': []},
            'dummy2': {'deps':[], 'loadedby': []}
        })
        infos_dummy = {
            'loadedby': [],
            'deps': []
        }
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy])
        mock_install.return_value.uninstall_module = Mock()

        self.assertTrue(self.module.uninstall_module('dummy'))
        self.assertFalse(self.module.uninstall_module('dummy2'))

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
        self.assertFalse(self.module.cleep_filesystem.disable_write.called)

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
        self.module.cleep_filesystem.disable_write.assert_called_with(True, True)

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

        self.module._Update__uninstall_module_callback(status)

        self.module._store_process_status.assert_called_with(status)
        self.assertEqual(self.session.get_event_calls('update.module.uninstall'), 1)
        self.assertFalse(self.module._need_restart)
        self.assertFalse(mock_cleepconf.return_value.uninstall_module.called)
        self.module.cleep_filesystem.disable_write.assert_called_with(True, True)

    @patch('backend.update.Install')
    def test_update_module(self, mock_install):
        self.init_context()
        self.module._get_installed_modules = Mock(return_value={'dummy': {'deps':[], 'loadedby': []}})
        infos_dummy_old = MODULES_JSON['list']['sensors']
        infos_dummy_new = INVENTORY_GETMODULES['data']['sensors']
        self.module._get_module_infos_from_inventory = Mock(side_effect=[infos_dummy_old])
        self.module._get_module_infos_from_modules_json = Mock(side_effect=[infos_dummy_new])
        mock_install.return_value.uninstall_module = Mock()
        self.assertTrue(self.module.update_module('dummy'))

        self.assertEqual(mock_install.return_value.update_module.call_count, 1)
        self.assertTrue(self.module.cleep_filesystem.enable_write.called)
        mock_install.return_value.update_module.assert_called_with('dummy', infos_dummy_new)



if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_update.py; coverage report -m -i
    unittest.main()
    
