/* global $, File, Folder, alert */
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

if (typeof (app) === 'undefined') {
  var app = {};
}

function keepExtention () {
  return app.setExtensionPersistent('com.pype', 0);
}

keepExtention();

var jsFilesList = ['json2.js'];

$._ext = {
  evalJSFiles: function (extensionFolder) {
    var libDir = new File(extensionFolder + '/lib');

    // adding JS from lib
    for (var jsi = 0; jsi < jsFilesList.length; jsi++) {
      var js = libDir + '/' + jsFilesList[jsi];
      try {
        $.evalFile(js);
        $.writeln(js);
      } catch (e) {
        $.writeln(e);
        alert('Exception:' + e);
      }
    }
  },
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
  evalJSXFiles: function (extensionFolder, appShortName) {
    // adding all jsx files
    var folderJsx = new Folder(extensionFolder + '/jsx/');
    var folderPpro = new Folder(folderJsx + '/' + appShortName);
    var foldersToImport = [folderPpro, folderJsx];
    for (var fi = 0; fi < foldersToImport.length; fi++) {
      if (foldersToImport[fi].exists) {
        var jsxFiles = foldersToImport[fi].getFiles('*.jsx');
        for (var i = 0; i < jsxFiles.length; i++) {
          var jsxFile = jsxFiles[i];
          $._ext.evalFile(jsxFile);
        }
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

// var extensionFolder = new Folder(
//   'C:/Users/jezsc/CODE/pype-setup/repos/pype/pype/premiere/extensions/com.pype');
// $.writeln(extensionFolder);
// var mainJsx = extensionFolder + '/pypeApp.jsx';
// var appName = 'PPRO';
// $.writeln(mainJsx);
// $.evalFile(mainJsx);
// $._ext.evalJSXFiles(extensionFolder, appName);
// $._ext.evalJSFiles(extensionFolder);
