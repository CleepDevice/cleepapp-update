/*global angular*/

/**
 * Installed applications page (owned by update app).
 */
angular
.module('Cleep')
.directive('applicationsPageDirective', ['$rootScope', 'cleepService', 'updateService', '$window', 'confirmService', '$mdDialog', '$location', '$anchorScroll',
function($rootScope, cleepService, updateService, $window, confirm, $mdDialog, $location, $anchorScroll) {

    var applicationsController = ['$scope', function($scope) {
        var self = this;
        self.cleepService = cleepService;
        self.updateService = updateService;
        self.search = {'$': ''};
        self.displayedModules = [];
        self.moduleUpdate = {};
        self.moduleNotStarted = null;

        self.clearSearch = function() {
            self.search['$'] = '';
        };

        self.gotoInstallPage = function() {
            $window.location.href = '#!/module/update/market';
        };

        self.gotoUpdateModule = function(moduleName) {
            var url = '#!/module/update?tab=logs';
            if (moduleName) {
                url += '&app=' + encodeURIComponent(moduleName);
            }
            $window.location.href = url;
        };

        self.uninstallModule = function(module) {
            confirm.open(
                'App uninstallation',
                'Do you want to uninstall ' + module + ' application?<br/>Configuration files will be kept.',
                'Uninstall',
                'Cancel'
            )
                .then(function() {
                    return updateService.uninstallModule(module);
                }, function() {});
        };

        self.forceUninstallModule = function(module) {
            self.closeDialog();
            return updateService.forceUninstallModule(module);
        };

        self.updateModule = function(module) {
            self.closeDialog();
            updateService.updateModule(module);
        };

        self.$onInit = function() {
            if ($location.search().app) {
                $location.hash('mod-' + $location.search().app);
                $anchorScroll();
            }

            updateService.getInstallableModules();
            updateService.refreshModulesUpdates();

            $rootScope.$broadcast('enableFab', [{
                callback: self.gotoInstallPage,
                icon: 'plus',
                aria: 'Install app',
                tooltip: 'Install app'
            }]);
        };

        self.fillModules = function() {
            var modules = [];
            for (var moduleName in cleepService.modules) {
                if (!Object.prototype.hasOwnProperty.call(cleepService.modules, moduleName)) {
                    continue;
                }
                var module = cleepService.modules[moduleName];
                if (module.library) {
                    continue;
                }
                modules.push(module);
            }
            self.displayedModules = modules;
        };

        $scope.$watchCollection(
            function() { return cleepService.modules; },
            function(newValue) {
                if (newValue && Object.keys(newValue).length) {
                    self.fillModules();
                }
            }
        );

        self.closeDialog = function() {
            $mdDialog.hide();
        };

        self.showModuleUpdateDialog = function(module, ev) {
            self.moduleUpdate = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateCtl',
                templateUrl: 'applications-update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {}, function() {});
        };

        self.showNotStartedDialog = function(module, ev) {
            self.moduleNotStarted = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'notstartedCtl',
                templateUrl: 'applications-not-started.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {}, function() {});
        };
    }];

    return {
        templateUrl: 'applications.page.html',
        replace: true,
        controller: applicationsController,
        controllerAs: 'applicationsCtl',
    };
}]);
