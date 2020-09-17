/**
 * Update service
 * Handle update application requests
 */
var updateService = function($q, $rootScope, rpcService) {
    var self = this;

    self.getModulesUpdates = function() {
        return rpcService.sendCommand('get_modules_updates', 'update');
    };

    self.getCleepUpdates = function() {
        return rpcService.sendCommand('get_cleep_updates', 'update');
    };

    self.checkCleepUpdates = function() {
        return rpcService.sendCommand('check_cleep_updates', 'update');
    };

    self.checkModulesUpdates = function() {
        return rpcService.sendCommand('check_modules_updates', 'update');
    };

    self.updateCleep = function() {
        return rpcService.sendCommand('update_cleep', 'update');
    };

    self.updateModules = function() {
        return rpcService.sendCommand('update_modules', 'update');
    };

    self.setAutomaticUpdate = function(cleepUpdateEnabled, modulesUpdateEnabled) {
        return rpcService.sendCommand('set_automatic_update', 'update', {
            'cleep_update_enabled': cleepUpdateEnabled,
            'modules_update_enabled': modulesUpdateEnabled,
        });
    };

    self.installModule = function(moduleName) {
        return rpcService.sendCommand('install_module', 'update', {
            'module_name': moduleName,
        });
    };

    self.uninstallModule = function(moduleName, force) {
        return rpcService.sendCommand('uninstall_module', 'update', {
            'module_name': moduleName,
            'force': force,
        });
    };

    self.updateModule = function(moduleName) {
        return rpcService.sendCommand('update_module', 'update', {
            'module_name': moduleName,
        });
    };


    /**
     * Catch events
     */
    $rootScope.$on('update.module.install', function(event, uuid, params) {
    });

    $rootScope.$on('update.module.uninstall', function(event, uuid, params) {
    });

    $rootScope.$on('update.module.update', function(event, uuid, params) {
    });

    $rootScope.$on('update.cleep.update', function(event, uuid, params) {
    });
}
    
var Cleep = angular.module('Cleep');
Cleep.service('updateService', ['$q', '$rootScope', 'rpcService', updateService]);
    
