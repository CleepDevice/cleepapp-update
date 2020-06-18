/**
 * Update config directive
 * Handle update application configuration
 */
var updateConfigDirective = function($rootScope, updateService, cleepService) {

    var updateConfigController = function() {
        var self = this;

        /**
         * Init controller
         */
        self.init = function() {
            // TODO
        };
    };

    var updateConfigLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'update.config.html',
        replace: true,
        scope: true,
        controller: updateConfigController,
        controllerAs: 'updateCtl',
        link: updateConfigLink
    };
};

var Cleep = angular.module('Cleep');
Cleep.directive('updateConfigDirective', ['$rootScope', 'updateService', 'cleepService', updateConfigDirective]);
    
