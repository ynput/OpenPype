/* global CSInterface, $, PypeRestApiClient, SystemPath */
/* eslint-env node, es2017, esversion:6 */

class Pype {

    /**
     * Initialize important properties and load necessary JSX files.
     */
    constructor() {
        this.csi = new CSInterface();
        this.outputId = $("#output");

        this.rootFolderPath = this.csi.getSystemPath(SystemPath.EXTENSION);
        var extensionRoot = this.rootFolderPath + "/jsx/";
        this.progress("Loading premiere.jsx", true);
        this.csi.evalScript('$.evalFile("' + extensionRoot + '/PPRO/Premiere.jsx");', () => {
            this.progress("Loading pype.jsx", true);
            this.csi.evalScript('$.evalFile("' + extensionRoot + 'pype.jsx");', () => {
                this.progress("Loading batchRenamer.jsx", true);
                this.csi.evalScript('$.evalFile("' + extensionRoot + 'batchRenamer.jsx");', () => {
                    this._initialize();
                });
            });
        });
    }

    _initialize() {
        var self = this;
        // get environment
        this.csi.evalScript('$.pype.getProjectFileData();', (result) => {
            if (result == "EvalScript error.") {
                this.error("Cannot get project data.");
                throw "Cannot get project data";
            }
            process.env.EXTENSION_PATH = this.rootFolderPath;
            this.env = process.env;
            var resultData = JSON.parse(result);
            for (var key in resultData) {
                this.env[key] = resultData[key];
            }
            this.csi.evalScript('$.pype.setEnvs(' + JSON.stringify(self.env) + ')');
            this.pras = new PypeRestApiClient(this.env);
            this.progress(`Getting presets for ${this.env.AVALON_PROJECT}`, true);
            this.presets = this.pras.get_presets(this.env.AVALON_PROJECT)
            .then((presets) => {
                this.progress("transferring presets to jsx")
                this.presets = presets;
                this.csi.evalScript('$.pype.setProjectPreset(' + JSON.stringify(presets) + ');', () => {
                    this.progress("Panel's backend loaded...", true);
                    // bind encoding jobs event listener
                    this.csi.addEventListener("pype.EncoderJobsComplete", this._encodingDone);

                    // Bind Interface buttons
                    this._bindButtons();
                });
            });
        });
    }

    /**
     * Wrapper function over clip renamer
     */
    rename () {
        let $renameId = $('#rename');
        let data = {};
        data.ep = $('input[name=episode]', $renameId).val();
        data.epSuffix = $('input[name=ep_suffix]', $renameId).val();
        data.projectCode = this.env.AVALON_PROJECT_CODE;

        if (!data.ep) {
          this.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode code' + '")');
          return;
        }

        if (!data.epSuffix) {
          this.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode longer suffix' + '")');
          return;
        }

        this.progress(`Doing rename [ ${data.ep} ] | [ ${data.epSuffix} ]`);
        this.csi.evalScript(
          'BatchRenamer.renameTargetedTextLayer(' + JSON.stringify(data) + ' );', (result) => {
            this.progress(`Renaming result: ${result}`, true);
          });
      }

    _bindButtons() {
        var self = this;
        $('#btn-publish').click(function () {
            self.publish();
        });

        $('#btn-rename').click(function () {
            self.rename();
        });

        $('#btn-send-reset').click(function () {
          $('#publish input[name=send-path]').val("");
        });

        $('#btn-get-reset').click(function () {
          $('#publish input[name=get-path]').val("");
        });

        $('#btn-newWorkfileVersion').click(function () {
          self.csi.evalScript('$.pype.versionUpWorkFile();');
          self.progress('New version of the project file saved...', true);
        });

        $('#btn-get-frame').click(function () {
          self.csi.evalScript('$._PPP_.exportCurrentFrameAsPNG();', (result) => {
            self.progress(`Screen grabing image path in: [${result}]`, true);
          });
});
    }

    /**
     * Normalize slashes in path string
     * @param {String} path
     */
    static convertPathString (path) {
        return path.replace(
            new RegExp('\\\\', 'g'), '/').replace(new RegExp('//\\?/', 'g'), '');
     }
    /**
     * Gather all user UI options for publishing
     */
    _gatherPublishUI() {
        let publishId = $('#publish');
        let uiVersionUp = $('input[name=version-up]', publishId);
        let uiAudioOnly = $('input[name=audio-only]', publishId);
        let uiJsonSendPath = $('input[name=send-path]', publishId);
        let uiJsonGetPath = $('input[name=get-path]', publishId);
        this.publishUI = {
            "versionUp": uiVersionUp.prop('checked'),
            "audioOnly": uiAudioOnly.prop('checked'),
            "jsonSendPath": uiJsonSendPath.val(),
            "jsonGetPath": uiJsonGetPath.val()
        }
    }

    _getStagingDir() {
        const path = require('path');
        const UUID = require('pure-uuid');
        const os = require('os');

        const id = new UUID(4).format();
        return path.join(os.tmpdir(), id);
    }

    /**
     * Create staging directories and copy project files
     * @param {object} projectData Project JSON data
     */
    _copyProjectFiles(projectData) {
        const path = require('path');
        const fs = require('fs');
        const mkdirp = require('mkdirp');

        this.stagingDir = this._getStagingDir();

        this.progress(`Creating directory [ ${this.stagingDir} ]`, true);

        mkdirp.sync(this.stagingDir);

        let stagingDir = Pype.convertPathString(this.stagingDir);
        const destination = Pype.convertPathString(
            path.join(stagingDir, projectData.projectfile));

        this.progress(`Copying files from [ ${projectData.projectpath} ] -> [ ${destination} ]`);
        fs.copyFileSync(projectData.projectpath, destination);

        this.progress("Project files copied.", true);
    }

    _encodeRepresentation(repre) {
        var self = this;
        return new Promise(function(resolve, reject) {
            self.csi.evalScript('$.pype.encodeRepresentation(' + JSON.stringify(repre) + ');', (result) => {
                if (result == "EvalScript error.") {
                    reject(result);
                }
                self.progress("Encoding files to Encoder queue submitted ...", true);
                const jsonfile = require('jsonfile');
                let jsonContent = JSON.parse(result);
                if (self.publishUI.jsonSendPath == "") {
                    self.publishUI.jsonSendPath = self.stagingDir + "\\publishSend.json";
                    $('#publish input[name=send-path]').val(self.publishUI.jsonSendPath);
                }
                if (self.publishUI.jsonGetPath == "") {
                    self.publishUI.jsonGetPath = self.stagingDir + "_publishGet.json";
                    $('#publish input[name=get-path]').val(self.publishUI.jsonGetPath);
                }
                jsonfile.writeFile(self.publishUI.jsonSendPath, jsonContent);
                resolve(result);
            });
        });
    }

    _getPyblishRequest(stagingDir) {
        var self = this;
        return new Promise(function(resolve, reject) {
            self.csi.evalScript("$.pype.getPyblishRequest('" + stagingDir + "', '" + self.publishUI.audioOnly + "');", (result) => {
                if (result === "null" || result === "EvalScript error.") {
                    self.error(`cannot create publish request data ${result}`);
                    reject("cannot create publish request data");
                } else {
                    console.log(`Request generated: ${result}`);
                    resolve(result);
                }
            });
        });
    }

    publish() {
        this._gatherPublishUI();
        if (this.publishUI.jsonSendPath === "") {
            // path is empty, so we first prepare data for publishing
            // and create json

            this.progress("Gathering project data ...", true);
            this.csi.evalScript('$.pype.getProjectFileData();', (result) => {
                this._copyProjectFiles(JSON.parse(result))
                // create request and start encoding
                // after that is done, we should recieve event and continue in
                // _encodingDone()
                this.progress("Creating publishing request ...", true)
                this._getPyblishRequest(Pype.convertPathString(this.stagingDir))
                .then(result => {
                    this.progress('Encoding ...');
                    this._encodeRepresentation(JSON.parse(result))
                    .then(result => {
                      console.log('printing result from enconding.. ' + result);
                    })
                    .catch(error => {
                        this.error(`failed to encode: ${error}`);
                    });
                }, error => {
                    this.error(`failed to publish: ${error}`);
                });
                this.progress("Waiting for result ...");
            });
        } else {
            // load request
            var dataToPublish = {
                "adobePublishJsonPathSend": this.publishUI.jsonSendPath,
                "adobePublishJsonPathGet": this.publishUI.jsonGetPath,
                "project": this.env.AVALON_PROJECT,
                "asset": this.env.AVALON_ASSET,
                "task": this.env.AVALON_TASK,
                "workdir": Pype.convertPathString(this.env.AVALON_WORKDIR),
                "AVALON_APP": this.env.AVALON_APP,
                "AVALON_APP_NAME": this.env.AVALON_APP_NAME
            }
            // C:\Users\jezsc\AppData\Local\Temp\4c56ba52-8839-44de-b327-0187c79d0814\publishSend.json
            this.pras.publish(JSON.stringify(dataToPublish))
            .then((result) => {
                const fs = require('fs');
                if (fs.existsSync(result.return_data_path)) {
                    if (this.publishUI.versionUp) {
                        this.progress('Saving new version of the project file', true);
                        this.csi.evalScript('$.pype.versionUpWorkFile();');
                    }
                    // here jsonSetPath and jsonGetPath are set to gui
                    $('#publish input[name=send-path]').val("");
                    $('#publish input[name=get-path]').val("");
                    this.progress("Publishing done.", true);
                } else {
                    this.error("Publish has not finished correctly");
                    throw "Publish has not finished correctly";
                }
            }, (error) => {
                this.error("Invalid response from server");
                console.error(error);
            });
        }
    }

    _encodingDone(event) {
        // this will be global in this context
        console.debug(event);
        this.pype.progress("Publishing event after encoding finished recieved ...", true);
        var dataToPublish = {
            "adobePublishJsonPathSend": this.pype.publishUI.jsonSendPath,
            "adobePublishJsonPathGet": this.pype.publishUI.jsonGetPath,
            "gui": true,
            // "publishPath": Pype.convertPathString(this.pype.env.PUBLISH_PATH),
            "project": this.pype.env.AVALON_PROJECT,
            "asset": this.pype.env.AVALON_ASSET,
            "task": this.pype.env.AVALON_TASK,
            "workdir": Pype.convertPathString(this.pype.env.AVALON_WORKDIR),
            "AVALON_APP": this.pype.env.AVALON_APP,
            "AVALON_APP_NAME": this.pype.env.AVALON_APP_NAME
        }

        this.pype.progress("Preparing publish ...", true);
        console.log(JSON.stringify(dataToPublish));
        this.pype.pras.publish(JSON.stringify(dataToPublish))
        .then((result) => {
            const fs = require('fs');
            if (fs.existsSync(result.return_data_path)) {
                if (this.pype.publishUI.versionUp) {
                    this.pype.progress('Saving new version of the project file', true);
                    this.pype.csi.evalScript('$.pype.versionUpWorkFile();');
                }
                // here jsonSetPath and jsonGetPath are set to gui
                $('#publish input[name=send-path]').val("");
                $('#publish input[name=get-path]').val("");
                this.pype.progress("Publishing done.", true);
            } else {
                this.pype.error("Publish has not finished correctly")
                throw "Publish has not finished correctly";
            }
        }, (error) => {
            this.pype.error("Invalid response from server");
            console.error(error);
        });
    }

    /**
     * Display error message in div
     * @param {String} message
     */
    error(message) {
        this.outputId.html(message);
        this.outputId.addClass("error");
        console.error(message);
    }

    /**
     * Display message in output div. If append is set, new message is appended to rest with <br>
     * @param {String} message
     * @param {Boolean} append
     */
    progress(message, append=false) {
        this.outputId.removeClass("error");
        if (append) {
            this.outputId.prepend(message + "<br/>");
        }
        console.info(message);
    }
}
$(function() {
    global.pype = new Pype();
});
