/* global $, CSInterface, process */
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

var csi = new CSInterface();

function displayResults(data) {
  var con = $('#output');
  con.html(data);
}

// Bind renamer controls
$('#renamer-modes a').click(function () {
  var mode = $(this).data('mode');
  $('#renamerDropdown').dropdown('toggle');
  $('#renamerDropdown').html($(this).html());
  $('#renamer-ui .pane').css('display', 'none');
  $('#rpane-' + mode).css('display', 'block');
  $('#renamerDropdown').data('mode', mode);
  return false;
});

$('#renamer-caseSelect a').click(function () {
  $('#renamer-caseSelect').data('mode', $(this).data('mode'));
  return false;
});

$('#btn-rename').click(function () {
  var mode = $('#renamerDropdown').data('mode');
  if (!mode) {
    mode = 'seqRename';
  }
  var data = '';
  switch (mode) {
  case 'seqRenameHierarchy':
    data = {
      'folder': $('#rpane-' + mode + ' input[name=renamer-folder]').val(),
      'episode': $('#rpane-' + mode + ' input[name=renamer-episode]').val(),
      'sequence': $('#rpane-' + mode + ' input[name=renamer-sequence]').val(),
      'pattern': $('#rpane-' + mode + ' input[name=renamer-pattern]').val(),
      'start': $('#rpane-' + mode + ' input[name=renamer-start]').val(),
      'increment': $('#rpane-' + mode + ' input[name=renamer-inc]').val()
    };
    csi.evalScript('renamer.renameSeqHierarchy(' + JSON.stringify(data) + ');', function (result) {
      displayResults(result);
    });
    break;
  case 'seqRename':
    data = {
      'pattern': $('#rpane-' + mode + ' input[name=renamer-pattern]').val(),
      'start': $('#rpane-' + mode + ' input[name=renamer-start]').val(),
      'increment': $('#rpane-' + mode + ' input[name=renamer-inc]').val()
    };
    csi.evalScript('renamer.renameSeq(' + JSON.stringify(data) + ');', function (result) {
      displayResults(result);
    });
    break;

  case 'simpleRename':
    data = $('#rpane-' + mode + ' input[name=renamer-newName]').val();
    displayResults(data);
    csi.evalScript('renamer.renameSimple("' + data + '");', function (result) {
      displayResults(result);
    });
    break;

  case 'findAndReplace':
    data = {
      'find': $('#rpane-' + mode + ' input[name=renamer-find]').val(),
      'replaceWith': $('#rpane-' + mode + ' input[name=renamer-replace]').val()
    };
    csi.evalScript('renamer.renameFindReplace(' + JSON.stringify(data) + ');', function (result) {
      displayResults(result);
    });
    break;

  case 'matchSequence':
    // not implemented
    break;

  case 'clipRename':
    csi.evalScript('renamer.renameClipRename();', function (result) {
      displayResults(result);
    });
    break;

  case 'changeCase':
    var stringCase = 0;
    var caseMode = $('#renamer-caseSelect').data('mode');
    if (caseMode === 'uppercase') {
      stringCase = 1;
    }
    $('#renamer-case').val(caseMode);
    csi.evalScript('renamer.renameChangeCase("' + stringCase + '");', function (result) {
      displayResults(result);
    });
    break;

  default:
  }
});

// add selection changed addEventListener
csi.evalScript('renamer.registerActiveSelectionChanged()');
csi.addEventListener('activeSequenceSelectionChanged', function (event) {
  var mode = $('#renamerDropdown').data('mode');
  if (mode !== 'seqRenameHierarchy') {
    return;
  }
  var path = event.data[0].path.split('\\');
  // test if path has more then 4 elements - folder/episode/sequence/filename
  if (path.length > 4) {
    var folder = path[path.length - 4];
    var episode = path[path.length - 3];
    var sequence = path[path.length - 2];

    if ($('#renamer-parse-path').prop('checked')) {
      $('#rpane-' + mode + ' input[name=renamer-folder]').val(folder);
      $('#rpane-' + mode + ' input[name=renamer-episode]').val(episode);
      $('#rpane-' + mode + ' input[name=renamer-sequence]').val(sequence);
    }
  }
});
