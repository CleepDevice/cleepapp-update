#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import random
import copy
import importlib
import re
from cleep.exception import MissingParameter, InvalidParameter, CommandError, CommandInfo
from cleep.core import CleepModule
from cleep.libs.internals.installmodule import PATH_INSTALL
from cleep.libs.configs.modulesjson import ModulesJson
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.internals.cleepgithub import CleepGithub
import cleep.libs.internals.tools as Tools
from cleep import __version__ as CLEEP_VERSION
from cleep.libs.internals.installcleep import InstallCleep
from cleep.libs.internals.install import Install
from cleep.libs.internals.task import Task
from cleep.libs.internals.tools import compare_versions

class Update(CleepModule):
    """
    Update application
    """
    MODULE_AUTHOR = 'Cleep'
    MODULE_VERSION = '1.1.0'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Applications and Cleep updater'
    MODULE_LONGDESCRIPTION = 'Manage all Cleep applications and Cleep core updates.'
    MODULE_TAGS = ['update', 'application', 'module']
    MODULE_CATEGORY = 'APPLICATION'
    MODULE_COUNTRY = None
    MODULE_URLINFO = 'https://github.com/tangb/cleepmod-update'
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = 'https://github.com/tangb/cleepmod-update/issues'

    MODULE_CONFIG_FILE = 'update.conf'
    DEFAULT_CONFIG = {
        'cleepupdateenabled': False,
        'modulesupdateenabled': False,
        'cleepversion': '0.0.0',
        'cleeplastcheck': None,
        'moduleslastcheck': None,
    }

    CLEEP_GITHUB_OWNER = 'tangb'
    CLEEP_GITHUB_REPO = 'cleep'
    PROCESS_STATUS_SUCCESS_FILENAME = 'process_success.log'
    PROCESS_STATUS_FAILURE_FILENAME = 'process_failure.log'
    CLEEP_STATUS_FILEPATH = ''
    ACTION_MODULE_INSTALL = 'install'
    ACTION_MODULE_UPDATE = 'update'
    ACTION_MODULE_UNINSTALL = 'uninstall'

    MAIN_ACTIONS_TASK_INTERVAL = 1.0
    SUB_ACTIONS_TASK_INTERVAL = 1.0

    PYTHON_CLEEP_IMPORT_PATH = 'cleep.modules.'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Params:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)
        # self.logger.setLevel(logging.TRACE)

        # members
        self.modules_json = ModulesJson(self.cleep_filesystem)
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self._modules_updates = {}
        self._cleep_updates = {
            'updatable': False,
            'processing': False,
            'pending': False,
            'failed': False,
            'version': None,
            'changelog': None,
            'packageurl': None,
            'checksumurl': None,
        }
        self._check_update_time = {
            'hour': int(random.uniform(0, 24)),
            'minute': int(random.uniform(0, 60))
        }
        self.logger.info('Software updates will be checked every day at %(hour)02d:%(minute)02d' % self._check_update_time)
        self.__processor = None
        self._need_restart = False
        # contains main actions (install/uninstall/update)
        self.__main_actions = []
        self.__main_actions_task = None
        # contains sub actions of mains actions (to perform action on dependencies)
        self.__sub_actions = []
        self.__sub_actions_task = None
        self.compat_pattern = r"(.*?)([><=]{1,2})(\d+\.\d+\.\d+)"

        # events
        self.module_install_event = self._get_event('update.module.install')
        self.module_uninstall_event = self._get_event('update.module.uninstall')
        self.module_update_event = self._get_event('update.module.update')
        self.cleep_update_event = self._get_event('update.cleep.update')
        self.cleep_need_restart_event = self._get_event('system.cleep.needrestart')

    def _configure(self):
        """
        Configure module
        """
        self._set_config_field('cleepversion', CLEEP_VERSION)

    def _on_start(self):
        """
        Module is started
        """
        # init installed modules
        self._fill_modules_updates()

    def _on_stop(self):
        """
        Module stopped
        """
        self.__stop_actions_tasks()

    def get_module_config(self):
        """
        Return module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()
        config.update({
            'cleepupdatelogs': self._get_last_update_logs('cleep'),
        })

        return config

    def on_event(self, event):
        """
        Event received

        Params:
            event (MessageRequest): event data
        """
        if event['event'] == 'parameters.time.now':
            # update
            if (event['params']['hour'] == self._check_update_time['hour'] and
                    event['params']['minute'] == self._check_update_time['minute']):
                # check updates
                self.check_cleep_updates()
                self.check_modules_updates()

                # and perform updates if allowed
                # update in priority cleep then modules
                config = self._get_config()
                if config['cleepupdateenabled']:
                    try:
                        self.update_cleep()
                    except Exception: # pragma: no cover
                        self.crash_report.report_exception()
                elif config['modulesupdateenabled']:
                    try:
                        self.update_modules()
                    except Exception: # pragma: no cover
                        self.crash_report.report_exception()

    def get_modules_logs(self):
        """
        Return all modules logs

        Returns:
            dict: list of log files::

            {
                module name: {
                    timestamp (int)
                    path (string)
                    failed (bool)
                }
                ...
            }

        """
        out = {}

        if not os.path.exists(PATH_INSTALL):
            return out

        installed_modules = self._get_installed_modules_names()
        module_names = os.listdir(PATH_INSTALL)
        for module_name in module_names:
            if module_name == 'cleep':
                continue

            infos = self._get_last_update_logs(module_name)
            if not infos:
                continue

            infos.update({
                'name': module_name,
                'installed': module_name in installed_modules,
            })
            out[module_name] = infos

        return out

    def _get_last_update_logs(self, module_name):
        """
        Return infos about last cleep update logs

        Args:
            module_name (string): module name to search log for. If it is cleep last update
                                  log, specify "cleep" as module name.

        Returns:
            dict: last cleep update logs or None if no logs::

            {
                timestamp (int): logs file timestamp
                path (string): log file path
                failed (bool): True if last update failed
            }

        """
        path_success = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME)
        timestamp_success = 0
        if os.path.exists(path_success):
            timestamp_success = int(os.path.getmtime(path_success))
        path_failure = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME)
        timestamp_failure = 0
        if os.path.exists(path_failure):
            timestamp_failure = int(os.path.getmtime(path_failure))

        if timestamp_success == 0 and timestamp_failure == 0:
            return None

        # keep most recent one
        if timestamp_success > timestamp_failure:
            return {
                'timestamp': timestamp_success,
                'path': path_success,
                'failed': False,
            }

        return {
            'timestamp': timestamp_failure,
            'path': path_failure,
            'failed': True,
        }

    def get_logs(self, module_name):
        """
        Get logs content for specified module or cleep

        Args:
            module_name (string): module name. Specify "cleep" to retrieve logs for cleep
        """
        path_success = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME)
        timestamp_success = 0
        if os.path.exists(path_success):
            timestamp_success = int(os.path.getmtime(path_success))
        path_failure = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME)
        timestamp_failure = 0
        if os.path.exists(path_failure):
            timestamp_failure = int(os.path.getmtime(path_failure))

        if timestamp_success == 0 and timestamp_failure == 0:
            raise CommandError('There is no logs for app "%s"' % module_name)

        path = path_failure
        if timestamp_success > timestamp_failure:
            path = path_success

        lines = self.cleep_filesystem.read_data(path, encoding='utf8')
        if lines is None:
            raise CommandError('Error reading app "%s" logs file' % module_name)

        return ''.join(lines)

    def get_modules_updates(self):
        """
        Return list of modules updates

        Returns:
            dict: list of modules updates::

            {
                module name (string): {
                },
                ...
            }

        """
        return self._modules_updates

    def get_cleep_updates(self):
        """
        Return cleep update infos

        Returns:
            dict: Cleep update infos::

            {
                updatable (bool): true if new version available
                processing (bool): true if cleep update is running
                pending (bool): true if cleep update has been done and a restart is required
                failed (bool): True if last update failed
                version (string): new available version (format x.x.x) (None if no update)
                changelog (string): update changelog (None if no update)
                packageurl (string): package url (None if no update)
                checksumurl (string): package checksum url (None if no update)
            }

        """
        return self._cleep_updates

    def _get_installed_modules_names(self):
        """
        Return installed modules names

        Returns:
            list: list of modules names
        """
        # modules updates dict can contains module that are installing,
        # but there are not yet so we must filter them
        return [module['name'] for module in self._modules_updates.values() if module['version'] is not None]

    def __start_actions_tasks(self):
        """
        Start actions tasks.

        Tasks are not started if there are already running.
        Main actions and sub actions tasks are correlated, start them at the same time.
        """
        # main actions task
        if not self.__main_actions_task:
            self.logger.debug('Start main actions task')
            self.__main_actions_task = Task(
                Update.MAIN_ACTIONS_TASK_INTERVAL,
                self._execute_main_action_task,
                logger=self.logger,
            )
            self.__main_actions_task.start()

        # sub actions task
        if not self.__sub_actions_task:
            self.logger.debug('Start sub actions task')
            self.__sub_actions_task = Task(
                Update.SUB_ACTIONS_TASK_INTERVAL,
                self._execute_sub_actions_task,
                logger=self.logger,
            )
            self.__sub_actions_task.start()

    def __stop_actions_tasks(self):
        """
        Stop actions tasks.
        """
        if self.__main_actions_task:
            self.logger.debug('Stop main actions task')
            self.__main_actions_task.stop()
            self.__main_actions_task = None

        if self.__sub_actions_task:
            self.logger.debug('Stop sub actions task')
            self.__sub_actions_task.stop()
            self.__sub_actions_task = None

    def _execute_main_action_task(self):
        """
        Function triggered regularly to process main actions (only one running at a time)
        """
        action = {}
        try:
            self.logger.debug('Main actions in progress: %s (sub actions: %s)' % (
                len(self.__main_actions),
                len(self.__sub_actions)
            ))

            # check if action is already processing
            if len(self.__sub_actions) != 0 or self.__processor:
                self.logger.debug('Main action is processing, stop main action task here.')
                return

            # remove previous action if necessary
            if len(self.__main_actions) > 0 and self.__main_actions[len(self.__main_actions)-1]['processing']:
                self.__main_actions.pop()

            # is there main action to run ?
            if len(self.__main_actions) == 0 and len(self.__sub_actions) == 0 and not self.__processor:
                self.logger.debug('No more main action to execute, stop all tasks.')

                # send need restart event
                if self._need_restart:
                    self.cleep_need_restart_event.send()

                self.__stop_actions_tasks()
                return

            # compute sub actions
            action = self.__main_actions[len(self.__main_actions)-1]
            self.logger.debug('Processing action %s' % action)
            action['processing'] = True
            if action['action'] == Update.ACTION_MODULE_INSTALL:
                self._install_main_module(action['module'])
            elif action['action'] == Update.ACTION_MODULE_UNINSTALL:
                self._uninstall_main_module(action['module'], action['extra'])
            elif action['action'] == Update.ACTION_MODULE_UPDATE:
                self._update_main_module(action['module'])

            # if no action postponed it means process can be terminated here
            self.logger.debug('%d sub actions postponed' % len(self.__sub_actions))
            if len(self.__sub_actions) == 0:
                self.logger.debug('Stop current action here because no subaction to execute')
                return

            # update main action and module infos
            action['processing'] = True
            self._set_module_process(progress=0)

            # update progress step for all sub actions
            # this is done after all sub actions are stored to compute valid progress step
            progress_step = int(100 / len(self.__sub_actions))
            for sub_action in self.__sub_actions:
                sub_action['progressstep'] = progress_step

        except Exception as error:
            self.logger.exception('Error occured executing action: %s' % action)
            self._set_module_process(failed=True)
            if action:
                # store action error
                self._store_process_status(status={
                    'module': action['module'],
                    'error': str(error)
                }, success=False)

                # and send error event
                params = {
                    'module': action['module'],
                    'status': Install.STATUS_ERROR
                }
                if action['action'] == Update.ACTION_MODULE_INSTALL:
                    self.module_install_event.send(params)
                elif action['action'] == Update.ACTION_MODULE_UNINSTALL:
                    self.module_uninstall_event.send(params)
                elif action['action'] == Update.ACTION_MODULE_UPDATE:
                    self.module_update_event.send(params)

    def _execute_sub_actions_task(self):
        """
        Function triggered regularly to perform sub actions
        """
        self.logger.debug('Executing sub action')
        # check if sub action is being processed
        if self.__processor:
            self.logger.trace('Sub action is processing, stop sub action task here')
            return

        # return if no sub action in pipe
        if len(self.__sub_actions) == 0:
            self.logger.debug('No more sub actions to process, stop sub action task here')
            return

        # no running sub action, run next one
        sub_action = self.__sub_actions.pop()
        self.logger.debug('Poped sub action: %s' % sub_action)

        # is last sub actions execution failed ?
        if self._is_module_process_failed():
            self.logger.debug(
                'One of previous sub action failed during "%s" module process, stop here'
                % sub_action['main']
            )
            return

        # update module process progress
        self._set_module_process(inc_progress=sub_action['progressstep'])

        # launch sub action
        if sub_action['action'] == Update.ACTION_MODULE_INSTALL:
            self._install_module(sub_action['module'], sub_action['infos'], sub_action['module'] != sub_action['main'])
        elif sub_action['action'] == Update.ACTION_MODULE_UNINSTALL:
            self._uninstall_module(sub_action['module'], sub_action['infos'], sub_action['extra'])
        elif sub_action['action'] == Update.ACTION_MODULE_UPDATE:
            self._update_module(sub_action['module'], sub_action['infos'])

    def _get_processing_module_name(self):
        """
        Return processing module name

        Returns:
            string: processing module name or None if no module is processing
        """
        if len(self.__main_actions) == 0:
            return None

        action = self.__main_actions[len(self.__main_actions)-1]
        return action['module'] if action['processing'] else None

    def _set_module_process(self, progress=None, inc_progress=None, failed=None, pending=None, forced_module_name=None):
        """
        Set module process infos. Nothing is updated if no module is processing.

        Args:
            progress (int): set progress value to specified value (0-100)
            inc_progress (int): increase progress value with specified value
            failed (bool): action process failed if set to False
            pending (bool): True if module action termined successfully and app needs to be restarted
            forced_module_name (string): Force module name instead of getting it from currently processing one
        """
        # get processing module name
        module_name = forced_module_name if forced_module_name is not None else self._get_processing_module_name()
        if not module_name:
            self.logger.debug('Can\'t update module infos when no module is processing')
            return
        self.logger.debug('set_module_process [%s]: progress=%s inc_progress=%s failed=%s pending=%s forced_module_name=%s' % (
            module_name,
            progress,
            inc_progress,
            failed,
            pending,
            forced_module_name
        ))

        # make sure entry exists in modules updates (case when installing new module)
        if module_name not in self._modules_updates:
            module_infos = self._get_module_infos_from_modules_json(module_name)
            new_module_version = module_infos['version'] if module_infos else '0.0.0'
            self._modules_updates[module_name] = self.__get_module_update_data(module_name, None, new_module_version)

        # get module
        module = self._modules_updates[module_name]

        # handle process flags
        module['processing'] = True
        if progress is not None:
            module['update']['progress'] = progress
        elif inc_progress is not None:
            module['update']['progress'] += inc_progress
        if module['update']['progress'] > 100:
            module['update']['progress'] = 100
            module['processing'] = False
        if failed is not None:
            module['update']['failed'] = failed
            module['update']['progress'] = 100
            module['processing'] = False
        if pending is not None:
            module['pending'] = pending
            module['processing'] = not pending

    def _is_module_process_failed(self):
        """
        Return True if module process failed

        Returns:
            bool: True if module process failed
        """
        module_name = self._get_processing_module_name()
        if not module_name:
            self.logger.debug('Can\'t get process status while no module is processing')
            return True

        return self._modules_updates[module_name]['update']['failed']

    def _fill_modules_updates(self):
        """
        Get modules from inventory and fill useful data for updates.
        Note that only installed modules are used to fill dict

        Notes:
            modules_updates format:

                {
                    module name (string): dict returned by __get_module_update_data
                    ...
                }

        Raises:
            Exception if send command failed
        """
        # retrieve modules from inventory
        resp = self.send_command('get_modules', 'inventory', timeout=20)
        if resp.error:
            raise Exception('Unable to get modules list from inventory')
        inventory_modules = resp.data

        # save modules
        modules = {}
        for (module_name, module) in {k:v for (k, v) in inventory_modules.items() if v['installed']}.items():
            modules[module_name] = self.__get_module_update_data(module_name, module.get('version', '0.0.0'))
        self._modules_updates = modules

    def __get_module_update_data(self, module_name, installed_module_version, new_module_version=None):
        """
        Get module update data

        Args:
            module_name (string): module name
            installed_module_version (string): installed module version
            new_module_version (string): new module version after update

        Returns:
            dict: module update data::

                {
                    updatable (bool): True if module is updatable
                    processing (bool): True if module has action in progress
                    pending (bool): True if module has been updated/uninstalled/installed
                    name (string): module name
                    version (string): installed module version, None if module is not installed yet
                    update (dict): update data::

                        {
                            progress (int): progress percentage (0-100)
                            failed (bool): True if process has failed
                            version (string): update version
                            changelog (string): update changelog
                        }

                }

        """
        return {
            'updatable': False,
            'processing': False,
            'pending': False,
            'name': module_name,
            'version': installed_module_version,
            'update': {
                'progress': 0,
                'failed': False,
                'version': new_module_version,
                'changelog': None,
            },
        }

    def _restart_cleep(self, delay=10.0):
        """
        Restart cleep sending command to system module

        Args:
            delay (float): delay before restarting (default 10.0 seconds)
        """
        self.logger.info('Restart Cleep in %s seconds)' % delay)
        resp = self.send_command('restart_cleep', 'system', {'delay': delay})
        if resp.error:
            self.logger.error('Unable to restart Cleep')

    def check_cleep_updates(self):
        """
        Check for available cleep updates

        Notes:
            If GITHUB_TOKEN is referenced in env vars, it will also check pre-releases

        Returns:
            dict: last update infos::

                {
                    version (string): latest update version
                    changelog (string): latest update changelog
                    packageurl (string): latest update package url
                    checksumurl (string): latest update checksum url
                }

        """
        update = copy.deepcopy(self._cleep_updates)

        try:
            # get beta release if GITHUB_TOKEN env variable registered
            auth_string = None
            only_released = True
            if 'GITHUB_TOKEN' in os.environ:
                auth_string = 'token %s' % os.environ['GITHUB_TOKEN']
                only_released = False # used to get beta release

            github = CleepGithub(auth_string)
            releases = github.get_releases(
                self.CLEEP_GITHUB_OWNER,
                self.CLEEP_GITHUB_REPO,
                only_latest=True,
                only_released=only_released
            )
            if len(releases) > 0:
                # get latest version available
                latest_version = github.get_release_version(releases[0])
                latest_changelog = github.get_release_changelog(releases[0])
                self.logger.debug('Found latest update: %s - %s' % (latest_version, latest_changelog))

                self.logger.info('Cleep version status: latest %s - installed %s' % (latest_version, CLEEP_VERSION))
                if Tools.compare_versions(CLEEP_VERSION, latest_version):
                    # new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])
                    self.logger.trace('assets: %s' % assets)

                    # search for deb file
                    package_asset = None
                    for asset in assets:
                        if asset['name'].startswith('cleep_') and asset['name'].endswith('.deb'):
                            self.logger.debug('Found Cleep package asset: %s' % asset)
                            package_asset = asset
                            update['packageurl'] = asset['url']
                            break

                    # search for checksum file
                    if package_asset:
                        package_name = os.path.splitext(package_asset['name'])[0]
                        checksum_name = '%s.%s' % (package_name, 'sha256')
                        self.logger.debug('Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset['name'] == checksum_name:
                                self.logger.debug('Found checksum asset: %s' % asset)
                                update['checksumurl'] = asset['url']
                                break

                    if update['packageurl'] and update['checksumurl']:
                        update['updatable'] = True
                        update['version'] = latest_version
                        update['changelog'] = latest_changelog
                    else:
                        self.logger.warning('Cleep update is available but is was impossible to retrieve all needed data')
                        update['packageurl'] = None
                        update['checksumurl'] = None

                else:
                    # already up-to-date
                    self.logger.info('Cleep is already up-to-date')

            else:
                # no release found
                self.logger.warning('No Cleep release found during check')

        except Exception as error:
            self.logger.exception('Error occured during updates checking:')
            self.crash_report.report_exception()
            raise CommandError('Error occured during cleep update check') from error

        # update config
        self._set_config_field('cleeplastcheck', int(time.time()))
        self._cleep_updates = update

        return self._cleep_updates

    def check_modules_updates(self):
        """
        Check for modules updates.

        Returns:
            dict: last modules update infos::

                {
                    modulesupdates (bool): True if at least one module has an update
                    moduleslastcheck (int): last modules update check timestamp
                    modulesjsonupdated (bool): True if modules.json updated (front needs to force modules update)
                }

        """
        # update modules.json content
        try:
            modules_json_updated = self.modules_json.update()
            if modules_json_updated:
                new_modules_json = self.modules_json.get_json()
        except Exception as error:
            self.logger.exception('Unable to refresh modules list from repository')
            raise CommandError('Unable to refresh modules list from internet') from error

        update_available = False
        if modules_json_updated:
            # request inventory to update its modules list
            resp = self.send_command('reload_modules', 'inventory')
            if resp.error:
                self.logger.error('Error occured during inventory modules reloading: %s' % (resp.message))

            # check for modules updates available
            for module_name, module in self._modules_updates.items():
                try:
                    new_version = (new_modules_json['list'][module_name]['version'] if module_name in new_modules_json['list']
                                   else '0.0.0')
                    if Tools.compare_versions(module['version'], new_version):
                        # new version available for current module
                        update_available = True
                        module['updatable'] = True
                        module['update'] = {
                            'version': new_version,
                            'changelog': new_modules_json['list'][module_name]['changelog'],
                        }
                        self.logger.info('New version available for app "%s" (v%s => v%s)' % (
                            module_name,
                            module['version'],
                            new_version
                        ))
                    else:
                        # force module infos update in case of version revert in modules.json
                        module['updatable'] = False
                        module['update'] = {
                            'version': module['version'],
                            'changelog': '',
                        }
                        self.logger.debug('No new version available for app "%s" (v%s => v%s)' % (
                            module_name,
                            module['version'],
                            new_version
                        ))

                except Exception:
                    self.logger.exception('Invalid "%s" app infos from modules.json' % module_name)

        # update config
        config = {
            'modulesupdates': update_available,
            'moduleslastcheck': int(time.time())
        }
        self._update_config(config)

        return {
            'modulesupdates': update_available,
            'modulesjsonupdated': modules_json_updated,
            'moduleslastcheck': config['moduleslastcheck']
        }

    def _update_cleep_callback(self, status):
        """
        Cleep update callback

        Args:
            status (dict): update status
        """
        self.logger.debug('Cleep update callback status: %s' % status)

        # send process status (only status)
        self.cleep_update_event.send(params={'status': status['status']})

        # store final status when update terminated (successfully or not)
        if status['status'] >= InstallCleep.STATUS_UPDATED:
            # lock filesystem
            self.cleep_filesystem.disable_write(True, True)

        # handle end of cleep update
        if status['status'] == InstallCleep.STATUS_UPDATED:
            # update successful
            self.logger.info('Cleep update installed successfully. Restart now')
            self._store_process_status(status, success=True)

            # reset cleep update
            self._cleep_updates.update({
                'updatable': False,
                'processing': False,
                'pending': True,
                'failed': False,
                'version': None,
                'changelog': None,
                'packageurl': None,
                'checksumurl': None,
            })

            # restart cleep
            self._restart_cleep()

        elif status['status'] > InstallCleep.STATUS_UPDATED:
            # error occured
            self._store_process_status(status, success=False)
            self.logger.error('Cleep update failed. Please check process outpout')

            # reset cleep update
            self._cleep_updates.update({
                'processing': False,
                'pending': False,
                'failed': True,
            })

    def update_cleep(self):
        """
        Update Cleep installing debian package
        """
        # check
        if not self._cleep_updates['updatable']:
            raise CommandInfo('No Cleep update available, please launch update check first')
        if len(self.__main_actions) != 0:
            raise CommandInfo('Applications updates are in progress. Please wait end of it')

        # unlock filesystem
        self.cleep_filesystem.enable_write(True, True)

        # reset flags
        self._cleep_updates.update({
            'failed': False,
            'pending': False,
            'processing': True,
        })

        # launch update
        package_url = self._cleep_updates['packageurl']
        checksum_url = self._cleep_updates['checksumurl']
        self.logger.debug('Update Cleep: package_url=%s checksum_url=%s' % (package_url, checksum_url))
        update = InstallCleep(self.cleep_filesystem, self.crash_report)
        update.install(package_url, checksum_url, self._update_cleep_callback)

    def update_modules(self):
        """
        Update modules that can be updated. It consists of processing postponed main actions filled
        during module updates check.
        """
        if self._cleep_updates['processing'] or self._cleep_updates['pending']:
            raise CommandInfo('Cleep update is in progress. Please wait end of it')

        # fill main actions with upgradable modules
        for module in [
            module
            for module in self._modules_updates.values()
            if module["updatable"] and not module["processing"] and not module["pending"]
        ]:
            self._postpone_main_action(Update.ACTION_MODULE_UPDATE, module['name'])

        # start main actions task
        self.__start_actions_tasks()

    def _postpone_main_action(self, action, module_name, extra=None):
        """
        Postpone main action (module install/update/uninstall) in a FIFO list.

        Args:
            action (string): action name (see ACTION_XXX constants)
            module_name (string): module name concerned by action
            extra (any): extra data to send to action

        Returns:
            bool: True if new action postponed, False if action was already postponed
        """
        # search if similar action for same module already exists
        existing_actions = [
            action_obj
            for action_obj in self.__main_actions
            if action_obj["module"] == module_name and action_obj["action"] == action
        ]
        self.logger.trace('Existing_actions: %s' % existing_actions)
        if len(existing_actions) > 0:
            self.logger.debug('Same action "%s" for "%s" module already exists, drop it' % (action, module_name))
            return False

        self.logger.trace('Postpone main action "%s" for module "%s" (extra: %s)' % (action, module_name, extra))
        # set module is processing
        self._set_module_process(forced_module_name=module_name)

        # store main action
        self.__main_actions.insert(0, {
            'action': action,
            'module': module_name,
            'extra': extra,
            'processing': False,
        })

        # send event before it really starts to warn api clients
        params = {
            'status': Install.STATUS_PROCESSING,
            'module': module_name,
        }
        if action == self.ACTION_MODULE_INSTALL:
            self.module_install_event.send(params)
        elif action == self.ACTION_MODULE_UNINSTALL:
            self.module_uninstall_event.send(params)
        elif action == self.ACTION_MODULE_UPDATE:
            self.module_update_event.send(params)

        return True

    def _postpone_sub_action(self, action, module_name, module_infos, main_module_name, extra=None):
        """
        Postpone sub action (module install/update/uninstall) in a stand alone list.

        Args:
            action (string): action name (see ACTION_XXX constants)
            module_name (string): module name concerned by action
            module_infos (dict): module informations
            main_module_name (string): main module name
            extra (any): any extra data
        """
        self.__sub_actions.insert(0, {
            'action': action,
            'module': module_name,
            'main': main_module_name,
            'infos': module_infos,
            'extra': extra,
            'progressstep': None, # will be set after all sub actions are computed
        })

    def set_automatic_update(self, cleep_update_enabled, modules_update_enabled):
        """
        Set automatic update values

        Args:
            cleep_update_enabled (bool): enable cleep automatic update
            modules_update_enabled (bool): enable modules automatic update

        Returns:
            dict: update flags::

                {
                    cleepupdateenabled (bool): True if cleep update enabled
                    modulesupdateenabled (bool): True if module update enabled
                }

        """
        if not isinstance(cleep_update_enabled, bool):
            raise InvalidParameter('Parameter "cleep_update_enabled" is invalid')
        if not isinstance(modules_update_enabled, bool):
            raise InvalidParameter('Parameter "modules_update_enabled" is invalid')

        # stop modules update task if necessary
        if not modules_update_enabled and self.__main_actions_task:
            self.__main_actions_task.stop()

        return self._update_config({
            'cleepupdateenabled': cleep_update_enabled,
            'modulesupdateenabled': modules_update_enabled
        })

    def _get_module_infos_from_modules_json(self, module_name):
        """
        Return modules infos from modules.json file

        Args:
            module_name (string): module name

        Returns:
            dict: module infos or None if module not found

        Raises:
            Exception if modules.json is invalid
        """
        modules_json = self.modules_json.get_json()
        if module_name in modules_json['list']:
            return modules_json['list'][module_name]

        return None

    def _get_module_infos_from_inventory(self, module_name):
        """
        Return module infos from modules.json file

        Args:
            module_name (string): module name

        Returns:
            dict: module infos

        Raises:
            Exception if unknown module or error
        """
        # get infos from inventory
        resp = self.send_command('get_module_infos', 'inventory', {'module_name': module_name})
        if resp.error:
            self.logger.error('Unable to get module "%s" infos: %s' % (module_name, resp.message))
            raise Exception('Unable to get module "%s" infos' % module_name)
        if not resp.data:
            self.logger.error('Module "%s" not found in modules list' % module_name)
            raise Exception('Module "%s" not found in installable modules list' % module_name)

        return resp.data

    def __extract_compat(self, compat_str):
        """
        Extract parts from compat string

        Args:
            compat_str (string): compat string

        Returns:
            dict: compat string parts::

                {
                    module_name (string)
                    operator (string)
                    version (string)
                }

        """
        try:
            match = re.search(self.compat_pattern, compat_str)
            module_name = match.group(1)
            operator = match.group(2)
            version = match.group(3)
            return {
                'module_name': module_name,
                'operator': operator,
                'version': version,
            }
        except Exception as error:
            self.logger.debug('Exception occured during compat parsing: %s' % str(error))
            return {
                'module_name': None,
                'operator': None,
                'version': None,
            }

    def __check_dependencies_compatibility(self, module_name, dependencies, modules_infos_json):
        """
        Check dependencies compatibility

        Args:
            module_name (string): main module name
            dependencies (list): list of dependencies
            modules_infos_json (dict): modules informations

        Raises:
            Exception if one of dependencies if not compatible. It should breaks installation
        """
        for dependency in dependencies:
            module_infos = modules_infos_json.get(dependency) or {}
            compat_str = module_infos.get('compat', 'cleep<=%s' % CLEEP_VERSION)
            compat = self.__extract_compat(compat_str)
            self.logger.debug('Compat for "%s" dependency: %s' % (dependency, compat))
            if any([val is None for val in compat.values()]):
                raise Exception('Invalid compat string for "%s" application' % dependency)
            if compat['module_name'].lower() != 'cleep':
                raise Exception('Invalid compat string (invalid module name) for "%s" application' % dependency)
            if compat['operator'] not in ('<', '=', '<='):
                raise Exception('Invalid compat string (invalid operator) for "%s" application' % dependency)

            compare_strict = compat['operator'] == '<'
            if (compat["operator"] == "=" and CLEEP_VERSION != compat["version"]) or (
                compat["operator"] != "="
                and not compare_versions(CLEEP_VERSION, compat["version"], compare_strict)
            ):
                raise Exception(
                    'Application "%s" is not installable due to version incompatibility of app "%s" that requires %s to be installed' % (
                        module_name,
                        dependency,
                        compat_str
                    )
                )

    def __get_local_module_dependencies(self, module_name):
        """
        Install local module.
        This functions loads dynamically module and get MODULE_DEPS member content

        Args:
            module_name (string): module name

        Returns:
            list: list of local module dependencies::

                ['dep1', 'dep2', ...]

        """
        module_deps = []
        try:
            module_path = '%s%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name)
            module_ = importlib.import_module(module_path)
            app_filename = getattr(module_, 'APP_FILENAME', module_name)
            del module_
            class_path = '%s%s.%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name, app_filename)
            self.logger.trace('Importing module "%s"' % class_path)
            module_ = importlib.import_module(class_path)
            module_class_ = getattr(module_, app_filename.capitalize())
            module_deps = getattr(module_class_, 'MODULE_DEPS', [])
        except Exception:
            self.logger.exception(
                'Error loading locally installed application "%s". Dependencies may not be installed.' % module_name
            )

        return module_deps

    def _get_module_dependencies(self, module_name, modules_infos, get_module_infos_callback, context=None):
        """
        Get module dependencies. Specified module will be also returned in result.
        Returned items are ordered by descent with first item as deepest leaf.

        Args:
            module_name (string): module name
            module_infos (dict): module infos (as returned by _get_module_infos). It must contains
                                 infos of module_name to allow dependencies search.
            get_module_infos_callback (function): callback to get module infos. Can be either _get_module_infos_from_inventory
                                 or _get_module_infos_from_modules_json
            context (None): internal context for recursive call. Do not set.

        Returns:
            list: list of dependencies
        """
        if context is None:
            # initiate recursive process
            context = {
                'dependencies': [],
                'visited': [module_name],
            }
        elif module_name in context['visited']:
            # avoid circular deps
            return None

        # get module infos if needed
        if module_name not in modules_infos:
            infos = get_module_infos_callback(module_name)
            modules_infos[module_name] = infos

        # get list of dependencies
        if not modules_infos[module_name]:
            # no infos available, surely a locally installed module
            module_dependencies = self.__get_local_module_dependencies(module_name)
        else:
            # info available get dependencies from meta
            module_dependencies = modules_infos[module_name].get('deps', [])

        # get dependencies (recursive call)
        for dependency_name in module_dependencies:
            if dependency_name == module_name:
                # avoid infinite loop
                continue
            self._get_module_dependencies(dependency_name, modules_infos, get_module_infos_callback, context)

        context['dependencies'].append(module_name)
        return context['dependencies']

    def _store_process_status(self, status, success=True):
        """
        Store last module process status in filesystem

        Args:
            status (dict): process status
        """
        # if no module name specified in status, it means it's cleep process
        module_name = 'cleep' if 'module' not in status else status['module']

        # build and check path
        if success:
            fullpath = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_SUCCESS_FILENAME)
        else:
            fullpath = os.path.join(PATH_INSTALL, module_name, self.PROCESS_STATUS_FAILURE_FILENAME)
        path = os.path.join(PATH_INSTALL, module_name)
        if not os.path.exists(path):
            self.cleep_filesystem.mkdir(path, True)

        # store status
        self.logger.debug('Storing process status in "%s"' % fullpath)
        if not self.cleep_filesystem.write_json(fullpath, status):
            self.logger.error('Error storing module "%s" process status into "%s"' % (module_name, fullpath))

    def __install_module_callback(self, status):
        """
        Module install callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug('Module install callback status: %s' % status)

        # handle install success
        if status['status'] == Install.STATUS_DONE:
            # need to restart
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status['module'])
            self._store_process_status(status, success=True)

            # update cleep.conf only for main module not dependencies
            is_dependency = 'extra' in status and status['extra'].get('isdependency', False)
            if not is_dependency:
                self.cleep_conf.install_module(status['module'])

        elif status['status'] == Install.STATUS_ERROR:
            # set main action failed
            self._store_process_status(status, success=False)
            self._set_module_process(failed=True)

        # handle end of install to finalize install
        if status['status'] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None

        # send process status
        self.module_install_event.send(params={
            'status': status['status'],
            'module': status['module'],
        })

    def _install_module(self, module_name, module_infos, is_dependency):
        """
        Execute specified module installation

        Args:
            module_name (string): module name
            module_infos (dict): module infos
            is_dependency (bool): True if module to install is a dependency
        """
        if module_infos is None:
            # surely locally installed module, no need to perform complete install, just run final callback
            self.__install_module_callback({
                'process': ['Locally installed application'],
                'stdout': [],
                'stderr': [],
                'status': Install.STATUS_DONE,
                'module': module_name,
            })
            return

        # non blocking, end of process handled in specified callback
        try:
            self.__processor = Install(self.cleep_filesystem, self.crash_report, self.__install_module_callback)
            self.__processor.install_module(module_name, module_infos, extra={'isdependency': is_dependency})
        except Exception as error:
            self.crash_report.manual_report('Error installing module "%s"' % module_name, extra={'module_infos': module_infos})
            self.__install_module_callback({
                'process': ['Internal error during installation: %s' % str(error)],
                'stdout': [],
                'stderr': [],
                'status': Install.STATUS_ERROR,
                'module': module_name,
            })

    def _install_main_module(self, module_name):
        """
        Install main module. This function will install all dependencies and update modules
        if necessary.

        Args:
            module_name (string): module name to install
        """
        self.logger.trace('_install_main_module "%s"' % module_name)
        installed_modules = self._get_installed_modules_names()

        # compute dependencies to install
        modules_infos_json = {}
        dependencies = self._get_module_dependencies(module_name, modules_infos_json, self._get_module_infos_from_modules_json)
        self.logger.debug('Module "%s" dependencies: %s' % (module_name, dependencies))

        # check dependencies compatibility
        self.__check_dependencies_compatibility(module_name, dependencies, modules_infos_json)

        # schedule module + dependencies installs
        for dependency_name in dependencies:
            if dependency_name not in installed_modules:
                # install dependency
                self._postpone_sub_action(
                    Update.ACTION_MODULE_INSTALL,
                    dependency_name,
                    modules_infos_json[dependency_name],
                    module_name,
                )
            else:
                # check if already installed module needs to be updated
                module_infos_inventory = self._get_module_infos_from_inventory(dependency_name)
                if Tools.compare_versions(module_infos_inventory['version'], modules_infos_json[dependency_name]['version']):
                    self._postpone_sub_action(
                        Update.ACTION_MODULE_UPDATE,
                        dependency_name,
                        modules_infos_json[dependency_name],
                        module_name,
                    )

    def install_module(self, module_name):
        """
        Install specified module

        Args:
            module_name (string): module name to install

        Returns:
            bool: True if installation will starts
        """
        # check params
        if self._cleep_updates['processing'] or self._cleep_updates['pending']:
            raise CommandInfo('Cleep update is in progress. Please wait end of it')
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        if self.cleep_conf.is_module_installed(module_name):
            raise InvalidParameter('Module "%s" is already installed' % module_name)

        # check if module not already installed as library
        installed_modules = self._get_installed_modules_names()
        if module_name in installed_modules:
            self.logger.debug('Module "%s" is already installed as library, just enable it in cleep.conf' % module_name)
            self.cleep_conf.install_module(module_name)
            self._set_module_process(progress=100, failed=False, pending=True, forced_module_name=module_name)
            self.module_install_event.send(params={
                'status': Install.STATUS_DONE,
                'module': module_name,
            })
            self.cleep_need_restart_event.send()
            return True

        # postpone module installation
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_INSTALL,
            module_name
        )

        # start main actions task
        if postponed:
            self.__start_actions_tasks()

        return postponed

    def __uninstall_module_callback(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug('Module uninstall callback status: %s' % status)

        # handle process success
        if status['status'] == Install.STATUS_DONE:
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status['module'])
            self._store_process_status(status, success=True)

            # update cleep.conf
            self.cleep_conf.uninstall_module(status['module'])

        elif status['status'] == Install.STATUS_ERROR:
            # set main action failed
            self._set_module_process(failed=True, pending=True)
            self._store_process_status(status, success=False)

        # handle end of process
        if status['status'] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None

        # send process status to ui
        self.module_uninstall_event.send(params={
            'status': status['status'],
            'module': status['module'],
        })

    def _uninstall_module(self, module_name, module_infos, extra):
        """
        Execute specified module uninstallation

        Args:
            module_name (string): module name
            module_infos (dict): module infos
            extra (any): extra data (not used here)
        """
        try:
            self.__processor = Install(self.cleep_filesystem, self.crash_report, self.__uninstall_module_callback)
            self.__processor.uninstall_module(module_name, module_infos, extra['force'])
        except Exception as error:
            self.crash_report.manual_report('Error uninstalling module "%s"' % module_name, extra={'module_infos': module_infos})
            self.__uninstall_module_callback({
                'process': ['Internal error during uninstallation: %s' % str(error)],
                'stdout': [],
                'stderr': [],
                'status': Install.STATUS_ERROR,
                'module': module_name,
            })

    def _uninstall_main_module(self, module_name, extra):
        """
        Uninstall module. This function will uninstall useless dependencies.

        Args:
            module_name (string): module name
            extra (any): extra data
        """
        self.logger.trace('_uninstall_main_module "%s"' % module_name)
        # compute dependencies to uninstall
        modules_infos = {}
        dependencies = self._get_module_dependencies(module_name, modules_infos, self._get_module_infos_from_inventory)
        self.logger.debug('Module "%s" dependencies: %s' % (module_name, dependencies))
        modules_to_uninstall = self._get_modules_to_uninstall(dependencies, modules_infos)
        self.logger.info('Module "%s" uninstallation will remove "%s"' % (module_name, modules_to_uninstall))

        if len(modules_to_uninstall) == 0:
            # nothing to uninstall, stop process
            self.logger.debug('Module "%s" is surely still needed as library, just disable it in cleep.conf' % module_name)
            self.cleep_conf.uninstall_module(module_name)
            self._set_module_process(progress=100, failed=False, pending=True, forced_module_name=module_name)
            self.module_uninstall_event.send(params={
                'status': Install.STATUS_DONE,
                'module': module_name,
            })
            self.cleep_need_restart_event.send()
            return

        # schedule module + dependencies uninstalls
        for module_to_uninstall in modules_to_uninstall:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UNINSTALL,
                module_to_uninstall,
                modules_infos[module_to_uninstall],
                module_name,
                extra,
            )

    def uninstall_module(self, module_name, force=False):
        """
        Uninstall specified module

        Args:
            module_name (string): module name to uninstall
            force (bool): True to force uninstall even if error occured
        """
        # check params
        if self._cleep_updates['processing'] or self._cleep_updates['pending']:
            raise CommandInfo('Cleep update is in progress. Please wait end of it')
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        installed_modules = self._get_installed_modules_names()
        if module_name not in installed_modules:
            raise InvalidParameter('Module "%s" is not installed' % module_name)

        # postpone uninstall
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_UNINSTALL,
            module_name,
            extra={'force': force},
        )

        # start main actions task
        if postponed:
            self.__start_actions_tasks()

        return postponed

    def _get_modules_to_uninstall(self, modules_to_uninstall, modules_infos):
        """
        Look for modules to uninstall list and remove modules that cannot be removed
        due to dependency with other module still needed.

        Args:
            modules_to_uninstall (list): module names to uninstall
            modules_infos (dict): dict of modules infos

        Returns:
            list: modules names to uninstall
        """
        out = modules_to_uninstall[:]

        for module_to_uninstall in modules_to_uninstall:
            # fix potential missing module_infos
            if module_to_uninstall not in modules_infos:
                self.logger.warning('Module infos dict should contains "%s" module infos. '
                                    'Module won\'t be removed and can become an orphan.' % module_to_uninstall)
                module_infos = {
                    'loadedby': ['orphan']
                }
            else:
                module_infos = modules_infos[module_to_uninstall]

            for loaded_by in module_infos['loadedby']:
                if loaded_by not in modules_to_uninstall:
                    # do not uninstall this module because it is a dependency of another module
                    self.logger.debug('Do not uninstall module "%s" which is still needed by "%s" module' % (
                        module_to_uninstall,
                        loaded_by
                    ))
                    out.remove(module_to_uninstall)
                    break

            if self.cleep_conf.is_module_installed(module_to_uninstall):
                # do not uninstall module that has been installed by user
                out.remove(module_to_uninstall)

        return out

    def __update_module_callback(self, status):
        """
        Module update callback

        Args:
            status (dict): process status::

                {
                    process (list): process output
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug('Module update callback status: %s' % status)

        # handle process success
        if status['status'] == Install.STATUS_DONE:
            self._need_restart = True
            self._set_module_process(pending=True, forced_module_name=status['module'])
            self._store_process_status(status, success=True)

            # update cleep.conf adding module to updated ones
            self.cleep_conf.update_module(status['module'])

        elif status['status'] == Install.STATUS_ERROR:
            # set main action failed
            self._set_module_process(failed=True)
            self._store_process_status(status, success=False)

        # handle end of process
        if status['status'] >= Install.STATUS_DONE:
            # reset processor
            self.__processor = None

        # send process status to ui
        self.module_update_event.send(params={
            'status': status['status'],
            'module': status['module'],
        })

    def _update_module(self, module_name, module_infos):
        """
        Execute module update

        Params:
            module_name (string): module name to install
            module_infos (dict): module infos
        """
        self.__processor = Install(self.cleep_filesystem, self.crash_report, self.__update_module_callback)
        self.__processor.update_module(module_name, module_infos)

    def _update_main_module(self, module_name):
        """
        Update main module performing:
            - install of new dependencies
            - uninstall of old dependencies
            - update of modules

        Args:
            module_name (string): module name
        """
        self.logger.trace('_update_main_module "%s"' % module_name)
        # compute module dependencies
        modules_infos_inventory = {}
        modules_infos_json = {}
        old_dependencies = self._get_module_dependencies(
            module_name,
            modules_infos_inventory,
            self._get_module_infos_from_inventory
        )
        self.logger.debug('Module "%s" old dependencies: %s' % (module_name, old_dependencies))
        new_dependencies = self._get_module_dependencies(
            module_name,
            modules_infos_json,
            self._get_module_infos_from_modules_json
        )
        self.logger.debug('Module "%s" new dependencies: %s' % (module_name, new_dependencies))
        dependencies_to_uninstall = [mod_name for mod_name in old_dependencies if mod_name not in new_dependencies]
        self.logger.debug('Module "%s" requires to uninstall modules: %s' % (module_name, dependencies_to_uninstall))
        dependencies_to_install = [mod_name for mod_name in new_dependencies if mod_name not in old_dependencies]
        self.logger.debug('Module "%s" requires to install new modules: %s' % (module_name, dependencies_to_install))
        dependencies_to_update = [
            mod_name for mod_name in new_dependencies
            if mod_name in old_dependencies
            and Tools.compare_versions(modules_infos_inventory[mod_name]['version'], modules_infos_json[mod_name]['version'])
        ]
        self.logger.debug('Module "%s" requires to update modules: %s' % (module_name, dependencies_to_update))

        # postpone old dependencies uninstallations
        for mod_name in dependencies_to_uninstall:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UNINSTALL,
                mod_name,
                modules_infos_inventory[mod_name],
                module_name,
                extra={'force': True}, # always force to make sure module is completely uninstalled
            )

        # postpone new dependencies installations
        for mod_name in dependencies_to_install:
            self._postpone_sub_action(
                Update.ACTION_MODULE_INSTALL,
                mod_name,
                modules_infos_json[mod_name],
                module_name,
            )

        # postpone dependencies update
        for mod_name in dependencies_to_update:
            self._postpone_sub_action(
                Update.ACTION_MODULE_UPDATE,
                mod_name,
                modules_infos_json[mod_name],
                module_name,
            )

    def update_module(self, module_name):
        """
        Update specified module

        Args:
            module_name (string): module name to uninstall

        Returns:
            bool: True if module update started. False if update is postponed
        """
        # check params
        if self._cleep_updates['processing'] or self._cleep_updates['pending']:
            raise CommandInfo('Cleep update is in progress. Please wait end of it')
        if module_name is None or len(module_name) == 0:
            raise MissingParameter('Parameter "module_name" is missing')
        installed_modules = self._get_installed_modules_names()
        if module_name not in installed_modules:
            raise InvalidParameter('Module "%s" is not installed' % module_name)

        # postpone uninstall
        postponed = self._postpone_main_action(
            Update.ACTION_MODULE_UPDATE,
            module_name,
        )

        # start actions tasks
        if postponed:
            self.__start_actions_tasks()

        return postponed

