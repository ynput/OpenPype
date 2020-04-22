/*global CSInterface, $, PypeRestApiClient, SystemPath, document */
/* eslint-env node, es2017 */

class Pype {
    constructor() {
        var self = this;
        this.csi = new CSInterface();
        this.rootFolderPath = this.csi.getSystemPath(SystemPath.EXTENSION);
        var extensionRoot = this.rootFolderPath + "/jsx/";
        console.info("Loading premiere.jsx");
        this.csi.evalScript('$.evalFile("' + extensionRoot + '/PPRO/Premiere.jsx");');
        console.info("Loading pype.jsx");
        this.csi.evalScript('$.evalFile("' + extensionRoot + 'pype.jsx");');
        console.info("Loading batchRenamer.jsx");
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
            console.info(`Getting presets for ${this.env.AVALON_PROJECT}`);
            this.presets = this.pras.get_presets(this.env.AVALON_PROJECT)
            .then((presets) => {
                console.info("transferring presets to jsx")
                this.presets = presets;
                this.csi.evalScript('$.pype.setProjectPreset(' + JSON.stringify(presets) + ');', () => {
                    console.log("done");
                    // bind encoding jobs event listener
                    this.csi.addEventListener("pype.EncoderJobsComplete", this._encodingDone);
        
                    // Bind Interface buttons
                    this._bindButtons();
                });
            });
        });   
    }

    rename () {
        let renameId = document.querySelector('#rename');
        let data = {};
        data.ep = renameId.querySelector('input[name=episode]').value;
        data.epSuffix = renameId.querySelector('input[name=ep_suffix]').value;
      
        if (!data.ep) {
          this.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode code' + '")');
          return;
        }
      
        if (!data.epSuffix) {
          this.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode longer suffix' + '")');
          return;
        }
      
        console.log(`Doing rename ${data.ep} | ${data.epSuffix}`);
        this.csi.evalScript(
          'BatchRenamer.renameTargetedTextLayer(' + JSON.stringify(data) + ' );', (result) => {
            console.info(`Renaming result: ${result}`);
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
        var publishId = document.querySelector('#publish');
        var publishUI = {
            "publishId": publishId,
            "versionUp": publishId.querySelector('input[name=version-up]').checked,
            "audioOnly": publishId.querySelector('input[name=audio-only]').checked,
            "jsonSendPath": publishId.querySelector('input[name=send-path]').value,
            "jsonGetPath": publishId.querySelector('input[name=get-path]').value
        }
        this.publishUI = publishUI;
        return publishUI;
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

        console.info(`Creating directory [ ${this.stagingDir} ]`);

        mkdirp.sync(this.stagingDir)

        let stagingDir = Pype.convertPathString(this.stagingDir);
        const destination = Pype.convertPathString(
            path.join(stagingDir, projectData.projectfile));

        console.info(`Copying files from [ ${projectData.projectpath} ] -> [ ${destination} ]`);
        fs.copyFileSync(projectData.projectpath, destination);

        console.info("Project files copied.")
    }

    _encodeRepresentation(repre) {
        var self = this;
        return new Promise(function(resolve, reject) {
            self.csi.evalScript('$.pype.encodeRepresentation(' + JSON.stringify(repre) + ');', (result) => {
                if (result == "EvalScript error.") {
                    reject(result);
                }
                resolve(result);
            });
        });
    }

    _getPyblishRequest(stagingDir) {
        var self = this;
        return new Promise(function(resolve, reject) {
            console.log(`Called with ${stagingDir} and ${self.publishUI.audioOnly}`);
            self.csi.evalScript("$.pype.getPyblishRequest('" + stagingDir + "', '" + self.publishUI.audioOnly + "');", (result) => {
                if (result === "null" || result === "EvalScript error.") {
                    console.error(`cannot create publish request data ${result}`);
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

            console.log("Gathering project data ...")
            this.csi.evalScript('$.pype.getProjectFileData();', (result) => {
                this._copyProjectFiles(JSON.parse(result))
                // create request and start encoding
                // after that is done, we should recieve event and continue in
                // _encodingDone()
                console.log("Creating request ...")
                this._getPyblishRequest(Pype.convertPathString(this.stagingDir))
                .then(result => {
                    console.log("Encoding ...");
                    this._encodeRepresentation(JSON.parse(result)).catch(error => {
                        console.error(`failed to encode: ${error}`);
                    });
                }, error => {
                    console.error(`failed to publish: ${error}`);
                });
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
                        console.log('Saving new version of the project file');
                        this.csi.evalScript('$.pype.versionUpWorkFile();');
                    }
                } else {
                    console.error("Publish has not finished correctly")
                    throw "Publish has not finished correctly";
                }
            });
        }
    }

    _encodingDone(event) {
        var dataToPublish = {
            "adobePublishJsonPathSend": this.publishUI.jsonSendPath,
            "adobePublishJsonPathGet": this.publishUI.jsonGetPath,
            "gui": true,
            "publishPath": Pype.convertPathString(this.env.PUBLISH_PATH),
            "project": this.env.AVALON_PROJECT,
            "asset": this.env.AVALON_ASSET,
            "task": this.env.AVALON_TASK,
            "workdir": Pype.convertPathString(this.env.ENV.AVALON_WORKDIR),
            "host": this.env.ENV.AVALON_APP
        }

        this.pras.publish(dataToPublish)
        .then((result) => {
            const fs = require('fs');
            if (fs.existsSync(result.return_data_path)) {
                if (this.publishUI.versionUp) {
                    console.log('Saving new version of the project file');
                    this.csi.evalScript('$.pype.versionUpWorkFile();');
                }
            } else {
                console.error("Publish has not finished correctly")
                throw "Publish has not finished correctly";
            }
        });
    }
}

$(document).ready(function() {
    new Pype();
});
// -------------------------------------------------------

