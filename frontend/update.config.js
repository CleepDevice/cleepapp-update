/**
 * System config directive
 * Handle system configuration
 **/
var updateConfigDirective = function($rootScope, cleepService, updateService, $location, toast, $mdDialog, marked) {
    var updateController = ['$scope', function($scope) {   
        var self = this;
        self.updateService = updateService;
        self.tabIndex = 'modules';
        self.config = {};
        self.cleepUpdateEnabled = false;
        self.modulesUpdateEnabled = false;
        self.cleepUpdates = null;
        self.modulesUpdates = null;
        self.cleepLastCheck = null;
        self.cleepLogs = '';

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
                    self.cleepLastCheck = (new Date().getTime() / 1000);
                    if( resp.data.updatable ) {   
                        message = 'Update available';
                    }
                })
                .finally(function() {
                    toast.info(message);
                });
		};

        /**
         * Check for modules updates
         */
        self.checkModulesUpdates = function() {
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
        self.showCleepLogsDialog = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'logsCtl',
                templateUrl: 'logs.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true,
                onShowing: function() {
                    self.updateService.getCleepLogs()
                        .then(function(resp) {
                            self.cleepLogs = resp.data;
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
		 * Controller init
		 */
        self.$onInit = function() {
            // open required tab
			if( $location.search().tab ) {
                self.tabIndex = $location.search().tab;
            }

            // load module config
            cleepService.getModuleConfig('update')
                .then(function(config) {
                    Object.assign(self.config, config);
                    self.cleepUpdateEnabled = config.cleepupdateenabled;
                    self.modulesUpdateEnabled = config.modulesupdateenabled;
                    self.cleepLastCheck = config.cleeplastcheck;

                    return updateService.getCleepUpdates();
                })
                .then(function(resp) {
                    self.cleepUpdates = resp.data;
                });
        };

        $rootScope.$watch(
            function() {
                return updateService.cleepUpdateStatus;
            },
            function(newVal, oldVal) {
                if( newVal && newVal>=2 ) {
                    // cleep install terminated, refresh config to get last results
                    cleepService.reloadModuleConfig('update')
                        .then(function(config) {
                            Object.assign(self.config, config);
                        });
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
};

var Cleep = angular.module('Cleep');
Cleep.directive('updateConfigDirective', ['$rootScope', 'cleepService', 'updateService', '$location', 'toastService', '$mdDialog', 'marked', updateConfigDirective]);

