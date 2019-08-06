var projectItems = [];
var sequences = [];

function importClips(obj) {
    app.project.importFiles(obj.paths);
    return JSON.stringify(obj);
}

function getEnv() {
    app.enableQE();
    var obj = {
        os: qe.platform,
        name: app.project.name,
        path: app.project.path
    }
    return JSON.stringify(obj);
}

function getSequences() {
    var project = app.project;
    // var sequences = [];
    for (var i = 0; i < project.sequences.numSequences; i++) {
        var seq = project.sequences[i];
        seq.clipNames = [];
        sequences[i] = seq;
        log('sequences[i]  id: ' + project.sequences[i].sequenceID);
    }

    var obj = {
        sequences: sequences
    }
    return JSON.stringify(obj);
}

function getSequenceItems(seqs) {
    app.enableQE();
    qe.project.init();
    sequences = seqs;
    // log('getSequenceItems sequences obj from app: ' + sequences);

    var rootFolder = app.project.rootItem;
    var binCounter = -1;
    var rootSeqCounter = -1; //count sequences in root folder

    //walk through root folder of project to differentiate between bins, sequences and clips
    for (var i = 0; i < rootFolder.children.numItems; i++) {
        //        log('\nroot item at ' + i + " is " +  rootFolder.children[i].name + " of type " + rootFolder.children[i].type);
        var item = rootFolder.children[i];
        // log('item has video tracks? ' + item.videoTracks);
        if (item.type == 2) { //bin
            binCounter++;
            walkBins(item, 'root', binCounter);
        } else if (item.type == 1 && !item.getMediaPath()) //sequence  OR other type of object
        {
            //     log('\nObject of type 1 in root: ' +  typeof item + '   ' + item.name);

            if (objectIsSequence(item)) { //objects of type can also be other objects such as titles, so check if it really is a sequence
                //                    log('\nSequence in root: ' +  item.name );
                rootSeqCounter++;
                var seq = qe.project.getSequenceAt(rootSeqCounter);
                //  log('\nSequence in root, guid: ' +  seq );
                for (var property in seq) {
                    if (seq.hasOwnProperty(property)) {
                        //  log('\nSequence in root: ' + seq );
                        //log('qe sequence prop: ' + property );
                    }
                }
                getClipNames(seq, sequences);
            }
        }
    }

    function objectIsSequence() {
        var isSequence = false;

        for (var s = 0; s < app.project.sequences.numSequences; s++)
            if (item.name == app.project.sequences[s].name)
                isSequence = true;

        return isSequence
    }

    // walk through bins recursively
    function walkBins(item, source, rootBinCounter) {
        app.enableQE();
        //        log('\nget clips for bin  ' + item.name  );

        var bin;
        if (source == 'root') //bin in root folder
            bin = qe.project.getBinAt(rootBinCounter);
        else // bin in other bin
            bin = item;

        for (var i = 0; i < bin.numBins; i++) //if bin contains bin(s) walk through them                
            walkBins(bin.getBinAt(i));

        //        log('Bin ' + bin.name + ' has ' + bin.numSequences + ' sequences ' );
        var seqCounter = -1;
        for (var j = 0; j < bin.numSequences; j++) {
            //if(objectIsSequence(item)) {//objects of type can also be other objects such as titles, so check if it really is a sequence?
            //not needed because getSequenceAt apparently only looks at sequences already?
            var seq = bin.getSequenceAt(j);
            //   log('\nSequence in bin, guid: ' +  seq.guid );
            getClipNames(seq, sequences);
            //}
        }
    }

    //walk through sequences and video & audiotracks to find clip names in sequences
    function getClipNames(seq, sequences) {

        for (var k = 0; k < sequences.length; k++) {
            //  log('getClipNames seq.guid ' + seq.guid  );
            //log(' getClipNames sequences[k].id ' +  sequences[k].sequenceID  );
            if (seq.guid == sequences[k].sequenceID) {
                //  log('Sequence ' + seq.name + ' has ' + app.project.sequences[k].videoTracks.numTracks +' video tracks'  );
                //  log('Sequence ' + seq.name + ' has ' + app.project.sequences[k].audioTracks.numTracks +' audio tracks'  );

                //VIDEO CLIPS IN SEQUENCES
                for (var l = 0; l < sequences[k].videoTracks.numTracks; l++) {
                    var videoTrack = seq.getVideoTrackAt(l);
                    //  log(seq.name + ' has video track '+ videoTrack.name + ' at index ' + l);

                    var clipCounter = 0;
                    var numOfClips = app.project.sequences[k].videoTracks[l].clips.numTracks;
                    //  log('\n' + bin.name + ' ' + seq.name + ' ' + videoTrack.name + ' has  ' + numOfClips + ' clips');
                    for (var m = 0; m < numOfClips; m++) {
                        var clip = app.project.sequences[k].videoTracks[l].clips[m];
                        //                       log('clips in video tracks:   ' + m + ' - ' + clip); //TrackItem, doesn't have name property                              
                        //if a clip was deleted and another one added, the index of the new one is one  or more higher
                        while (clipCounter < numOfClips) //undefined because of old clips
                        {
                            if (videoTrack.getItemAt(m).name) {
                                clipCounter++;
                                //     log('getClipNames ' + seq.name + ' ' + videoTrack.name + ' has  ' + videoTrack.getItemAt(m).name); //Object

                                for (var s = 0; s < sequences.length; s++)
                                    if (seq.guid == sequences[s].sequenceID)
                                        sequences[s].clipNames.push(videoTrack.getItemAt(m).name);
                            }
                            m++;
                        }
                    }
                }
                // log('jsx after video loop clipsInSequences:' + clipsInSequences);

                //AUDIO CLIPS IN SEQUENCES
                for (var l = 0; l < sequences[k].audioTracks.numTracks; l++) {
                    var audioTrack = seq.getAudioTrackAt(l);
                    //log(bin.name + ' ' + seq.name + ' has audio track '+ audioTrack.name + ' at index ' + l);
                    //log('\n' + bin.name + ' ' + seq.name + ' ' + audioTrack.name + ' has  ' + app.project.sequences[k].audioTracks[l].clips.numTracks + ' clips');
                    var clipCounter = 0;
                    var numOfClips = app.project.sequences[k].audioTracks[l].clips.numTracks;

                    for (var m = 0; m < numOfClips; m++) {
                        var clip = app.project.sequences[k].audioTracks[l].clips[m];
                        //     log('clips in audio tracks:   ' + m + ' - ' + clip);
                        //if a clip was deleted and another one added, the index of the new one is one  or more higher 
                        while (clipCounter < numOfClips) //undefined because of old clips
                        {
                            if (audioTrack.getItemAt(m).name) {
                                clipCounter++;
                                //                                log(seq.name + ' ' + audioTrack.name + ' has  ' + audioTrack.getItemAt(m).name);

                                for (var s = 0; s < sequences.length; s++)
                                    if (seq.guid == sequences[s].sequenceID)
                                        sequences[s].clipNames.push(audioTrack.getItemAt(m).name);
                            }
                            m++;
                        }
                    }
                }

            } //end if
        } //end for
    } //end getClipNames
    log('sequences returned:' + sequences);
    //return result to ReplaceService.js
    var obj = {
        data: sequences
    };
    // log('jsx getClipNames obj:' + obj);
    return JSON.stringify(obj);
}

//getSequenceItems();

function getProjectItems() {
    projectItems = [];
    app.enableQE();
    qe.project.init();

    var rootFolder = app.project.rootItem;
    //walk through root folder of project to differentiate between bins, sequences and clips
    for (var i = 0; i < rootFolder.children.numItems; i++) {
        //  log('\nroot item at ' + i + " is of type " + rootFolder.children[i].type);
        var item = rootFolder.children[i];

        if (item.type == 2) { //bin
            //  log('\n' );
            walkBins(item);
        } else if (item.type == 1 && item.getMediaPath()) //clip in root
        {
            //  log('Root folder has '  + item + ' ' + item.name);
            projectItems.push(item);
        }
    }

    // walk through bins recursively
    function walkBins(bin) {
        app.enableQE();

        //  $.writeln('bin.name + ' has ' + bin.children.numItems); 
        for (var i = 0; i < bin.children.numItems; i++) {
            var object = bin.children[i];
            // log(bin.name + ' has ' + object + ' ' + object.name  + ' of type ' +  object.type + ' and has mediapath ' + object.getMediaPath() );
            if (object.type == 2) { //bin
                // log(object.name  + ' has ' +  object.children.numItems  );
                for (var j = 0; j < object.children.numItems; j++) {
                    var obj = object.children[j];
                    if (obj.type == 1 && obj.getMediaPath()) { //clip  in sub bin
                        //log(object.name  + ' has ' + obj + ' ' +  obj.name  );
                        projectItems.push(obj);
                    } else if (obj.type == 2) { //bin
                        walkBins(obj);
                    }
                }
            } else if (object.type == 1 && object.getMediaPath()) //clip in bin in root
            {
                // log(bin.name + ' has ' + object + ' ' + object.name );
                projectItems.push(object);
            }
        }
    }
    log('\nprojectItems:' + projectItems.length + ' ' + projectItems);
    return projectItems;
}

function replaceClips(obj) {

    log('num of projectItems:' + projectItems.length);
    var hiresVOs = obj.hiresOnFS;
    for (var i = 0; i < hiresVOs.length; i++) {
        log('hires vo name: ' + hiresVOs[i].name);
        log('hires vo id:  ' + hiresVOs[i].id);
        log('hires vo path: ' + hiresVOs[i].path);
        log('hires vo replace: ' + hiresVOs[i].replace);

        for (var j = 0; j < projectItems.length; j++) {
            // log('projectItem id: ' + projectItems[j].name.split(' ')[0] + ' ' + hiresVOs[i].id + ' can change path  ' + projectItems[j].canChangeMediaPath() );
            if (projectItems[j].name.split(' ')[0] == hiresVOs[i].id && hiresVOs[i].replace && projectItems[j].canChangeMediaPath()) {
                log('replace: ' + projectItems[j].name + ' with ' + hiresVOs[i].name);
                projectItems[j].name = hiresVOs[i].name;
                projectItems[j].changeMediaPath(hiresVOs[i].path);
            }
        }
    }
}

function log(info) {
    try {
        var xLib = new ExternalObject("lib:\PlugPlugExternalObject");
    } catch (e) {
        alert(e);
    }

    if (xLib) {
        var eventObj = new CSXSEvent();
        eventObj.type = "LogEvent";
        eventObj.data = info;
        eventObj.dispatch();
    }
}

function message(msg) {
    $.writeln(msg); // Using '$' object will invoke ExtendScript Toolkit, if installed.
}
