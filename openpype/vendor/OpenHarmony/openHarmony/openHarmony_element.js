//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library v0.01
//
//
//         Developped by Mathieu Chaptel, Chris Fourney...
//
//
//   This library is an open source implementation of a Document Object Model
//   for Toonboom Harmony. It also implements patterns similar to JQuery
//   for traversing this DOM.
//
//   Its intended purpose is to simplify and streamline toonboom scripting to
//   empower users and be easy on newcomers, with default parameters values,
//   and by hiding the heavy lifting required by the official API.
//
//   This library is provided as is and is a work in progress. As such, not every
//   function has been implemented or is garanteed to work. Feel free to contribute
//   improvements to its official github. If you do make sure you follow the provided
//   template and naming conventions and document your new methods properly.
//
//   This library doesn't overwrite any of the objects and classes of the official
//   Toonboom API which must remains available.
//
//   This library is made available under the MIT license.
//   https://opensource.org/licenses/mit
//
//   The repository for this library is available at the address:
//   https://github.com/cfourney/OpenHarmony/
//
//
//   For any requests feel free to contact m.chaptel@gmail.com
//
//
//
//
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//          $.oElement class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The base class for the $.oElement.<br> Elements hold the drawings displayed by a "READ" Node or Drawing Node. They can be used to create new drawings, rename them, etc.
 * @constructor
 * @classdesc  $.oElement Class
 * @param   {int}                   id                          The element ID.
 * @param   {$.oColumn}             oColumnObject               The column object associated to the element.
 *
 * @property {int}                  id                          The element ID.
 * @property {$.oColumn}            oColumnObject               The column object associated to the element.
 */
$.oElement = function( id, oColumnObject){
  this._type = "element";

  this.id = id;
  this.column = oColumnObject;
}

// $.oElement Object Properties

/**
 * The name of the element.
 * @name $.oElement#name
 * @type {string}
 */
Object.defineProperty($.oElement.prototype, 'name', {
    get : function(){
         return element.getNameById(this.id)
    },

    set : function(newName){
         element.renameById(this.id, newName);
    }
})


/**
 * The folder path of the element on the filesystem.
 * @name $.oElement#path
 * @type {string}
 */
Object.defineProperty($.oElement.prototype, 'path', {
    get : function(){
         return fileMapper.toNativePath(element.completeFolder(this.id))
    }
})


/**
 * The drawings available in the element.
 * @name $.oElement#drawings
 * @type {$.oDrawing[]}
 */
Object.defineProperty($.oElement.prototype, 'drawings', {
  get : function(){
    var _drawingsNumber = Drawing.numberOf(this.id);
    var _drawings = [];
    for (var i=0; i<_drawingsNumber; i++){
      _drawings.push( new this.$.oDrawing(Drawing.name(this.id, i), this) );
    }
    return _drawings;
  }
})


/**
 * The file format of the element.
 * @name $.oElement#format
 * @type {string}
 */
Object.defineProperty($.oElement.prototype, 'format', {
  get : function(){
    var _type = element.pixmapFormat(this.id);
    if (element.vectorType(this.id)) _type = "TVG";
    return _type;
  }
})


/**
 * The palettes linked to this element.
 * @name $.oElement#palettes
 * @type {$.oPalette[]}
 */
Object.defineProperty($.oElement.prototype, 'palettes', {
  get: function(){
    var _paletteList = PaletteObjectManager.getPaletteListByElementId(this.id);
    var _palettes = [];
    for (var i=0; i<_paletteList.numPalettes; i++){
      _palettes.push( new this.$.oPalette( _paletteList.getPaletteByIndex(i), _paletteList ) );
    }

    return _palettes;
  }
})


// $.oElement Class methods

/**
 * Adds a drawing to the element. Provide a filename to import an external file as a drawing.
 * @param   {int}        [atFrame=1]            The frame at which to add the drawing on the $.oDrawingColumn. Values < 1 create no exposure.
 * @param   {name}       [name]                 The name of the drawing to add.
 * @param   {string}     [filename]             Optionally, a path for a drawing file to use for this drawing. Can pass an oFile object as well.
 * @param   {bool}       [convertToTvg=false]   If the filename isn't a tvg file, specify if you want it converted (this doesn't vectorize the drawing).
 *
 * @return {$.oDrawing}      The added drawing
 */
$.oElement.prototype.addDrawing = function( atFrame, name, filename, convertToTvg ){
  if (typeof atFrame === 'undefined') var atFrame = 1;
  if (typeof filename === 'undefined') var filename = null;
  var nameByFrame = this.$.app.preferences.XSHEET_NAME_BY_FRAME;
  if (typeof name === 'undefined') var name = nameByFrame?atFrame:1;
  var name = name +""; // convert name to string

  // ensure a new drawing is always created by incrementing depending on preference
  var _drawingNames = this.drawings.map(function(x){return x.name}); // index of existing names
  var _nameFormat = /(.*?)_(\d+)$/
  while (_drawingNames.indexOf(name) != -1){
    if (nameByFrame || isNaN(name)){
      var nameGroups = name.match(_nameFormat);
      if (nameGroups){
        // increment the part after the underscore
        name = nameGroups[1] + "_" + (parseInt(nameGroups[2])+1);
      }else{
        name += "_1";
      }
    }else{
      name = parseInt(name, 10);
      if (isNaN(name)) name = 0;
      name = name + 1 + ""; // increment and convert back to string
    }
  }

  if (!(filename instanceof this.$.oFile)) filename = new this.$.oFile(filename);
  var _fileExists = filename.exists;
  Drawing.create (this.id, name, _fileExists, true);

  var _drawing = new this.$.oDrawing( name, this );

  if (_fileExists) _drawing.importBitmap(filename, convertToTvg);

  // place drawing on the column at the provided frame
  if (this.column != null || this.column != undefined && atFrame >= 1){
    column.setEntry(this.column.uniqueName, 1, atFrame, name);
  }

  return _drawing;
}


/**
 * Gets a drawing object by the name.
 * @param   {string}  name  The name of the drawing to get.
 *
 * @return  {$.oDrawing}      The drawing found by the search
 */
$.oElement.prototype.getDrawingByName = function ( name ){
  var _drawings = this.drawings;
  for (var i in _drawings){
    if (_drawings[i].name == name) return _drawings[i];
  }
  return null;
}


/**
 * Link a provided palette to an element as an Element palette.
 * @param   {$.oPalette}    oPaletteObject              The oPalette object to link
 * @param   {int}           [listIndex]              The index in the element palette list at which to add the newly linked palette
 * @return  {$.oPalette}    The linked element palette.
 */
$.oElement.prototype.linkPalette = function ( oPaletteObject , listIndex){
  var _paletteList = PaletteObjectManager.getPaletteListByElementId(this.id);
  if (typeof listIndex === 'undefined') var listIndex = _paletteList.numPalettes;

  var _palettePath = oPaletteObject.path.path.replace(".plt", "");

  var _palette = new this.$.oPalette(_paletteList.insertPalette (_palettePath, listIndex), _paletteList);
  return _palette;
}


/**
 * If the palette passed as a parameter is linked to this element, it will be unlinked, and moved to the scene palette list.
 * @param {$.oPalette} oPaletteObject
 * @return {bool} the success of the unlinking process.
 */
$.oElement.prototype.unlinkPalette = function (oPaletteObject) {
  var _palettes = this.palettes;
  var _ids = _palettes.map(function(x){return x.id});
  var _paletteId = oPaletteObject.id;
  var _paletteIndex = _ids.indexOf(_paletteId);

  if (_paletteIndex == -1) return; // palette already isn't linked

  var _palette = _palettes[_paletteIndex];
  try{
    _palette.remove(false);
    return true;
  }catch(err){
    this.$.debug("Failed to unlink palette "+_palette.name+" from element "+this.name);
    return false;
  }
}



/**
 * Duplicate an element.
 * @param   {string}     [name]              The new name for the duplicated element.
 * @return  {$.oElement}      The duplicate element
 */
$.oElement.prototype.duplicate = function(name){
  if (typeof name === 'undefined') var name = this.name;

  var _fieldGuide = element.fieldChart(this.id);
  var _scanType = element.scanType(this.id);

  var _duplicateElement = this.$.scene.addElement(name, this.format, _fieldGuide, _scanType);

  var _drawings = this.drawings;
  var _elementFolder = new this.$.oFolder(_duplicateElement.path);

  for (var i in _drawings){
    var _drawingFile = new this.$.oFile(_drawings[i].path);
    try{
      var duplicateDrawing = _duplicateElement.addDrawing(0, _drawings[i].name, _drawingFile);
      _drawingFile.copy(_elementFolder, duplicateDrawing.name, true);
    }catch(err){
      this.debug("could not copy drawing file "+drawingFile.name+" into element "+_duplicateElement.name, this.DEBUG_LEVEL.ERROR);
    }
  }
  return _duplicateElement;
}