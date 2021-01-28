/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                        CollectFarmRender                                *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony !== 'undefined') {
    var PYPE_HARMONY_JS = System.getenv('PYPE_HARMONY_JS');
    include(PYPE_HARMONY_JS + '/pype_harmony.js');
}


/**
 * @namespace
 * @classdesc Image Sequence loader JS code.
 */
var CollectFarmRender = function() {};


/**
 * Get information important for render output.
 * @function
 * @param node {String} node name.
 * @return {array} array of render info.
 *
 * @example
 *
 * var ret = [
 *    file_prefix, // like foo/bar-
 *    type, // PNG4, ...
 *    leading_zeros, // 3 - for 0001
 *    start // start frame
 * ]
 */
CollectFarmRender.prototype.getRenderNodeSettings = function(n) {
    // this will return
    var output = [
        node.getTextAttr(
            n, frame.current(), 'DRAWING_NAME'),
        node.getTextAttr(
            n, frame.current(), 'DRAWING_TYPE'),
        node.getTextAttr(
            n, frame.current(), 'LEADING_ZEROS'),
        node.getTextAttr(n, frame.current(), 'START'),
        node.getEnable(n)
    ];

    return output;
};

// add self to Pype Loaders
PypeHarmony.Publish.CollectFarmRender = new CollectFarmRender();
