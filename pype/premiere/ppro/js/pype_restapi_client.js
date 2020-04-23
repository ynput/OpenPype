/* eslint-env node, es2017, esversion:6 */

// connecting pype module pype rest api server (pras)


class PypeRestApiClient {

  constructor(env) {
    this.env = env;
  }

  /**
   * Return url for pype rest api server service
   * @return {url string}
   */
  _getApiServerUrl() {
    var url = this.env.PYPE_REST_API_URL;
    return url
  }

  /**
   * Return JSON from server. This will wait for result.
   * @todo handle status codes and non-json data
   * @param {String} url server url
   * @param {object} options request options
   */
  async getResponseFromRestApiServer(url, options = {}) {
    const fetch = require('node-fetch');
    let defaults = {
      method: "GET",
      headers: {
        "Content-Type": "application/json"
      }
    }
    let settings = {...defaults, ...options}
    const res = await fetch(url, settings);
    return await res.json();
  }


  /**
   * Return presets for project from server
   * @param {String} projectName
   */
  async get_presets(projectName) {
    let server = this._getApiServerUrl();
    let url = `${server}/adobe/presets/${projectName}`;
    console.log("connecting ...");
    let response = await this.getResponseFromRestApiServer(url)
    console.log("got presets:");
    console.log(response.data);
    return response.data;
  }

  async publish(data) {
    let server = this._getApiServerUrl();
    let url = `${server}/adobe/publish`;

    let headers = {
      "Content-Type": "application/json"
    }
    console.log("connecting ...");
    let response = await this.getResponseFromRestApiServer(
      url, {method: 'POST', headers: headers, body: data});
    console.log("got response:");
    console.log(response.data);
    return response.data;
  }
}
