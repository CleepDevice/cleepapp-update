#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import random
import copy
import uuid
from cleep.exception import MissingParameter, InvalidParameter, CommandError, CommandInfo
from cleep.core import CleepModule
from cleep.libs.internals.installmodule import PATH_INSTALL
from cleep.libs.configs.modulesjson import ModulesJson
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.internals.cleepgithub import CleepGithub
import cleep.libs.internals.tools as Tools
from cleep import __version__ as VERSION
from cleep.libs.internals.installcleep import InstallCleep
from cleep.libs.internals.install import Install

class Update(CleepModule):
    """
    Update application
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.0.0'
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Applications and Cleep updater'
    MODULE_LONGDESCRIPTION = u'Manage all Cleep applications and Cleep core updates.'
    MODULE_TAGS = ['update', 'application', 'module']
    MODULE_CATEGORY = u'APPLICATION'
    MODULE_COUNTRY = None
    MODULE_URLINFO = u'https://github.com/tangb/cleepmod-update'
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = u'https://github.com/tangb/cleepmod-update/issues'

    MODULE_CONFIG_FILE = u'update.conf'
    DEFAULT_CONFIG = {
        'cleepupdateenabled': False,
        'modulesupdateenabled': False,
        'cleepupdate': {
            'version': None,
            'changelog': None,
            'packageurl': None,
            'checksumurl': None,
        },
        'cleeplastcheck': None,
        'modulesupdate': False,
        'moduleslastcheck': None,
    }

    CLEEP_GITHUB_OWNER = u'tangb'
    CLEEP_GITHUB_REPO = u'cleep'
    PROCESS_STATUS_FILENAME = 'process.log'
    CLEEP_STATUS_FILEPATH = ''
    ACTION_MODULE_INSTALL = 'install'
    ACTION_MODULE_UPDATE = 'update'
    ACTION_MODULE_UNINSTALL = 'uninstall'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Params:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.modules_json = ModulesJson(self.cleep_filesystem)
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self._modules_updates = {}
        self._check_update_time = {
            'hour': int(random.uniform(0, 24)),
            'minute': int(random.uniform(0, 60))
        }
        self.logger.debug('Next updates check will be performed @ %(hour)s:%(minute)s' % self._check_update_time)
        self.__processing_counter = 0
        self.__postponed_actions = {}
        self._need_restart = False

        # events
        self.update_module_install = self._get_event(u'update.module.install')
        self.update_module_uninstall = self._get_event(u'update.module.uninstall')
        self.update_module_update = self._get_event(u'update.module.update')
        self.update_cleep_update = self._get_event(u'update.cleep.update')

    def _configure(self):
        """
        Configure module
        """
        # download modules.json file if not exists
        if not self.modules_json.exists():
            self.logger.info(u'Download latest modules.json file from Cleep repository')
            self.modules_json.update()

    def event_received(self, event):
        """
        Event received

        Params:
            event (MessageRequest): event data
        """
        if event[u'event'] == u'parameters.time.now':
            # update
            if event[u'params'][u'hour'] == self._check_update_time['hour'] and event[u'params'][u'minute'] == self._check_update_time['minute']:
                # check updates
                self.check_cleep_updates()
                self.check_modules_updates()

                # and perform updates if allowed
                # update in priority cleep then modules
                config = self._get_config()
                if config[u'cleepupdateenabled']:
                    try:
                        self.update_cleep()
                    except Exception:
                        pass
                elif config[u'modulesupdateenabled']:
                    # TODO
                    self.update_modules()

    def _get_installed_modules(self):
        """
        Get modules from inventory and return useful data for updates.
        Note that only installed modules are returned.

        Returns:
            dict: modules dict::

                {
                    module name (string): module infos::
                        {
                            updatable (bool): True if module is updatable
                            updating (bool): True if module has update in progress
                            name (string): module name
                            version (string): installed module version
                            update (dict): update data::
                                {
                                    version (string): update version
                                    changelog (string): update changelog
                                }
                        },
                    ...
                }

        Raises:
            Exception if send command failed
        """
        # retrieve modules from inventory
        resp = self.send_command(u'get_modules', u'inventory', timeout=20)
        if not resp or resp[u'error']:
            raise Exception(u'Unable to get modules list from inventory')
        inventory_modules = resp[u'data']

        # save modules
        modules = {}
        for module_name in inventory_modules:
            # drop not installed modules
            if not inventory_modules[module_name][u'installed']:
                continue

            # add new entry
            modules[module_name] = {
                'updatable': self._modules_updates[module_name]['updatable'] if module_name in self._modules_updates else False,
                'updating': self._modules_updates[module_name]['updating'] if module_name in self._modules_updates else False,
                'name': module_name,
                'version': inventory_modules[module_name]['version'],
                'update': {
                    'version': self._modules_updates[module_name]['update']['version'] if module_name in self._modules_updates else None,
                    'changelog': self._modules_updates[module_name]['update']['changelog'] if module_name in self._modules_updates else None,
                }
            }
            
        return modules

    def _restart_cleep(self, delay=10.0):
        """
        Restart cleep sending command to system module

        Args:
            delay (float): delay before restarting (default 10.0 seconds)
        """
        resp = self.send_command(u'restart', u'system', { 'delay': delay })
        if not resp or resp['error']:
            self.logger.error('Unable to restart Cleep')

    def check_cleep_updates(self):
        """
        Check for available cleep updates

        Notes:
            If GITHUB_TOKEN is referenced in env vars, it will also check pre-releases

        Returns:
            dict: last update infos::

                {
                    cleeplastcheck (int): last cleep update check timestamp
                    cleepupdate (dict): latest cleep update informations::

                        {
                            version (string): latest update version
                            changelog (string): latest update changelog
                            packageurl (string): latest update package url
                            checksumurl (string): latest update checksum url
                        }

                }

        """
        # init
        update = {
            'version': None,
            'changelog': None,
            'packageurl': None,
            'checksumurl': None
        }

        try:
            # get beta release if GITHUB_TOKEN env variable registered
            auth_string = None
            only_released = True
            if u'GITHUB_TOKEN' in os.environ:
                auth_string = 'token %s' % os.environ[u'GITHUB_TOKEN']
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
                self.logger.debug(u'Found latest update: %s - %s' % (latest_version, latest_changelog))

                self.logger.info('Cleep version status: latest %s - installed %s' % (latest_version, VERSION))
                if Tools.compare_versions(VERSION, latest_version):
                    # new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])
                    self.logger.trace('assets: %s' % assets)

                    # search for deb file
                    package_asset = None
                    for asset in assets:
                        if asset[u'name'].startswith(u'cleep_') and asset[u'name'].endswith('.zip'):
                            self.logger.debug(u'Found Cleep package asset: %s' % asset)
                            package_asset = asset
                            update[u'packageurl'] = asset['url']
                            break

                    # search for checksum file
                    if package_asset:
                        package_name = os.path.splitext(package_asset[u'name'])[0]
                        checksum_name = u'%s.%s' % (package_name, u'sha256')
                        self.logger.debug(u'Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset[u'name'] == checksum_name:
                                self.logger.debug(u'Found checksum asset: %s' % asset)
                                update[u'checksumurl'] = asset['url']
                                break

                    if update[u'packageurl'] and update[u'checksumurl']:
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
                self.logger.warning(u'No Cleep release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')
            self.crash_report.report_exception()
            raise CommandError(u'Error occured during cleep update check')

        # update config
        config = {
            u'cleepupdate': update,
            u'cleeplastcheck': int(time.time())
        }
        self._update_config(config)

        return config

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
        # get inventory modules
        self._modules_updates = self._get_installed_modules()

        # store local modules list (from modules.json)
        current_modules_json = self.modules_json.get_json()
        
        # update modules.json content
        try:
            modules_json_updated = self.modules_json.update()
            new_modules_json = current_modules_json
            if modules_json_updated:
                new_modules_json = self.modules_json.get_json()
        except:
            self.logger.warning('Unable to refresh modules list from repository')
            raise CommandError('Unable to refresh modules list from internet')
        
        # check for modules updates available
        update_available = False
        if modules_json_updated:
            for module_name, module in self._modules_updates.items():
                try:
                    new_version = new_modules_json['list'][module_name]['version'] if module_name in new_modules_json['list'] else '0.0.0'
                    if Tools.compare_versions(module['version'], new_version):
                        # new version available for current module
                        update_available = True
                        self.logger.info('New version available for app "%s" (v%s => v%s)' % (
                            module_name,
                            module['version'],
                            new_version
                        ))
                        module['updatable'] = True
                    else:
                        self.logger.debug('No new version available for app "%s" (v%s => v%s)' % (
                            module_name,
                            module['version'],
                            new_version
                        ))

                except Exception:
                    self.logger.exception('Invalid "%s" app infos from modules.json' % module_name)

        # update config
        config = {
            u'modulesupdates': update_available,
            u'moduleslastcheck': int(time.time())
        }
        self._update_config(config)

        return {
            u'modulesupdates': update_available,
            u'modulesjsonupdated': modules_json_updated,
            u'moduleslastcheck': config[u'moduleslastcheck']
        }

    def _update_cleep_callback(self, status):
        """
        Cleep update callback
        Args:
            status (dict): update status
        """
        self.logger.debug(u'Cleep update callback status: %s' % status)

        # send process status (only status)
        self.update_cleep_update.send(params={u'status': status[u'status']})

        # store final status when update terminated (successfully or not)
        if status[u'status'] >= InstallCleep.STATUS_UPDATED:
            self._store_process_status(status)

            # reset cleep update config
            self._update_config({
                'cleepupdate': {
                    'version': None,
                    'changelog': None,
                    'packageurl': None,
                    'checksumurl': None,
                }
            })

            # lock filesystem
            self.cleep_filesystem.disable_write(True, True)

        # handle end of cleep update
        if status[u'status'] == InstallCleep.STATUS_UPDATED:
            # update successful
            self.logger.info('Cleep update installed successfully. Restart now')
            self._restart_cleep()
        elif status[u'status'] > InstallCleep.STATUS_UPDATED:
            # error occured
            self.logger.error('Cleep update failed. Please check process outpout')

    def update_cleep(self):
        """
        Update Cleep.

        It consists of installing deb file.
        """
        # check
        cleep_update = self._get_config_field('cleepupdate')
        if cleep_update['version'] is None:
            raise CommandInfo('No Cleep update available, please launch update check')

        # unlock filesystem
        self.cleep_filesystem.enable_write(True, True)

        # launch update
        package_url = cleep_update[u'packageurl']
        checksum_url = cleep_update[u'checksumurl']
        self.logger.debug(u'Update Cleep: package_url=%s checksum_url=%s' % (package_url, checksum_url))
        update = InstallCleep(package_url, checksum_url, self._update_cleep_callback, self.cleep_filesystem, self.crash_report)
        update.start()

    def __install_module_callback(self, status):
        """
        Module install callback

        Args:
            status (dict): process status::

                {
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug(u'Module install callback status: %s' % status)

        # send process status
        self.update_module_install.send(params=status)

        # save last module processing
        self._store_process_status(status)

        # handle install success
        if status[u'status'] == Install.STATUS_DONE:
            # need to restart
            self._need_restart = True

            # update cleep.conf
            self.cleep_conf.install_module(status[u'module'])
        
        # handle end of install to finalize install
        if status[u'status'] >= Install.STATUS_DONE:
            # decrease counter
            self.__processing_counter -= 1

            # lock filesystem
            if self.cleep_filesystem:
                self.cleep_filesystem.disable_write(True, True)

    def __install_module(self, module_name, installed_modules):
        """
        Install module

        Args:
            module_name (string): module name to install
            installed_modules (list): list of installed (or installing) modules names
        """
        # increase counter
        self.__processing_counter += 1

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # get module infos
        module_infos = self._get_module_infos_from_modules_json(module_name)
        self.logger.trace(u'Module "%s" infos: %s' % (module_name, module_infos))

        # install module dependencies if not already installed
        for dep_name in module_infos[u'deps']:
            # prevent from circular dependency
            if dep_name not in installed_modules:
                installed_modules.append(dep_name)
                self.logger.debug('Install module "%s" dependency "%s"' % (module_name, dep_name))
                self.__install_module(dep_name, installed_modules)

        # launch module installation (non blocking)
        self.logger.debug('Install module "%s"' % module_name)
        install = Install(self.cleep_filesystem, self.crash_report, self.__install_module_callback)
        install.install_module(module_name, module_infos)

    def install_module(self, module_name):
        """
        Install specified module

        Args:
            module_name (string): module name to install

        Returns:
            bool: True if module installation started. False if install is postponed
        """
        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter(u'Parameter "module_name" is missing')
        installed_modules = list(self._get_installed_modules().keys())
        if module_name in installed_modules:
            raise InvalidParameter('Module "%s" is already installed' % module_name)

        if self.__processing_counter != 0:
            # postpone install
            self.__postponed_actions[module_name] = {
                'action': Update.ACTION_MODULE_INSTALL,
                'module': module_name,
                'processing': self.__postponed_actions[module_name]['processing'] if module_name in self.__postponed_actions else False,
            }
            return self.__postponed_actions[module_name]['processing']

        # launch install
        installed_modules.append(module_name)
        self.__install_module(module_name, installed_modules)

        return True

    def __uninstall_module_callback(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): process status::

                {
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug(u'Module uninstall callback status: %s' % status)

        # send process status to ui
        self.update_module_uninstall.send(params=status)

        # save last module processing
        self._store_process_status(status)

        # handle process success
        if status[u'status'] == Install.STATUS_DONE:
            self._need_restart = True

            # update cleep.conf
            self.cleep_conf.uninstall_module(status[u'module'])

        # handle end of process
        if status['status'] >= Install.STATUS_DONE:
            # decrease counter
            self.__processing_counter -= 1

            # lock filesystem
            if self.cleep_filesystem:
                self.cleep_filesystem.disable_write(True, True)

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
            if module_to_uninstall not in modules_infos:
                self.logger.warning('Module infos dict should contains "%s" module infos. Module won\'t be removed and can become an orphan.' % module_to_uninstall)
                module_infos = {
                    'loadedby': ['orphan']
                }
            else:
                module_infos = modules_infos[module_to_uninstall]
            for loaded_by in module_infos[u'loadedby']:
                if loaded_by not in modules_to_uninstall:
                    # do not uninstall this module because it is a dependency of another module
                    self.logger.debug('Do not uninstall module "%s" which is still needed by "%s" module' % (
                        module_to_uninstall,
                        loaded_by
                    ))
                    out.remove(module_to_uninstall)
                    break

        return out

    def __uninstall_module(self, module_name, force=False):
        """
        Uninstall specified module

        Args:
            module_name (string): module name
            force (bool): force uninstallation even if error occured

        Returns:
            bool: True if module uninstalled successfully
        """
        # increase counter
        self.__processing_counter += 1

        # get module infos
        module_infos = self._get_module_infos_from_inventory(module_name)
        self.logger.debug(u'Module "%s" infos: %s' % (module_name, module_infos))

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # resolve module dependencies
        modules_infos = {
            module_name: module_infos
        }
        dependencies = self._get_module_dependencies(module_name, modules_infos, self._get_module_infos_from_inventory)
        self.logger.debug(u'Module "%s" dependencies: %s' % (module_name, dependencies))
        modules_to_uninstall = self._get_modules_to_uninstall(dependencies, modules_infos)

        # uninstall module + dependencies
        self.logger.info(u'Module "%s" uninstallation will remove "%s"' % (module_name, modules_to_uninstall))
        for module_to_uninstall in modules_to_uninstall:
            install = Install(self.cleep_filesystem, self.crash_report, self.__uninstall_module_callback)
            install.uninstall_module(module_to_uninstall, modules_infos[module_to_uninstall], force)

        return True

    def uninstall_module(self, module_name, force=False):
        """
        Uninstall specified module

        Args:
            module_name (string): module name to uninstall
            force (bool): True to force uninstall even if error occured

        Returns:
            bool: True if module uninstallation started. False if uninstall is postponed
        """
        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter(u'Parameter "module_name" is missing')
        installed_modules = list(self._get_installed_modules().keys())
        if module_name not in installed_modules:
            raise InvalidParameter('Module "%s" is not installed' % module_name)

        if self.__processing_counter != 0:
            # postpone uninstall
            self.__postponed_actions[module_name] = {
                'action': Update.ACTION_MODULE_UNINSTALL,
                'module': module_name,
                'processing': self.__postponed_actions[module_name]['processing'] if module_name in self.__postponed_actions else False,
            }
            return self.__postponed_actions[module_name]['processing']

        # launch install
        self.__uninstall_module(module_name, force)

        return True

    def __update_module_callback(self, status):
        """
        Module update callback

        Args:
            status (dict): process status::

                {
                    stdout (list): stdout output
                    stderr (list): stderr output
                    status (int): install status
                    module (string): module name
                }

        """
        self.logger.debug(u'Module update callback status: %s' % status)

        # send process status to ui
        self.update_module_update.send(params=status)

        # save last module processing
        self.__update_last_module_processing(status)

        # handle process success
        if status[u'status'] == Install.STATUS_DONE:
            self._need_restart = True

            # update cleep.conf adding module to updated ones
            self.cleep_conf.update_module(status[u'module'])

        # handle end of process
        if status['status'] >= Install.STATUS_DONE:
            # decrease counter
            self.__processing_counter -= 1

            # lock filesystem
            if self.cleep_filesystem:
                self.cleep_filesystem.disable_write(True, True)

    def __update_module(self, module_name):
        """
        Update specified module

        Params:
            module_name (string): module name to install
        """
        # get module infos
        module_infos = self._get_module_infos_from_modules_json(module_name)
        self.logger.debug(u'Module "%s" infos: %s' % (module_name, module_infos))

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # compute module dependencies
        modules_infos_inventory = {
            module_name: module_infos
        }
        modules_infos_json = {
            module_name: module_infos
        }
        old_dependencies = self._get_module_dependencies(module_name, modules_infos_inventory, self._get_module_infos_from_inventory)
        self.logger.trace('Module "%s" old dependencies: %s' % (module_name, old_dependencies))
        new_dependencies = self._get_module_dependencies(module_name, modules_infos_json, self._get_module_infos_from_modules_json)
        self.logger.trace('Module "%s" new dependencies: %s' % (module_name, new_dependencies))
        dependencies_to_uninstall = [mod_name for mod_name in old_dependencies if mod_name not in new_dependencies]
        self.logger.debug('Module "%s" requires to uninstall modules: %s' % (module_name, dependencies_to_uninstall))
        dependencies_to_install = [mod_name for mod_name in new_dependencies if mod_name not in old_dependencies]
        self.logger.debug('Module "%s" requires to install new modules: %s' % (module_name, dependencies_to_uninstall))
        dependencies_to_update = [
            mod_name for mod_name in new_dependencies
            if mod_name in old_dependencies
            and Tools.compare_versions(modules_infos_inventory[mod_name]['version'], modules_infos_json[mod_name]['version'])
        ]
        self.logger.debug('Module "%s" requires to update modules: %s' % (module_name, dependencies_to_update))

        # uninstall old dependencies
        for mod_name in dependencies_to_uninstall:
            uninstall = Install(self.cleep_filesystem, self.crash_report, self.__update_module_callback)
            uninstall.uninstall_module(mod_name, modules_infos_from_inventory)

        # install new dependencies
        for mod_name in dependencies_to_install:
            install = Install(self.cleep_filesystem, self.crash_report, self.__update_module_callback)
            install.install_module(mod_name, modules_infos_json)

        # update dependencies
        for mod_name in dependencies_to_update:
            update = Install(self.cleep_filesystem, self.crash_report, self.__update_module_callback)
            update.update_module(mod_name, module_infos_json)

        # update module
        install = Install(self.cleep_filesystem, self.crash_report, self.__update_module_callback)
        install.update_module(module_name, module_infos)

    def update_module(self, module_name):
        """
        Update specified module

        Args:
            module_name (string): module name to uninstall

        Returns:
            bool: True if module update started. False if update is postponed
        """
        # check params
        if module_name is None or len(module_name) == 0:
            raise MissingParameter(u'Parameter "module_name" is missing')
        installed_modules = list(self._get_installed_modules().keys())
        if module_name not in installed_modules:
            raise InvalidParameter('Module "%s" is not installed' % module_name)

        # schedule update
        self.__postponed_actions[module_name] = {
            'uuid': str(uuid.uuid4()),
            'action': Update.ACTION_MODULE_UPDATE,
            'module': module_name,
            'processing': self.__postponed_actions[module_name]['processing'] if module_name in self.__postponed_actions else False,
        }
        
        return self.__postponed_actions[module_name]['processing']

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

        return self._update_config({
            u'cleepupdateenabled': cleep_update_enabled,
            u'modulesupdateenabled': modules_update_enabled
        })

    def _get_module_infos_from_modules_json(self, module_name):
        """
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
        resp = self.send_command('get_module_infos', u'inventory', {'module': module_name})
        if resp['error'] == True:
            self.logger.error(u'Unable to get module "%s" infos: %s' % (module_name, resp[u'msg']))
            raise Exception('Unable to get module "%s" infos' % module_name)
        if resp['data'] is None:
            self.logger.error(u'Module "%s" not found in modules list' % module_name)
            raise Exception(u'Module "%s" not found in installable modules list' % module_name)

        return resp[u'data']

    def _get_module_dependencies(self, module_name, modules_infos, get_module_infos_callback, dependencies=None):
        """
        Get module dependencies. Specified module will be returned in result.

        Args:
            module_name (string): module name
            module_infos (dict): module infos (as returned by _get_module_infos). It must contains
                                 infos of module_name to allow dependencies search.
            get_module_infos_callback (function): callback to get module infos. Can be either _get_modules_infos_from_inventory
                                 or _get_modules_infos_from_modules_json

        Returns:
            list: list of dependencies
            dict: input parameter modules_infos is also updated
        """
        if dependencies is None:
            # initiate recursive process
            dependencies = [module_name]
        elif module_name in dependencies:
            # avoid circular deps
            return

        # get module infos
        if module_name in modules_infos:
            infos = modules_infos[module_name]
        else:
            infos = get_module_infos_callback(module_name)
            modules_infos[module_name] = infos

        # get dependencies (recursive call)
        for dependency_name in infos[u'deps']:
            if dependency_name == module_name:
                # avoid infinite loop
                continue
            if self._get_module_dependencies(dependency_name, modules_infos, get_module_infos_callback, dependencies):
                dependencies.append(dependency_name)

        return dependencies

    def _store_process_status(self, status):
        """
        Store last module process status in filesystem

        Args:
            status (dict): process status

        """
        # if no module name specified in status, it means it's cleep process
        module_name = 'cleep'
        if 'module' in status:
            module_name = status['module']

        # build and check path
        path = os.path.join(PATH_INSTALL, module_name, PROCESS_STATUS_FILENAME)
        if not os.path.exists(path):
            self.cleep_filesystem.mkdir(PATH_INSTALL, True)

        # store status
        if not self.cleep_filesystem.write_json(path, status):
            self.logger.error('Error storing module "%s" process status' % module_name)


