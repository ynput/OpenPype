/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                           ExtractPalette                                *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony !== 'undefined') {
    var PYPE_HARMONY_JS = System.getenv('PYPE_HARMONY_JS');
    include(PYPE_HARMONY_JS + '/pype_harmony.js');
}


/**
 * @namespace
 * @classdesc Code for extracting palettes.
 */
var ExtractPalette = function() {};


/**
 * Get palette from Harmony.
 * @function
 * @param   {string} paletteId ID of palette to get.
 * @return  {array}  [paletteName, palettePath]
 */
ExtractPalette.prototype.getPalette = function(paletteId) {
    var palette_list = PaletteObjectManager.getScenePaletteList();
    var palette = palette_list.getPaletteById(paletteId);
    var palette_name = palette.getName();
    return [
        palette_name,
        (palette.getPath() + '/' + palette.getName() + '.plt')
    ];  
};

// add self to Pype Loaders
PypeHarmony.Publish.ExtractPalette = new ExtractPalette();
