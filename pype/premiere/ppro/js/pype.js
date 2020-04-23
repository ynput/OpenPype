/*global CSInterface, $, PypeRestApiClient, SystemPath */
/* eslint-env node, es2017 */

class Pype {
    constructor() {
        var self = this;
        this.csi = new CSInterface();
        this.outputId = $("#output");

        this.rootFolderPath = this.csi.getSystemPath(SystemPath.EXTENSION);
        var extensionRoot = this.rootFolderPath + "/jsx/";
        this.progress("Loading premiere.jsx", true);
        this.csi.evalScript('$.evalFile("' + extensionRoot + '/PPRO/Premiere.jsx");');
        this.progress("Loading pype.jsx", true);
        this.csi.evalScript('$.evalFile("' + extensionRoot + 'pype.jsx");');
        this.progress("Loading batchRenamer.jsx", true);
        this.csi.evalScript('$.evalFile("' + extensionRoot + 'batchRenamer.jsx");');

        // get environment
        this.csi.evalScript('$.pype.getProjectFileData();', (result) => {
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
                this.progress("transferring presets to jsx", true)
                this.presets = presets;
                this.csi.evalScript('$.pype.setProjectPreset(' + JSON.stringify(presets) + ');', () => {
                    this.progress("done", true);
                    // bind encoding jobs event listener
                    this.csi.addEventListener("pype.EncoderJobsComplete", this._encodingDone);

                    // Bind Interface buttons
                    this._bindButtons();
                });
            });
        });
    }

    rename () {
        let $renameId = $('#rename');
        let data = {};
        data.ep = $renameId('input[name=episode]').val();
        data.epSuffix = $renameId('input[name=ep_suffix]').val();

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
        let uiVersionUp = publishId.querySelector('input[name=version-up]');
        let uiAudioOnly = publishId.querySelector('input[name=audio-only]');
        let uiJsonSendPath = publishId.querySelector('input[name=send-path]');
        let uiJsonGetPath = publishId.querySelector('input[name=get-path]');
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

        this.progress(`Copying files from [ ${projectData.projectpath} ] -> [ ${destination} ]`, true);
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
                self.progress("encoding submitted ...", true);
                const jsonfile = require('jsonfile');
                let jsonContent = JSON.parse(result);
                if (self.publishUI.jsonSendPath == "") {
                    self.publishUI.jsonSendPath = self.stagingDir + "\\publishSend.json";
                }
                if (self.publishUI.jsonGetPath == "") {
                    self.publishUI.jsonGetPath = self.stagingDir + "\\publishGet.json";
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

            this.progress("Gathering project data ...", true)
            this.csi.evalScript('$.pype.getProjectFileData();', (result) => {
                this._copyProjectFiles(JSON.parse(result))
                // create request and start encoding
                // after that is done, we should recieve event and continue in
                // _encodingDone()
                this.progress("Creating request ...", true)
                this._getPyblishRequest(Pype.convertPathString(this.stagingDir))
                .then(result => {
                    this.progress("Encoding ...", true);
                    this._encodeRepresentation(JSON.parse(result))
                    .then(result => {
                      console.log('printing result from enconding.. ' + result);
                      // here jsonSetPath and jsonGetPath are set to gui
                      this.uiJsonSendPath.value = this.publishUI.jsonSendPath;
                      this.uiJsonGetPath.value = this.publishUI.jsonGetPath;
                    })
                    .catch(error => {
                        this.error(`failed to encode: ${error}`);
                    });
                }, error => {
                    this.error(`failed to publish: ${error}`);
                });
                this.progress("waiting for result", true);
            });
        } else {
            // load request
            var request = require(this.publishUI.jsonSendPath);
            this.pras.publish(request)
            .then((result) => {
                const fs = require('fs');
                if (fs.existsSync(result.return_data_path)) {
                    this.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(result) + ');');
                    if (this.publishUI.versionUp) {
                        this.progress('Saving new version of the project file');
                        this.csi.evalScript('$.pype.versionUpWorkFile();');
                    }
                } else {
                    this.error("Publish has not finished correctly")
                    throw "Publish has not finished correctly";
                }
            });
        }
    }

    _encodingDone(event) {
        // this will be global in this context
        this.pype.progress("Event recieved ...", true);
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
                    this.pyp.progress('Saving new version of the project file', true);
                    this.pype.csi.evalScript('$.pype.versionUpWorkFile();');
                }
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

    error(message) {
        this.outputId.html(message);
        this.outputId.addClass("error");
        console.error(message);
    }

    progress(message, append=false) {
        this.outputId.removeClass("error");
        if (append) {
            this.outputId.append(message + "<br/>");
        }
        console.info(message);
    }
}
$(function() {
    global.pype = new Pype();
});

// -------------------------------------------------------
