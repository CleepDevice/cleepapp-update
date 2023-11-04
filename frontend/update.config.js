/**
 * System config component
 * Handle system configuration
 **/
angular
.module('Cleep')
.directive('updateConfigComponent', ['$rootScope', 'cleepService', 'updateService', '$location', 'toastService', '$mdDialog', 'marked', 'blockUI', '$window', '$filter',
function($rootScope, cleepService, updateService, $location, toast, $mdDialog, marked, blockUI, $window, $filter) {
    var updateController = ['$scope', function($scope) {   
        var self = this;
        self.updateService = updateService;
        self.cleepService = cleepService;
        self.tabIndex = 'modules';
        self.config = {};
        self.cleepUpdateEnabled = false;
        self.modulesUpdateEnabled = false;
        self.cleepUpdates = null;
        self.moduleLogs = [];
        self.moduleUpdates = [];
        self.cleepInstallProgress = 'Updating Cleep...';

        self.setAutomaticUpdate = function(value, meta) {
            const options = {
                cleep: meta.type === 'cleep' ? value : self.cleepUpdateEnabled,
                apps: meta.type === 'apps' ? value : self.modulesUpdateEnabled,
            }

            // perform update
            updateService.setAutomaticUpdate(options.cleep, options.apps)
                .then(function(resp) {
                    if (resp.data === true) {
                        toast.success('Option saved');
                    } else {
                        toast.error('Error saving option');
                    }
                    return self.cleepService.reloadModuleConfig('update');
                })
        }

        self.checkCleepUpdates = function() {
            toast.loading('Checking Cleep updates...');
            var message = 'No update available';
            updateService.checkCleepUpdates()
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                    if (resp.data.updatable) {
                        message = 'Update available';
                    }

                    return self.cleepService.reloadModuleConfig('update');
                })
                .finally(function() {
                    toast.info(message);
                });
        };

        self.checkModulesUpdates = function() {
            toast.loading('Checking applications updates...');
            self.updateService.checkModulesUpdates()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    
                    cleepService.refreshModulesUpdates();
                    if (resp.data.modulesupdates) {
                        toast.success('There are applications updates available');
                    } else {
                        toast.info('No applications updates available');
                    }

                    return self.cleepService.reloadModuleConfig('update');
                });
        };

        self.gotoModulesPage = function(moduleName) {
            if (!moduleName) {
                return;
            }
            $window.location.href = '#!/modules?app=' + moduleName;
        };

        self.closeDialog = function() {
            $mdDialog.hide();
        };

        self.showLogsDialog = function(moduleName, $event) {
            $mdDialog.show({
                controller: function($mdDialog) {
                    this.logs = '';
                    this.logsBlockui = blockUI.instances.get('logs-blockui');
                    this.logsBlockui.start();
                    this.closeDialog = function() {
                        $mdDialog.hide();
                    }
                },
                controllerAs: '$ctrl',
                templateUrl: 'logs.dialog.html',
                parent: angular.element(document.body),
                targetEvent: $event,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function(scope, element, options, controller) {
                    self.updateService.getLogs(moduleName)
                        .then(function(resp) {
                            controller.logs = resp.data;
                        })
                        .finally(function() {
                            controller.logsBlockui.stop();
                        });
                },
            })
            .then(function() {}, function() {});
        };

        self.showCleepUpdateDialog = function($event) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: '$ctrl',
                templateUrl: 'cleep-update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: $event,
                clickOutsideToClose: true,
                fullscreen: true,
            })
            .then(function() {}, function() {});
        };

        self.updateCleep = function() {
            self.cleepUpdates.processing = true;
            self.closeDialog();
            updateService.updateCleep();
        };

        self.$onInit = function() {
            // open required tab
            if ($location.search().tab) {
                self.tabIndex = $location.search().tab;
            }

            // load module config
            cleepService.getModuleConfig('update')
                .then(function(config) {
                    return updateService.getCleepUpdates();
                })
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                    // force installing status if cleep update is processing
                    if (self.cleepUpdates.processing) {
                        updateService.cleepUpdateStatus = 1;
                    }
                });

            // refresh modules updates
            cleepService.refreshModulesUpdates();

            // load modules logs
            updateService.getModulesLogs()
                .then(function(resp) {
                    self.setModuleLogs(resp.data);
                });
        };

        self.setModuleLogs = function (moduleLogs) {
            self.moduleLogs.splice(0, self.moduleLogs.length);

            for (const [moduleName, moduleLog] of Object.entries(moduleLogs)) {
                const uninstalledStr = moduleLog.installed ? '' : 'Uninstalled - ';
                const resultStr = moduleLog.failed ? 'failed' : 'succeed';
                self.moduleLogs.push({
                    title: moduleName,
                    subtitle: uninstalledStr + 'Last action ' + resultStr  + ' at ' + $filter('hrDatetime')(moduleLog.timestamp),
                    icon: moduleLog.installed ? 'chevron-right' : 'trash-can',
                    clicks: [
                        {
                            icon: moduleLog.failed ? 'file-document-alert' : 'file-document-outline',
                            tooltip: 'Show last logs',
                            meta: { moduleName },
                            click: self.showLogsDialog,
                            style: moduleLog.failed ? 'md-raised md-accent' : '',
                        },
                    ],
                });
            }
        };

        self.setModuleUpdates = function (moduleUpdates) {
            self.moduleUpdates.splice(0, self.moduleUpdates.length);

            for (const [moduleName, moduleUpdate] of Object.entries(moduleUpdates)) {
                const updatable = moduleUpdate.updatable;
                self.moduleUpdates.push({
                    title: moduleName + ' v'+ moduleUpdate.version,
                    clicks: [
                        {
                            tooltip: updatable ? 'Update available' : 'No update available',
                            icon: 'update',
                            disabled: !updatable,
                            style: updatable ? 'md-accent md-raised' : '',
                            meta: { moduleName },
                            click: self.gotoModulesPage,
                        },
                    ],
                });
            }
        };

        $rootScope.$watch(
            () => cleepService.modulesUpdates,
            (newVal) => {
                if (newVal && Object.keys(newVal).length) {
                    self.setModuleUpdates(newVal);
                }
            },
        );

        $rootScope.$watch(
            () => cleepService.modules['update'].config,
            (newVal) => {
                if (newVal && Object.keys(newVal).length) {
                    Object.assign(self.config, newVal);
                }
            },
        );

        $rootScope.$watch(
            () => updateService.cleepUpdateStatus,
            (newVal) => {
                if (newVal !== undefined && newVal !== null) {
                    switch (newVal) {
                        case 1:
                            self.cleepInstallProgress = 'Installing update, it might takes some time...';
                            break;
                        case 2:
                            self.cleepInstallProgress = 'Installation completed successfully';
                            break;
                        case 3:
                            self.cleepInstallProgress = 'Installation failed (internal error)';
                            break;
                        case 4:
                            self.cleepInstallProgress = 'Download failed';
                            break;
                        case 5:
                            self.cleepInstallProgress = 'Download failed (file may be corrupted)';
                            break;
                        case 6:
                            self.cleepInstallProgress = 'Installation failed (package install failed)';
                            break;
                        default:
                            self.cleepInstallProgress = 'Updating Cleep...';
                    }

                    if (newVal >= 2) {
                        // cleep install terminated, refresh config to get last results
                        cleepService.reloadModuleConfig('update')
                    }
                }
            },
        );
    }];

    return {
        templateUrl: 'update.config.html',
        replace: true,
        scope: true,
        controller: updateController,
        controllerAs: '$ctrl',
    };
}]);

