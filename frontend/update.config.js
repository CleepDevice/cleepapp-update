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
        self.osInfo = {};
        self.osUpdates = {
            updatable: false,
            cleep_too_old: false,
        };
        self.osCheckSubtitle = 'No check performed yet';
        self.osInstallProgress = 'Updating OS...';
        self.osConfReport = null;
        self.osConfReportTitle = 'No OS conf report yet';
        self.osConfReportSubtitle = 'Generated after a successful OS upgrade when the option is enabled';
        self.moduleLogs = [];
        self.moduleUpdates = [];
        self.cleepInstallProgress = 'Updating Cleep...';

        self._refreshOsConfReportLabels = function() {
            var report = self.osConfReport;
            if (!report || !report.generated_at) {
                self.osConfReportTitle = 'No OS conf report yet';
                self.osConfReportSubtitle = 'Generated after a successful OS upgrade when the option is enabled';
                return;
            }
            var count = report.leftover_count || 0;
            self.osConfReportTitle = count + ' leftover path(s) — '
                + (report.from_version || '?') + ' → ' + (report.to_version || '?');
            self.osConfReportSubtitle = 'Generated '
                + $filter('hrDatetime')(report.generated_at)
                + (report.sent ? ' · sent to Sentry' : ' · not sent');
        };

        self._loadOsConfReport = function() {
            if (!self.config.osconfreportenabled) {
                self.osConfReport = null;
                self._refreshOsConfReportLabels();
                return;
            }
            return updateService.getOsConfReport()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    self.osConfReport = (resp.data && resp.data.report) || null;
                    self._refreshOsConfReportLabels();
                });
        };

        self.setOsConfReportOptions = function(value, meta) {
            var enabled = meta.field === 'enabled' ? value : !!self.config.osconfreportenabled;
            var autosend = meta.field === 'autosend' ? value : !!self.config.osconfreportautosend;
            if (meta.field === 'enabled' && !value) {
                autosend = false;
            }
            updateService.setOsConfReportOptions(enabled, autosend)
                .then(function(resp) {
                    if (resp.error) {
                        toast.error('Error saving option');
                        return self.cleepService.reloadModuleConfig('update');
                    }
                    toast.success('Option saved');
                    return self.cleepService.reloadModuleConfig('update');
                })
                .then(function() {
                    return self._loadOsConfReport();
                });
        };

        self.refreshOsConfReport = function() {
            toast.loading('Scanning leftover conf paths...');
            updateService.generateOsConfReport()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    self.osConfReport = (resp.data && resp.data.report) || null;
                    self._refreshOsConfReportLabels();
                    toast.success('Report refreshed');
                    return self.cleepService.reloadModuleConfig('update');
                });
        };

        self.sendOsConfReport = function() {
            toast.loading('Sending report to Sentry...');
            updateService.sendOsConfReport()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    self.osConfReport = (resp.data && resp.data.report) || self.osConfReport;
                    self._refreshOsConfReportLabels();
                    toast.success('Report sent to Sentry');
                    return self.cleepService.reloadModuleConfig('update');
                });
        };

        self.showOsConfReportDialog = function($event) {
            $mdDialog.show({
                controller: function($mdDialog, updateService, toastService) {
                    var dlg = this;
                    dlg.reportText = '';
                    dlg.sending = false;
                    dlg.logsBlockui = blockUI.instances.get('os-conf-report-blockui');
                    dlg.closeDialog = function() {
                        $mdDialog.hide();
                    };
                    dlg.sendReport = function() {
                        dlg.sending = true;
                        updateService.sendOsConfReport()
                            .then(function(resp) {
                                if (resp.error) {
                                    return;
                                }
                                toastService.success('Report sent to Sentry');
                                if (resp.data && resp.data.report) {
                                    self.osConfReport = resp.data.report;
                                    self._refreshOsConfReportLabels();
                                }
                            })
                            .finally(function() {
                                dlg.sending = false;
                            });
                    };
                },
                controllerAs: '$ctrl',
                templateUrl: 'os-conf-report.dialog.html',
                parent: angular.element(document.body),
                targetEvent: $event,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function(scope, element, options, controller) {
                    controller.logsBlockui.start();
                    updateService.getOsConfReport()
                        .then(function(resp) {
                            var report = resp.data && resp.data.report;
                            controller.reportText = (report && report.text) || '';
                            if (report) {
                                self.osConfReport = report;
                                self._refreshOsConfReportLabels();
                            }
                        })
                        .finally(function() {
                            controller.logsBlockui.stop();
                        });
                },
            })
            .then(function() {}, function() {});
        };

        self._refreshOsCheckSubtitle = function() {
            var lastCheck = self.config.oslastcheck;
            var lastCheckLabel = lastCheck
                ? $filter('hrDatetime')(lastCheck)
                : 'never';
            if (self.osUpdates && self.osUpdates.updatable) {
                self.osCheckSubtitle = 'Update available (last check ' + lastCheckLabel + ')';
            } else if (self.osUpdates && self.osUpdates.cleep_too_old) {
                self.osCheckSubtitle = 'Update blocked: Cleep too old (last check ' + lastCheckLabel + ')';
            } else if (lastCheck) {
                self.osCheckSubtitle = 'No update available (last check ' + lastCheckLabel + ')';
            } else {
                self.osCheckSubtitle = 'No check performed yet';
            }
        };

        self.checkOsUpdates = function() {
            toast.loading('Checking OS updates...');
            updateService.checkOsUpdates()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    self.osUpdates = resp.data || {};
                    if (self.osUpdates.current) {
                        self.osInfo = {
                            version: self.osUpdates.current,
                            suite: self.osUpdates.suite,
                            build: self.osInfo.build,
                        };
                    }
                    var message = self.osUpdates.updatable
                        ? 'OS update available'
                        : (self.osUpdates.cleep_too_old
                            ? 'OS update requires a newer Cleep'
                            : 'No OS update available');
                    toast.info(message);
                    return self.cleepService.reloadModuleConfig('update');
                })
                .then(function() {
                    self._refreshOsCheckSubtitle();
                });
        };

        self.updateOs = function() {
            toast.loading('Starting OS update...');
            self.osUpdates.processing = true;
            self.osUpdates.failed = false;
            updateService.osUpdateStatus = 1;
            updateService.osUpdateProgress = 0;
            self.osInstallProgress = 'Starting OS update...';
            updateService.updateOs()
                .then(function(resp) {
                    if (resp.error) {
                        self.osUpdates.processing = false;
                        updateService.osUpdateStatus = 0;
                    }
                })
                .catch(function() {
                    self.osUpdates.processing = false;
                    updateService.osUpdateStatus = 0;
                    updateService.osUpdateProgress = 0;
                });
        };

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
            updateService.checkCleepUpdates()
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                    var message = resp.data.updatable
                        ? 'Update available'
                        : 'No update available';
                    toast.info(message);
                    return self.cleepService.reloadModuleConfig('update');
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
            self.cleepUpdates.failed = false;
            updateService.cleepUpdateStatus = 1;
            updateService.cleepUpdateProgress = 0;
            self.closeDialog();
            updateService.updateCleep()
                .catch(function() {
                    self.cleepUpdates.processing = false;
                    updateService.cleepUpdateStatus = 0;
                    updateService.cleepUpdateProgress = 0;
                });
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

            updateService.getOsInfo()
                .then(function(resp) {
                    if (!resp.error) {
                        self.osInfo = resp.data || {};
                    }
                    return updateService.getOsUpdates();
                })
                .then(function(resp) {
                    if (resp && !resp.error) {
                        self.osUpdates = resp.data || self.osUpdates;
                    }
                    self._refreshOsCheckSubtitle();
                    return self._loadOsConfReport();
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
                const processing = moduleUpdate.processing;
                const pending = moduleUpdate.pending;
                const failed = moduleUpdate.update && moduleUpdate.update.failed;
                const progress = moduleUpdate.update && moduleUpdate.update.progress;
                let subtitle = '';
                if (processing) {
                    subtitle = 'Updating... ' + (progress || 0) + '%';
                } else if (pending) {
                    subtitle = 'Update applied, restart required';
                } else if (failed) {
                    subtitle = 'Last update failed';
                } else if (updatable) {
                    subtitle = 'Update available: v' + moduleUpdate.update.version;
                }

                self.moduleUpdates.push({
                    title: moduleName + ' v'+ moduleUpdate.version,
                    subtitle: subtitle,
                    clicks: [
                        {
                            tooltip: updatable && !processing && !pending
                                ? 'Update available'
                                : 'No update available',
                            icon: 'update',
                            disabled: !updatable || processing || pending,
                            style: updatable && !processing && !pending
                                ? 'md-accent md-raised'
                                : '',
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
                    self._refreshOsCheckSubtitle();
                    if (newVal.osconfreport) {
                        self.osConfReport = newVal.osconfreport;
                        self._refreshOsConfReportLabels();
                    }
                }
            },
        );

        $rootScope.$watch(
            () => updateService.cleepUpdateStatus,
            (newVal) => {
                if (newVal !== undefined && newVal !== null) {
                    switch (newVal) {
                        case 1:
                            self.cleepInstallProgress = self._cleepPhaseLabel(
                                updateService.cleepUpdateProgress
                            );
                            break;
                        case 2:
                            self.cleepInstallProgress = 'Installation completed successfully';
                            break;
                        case 3:
                            self.cleepInstallProgress = 'Installation failed (internal error)';
                            break;
                        case 4:
                            self.cleepInstallProgress = 'Download failed (checksum)';
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

                    if (newVal >= 2 && self.cleepUpdates) {
                        // cleep install terminated
                        self.cleepUpdates.processing = newVal === 2;
                        self.cleepUpdates.pending = newVal === 2;
                        self.cleepUpdates.failed = newVal > 2;
                        if (newVal === 2) {
                            self.cleepUpdates.updatable = false;
                        }
                        cleepService.reloadModuleConfig('update');
                    }
                }
            },
        );

        $rootScope.$watch(
            () => updateService.cleepUpdateProgress,
            (newVal) => {
                if (updateService.cleepUpdateStatus === 1) {
                    self.cleepInstallProgress = self._cleepPhaseLabel(newVal);
                }
            },
        );

        $rootScope.$watch(
            () => updateService.osUpdateStatus,
            (newVal) => {
                if (newVal === undefined || newVal === null || !self.osUpdates) {
                    return;
                }
                switch (newVal) {
                    case 1:
                        self.osInstallProgress = self._osPhaseLabel(
                            updateService.osUpdateProgress,
                            updateService.osUpdatePhase
                        );
                        self.osUpdates.processing = true;
                        break;
                    case 2:
                        self.osInstallProgress = 'OS update completed';
                        self.osUpdates.processing = false;
                        self.osUpdates.pending = true;
                        self.osUpdates.failed = false;
                        self.osUpdates.updatable = false;
                        break;
                    case 3:
                        self.osInstallProgress = 'OS update failed';
                        self.osUpdates.processing = false;
                        self.osUpdates.failed = true;
                        break;
                    default:
                        self.osInstallProgress = 'Updating OS...';
                }
            },
        );

        $rootScope.$watch(
            () => updateService.osUpdateProgress,
            (newVal) => {
                if (updateService.osUpdateStatus === 1) {
                    self.osInstallProgress = self._osPhaseLabel(
                        newVal,
                        updateService.osUpdatePhase
                    );
                }
            },
        );

        self._osPhaseLabel = function(progress, phase) {
            var label = phase ? ('Phase ' + phase) : 'Updating OS';
            if (progress > 0) {
                return label + ' (' + progress + '%)...';
            }
            return label + '...';
        };

        self._cleepPhaseLabel = function(progress) {
            if (progress >= 66) {
                return 'Installing package (' + progress + '%)...';
            }
            if (progress >= 33) {
                return 'Downloading package (' + progress + '%)...';
            }
            if (progress > 0) {
                return 'Preparing update (' + progress + '%)...';
            }
            return 'Starting Cleep update...';
        };
    }];

    return {
        templateUrl: 'update.config.html',
        replace: true,
        scope: true,
        controller: updateController,
        controllerAs: '$ctrl',
    };
}]);

