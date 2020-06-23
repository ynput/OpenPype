/* global $, JSON, app, XMPMeta, ExternalObject, CSXSEvent, Folder */
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


var BatchRenamer = {

  getSelectedVideoTrackItems: function() {
    var seq = app.project.activeSequence;
    var selected = [];
    var videoTracks = seq.videoTracks;
    var numOfVideoTracks = videoTracks.numTracks;

    // VIDEO CLIPS IN SEQUENCES
    for (var l = 0; l < numOfVideoTracks; l++) {
      var videoTrack = seq.videoTracks[l];
      if (videoTrack.isTargeted()) {
        $.writeln(videoTrack.name);
        // var numOfClips = videoTrack.clips.numTracks;
        var numOfClips = videoTrack.clips.numItems;
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

  renameTargetedTextLayer: function (data) {
    $.bp(true);
    $.writeln(data);
    var selected = BatchRenamer.getSelectedVideoTrackItems();

    var seq = app.project.activeSequence;
    var metadata = $.pype.getSequencePypeMetadata(seq, true);

    var padding = 3;
    var newItems = {};
    var projectCode = data.projectCode
    var episode = data.ep;
    var episodeSuf = data.epSuffix;
    var shotPref = 'sh';

    for (var c = 0; c < selected.length; c++) {
      // fill in hierarchy if set
      var parents = [];
      var hierarchy = [];
      var name = selected[c].name;
      var sequenceName = name.slice(0, 5);
      var shotNum = Number(name.slice((name.length - 3), name.length));

      var newName = projectCode + episode + sequenceName + shotPref + (shotNum).pad(padding);
      $.pype.log(newName);
      selected[c].clip.name = newName;

      parents.push({
        'entityType': 'Episode',
        'entityName': episode + '_' + episodeSuf
      });
      hierarchy.push(episode + '_' + episodeSuf);

      parents.push({
        'entityType': 'Sequence',
        'entityName': episode + sequenceName
      });
      hierarchy.push(episode + sequenceName);

      newItems[newName] = {
        'parents': parents,
        'hierarchy': hierarchy.join('/')
      };
    }

    metadata.clips = newItems;
    $.pype.setSequencePypeMetadata(seq, metadata);
    return JSON.stringify(metadata);
  }
}
