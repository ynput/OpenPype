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
  getRequestFromRestApiServer: function (url, callback) {
    _pype.displayResult('inside of getRequestFromRestApiServer: ' + url)
    fetch(url).then(
      res => res.json()).then(
        json => {callback(json)});
  },
  load_representations: function (projectName, requestList) {
    // preparation for getting representations from api server
    console.log('Load Represention:projectName: ' + projectName);
    console.log('Load Represention:requestList: ' + requestList);
  },
  get_presets: function (projectName) {
    var data = null;
    var template = '{serverUrl}/adobe/presets/{projectName}';
    var url = template.format({
      serverUrl: pras.getApiServerUrl(),
      projectName: projectName,
    });
    _pype.displayResult(url);

    // send request to server
    pras.getRequestFromRestApiServer(url, function (result) {
      _pype.displayResult(JSON.stringify(result));
      if (result.hasOwnProperty ('success')) {
          data = result.data;
          _pype.displayResult('_ data came as dict');
          _pype.displayResult(JSON.stringify(data));
        } else {
          _pype.displayResult('data came as nothing');
          _pype.displayError(
            'No data for `{projectName}` project in database'.format(
              {projectName: projectName}));
        }
    });
  },
  register_plugin_path: function (publishPath) {
    // preparation for getting representations from api server
  },
  deregister_plugin_path: function () {
    // preparation for getting representations from api server
  },
  publish: function (jsonSendPath, jsonGetPath, gui) {
    // preparation for publishing with rest api server
    console.log('__ publish:jsonSendPath: ' + jsonSendPath);
    console.log('__ publish:jsonGetPath ' + jsonGetPath);
    console.log('__ publish:gui ' + gui);
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
