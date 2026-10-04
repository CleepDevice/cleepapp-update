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
        self.osDryRunPreview = null;
        self.osLastAttemptTitle = '';
        self.osLastAttemptSubtitle = '';
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

        self._refreshOsLastAttemptLabels = function() {
            var attempt = self.config.oslastattempt;
            if (!attempt || !attempt.started_at || attempt.dry_run) {
                self.osLastAttemptTitle = 'No OS apply attempt recorded yet';
                self.osLastAttemptSubtitle = 'Apply will be saved here after it finishes';
                return;
            }
            var when = attempt.finished_at || attempt.started_at;
            var whenLabel = $filter('hrDatetime')(when);
            var target = attempt.to_version || '?';
            if (attempt.state === 'running') {
                self.osLastAttemptTitle = 'Apply in progress (since ' + whenLabel + ')';
                self.osLastAttemptSubtitle = 'Target ' + target;
                return;
            }
            if (attempt.state === 'success') {
                self.osLastAttemptTitle = 'Apply succeeded at ' + whenLabel;
                self.osLastAttemptSubtitle = (attempt.from_version || '?') + ' → ' + target;
                return;
            }
            self.osLastAttemptTitle = 'Apply failed at ' + whenLabel;
            var detail = attempt.error || ('phase ' + (attempt.phase || '?'));
            self.osLastAttemptSubtitle = detail;
        };

        self.osDryRunLogSubtitle = function() {
            var attempt = (self.config && self.config.oslastdryrun) || null;
            if (attempt && attempt.finished_at) {
                return 'Saved at ' + $filter('hrDatetime')(attempt.finished_at);
            }
            if (attempt && attempt.started_at) {
                return 'Started at ' + $filter('hrDatetime')(attempt.started_at);
            }
            return 'Separate file: /tmp/cleep/os-upgrade-dry-run.log';
        };

        self.requestOsReboot = function() {
            toast.loading('Showing reboot button...');
            updateService.showOsRebootButton()
                .then(function(resp) {
                    if (resp.error) {
                        return;
                    }
                    toast.info('Use the reboot button in the top bar');
                });
        };

        self.showOsUpgradeLogDialog = function($event, dryRun) {
            var isDryRun = !!dryRun;
            $mdDialog.show({
                controller: function($mdDialog) {
                    var dlg = this;
                    dlg.logs = '';
                    dlg.logPath = '';
                    dlg.fromExcerpt = false;
                    dlg.logsBlockui = blockUI.instances.get('logs-blockui');
                    dlg.closeDialog = function() {
                        $mdDialog.hide();
                    };
                },
                controllerAs: '$ctrl',
                templateUrl: 'logs.dialog.html',
                parent: angular.element(document.body),
                targetEvent: $event,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function(scope, element, options, controller) {
                    controller.logsBlockui.start();
                    updateService.getOsUpgradeLogs(isDryRun)
                        .then(function(resp) {
                            if (resp.error) {
                                controller.logs = resp.message || 'Unable to load OS upgrade log';
                                return;
                            }
                            var data = resp.data || {};
                            controller.logs = data.text || '';
                            controller.logPath = data.path || '';
                            controller.fromExcerpt = !!data.from_excerpt;
                            if (data.from_excerpt) {
                                controller.logs = '(Saved excerpt — log file no longer on device)\n\n'
                                    + controller.logs;
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
                        toast.error(resp.message || 'OS update check failed');
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
                })
                .catch(function() {
                    toast.error('OS update check failed');
                });
        };

        self.updateOs = function() {
            toast.loading('Updating OS...');
            self.osUpdates.processing = true;
            self.osUpdates.failed = false;
            self.osUpdates.dry_run = false;
            updateService.osUpdateStatus = 1;
            updateService.osUpdateProgress = 0;
            updateService.osUpdateDryRun = false;
            self.osInstallProgress = 'Updating OS...';
            updateService.updateOs(false)
                .then(function(resp) {
                    if (resp.error) {
                        self.osUpdates.processing = false;
                        updateService.osUpdateStatus = 0;
                        toast.error(resp.message || 'Unable to start OS update');
                    }
                })
                .catch(function() {
                    self.osUpdates.processing = false;
                    updateService.osUpdateStatus = 0;
                    updateService.osUpdateProgress = 0;
                    toast.error('Unable to start OS update');
                });
        };

        self.dryRunOs = function() {
            toast.loading('Running OS dry-run...');
            self.osUpdates.processing = true;
            self.osUpdates.failed = false;
            self.osUpdates.dry_run = true;
            updateService.osUpdateStatus = 1;
            updateService.osUpdateProgress = 0;
            updateService.osUpdateDryRun = true;
            self.osInstallProgress = 'Running OS dry-run...';
            updateService.updateOs(true)
                .then(function(resp) {
                    if (resp.error) {
                        self.osUpdates.processing = false;
                        self.osUpdates.dry_run = false;
                        updateService.osUpdateStatus = 0;
                        updateService.osUpdateDryRun = false;
                        toast.error(resp.message || 'Unable to start OS dry-run');
                    }
                })
                .catch(function() {
                    self.osUpdates.processing = false;
                    self.osUpdates.dry_run = false;
                    updateService.osUpdateStatus = 0;
                    updateService.osUpdateProgress = 0;
                    updateService.osUpdateDryRun = false;
                    toast.error('Unable to start OS dry-run');
                });
        };

        self._loadOsDryRunPreview = function() {
            return updateService.getOsDryRunPreview()
                .then(function(resp) {
                    if (resp.error) {
                        return null;
                    }
                    self.osDryRunPreview = (resp.data) || null;
                    return self.osDryRunPreview;
                });
        };

        self.osDryRunPreviewSubtitle = function() {
            var preview = self.osDryRunPreview || {};
            if (preview.summary) {
                return preview.summary;
            }
            if (preview.target_version) {
                return 'target ' + preview.target_version;
            }
            return 'Review findings before Apply';
        };

        self.showOsDryRunPreviewDialog = function($event) {
            $mdDialog.show({
                controller: function($mdDialog) {
                    var dlg = this;
                    dlg.previewText = '';
                    dlg.verdict = null;
                    dlg.findings = [];
                    dlg.logsBlockui = blockUI.instances.get('os-dry-run-preview-blockui');
                    dlg.closeDialog = function() {
                        $mdDialog.hide();
                    };
                },
                controllerAs: '$ctrl',
                templateUrl: 'os-dry-run-preview.dialog.html',
                parent: angular.element(document.body),
                targetEvent: $event,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function(scope, element, options, controller) {
                    controller.logsBlockui.start();
                    updateService.getOsDryRunPreview()
                        .then(function(resp) {
                            var preview = resp.data || {};
                            controller.previewText = preview.text || preview.summary || '';
                            controller.verdict = preview.verdict || null;
                            controller.findings = preview.findings || [];
                            if (preview.available) {
                                self.osDryRunPreview = preview;
                            }
                        })
                        .finally(function() {
                            controller.logsBlockui.stop();
                        });
                },
            })
            .then(function() {}, function() {});
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

                    return cleepService.refreshModulesUpdates()
                        .then(function() {
                            if (resp.data.modulesupdates) {
                                toast.success('There are applications updates available');
                            } else {
                                toast.info('No applications updates available');
                            }
                            return self.cleepService.reloadModuleConfig('update');
                        });
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

            // load module config (also carries osinfo/osupdates after reconnect)
            cleepService.getModuleConfig('update')
                .then(function(config) {
                    if (config) {
                        if (config.osinfo) {
                            self.osInfo = config.osinfo;
                        }
                        if (config.osupdates) {
                            self.osUpdates = config.osupdates;
                        }
                        self._refreshOsCheckSubtitle();
                        self._refreshOsLastAttemptLabels();
                    }
                    return updateService.getCleepUpdates();
                })
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                    // force installing status if cleep update is processing
                    if (self.cleepUpdates.processing) {
                        updateService.cleepUpdateStatus = 1;
                    }
                    // Fallback RPCs if config did not include OS fields (older backend)
                    if (self.osInfo && self.osInfo.version) {
                        self._loadOsConfReport();
                        self._loadOsDryRunPreview();
                        return null;
                    }
                    return updateService.getOsInfo();
                })
                .then(function(resp) {
                    if (!resp) {
                        return null;
                    }
                    if (!resp.error) {
                        self.osInfo = resp.data || {};
                    }
                    return updateService.getOsUpdates();
                })
                .then(function(resp) {
                    if (!resp) {
                        return;
                    }
                    if (!resp.error) {
                        self.osUpdates = resp.data || self.osUpdates;
                    }
                    if (self.osUpdates && self.osUpdates.processing) {
                        var dryRun = !!self.osUpdates.dry_run;
                        updateService.osUpdateStatus = self.osUpdates.status || 1;
                        updateService.osUpdateProgress = self.osUpdates.progress || 0;
                        updateService.osUpdatePhase = self.osUpdates.phase || null;
                        updateService.osUpdateDryRun = dryRun;
                        var label = self._osPhaseLabel(
                            updateService.osUpdateProgress,
                            updateService.osUpdatePhase
                        );
                        self.osInstallProgress = dryRun ? ('Dry-run: ' + label) : label;
                    }
                    self._refreshOsCheckSubtitle();
                    self._loadOsConfReport();
                    self._loadOsDryRunPreview();
                    self._refreshOsLastAttemptLabels();
                });

            // refresh modules updates
            cleepService.refreshModulesUpdates();

            // load modules logs (deep-link ?tab=logs&app=<name> opens that app's log)
            updateService.getModulesLogs()
                .then(function(resp) {
                    self.setModuleLogs(resp.data);
                    var app = String($location.search().app || '').trim();
                    if (self.tabIndex === 'logs' && app) {
                        self.showLogsDialog(app);
                    }
                });
        };

        self.setModuleLogs = function (moduleLogs) {
            // New array reference so config-list (`cl-items` one-way) re-renders.
            const next = [];
            for (const [moduleName, moduleLog] of Object.entries(moduleLogs || {})) {
                const uninstalledStr = moduleLog.installed ? '' : 'Uninstalled - ';
                const resultStr = moduleLog.failed ? 'failed' : 'succeed';
                next.push({
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
            self.moduleLogs = next;
        };

        self.setModuleUpdates = function (moduleUpdates) {
            // New array reference so config-list (`cl-items` one-way) re-renders.
            const next = [];
            for (const [moduleName, moduleUpdate] of Object.entries(moduleUpdates || {})) {
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

                next.push({
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
            self.moduleUpdates = next;
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
                    // OS identity / updates come from get_module_config on reconnect
                    if (newVal.osinfo) {
                        self.osInfo = newVal.osinfo;
                    }
                    if (newVal.osupdates) {
                        self.osUpdates = newVal.osupdates;
                        if (self.osUpdates.processing) {
                            var dryRun = !!self.osUpdates.dry_run;
                            updateService.osUpdateStatus = self.osUpdates.status || 1;
                            updateService.osUpdateProgress = self.osUpdates.progress || 0;
                            updateService.osUpdatePhase = self.osUpdates.phase || null;
                            updateService.osUpdateDryRun = dryRun;
                            var label = self._osPhaseLabel(
                                updateService.osUpdateProgress,
                                updateService.osUpdatePhase
                            );
                            self.osInstallProgress = dryRun ? ('Dry-run: ' + label) : label;
                        }
                    }
                    self._refreshOsCheckSubtitle();
                    if (newVal.osconfreport) {
                        self.osConfReport = newVal.osconfreport;
                        self._refreshOsConfReportLabels();
                    }
                    if (newVal.oslastattempt || newVal.oslastdryrun !== undefined) {
                        self._refreshOsLastAttemptLabels();
                    }
                    if (
                        newVal.oslastattempt
                        && newVal.oslastattempt.state === 'failed'
                        && !newVal.oslastattempt.dry_run
                        && self.osUpdates
                    ) {
                        self.osUpdates.failed = true;
                        self.osUpdates.error = newVal.oslastattempt.error;
                        self.osUpdates.log_path = newVal.oslastattempt.log_path;
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
                var dryRun = !!updateService.osUpdateDryRun;
                switch (newVal) {
                    case 1:
                        self.osInstallProgress = self._osPhaseLabel(
                            updateService.osUpdateProgress,
                            updateService.osUpdatePhase
                        );
                        if (dryRun && self.osInstallProgress.indexOf('dry-run') < 0) {
                            self.osInstallProgress = 'Dry-run: ' + self.osInstallProgress;
                        }
                        self.osUpdates.processing = true;
                        self.osUpdates.dry_run = dryRun;
                        break;
                    case 2:
                        self.osUpdates.processing = false;
                        self.osUpdates.failed = false;
                        self.osUpdates.dry_run = false;
                        if (dryRun) {
                            self.osInstallProgress = 'OS dry-run completed';
                            self.osUpdates.pending = false;
                            self._loadOsDryRunPreview()
                                .then(function(preview) {
                                    var verdict = (preview && preview.verdict) || null;
                                    if (verdict === 'ko') {
                                        toast.error('Dry-run verdict: KO — fix findings before Apply');
                                    } else if (verdict === 'ok') {
                                        toast.success('Dry-run verdict: OK — review preview then Apply');
                                    } else {
                                        toast.success('Dry-run completed — review the preview before Apply');
                                    }
                                    if (preview && preview.available) {
                                        self.showOsDryRunPreviewDialog();
                                    }
                                });
                        } else {
                            self.osInstallProgress = 'OS update completed';
                            self.osUpdates.pending = true;
                            self.osUpdates.reboot_needed = true;
                            self.osUpdates.updatable = false;
                            toast.success('OS update completed — use the top-bar reboot button');
                        }
                        cleepService.reloadModuleConfig('update');
                        break;
                    case 3:
                        self.osInstallProgress = dryRun ? 'OS dry-run failed' : 'OS update failed';
                        self.osUpdates.processing = false;
                        self.osUpdates.failed = true;
                        self.osUpdates.dry_run = false;
                        toast.error(
                            dryRun
                                ? 'OS dry-run failed — see device logs'
                                : 'OS update failed — see /tmp/cleep/os-upgrade.log'
                        );
                        // Refresh cached fields (error / log_path) for the failure note
                        updateService.getOsUpdates()
                            .then(function(resp) {
                                if (!resp.error && resp.data) {
                                    self.osUpdates = resp.data;
                                }
                                return cleepService.reloadModuleConfig('update');
                            });
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
                    var label = self._osPhaseLabel(
                        newVal,
                        updateService.osUpdatePhase
                    );
                    if (updateService.osUpdateDryRun) {
                        label = 'Dry-run: ' + label;
                    }
                    self.osInstallProgress = label;
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

