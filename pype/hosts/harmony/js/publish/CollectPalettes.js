/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                        CollectPalettes                                  *
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
var CollectPalettes = function() {};

CollectPalettes.prototype.getPalettes = function() {
    var palette_list = PaletteObjectManager.getScenePaletteList();

    var palettes = {};
    for(var i=0; i < palette_list.numPalettes; ++i) {
        var palette = palette_list.getPaletteByIndex(i);
        palettes[palette.getName()] = palette.id;
    }

    return palettes;
};

// add self to Pype Loaders
PypeHarmony.Publish.CollectPalettes = new CollectPalettes();
