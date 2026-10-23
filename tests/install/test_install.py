#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
from backend.install.install import Install
from cleep.exception import MissingParameter, InvalidParameter
import unittest
import logging
from unittest.mock import Mock, patch, ANY
from threading import Timer
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()


INSTALLDEB_STATUS_IDLE = 0 
INSTALLDEB_STATUS_RUNNING = 1 
INSTALLDEB_STATUS_DONE = 2 
INSTALLDEB_STATUS_ERROR = 3 
INSTALLDEB_STATUS_KILLED = 4 
INSTALLDEB_STATUS_TIMEOUT = 5

INSTALLMODULE_STATUS_IDLE = 0
INSTALLMODULE_STATUS_INSTALLING = 1
INSTALLMODULE_STATUS_INSTALLED = 2
INSTALLMODULE_STATUS_ERROR_INTERNAL = 4

UNINSTALLMODULE_STATUS_IDLE = 0
UNINSTALLMODULE_STATUS_UNINSTALLING = 1
UNINSTALLMODULE_STATUS_UNINSTALLED = 2
UNINSTALLMODULE_STATUS_ERROR_INTERNAL = 3

UPDATEMODULE_STATUS_IDLE = 0
UPDATEMODULE_STATUS_UPDATING = 1
UPDATEMODULE_STATUS_UPDATED = 2
UPDATEMODULE_STATUS_ERROR = 3

mock_endlessconsole = Mock()
mock_installdeb = Mock()
mock_installdeb.STATUS_IDLE.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_IDLE
mock_installdeb.STATUS_RUNNING.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_RUNNING
mock_installdeb.STATUS_DONE.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_DONE
mock_installdeb.STATUS_ERROR.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_ERROR
mock_installdeb.STATUS_KILLED.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_KILLED
mock_installdeb.STATUS_TIMEOUT.__eq__ = lambda self, other: other == INSTALLDEB_STATUS_TIMEOUT

mock_installmodule = Mock()
mock_installmodule.STATUS_IDLE.__eq__ = lambda self, other: other == INSTALLMODULE_STATUS_IDLE
mock_installmodule.STATUS_INSTALLING.__eq__ = lambda self, other: other == INSTALLMODULE_STATUS_INSTALLING
mock_installmodule.STATUS_INSTALLED.__eq__ = lambda self, other: other == INSTALLMODULE_STATUS_INSTALLED
mock_installmodule.STATUS_ERROR_INTERNAL.__eq__ = lambda self, other: other == INSTALLMODULE_STATUS_ERROR_INTERNAL

mock_uninstallmodule = Mock()
mock_uninstallmodule.STATUS_IDLE.__eq__ = lambda self, other: other == UNINSTALLMODULE_STATUS_IDLE
mock_uninstallmodule.STATUS_UNINSTALLING.__eq__ = lambda self, other: other == UNINSTALLMODULE_STATUS_UNINSTALLING
mock_uninstallmodule.STATUS_UNINSTALLED.__eq__ = lambda self, other: other == UNINSTALLMODULE_STATUS_UNINSTALLED
mock_uninstallmodule.STATUS_ERROR_INTERNAL.__eq__ = lambda self, other: other == UNINSTALLMODULE_STATUS_ERROR_INTERNAL

mock_updatemodule = Mock()
mock_updatemodule.STATUS_IDLE.__eq__ = lambda self, other: other == UPDATEMODULE_STATUS_IDLE
mock_updatemodule.STATUS_UPDATING.__eq__ = lambda self, other: other == UPDATEMODULE_STATUS_UPDATING
mock_updatemodule.STATUS_UPDATED.__eq__ = lambda self, other: other == UPDATEMODULE_STATUS_UPDATED
mock_updatemodule.STATUS_ERROR.__eq__ = lambda self, other: other == UPDATEMODULE_STATUS_ERROR

@patch('backend.install.install.EndlessConsole', mock_endlessconsole)
@patch('backend.install.install.InstallDeb', mock_installdeb)
@patch('backend.install.install.InstallModule', mock_installmodule)
@patch('backend.install.install.UninstallModule', mock_uninstallmodule)
@patch('backend.install.install.UpdateModule', mock_updatemodule)
class InstallTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        mock_endlessconsole.reset_mock()
        mock_installdeb.reset_mock()
        mock_installmodule.reset_mock()
        mock_uninstallmodule.reset_mock()

    def init_lib(self, blocking=False):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        self.status_callback = Mock()
        self.task_factory = Mock()

        self.i = Install(self.cleep_filesystem, self.crash_report, self.task_factory, self.status_callback, blocking)

    def end_callback(self, status=Install.STATUS_DONE):
        self.i._Install__running = False
        self.i.status = status

    def test_get_status(self):
        self.init_lib()

        status = self.i.get_status()

        self.assertListEqual(sorted(list(status.keys())), sorted(['status', 'stdout', 'stderr']))

    def test_end_callback(self):
        self.init_lib()

        self.i._Install__callback_end(0, False)

        self.assertEqual(self.i.status, Install.STATUS_DONE)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.status_callback.assert_called_with({'status': ANY, 'stderr': ANY, 'stdout': ANY})

    def test_end_callback_command_failed(self):
        self.init_lib()

        self.i._Install__callback_end(1, False)

        self.assertEqual(self.i.status, Install.STATUS_ERROR)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.status_callback.assert_called_with({'status': ANY, 'stderr': ANY, 'stdout': ANY})

    def test_end_callback_command_killed(self):
        self.init_lib()

        self.i._Install__callback_end(0, True)

        self.assertEqual(self.i.status, Install.STATUS_ERROR)
        self.assertTrue(self.cleep_filesystem.disable_write.called)
        self.status_callback.assert_called_with({'status': ANY, 'stderr': ANY, 'stdout': ANY})

    @patch('backend.install.install.Install._Install__reset_status')
    def test_refresh_system_packages_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.refresh_system_packages())

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get update', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_refresh_system_packages_blocking(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.refresh_system_packages())

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get update', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)

    def test_refresh_system_packages_blocking_failed(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.refresh_system_packages())

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get update', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)

    def test_refresh_system_packages_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.refresh_system_packages()
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_callback_package(self):
        self.init_lib()

        self.i._Install__callback_package(stdout='out1', stderr='err1')

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': ANY,
        })

    @patch('backend.install.install.Install._Install__reset_status')
    def test_install_system_package_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.install_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get install -y "dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_install_system_package_blocking(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.install_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get install -y "dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)

    def test_install_system_packages_blocking_failed(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.install_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)

    def test_install_system_package_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.install_system_package('dummy')
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    @patch('backend.install.install.Install._Install__reset_status')
    def test_uninstall_system_package_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.uninstall_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get remove -y "dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_uninstall_system_package_blocking(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.uninstall_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get remove -y "dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)

    def test_uninstall_system_packages_blocking_failed(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.uninstall_system_package('dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)

    def test_uninstall_system_package_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.uninstall_system_package('dummy')
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_uninstall_system_package_purge(self):
        self.init_lib()

        self.assertTrue(self.i.uninstall_system_package('dummy', purge=True))

        self.assertTrue(self.cleep_filesystem.enable_write.called)
        mock_endlessconsole.assert_called_with('/usr/bin/apt-get purge -y "dummy"', ANY, ANY)

    def test_callback_deb_done(self):
        self.init_lib()
        status = {
            'status': INSTALLDEB_STATUS_DONE,
            'stdout': ['out1'],
            'stderr': ['err1'],
        }
        
        self.i._Install__callback_deb(status)

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': Install.STATUS_DONE,
        })

    def test_callback_deb_error(self):
        self.init_lib()
        status = {
            'status': INSTALLDEB_STATUS_ERROR,
            'stdout': ['out1'],
            'stderr': ['err1'],
        }
        
        self.i._Install__callback_deb(status)

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': Install.STATUS_ERROR,
        })

    def test_callback_deb_killed(self):
        self.init_lib()
        status = {
            'status': INSTALLDEB_STATUS_KILLED,
            'stdout': ['out1'],
            'stderr': ['err1'],
        }
        
        self.i._Install__callback_deb(status)

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': Install.STATUS_ERROR,
        })

    def test_callback_deb_running(self):
        self.init_lib()
        status = {
            'status': INSTALLDEB_STATUS_RUNNING,
            'stdout': ['out1'],
            'stderr': ['err1'],
        }
        
        self.i._Install__callback_deb(status)

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': Install.STATUS_PROCESSING,
        })

    @patch('backend.install.install.Install._Install__reset_status')
    def test_install_deb_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.install_deb('dummy.deb'))

        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_installdeb.return_value.install.assert_called_with('dummy.deb', blocking=False, status_callback=ANY)
        self.assertTrue(mock_resetstatus.called)

    def test_install_deb_blocking(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.install_deb('dummy.deb'))

        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_installdeb.return_value.install.assert_called_with('dummy.deb', blocking=False, status_callback=ANY)

    def test_install_deb_blocking_failed(self):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.install_deb('dummy.deb'))

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_install_deb_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.install_deb('dummy.deb')
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_callback_archive(self):
        self.init_lib()

        self.i._Install__callback_archive(stdout='out1', stderr='err1')

        self.status_callback.assert_called_with({
            'stdout': ['out1'],
            'stderr': ['err1'],
            'status': ANY,
        })

    @patch('backend.install.install.Install._Install__reset_status')
    @patch('backend.install.install.os.path.exists')
    def test_install_archive_no_blocking_zip(self, mock_ospathexists, mock_resetstatus):
        self.init_lib()
        mock_ospathexists.return_value = True

        self.i.install_archive('dummy.zip', '/tmp/dummy')
        
        mock_endlessconsole.assert_called_with('/usr/bin/unzip "dummy.zip" -d "/tmp/dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(mock_resetstatus.called)

    @patch('backend.install.install.Install._Install__reset_status')
    @patch('backend.install.install.os.path.exists')
    def test_install_archive_no_blocking_targz(self, mock_ospathexists, mock_resetstatus):
        self.init_lib()
        mock_ospathexists.return_value = True

        self.assertTrue(self.i.install_archive('dummy.tar.gz', '/tmp/dummy'))
        
        mock_endlessconsole.assert_called_with('/bin/tar xzf "dummy.tar.gz" -C "/tmp/dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(mock_resetstatus.called)

    @patch('backend.install.install.Install._Install__reset_status')
    @patch('backend.install.install.os.path.exists')
    def test_install_archive_blocking_zip(self, mock_ospathexists, mock_resetstatus):
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback)
        t.start()
        mock_ospathexists.return_value = True

        self.assertTrue(self.i.install_archive('dummy.zip', '/tmp/dummy'))
        
        mock_endlessconsole.assert_called_with('/usr/bin/unzip "dummy.zip" -d "/tmp/dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(mock_resetstatus.called)

    @patch('backend.install.install.os.path.exists')
    def test_install_archive_blocking_failed(self, mock_ospathexists):
        mock_ospathexists.return_value = True
        self.init_lib(blocking=True)
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.install_archive('dummy.zip', '/tmp/dummy'))

        self.assertTrue(self.cleep_filesystem.enable_write.called)

    @patch('backend.install.install.Install._Install__reset_status')
    @patch('backend.install.install.os.path.exists')
    def test_install_archive_create_out_dir(self, mock_ospathexists, mock_resetstatus):
        self.init_lib()
        mock_ospathexists.side_effect = [True, False]

        self.i.install_archive('dummy.tar.gz', '/tmp/dummy')
        
        mock_endlessconsole.assert_called_with('/bin/tar xzf "dummy.tar.gz" -C "/tmp/dummy"', ANY, ANY)
        self.assertTrue(mock_endlessconsole.return_value.start.called)
        self.assertTrue(self.cleep_filesystem.enable_write.called)
        self.assertTrue(mock_resetstatus.called)
        self.cleep_filesystem.mkdir.assert_called_with('/tmp/dummy', recursive=True)

    @patch('backend.install.install.Install._Install__reset_status')
    @patch('backend.install.install.os.path.exists')
    def test_install_archive_unsupported_archive(self, mock_ospathexists, mock_resetstatus):
        self.init_lib()
        mock_ospathexists.side_effect = [True, False]

        with self.assertRaises(Exception) as cm:
            self.i.install_archive('dummy.rar', '/tmp/dummy')
        self.assertEqual(str(cm.exception), 'File format not supported. Only zip and tar.gz supported.')
        
        self.assertFalse(mock_endlessconsole.called)
        self.assertFalse(self.cleep_filesystem.enable_write.called)
        self.assertTrue(mock_resetstatus.called)

    def test_install_archive_check_params(self):
        self.init_lib()

        with self.assertRaises(Exception) as cm:
            self.i.install_archive('', '/tmp/dummy')
        self.assertEqual(str(cm.exception), 'Parameter "archive" is missing')
        with self.assertRaises(Exception) as cm:
            self.i.install_archive(None, '/tmp/dummy')
        self.assertEqual(str(cm.exception), 'Parameter "archive" is missing')

        with self.assertRaises(Exception) as cm:
            self.i.install_archive('dummy.zip', '')
        self.assertEqual(str(cm.exception), 'Parameter "install_path" is missing')
        with self.assertRaises(Exception) as cm:
            self.i.install_archive('dummy.zip', None)
        self.assertEqual(str(cm.exception), 'Parameter "install_path" is missing')

        with self.assertRaises(Exception) as cm:
            self.i.install_archive('dummy', '/tmp/dummy')
        self.assertEqual(str(cm.exception), 'Archive "dummy" does not exist')

    def test_install_archive_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.install_archive('dummy.zip', '/tmp/dummy')
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_callback_install_module_done(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_install_module({
            'module': 'dummy',
            'status': INSTALLMODULE_STATUS_INSTALLED,
            'updateprocess': False,
            'process': process,
            'stdout': ['out-line'],
            'stderr': ['err-line'],
        })

        self.assertEqual(self.i.status, Install.STATUS_DONE)
        self.assertListEqual(self.i.stdout, ['out-line'])
        self.assertListEqual(self.i.stderr, ['err-line'])
        self.status_callback.assert_called_with({
            'module': 'dummy',
            'status': Install.STATUS_DONE,
            'stdout': ['out-line'],
            'stderr': ['err-line'],
            'process': process,
            'updateprocess': False,
            'extra': None,
        })

    def test_callback_install_module_idle(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_install_module({
            'module': 'dummy',
            'status': INSTALLMODULE_STATUS_IDLE,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_IDLE)

    def test_callback_install_module_installing(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_install_module({
            'module': 'dummy',
            'status': INSTALLMODULE_STATUS_INSTALLING,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_PROCESSING)

    def test_callback_install_module_error_internal(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_install_module({
            'module': 'dummy',
            'status': INSTALLMODULE_STATUS_ERROR_INTERNAL,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_ERROR)

    @patch('backend.install.install.Install._Install__reset_status')
    def test_install_module_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.install_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_installmodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            update_process=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_installmodule.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_install_module_blocking(self):
        self.init_lib(blocking=True)
        mock_installmodule.return_value.is_installing.side_effect = [True, False]
        mock_installmodule.return_value.get_status.return_value = {'status': INSTALLMODULE_STATUS_INSTALLED}
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.install_module('dummy', {'infos': 'data'}))

        mock_installmodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            update_process=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_installmodule.return_value.start.called)
        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_install_module_blocking_with_package(self):
        self.init_lib(blocking=True)
        mock_installmodule.return_value.is_installing.side_effect = [True, False]
        mock_installmodule.return_value.get_status.return_value = {'status': INSTALLMODULE_STATUS_INSTALLED}
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.install_module('dummy', {'infos': 'data'}, extra={'package': 'archive.zip'}))

        mock_installmodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            update_process=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_installmodule.return_value.start.called)
        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_installmodule.return_value.set_package.assert_called_with('archive.zip')

    def test_install_module_blocking_failed(self):
        self.init_lib(blocking=True)
        mock_installmodule.return_value.is_installing.side_effect = [True, False]
        mock_installmodule.return_value.get_status.return_value = {
            'status': INSTALLMODULE_STATUS_ERROR_INTERNAL
        }
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.install_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_install_module_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.install_module('dummy', {'infos': 'data'})
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_install_module_check_parameters(self):
        self.init_lib()

        with self.assertRaises(MissingParameter) as cm:
            self.i.install_module('', {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.i.install_module(None, {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.i.install_module('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "module_infos" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.i.install_module('dummy', 123)
        self.assertEqual(str(cm.exception), 'Parameter "module_infos" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.i.install_module('dummy', {'data': 'data'}, None)
        self.assertEqual(str(cm.exception), 'Parameter "extra" is invalid')

    def test_callback_uninstall_module_done(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_uninstall_module({
            'module': 'dummy',
            'status': UNINSTALLMODULE_STATUS_UNINSTALLED,
            'updateprocess': False,
            'process': process,
            'stdout': ['out-line'],
            'stderr': ['err-line'],
        })

        self.assertEqual(self.i.status, Install.STATUS_DONE)
        self.assertListEqual(self.i.stdout, ['out-line'])
        self.assertListEqual(self.i.stderr, ['err-line'])
        self.status_callback.assert_called_with({
            'module': 'dummy',
            'status': Install.STATUS_DONE,
            'stdout': ['out-line'],
            'stderr': ['err-line'],
            'process': process,
            'updateprocess': False,
        })

    def test_callback_uninstall_module_idle(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_uninstall_module({
            'module': 'dummy',
            'status': UNINSTALLMODULE_STATUS_IDLE,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_IDLE)

    def test_callback_uninstall_module_uninstalling(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_uninstall_module({
            'module': 'dummy',
            'status': UNINSTALLMODULE_STATUS_UNINSTALLING,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_PROCESSING)

    def test_callback_uninstall_module_error_internal(self):
        self.init_lib()

        process = ['process1', 'process2'],
        self.i._Install__callback_uninstall_module({
            'module': 'dummy',
            'status': UNINSTALLMODULE_STATUS_ERROR_INTERNAL,
            'updateprocess': False,
            'process': process,
        })

        self.assertEqual(self.i.status, Install.STATUS_ERROR)

    @patch('backend.install.install.Install._Install__reset_status')
    def test_uninstall_module_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.uninstall_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_uninstallmodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            update_process=False,
            force_uninstall=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_uninstallmodule.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_uninstall_module_blocking(self):
        self.init_lib(blocking=True)
        mock_uninstallmodule.return_value.is_uninstalling.side_effect = [True, False]
        mock_uninstallmodule.return_value.get_status.return_value = {'status': UNINSTALLMODULE_STATUS_UNINSTALLED}
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.uninstall_module('dummy', {'infos': 'data'}))

        mock_uninstallmodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            update_process=False,
            force_uninstall=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_uninstallmodule.return_value.start.called)
        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_uninstall_module_blocking_failed(self):
        self.init_lib(blocking=True)
        mock_uninstallmodule.return_value.is_uninstalling.side_effect = [True, False]
        mock_uninstallmodule.return_value.get_status.return_value = {
            'status': UNINSTALLMODULE_STATUS_ERROR_INTERNAL
        }
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.uninstall_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_uninstall_module_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.uninstall_module('dummy', {'infos': 'data'})
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_uninstall_module_check_parameters(self):
        self.init_lib()

        with self.assertRaises(MissingParameter) as cm:
            self.i.uninstall_module('', {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.i.uninstall_module(None, {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.i.uninstall_module('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "module_infos" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.i.uninstall_module('dummy', 123)
        self.assertEqual(str(cm.exception), 'Parameter "module_infos" is invalid')

    @patch('backend.install.install.Install._Install__reset_status')
    def test_update_module_no_blocking(self, mock_resetstatus):
        self.init_lib()

        self.assertTrue(self.i.update_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)
        mock_updatemodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            force_uninstall=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_updatemodule.return_value.start.called)
        self.assertTrue(mock_resetstatus.called)

    def test_update_module_blocking(self):
        self.init_lib(blocking=True)
        mock_updatemodule.return_value.is_updating.side_effect = [True, False]
        mock_updatemodule.return_value.get_status.return_value = {'status': UPDATEMODULE_STATUS_UPDATED}
        t = Timer(0.4, self.end_callback)
        t.start()

        self.assertTrue(self.i.update_module('dummy', {'infos': 'data'}))

        mock_updatemodule.assert_called_with(
            'dummy',
            {'infos': 'data'},
            force_uninstall=False,
            status_callback=ANY,
            cleep_filesystem=self.cleep_filesystem,
            crash_report=self.crash_report,
            task_factory=self.task_factory,
        )
        self.assertTrue(mock_updatemodule.return_value.start.called)
        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_update_module_blocking_failed(self):
        self.init_lib(blocking=True)
        mock_updatemodule.return_value.is_updating.side_effect = [True, False]
        mock_updatemodule.return_value.get_status.return_value = {
            'status': UPDATEMODULE_STATUS_ERROR
        }
        t = Timer(0.4, self.end_callback, [Install.STATUS_ERROR])
        t.start()

        self.assertFalse(self.i.update_module('dummy', {'infos': 'data'}))

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_update_module_already_processing(self):
        self.init_lib()
        self.i.status = Install.STATUS_PROCESSING

        with self.assertRaises(Exception) as cm:
            self.i.update_module('dummy', {'infos': 'data'})
        self.assertEqual(str(cm.exception), 'Installer is already processing')

        self.assertFalse(self.cleep_filesystem.enable_write.called)

    def test_update_module_check_parameters(self):
        self.init_lib()

        with self.assertRaises(MissingParameter) as cm:
            self.i.update_module('', {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')
        with self.assertRaises(MissingParameter) as cm:
            self.i.update_module(None, {'info': 'data'})
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.i.update_module('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "new_module_infos" is missing')
        with self.assertRaises(InvalidParameter) as cm:
            self.i.update_module('dummy', 123)
        self.assertEqual(str(cm.exception), 'Parameter "new_module_infos" is invalid')

    def test_callback_update_module_done(self):
        self.init_lib()

        process_uninst = ['uninst1', 'uninst2']
        process_inst = ['inst1', 'inst2']
        self.i._Install__callback_update_module({
            'module': 'dummy',
            'status': UPDATEMODULE_STATUS_UPDATED,
            'uninstall': {
                'process': process_uninst,
                'stdout': ['u-out'],
                'stderr': ['u-err'],
            },
            'install': {
                'process': process_inst,
                'stdout': ['i-out'],
                'stderr': ['i-err'],
            },
        })

        self.assertEqual(self.i.status, Install.STATUS_DONE)
        self.assertListEqual(self.i.stdout, ['u-out', 'i-out'])
        self.assertListEqual(self.i.stderr, ['u-err', 'i-err'])
        self.status_callback.assert_called_with({
            'module': 'dummy',
            'status': Install.STATUS_DONE,
            'stdout': ['u-out', 'i-out'],
            'stderr': ['u-err', 'i-err'],
            'process': ['Uninstall process:'] + process_uninst + ['', 'Install process:'] + process_inst,
        })

    def test_callback_update_module_idle(self):
        self.init_lib()

        process_uninst = ['uninst1', 'uninst2']
        process_inst = ['inst1', 'inst2']
        self.i._Install__callback_update_module({
            'module': 'dummy',
            'status': UPDATEMODULE_STATUS_IDLE,
            'uninstall': {
                'process': process_uninst,
            },
            'install': {
                'process': process_inst,
            },
        })

        self.assertEqual(self.i.status, Install.STATUS_IDLE)

    def test_callback_update_module_updating(self):
        self.init_lib()

        process_uninst = ['uninst1', 'uninst2']
        process_inst = ['inst1', 'inst2']
        self.i._Install__callback_update_module({
            'module': 'dummy',
            'status': UPDATEMODULE_STATUS_UPDATING,
            'uninstall': {
                'process': process_uninst,
            },
            'install': {
                'process': process_inst,
            },
        })

        self.assertEqual(self.i.status, Install.STATUS_PROCESSING)

    def test_callback_update_module_error(self):
        self.init_lib()

        process_uninst = ['uninst1', 'uninst2']
        process_inst = ['inst1', 'inst2']
        self.i._Install__callback_update_module({
            'module': 'dummy',
            'status': UPDATEMODULE_STATUS_ERROR,
            'uninstall': {
                'process': process_uninst,
            },
            'install': {
                'process': process_inst,
            },
        })

        self.assertEqual(self.i.status, Install.STATUS_ERROR)


if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_install.py; coverage report -m -i
    unittest.main()

