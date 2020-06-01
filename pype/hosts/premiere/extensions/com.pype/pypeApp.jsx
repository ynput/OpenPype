/* global $, File, Folder, alert */

if (typeof ($) === 'undefined') {
  var $ = {};
}

if (typeof (app) === 'undefined') {
  var app = {};
}

function keepExtention () {
  return app.setExtensionPersistent('com.pype', 0);
}

keepExtention();
