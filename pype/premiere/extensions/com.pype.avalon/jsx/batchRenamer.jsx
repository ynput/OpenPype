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

// variable br is defined in pypeAvalon.jsx
var br = {
  getSelectedVideoTrackItems: function () {
    var seq = app.project.activeSequence;
    var selected = [];
    var videoTracks = seq.videoTracks;
    var numOfVideoTracks = videoTracks.numTracks;

    // VIDEO CLIPS IN SEQUENCES
    for (var l = 0; l < numOfVideoTracks; l++) {
      var videoTrack = seq.videoTracks[l];
      if (videoTrack.isTargeted()) {
        $.writeln(videoTrack.name);
        var numOfClips = videoTrack.clips.numTracks;
        for (var m = 0; m < numOfClips; m++) {
          var clip = videoTrack.clips[m];

          selected.push({
            name: clip.name,
            clip: clip,
            sequence: seq,
            videoTrack: videoTrack
          });
        }
      }
    }
    var names = [];
    var items = {};
    var sorted = [];
    for (var c = 0; c < selected.length; c++) {
      items[selected[c].name] = selected[c];
      names.push(selected[c].name);
    }
    names.sort();

    for (var cl = 0; cl < names.length; cl++) {
      sorted.push(items[names[cl]]);
    }
    return sorted;
  },

  /**
   * Set Pype metadata into sequence metadata using XMP.
   * This is `hackish` way to get over premiere lack of addressing unique clip on timeline,
   * so we cannot store data directly per clip.
   *
   * @param {Object} sequence - sequence object
   * @param {Object} data - to be serialized and saved
   */
  setSequencePypeMetadata: function (sequence, data) { // eslint-disable-line no-unused-vars
    var kPProPrivateProjectMetadataURI = 'http://ns.adobe.com/premierePrivateProjectMetaData/1.0/';
    var metadata = sequence.projectItem.getProjectMetadata();
    var pypeData = 'pypeData';
    var xmp = new XMPMeta(metadata);

    app.project.addPropertyToProjectMetadataSchema(pypeData, 'Pype Data', 2);

    xmp.setProperty(kPProPrivateProjectMetadataURI, pypeData, JSON.stringify(data));

    var str = xmp.serialize();
    sequence.projectItem.setProjectMetadata(str, [pypeData]);

    // test
    var newMetadata = sequence.projectItem.getProjectMetadata();
    var newXMP = new XMPMeta(newMetadata);
    var found = newXMP.doesPropertyExist(kPProPrivateProjectMetadataURI, pypeData);
    if (!found) {
      app.setSDKEventMessage('metadata not set', 'error');
    }
  },

  /**
   * Get Pype metadata from sequence using XMP.
   * @param {Object} sequence
   * @return {Object}
   */
  getSequencePypeMetadata: function (sequence) { // eslint-disable-line no-unused-vars
    var kPProPrivateProjectMetadataURI = 'http://ns.adobe.com/premierePrivateProjectMetaData/1.0/';
    var metadata = sequence.projectItem.getProjectMetadata();
    var pypeData = 'pypeData';
    var pypeDataN = 'Pype Data';
    var xmp = new XMPMeta(metadata);
    app.project.addPropertyToProjectMetadataSchema(pypeData, pypeDataN, 2);
    var pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);
    $.writeln('pypeDataValue');
    $.writeln(pypeDataValue);
    if (pypeDataValue === undefined) {
      var pyMeta = {
        clips: {},
        tags: {}
      };
      br.setSequencePypeMetadata(sequence, pyMeta);
      pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);
      return br.getSequencePypeMetadata(sequence);
    } else {
      return JSON.parse(pypeDataValue);
    }
  },
  renameTargetedTextLayer: function (data) {
    $.writeln(data);
    var selected = br.getSelectedVideoTrackItems();

    var seq = app.project.activeSequence;
    var metadata = br.getSequencePypeMetadata(seq);

    var startCount = 10;
    var stepCount = 10;
    var padding = 3;
    var newItems = {};
    var episode = data.ep;
    var episodeSuf = data.epSuffix;
    var shotPref = 'sh';
    var count = 0;
    var seqCheck = '';

    for (var c = 0; c < selected.length; c++) {
      // fill in hierarchy if set
      var parents = [];
      var hierarchy = [];
      var name = selected[c].name;
      var sequenceName = name.slice(0, 5);
      var shotNum = Number(name.slice((name.length - 3), name.length));

      // if (sequenceName !== seqCheck) {
      //   seqCheck = sequenceName;
      //   count = 0;
      // };
      //
      // var seqCount = (count * stepCount) + startCount;
      // count += 1;

      var newName = episode + sequenceName + shotPref + (shotNum).pad(padding);
      $.writeln(newName);
      selected[c].clip.name = newName;

      parents.push({
        'entityType': 'episode',
        'entityName': episode + '_' + episodeSuf
      });
      hierarchy.push(episode + '_' + episodeSuf);

      parents.push({
        'entityType': 'sequence',
        'entityName': episode + sequenceName
      });
      hierarchy.push(episode + sequenceName);

      newItems[newName] = {
        'parents': parents,
        'hierarchy': hierarchy.join('/')
      };
    }

    metadata.clips = newItems;
    br.setSequencePypeMetadata(seq, metadata);
    return JSON.stringify(metadata);
  }
};

Number.prototype.pad = function (size) {
  var s = String(this);
  while (s.length < (size || 2)) {
    s = "0" + s;
  }
  return s;
}
