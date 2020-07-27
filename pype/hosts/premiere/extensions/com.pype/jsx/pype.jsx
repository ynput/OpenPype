/* global app, qe, alert, File, $, JSON, ProjectItemType, CSXSEvent, XMPMeta, parseFloat */
/*
              .____ _ ___ .____.______
--- - - --   /  .  \//  //  .  \  ___/ --- ---- - -
 - --- ---  /  ____/ __//  ____/ /_/  --- - -- ---
           /__/ /___/  /__/ /______/
          ._- -=[ PyPe 4 3veR ]=- -_.
*/

if (ExternalObject.AdobeXMPScript === undefined) {
  ExternalObject.AdobeXMPScript = new ExternalObject('lib:AdobeXMPScript');
}

// this is needed for CSXSEvent to work
if (ExternalObject.PlugPlugExternalObject === undefined) {
  ExternalObject.PlugPlugExternalObject = new ExternalObject( "lib:PlugPlugExternalObject");
}
// variable pype is defined in pypeAvalon.jsx
$.pype = {
  presets: null,

  expectedJobs: [],

  setEnvs: function (env) {
    for (var key in env) {
      $.setenv(key, env[key]);
    }
  },

  importClips: function (obj) {
    app.project.importFiles(obj.paths);
    return JSON.stringify(obj);
  },

  convertPathString: function (path) {
    return path.replace(new RegExp('\\\\', 'g'), '/').replace(new RegExp('//\\?/', 'g'), '').replace(new RegExp('/', 'g'), '\\').replace('UNC', '\\');
  },

  getProjectFileData: function () {
    app.enableQE();
    var projPath = new File(app.project.path);
    var obj = {
      projectfile: app.project.name,
      projectpath: $.pype.convertPathString(projPath.fsName),
      projectdir: $.pype.convertPathString(app.project.path).split('\\').slice(0, -1).join('\\')
    };
    return JSON.stringify(obj);
  },

  getSequences: function () {
    var project = app.project;
    var sequences = [];
    for (var i = 0; i < project.sequences.numSequences; i++) {
      var seq = project.sequences[i];
      seq.clipNames = [];
      sequences[i] = seq;
      $.pype.log('sequences[i]  id: ' + project.sequences[i].sequenceID);
    }

    var obj = {
      sequences: sequences
    };
    return JSON.stringify(obj);
  },

  getSequenceItems: function (seqs) {
    var sequences = seqs;
    // $.pype.log('getSequenceItems sequences obj from app: ' + sequences);

    var rootFolder = app.project.rootItem;
    var binCounter = -1;
    var rootSeqCounter = -1; // count sequences in root folder

    // walk through root folder of project to differentiate between bins, sequences and clips
    for (var i = 0; i < rootFolder.children.numItems; i++) {
      // $.pype.log('\nroot item at ' + i + " is " +  rootFolder.children[i].name + " of type " + rootFolder.children[i].type);
      var item = rootFolder.children[i];
      // $.pype.log('item has video tracks? ' + item.videoTracks);
      if (item.type === 2) { // bin
        binCounter++;
        walkBins(item, 'root', binCounter);
      } else if (item.type === 1 && !item.getMediaPath()) { // sequence  OR other type of object
        // $.pype.log('\nObject of type 1 in root: ' +  typeof item + '   ' + item.name);
        if (objectIsSequence(item)) { // objects of type can also be other objects such as titles, so check if it really is a sequence
          // $.pype.log('\nSequence in root: ' +  item.name );
          rootSeqCounter++;
          var seq = app.project.sequences[rootSeqCounter];
          //  $.pype.log('\nSequence in root, guid: ' +  seq );
          for (var property in seq) {
            if (Object.prototype.hasOwnProperty.call(seq, property)) {
              $.pype.log('\nSequence in root: ' + seq);
              $.pype.log('qe sequence prop: ' + property);
            }
          }
          getClipNames(seq, sequences);
        }
      }
    }

    function objectIsSequence() {
      var isSequence = false;

      for (var s = 0; s < app.project.sequences.numSequences; s++) {
        if (item.name === app.project.sequences[s].name) {
          isSequence = true;
        }
      }

      return isSequence;
    }

    // walk through bins recursively
    function walkBins (item, source, rootBinCounter) {
      var bin;
      if (source === 'root') { // bin in root folder
        bin = source.children[rootBinCounter];
      } else { // bin in other bin
        bin = item;

        for (var i = 0; i < bin.children.numItems; i++) { // if bin contains bin(s) walk through them
          walkBins(bin.children[i]);
        }
        // $.pype.log('Bin ' + bin.name + ' has ' + bin.numSequences + ' sequences ' );
        // var seqCounter = -1;
        for (var j = 0; j < bin.numSequences; j++) {
          // if(objectIsSequence(item)) {//objects of type can also be other objects such as titles, so check if it really is a sequence?
          // not needed because getSequenceAt apparently only looks at sequences already?
          var seq = bin.getSequenceAt(j);
          // $.pype.log('\nSequence in bin, guid: ' +  seq.guid );
          getClipNames(seq, sequences);
        }
      }
    }

    // walk through sequences and video & audiotracks to find clip names in sequences
    function getClipNames (seq, sequences) {
      for (var k = 0; k < sequences.length; k++) {
        //  $.pype.log('getClipNames seq.guid ' + seq.guid  );
        // $.pype.log(' getClipNames sequences[k].id ' +  sequences[k].sequenceID  );
        if (seq.guid === sequences[k].sequenceID) {
          //  $.pype.log('Sequence ' + seq.name + ' has ' + app.project.sequences[k].videoTracks.numTracks +' video tracks'  );
          //  $.pype.log('Sequence ' + seq.name + ' has ' + app.project.sequences[k].audioTracks.numTracks +' audio tracks'  );

          // VIDEO CLIPS IN SEQUENCES
          for (var l = 0; l < sequences[k].videoTracks.numTracks; l++) {
            var videoTrack = seq.getVideoTrackAt(l);
            //  $.pype.log(seq.name + ' has video track '+ videoTrack.name + ' at index ' + l);
            var clipCounter = 0;
            var numOfClips = app.project.sequences[k].videoTracks[l].clips.numTracks;
            //  $.pype.log('\n' + bin.name + ' ' + seq.name + ' ' + videoTrack.name + ' has  ' + numOfClips + ' clips');
            for (var m = 0; m < numOfClips; m++) {
              // var clip = app.project.sequences[k].videoTracks[l].clips[m];
              // $.pype.log('clips in video tracks:   ' + m + ' - ' + clip); TrackItem, doesn't have name property
              // if a clip was deleted and another one added, the index of the new one is one  or more higher
              while (clipCounter < numOfClips) { // undefined because of old clips
                if (videoTrack.getItemAt(m).name) {
                  clipCounter++;
                  // $.pype.log('getClipNames ' + seq.name + ' ' + videoTrack.name + ' has  ' + videoTrack.getItemAt(m).name); Object

                  for (var s = 0; s < sequences.length; s++) {
                    if (seq.guid === sequences[s].sequenceID) {
                      sequences[s].clipNames.push(videoTrack.getItemAt(m).name);
                    }
                  }
                }
                m++;
              }
            }
          }
          // $.pype.log('jsx after video loop clipsInSequences:' + clipsInSequences);

          // AUDIO CLIPS IN SEQUENCES
          for (var l = 0; l < sequences[k].audioTracks.numTracks; l++) {
            var audioTrack = seq.getAudioTrackAt(l);
            // $.pype.log(bin.name + ' ' + seq.name + ' has audio track '+ audioTrack.name + ' at index ' + l);
            // $.pype.log('\n' + bin.name + ' ' + seq.name + ' ' + audioTrack.name + ' has  ' + app.project.sequences[k].audioTracks[l].clips.numTracks + ' clips');
            clipCounter = 0;
            numOfClips = app.project.sequences[k].audioTracks[l].clips.numTracks;

            for (var m = 0; m < numOfClips; m++) {
              var clip = app.project.sequences[k].audioTracks[l].clips[m];
              $.pype.log('clips in audio tracks:   ' + m + ' - ' + clip);
              // if a clip was deleted and another one added, the index of the new one is one  or more higher
              while (clipCounter < numOfClips) { // undefined because of old clips
                if (audioTrack.getItemAt(m).name) {
                  clipCounter++;
                  // $.pype.log(seq.name + ' ' + audioTrack.name + ' has  ' + audioTrack.getItemAt(m).name);

                  for (var s = 0; s < sequences.length; s++) {
                    if (seq.guid === sequences[s].sequenceID) {
                      sequences[s].clipNames.push(audioTrack.getItemAt(m).name);
                    }
                  }
                }
                m++;
              }
            }
          }
        } // end if
      } // end for
    } // end getClipNames

    $.pype.log('sequences returned:' + sequences);
    // return result to ReplaceService.js
    var obj = {
      data: sequences
    };
    // $.pype.log('jsx getClipNames obj:' + obj);
    return JSON.stringify(obj);
  },

  getProjectItems: function () {
    var projectItems = [];

    var rootFolder = app.project.rootItem;
    // walk through root folder of project to differentiate between bins, sequences and clips
    for (var i = 0; i < rootFolder.children.numItems; i++) {
      // $.pype.log('\nroot item at ' + i + " is of type " + rootFolder.children[i].type);
      var item = rootFolder.children[i];

      if (item.type === 2) { // bin
        //  $.pype.log('\n' );
        $.pype.getProjectItems.walkBins(item);
      } else if (item.type === 1 && item.getMediaPath()) { // clip in root
        //  $.pype.log('Root folder has '  + item + ' ' + item.name);
        projectItems.push(item);
      }
    }

    // walk through bins recursively
    function walkBins (bin) { // eslint-disable-line no-unused-vars

      // $.writeln('bin.name + ' has ' + bin.children.numItems);
      for (var i = 0; i < bin.children.numItems; i++) {
        var object = bin.children[i];
        // $.pype.log(bin.name + ' has ' + object + ' ' + object.name  + ' of type ' +  object.type + ' and has mediapath ' + object.getMediaPath() );
        if (object.type === 2) { // bin
          // $.pype.log(object.name  + ' has ' +  object.children.numItems  );
          for (var j = 0; j < object.children.numItems; j++) {
            var obj = object.children[j];
            if (obj.type === 1 && obj.getMediaPath()) { // clip  in sub bin
              // $.pype.log(object.name  + ' has ' + obj + ' ' +  obj.name  );
              projectItems.push(obj);
            } else if (obj.type === 2) { // bin
              walkBins(obj);
            }
          }
        } else if (object.type === 1 && object.getMediaPath()) { // clip in bin in root
          // $.pype.log(bin.name + ' has ' + object + ' ' + object.name );
          projectItems.push(object);
        }
      }
    }
    $.pype.log('\nprojectItems:' + projectItems.length + ' ' + projectItems);
    return projectItems;
  },

  getImageSize: function () {
    return {h: app.project.activeSequence.frameSizeHorizontal, v: app.project.activeSequence.frameSizeVertical};
  },

  getInOutOfAll: function () {
    var seq = app.project.activeSequence;
    var points = [];
    var output = [];

    // VIDEO CLIPS IN SEQUENCES
    for (var l = 0; l < seq.videoTracks.numTracks; l++) {
      var numOfClips = seq.videoTracks[l].clips.numTracks;
      // $.writeln('\n' + seq.name + ' ' + seq.videoTracks[l].name + ' has  ' + numOfClips + ' clips');
      for (var m = 0; m < numOfClips; m++) {
        var clip = seq.videoTracks[l].clips[m];
        points.push(Math.ceil(clip.start.seconds * 1000) / 1000);
        points.push(Math.ceil(clip.end.seconds * 1000) / 1000);
      }
    }

    points.sort(function (a, b) {
      return a - b;
    });

    output.push(points[0]);
    output.push(points[points.length - 1]);

    return output;
  },

  getSelectedItems: function () {
    var seq = app.project.activeSequence;
    var selected = [];

    // VIDEO CLIPS IN SEQUENCES
    for (var l = 0; l < seq.videoTracks.numTracks; l++) {
      var numOfClips = seq.videoTracks[l].clips.numTracks;
      // $.writeln('\n' + seq.name + ' ' + seq.videoTracks[l].name + ' has  ' + numOfClips + ' clips');
      for (var m = 0; m < numOfClips; m++) {
        var clip = seq.videoTracks[l].clips[m];
        if (clip.isSelected()) {
          selected.push({clip: clip, sequence: seq, videoTrack: seq.videoTracks[l], trackOrder: l});
        }
      }
    }
    return selected;
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
   * @param {Bool} firstTimeRun
   * @return {Object}
   */
  getSequencePypeMetadata: function (sequence, firstTimeRun) { // eslint-disable-line no-unused-vars
    var kPProPrivateProjectMetadataURI = 'http://ns.adobe.com/premierePrivateProjectMetaData/1.0/';
    var metadata = sequence.projectItem.getProjectMetadata();
    var pypeData = 'pypeData';
    var pypeDataN = 'Pype Data';
    var xmp = new XMPMeta(metadata);
    var successfullyAdded = app.project.addPropertyToProjectMetadataSchema(pypeData, pypeDataN, 2);
    var pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);

    $.pype.log('__ pypeDataValue: ' + pypeDataValue);
    $.pype.log('__ firstTimeRun: ' + firstTimeRun);
    $.pype.log('__ successfullyAdded: ' + successfullyAdded);
    if ((pypeDataValue === undefined) && (firstTimeRun !== undefined)) {
      var pyMeta = {
        clips: {},
        tags: {}
      };
      $.pype.log('__ pyMeta: ' + pyMeta);
      $.pype.setSequencePypeMetadata(sequence, pyMeta);
      pypeDataValue = xmp.getProperty(kPProPrivateProjectMetadataURI, pypeData);
      return $.pype.getSequencePypeMetadata(sequence);
    } else {
      if (successfullyAdded === true) {
        $.pype.log('__ adding {}');
        $.pype.setSequencePypeMetadata(sequence, {});
      }
      if ((pypeDataValue === undefined) || (!Object.prototype.hasOwnProperty.call(JSON.parse(pypeDataValue), 'clips'))) {
        $.pype.log('__ getSequencePypeMetadata: returning null');
        return null;
      } else {
        $.pype.log('__ getSequencePypeMetadata: returning data');
        return JSON.parse(pypeDataValue);
      }
    }
  },
  /**
   * Sets project presets into module's variable for other functions to use.
   * @param inPresets {object} - dictionary object comming from js
   * @return {bool}: true is success, false if not
   */
  setProjectPreset: function (inPresets) {
    // validating the incoming data are having `plugins` key
    if (Object.prototype.hasOwnProperty.call(inPresets, 'plugins')) {
      $.pype.presets = inPresets;
      return true;
    } else {
      $.pype.alert_message('Presets are missing `plugins` key!');
      return false;
    }
  },
  /**
   * Gets project presets from module's variable for other functions to use.
   * @return {Object}: JSON string with presets dictionary or false if unsuccess
   */
  getProjectPreset: function () {
    if ($.pype.presets === null) {
      $.pype.alert_message('Presets needs to be set before they could be required!');
      return false;
    } else {
      return JSON.stringify($.pype.presets);
    }
  },
  /**
   * Return instance representation of clip
   * @param clip {object} - index of clip on videoTrack
   * @param sequence {object Sequence} - Sequence clip is in
   * @param videoTrack {object VideoTrack} - VideoTrack clip is in
   * @return {Object}
   */
  getClipAsInstance: function (clip, sequence, videoTrack, pypeData) {
    var presets = JSON.parse($.pype.getProjectPreset());
    if ((clip.projectItem.type !== ProjectItemType.CLIP) && (clip.mediaType !== 'Video')) {
      return false;
    }
    var pdClips = pypeData.clips;
    var hierarchy;
    var parents;
    $.pype.log('>> getClipAsInstance:clip.name ' + clip.name);
    if (pdClips[clip.name]) {
      parents = pdClips[clip.name].parents;
      hierarchy = pdClips[clip.name].hierarchy;
    }

    if (hierarchy === null) {
      $.pype.alert_message('First you need to rename clip sequencially with hierarchy!\nUse `Pype Rename` extension', 'No hierarchy data available at clip ' + clip.name + '!', 'error');
      return;
    }

    var interpretation = clip.projectItem.getFootageInterpretation();
    $.pype.log('>> getClipAsInstance:interpretation ' + interpretation);
    var instance = {};
    instance.publish = true;
    instance.family = 'clip';
    instance.name = clip.name;
    instance.hierarchy = hierarchy;
    instance.parents = parents;
    instance.subsetToRepresentations = presets.premiere.rules_tasks.subsetToRepresentations;
    // metadata
    var metadata = {};
    // TODO: how to get colorspace clip info
    metadata.colorspace = 'bt.709';
    var settings = sequence.getSettings();
    var sequenceSize = $.pype.getImageSize();
    metadata['ppro.videoTrack.name'] = videoTrack.name;
    metadata['ppro.sequence.name'] = sequence.name;
    metadata['ppro.source.fps'] = parseFloat(1 / interpretation.frameRate).toFixed(4);
    metadata['ppro.timeline.fps'] = parseFloat(1 / settings.videoFrameRate.seconds).toFixed(4);
    metadata['ppro.source.path'] = $.pype.convertPathString(clip.projectItem.getMediaPath());
    metadata['ppro.format.width'] = sequenceSize.h;
    metadata['ppro.format.height'] = sequenceSize.v;
    metadata['ppro.format.pixelaspect'] = parseFloat(interpretation.pixelAspectRatio).toFixed(4);
    metadata['ppro.source.start'] = clip.inPoint.seconds;
    metadata['ppro.source.end'] = clip.outPoint.seconds;
    metadata['ppro.source.duration'] = clip.duration.seconds;
    metadata['ppro.clip.start'] = clip.start.seconds;
    metadata['ppro.clip.end'] = clip.end.seconds;

    $.pype.log('>> getClipAsInstance:reprs ' + JSON.stringify(instance.subsetToRepresentations));

    // set metadata to instance
    instance.metadata = metadata;
    return instance;
  },

  getSelectedClipsAsInstances: function () {
    // get project script version and add it into clip instance data
    var version = $.pype.getWorkFileVersion();
    $.pype.log('__ getSelectedClipsAsInstances:version: ' + version);

    var pypeData = $.pype.getSequencePypeMetadata(app.project.activeSequence);
    $.pype.log(
      '__ getSelectedClipsAsInstances:typeof(pypeData): ' + typeof (pypeData));
    $.pype.log('__ getSelectedClipsAsInstances:pypeData: ' + JSON.stringify(pypeData));

    // check if the pype data are available and if not alert the user
    // we need to have avalable metadata for correct hierarchy
    if (pypeData === null) {
      $.pype.alert_message('First you need to rename clips sequencially with hierarchy!\nUse `Pype Rename` extension, or use the above rename text layer section of `Pype` panel.\n\n>> No hierarchy data available! <<');
      return null;
    }

    // instances
    var instances = [];
    var selected = $.pype.getSelectedItems();
    for (var s = 0; s < selected.length; s++) {
      $.pype.log('__ getSelectedClipsAsInstances:selected[s].clip: ' + selected[s].clip);
      var instance = $.pype.getClipAsInstance(selected[s].clip, selected[s].sequence, selected[s].videoTrack, pypeData);
      if (instance !== false) {
        instance.version = version;
        instances.push(instance);
      }
    }

    // adding project file instance
    var projectFileData = JSON.parse($.pype.getProjectFileData());
    var projectFileInstance = projectFileData;
    projectFileInstance.subsetToRepresentations = {
      workfile: {
        representation: 'prproj'
      }
    };
    projectFileInstance.name = projectFileData.projectfile.split('.')[0];
    projectFileInstance.publish = true;
    projectFileInstance.family = 'workfile';
    projectFileInstance.version = version;
    instances.push(projectFileInstance);

    return instances;
  },
  /**
   * Return request json data object with instances for pyblish
   * @param stagingDir {string} - path to temp directory
   * @return {json string}
   */
  getPyblishRequest: function (stagingDir, audioOnly) {
    try {
      var sequence = app.project.activeSequence;
      var settings = sequence.getSettings();
      $.pype.log('__ stagingDir: ' + stagingDir);
      $.pype.log('__ audioOnly: ' + audioOnly);
      $.pype.log('__ sequence: ' + sequence);
      $.pype.log('__ settings: ' + settings);
      var request = {
        stagingDir: stagingDir,
        currentFile: $.pype.convertPathString(app.project.path),
        framerate: (1 / settings.videoFrameRate.seconds),
        host: $.getenv('AVALON_APP'),
        hostVersion: $.getenv('AVALON_APP_NAME').split('_')[1],
        cwd: $.pype.convertPathString(app.project.path).split('\\').slice(0, -1).join('\\')
      };
      var sendInstances = [];
      var instances = $.pype.getSelectedClipsAsInstances();

      // make sure the process will end if no instancess are returned
      if (instances === null) {
        return null;
      }

      // make only audio representations
      if (audioOnly === 'true') {
        $.pype.log('? looping if audio True');
        for (var i = 0; i < instances.length; i++) {
          var subsetToRepresentations = instances[i].subsetToRepresentations;
          var newRepr = {};
          for (var key in subsetToRepresentations) {
            var _include = ['audio', 'thumbnail', 'workfile'];
            if (include(_include, key)) {
              newRepr[key] = subsetToRepresentations[key];
            }
          }
          instances[i].subsetToRepresentations = newRepr;
          sendInstances.push(instances[i]);
        }
      } else {
        sendInstances = instances;
      }
      request.instances = sendInstances;
      return JSON.stringify(request);
    } catch (error) {
      $.pype.log('error: ' + error);
      return error;
    }
  },

  // convertSecToTimecode: function (timeSec, fps) {
  //   var ceiled = Math.round(timeSec * 100) / 100;
  //   var parts = ('' + ceiled).split('.');
  //   var dec = Number(parts[1]);
  //   var main = Number(parts[0]);
  //   var sec;
  //   var frames = (Number(('' + (
  //   (dec * fps) / 100)).split('.')[0])).pad(2);
  //   if (main > 59) {
  //     sec = (Math.round(((Number(('' + (
  //     Math.round((main / 60) * 100) / 100).toFixed(2)).split('.')[1]) / 100) * 60))).pad(2);
  //     if (sec === 'NaN') {
  //       sec = '00';
  //     };
  //   } else {
  //     sec = main;
  //   };
  //   var min = (Number(('' + (
  //   main / 60)).split('.')[0])).pad(2);
  //   var hov = (Number(('' + (
  //   main / 3600)).split('.')[0])).pad(2);
  //
  //   return hov + ':' + min + ':' + sec + ':' + frames;
  // },

  // exportThumbnail: function (name, family, version, outputPath, time, fps) {
  //   app.enableQE();
  //   var activeSequence = qe.project.getActiveSequence(); // note: make sure a sequence is active in PPro UI
  //   var file = name + '_' + family + '_v' + version + '.jpg';
  //   var fullPathToFile = outputPath + $._PPP_.getSep() + file;
  //   var expJPEG = activeSequence.exportFrameJPEG($.pype.convertSecToTimecode(time, fps), $.pype.convertPathString(fullPathToFile).split('/').join($._PPP_.getSep()));
  //   return file;
  // },

  encodeRepresentation: function (request) {
    $.pype.log('__ request: ' + JSON.stringify(request));
    var sequence = app.project.activeSequence
    // get original timeline in out points
    var defaultTimelinePointValue = -400000
    var origInPoint = Math.ceil(sequence.getInPoint() * 100) / 100;
    var origOutPoint = Math.ceil(sequence.getOutPoint() * 100) / 100;
    if (origInPoint === defaultTimelinePointValue) {
      var allInOut = $.pype.getInOutOfAll();
      origInPoint = allInOut[0];
      origOutPoint = allInOut[1];
    };
    $.pype.log('__ origInPoint: ' + origInPoint);
    $.pype.log('__ origOutPoint: ' + origOutPoint);

    // instances
    var instances = request.instances;
    $.pype.log('__ instances: ' + JSON.stringify(instances));

    for (var i = 0; i < instances.length; i++) {
      // generate data for instance.subset representations
      // loop representations of instance.subset and sent job to encoder
      var subsetToRepresentations = instances[i].subsetToRepresentations;
      $.pype.log('__ subsetToRepresentations: ' + subsetToRepresentations);
      instances[i].files = [];
      for (var key in subsetToRepresentations) {
        $.pype.log('representation: ' + key);
        // send render jobs to encoder
        var exclude = ['workfile', 'thumbnail'];
        if (!include(exclude, key)) {
          instances[i].files.push(
            $.pype.render(
              request.stagingDir,
              key,
              subsetToRepresentations[key],
              instances[i].name,
              instances[i].version,
              instances[i].metadata['ppro.clip.start'],
              instances[i].metadata['ppro.clip.end']
            ));
        } else if (key === 'thumbnail') {
          // // create time to be in middle of clip
          // var thumbStartTime = (instances[i].metadata['ppro.clip.start'] + ((instances[i].metadata['ppro.clip.end'] - instances[i].metadata['ppro.clip.start']) / 2));
          var thumbStartTime = instances[i].metadata['ppro.clip.start'] * 100;

          var thumbEndTime = Number(
            thumbStartTime + ((1 / instances[i].metadata['ppro.timeline.fps']) * 100));

          $.pype.log('_ thumbStartTime: ' + thumbStartTime);
          $.pype.log('_ thumbEndTime: ' + thumbEndTime);

          // add instance of thumbnail
          instances[i].files.push(
            $.pype.render(
              request.stagingDir,
              key,
              subsetToRepresentations[key],
              instances[i].name,
              instances[i].version,
              Number(parseFloat(thumbStartTime / 100).toFixed(2)),
              Number(parseFloat(thumbEndTime / 100).toFixed(2))
            )
          );
        } else if (key === 'workfile') {
          instances[i].files.push(instances[i].projectfile);
        };
      }
    }
    app.encoder.startBatch();
    // set back original in/out point on timeline
    app.project.activeSequence.setInPoint(origInPoint);
    app.project.activeSequence.setOutPoint(origOutPoint);
    return JSON.stringify(request);
  },

  onEncoderJobComplete: function (jobID, outputFilePath) {
    // remove job from expected jobs list
    const index = $.pype.expectedJobs.indexOf(jobID);
    if (index > -1) {
      $.pype.expectedJobs.splice(index, 1);
    }

    // test if expected job list is empty. If so, emit event for JS
    if ($.pype.expectedJobs.length == 0) {
      $.pype.log("encoding jobs finished.");
      var eventObj = new CSXSEvent();
      eventObj.type = 'pype.EncoderJobsComplete';
      eventObj.data = {"jobID": jobID, "outputFilePath": outputFilePath};
      eventObj.dispatch();
    }
  },

  render: function (outputPath, family, representation, clipName, version, inPoint, outPoint) {
    $.pype.log("_ inPoint: " + inPoint)
    $.pype.log("_ outPoint: " + outPoint)
    var outputPresetPath = $.getenv('EXTENSION_PATH').split('/').concat([
      'encoding',
      (representation.preset + '.epr')
    ]).join($._PPP_.getSep());


    var activeSequence = app.project.activeSequence;
    $.pype.log('launching encoder ... ' + family + ' ' + clipName);
    if (activeSequence) {
      app.encoder.launchEncoder(); // This can take a while; let's get the ball rolling.

      var projPath = new File(app.project.path);

      if ((outputPath) && projPath.exists) {
        var outPreset = new File(outputPresetPath);
        if (outPreset.exists === true) {
          var outputFormatExtension = activeSequence.getExportFileExtension(outPreset.fsName);
          if (outputFormatExtension) {
            app.project.activeSequence.setInPoint(inPoint);
            app.project.activeSequence.setOutPoint(outPoint);
            var file = clipName + '_' + family + '_v' + version + '.' + outputFormatExtension;
            var fullPathToFile = outputPath + $._PPP_.getSep() + file;

            var outFileTest = new File(fullPathToFile);

            if (outFileTest.exists) {
              var destroyExisting = confirm('A file with that name already exists; overwrite?', false, 'Are you sure...?');
              if (destroyExisting) {
                outFileTest.remove();
                outFileTest.close();
              }
            }

            $.pype.log('binding events ...');
            app.encoder.bind('onEncoderJobComplete', $.pype.onEncoderJobComplete);

            // use these 0 or 1 settings to disable some/all metadata creation.
            app.encoder.setSidecarXMPEnabled(0);
            app.encoder.setEmbeddedXMPEnabled(0);

            $.pype.log('adding job to encoder');
            var jobID = app.encoder.encodeSequence(app.project.activeSequence, fullPathToFile, outPreset.fsName, app.encoder.ENCODE_IN_TO_OUT, 1); // Remove from queue upon successful completion?
            $.pype.expectedJobs.push(jobID);
            $.pype.log('job queue length: ' + $.pype.expectedJobs.length);
            $._PPP_.updateEventPanel('jobID = ' + jobID);
            outPreset.close();
            if (family === 'thumbnail') {
              return clipName + '_' + family + '_v' + version + '0.' + outputFormatExtension;
            } else {
              return file;
            }
          }
        } else {
          $._PPP_.updateEventPanel('Could not find output preset.');
        }
      } else {
        $._PPP_.updateEventPanel('Could not find/create output path.');
      }
      projPath.close();
    } else {
      $._PPP_.updateEventPanel('No active sequence.');
    }
  },

  log: function (message) {
    $.writeln(message);
    message = JSON.stringify(message);
    if (message.length > 100) {
      message = message.slice(0, 100);
    }
    app.setSDKEventMessage(message, 'info');
  },

  message: function (msg) {
    $.writeln(msg); // Using '$' object will invoke ExtendScript Toolkit, if installed.
  },

  alert_message: function (message) {
    alert(message, 'WARNING', true);
    app.setSDKEventMessage(message, 'error');
  },

  getWorkFileVersion: function () {
    var outputPath = $.pype.convertPathString(app.project.path);
    var outputName = String(app.project.name);
    var dirPath = outputPath.replace(outputName, '');
    var pattern = /_v([0-9]*)/g;
    var search = pattern.exec(outputName);
    var version = 1;
    var newFileName,
      absPath;

    if (search) {
      return search[1]
    } else {
      var create = confirm('The project file name is missing version `_v###` \n example: `NameOfFile_v001.prproj`\n\n Would you like to create version?', true, 'ERROR in name syntax');
      if (create) {
        var splitName = outputName.split('.');
        newFileName = splitName[0] + '_v001.' + splitName[1];
        absPath = dirPath + newFileName;
        app.project.saveAs(absPath.split('/').join($._PPP_.getSep()));
        return '001';
      }
    }
  },

  nextVersionCheck: function (dir, file, vCurVersStr, curVersStr, padding, nextVersNum) {
    var replVers = vCurVersStr.replace(curVersStr, (nextVersNum).pad(padding));
    var newFileName = file.replace(vCurVersStr, replVers);
    var absPath = dir + newFileName;
    var absPathF = new File(absPath);
    if (absPathF.exists) {
      return $.pype.nextVersionCheck(dir, file, vCurVersStr, curVersStr, padding, (nextVersNum + 1));
    } else {
      return absPathF
    }
  },

  versionUpWorkFile: function () {
    var outputPath = $.pype.convertPathString(app.project.path);
    var outputName = String(app.project.name);
    var dirPath = outputPath.replace(outputName, '');
    var pattern = /_v([0-9]*)/g;
    var search = pattern.exec(outputName);
    var version = 1;
    var newFileName,
      absPath;

    if (search) {
      var match = parseInt(search[1], 10);
      var padLength = search[1].length;
      version += match;
      var replVers = search[0].replace(search[1], (version).pad(padLength));
      newFileName = outputName.replace(search[0], replVers);
      absPath = dirPath + newFileName;

      // check if new file already exists and offer confirmation
      var absPathF = new File(absPath);
      if (absPathF.exists) {
        var overwrite = confirm('The file already exists! Do you want to overwrite it? NO: will save it as next available version', false, 'Are you sure...?');
        if (overwrite) {
          // will overwrite
          app.project.saveAs(absPath.split('/').join($._PPP_.getSep()));
          return newFileName;
        } else {
          // will not overwrite
          // will find next available version
          absPathF = $.pype.nextVersionCheck(dirPath, outputName, search[0], search[1], padLength, (version + 1));
          absPath = $.pype.convertPathString(absPathF.fsName)
          newFileName = absPath.replace(dirPath, '')
          $.writeln('newFileName: ' + newFileName)
          // will save it as new file
          app.project.saveAs(absPath.split('/').join($._PPP_.getSep()));
          return newFileName;
        };
      } else {
        app.project.saveAs(absPath.split('/').join($._PPP_.getSep()));
        return newFileName;
      };
    } else {
      var create = confirm('The project file name is missing version `_v###` \n example: `NameOfFile_v001.prproj`\n\n Would you like to create version?", true, "ERROR in name syntax');
      if (create) {
        var splitName = outputName.split('.');
        newFileName = splitName[0] + '_v001.' + splitName[1];
        absPath = dirPath + newFileName;
        app.project.saveAs(absPath.split('/').join($._PPP_.getSep()));
        return newFileName;
      }
    }
  },
  // ,
  /**
   * #######################################################################
   * bellow section is dedicated mostly to loading clips
   * #######################################################################
   */

  // replaceClips: function (obj, projectItems) {
  //    $.pype.log('num of projectItems:' + projectItems.length);
  //    var hiresVOs = obj.hiresOnFS;
  //    for (var i = 0; i < hiresVOs.length; i++) {
  //      $.pype.log('hires vo name: ' + hiresVOs[i].name);
  //      $.pype.log('hires vo id:  ' + hiresVOs[i].id);
  //      $.pype.log('hires vo path: ' + hiresVOs[i].path);
  //      $.pype.log('hires vo replace: ' + hiresVOs[i].replace);
  //
  //      for (var j = 0; j < projectItems.length; j++) {
  //        // $.pype.log('projectItem id: ' + projectItems[j].name.split(' ')[0] + ' ' + hiresVOs[i].id + ' can change path  ' + projectItems[j].canChangeMediaPath() );
  //        if (projectItems[j].name.split(' ')[0] === hiresVOs[i].id && hiresVOs[i].replace && projectItems[j].canChangeMediaPath()) {
  //          $.pype.log('replace: ' + projectItems[j].name + ' with ' + hiresVOs[i].name);
  //          projectItems[j].name = hiresVOs[i].name;
  //          projectItems[j].changeMediaPath(hiresVOs[i].path);
  //        }
  //      }
  //    }
  //  },

  // addNewTrack: function (numTracks) {
  //   app.enableQE();
  //   var sequence = app.project.activeSequence;
  //   var activeSequence = qe.project.getActiveSequence();
  //   activeSequence.addTracks(numTracks, sequence.videoTracks.numTracks, 0);
  //
  //   for (var t = 0; t < sequence.videoTracks.numTracks; t++) {
  //     var videoTrack = sequence.videoTracks[t];
  //     var trackName = videoTrack.name;
  //     var trackTarget = videoTrack.isTargeted();
  //     // $.writeln(trackTarget);
  //     sequence.videoTracks[t].setTargeted(false, true);
  //     trackTarget = videoTrack.isTargeted();
  //     // $.writeln(trackTarget);
  //     // $.writeln(videoTrack);
  //   }
  // },

  // searchForBinWithName: function (nameToFind, folderObject) {
  //   // deep-search a folder by name in project
  //   var deepSearchBin = function (inFolder) {
  //     if (inFolder && inFolder.name === nameToFind && inFolder.type === 2) {
  //       return inFolder;
  //     } else {
  //       for (var i = 0; i < inFolder.children.numItems; i++) {
  //         if (inFolder.children[i] && inFolder.children[i].type === 2) {
  //           var foundBin = deepSearchBin(inFolder.children[i]);
  //           if (foundBin)
  //             return foundBin;
  //           }
  //         }
  //     }
  //     return undefined;
  //   };
  //   if (folderObject === undefined) {
  //     return deepSearchBin(app.project.rootItem);
  //   } else {
  //     return deepSearchBin(folderObject);
  //   }
  // },

  // createDeepBinStructure: function (hierarchyString) {
  //   var parents = hierarchyString.split('/');
  //
  //   // search for the created folder
  //   var currentBin = $.pype.searchForBinWithName(parents[0]);
  //   // create bin if doesn't exists
  //   if (currentBin === undefined) {
  //     currentBin = app.project.rootItem.createBin(parents[0]);
  //   }
  //   for (var b = 1; b < parents.length; b++) {
  //     var testBin = $.pype.searchForBinWithName(parents[b], currentBin);
  //     if (testBin === undefined) {
  //       currentBin = currentBin.createBin(parents[b]);
  //     } else {
  //       currentBin = testBin;
  //     }
  //   }
  //   return currentBin;
  // },

  // insertBinClipToTimeline: function (binClip, time, trackOrder, numTracks, origNumTracks) {
  //   var seq = app.project.activeSequence;
  //   var numVTracks = seq.videoTracks.numTracks;
  //
  //   var addInTrack = (numTracks === 1)
  //     ? (origNumTracks)
  //     : (numVTracks - numTracks + trackOrder);
  //   $.writeln('\n___name: ' + binClip.name);
  //   $.writeln('numVTracks: ' + numVTracks + ', trackOrder: ' + trackOrder + ', numTracks: ' + numTracks + ', origNumTracks: ' + origNumTracks + ', addInTrack: ' + addInTrack);
  //
  //   var targetVTrack = seq.videoTracks[addInTrack];
  //
  //   if (targetVTrack) {
  //     targetVTrack.insertClip(binClip, time);
  //   }
  // },
  // /**
  //  * Return instance representation of clip imported into bin
  //  * @param data {object} - has to have at least two attributes `clips` and `binHierarchy`
  //  * @return {Object}
  //  */

  // importFiles: function (data) {
  //   // remove all empty tracks
  //   app.enableQE();
  //   var activeSequence = qe.project.getActiveSequence();
  //   activeSequence.removeEmptyVideoTracks();
  //   activeSequence.removeEmptyAudioTracks();
  //
  //   if (app.project) {
  //     if (data !== undefined) {
  //       var pathsToImport = [];
  //       var namesToGetFromBin = [];
  //       var namesToSetToClips = [];
  //       var origNumTracks = app.project.activeSequence.videoTracks.numTracks;
  //       // TODO: for now it always creates new track and adding it into it
  //       $.pype.addNewTrack(data.numTracks);
  //
  //       // get all paths and names list
  //       var key = '';
  //       for (key in data.clips) {
  //         var path = data.clips[key]['data']['path'];
  //         var fileName = path.split('/');
  //         if (fileName.length <= 1) {
  //           fileName = path.split('\\');
  //         }
  //         fileName = fileName[fileName.length - 1];
  //         pathsToImport.push(path);
  //         namesToGetFromBin.push(fileName);
  //         namesToSetToClips.push(key);
  //       }
  //
  //       // create parent bin object
  //       var parent = $.pype.createDeepBinStructure(data.binHierarchy);
  //
  //       // check if any imported clips are in the bin
  //       if (parent.children.numItems > 0) {
  //         // loop pathsToImport
  //         var binItemNames = [];
  //         for (var c = 0; c < parent.children.numItems; c++) {
  //           binItemNames.push(parent.children[c].name);
  //         }
  //
  //         // loop formated clip names to be imported
  //         for (var p = 0; p < namesToSetToClips.length; p++) {
  //           // check if the clip is not in bin items alrady
  //           if (!include(binItemNames, namesToSetToClips[p])) {
  //             app.project.importFiles([pathsToImport[p]], 1, // suppress warnings
  //                 parent, 0); // import as numbered stills
  //
  //             for (var pi = 0; pi < parent.children.numItems; pi++) {
  //               if (namesToGetFromBin[p] === parent.children[pi].name) {
  //                 parent.children[pi].name = namesToSetToClips[p];
  //                 var start = data.clips[namesToSetToClips[p]]['parentClip']['start']
  //                 $.pype.insertBinClipToTimeline(parent.children[pi], start, data.clips[namesToSetToClips[p]]['parentClip']['trackOrder'], data.numTracks, origNumTracks);
  //               }
  //             }
  //           } else { // if the bin item already exist just update the path
  //             // loop children in parent bin
  //             for (var pi = 0; pi < parent.children.numItems; pi++) {
  //               if (namesToSetToClips[p] === parent.children[pi].name) {
  //                 $.writeln('__namesToSetToClips[p]__: ' + namesToSetToClips[p]);
  //                 parent.children[pi].changeMediaPath(pathsToImport[p]);
  //                 // clip exists and we can update path
  //                 $.writeln('____clip exists and updating path');
  //               }
  //             }
  //           }
  //         }
  //       } else {
  //         app.project.importFiles(pathsToImport, 1, // suppress warnings
  //             parent, 0); // import as numbered stills
  //         for (var pi = 0; pi < parent.children.numItems; pi++) {
  //           parent.children[pi].name = namesToSetToClips[i];
  //           start = data.clips[namesToSetToClips[i]]['parentClip']['start']
  //           $.pype.insertBinClipToTimeline(parent.children[pi], start, data.clips[namesToSetToClips[i]]['parentClip']['trackOrder'], data.numTracks, origNumTracks);
  //         }
  //
  //         return;
  //       }
  //     } else {
  //       alert('Missing data for clip insertion', 'error');
  //       return false;
  //     }
  //   }
  //   // remove all empty tracks
  //   activeSequence.removeEmptyVideoTracks();
  //   activeSequence.removeEmptyAudioTracks();
  // }
};

Number.prototype.pad = function (size) {
  var s = String(this);
  while (s.length < (size || 2)) {
    s = "0" + s;
  }
  return s;
};

function include (arr, obj) {
  for (var i = 0; i < arr.length; i++) {
    if (arr[i] === obj)
      return true;
    }
  return false
}
