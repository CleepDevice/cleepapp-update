/**
 * Update service
 * Handle update application requests
 */
var updateService = function($q, $rootScope, rpcService) {
    var self = this;

    /**
     * Catch x.x.x events
     */
    $rootScope.$on('x.x.x', function(event, uuid, params) {
    });
}
    
var Cleep = angular.module('Cleep');
Cleep.service('updateService', ['$q', '$rootScope', 'rpcService', updateService]);
    
