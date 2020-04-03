/*************************************************************************
 * ADOBE CONFIDENTIAL
 * ___________________
 *
 * Copyright 2014 Adobe
 * All Rights Reserved.
 *
 * NOTICE: Adobe permits you to use, modify, and distribute this file in
 * accordance with the terms of the Adobe license agreement accompanying
 * it. If you have received this file from a source other than Adobe,
 * then your use, modification, or distribution of it requires the prior
 * written permission of Adobe.
 **************************************************************************/

if (typeof ($) === 'undefined') {
  var $ = {};
}

if (typeof (pype) === 'undefined') {
  var pype = {};
}

if (typeof (br) === 'undefined') {
  var br = {};
}

if (typeof (app) === 'undefined') {
  var app = {};
}

if (typeof (JSON) === 'undefined') {
  var JSON = {};
}

function keepExtention () {
  return app.setExtensionPersistent('com.pype.avalon', 0);
}

keepExtention()

$._ext = {
  // Evaluate a file and catch the exception.
  evalFile: function (path) {
    try {
      $.evalFile(path);
      $.writeln(path);
    } catch (e) {
      $.writeln(e);
      alert('Exception:' + e);
    }
  },
  // Evaluate all the files in the given folder
  evalFiles: function (jsxFolderPath) {
    var folder = new Folder(jsxFolderPath);
    if (folder.exists) {
      var jsxFiles = folder.getFiles('*.jsx');
      for (var i = 0; i < jsxFiles.length; i++) {
        var jsxFile = jsxFiles[i];
        $._ext.evalFile(jsxFile);
      }
    }
  },
  // entry-point function to call scripts more easily & reliably
  callScript: function (dataStr) {
    try {
      var dataObj = JSON.parse(decodeURIComponent(dataStr));
      if (
        !dataObj ||
        !dataObj.namespace ||
        !dataObj.scriptName ||
        !dataObj.args
      ) {
        throw new Error('Did not provide all needed info to callScript!');
      }
      // call the specified jsx-function
      var result = $[dataObj.namespace][dataObj.scriptName].apply(
        null,
        dataObj.args
      );
      // build the payload-object to return
      var payload = {
        err: 0,
        result: result
      };
      return encodeURIComponent(JSON.stringify(payload));
    } catch (err) {
      payload = {
        err: err
      };
      return encodeURIComponent(JSON.stringify(payload));
    }
  }
};

// var dalsiJsxFile = 'C:\\Users\\hubert\\CODE\\pype-setup\\repos\\pype-config\\pype\\premiere\\extensions\\com.pype.avalon\\jsx\\pype.jsx';
// $.evalFile(dalsiJsxFile);
