/* global CSInterface, $, querySelector, api, displayResult */
var csi = new CSInterface();

function deregister () {
  api.deregister_plugin_path().then(displayResult);
}

function register () {
  var $ = querySelector('#register');
  var path = $('input[name=path]').value;
  api.register_plugin_path(path).then(displayResult);
}

function publish () {
  var $ = querySelector('#publish');
  var path = $('input[name=path]').value;
  var gui = $('input[name=gui]').checked;
  api.publish(path, gui).then(displayResult);
}

function context () {
  var $ = querySelector('#context');
  var project = $('input[name=project]').value;
  var asset = $('input[name=asset]').value;
  var task = $('input[name=task]').value;
  var app = $('input[name=app]').value;
  api.context(project, asset, task, app).then(displayResult);
}

// bind buttons

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

$('#btn-get-sequence').click(function () {
  csi.evalScript('getSequences();', function (result) {
    displayResult(result);
  });
});

$('#btn-get-selected').click(function () {
  $('#output').html('getting selected clips info ...');
  csi.evalScript('getSelectedItems();', function (result) {
    displayResult(result);
  });
});
