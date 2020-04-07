/* global CSInterface, $, querySelector, pras, SystemPath, displayResult */

var csi = new CSInterface();
var output = document.getElementById('output');
var process = cep_node.require('process');
var timecodes = cep_node.require('node-timecodes');

var _pype = {
  csi: csi,
  rootFolderPath: csi.getSystemPath(SystemPath.EXTENSION),
  getPresets: function () {
    var url = pras.getApiServerUrl();
    var projectName = 'J01_jakub_test';
    var urlType = 'adobe/presets';
    var restApiGetUrl = [url, urlType, projectName].join('/');
    return restApiGetUrl;
  },
  getEnv: function () {
    _pype.csi.evalScript('$.pype.getProjectFileData();', function (result) {
      process.env.EXTENSION_PATH = _pype.rootFolderPath;
      _pype.ENV = process.env;
      var url = pras.getApiServerUrl();
      console.log(url);
      // _pype.csi.evalScript('$.writeln( "' + url + '" );');
      console.log(result);
      console.log(_pype.rootFolderPath);
      var resultData = JSON.parse(result);
      for (var key in resultData) {
        _pype.ENV[key] = resultData[key];
      }
      csi.evalScript('$.pype.setEnvs(' + JSON.stringify(window.ENV) + ')');
    });
  }
};

function renderClips() {
  _pype.csi.evalScript('$.pype.transcodeExternal(' + pras.rootFolderPath + ');', function (result) {
    displayResult(result);
  });
}

function displayResult(r) {
  console.log(r);
  _pype.csi.evalScript('$.writeln( ' + JSON.stringify(r) + ' )');
  output.classList.remove("error");
  output.innerText = r;
}

function displayError(e) {
  output.classList.add("error");
  output.innerText = e.message;
}

function loadJSX() {
  // get the appName of the currently used app. For Premiere Pro it's "PPRO"
  var appName = _pype.csi.hostEnvironment.appName;
  var extensionPath = _pype.csi.getSystemPath(SystemPath.EXTENSION);

  // load general JSX script independent of appName
  // var extensionRootGeneral = extensionPath + '/jsx/';
  _pype.csi.evalScript('$._ext.evalFiles("' + extensionPath + '")');

  _pype.csi.evalScript('$._PPP_.updateEventPanel( "' + "all plugins are loaded" + '" )');
  _pype.csi.evalScript('$._PPP_.updateEventPanel( "' + "testing function done" + '" )');

}

// run all at loading
loadJSX()

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
    // gets data from mongodb
    pras.load_representations(_pype.ENV['AVALON_PROJECT'], requestList).then(
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

function evalScript(script) {
  var callback = function (result) {
    displayResult(result);
  };
  _pype.csi.evalScript(script, callback);
}

function deregister() {
  pras.deregister_plugin_path().then(displayResult);
}

function register() {
  var $ = querySelector('#register');
  var path = $.querySelector('input[name=path]').value;
  pras.register_plugin_path(path).then(displayResult);
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
  // var gui = $.querySelector('input[name=gui]').checked;
  var gui = true;
  var versionUp = $.querySelector('input[name=version-up]').checked;
  var audioOnly = $.querySelector('input[name=audio-only]').checked;
  var jsonSendPath = $.querySelector('input[name=send-path]').value;
  var jsonGetPath = $.querySelector('input[name=get-path]').value;
  var publish_path = _pype.ENV['PUBLISH_PATH'];

  if (jsonSendPath == '') {
    // create temp staging directory on local
    var stagingDir = convertPathString(getStagingDir());

    // copy project file to stagingDir
    const fs = require('fs-extra');
    const path = require('path');

    _pype.csi.evalScript('$.pype.getProjectFileData();', function (result) {
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
    _pype.csi.evalScript('$.pype.getPyblishRequest("' + stagingDir + '", ' + audioOnly + ');', function (r) {
      var request = JSON.parse(r);
      displayResult(JSON.stringify(request));

      _pype.csi.evalScript('$.pype.encodeRepresentation(' + JSON.stringify(request) + ');', function (result) {
        // create json for pyblish
        var jsonfile = require('jsonfile');
        var jsonSendPath = stagingDir + '_send.json'
        var jsonGetPath = stagingDir + '_get.json'
        $.querySelector('input[name=send-path]').value = jsonSendPath;
        $.querySelector('input[name=get-path]').value = jsonGetPath;
        var jsonContent = JSON.parse(result);
        jsonfile.writeFile(jsonSendPath, jsonContent);
        var checkingFile = function (path) {
          var timeout = 1000;
          setTimeout(function () {
              if (fs.existsSync(path)) {
                // register publish path
                pras.register_plugin_path(publish_path).then(displayResult);
                // send json to pyblish
                pras.publish(jsonSendPath, jsonGetPath, gui).then(function (result) {
                  // check if resulted path exists as file
                  if (fs.existsSync(result.get_json_path)) {
                    // read json data from resulted path
                    displayResult('Updating metadata of clips after publishing');

                    jsonfile.readFile(result.get_json_path, function (err, json) {
                      _pype.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
                    })

                    // version up project
                    if (versionUp) {
                      displayResult('Saving new version of the project file');
                      _pype.csi.evalScript('$.pype.versionUpWorkFile();');
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
    pras.register_plugin_path(publish_path).then(displayResult);
    // send json to pyblish
    pras.publish(jsonSendPath, jsonGetPath, gui).then(function (result) {
      // check if resulted path exists as file
      if (fs.existsSync(result.get_json_path)) {
        // read json data from resulted path
        displayResult('Updating metadata of clips after publishing');

        jsonfile.readFile(result.get_json_path, function (err, json) {
          _pype.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
        })

        // version up project
        if (versionUp) {
          displayResult('Saving new version of the project file');
          _pype.csi.evalScript('$.pype.versionUpWorkFile();');
        };
      } else {
        // if resulted path file not existing
        displayResult('Publish has not been finished correctly. Hit Publish again to publish from already rendered data, or Reset to render all again.');
      };

    });
  };
  // $.querySelector('input[name=send-path]').value = '';
  // $.querySelector('input[name=get-path]').value = '';
}

function context() {
  var $ = querySelector('#context');
  var project = $.querySelector('input[name=project]').value;
  var asset = $.querySelector('input[name=asset]').value;
  var task = $.querySelector('input[name=task]').value;
  var app = $.querySelector('input[name=app]').value;
  pras.context(project, asset, task, app).then(displayResult);
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
  data.ep = $.querySelector('input[name=episode]').value;
  data.epSuffix = $.querySelector('input[name=ep_suffix]').value;

  if (!data.ep) {
    _pype.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode code' + '")');
    return;
  };

  if (!data.epSuffix) {
    _pype.csi.evalScript('$.pype.alert_message("' + 'Need to fill episode longer suffix' + '")');
    return;
  };

  _pype.csi.evalScript('br.renameTargetedTextLayer( ' + JSON.stringify(data) + ' );', function (result) {
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
  var jsonfile = require('jsonfile');
  displayResult(path);
  jsonfile.readFile(path, function (err, json) {
    _pype.csi.evalScript('$.pype.dumpPublishedInstancesToMetadata(' + JSON.stringify(json) + ');');
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
  evalScript('$.pype.getPyblishRequest();');
});

$('#btn-newWorkfileVersion').click(function () {
  evalScript('$.pype.versionUpWorkFile();');
});


_pype.getEnv();
