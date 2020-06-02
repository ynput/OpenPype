/* global app, XMPMeta, ExternalObject, CSXSEvent, Folder */
/* --------------------------------------
   -. ==  [ part 0f PyPE CluB ] == .-
_______________.___._____________________
\______   \__  |   |\______   \_   _____/
 |     ___//   |   | |     ___/|    __)_
 |    |    \____   | |    |    |        \
 |____|    / ______| |____|   /_______  /
           \/                         \/
        .. __/ CliP R3N4M3R \__ ..
*/
var renamer = {};

/**
 * Sequence-rename selected clips and establish their hierarchy based upon provided
 * data. Using data.folder, data.episode, data.sequence to name a clip and write
 * resulting hierarchical clip data into sequence metadata via XMP.
 *
 * @param {Object} data - data {'folder', 'episode', 'sequence', 'pattern', 'increment', 'start'}
 * @return {String} state
 */
renamer.renameSeqHierarchy = function (data) { // eslint-disable-line no-unused-vars
  var sequence = app.project.activeSequence;
  var selected = sequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }
  app.setSDKEventMessage('pattern ' + data.pattern + '\n' + 'increment ' + data.increment, 'info');
  // get padding
  var padPtr = RegExp('(?:.*?)(#+)(.*)');
  var res = data.pattern.match(padPtr);
  // res is now null if there is no padding string (###) in Pattern
  // res[1] is padding string
  if (!res) {
    app.setSDKEventMessage('no padding string detected in pattern ' + data.pattern, 'error');
    return false;
  }

  // convert to int
  var index = parseInt(data.start);
  // change padding string to zero: '####' -> '0000'
  var rx = RegExp('#', 'g');
  var fgexp = RegExp('{folder}', 'i');
  var egexp = RegExp('{episode}', 'i');
  var sgexp = RegExp('{sequence}', 'i');
  var shotrg = RegExp('{shot}', 'i');
  var zero = res[1].replace(rx, '0');
  // iterate over selection
  var metadata = renamer.getSequencePypeMetadata(sequence);
  for (var c = 0; c < selected.length; c++) {
    var mediaType = selected[c].mediaType;
    if (mediaType === 'Audio') {
      continue
    }
    delete metadata.clips[selected[c].name];
    // convert index to string
    var indexStr = '' + index;
    // left-zero pad number
    var padding = zero.substring(0, zero.length - indexStr.length) + indexStr;
    // put name together
    // replace {shot} token
    selected[c].name = data.pattern.replace(shotrg, selected[c].name);
    selected[c].name = selected[c].name.replace(res[1], padding);
    selected[c].name = selected[c].name.replace(fgexp, data.folder);
    selected[c].name = selected[c].name.replace(egexp, data.episode);
    selected[c].name = selected[c].name.replace(sgexp, data.sequence);

    // fill in hierarchy if set
    var parents = [];
    var hierarchy = [];

    if (data.folder) {
      parents.push({
        'entityType': 'folder',
        'entityName': data.folder
      });
      hierarchy.push(data.folder);
    }

    if (data.episode) {
      parents.push({
        'entityType': 'episode',
        'entityName': data.episode
      });
      hierarchy.push(data.episode);
    }

    if (data.sequence) {
      parents.push({
        'entityType': 'sequence',
        'entityName': data.sequence
      });
      hierarchy.push(data.sequence);
    }

    // push it to metadata
    metadata.clips[selected[c].name] = {
      'parents': parents,
      'hierarchy': hierarchy.join('/')
    };

    // add increment
    index = index + parseInt(data.increment);
  }

  renamer.setSequencePypeMetadata(sequence, metadata);

  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Sequence rename seleced clips
 * @param {Object} data - {pattern, start, increment}
 */
renamer.renameSeq = function (data) { // eslint-disable-line no-unused-vars
  var selected = app.project.activeSequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }
  app.setSDKEventMessage('pattern ' + data.pattern + '\n' + 'increment ' + data.increment, 'info');
  // get padding
  var padPtr = RegExp('(?:.*?)(#+)(?:.*)');
  var res = data.pattern.match(padPtr);
  // res is now null if there is no padding string (###) in Pattern
  // res[1] is padding string

  if (!res) {
    app.setSDKEventMessage('no padding string detected in pattern ' + data.pattern, 'error');
    return false;
  }

  // convert to int
  var index = parseInt(data.start);
  // change padding string to zero: '####' -> '0000'
  var rx = RegExp('#', 'g');
  var zero = res[2].replace(rx, '0');
  // iterate over selection
  for (var c = 0; c < selected.length; c++) {
    // convert index to string
    var indexStr = '' + index;
    // left-zero pad number
    var padding = zero.substring(0, zero.length - indexStr.length) + indexStr;
    // put name together
    selected[c].name = data.pattern.replace(res[1], padding);
    // add increment
    index = index + parseInt(data.increment);
  }
  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Simple rename clips
 * @param {string} newName - new clip name. `{shot}` designates current clip name
 * @return {string} result - return stringified JSON status
 */
renamer.renameSimple = function (newName) { // eslint-disable-line no-unused-vars
  app.setSDKEventMessage('Replacing with pattern ' + newName, 'info');
  var selected = app.project.activeSequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }
  var rx = RegExp('{shot}', 'i');
  for (var c = 0; c < selected.length; c++) {
    // find {shot} token and replace it with existing clip name
    selected[c].name = newName.replace(rx, selected[c].name);
  }
  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Find string in clip name and replace it with another
 * @param {Object} data - {find, replaceWith} object
 * @return {string} result - return stringified JSON status
 */
renamer.renameFindReplace = function (data) { // eslint-disable-line no-unused-vars
  var selected = app.project.activeSequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }

  var rx = RegExp('{shot}', 'i');
  for (var c = 0; c < selected.length; c++) {
    // replace {shot} token with actual clip name
    var find = data.find.replace(rx, selected[c].name);
    var repl = data.replaceWith.replace(rx, selected[c].name);
    // replace find with replaceWith
    selected[c].name = selected[c].name.replace(find, repl);
  }
  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Replace current clip name with filename (without extension)
 * @return {string} result - return stringified JSON status
 */
renamer.renameClipRename = function () { // eslint-disable-line no-unused-vars
  var selected = app.project.activeSequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }

  var regexp = new RegExp('.[^/.]+$');
  for (var c = 0; c < selected.length; c++) {
    // suddenly causes syntax error on regexp? So using explicit contructor
    // regexp above.
    // selected[c].name = selected[c].projectItem.name.replace(/\.[^/.]+$/, '');
    selected[c].name = selected[c].projectItem.name.replace(regexp, '');
  }
  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Change clip name to lower or upper case
 * @param {int} case - 0 lower, 1 upper
 * @return {string} result - return stringified JSON status
 */
renamer.renameChangeCase = function (caseMode) { // eslint-disable-line no-unused-vars
  var selected = app.project.activeSequence.getSelection();
  if (selected.length < 1) {
    app.setSDKEventMessage('nothing selected', 'error');
    return false;
  }

  for (var c = 0; c < selected.length; c++) {
    if (caseMode === 0) {
      selected[c].name = selected[c].name.toLowerCase();
    } else {
      selected[c].name = selected[c].name.toUpperCase();
    }
  }
  return JSON.stringify({
    'status': 'renamed ' + selected.length + ' clips'
  });
};

/**
 * Set Pype metadata into sequence metadata using XMP.
 * This is `hackish` way to get over premiere lack of addressing unique clip on timeline,
 * so we cannot store data directly per clip.
 *
 * @param {Object} sequence - sequence object
 * @param {Object} data - to be serialized and saved
 */
renamer.setSequencePypeMetadata = function (sequence, data) { // eslint-disable-line no-unused-vars
  var kPProPrivateProjectMetadataURI = 'http://ns.adobe.com/premierePrivateProjectMetaData/1.0/';
  var metadata = sequence.projectItem.getProjectMetadata();
  var pypeData = 'pypeData';
  var xmp = new XMPMeta(metadata);
  var dataJSON = JSON.stringify(data);
  app.project.addPropertyToProjectMetadataSchema(pypeData, 'Pype Data', 2);

  xmp.setProperty(kPProPrivateProjectMetadataURI, pypeData, dataJSON);

  var str = xmp.serialize();
  sequence.projectItem.setProjectMetadata(str, [pypeData]);

  // test

  var newMetadata = sequence.projectItem.getProjectMetadata();
  var newXMP = new XMPMeta(newMetadata);
  var found = newXMP.doesPropertyExist(kPProPrivateProjectMetadataURI, pypeData);
  if (!found) {
    app.setSDKEventMessage('metadata not set', 'error');
  }
};

/**
 * Get Pype metadata from sequence using XMP.
 * @param {Object} sequence
 * @return {Object}
 */
renamer.getSequencePypeMetadata = function (sequence) { // eslint-disable-line no-unused-vars
  var kPProPrivateProjectMetadataURI = 'http://ns.adobe.com/premierePrivateProjectMetaData/1.0/';
  var metadata = sequence.projectItem.getProjectMetadata();
  var pypeData = 'pypeData';
  var pypeDataN = 'Pype Data';
  var xmp = new XMPMeta(metadata);
  app.project.addPropertyToProjectMetadataSchema(pypeData, pypeDataN, 2);
  var pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);
  if (pypeDataValue === undefined) {
    var metadata = {
      clips: {},
      tags: {}
    };
    renamer.setSequencePypeMetadata(sequence, metadata);
    pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);
    return renamer.getSequencePypeMetadata(sequence);
  } else {
    return JSON.parse(pypeDataValue);
  }
};

function keepExtension() {
  return app.setExtensionPersistent('com.pype.rename', 0);
}

/**
 * Dispatch event with new selection
 */
renamer.activeSequenceSelectionChanged = function () {
  var sel = app.project.activeSequence.getSelection();
  var selection = [];
  for (var i = 0; i < sel.length; i++) {
    if (sel[i].name !== 'anonymous') {
      selection.push({
        'name': sel[i].name,
        'path': sel[i].projectItem.getMediaPath()
      });
    }
  }

  var eoName;
  if (Folder.fs === 'Macintosh') {
    eoName = 'PlugPlugExternalObject';
  } else {
    eoName = 'PlugPlugExternalObject.dll';
  }

  var mylib = new ExternalObject('lib:' + eoName);

  var eventObj = new CSXSEvent();
  eventObj.type = 'activeSequenceSelectionChanged';
  eventObj.data = JSON.stringify(selection);
  eventObj.dispatch();
  // app.setSDKEventMessage('selection changed', 'info');
};

/**
 * Register active selection event dispatching
 */
renamer.registerActiveSelectionChanged = function () {
  var success = app.bind('onActiveSequenceSelectionChanged', renamer.activeSequenceSelectionChanged);
  return success;
};

keepExtension();

// load the XMPScript library
if (ExternalObject.AdobeXMPScript === undefined) {
  ExternalObject.AdobeXMPScript = new ExternalObject('lib:AdobeXMPScript');
}

// var seq = app.project.activeSequence;
// renamer.getSequencePypeMetadata(seq);

var messageText = 'this module is loaded> PypeRename.jsx';
$._PPP_.updateEventPanel(messageText);
$.writeln(messageText);
