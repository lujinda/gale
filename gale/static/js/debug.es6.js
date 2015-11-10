var app = angular.module('tor_debug', []);
app.config(function($interpolateProvider){
    $interpolateProvider.startSymbol('//');
    $interpolateProvider.endSymbol('//');
});

function show_debug_wrap(button){
    var $wrap = $(button).parent();
    var $request_params = $wrap.find('.request_param');
    var api_request_params = [];
    $request_params.each(function(index, param){
        api_request_params.push(param.innerHTML);
    });
    var api_url = $wrap.find('.api_url').html();
    var api_method = $wrap.find('.api_method').html();
    var api_doc = $wrap.find('.restapi').html();
    var elem = document.querySelector("[ng-controller=debug_controller]");
    var $scope = angular.element(elem).scope();
    $scope.reset(api_doc, api_url, api_method, api_request_params);
    $('#debug_wrap').modal();
}

function urlencode(data){
    var query_params = [];
    if (!data){
        return '';
    }
    for (var key in data){
        var value = data[key];
        if (value === undefined){
            continue;
        }

        if(value instanceof Array){
            for (var _i in value){
                query_params.push(key + '=' + value[_i]);
            }
        }else{
            query_params.push(key + '=' + value);
        }
    }

    return query_params.join('&');
}

function debug_controller($scope, $http){
    function encode_data(content_type, data){
        switch (content_type.toLowerCase()){
            case 'json':
                return JSON.stringify(data);
            case 'urlencoded':
                return urlencode(data);
        }
    }
    function request(options, callback){
        var method = (options.method || 'GET').toUpperCase();
        var data = options.data;
        delete options.data;
        var headers = options.headers || {'User-Agent': 'tordoc online debug'};
        if (typeof(data) == 'object' && method != 'GET'){
            data = encode_data($scope.request_content_type, data);
            headers['Content-Type'] = {'json': 'application/json', 
                'urlencoded': 'application/x-www-form-urlencoded'}[$scope.request_content_type];
            headers['Content-Length'] = data.length;
            options.data = data;
        }
        if (method == 'GET'){
            options.url += '?' + urlencode(data);
        }
        $http(options).success(callback).error(callback);
    }
    function init(){
        $scope.request_content_type = 'json';
    }
    $scope.reset= function(api_doc, api_url, api_method, api_request_params){
        $scope.request_params = api_request_params;
        $scope.api_doc = api_doc;

        $scope.request_form = {'url': api_url, 'method': api_method,
                    'data': []};
        $scope.all_request_params = {};
        $scope.request_params.forEach(request_param_name => $scope.all_request_params[request_param_name] = [{}]);
        $scope.response_string = '';
        $scope.$apply();
    };
    function parse_headers_string(headers_string){
        if (!headers_string){
            return {};
        }
        var _headers = {};
        headers_string.split('\n').forEach(function(header_string){
            var [_k, _v] = header_string.split(':', 2);
            _headers[_k] = [_v];
        });
        return _headers;
    };

    function parse_all_request_params(all_request_params){
        var _request_params = {};
        for (var _param_name in all_request_params){
            var _param_values_list = all_request_params[_param_name];
            if (_param_values_list.length <= 1){
                _request_params[_param_name] = _param_values_list[0][_param_name];
                continue;
            }else{
                _request_params[_param_name] = _param_values_list.map(_param_values => _param_values[_param_name]);
            }
        }
        return _request_params;
    };
    $scope.debug_api = function(){
        var headers = parse_headers_string($scope.custom_headers);
        $scope.request_form['headers'] = headers;
        $scope.request_form['data'] = parse_all_request_params($scope.all_request_params);
        request($scope.request_form, function(response, status_code, header){
            var _response = ["status: " + status_code];
            _response.push('------------');
            _response.push('headers:');
            var headers = header();
            for (var header_key in headers){
                var header_value = headers[header_key];
                _response.push(header_key + ': ' + header_value);
            }
            _response.push('------------');
            _response.push('body');
            _response.push(JSON.stringify(response));
            $scope.response_string = _response.join('\n');
        });
    };
    $scope.add_param_value = function(request_param_name){
        $scope.all_request_params[request_param_name].push({request_param_name: ''});
    };
    init();
}

app.controller('debug_controller', debug_controller);

