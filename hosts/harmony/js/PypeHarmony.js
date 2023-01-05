/* global include */
// ***************************************************************************
// *                        Pype Harmony Host                                *
// ***************************************************************************

var LD_OPENHARMONY_PATH = System.getenv('LIB_OPENHARMONY_PATH');
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH + '/openHarmony.js';
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH.replace(/\\/g, "/");



/**
 * @namespace
 * @classdesc PypeHarmony encapsulate all Pype related functions.
 * @property  {Object}  loaders   Namespace for Loaders JS code.
 * @property  {Object}  Creators  Namespace for Creators JS code.
 * @property  {Object}  Publish   Namespace for Publish plugins JS code.
 */
var PypeHarmony = {
    Loaders: {},
    Creators: {},
    Publish: {}
};


/**
 * Show message in Harmony.
 * @function
 * @param {string} message  Argument containing message.
 */
PypeHarmony.message = function(message) {
    MessageBox.information(message);
};


/**
 * Set scene setting based on shot/asset settngs.
 * @function
 * @param {obj} settings  Scene settings.
 */
PypeHarmony.setSceneSettings = function(settings) {
    if (settings.fps) {
        scene.setFrameRate(settings.fps);
    }

    if (settings.frameStart && settings.frameEnd) {
        var duration = settings.frameEnd - settings.frameStart + 1;

        if (frame.numberOf() > duration) {
            frame.remove(duration, frame.numberOf() - duration);
        }

        if (frame.numberOf() < duration) {
            frame.insert(duration, duration - frame.numberOf());
        }

        scene.setStartFrame(1);
        scene.setStopFrame(duration);
    }
    if (settings.resolutionWidth && settings.resolutionHeight) {
        scene.setDefaultResolution(
            settings.resolutionWidth, settings.resolutionHeight, 41.112
        );
    }
};


/**
 * Get scene settings.
 * @function
 * @return {array} Scene settings.
 */
PypeHarmony.getSceneSettings = function() {
    return [
        about.getApplicationPath(),
        scene.currentProjectPath(),
        scene.currentScene(),
        scene.getFrameRate(),
        scene.getStartFrame(),
        scene.getStopFrame(),
        sound.getSoundtrackAll().path(),
        scene.defaultResolutionX(),
        scene.defaultResolutionY(),
        scene.defaultResolutionFOV()
    ];
};


/**
 * Set color of nodes.
 * @function
 * @param {array} nodes List of nodes.
 * @param {array} rgba  array of RGBA components of color.
 */
PypeHarmony.setColor = function(nodes, rgba) {
    for (var i =0; i <= nodes.length - 1; ++i) {
        var color = PypeHarmony.color(rgba);
        node.setColor(nodes[i], color);
    }
};


/**
 * Extract Template into file.
 * @function
 * @param {array} args  Arguments for template extraction.
 *
 * @example
 * // arguments are in this order:
 * var args = [backdrops, nodes, templateFilename, templateDir];
 *
 */
PypeHarmony.exportTemplate = function(args) {
    var tempNode = node.add('Top', 'temp_note', 'NOTE', 0, 0, 0);
    var templateGroup = node.createGroup(tempNode, 'temp_group');
    node.deleteNode( templateGroup + '/temp_note' );

    selection.clearSelection();
    for (var f = 0; f < args[1].length; f++) {
        selection.addNodeToSelection(args[1][f]);
    }

    Action.perform('copy()', 'Node View');

    selection.clearSelection();
    selection.addNodeToSelection(templateGroup);
    Action.perform('onActionEnterGroup()', 'Node View');
    Action.perform('paste()', 'Node View');

    // Recreate backdrops in group.
    for (var i = 0; i < args[0].length; i++) {
        MessageLog.trace(args[0][i]);
        Backdrop.addBackdrop(templateGroup, args[0][i]);
    }

    Action.perform('selectAll()', 'Node View' );
    copyPaste.createTemplateFromSelection(args[2], args[3]);

    // Unfocus the group in Node view, delete all nodes and backdrops
    // created during the process.
    Action.perform('onActionUpToParent()', 'Node View');
    node.deleteNode(templateGroup, true, true);
};


/**
 * Toggle instance in Harmony.
 * @function
 * @param {array} args  Instance name and value.
 */
PypeHarmony.toggleInstance = function(args) {
    node.setEnable(args[0], args[1]);
};


/**
 * Delete node in Harmony.
 * @function
 * @param {string} _node  Node name.
 */
PypeHarmony.deleteNode = function(_node) {
    node.deleteNode(_node, true, true);
};


/**
 * Copy file.
 * @function
 * @param {string}  src Source file name.
 * @param {string}  dst Destination file name.
 */
PypeHarmony.copyFile = function(src, dst) {
    var srcFile = new PermanentFile(src);
    var dstFile = new PermanentFile(dst);
    srcFile.copy(dstFile);
};


/**
 * create RGBA color from array.
 * @function
 * @param   {array}     rgba array of rgba values.
 * @return  {ColorRGBA} ColorRGBA Harmony class.
 */
PypeHarmony.color = function(rgba) {
    return new ColorRGBA(rgba[0], rgba[1], rgba[2], rgba[3]);
};


/**
 * get all dependencies for given node.
 * @function
 * @param   {string}  _node node path.
 * @return  {array}   List of dependent nodes.
 */
PypeHarmony.getDependencies = function(_node) {
    var target_node = _node;
    var numInput = node.numberOfInputPorts(target_node);
    var dependencies = [];
    for (var i = 0 ; i < numInput; i++) {
        dependencies.push(node.srcNode(target_node, i));
    }
    return dependencies;
};


/**
 * return version of running Harmony instance.
 * @function
 * @return  {array} [major_version, minor_version]
 */
PypeHarmony.getVersion = function() {
    return [
        about.getMajorVersion(),
        about.getMinorVersion()
    ];
};
