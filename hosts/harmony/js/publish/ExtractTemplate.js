/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                           ExtractTemplate                               *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony === 'undefined') {
    var OPENPYPE_HARMONY_JS = System.getenv('OPENPYPE_HARMONY_JS') + '/PypeHarmony.js';
    include(OPENPYPE_HARMONY_JS.replace(/\\/g, "/"));
}


/**
 * @namespace
 * @classdesc Code for extracting palettes.
 */
var ExtractTemplate = function() {};


/**
 * Get backdrops for given node.
 * @function
 * @param   {string} probeNode Node path to probe for backdrops.
 * @return  {array} list of backdrops.
 */
ExtractTemplate.prototype.getBackdropsByNode = function(probeNode) {
    var backdrops = Backdrop.backdrops('Top');
    var valid_backdrops = [];
    for(var i=0; i<backdrops.length; i++)
    {
        var position = backdrops[i].position;

        var x_valid = false;
        var node_x = node.coordX(probeNode);
        if (position.x < node_x && node_x < (position.x + position.w)){
            x_valid = true;
        }

        var y_valid = false;
        var node_y = node.coordY(probeNode);
        if (position.y < node_y && node_y < (position.y + position.h)){
            y_valid = true;
        }

        if (x_valid && y_valid){
            valid_backdrops.push(backdrops[i]);
        }
    }
    return valid_backdrops;
};

// add self to Pype Loaders
PypeHarmony.Publish.ExtractTemplate = new ExtractTemplate();
