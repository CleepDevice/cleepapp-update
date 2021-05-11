/**
 * System config component
 * Handle system configuration
 **/
angular
.module('Cleep')
.directive('updateConfigComponent', ['$rootScope', 'cleepService', 'updateService', '$location', 'toastService', '$mdDialog', 'marked', 'blockUI', '$window',
function($rootScope, cleepService, updateService, $location, toast, $mdDialog, marked, blockUI, $window) {
    var updateController = ['$scope', function($scope) {   
        var self = this;
        self.updateService = updateService;
        self.cleepService = cleepService;
        self.tabIndex = 'modules';
        self.config = {};
        self.cleepUpdateEnabled = false;
        self.modulesUpdateEnabled = false;
        self.cleepUpdates = null;
        self.modulesLogs = null;

        /**
         * Set automatic update
         */
        self.setAutomaticUpdate = function(row) {   
            // toggle value if row clicked
            if( row==='cleep' ) {
                self.cleepUpdateEnabled = !self.cleepUpdateEnabled;
            } else if( row==='modules' ) {
                self.modulesUpdateEnabled = !self.modulesUpdateEnabled;
            }

            // perform update
            updateService.setAutomaticUpdate(self.cleepUpdateEnabled, self.modulesUpdateEnabled)
                .then(function(resp) {
                    if( resp.data===true ) {
                        toast.success('New value saved');
                    } else {
                        toast.error('Unable to save new value');
                    }
                });
        }

        /** 
         * Check for cleep updates
         */
        self.checkCleepUpdates = function() {
            toast.loading('Checking Cleep updates...');
            var message = 'No update available';
            updateService.checkCleepUpdates()
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                    if( resp.data.updatable ) {   
                        message = 'Update available';
                    }

                    return self.cleepService.reloadModuleConfig('update');
                })
                .finally(function() {
                    toast.info(message);
                });
        };

        /**
         * Check for modules updates
         */
        self.checkModulesUpdates = function() {
            self.updateService.checkModulesUpdates()
                .then(function(resp) {
                    if( resp.error ) {
                        return;
                    }
                    
                    cleepService.refreshModulesUpdates();
                    if( resp.data.modulesupdates ) {
                        toast.success('There are applications updates available');
                    } else {
                        toast.info('No applications updates available');
                    }

                    return self.cleepService.reloadModuleConfig('update');
                });
        };

        /**
         * Go to modules pages scrolling on specified module
         */
        self.gotoModulesPage = function(moduleName) {
            if (!moduleName) return;
            $window.location.href = '#!/modules?app=' + moduleName;
        };

        /**
         * Close opened dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show logs dialog (the same for Cleep and modules)
         */
        self.showLogsDialog = function(moduleName, ev) {
            $mdDialog.show({
                controller: function($mdDialog) {
                    this.logs = '';
                    this.logsBlockui = blockUI.instances.get('logs-blockui');
                    this.logsBlockui.start();
                    this.closeDialog = function() {
                        $mdDialog.hide();
                    }
                },
                controllerAs: 'logsCtl',
                templateUrl: 'logs.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function(scope, element, options, controller) {
                    self.updateService.getLogs(moduleName)
                        .then(function(resp) {
                            controller.logs = resp.data;
                        })
                        .finally(function() {
                            controller.logsBlockui.stop();;
                        });
                },
            })
            .then(function() {}, function() {});
        };

        /**
         * Show Cleep update dialog
         */
        self.showCleepUpdateDialog = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateCtl',
                templateUrl: 'cleep-update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true,
            })
            .then(function() {}, function() {});
        };

        /**
         * Update cleep
         */
        self.updateCleep = function() {
            self.cleepUpdates.processing = true;
            self.closeDialog();
            updateService.updateCleep();
        };

        /**
         * Component init
         */
        self.$onInit = function() {
            // open required tab
            if( $location.search().tab ) {
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
                    self.modulesLogs = resp.data;
                });
        };

        /**
         * Watch configuration changes
         */
        $rootScope.$watch(
            function() {
                return cleepService.modules['update'].config;
            },
            function(newVal, oldVal) {
                if( newVal && Object.keys(newVal).length ) {
                    Object.assign(self.config, newVal);
                }
            }
        );

        /**
         * Watch for cleep update events
         */
        $rootScope.$watch(
            function() {
                return updateService.cleepUpdateStatus;
            },
            function(newVal, oldVal) {
                if( newVal && newVal>=2 ) {
                    // cleep install terminated, refresh config to get last results
                    cleepService.reloadModuleConfig('update')
                }
            }
        );
    }];

    return {
        templateUrl: 'update.config.html',
        replace: true,
        scope: true,
        controller: updateController,
        controllerAs: 'updateCtl',
    };
}]);

