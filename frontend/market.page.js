/*global angular*/

/**
 * Market / installable applications page (owned by update app).
 */
angular
.module('Cleep')
.directive('marketPageDirective', ['cleepService', 'updateService', '$mdDialog', '$sce',
function(cleepService, updateService, $mdDialog, $sce) {

    var marketController = ['$scope', '$window', function($scope, $window) {
        var self = this;
        self.cleepService = cleepService;
        self.updateService = updateService;
        self.search = {'$': ''};
        self.moduleToInstall = null;
        self.loading = true;
        self.displayedModules = [];
        self.gaugeThreshold = {
            '0': { color: '#000000' },
            '5': { color: '#d32f2f' },
            '6': { color: '#f57c00' },
            '7': { color: '#fbc02d' },
            '8': { color: '#0288d1' },
            '9': { color: '#689f38' },
        };
        self.moduleIncompatible = null;

        self.clearSearch = function() {
            self.search['$'] = '';
        };

        self.install = function(module) {
            self.closeDialog();
            updateService.installModule(module);
        };

        self.fillModules = function() {
            cleepService.getModuleConfig('parameters')
                .then(function(parametersConfig) {
                    const modules = [];
                    for (const module of Object.values(updateService.installableModules)) {
                        const countryAlpha = module.country || '';
                        if ((!module.installed || (module.installed && module.library)) &&
                            (countryAlpha.length === 0 || countryAlpha.toUpperCase() === parametersConfig.country.alpha2)) {
                            modules.push(module);
                        }
                    }
                    self.displayedModules = modules;
                    self.loading = false;
                });
        };

        self.showIncompatibleDialog = function(module, ev) {
            self.moduleIncompatible = module;
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'incompatibleCtl',
                templateUrl: 'market-incompatible.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {}, function() {});
        };

        self.closeDialog = function() {
            $mdDialog.hide();
        };

        self.showInstallDialog = function(module, ev) {
            self.moduleToInstall = module;
            self.sceLongDescription = $sce.trustAsHtml(self.moduleToInstall.longdescription);
            self.sceChangelog = $sce.trustAsHtml(self.moduleToInstall.changelog);
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'installCtl',
                templateUrl: 'market-install.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            }).then(function() {}, function() {});
        };

        self.gotoUpdateLogs = function(moduleName) {
            var url = '#!/module/update?tab=logs';
            if (moduleName) {
                url += '&app=' + encodeURIComponent(moduleName);
            }
            $window.location.href = url;
        };

        self.gotoUpdateCleep = function() {
            self.closeDialog();
            $window.location.href = '#!/module/update?tab=cleep';
        };

        $scope.$watch(
            function() { return updateService.installableModules; },
            function(newValue) {
                if (newValue && Object.keys(newValue).length) {
                    self.fillModules();
                }
            },
            true
        );

        self.$onInit = function() {
            updateService.getInstallableModules(true);
            updateService.refreshModulesUpdates();
        };
    }];

    return {
        templateUrl: 'market.page.html',
        replace: true,
        controller: marketController,
        controllerAs: 'installCtl',
    };
}]);
