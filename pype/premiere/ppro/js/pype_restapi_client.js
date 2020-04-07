/* global _pype */
// connecting pype module pype rest api server (pras)

var pras = {
  /**
   * Return url for pype rest api server service
   * @return {url string}
   */
  getApiServerUrl: function () {
    var url = _pype.ENV.PYPE_REST_API_URL;
    return url
  },
  load_representations: function (projectName, requestList) {
    // preparation for getting representations from api server
  },
  register_plugin_path: function (publishPath) {
    // preparation for getting representations from api server
  },
  deregister_plugin_path: function () {
    // preparation for getting representations from api server
  },
  publish: function (jsonSendPath, jsonGetPath, gui) {
    // preparation for publishing with rest api server
  },
  context: function (project, asset, task, app) {
    // getting context of project
  }
};
