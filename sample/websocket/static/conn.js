var app = angular.module('demo', []);
app.config(function($interpolateProvider){
    $interpolateProvider.startSymbol('//');
    $interpolateProvider.endSymbol('//');
});

function demo_controller($scope, $http){
    var ws_conn = null;
    $scope.is_connected = false;
    $scope.message_list = [];
    function start_ws_conn(){
        ws_conn = new WebSocket('ws://' + location.host + '/conn');
        ws_conn.onopen = function(){
            console.log('连接已建立');
            $scope.is_connected = true;
            $scope.$apply();
            ws_conn.send($scope.nickname);
        }
        ws_conn.onclose = function(){
            ws_conn = null;
            $scope.is_connected = false;
        }
        ws_conn.onmessage = function(frame){
            console.log(frame.data);
            var data = {'data': frame.data}
            $scope.message_list.push(frame);
            $scope.$apply();
            var _obj = document.getElementById('message_box');
            _obj.scrollTop = _obj.scrollHeight;
        }
    }
    $scope.login = function(){
        start_ws_conn();
    }
    $scope.send_message = function(){
        var message = $scope.message;
        if (!message){
            return;
        }
        ws_conn.send(message);
        $scope.message = '';
    }
}

app.controller('demo_controller', demo_controller);

