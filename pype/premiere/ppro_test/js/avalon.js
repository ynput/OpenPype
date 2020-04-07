/* global CSInterface, $, querySelector, api, displayResult */

var csi = new CSInterface();
var output = document.getElementById('output');

var rootFolderPath = csi.getSystemPath(SystemPath.EXTENSION);
var timecodes = cep_node.require('node-timecodes');
var process = cep_node.require('process');


function getEnv() {
  csi.evalScript('pype.getProjectFileData();', function (result) {
    process.env.EXTENSION_PATH = rootFolderPath
    window.ENV = process.env;
    var resultData = JSON.parse(result);
    for (key in resultData) {
      window.ENV[key] = resultData[key];
    };
    csi.evalScript('pype.setEnvs(' + JSON.stringify(window.ENV) + ')');
  });
}

function renderClips() {
  csi.evalScript('pype.transcodeExternal(' + rootFolderPath + ');', function (result) {
    displayResult(result);
  });
}

function displayResult(r) {
  console.log(r);
  csi.evalScript('$.writeln( ' + JSON.stringify(r) + ' )');
  output.classList.remove("error");
  output.innerText = r;
}

function displayError(e) {
  output.classList.add("error");
  output.innerText = e.message;
}

function loadJSX() {
  // get the appName of the currently used app. For Premiere Pro it's "PPRO"
  var appName = csi.hostEnvironment.appName;
  var extensionPath = csi.getSystemPath(SystemPath.EXTENSION);

  // load general JSX script independent of appName
  var extensionRootGeneral = extensionPath + '/jsx/';
  csi.evalScript('$._ext.evalFiles("' + extensionRootGeneral + '")');

  // load JSX scripts based on appName
  var extensionRootApp = extensionPath + '/jsx/' + appName + '/';
  csi.evalScript('$._ext.evalFiles("' + extensionRootApp + '")');
  // csi.evalScript('$._PPP_.logConsoleOutput()');
  getEnv();

  csi.evalScript('$._PPP_.updateEventPanel( "' + "all plugins are loaded" + '" )');
  csi.evalScript('$._PPP_.updateEventPanel( "' + "testing function done" + '" )');

}

// run all at loading
loadJSX()


function loadAnimationRendersToTimeline() {
  // it will get type of asset and extension from input
  // and start loading script from jsx
  var $ = querySelector('#load');
  var data = {};
  data.subset = $('input[name=type]').value;
  data.subsetExt = $('input[name=ext]').value;
  var requestList = [];
  // get all selected clips
  csi.evalScript('pype.getClipsForLoadingSubsets( "' + data.subset + '" )', function (result) {
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
    // gets data from mongodb
    api.load_representations(window.ENV['AVALON_PROJECT'], requestList).then(
      function (avalonData) {
        // creates or updates data on timeline
        var makeData = {};
        makeData.binHierarchy = data.subset + '/' + data.subsetExt;
        makeData.clips = avalonData;
        makeData.numTracks = numTracks;
        csi.evalScript('pype.importFiles( ' + JSON.stringify(makeData) + ' )');
      }
    );
  });
}

function evalScript(script) {
  var callback = function (result) {
    displayResult(result);
  };
  csi.evalScript(script, callback);
}

function deregister() {
  api.deregister_plugin_path().then(displayResult);
}

function register() {
  var $ = querySelector('#register');
  var path = $('input[name=path]').value;
  api.register_plugin_path(path).then(displayResult);
}

function getStagingDir() {
  // create stagingDir
  const fs = require('fs-extra');
  const os = require('os');
  const path = require('path');
  const UUID = require('pure-uuid');
  const id = new UUID(4).format();
  const stagingDir = path.join(os.tmpdir(), id);

  fs.mkdirs(stagingDir);
  return stagingDir;

}

function convertPathString(path) {
  return path.replace(
    new RegExp('\\\\', 'g'), '/').replace(new RegExp('//\\?/', 'g'), '');
}

function publish() {
  var $ = querySelector('#publish');
  // var gui = $('input[name=gui]').checked;
  var gui = true;
  var versionUp = $('input[name=version-up]').checked;
  var audioOnly = $('input[name=audio-only]').checked;
  var jsonSendPath = $('input[name=send-path]').value;
  var jsonGetPath = $('input[name=get-path]').value;
  var publish_path = window.ENV['PUBLISH_PATH'];

  if (jsonSendPath == '') {
    // create temp staging directory on local
    var stagingDir = convertPathString(getStagingDir());

    // copy project file to stagingDir
    const fs = require('fs-extra');
    const path = require('path');

    csi.evalScript('pype.getProjectFileData();', function (result) {
      displayResult(result);
      var data = JSON.parse(result);
      displayResult(stagingDir);
      displayResult(data.projectfile);
      var destination = convertPathString(path.join(stagingDir, data.projectfile));
      displayResult('copy project file');
      displayResult(data.projectfile);
      displayResult(destination);
      fs.copyFile(data.projectpath, destination);
      displayResult('project file coppied!');
    });

    // publishing file
    csi.evalScript('pype.getPyblishRequest("' + stagingDir + '", ' + audioOnly + ');', function (r) {
      var request = JSON.parse(r);
      displayResult(JSON.stringify(request));

      csi.evalScript('pype.encodeRepresentation(' + JSON.stringify(request) + ');', function (result) {
        // create json for pyblish
        var jsonfile = require('jsonfile');
        var jsonSendPath = stagingDir + '_send.json'
        var jsonGetPath = stagingDir + '_get.json'
        $('input[name=send-path]').value = jsonSendPath;
        $('input[name=get-path]').value = jsonGetPath;
        var jsonContent = JSON.parse(result);
        jsonfile.writeFile(jsonSendPath, jsonContent);
        var checkingFile = function (path) {
          var timeout = 1000;
          setTimeout(function () {
              if (fs.existsSync(path)) {
                // register publish path
                api.register_plugin_path(publish_path).then(displayResult);
                // send json to pyblish
                api.publish(jsonSendPath, jsonGetPath, gui).then(function (result) {
                  // check if resulted path exists as file
                  if (fs.existsSync(result.get_json_path)) {
                    // read json data from resulted path
                    displayResult('Updating metadata of clips after publishing');

                    jsonfile.readFile(result.get_json_path, function (err, json) {
                      csi.evalScript('pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
                    })

                    // version up project
                    if (versionUp) {
                      displayResult('Saving new version of the project file');
                      csi.evalScript('pype.versionUpWorkFile();');
                    };
                  } else {
                    // if resulted path file not existing
                    displayResult('Publish has not been finished correctly. Hit Publish again to publish from already rendered data, or Reset to render all again.');
                  };

                });

              } else {
                displayResult('waiting');
                checkingFile(path);
              };
            },
            timeout)
        };

        checkingFile(jsonContent.waitingFor)
      });
    });
  } else {
    // register publish path
    api.register_plugin_path(publish_path).then(displayResult);
    // send json to pyblish
    api.publish(jsonSendPath, jsonGetPath, gui).then(function (result) {
      // check if resulted path exists as file
      if (fs.existsSync(result.get_json_path)) {
        // read json data from resulted path
        displayResult('Updating metadata of clips after publishing');

        jsonfile.readFile(result.get_json_path, function (err, json) {
          csi.evalScript('pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
        })

        // version up project
        if (versionUp) {
          displayResult('Saving new version of the project file');
          csi.evalScript('pype.versionUpWorkFile();');
        };
      } else {
        // if resulted path file not existing
        displayResult('Publish has not been finished correctly. Hit Publish again to publish from already rendered data, or Reset to render all again.');
      };

    });
  };
  // $('input[name=send-path]').value = '';
  // $('input[name=get-path]').value = '';
}

function context() {
  var $ = querySelector('#context');
  var project = $('input[name=project]').value;
  var asset = $('input[name=asset]').value;
  var task = $('input[name=task]').value;
  var app = $('input[name=app]').value;
  api.context(project, asset, task, app).then(displayResult);
}

function tc(timecode) {
  var seconds = timecodes.toSeconds(timecode);
  var timec = timecodes.fromSeconds(seconds);
  displayResult(seconds);
  displayResult(timec);
}

function rename() {
  var $ = querySelector('#rename');
  var data = {};
  data.ep = $('input[name=episode]').value;
  data.epSuffix = $('input[name=ep_suffix]').value;

  if (!data.ep) {
    csi.evalScript('pype.alert_message("' + 'Need to fill episode code' + '")');
    return;
  };

  if (!data.epSuffix) {
    csi.evalScript('pype.alert_message("' + 'Need to fill episode longer suffix' + '")');
    return;
  };

  csi.evalScript('br.renameTargetedTextLayer( ' + JSON.stringify(data) + ' );', function (result) {
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
  publish();
});

$('#btn-send-reset').click(function () {
  var $ = querySelector('#publish');
  $('input[name=send-path]').value = '';
});
$('#btn-get-reset').click(function () {
  var $ = querySelector('#publish');
  $('input[name=get-path]').value = '';
});
$('#btn-get-active-sequence').click(function () {
  evalScript('pype.getActiveSequence();');
});

$('#btn-get-selected').click(function () {
  $('#output').html('getting selected clips info ...');
  evalScript('pype.getSelectedItems();');
});

$('#btn-get-env').click(function () {
  console.log("print this")
});

$('#btn-get-projectitems').click(function () {
  evalScript('pype.getProjectItems();');
});

$('#btn-metadata').click(function () {
  var $ = querySelector('#publish');
  var path = $('input[name=get-path]').value;
  var jsonfile = require('jsonfile');
  displayResult(path);
  jsonfile.readFile(path, function (err, json) {
    csi.evalScript('pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
    displayResult('Metadata of clips after publishing were updated');
  })


});
$('#btn-get-frame').click(function () {
  evalScript('$._PPP_.exportCurrentFrameAsPNG();');
});

$('#btn-tc').click(function () {
  tc('00:23:47:10');
});

$('#btn-generateRequest').click(function () {
  evalScript('pype.getPyblishRequest();');
});

$('#btn-newWorkfileVersion').click(function () {
  evalScript('pype.versionUpWorkFile();');
});
