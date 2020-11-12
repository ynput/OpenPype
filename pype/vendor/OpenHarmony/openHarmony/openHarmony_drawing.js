//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library
//
//
//         Developped by Mathieu Chaptel, Chris Fourney
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
//   This library is made available under the Mozilla Public license 2.0.
//   https://www.mozilla.org/en-US/MPL/2.0/
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
//          $.oDrawing class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oDrawing constructor.
 * @constructor
 * @classdesc The $.oDrawing Class represents a single drawing from an element.
 * @param   {int}                    name                       The name of the drawing.
 * @param   {$.oElement}             oElementObject             The element object associated to the element.
 *
 * @property {int}                   name                       The name of the drawing.
 * @property {$.oElement}            element                    The element object associated to the element.
 */
$.oDrawing = function( name, oElementObject ){
  this._type = "drawing";
  this._name = name;
  this.element = oElementObject;
  this._key = Drawing.Key({
    elementId : oElementObject.id,
    exposure : name
  });
}


/**
 * The different types of lines ends.
 * @name $.oDrawing#LINE_END_TYPE
 * @enum
 */
$.oDrawing.LINE_END_TYPE = {
  ROUND : 1,
  FLAT : 2,
  BEVEL : 3
};


/**
 * The reference to the art layers to use with oDrawing.setAsActiveDrawing()
 * @name $.oDrawing#ART_LAYER
 * @enum
 */
$.oDrawing.ART_LAYER = {
  OVERLAY : 8,
  LINEART : 4,
  COLORART : 2,
  UNDERLAY : 1
};


/**
 * The name of the drawing.
 * @name $.oDrawing#name
 * @type {string}
 */
Object.defineProperty( $.oDrawing.prototype, 'name', {
    get : function(){
       return this._name;
    },

    set : function(newName){
      if (this._name == newName) return;

      var _column = this.element.column.uniqueName;
      // this ripples recursively

      if (Drawing.isExists(this.element.id, newName)) this.element.getDrawingByName(newName).name = newName+"_1";
      column.renameDrawing(_column, this._name, newName);
      this._name = newName;
    }
})


/**
 * The internal Id used to identify drawings.
 * @name $.oDrawing#id
 * @type {int}
 */
Object.defineProperty( $.oDrawing.prototype, 'id', {
  get : function(){
    return this._key.drawingId;
  }
})


/**
 * The folder path of the drawing on the filesystem.
 * @name $.oDrawing#path
 * @type {string}
 */
Object.defineProperty( $.oDrawing.prototype, 'path', {
    get : function(){
        return fileMapper.toNativePath(Drawing.filename(this.element.id, this.name))
    }
})


/**
 * The drawing pivot of the drawing.
 * @name $.oDrawing#pivot
 * @type {$.oPoint}
 */
Object.defineProperty( $.oDrawing.prototype, 'pivot', {
  get : function(){
    var _pivot = Drawing.getPivot({"drawing":this._key});
    return new this.$.oPoint(_pivot.x, _pivot.y, 0);
  },

  set : function(newPivot){
    var _pivot = {x: newPivot.x, y: newPivot.y};
    Drawing.setPivot({drawing:this._key, pivot:_pivot});
  }
})



/**
 * Access the underlay art layer's content through this object.
 * @name $.oDrawing#underlay
 * @type {$.oArtLayer}
 */
Object.defineProperty( $.oDrawing.prototype, 'underlay', {
  get : function(){
    return new this.$.oArtLayer(0, this);
  }
})


/**
 * Access the color art layer's content through this object.
 * @name $.oDrawing#colorArt
 * @type {$.oArtLayer}
 */
Object.defineProperty( $.oDrawing.prototype, 'colorArt', {
  get : function(){
    return new this.$.oArtLayer(1, this);
  }
})


/**
 * Access the line art layer's content through this object.
 * @name $.oDrawing#lineArt
 * @type {$.oArtLayer}
 */
Object.defineProperty( $.oDrawing.prototype, 'lineArt', {
  get : function(){
    return new this.$.oArtLayer(2, this);
  }
})


/**
 * Access the overlay art layer's content through this object.
 * @name $.oDrawing#overlay
 * @type {$.oArtLayer}
 */
Object.defineProperty( $.oDrawing.prototype, 'overlay', {
  get : function(){
    return new this.$.oArtLayer(3, this);
  }
})





// $.oDrawing Class methods

/**
 * Import a given file into an existing drawing.
 * @param   {string}     file              The path to the file
 *
 * @return { $.oDrawing }      The drawing found by the search
 */
$.oDrawing.prototype.importBitmap = function(file){
  var _path = new this.$.oFile(this.path);
  if (!(file instanceof this.$.oFile)) file = new this.$.oFile(file);

  if (!file.exists) return false;
  file.copy(_path.folder, _path.name, true);
}


/**
 * @returns {int[]}  The frame numbers at which this drawing appears.
 */
$.oDrawing.prototype.getVisibleFrames = function(){
  var _element = this.element;
  var _column = _element.column;

  if (!_column){
    this.$.log("Column missing: can't get visible frames for  drawing "+this.name+" of element "+_element.name);
    return null;
  }

  var _frames = [];
  var _keys = _column.keyframes;
  for (var i in _keys){
    if ( _keys[i].value == this.name) _frames.push(_keys[i].frameNumber);
  }

  return _frames;
}


/**
 * Remove the drawing from the element.
 */
$.oDrawing.prototype.remove = function(){
    var _element = this.element;
    var _column = _element.column;

    if (!_column){
      this.$.log("Column missing: impossible to delete drawing "+this.name+" of element "+_element.name);
      return;
    }

    var _frames = _column.frames;
    var _lastFrame = _frames.pop();
    // this.$.log(_lastFrame.frameNumber+": "+_lastFrame.value)

    var _thisDrawing = this;

    // we have to expose the drawing on the column to delete it. Exposing at the last frame...
    this.$.debug("deleting drawing "+_thisDrawing+" from element "+_element.name, this.$.DEBUG_LEVEL.LOG)
    var _lastDrawing = _lastFrame.value;
    var _keyFrame = _lastFrame.isKeyFrame;
    _lastFrame.value = _thisDrawing;

    column.deleteDrawingAt(_column.uniqueName, _lastFrame.frameNumber);

    // resetting the last frame
    _lastFrame.value = _lastDrawing;
    _lastFrame.isKeyFrame = _keyFrame;
}



/**
 * refresh the preview of the drawing.
 */
$.oDrawing.prototype.refreshPreview = function(){
  if (this.element.format == "TVG") return;

  var _path = new this.$.oFile(this.path);
  var _elementFolder = _path.folder;
  var _previewFiles = _elementFolder.getFiles(_path.name+"-*.tga");

  for (var i in _previewFiles){
    _previewFiles[i].remove();
  }
}


 /**
 * Change the currently active drawing. Can specify an art Layer
 * Doesn't work in batch mode.
 * @param {oDrawing.ART_LAYER}   [artLayer]      activate the given art layer
 * @return {bool}   success of setting the drawing as current
 */
$.oDrawing.prototype.setAsActiveDrawing = function(artLayer){
  if (this.$.batchMode){
    this.$.debug("Setting as active drawing not available in batch mode", this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  var _column = this.element.column;
  if (!_column){
    this.$.debug("Column missing: impossible to set as active drawing "+this.name+" of element "+_element.name, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  var _frame = this.getVisibleFrames();
  if (_frame.length == 0){
    this.$.debug("Drawing not exposed: impossible to set as active drawing "+this.name+" of element "+_element.name, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  DrawingTools.setCurrentDrawingFromColumnName( _column.uniqueName, _frame[0] );

  if (artLayer) DrawingTools.setCurrentArt( artLayer );

  return true;
}


/**
 * Copies the contents of the Drawing into the clipboard
 * @param {oDrawing.ART_LAYER} [artLayer]    Specify to only copy the contents of the specified artLayer
 */
$.oDrawing.prototype.copyContents = function(artLayer){

  var _current = this.setAsActiveDrawing( artLayer );
  if (!_current) {
    this.$.debug("Impossible to copy contents of drawing "+this.name+" of element "+_element.name+", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }
  ToolProperties.setApplyAllArts( !artLayer );
  Action.perform( "deselect()", "cameraView" );
  Action.perform( "onActionChooseSelectTool()" );
  Action.perform( "selectAll()", "cameraView" );

  if (Action.validate("copy()", "cameraView").enabled) Action.perform("copy()", "cameraView");
}


/**
 * Pastes the contents of the clipboard into the Drawing
 * @param {oDrawing.ART_LAYER} [artLayer]    Specify to only paste the contents onto the specified artLayer
 */
$.oDrawing.prototype.pasteContents = function(artLayer){

  var _current = this.setAsActiveDrawing( artLayer );
  if (!_current) {
    this.$.debug("Impossible to copy contents of drawing "+this.name+" of element "+_element.name+", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }
  ToolProperties.setApplyAllArts( !artLayer );
  Action.perform( "deselect()", "cameraView" );
  Action.perform( "onActionChooseSelectTool()" );
  if (Action.validate("paste()", "cameraView").enabled) Action.perform("paste()", "cameraView");
}


 /**
 * Converts the line ends of the Drawing object to the defined type.
 * Doesn't work in batch mode. This function modifies the selection.
 *
 * @param {oDrawing.LINE_END_TYPE}     endType        the type of line ends to set.
 * @param {oDrawing.ART_LAYER}        [artLayer]      only apply to provided art Layer.
 */
$.oDrawing.prototype.setLineEnds = function(endType, artLayer){
  if (this.$.batchMode){
    this.$.debug("setting line ends not available in batch mode", this.DEBUG_LEVEL.ERROR);
    return;
  }

  var _current = this.setAsActiveDrawing( artLayer );
  if (!_current) {
    this.$.debug("Impossible to change line ends on drawing "+this.name+" of element "+_element.name+", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }

  // apply to all arts only if art layer not specified
  ToolProperties.setApplyAllArts( !artLayer );
  Action.perform( "deselect()", "cameraView" );
  Action.perform( "onActionChooseSelectTool()" );
  Action.perform( "selectAll()", "cameraView" );

  var widget = $.getHarmonyUIWidget("pencilShape", "frameBrushParameters");
  if (widget){
    widget.onChangeTipStart( endType );
    widget.onChangeTipEnd( endType );
    widget.onChangeJoin( endType );
  }
  Action.perform("deselect()", "cameraView");
}

 /**
 * Converts the Drawing object to a string of the drawing name.
 * @return: { string }                 The name of the drawing.
 */
$.oDrawing.prototype.toString = function(){
    return this.name;
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oArtLayer class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oArtLayer class.
 * @constructor
 * @classdesc  $.oArtLayer represents art layers, as described by the artlayer toolbar. Access the drawing contents of the layers through this class.
 * @param   {int}                    index                      The artLayerIndex (0: underlay, 1: line art, 2: color art, 3:overlay).
 * @param   {$.oDrawing}             oDrawingObject             The oDrawing this layer belongs to.
 */
$.oArtLayer = function( index , oDrawingObject ){
  this._layerIndex = index;
  this._drawing = oDrawingObject;
  this._key = {drawing: oDrawingObject._key, art:index}
}


/**
 * The shapes contained on the drawing.
 * @name $.oArtLayer#shapes
 * @type {$.oShape[]}
 */
Object.defineProperty( $.oArtLayer.prototype, 'shapes', {
  get : function(){
    var _shapesNum = Drawing.query.getNumberOfLayers(this._key);
    var _shapes = [];
    for (var i=0;i<_shapesNum; i++){
      _shapes.push(new this.$.oShape(i, this));
    }
    return _shapes;
  }
})


/**
 * Removes the contents of the art layer.
 */
$.oArtLayer.prototype.clear = function(){
  return this.name;
}




//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//          $.oShape class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oShape class.
 * @constructor
 * @classdesc  $.oShape represents shapes drawn on the art layer. Strokes, colors, line styles, can be accessed through this class.<br>Warning, Toonboom stores strokes by index, so stroke objects may become obsolete when modifying the contents of the drawing.
 * @param   {int}                    index                      The artLayerIndex (0: underlay, 1: line art, 2: color art, 3:overlay).
 * @param   {$.oArtLayer}            oArtLayerObject            The oArtLayer this layer belongs to.
 */
$.oShape = function( index , oArtLayerObject ){
  this._shapeIndex = index;
  this._drawingLayer = oArtLayerObject;
  var _key = oArtLayerObject._key;
  this._key = {drawing:_key.drawing, art:_key.art, layers:[index]}
}


/**
 * The strokes making up the shape.
 * @name $.oShape#strokes
 * @type {$.oShape[]}
 */
Object.defineProperty( $.oShape.prototype, 'strokes', {
  get : function(){
    var _strokes = Drawing.query.getLayerStrokes(this._key).layers[0].strokes;
    return _strokes;
  }
})


/**
 * WIP Set and retrieve the selected status of each shape.
 * @name $.oShape#selected
 * @type {$.oShape[]}
 */
Object.defineProperty( $.oShape.prototype, 'selected', {
  get : function(){
  },

  set : function(){
  }
})



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oStencil class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oStencil class.
 * @constructor
 * @classdesc  The $.oStencil class allows access to some of the settings, name and type of the stencils available in the Harmony UI. <br>
 * Harmony stencils can have the following types: "pencil", "penciltemplate", "brush", "texture", "bitmapbrush" and "bitmaperaser". Each type is only available to specific tools. <br>
 * Access the main size information of the brush with the mainBrushShape property.
 * @param   {string}   xmlDescription        the part of the penstyles.xml file between <pen> tags that describe a stencils.
 * @property {string}  name                  the display name of the stencil
 * @property {string}  type                  the type of stencil
 * @property {Object}  mainBrushShape        the description of the shape of the stencil
 */
$.oStencil = function(xmlDescription){
  _settings = this.$.oStencil.getSettingsFromXml(xmlDescription);
  this.type = _settings.style;
  for (var i in _settings){
    this[i] = _settings[i];
  }
}


/**
 * Parses the xml string of the stencil xml description to create an object with all the information from it.
 * @private
 */
$.oStencil.getSettingsFromXml = function(xmlString){
  var object = {};
  var objectRE = /<(\w+)>([\S\s]*?)<\/\1>/igm
  var match;
  var string = xmlString+"";
  while (match = objectRE.exec(xmlString)){
    object[match[1]] = this.prototype.$.oStencil.getSettingsFromXml(match[2]);
    // remove the match from the string to parse the rest as properties
    string = string.replace(match[0], "");
  }

  var propsRE = /<(\w+) value="([\S\s]*?)"\/>/igm
  var match;
  while (match = propsRE.exec(string)){
    // try to convert the value to int, float or bool
    var value = match[2];
    var intValue = parseInt(value, 10);
    var floatValue = parseFloat(value);
    if (value == "true" || value == "false"){
      value = !!value
    }else if(!isNaN(floatValue)){
      if(intValue == floatValue){
        value = intValue;
      }else{
        value = floatValue;
      }
    }

    object[match[1]] = match[2];
  }

  return object;
}
