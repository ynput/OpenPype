/* global CSInterface, $, cep_node, querySelector, pras, SystemPath, displayResult */

var csi = new CSInterface();
var output = document.getElementById('output');
var process = require('process');
var timecodes = require('node-timecodes');

function displayResult (r) {
  console.log(r);
  _pype.csi.evalScript('$.writeln( ' + JSON.stringify(r) + ' );');
  output.classList.remove('error');
  output.innerText = r;
  _pype.csi.evalScript('$.pype.log( ' + JSON.stringify(r) + ' );');
}

function displayError (e) {
  _pype.csi.evalScript('$.pype.alert_message( ' + JSON.stringify(e) + ' )');
  output.classList.add('error');
  output.innerText = e;
}

var _pype = {
  csi: csi,
  rootFolderPath: csi.getSystemPath(SystemPath.EXTENSION),
  displayResult: displayResult,
  displayError: displayError,
  getEnv: function () {
    _pype.csi.evalScript('$.pype.getProjectFileData();', function (result) {
      process.env.EXTENSION_PATH = _pype.rootFolderPath;
      _pype.ENV = process.env;
      console.log(result);
      console.log(_pype.rootFolderPath);
      var resultData = JSON.parse(result);
      for (var key in resultData) {
        _pype.ENV[key] = resultData[key];
      }
      csi.evalScript('$.pype.setEnvs(' + JSON.stringify(_pype.ENV) + ')');
    });
  }
};

// function renderClips () {
//   _pype.csi.evalScript('$.pype.transcodeExternal(' + pras.rootFolderPath + ');', function (result) {
//     displayResult(result);
//   });
// }

function loadExtensionDependencies () {
  // get extension path
  var extensionPath = _pype.csi.getSystemPath(SystemPath.EXTENSION);

  // get the appName of the currently used app. For Premiere Pro it's "PPRO"
  var appName = _pype.csi.hostEnvironment.appName;
  console.log('App name: ' + appName);

  // load general JS scripts from `extensionPath/lib/`
  _pype.csi.evalScript(
    '$._ext.evalJSFiles("' + extensionPath + '" )');
  console.log('js load done');

  // load all available JSX scripts from `extensionPath/jsx/*` with subfolders
  _pype.csi.evalScript(
    '$._ext.evalJSXFiles("' + extensionPath + '", "' + appName + '")');
  console.log('jsx load done');

  _pype.csi.evalScript('$._PPP_.updateEventPanel( "' + 'all plugins are loaded' + '" )');
}

// run all at loading
loadExtensionDependencies();

function querySelector (elementId) {
  return document.querySelector(elementId);
}

function loadAnimationRendersToTimeline () {
  // it will get type of asset and extension from input
  // and start loading script from jsx
  var $ = querySelector('#load');
  var data = {};
  data.subset = $.querySelector('input[name=type]').value;
  data.subsetExt = $.querySelector('input[name=ext]').value;
  var requestList = [];
  // get all selected clips
  _pype.csi.evalScript('$.pype.getClipsForLoadingSubsets( "' + data.subset + '" )', function (result) {
    // TODO: need to check if the clips are already created and this is just updating to last versions
    var resultObj = JSON.parse(result);
    var instances = resultObj[0];
    var numTracks = resultObj[1];

    var key = '';
    // creating requesting list of dictionaries
    for (key in instances) {
      var clipData = {};
      clipData.parentClip = instances[key];
      clipData.asset = key;
      clipData.subset = data.subset;
      clipData.representation = data.subsetExt;
      requestList.push(clipData);
    }

    if (requestList.length < 1) {
      _pype.csi.evalScript(
        '$.pype.alert_message("' + 'Need to select at least one clip' + '")');
      return;
    }

    // gets data from mongodb
    pras.load_representations(_pype.ENV.AVALON_PROJECT, requestList).then(
      function (avalonData) {
        // creates or updates data on timeline
        var makeData = {};
        makeData.binHierarchy = data.subset + '/' + data.subsetExt;
        makeData.clips = avalonData;
        makeData.numTracks = numTracks;
        _pype.csi.evalScript('$.pype.importFiles( ' + JSON.stringify(makeData) + ' )');
      }
    );
  });
}

function evalScript (script) {
  var callback = function (result) {
    displayResult(result);
  };
  _pype.csi.evalScript(script, callback);
}

function deregister () {
  pras.deregister_plugin_path().then(displayResult);
}

function register () {
  var $ = querySelector('#register');
  var path = $.querySelector('input[name=path]').value;
  pras.register_plugin_path(path).then(displayResult);
}

function getStagingDir () {
  const mkdirp = require('mkdirp');
  const os = require('os');
  const path = require('path');
  const UUID = require('pure-uuid');
  // create stagingDir
  var id = new UUID(4).format();
  var stagingDir = path.join(os.tmpdir(), id);

  mkdirp(stagingDir);
  return stagingDir;
}

function convertPathString (path) {
  return path.replace(
    new RegExp('\\\\', 'g'), '/').replace(new RegExp('//\\?/', 'g'), '');
}

function _publish () {
  var $ = querySelector('#publish');
  // var gui = $.querySelector('input[name=gui]').checked;
  var gui = true;
  var versionUp = $.querySelector('input[name=version-up]').checked;
  var audioOnly = $.querySelector('input[name=audio-only]').checked;
  var jsonSendPath = $.querySelector('input[name=send-path]').value;
  var jsonGetPath = $.querySelector('input[name=get-path]').value;

  if (jsonSendPath === '') {
    // create temp staging directory on local
    var stagingDir = convertPathString(getStagingDir());

    // copy project file to stagingDir
    _pype.csi.evalScript('$.pype.getProjectFileData();', function (result) {
      const path = require('path');
      const fs = require('fs');
      displayResult(result);
      var data = JSON.parse(result);
      displayResult(stagingDir);
      displayResult(data.projectfile);
      var destination = convertPathString(path.join(stagingDir, data.projectfile));
      displayResult('copy project file');
      displayResult(data.projectfile);
      displayResult(destination);
      fs.copyFile(data.projectpath, destination, displayResult);
      displayResult('project file coppied!');
    });

    // set presets to jsx
    pras.get_presets(_pype.ENV.AVALON_PROJECT, function (presetResult) {
      displayResult('result from get_presets: ' + presetResult);
      // publishing file
      _pype.csi.evalScript('$.pype.getPyblishRequest("' + stagingDir + '", ' + audioOnly + ');', function (r) {
        displayResult(r);
        // make sure the process will end if no instancess are returned
        if (r === 'null') {
          displayError('Publish cannot be finished. Please fix the previously pointed problems');
          return null;
        }
        var request = JSON.parse(r);
        displayResult(JSON.stringify(request));

        _pype.csi.evalScript('$.pype.encodeRepresentation(' + JSON.stringify(request) + ');', function (result) {
          // create json for pyblish
          const jsonfile = require('jsonfile');
          const fs = require('fs');
          var jsonSendPath = stagingDir + '_send.json';
          var jsonGetPath = stagingDir + '_get.json';
          $.querySelector('input[name=send-path]').value = jsonSendPath;
          $.querySelector('input[name=get-path]').value = jsonGetPath;
          var jsonContent = JSON.parse(result);
          jsonfile.writeFile(jsonSendPath, jsonContent);
          var checkingFile = function (path) {
            var timeout = 10;
            setTimeout(function () {
              if (fs.existsSync(path)) {
                displayResult('path were rendered: ' + path);
                // send json to pyblish
                var dataToPublish = {
                  "adobePublishJsonPathSend": jsonSendPath,
                  "adobePublishJsonPathGet": jsonGetPath,
                  "gui": gui,
                  "publishPath": convertPathString(_pype.ENV.PUBLISH_PATH),
                  "project": _pype.ENV.AVALON_PROJECT,
                  "asset": _pype.ENV.AVALON_ASSET,
                  "task": _pype.ENV.AVALON_TASK,
                  "workdir": convertPathString(_pype.ENV.AVALON_WORKDIR),
                  "host": _pype.ENV.AVALON_APP
                }
                displayResult('dataToPublish: ' + JSON.stringify(dataToPublish));
                pras.publish(dataToPublish).then(function (result) {
                  displayResult(
                    'pype.js:publish < pras.publish: ' + JSON.stringify(result));
                  // check if resulted path exists as file
                  if (fs.existsSync(result.return_data_path)) {
                    // read json data from resulted path
                    displayResult('Updating metadata of clips after publishing');

                    // jsonfile.readFile(result.return_data_path, function (json) {
                    //   _pype.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
                    // });

                    // version up project
                    if (versionUp) {
                      displayResult('Saving new version of the project file');
                      _pype.csi.evalScript('$.pype.versionUpWorkFile();');
                    }
                  } else {
                    // if resulted path file not existing
                    displayResult('Publish has not been finished correctly. Hit Publish again to publish from already rendered data, or Reset to render all again.');
                  }
                });
              } else {
                displayResult('waiting');
                checkingFile(path);
              }
            }, timeout);
          };
          checkingFile(jsonContent.waitingFor);
        });
      });
    });
  } else {
    // send json to pyblish
    pras.publish(jsonSendPath, jsonGetPath, gui).then(function (result) {
      const jsonfile = require('jsonfile');
      const fs = require('fs');
      // check if resulted path exists as file
      if (fs.existsSync(result.get_json_path)) {
        // read json data from resulted path
        displayResult('Updating metadata of clips after publishing');

        jsonfile.readFile(result.get_json_path, function (json) {
          _pype.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
        });

        // version up project
        if (versionUp) {
          displayResult('Saving new version of the project file');
          _pype.csi.evalScript('$.pype.versionUpWorkFile();');
        }
      } else {
        // if resulted path file not existing
        displayResult('Publish has not been finished correctly. Hit Publish again to publish from already rendered data, or Reset to render all again.');
      }
    });
  }
}

function context () {
  var $ = querySelector('#context');
  var project = $.querySelector('input[name=project]').value;
  var asset = $.querySelector('input[name=asset]').value;
  var task = $.querySelector('input[name=task]').value;
  var app = $.querySelector('input[name=app]').value;
  pras.context(project, asset, task, app).then(displayResult);
}

function tc (timecode) {
  var seconds = timecodes.toSeconds(timecode);
  var timec = timecodes.fromSeconds(seconds);
  displayResult(seconds);
  displayResult(timec);
}

function rename () {
  var $ = querySelector('#rename');
  var data = {};
  data.ep = $.querySelector('input[name=episode]').value;
  data.epSuffix = $.querySelector('input[name=ep_suffix]').value;

  if (!data.ep) {
    _pype.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode code' + '")');
    return;
  }

  if (!data.epSuffix) {
    _pype.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode longer suffix' + '")');
    return;
  }

  _pype.csi.evalScript(
    '$.batchrenamer.renameTargetedTextLayer( ' + JSON.stringify(
      data) + ' );', function (result) {
      displayResult(result);
    });
}

// bind buttons
$('#btn-getRernderAnimation').click(function () {
  loadAnimationRendersToTimeline();
});

$('#btn-rename').click(function () {
  rename();
});

$('#btn-set-context').click(function () {
  context();
});

$('#btn-register').click(function () {
  register();
});

$('#btn-deregister').click(function () {
  deregister();
});

$('#btn-publish').click(function () {
  _publish();
});

$('#btn-send-reset').click(function () {
  var $ = querySelector('#publish');
  $.querySelector('input[name=send-path]').value = '';
});
$('#btn-get-reset').click(function () {
  var $ = querySelector('#publish');
  $.querySelector('input[name=get-path]').value = '';
});
$('#btn-get-active-sequence').click(function () {
  evalScript('$.pype.getActiveSequence();');
});

$('#btn-get-selected').click(function () {
  $.querySelector('#output').html('getting selected clips info ...');
  evalScript('$.pype.getSelectedItems();');
});

$('#btn-get-env').click(function () {
  displayResult(window.ENV);
});

$('#btn-get-projectitems').click(function () {
  evalScript('$.pype.getProjectItems();');
});

$('#btn-metadata').click(function () {
  var $ = querySelector('#publish');
  var path = $.querySelector('input[name=get-path]').value;
  const jsonfile = require('jsonfile');
  displayResult(path);
  jsonfile.readFile(path, function (json) {
    _pype.csi.evalScript(
      '$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
    displayResult('Metadata of clips after publishing were updated');
  });
});

$('#btn-get-frame').click(function () {
  _pype.csi.evalScript('$._PPP_.exportCurrentFrameAsPNG();', function (result) {
    displayResult(result);
  });
});

$('#btn-tc').click(function () {
  tc('00:23:47:10');
});

$('#btn-generateRequest').click(function () {
  evalScript('$.pype.getPyblishRequest();');
});

$('#btn-newWorkfileVersion').click(function () {
  displayResult('Saving new version of the project file');
  _pype.csi.evalScript('$.pype.versionUpWorkFile();');
});

$('#btn-testing').click(function () {
  // var data = {
  //   "adobePublishJsonPathSend": "C:/Users/jezsc/_PYPE_testing/testing_data/premiere/95478408-91ee-4522-81f6-f1689060664f_send.json",
  //   "adobePublishJsonPathGet": "C:/Users/jezsc/_PYPE_testing/testing_data/premiere/95478408-91ee-4522-81f6-f1689060664f_get.json",
  //   "gui": true,
  //   "project": "J01_jakub_test",
  //   "asset": "editorial",
  //   "task": "conforming",
	// 	"workdir": "C:/Users/jezsc/_PYPE_testing/projects/J01_jakub_test/editorial/work/conforming",
  //   "publishPath": "C:/Users/jezsc/CODE/pype-setup/repos/pype/pype/plugins/premiere/publish",
  //   "host": "premiere"
  // }
  var data =  {"adobePublishJsonPathSend":"C:/Users/jezsc/AppData/Local/Temp/887ed0c3-d772-4105-b285-847ef53083cd_send.json","adobePublishJsonPathGet":"C:/Users/jezsc/AppData/Local/Temp/887ed0c3-d772-4105-b285-847ef53083cd_get.json","gui":true,"publishPath":"C:/Users/jezsc/CODE/pype-setup/repos/pype/pype/plugins/premiere/publish","project":"J01_jakub_test","asset":"editorial","task":"conforming","workdir":"C:/Users/jezsc/_PYPE_testing/projects/J01_jakub_test/editorial/work/conforming","host":"premiere"}

  pras.publish(data);
});

_pype.getEnv();
