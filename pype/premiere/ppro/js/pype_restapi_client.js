/* global _pype */
// connecting pype module pype rest api server (pras)
const fetch = require('node-fetch');

var pras = {
  /**
   * Return url for pype rest api server service
   * @return {url string}
   */
  getApiServerUrl: function () {
    var url = _pype.ENV.PYPE_REST_API_URL;
    return url
  },
  getRequestFromRestApiServer: function (url, options, callback) {
    _pype.displayResult('url: ' + url);
    _pype.displayResult('options: ' + JSON.stringify(options));

    // define options in case there is null comming
    if (options === null) {
      options = {
        method: 'get',
        headers: {
          'Content-Type': 'application/json'
        }
      }
    }
    _pype.displayResult('options: ' + JSON.stringify(options));

    // send post request to rest api server
    fetch(url, options).then(res => {
      try {
        return res.json();
      } catch (e) {
        return res.text();
      }
    }).then(json => {
      if (isPypeData(json)) {
        _pype.displayResult('json: ' + JSON.stringify(json.data));

        // send it to callback function
        callback(json.data);
      } else {
        _pype.displayError('Data comming from `{url}` are not correct'.format({url: url}));
        callback(null)
      }
    }).catch(err => _pype.displayError('Data comming from `{url}` are not correct.\n\nError: {error}'.format({url: url, error: err})));
  },
  load_representations: function (projectName, requestList) {
    // preparation for getting representations from api server
    console.log('Load Represention:projectName: ' + projectName);
    console.log('Load Represention:requestList: ' + requestList);
  },
  get_presets: function (projectName, callback) {
    var template = '{serverUrl}/adobe/presets/{projectName}';
    var url = template.format({serverUrl: pras.getApiServerUrl(), projectName: projectName});
    _pype.displayResult(url);

    // send request to server
    pras.getRequestFromRestApiServer(url, options = null, function (result) {
      if (result === null) {
        _pype.displayError('No data for `{projectName}` project in database'.format({projectName: projectName}));
        return null
      } else {
        // send the data into jsx and write to module's global variable
        _pype.csi.evalScript('$.pype.setProjectPreset(' + JSON.stringify(result) + ');', function (resultBack) {
          _pype.displayResult('$.pype.setProjectPreset(): ' + resultBack);
          callback(resultBack);
          // test the returning presets data from jsx if they are there
          // _pype.csi.evalScript(
          //   '$.pype.getProjectPreset();',
          //   function (resultedPresets) {
          //     _pype.displayResult(
          //       '$.pype.getProjectPreset(): ' + resultedPresets);
          // });
        });
      }
    });
  },
  publish: function (data) {
    var template = '{serverUrl}/adobe/publish';
    var url = template.format({serverUrl: pras.getApiServerUrl()});
    var _options = {
      method: 'POST',
      body: JSON.stringify(data),
      headers: {
        'Content-Type': 'application/json'
      }
    };
    _pype.displayResult('__ publish:url ' + url);
    _pype.displayResult('__ publish:_options ' + JSON.stringify(_options));

    // publish data with rest api server
    pras.getRequestFromRestApiServer(url, _options, function (result) {
      if (result === null) {
        _pype.displayError('No data for `{projectName}` project in database'.format({projectName: projectName}));
        return null
      } else {
        _pype.displayResult('pras.publish.getRequestFromRestApiServer: ' + JSON.stringify(result));
        return result
      }
      // preparation for publishing with rest api server

    });
  },
  context: function (project, asset, task, app) {
    // getting context of project
  }
};

String.prototype.format = function (arguments) {
  var this_string = '';
  for (var char_pos = 0; char_pos < this.length; char_pos++) {
    this_string = this_string + this[char_pos];
  }

  for (var key in arguments) {
    var string_key = '{' + key + '}'
    this_string = this_string.replace(new RegExp(string_key, 'g'), arguments[key]);
  }
  return this_string;
};

function isPypeData(v) {
  try {
    return Object.prototype.hasOwnProperty.call(v, 'success');
  } catch (e) {
    /* console.error("not a dict",e); */
    return false;
  }
}
