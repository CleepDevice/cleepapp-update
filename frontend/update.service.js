/**
 * Update service
 * Handle update application requests
 */
angular
.module('Cleep')
.service('updateService', ['$q', '$rootScope', 'rpcService',
function($q, $rootScope, rpcService) {

    var self = this;
    self.cleepUpdateStatus = 0;
    self.cleepUpdateProgress = 0;
    self.osUpdateStatus = 0;
    self.osUpdateProgress = 0;
    self.osUpdatePhase = null;

    self.updateOs = function() {
        return rpcService.sendCommand('update_os', 'update');
    };

    self.getModulesUpdates = function() {
        return rpcService.sendCommand('get_modules_updates', 'update');
    };

    self.getCleepUpdates = function() {
        return rpcService.sendCommand('get_cleep_updates', 'update');
    };

    self.getOsInfo = function() {
        return rpcService.sendCommand('get_os_info', 'update');
    };

    self.getOsUpdates = function() {
        return rpcService.sendCommand('get_os_updates', 'update');
    };

    self.checkOsUpdates = function() {
        return rpcService.sendCommand('check_os_updates', 'update');
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

    self.setOsConfReportOptions = function(enabled, autosend) {
        return rpcService.sendCommand('set_os_conf_report_options', 'update', {
            'enabled': enabled,
            'autosend': autosend,
        });
    };

    self.getOsConfReport = function() {
        return rpcService.sendCommand('get_os_conf_report', 'update');
    };

    self.generateOsConfReport = function() {
        return rpcService.sendCommand('generate_os_conf_report', 'update');
    };

    self.sendOsConfReport = function() {
        return rpcService.sendCommand('send_os_conf_report', 'update');
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

    self.getLogs = function(moduleName) {
        if (!moduleName) {
            moduleName = 'cleep';
        }
        return rpcService.sendCommand('get_logs', 'update', {
            'module_name': moduleName,
        });
    };

    self.getModulesLogs = function() {
        return rpcService.sendCommand('get_modules_logs', 'update');
    };

    $rootScope.$on('update.cleep.update', function(event, uuid, params) {
        self.cleepUpdateStatus = params.status;
        if (params.progress !== undefined && params.progress !== null) {
            self.cleepUpdateProgress = params.progress;
        }
    });

    $rootScope.$on('update.os.update', function(event, uuid, params) {
        self.osUpdateStatus = params.status;
        if (params.progress !== undefined && params.progress !== null) {
            self.osUpdateProgress = params.progress;
        }
        if (params.phase !== undefined) {
            self.osUpdatePhase = params.phase;
        }
    });

}]);

