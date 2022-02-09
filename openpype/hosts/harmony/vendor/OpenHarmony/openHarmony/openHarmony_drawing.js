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
$.oDrawing = function (name, oElementObject) {
  this._type = "drawing";
  this._name = name;
  this.element = oElementObject;

  this._key = Drawing.Key({
    elementId: oElementObject.id,
    exposure: name
  });

  //log(JSON.stringify(this._key))

  this._overlay = new this.$.oArtLayer(3, this);
  this._lineArt = new this.$.oArtLayer(2, this);
  this._colorArt = new this.$.oArtLayer(1, this);
  this._underlay = new this.$.oArtLayer(0, this);
  this._artLayers = [this._underlay, this._colorArt, this._lineArt, this._overlay];
}


/**
 * The different types of lines ends.
 * @name $.oDrawing#LINE_END_TYPE
 * @enum
 */
$.oDrawing.LINE_END_TYPE = {
  ROUND: 1,
  FLAT: 2,
  BEVEL: 3
};


/**
 * The reference to the art layers to use with oDrawing.setAsActiveDrawing()
 * @name $.oDrawing#ART_LAYER
 * @enum
 */
$.oDrawing.ART_LAYER = {
  OVERLAY: 8,
  LINEART: 4,
  COLORART: 2,
  UNDERLAY: 1
};


/**
 * The name of the drawing.
 * @name $.oDrawing#name
 * @type {string}
 */
Object.defineProperty($.oDrawing.prototype, 'name', {
  get: function () {
    return this._name;
  },

  set: function (newName) {
    if (this._name == newName) return;

    var _column = this.element.column.uniqueName;
    // this ripples recursively

    if (Drawing.isExists(this.element.id, newName)) this.element.getDrawingByName(newName).name = newName + "_1";
    column.renameDrawing(_column, this._name, newName);
    this._name = newName;
  }
})


/**
 * The internal Id used to identify drawings.
 * @name $.oDrawing#id
 * @readonly
 * @type {int}
 */
Object.defineProperty($.oDrawing.prototype, 'id', {
  get: function () {
    return this._key.drawingId;
  }
})


/**
 * The folder path of the drawing on the filesystem.
 * @name $.oDrawing#path
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oDrawing.prototype, 'path', {
  get: function () {
    return fileMapper.toNativePath(Drawing.filename(this.element.id, this.name))
  }
})


/**
 * The drawing pivot of the drawing.
 * @name $.oDrawing#pivot
 * @type {$.oPoint}
 */
Object.defineProperty($.oDrawing.prototype, 'pivot', {
  get: function () {
    if (this.$.batchMode){
      throw new Error("oDrawing.pivot is not available in batch mode.")
    }

    var _pivot = Drawing.getPivot({ "drawing": this._key });
    return new this.$.oPoint(_pivot.x, _pivot.y, 0);
  },

  set: function (newPivot) {
    var _pivot = { x: newPivot.x, y: newPivot.y };
    Drawing.setPivot({ drawing: this._key, pivot: _pivot });
  }
})


/**
 * The color Ids present on the drawing.
 * @name $.oDrawing#usedColorIds
 * @type {string[]}
 */
Object.defineProperty($.oDrawing.prototype, 'usedColorIds', {
  get: function () {
    var _colorIds = DrawingTools.getDrawingUsedColors(this._key);
    return _colorIds;
  }
})


/**
 * The bounding box of the drawing, in drawing space coordinates. (null if the drawing is empty.)
 * @name $.oDrawing#boundingBox
 * @readonly
 * @type {$.oBox}
 */
Object.defineProperty($.oDrawing.prototype, 'boundingBox', {
  get: function () {
    if (this.$.batchMode){
      throw new Error("oDrawing.boudingBox is not available in batch mode.")
    }

    var _box = new this.$.oBox()
    for (var i in this.artLayers) {
      var _layerBox = this.artLayers[i].boundingBox
      if (_layerBox) _box.include(_layerBox)
    }

    return _box
  }
})


/**
 * Access the underlay art layer's content through this object.
 * @name $.oDrawing#underlay
 * @readonly
 * @type {$.oArtLayer}
 */
Object.defineProperty($.oDrawing.prototype, 'underlay', {
  get: function () {
    return this._underlay;
  }
})


/**
 * Access the color art layer's content through this object.
 * @name $.oDrawing#colorArt
 * @readonly
 * @type {$.oArtLayer}
 */
Object.defineProperty($.oDrawing.prototype, 'colorArt', {
  get: function () {
    return this._colorArt;
  }
})


/**
 * Access the line art layer's content through this object.
 * @name $.oDrawing#lineArt
 * @readonly
 * @type {$.oArtLayer}
 */
Object.defineProperty($.oDrawing.prototype, 'lineArt', {
  get: function () {
    return this._lineArt;
  }
})


/**
 * Access the overlay art layer's content through this object.
 * @name $.oDrawing#overlay
 * @readonly
 * @type {$.oArtLayer}
 */
Object.defineProperty($.oDrawing.prototype, 'overlay', {
  get: function () {
    return this._overlay;
  }
})


/**
 * The list of artLayers of this drawing.
 * @name $.oDrawing#artLayers
 * @readonly
 * @type {$.oArtLayer[]}
 */
Object.defineProperty($.oDrawing.prototype, 'artLayers', {
  get: function () {
    return this._artLayers;
  }
})



/**
 * the shapes contained amongst all artLayers of this drawing.
 * @name $.oDrawing#shapes
 * @readonly
 * @type {$.oShape[]}
 */
Object.defineProperty($.oDrawing.prototype, 'shapes', {
  get: function () {
    var _shapes = [];
    for (var i in this.artLayers) {
      _shapes = _shapes.concat(this.artLayers[i].shapes);
    }

    return _shapes;
  }
})


/**
 * the strokes contained amongst all artLayers of this drawing.
 * @name $.oDrawing#strokes
 * @readonly
 * @type {$.oStroke[]}
 */
Object.defineProperty($.oDrawing.prototype, 'strokes', {
  get: function () {
    var _strokes = [];
    for (var i in this.artLayers) {
      _strokes = _strokes.concat(this.artLayers[i].strokes);
    }

    return _strokes;
  }
})


/**
 * The contours contained amongst all the shapes of the artLayer.
 * @name $.oDrawing#contours
 * @type {$.oContour[]}
 */
 Object.defineProperty($.oDrawing.prototype, 'contours', {
  get: function () {
    var _contours = []

    for (var i in this.artLayers) {
      _contours = _contours.concat(this.artLayers[i].contours)
    }

    return _contours
  }
})



/**
 * the currently active art layer of this drawing.
 * @name $.oDrawing#activeArtLayer
 * @type {$.oArtLayer}
 */
Object.defineProperty($.oDrawing.prototype, 'activeArtLayer', {
  get: function () {
    var settings = Tools.getToolSettings();
    if (!settings.currentDrawing) return null;

    return this.artLayers[settings.activeArt]
  },
  set: function (newArtLayer) {
    var layers = this.$.oDrawing.ART_LAYER
    var index = layers[newArtLayer.name.toUpperCase()]
    this.setAsActiveDrawing(index);
  }
})


/**
 * the selected shapes on this drawing
 * @name $.oDrawing#selectedShapes
 * @type {$.oShape}
 */
Object.defineProperty($.oDrawing.prototype, 'selectedShapes', {
  get: function () {
    var _selectedShapes = [];
    for (var i in this.artLayers) {
      _selectedShapes = _selectedShapes.concat(this.artLayers[i].selectedShapes);
    }

    return _selectedShapes;
  }
})


/**
 * the selected shapes on this drawing
 * @name $.oDrawing#selectedStrokes
 * @type {$.oShape}
 */
Object.defineProperty($.oDrawing.prototype, 'selectedStrokes', {
  get: function () {
    var _selectedStrokes = [];
    for (var i in this.artLayers) {
      _selectedStrokes = _selectedStrokes.concat(this.artLayers[i].selectedStrokes);
    }

    return _selectedStrokes;
  }
})


/**
 * the selected shapes on this drawing
 * @name $.oDrawing#selectedContours
 * @type {$.oShape}
 */
Object.defineProperty($.oDrawing.prototype, 'selectedContours', {
  get: function () {
    var _selectedContours = [];
    for (var i in this.artLayers) {
      _selectedContours = _selectedContours.concat(this.artLayers[i].selectedContours);
    }

    return _selectedContours;
  }
})


/**
 * all the data from this drawing. For internal use.
 * @name $.oDrawing#drawingData
 * @type {Object}
 * @readonly
 * @private
 */
Object.defineProperty($.oDrawing.prototype, 'drawingData', {
  get: function () {
    var _data = Drawing.query.getData({drawing: this._key});
    if (!_data) throw new Error("Data unavailable for drawing "+this.name)
    return _data;
  }
})




// $.oDrawing Class methods

/**
 * Import a given file into an existing drawing.
 * @param   {$.oFile} file                  The path to the file
 * @param   {bool}    [convertToTvg=false]  Wether to convert the bitmap to the tvg format (this doesn't vectorise the drawing)
 *
 * @return { $.oFile }   the oFile object pointing to the drawing file after being it has been imported into the element folder.
 */
$.oDrawing.prototype.importBitmap = function (file, convertToTvg) {
  var _path = new this.$.oFile(this.path);
  if (!(file instanceof this.$.oFile)) file = new this.$.oFile(file);
  if (!file.exists) throw new Error ("Can't import bitmap "+file.path+", file doesn't exist");

  if (convertToTvg && file.extension.toLowerCase() != "tvg"){
    // use utransform binary to perform conversion
    var _bin = specialFolders.bin + "/utransform";

    var tempFolder = this.$.scn.tempFolder;

    var _convertedFilePath = tempFolder.path + "/" + file.name + ".tvg";
    var _convertProcess = new this.$.oProcess(_bin, ["-outformat", "TVG", "-debug", "-scale", "1", "-bboxtvgincrease","0" , "-outfile", _convertedFilePath, file.path]);
    log(_convertProcess.execute())

    var convertedFile = new this.$.oFile(_convertedFilePath);
    if (!convertedFile.exists) throw new Error ("Converting " + file.path + " to TVG has failed.");

    file = convertedFile;
  }

  return file.copy(_path.folder, _path.name, true);
}


/**
 * @returns {int[]}  The frame numbers at which this drawing appears.
 */
$.oDrawing.prototype.getVisibleFrames = function () {
  var _element = this.element;
  var _column = _element.column;

  if (!_column) {
    this.$.debug("Column missing: can't get visible frames for  drawing " + this.name + " of element " + _element.name, this.$.DEBUG_LEVEL.ERROR);
    return null;
  }

  var _frames = [];
  var _keys = _column.keyframes;
  for (var i in _keys) {
    if (_keys[i].value == this.name) _frames.push(_keys[i].frameNumber);
  }

  return _frames;
}


/**
 * Remove the drawing from the element.
 */
$.oDrawing.prototype.remove = function () {
  var _element = this.element;
  var _column = _element.column;

  if (!_column) {
    throw new Error ("Column missing: impossible to delete drawing " + this.name + " of element " + _element.name);
  }

  var _frames = _column.frames;
  var _lastFrame = _frames.pop();

  var _thisDrawing = this;

  // we have to expose the drawing on the column to delete it. Exposing at the last frame...
  this.$.debug("deleting drawing " + _thisDrawing + " from element " + _element.name, this.$.DEBUG_LEVEL.LOG);
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
$.oDrawing.prototype.refreshPreview = function () {
  if (this.element.format == "TVG") return;

  var _path = new this.$.oFile(this.path);
  var _elementFolder = _path.folder;
  var _previewFiles = _elementFolder.getFiles(_path.name + "-*.tga");

  for (var i in _previewFiles) {
    _previewFiles[i].remove();
  }
}


/**
* Change the currently active drawing. Can specify an art Layer
* Doesn't work in batch mode.
* @param {oDrawing.ART_LAYER}   [artLayer]      activate the given art layer
* @return {bool}   success of setting the drawing as current
*/
$.oDrawing.prototype.setAsActiveDrawing = function (artLayer) {
  if (this.$.batchMode) {
    this.$.debug("Setting as active drawing not available in batch mode", this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  var _column = this.element.column;
  if (!_column) {
    this.$.debug("Column missing: impossible to set as active drawing " + this.name + " of element " + _element.name, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  var _frame = this.getVisibleFrames();
  if (_frame.length == 0) {
    this.$.debug("Drawing not exposed: impossible to set as active drawing " + this.name + " of element " + _element.name, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  DrawingTools.setCurrentDrawingFromColumnName(_column.uniqueName, _frame[0]);

  if (artLayer) DrawingTools.setCurrentArt(artLayer);

  return true;
}


/**
 * Duplicates the drawing to the given frame, and renames the drawing with the given name.
 * @param {int}      [frame]     the frame at which to create the drawing. By default, the current frame.
 * @param {string}   [newName]   A new name for the drawing. By default, the name will be the number of the frame.
 * @returns {$.oDrawing}   the newly created drawing
 */
$.oDrawing.prototype.duplicate = function(frame, newName){
  var _element = this.element
  if (typeof frame ==='undefined') var frame = this.$.scn.currentFrame;
  if (typeof newName === 'undefined') var newName = frame;
  var newDrawing = _element.addDrawing(frame, newName, this.path)
  return newDrawing;
}

/**
 * Replaces a color Id present on the drawing by another.
 * @param {string} currentId
 * @param {string} newId
 */
$.oDrawing.prototype.replaceColorId = function (currentId, newId){
  DrawingTools.recolorDrawing( this._key, [{from:currentId, to:newId}]);
}


/**
 * Copies the contents of the Drawing into the clipboard
 * @param {oDrawing.ART_LAYER} [artLayer]    Specify to only copy the contents of the specified artLayer
 */
$.oDrawing.prototype.copyContents = function (artLayer) {

  var _current = this.setAsActiveDrawing(artLayer);
  if (!_current) {
    this.$.debug("Impossible to copy contents of drawing " + this.name + " of element " + _element.name + ", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }
  ToolProperties.setApplyAllArts(!artLayer);
  Action.perform("deselect()", "cameraView");
  Action.perform("onActionChooseSelectTool()");
  Action.perform("selectAll()", "cameraView");

  if (Action.validate("copy()", "cameraView").enabled) Action.perform("copy()", "cameraView");
}


/**
 * Pastes the contents of the clipboard into the Drawing
 * @param {oDrawing.ART_LAYER} [artLayer]    Specify to only paste the contents onto the specified artLayer
 */
$.oDrawing.prototype.pasteContents = function (artLayer) {

  var _current = this.setAsActiveDrawing(artLayer);
  if (!_current) {
    this.$.debug("Impossible to copy contents of drawing " + this.name + " of element " + _element.name + ", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }
  ToolProperties.setApplyAllArts(!artLayer);
  Action.perform("deselect()", "cameraView");
  Action.perform("onActionChooseSelectTool()");
  if (Action.validate("paste()", "cameraView").enabled) Action.perform("paste()", "cameraView");
}


/**
* Converts the line ends of the Drawing object to the defined type.
* Doesn't work in batch mode. This function modifies the selection.
*
* @param {oDrawing.LINE_END_TYPE}     endType        the type of line ends to set.
* @param {oDrawing.ART_LAYER}        [artLayer]      only apply to provided art Layer.
*/
$.oDrawing.prototype.setLineEnds = function (endType, artLayer) {
  if (this.$.batchMode) {
    this.$.debug("setting line ends not available in batch mode", this.DEBUG_LEVEL.ERROR);
    return;
  }

  var _current = this.setAsActiveDrawing(artLayer);
  if (!_current) {
    this.$.debug("Impossible to change line ends on drawing " + this.name + " of element " + _element.name + ", the drawing cannot be set as active.", this.DEBUG_LEVEL.ERROR);
    return;
  }

  // apply to all arts only if art layer not specified
  ToolProperties.setApplyAllArts(!artLayer);
  Action.perform("deselect()", "cameraView");
  Action.perform("onActionChooseSelectTool()");
  Action.perform("selectAll()", "cameraView");

  var widget = $.getHarmonyUIWidget("pencilShape", "frameBrushParameters");
  if (widget) {
    widget.onChangeTipStart(endType);
    widget.onChangeTipEnd(endType);
    widget.onChangeJoin(endType);
  }
  Action.perform("deselect()", "cameraView");
}


/**
* Converts the Drawing object to a string of the drawing name.
* @return: { string }                 The name of the drawing.
*/
$.oDrawing.prototype.toString = function () {
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
$.oArtLayer = function (index, oDrawingObject) {
  this._layerIndex = index;
  this._drawing = oDrawingObject;
  //log(this._drawing._key)
  this._key = { "drawing": this._drawing._key, "art": index }
}


/**
 * The name of the artLayer (lineArt, colorArt, etc)
 * @name $.oArtLayer#name
 * @type {string}
 */
Object.defineProperty($.oArtLayer.prototype, 'name', {
  get: function(){
    var names = ["underlay", "colorArt", "lineArt", "overlay"];
    return names[this._layerIndex];
  }
})


/**
 * The shapes contained on the artLayer.
 * @name $.oArtLayer#shapes
 * @type {$.oShape[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'shapes', {
  get: function () {
    if (!this.hasOwnProperty("_shapes")){
      var _shapesNum = Drawing.query.getNumberOfLayers(this._key);
      var _shapes = [];
      for (var i = 0; i < _shapesNum; i++) {
        _shapes.push(this.getShapeByIndex(i));
      }
      this._shapes = _shapes;
    }
    return this._shapes;
  }
})


/**
 * The strokes contained amongst all the shapes of the artLayer.
 * @name $.oArtLayer#strokes
 * @type {$.oStroke[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'strokes', {
  get: function () {
    var _strokes = [];

    var _shapes = this.shapes;
    for (var i in _shapes) {
      _strokes = _strokes.concat(_shapes[i].strokes);
    }

    return _strokes;
  }
})


/**
 * The contours contained amongst all the shapes of the artLayer.
 * @name $.oArtLayer#contours
 * @type {$.oContour[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'contours', {
  get: function () {
    var _contours = [];

    var _shapes = this.shapes;
    for (var i in _shapes) {
      _contours = _contours.concat(_shapes[i].contours);
    }

    return _contours;
  }
})


/**
 * The bounds of the layer, in drawing space coordinates. (null if the drawing is empty.)
 * @name $.oArtLayer#boundingBox
 * @type {$.oBox}
 */
Object.defineProperty($.oArtLayer.prototype, 'boundingBox', {
  get: function () {
    var _box = Drawing.query.getBox(this._key);
    if (_box.empty) return null;

    var _boundingBox = new $.oBox(_box.x0, _box.y0, _box.x1, _box.y1);
    return _boundingBox;
  }
})


/**
 * the currently selected shapes on the ArtLayer.
 * @name $.oArtLayer#selectedShapes
 * @type {$.oShape[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'selectedShapes', {
  get: function () {
    var _shapes = Drawing.selection.get(this._key).selectedLayers;
    var _artLayer = this;
    return _shapes.map(function (x) { return _artLayer.getShapeByIndex(x) });
  }
})



/**
 * the currently selected strokes on the ArtLayer.
 * @name $.oArtLayer#selectedStrokes
 * @type {$.oStroke[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'selectedStrokes', {
  get: function () {
    var _shapes = this.selectedShapes;
    var _strokes = [];

    for (var i in _shapes) {
      _strokes = _strokes.concat(_shapes[i].strokes);
    }

    return _strokes;
  }
})


/**
 * the currently selected contours on the ArtLayer.
 * @name $.oArtLayer#selectedContours
 * @type {$.oContour[]}
 */
Object.defineProperty($.oArtLayer.prototype, 'selectedContours', {
  get: function () {
    var _shapes = this.selectedShapes;
    var _contours = [];

    for (var i in _shapes) {
      _contours = _contours.concat(_shapes[i].contours);
    }

    return _contours;
  }
})



/**
 * all the data from this artLayer. For internal use.
 * @name $.oArtLayer#drawingData
 * @type {$.oStroke[]}
 * @readonly
 * @private
 */
Object.defineProperty($.oArtLayer.prototype, 'drawingData', {
  get: function () {
    var _data = this._drawing.drawingData
    for (var i in _data.arts){
      if (_data.arts[i].art == this._layerIndex) {
        return _data.arts[i];
      }
    }

    // in case of empty layerArt, return a default object
    return {art:this._layerIndex, artName:this.name, layers:[]};
  }
})


/**
 * Draws a circle on the artLayer.
 * @param {$.oPoint}       center         The center of the circle
 * @param {float}          radius         The radius of the circle
 * @param {$.oLineStyle}   [lineStyle]    Provide a $.oLineStyle object to specify how the line will look
 * @param {object}         [fillStyle=null]    The fill information to fill the circle with.
 * @returns {$.oShape}  the created shape containing the circle.
*/
$.oArtLayer.prototype.drawCircle = function(center, radius, lineStyle, fillStyle){
  if (typeof fillStyle === 'undefined') var fillStyle = null;

  var arg = {
    x: center.x,
    y: center.y,
    radius: radius
  };
  var _path = Drawing.geometry.createCircle(arg);

  return this.drawShape(_path, lineStyle, fillStyle);
}

/**
 * Draws the given path on the artLayer.
 * @param {$.oVertex[]}    path         an array of $.oVertex objects that describe a path.
 * @param {$.oLineStyle}   [lineStyle]  the line style to draw with. (By default, will use the current stencil selection)
 * @param {$.oFillStyle}   [fillStyle]  the fill information for the path. (By default, will use the current palette selection)
 * @param {bool}   [polygon]            Wether bezier handles should be created for the points in the path (ignores "onCurve" properties of oVertex from path)
 * @param {bool}   [createUnderneath]   Wether the new shape will appear on top or underneath the contents of the layer. (not working yet)
 */
$.oArtLayer.prototype.drawShape = function(path, lineStyle, fillStyle, polygon, createUnderneath){
  if (typeof fillStyle === 'undefined') var fillStyle = new this.$.oFillStyle();
  if (typeof lineStyle === 'undefined') var lineStyle = new this.$.oLineStyle();
  if (typeof polygon === 'undefined') var polygon = false;
  if (typeof createUnderneath === 'undefined') var createUnderneath = false;

  var index = this.shapes.length;

  var _lineStyle = {};

  if (lineStyle){
    _lineStyle.pencilColorId = lineStyle.colorId;
    _lineStyle.thickness = {
      "minThickness": lineStyle.minThickness,
      "maxThickness": lineStyle.maxThickness,
      "thicknessPath": 0
    };
  }

  if (fillStyle) _lineStyle.shaderLeft = 0;
  if (polygon) _lineStyle.polygon = true;
  _lineStyle.under = createUnderneath;
  _lineStyle.stroke = !!lineStyle;

  var strokeDesciption = _lineStyle;
  strokeDesciption.path = path;
  strokeDesciption.closed = !!fillStyle;

  var shapeDescription = {}
  if (fillStyle) shapeDescription.shaders = [{ colorId : fillStyle.colorId }]
  shapeDescription.strokes = [strokeDesciption]
  if (lineStyle) shapeDescription.thicknessPaths = [lineStyle.stencil.thicknessPath]

  var config = {
    label: "draw shape",
    drawing: this._key.drawing,
    art: this._key.art,
    layers: [shapeDescription]
  };


  var layers = DrawingTools.createLayers(config);

  var newShape = this.getShapeByIndex(index);
  this._shapes.push(newShape);
  return newShape;
};


/**
 * Draws the given path on the artLayer.
 * @param {$.oVertex[]}    path          an array of $.oVertex objects that describe a path.
 * @param {$.oLineStyle}   lineStyle     the line style to draw with.
 * @returns {$.oShape} the shape containing the added stroke.
 */
$.oArtLayer.prototype.drawStroke = function(path, lineStyle){
  return this.drawShape(path, lineStyle, null);
};


/**
 * Draws the given path on the artLayer as a contour.
 * @param {$.oVertex[]}    path          an array of $.oVertex objects that describe a path.
 * @param {$.oFillStyle}   fillStyle     the fill style to draw with.
 * @returns {$.oShape} the shape newly created from the path.
 */
$.oArtLayer.prototype.drawContour = function(path, fillStyle){
  return this.drawShape(path, null, fillStyle);
};


/**
 * Draws a rectangle on the artLayer.
 * @param {float}        x          the x coordinate of the top left corner.
 * @param {float}        y          the y coordinate of the top left corner.
 * @param {float}        width      the width of the rectangle.
 * @param {float}        height     the height of the rectangle.
 * @param {$.oLineStyle} lineStyle  a line style to use for the rectangle stroke.
 * @param {$.oFillStyle} fillStyle  a fill style to use for the rectange fill.
 * @returns {$.oShape} the shape containing the added stroke.
 */
$.oArtLayer.prototype.drawRectangle = function(x, y, width, height, lineStyle, fillStyle){
  if (typeof fillStyle === 'undefined') var fillStyle = null;

  var path = [
    {x:x,y:y,onCurve:true},
    {x:x+width,y:y,onCurve:true},
    {x:x+width,y:y-height,onCurve:true},
    {x:x,y:y-height,onCurve:true},
    {x:x,y:y,onCurve:true}
  ];

  return this.drawShape(path, lineStyle, fillStyle);
}



/**
 * Draws a line on the artLayer
 * @param {$.oPoint}     startPoint
 * @param {$.oPoint}     endPoint
 * @param {$.oLineStyle} lineStyle
 * @returns {$.oShape} the shape containing the added line.
 */
$.oArtLayer.prototype.drawLine = function(startPoint, endPoint, lineStyle){
  var path = [{x:startPoint.x,y:startPoint.y,onCurve:true},{x:endPoint.x,y:endPoint.y,onCurve:true}];

  return this.drawShape(path, lineStyle, null);
}


/**
 * Removes the contents of the art layer.
 */
$.oArtLayer.prototype.clear = function(){
  var _shapes = this.shapes;
  this.$.debug(_shapes, this.$.DEBUG_LEVEL.DEBUG);
  for (var i=_shapes.length - 1; i>=0; i--){
    _shapes[i].remove();
  }
}


/**
 * get a shape from the artLayer by its index
 * @param {int} index
 *
 * @return {$.oShape}
 */
$.oArtLayer.prototype.getShapeByIndex = function (index) {
  return new this.$.oShape(index, this);
}


/**
 * @private
 */
$.oArtLayer.prototype.toString = function(){
  return "Object $.oArtLayer ["+this.name+"]";
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oLineStyle class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oLineStyle class.
 * @constructor
 * @classdesc
 * The $.oLineStyle class describes a lineStyle used to describe the appearance of strokes and perform drawing operations. <br>
 * Initializing a $.oLineStyle without any parameters attempts to get the current pencil thickness settings and color.
 * @param {string}     colorId             the color Id to paint the line with.
 * @param {$.oStencil} stencil             the stencil object representing the thickness keys
 */
$.oLineStyle = function (colorId, stencil) {
  if (typeof minThickness === 'undefined') var minThickness = PenstyleManager.getCurrentPenstyleMinimumSize();
  if (typeof maxThickness === 'undefined') {
    var maxThickness = PenstyleManager.getCurrentPenstyleMaximumSize();
    if (!maxThickness && !minThickness) maxThickness = 1;
  }
  if (typeof stencil === 'undefined') {
    var stencil = new $.oStencil("", "pencil", {maxThickness:maxThickness, minThickness:minThickness, keys:[]});
  }

  if (typeof colorId === 'undefined'){
    var _palette = this.$.scn.selectedPalette;
    if (_palette) {
      var _color = this.$.scn.selectedPalette.currentColor;
      if (_color) {
        var colorId = _color.id;
      } else{
        var colorId = "0000000000000003";
      }
    }
  }

  this.colorId = colorId;
  this.stencil = stencil;

  // this.$.debug(colorId+" "+minThickness+" "+maxThickness+" "+stencil, this.$.DEBUG_LEVEL.DEBUG)
}


/**
 * The minimum thickness of the line using this lineStyle
 * @name $.oLineStyle#minThickness
 * @type {float}
 */
Object.defineProperty($.oLineStyle.prototype, "minThickness", {
  get: function(){
    return this.stencil.minThickness;
  },

  set: function(newMinThickness){
    this.stencil.minThickness = newMinThickness;
  }
})


/**
 * The minimum thickness of the line using this lineStyle
 * @name $.oLineStyle#maxThickness
 * @type {float}
 */
Object.defineProperty($.oLineStyle.prototype, "maxThickness", {
  get: function(){
    return this.stencil.maxThickness;
  },

  set: function(newMaxThickness){
    this.stencil.maxThickness = newMaxThickness;
  }
})


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
 * The constructor for the $.oShape class. These types of objects are not supported for harmony versions < 16
 * @constructor
 * @classdesc  $.oShape represents shapes drawn on the art layer. Strokes, colors, line styles, can be accessed through this class.<br>Warning, Toonboom stores strokes by index, so stroke objects may become obsolete when modifying the contents of the drawing.
 * @param   {int}                    index                      The index of the shape on the artLayer
 * @param   {$.oArtLayer}            oArtLayerObject            The oArtLayer this layer belongs to.
 *
 * @property {int}          index       the index of the shape in the parent artLayer
 * @property {$.oArtLayer}  artLayer    the art layer that contains this shape
 */
$.oShape = function (index, oArtLayerObject) {
  this.index = index;
  this.artLayer = oArtLayerObject;
}


/**
 * the toonboom key object identifying this shape.
 * @name $.oShape#_key
 * @type {object}
 * @private
 * @readonly
 */
Object.defineProperty($.oShape.prototype, '_key', {
  get: function () {
    var _key = this.artLayer._key;
    return { drawing: _key.drawing, art: _key.art, layers: [this.index] };
  }
})


/**
 * The underlying data describing the shape.
 * @name $.oShape#_data
 * @type {$.oShape[]}
 * @readonly
 * @private
 */
Object.defineProperty($.oShape.prototype, '_data', {
  get: function () {
    return this.artLayer.drawingData.layers[this.index];
  }
})


/**
 * The strokes making up the shape.
 * @name $.oShape#strokes
 * @type {$.oShape[]}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'strokes', {
  get: function () {
    if (!this.hasOwnProperty("_strokes")) {
      var _data = this._data;

      if (!_data.hasOwnProperty("strokes")) return [];

      var _shape = this;
      var _strokes = _data.strokes.map(function (x, idx) { return new _shape.$.oStroke(idx, x, _shape) })
      this._strokes = _strokes;
    }
    return this._strokes;
  }
})


/**
 * The contours (invisible strokes that can delimit colored areas) making up the shape.
 * @name $.oShape#contours
 * @type {$.oContour[]}
 * @readonly
 */
 Object.defineProperty($.oShape.prototype, 'contours', {
  get: function () {
    if (!this.hasOwnProperty("_contours")) {
      var _data = this._data

      if (!_data.hasOwnProperty("contours")) return [];

      var _shape = this;
      var _contours = _data.contours.map(function (x, idx) { return new this.$.oContour(idx, x, _shape) })
      this._contours = _contours;
    }
    return this._contours;
  }
})


/**
 * The fills styles contained in the shape
 * @name $.oShape#fills
 * @type {$.oFillStyle[]}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'fills', {
  get: function () {
    if (!this.hasOwnProperty("_fills")) {
      var _data = this._data

      if (!_data.hasOwnProperty("contours")) return [];

      var _fills = _data.contours.map(function (x) { return new this.$.oFillStyle(x.colorId, x.matrix) })
      this._fills = _fills;
    }
    return this._fills;
  }
})

/**
 * The stencils used by the shape.
 * @name $.oShape#stencils
 * @type {$.oStencil[]}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'stencils', {
  get: function () {
    if (!this.hasOwnProperty("_stencils")) {
      var _data = this._data;
      var _shape = this;
      var _stencils = _data.thicknessPaths.map(function (x) { return new _shape.$.oStencil("", "pencil", x) })
      this._stencils = _stencils;
    }
    return this._stencils;
  }
})


/**
 * The bounding box of the shape.
 * @name $.oShape#bounds
 * @type {$.oBox}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'bounds', {
  get: function () {
    var _bounds = new this.$.oBox();
    var _contours = this.contours;
    var _strokes = this.strokes;

    for (var i in _contours){
      _bounds.include(_contours[i].bounds);
    }

    for (var i in _strokes){
      _bounds.include(_strokes[i].bounds);
    }

    return _bounds;
  }
})

/**
 * The x coordinate of the shape.
 * @name $.oShape#x
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'x', {
  get: function () {
    return this.bounds.left;
  }
})


/**
 * The x coordinate of the shape.
 * @name $.oShape#x
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'y', {
  get: function () {
    return this.bounds.top;
  }
})


/**
 * The width of the shape.
 * @name $.oShape#width
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'width', {
  get: function () {
    return this.bounds.width;
  }
})


/**
 * The height coordinate of the shape.
 * @name $.oShape#height
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oShape.prototype, 'height', {
  get: function () {
    return this.bounds.height;
  }
})


/**
 * Retrieve and set the selected status of each shape.
 * @name $.oShape#selected
 * @type {bool}
 */
Object.defineProperty($.oShape.prototype, 'selected', {
  get: function () {
    var _selection = this.artLayer._selectedShapes;
    var _indices = _selection.map(function (x) { return x.index });
    return (_indices.indexOf(this.index) != -1)
  },
  set: function (newSelectedState) {
    var _key = this.artLayer._key;

    var currentSelection = Drawing.selection.get(_key);
    var config = {drawing:_key.drawing, art:_key.art};

    if (newSelectedState){
      // adding elements to selection
      config.selectedLayers = currentSelection.selectedLayers.concat([this.index]);
      config.selectedStrokes = currentSelection.selectedStrokes;
    }else{
      config.selectedLayers = currentSelection.selectedLayers;
      config.selectedStrokes = currentSelection.selectedStrokes;

      // remove current element from selection before setting again
      for (var i=config.selectedLayers.length-1; i>=0; i--){
        if (config.selectedLayers[i] == this.index) config.selectedLayers.splice(i, 1);
      }
      for (var i=config.selectedStrokes.length-1; i>=0; i--){
        if (config.selectedStrokes[i].layer == this.index) config.selectedStrokes.splice(i, 1);
      }
    }

    Drawing.selection.set(config);
  }
})


/**
 * Deletes the shape from its artlayer.
 * Updates the index of all other oShapes on the artLayer in order to
 * keep tracking all of them without having to query the drawing again.
 */
$.oShape.prototype.remove = function(){
  DrawingTools.deleteLayers(this._key);

  // update shapes list for this artLayer
  var shapes = this.artLayer.shapes
  for (var i in shapes){
    if (i > this.index){
      shapes[i].index--;
    }
  }
  shapes.splice(this.index, 1);
}


/**
 * Deletes the shape from its artlayer.
 * Warning : Because shapes are referenced by index, deleting a shape
 * that isn't at the end of the list of shapes from this layer
 * might render other shape objects from this layer obsolete.
 * Get them again with artlayer.shapes.
 * @deprecated use oShape.remove instead
 */
$.oShape.prototype.deleteShape = function(){
  this.remove();
}


/**
 * Gets a stroke from this shape by its index
 * @param {int} index
 *
 * @returns {$.oStroke}
 */
$.oShape.prototype.getStrokeByIndex = function (index) {
  return this.strokes[index];
}


$.oShape.prototype.toString = function (){
  return "<oShape index:"+this.index+", layer:"+this.artLayer.name+", drawing:'"+this.artLayer._drawing.name+"'>"
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oFillStyle class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oFillStyle class.
 * @constructor
 * @classdesc
 * The $.oFillStyle class describes a fillStyle used to describe the appearance of filled in color areas and perform drawing operations. <br>
 * Initializing a $.oFillStyle without any parameters attempts to get the current color id.
 * @param {string}     colorId             the color Id to paint the line with.
 * @param {object}     fillMatrix
 */
$.oFillStyle = function (colorId, fillMatrix) {
  if (typeof fillMatrix === 'undefined') var fillMatrix = {
    "ox": 1,
    "oy": 1,
    "xx": 1,
    "xy": 0,
    "yx": 0,
    "yy": 1
  }

  if (typeof colorId === 'undefined'){
    var _palette = this.$.scn.selectedPalette;
    if (_palette) {
      var _color = this.$.scn.selectedPalette.currentColor;
      if (_color) {
        var colorId = _color.id;
      } else{
        var colorId = "0000000000000003";
      }
    }
  }

  this.colorId = colorId;
  this.fillMatrix = fillMatrix;

  this.$.log("new fill created: " + colorId + " " + JSON.stringify(this.fillMatrix))
}


$.oFillStyle.prototype.toString = function(){
  return "<oFillStyle colorId:"+this.colorId+", matrix:"+JSON.stringify(this.fillMatrix)+">";
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oStroke class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oStroke class. These types of objects are not supported for harmony versions < 16
 * @constructor
 * @classdesc  The $.oStroke class models the strokes that make up the shapes visible on the Drawings.
 * @param {int}       index             The index of the stroke in the shape.
 * @param {object}    strokeObject      The stroke object descriptor that contains the info for the stroke
 * @param {oShape}    oShapeObject      The parent oShape
 *
 * @property {int}          index       the index of the stroke in the parent shape
 * @property {$.oShape}     shape       the shape that contains this stroke
 * @property {$.oArtLayer}  artLayer    the art layer that contains this stroke
 */
$.oStroke = function (index, strokeObject, oShapeObject) {
  this.index = index;
  this.shape = oShapeObject;
  this.artLayer = oShapeObject.artLayer;
  this._data = strokeObject;
}


/**
 * The $.oVertex (including bezier handles) making up the complete path of the stroke.
 * @name $.oStroke#path
 * @type {$.oVertex[]}
 * @readonly
 */
Object.defineProperty($.oStroke.prototype, "path", {
  get: function () {
    // path vertices get cached
    if (!this.hasOwnProperty("_path")){
      var _stroke = this;
      var _path = this._data.path.map(function(point, index){
        return new _stroke.$.oVertex(_stroke, point.x, point.y, point.onCurve, index);
      })

      this._path = _path;
    }
    return this._path;
  }
})


/**
 * The oVertex that are on the stroke (Bezier handles exluded.)
 * The first is repeated at the last position when the stroke is closed.
 * @name $.oStroke#points
 * @type {$.oVertex[]}
 * @readonly
 */
Object.defineProperty($.oStroke.prototype, "points", {
  get: function () {
    return this.path.filter(function(x){return x.onCurve});
  }
})


/**
 * The segments making up the stroke. Each segment is a slice of the path, starting and stopping with oVertex present on the curve, and includes the bezier handles oVertex.
 * @name $.oStroke#segments
 * @type {$.oVertex[][]}
 * @readonly
 */
Object.defineProperty($.oStroke.prototype, "segments", {
  get: function () {
    var _points = this.points;
    var _path = this.path;
    var _segments = [];

    for (var i=0; i<_points.length-1; i++){
      var _indexStart = _points[i].index;
      var _indexStop = _points[i+1].index;
      var _segment = _path.slice(_indexStart, _indexStop+1);
      _segments.push(_segment);
    }

    return _segments;
  }
})


/**
 * The index of the stroke in the shape
 * @name $.oStroke#index
 * @type {int}
 */
Object.defineProperty($.oStroke.prototype, "index", {
  get: function () {
    this.$.debug("stroke object : "+JSON.stringify(this._stroke, null, "  "), this.$.DEBUG_LEVEL.DEBUG);
    return this._data.strokeIndex;
  }
})


/**
 * The style of the stroke. null if the stroke is invisible
 * @name $.oStroke#style
 * @type {$.oLineStyle}
 */
Object.defineProperty($.oStroke.prototype, "style", {
  get: function () {
    if (this._data.invisible){
      return null;
    }
    var _colorId = this._data.pencilColorId;
    var _stencil = this.shape.stencils[this._data.thickness];

    return new this.$.oLineStyle(_colorId, _stencil);
  }
})


/**
 * wether the stroke is a closed shape.
 * @name $.oStroke#closed
 * @type {bool}
 */
Object.defineProperty($.oStroke.prototype, "closed", {
  get: function () {
    var _path = this.path;
    $.log(_path)
    $.log(_path[_path.length-1].strokePosition)
    return _path[_path.length-1].strokePosition == 0;
  }
})


/**
 * The bounding box of the stroke.
 * @name $.oStroke#bounds
 * @type {$.oBox}
 * @readonly
 */
 Object.defineProperty($.oStroke.prototype, 'bounds', {
  get: function () {
    var _bounds = new this.$.oBox();
    // since Harmony doesn't allow natively to calculate the bounding box of a string,
    // we convert the bezier into a series of points and calculate the box from it
    var points = Drawing.geometry.discretize({precision: 1, path : this.path});
    for (var j in points){
      var point = points [j]
      var pointBox = new this.$.oBox(point.x, point.y, point.x, point.y);
      _bounds.include(pointBox);
    }
    return _bounds;
  }
})


/**
 * The intersections on this stroke. Each intersection is an object with stroke ($.oStroke), point($.oPoint), strokePoint(float) and ownPoint(float)
 * One of these objects describes an intersection by giving the stroke it intersects with, the coordinates of the intersection and two values which represent the place on the stroke at which the point is placed, with a value between 0 (start) and 1(end)
 * @param  {$.oStroke}   [stroke]       Specify a stroke to find intersections specific to it. If no stroke is specified,
 * @return {Object[]}
 * @example
// get the selected strokes on the active drawing
var sel = $.scn.activeDrawing.selectedStrokes;

for (var i in sel){
  // get intersections with all other elements of the drawing
	var intersections = sel[i].getIntersections();

  for (var j in intersections){
    log("intersection : " + j);
    log("point : " + intersections[j].point);                    // the point coordinates
    log("strokes index : " + intersections[j].stroke.index);     // the index of the intersecting strokes in their own shape
    log("own point : " + intersections[j].ownPoint);             // how far the intersection is on the stroke itself
    log("stroke point : " + intersections[j].strokePoint);       // how far the intersection is on the intersecting stroke
  }
}
 */
$.oStroke.prototype.getIntersections = function (stroke){
  if (typeof stroke !== 'undefined'){
    // get intersection with provided stroke only
    var _key = { "path0": [{ path: this.path }], "path0": [{ path: stroke.path }] };
    var intersections = Drawing.query.getIntersections(_key)[0];
  }else{
    // get all intersections on the stroke
    var _drawingKey = this.artLayer._key;
    var _key = { "drawing": _drawingKey.drawing, "art": _drawingKey.art, "paths": [{ path: this.path }] };
    var intersections = Drawing.query.getIntersections(_key)[0];
  }

  var result = [];
  for (var i in intersections) {
    var _shape = this.artLayer.getShapeByIndex(intersections[i].layer);
    var _stroke = _shape.getStrokeByIndex(intersections[i].strokeIndex);

    for (var j in intersections[i].intersections){
      var points = intersections[i].intersections[j];

      var point = new this.$.oVertex(this, points.x0, points.y0, true);
      var intersection = { stroke: _stroke, point: point, ownPoint: points.t0, strokePoint: points.t1 };

      result.push(intersection);
    }
  }

  return result;
}



/**
 * Adds points on the stroke without moving them, at the distance specified (0=start vertice, 1=end vertice)
 * @param   {float[]}       pointsToAdd     an array of float value between 0 and the number of current points on the curve
 * @returns {$.oVertex[]}   the points that were created (if points already existed, they will be returned)
 * @example
// get the selected stroke and create points where it intersects with the other two strokes
var sel = $.scn.activeDrawing.selectedStrokes[0];

var intersections = sel.getIntersections();

// get the two intersections
var intersection1 = intersections[0];
var intersection2 = intersections[1];

// add the points at the intersections on the intersecting strokes
intersection1.stroke.addPoints([intersection1.strokePoint]);
intersection2.stroke.addPoints([intersection2.strokePoint]);

// add the points on the stroke
sel.addPoints([intersection1.ownPoint, intersection2.ownPoint]);
*/
$.oStroke.prototype.addPoints = function (pointsToAdd) {
  // calculate the points that will be created
  var points = Drawing.geometry.insertPoints({path:this._data.path, params : pointsToAdd});

  // find the newly added points amongst the returned values
  for (var i in this.path){
    var pathPoint = this.path[i];

    // if point is found in path, it's not newly created
    for (var j = points.length-1; j >=0; j--){
      var point = points[j];
      if (point.x == pathPoint.x && point.y == pathPoint.y) {
        points.splice(j, 1);
        break
      }
    }
  }

  // actually add the points
  var config = this.artLayer._key;
  config.label = "addPoint";
  config.strokes = [{layer:this.shape.index, strokeIndex:this.index, insertPoints: pointsToAdd }];

  DrawingTools.modifyStrokes(config);
  this.updateDefinition();

  var newPoints = [];
  // find the points for the coordinates from the new path
  for (var i in points){
    var point = points[i];

    for (var j in this.path){
      var pathPoint = this.path[j];
      if (point.x == pathPoint.x && point.y == pathPoint.y) newPoints.push(pathPoint);
    }
  }

  if (newPoints.length != pointsToAdd.length) throw new Error ("some points in " + pointsToAdd + " were not created.");
  return newPoints;
}


/**
 * fetch the stroke information again to update it after modifications.
 * @returns {object} the data definition of the stroke, for internal use.
 */
$.oStroke.prototype.updateDefinition = function(){
  var _key = this.artLayer._key;
  var strokes = Drawing.query.getStrokes(_key);
  this._data = strokes.layers[this.shape.index].strokes[this.index];

  // remove cache for path
  delete this._path;

  return this._data;
}


/**
 * Gets the closest position of the point on the stroke (float value) from a point with x and y coordinates.
 * @param {oPoint}  point
 * @return {float}  the strokePosition of the point on the stroke (@see $.oVertex#strokePosition)
 */
$.oStroke.prototype.getPointPosition = function(point){
  var arg = {
    path : this.path,
    points: [{x:point.x, y:point.y}]
  }
  var strokePoint = Drawing.geometry.getClosestPoint(arg)[0].closestPoint;
  if (!strokePoint) return 0; // the only time this fails is when the point is the origin of the stroke

  return strokePoint.t;
}


/**
 * Get the coordinates of the point on the stroke from its strokePosition (@see $.oVertex#strokePosition).
 * Only works until a distance of 600 drawing vector units.
 * @param {float}  position
 * @return {$.oPoint} an oPoint object containing the coordinates.
 */
$.oStroke.prototype.getPointCoordinates = function(position){
  var arg = {
    path : this.path,
    params : [ position ]
  };
  var point = Drawing.geometry.evaluate(arg)[0];

  return new $.oPoint(point.x, point.y);
}


/**
 * projects a point onto a stroke and returns the closest point belonging to the stroke.
 * Only works until a distance of 600 drawing vector units.
 * @param {$.oPoint} point
 * @returns {$.oPoint}
 */
$.oStroke.prototype.getClosestPoint = function (point){
  var arg = {
    path : this.path,
    points: [{x:point.x, y:point.y}]
  };

  // returns an array of length 1 with an object containing
  // the original query and a "closestPoint" key that contains the information.
  var _result = Drawing.geometry.getClosestPoint(arg)[0];

  return new $.oPoint(_result.closestPoint.x, _result.closestPoint.y);
}


/**
 * projects a point onto a stroke and returns the distance between the point and the stroke.
 * Only works until a distance of 600 drawing vector units.
 * @param {$.oPoint} point
 * @returns {float}
 */
$.oStroke.prototype.getPointDistance = function (point){
  var arg = {
    path : this.path,
    points: [{x:point.x, y:point.y}]
  };

  // returns an array of length 1 with an object containing
  // the original query and a "closestPoint" key that contains the information.
  var _result = Drawing.geometry.getClosestPoint(arg)[0].closestPoint;

  return _result.distance;
}


/**
 * @private
 */
$.oStroke.prototype.toString = function(){
  return "<oStroke: path:"+this.path+">"
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oContour class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oContour class. These types of objects are not supported for harmony versions < 16
 * @constructor
 * @classdesc  The $.oContour class models the strokes that make up the shapes visible on the Drawings.<br>
 * $.oContour is a subclass of $.oSroke and shares its properties, but represents a stroke with a fill.
 * @extends $.oStroke
 * @param {int}       index             The index of the contour in the shape.
 * @param {object}    contourObject     The stroke object descriptor that contains the info for the stroke
 * @param {oShape}    oShapeObject      The parent oShape
 *
 * @property {int}          index       the index of the stroke in the parent shape
 * @property {$.oShape}     shape       the shape that contains this stroke
 * @property {$.oArtLayer}  artLayer    the art layer that contains this stroke
 */
$.oContour = function (index, contourObject, oShapeObject) {
  this.$.oStroke.call(this, index, contourObject, oShapeObject)
}
$.oContour.prototype = Object.create($.oStroke.prototype)


/**
 * The information about the fill of this contour
 * @name $.oContour#fill
 * @type {$.oFillStyle}
 */
Object.defineProperty($.oContour.prototype, "fill", {
  get: function () {
    var _data = this._data;
    return new this.$.oFillStyle(_data.colorId, _data.matrix);
  }
})


/**
 * The bounding box of the contour.
 * @name $.oContour#bounds
 * @type {$.oBox}
 * @readonly
 */
 Object.defineProperty($.oContour.prototype, 'bounds', {
  get: function () {
    var _data = this._data;
    var _box = _data.box;
    var _bounds = new this.$.oBox(_box.x0,_box.y0, _box.x1, _box.y1);
    return _bounds;
  }
})

/**
 * @private
 */
$.oContour.prototype.toString = function(){
  return "<oContour path:"+this.path+", fill:"+fill+">"
}




//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oVertex class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oVertex class
 * @constructor
 * @classdesc
 * The $.oVertex class represents a single control point on a stroke. This class is used to get the index of the point in the stroke path sequence, as well as its position as a float along the stroke's length.
 * The onCurve property describes wether this control point is a bezier handle or a point on the curve.
 *
 * @param {$.oStroke} stroke   the stroke that this vertex belongs to
 * @param {float}     x        the x coordinate of the vertex, in drawing space
 * @param {float}     y        the y coordinate of the vertex, in drawing space
 * @param {bool}      onCurve  whether the point is a bezier handle or situated on the curve
 * @param {int}       index    the index of the point on the stroke
 *
 * @property {$.oStroke} stroke    the stroke that this vertex belongs to
 * @property {float}     x         the x coordinate of the vertex, in drawing space
 * @property {float}     y         the y coordinate of the vertex, in drawing space
 * @property {bool}      onCurve   whether the point is a bezier handle or situated on the curve
 * @property {int}       index     the index of the point on the stroke
 */
$.oVertex = function(stroke, x, y, onCurve, index){
  if (typeof onCurve === 'undefined') var onCurve = false;
  if (typeof index === 'undefined') var index = stroke.getPointPosition({x:x, y:y});

  this.x = x;
  this.y = y;
  this.onCurve = onCurve;
  this.stroke = stroke;
  this.index = index
}


/**
 * The position of the point on the curve, from 0 to the maximum number of points
 * @name $.oVertex#strokePosition
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVertex.prototype, 'strokePosition', {
  get: function(){
    var _position = this.stroke.getPointPosition(this);
    return _position;
  }
})


/**
 * The position of the point on the drawing, as an oPoint
 * @name $.oVertex#position
 * @type {oPoint}
 * @readonly
 */
Object.defineProperty($.oVertex.prototype, 'position', {
  get: function(){
    var _position = new this.$.oPoint(this.x, this.y, 0);
    return _position;
  }
})


/**
 * The angle of the curve going through this vertex, compared to the x axis, counterclockwise.
 * (In degrees, or null if the stroke is open ended on the right.)
 * @name $.oVertex#angleRight
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVertex.prototype, 'angleRight', {
  get: function(){
    var _index = this.index+1;
    var _path = this.stroke.path;

    // get the next point by looping around if the stroke is closed
    if (_index >= _path.length){
      if (this.stroke.closed){
        var _nextPoint = _path[1];
      }else{
        return null;
      }
    }else{
      var _nextPoint = _path[_index];
    }

    var vector = this.$.oVector.fromPoints(this, _nextPoint);
    var angle = vector.degreesAngle;
    // if (angle < 0) angle += 360 //ensuring only positive values
    return angle
  }
})


/**
 * The angle of the line or bezier handle on the left of this vertex, compared to the x axis, counterclockwise.
 * (In degrees, or null if the stroke is open ended on the left.)
 * @name $.oVertex#angleLeft
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVertex.prototype, 'angleLeft', {
  get: function(){
    var _index = this.index-1;
    var _path = this.stroke.path;

    // get the next point by looping around if the stroke is closed
    if (_index < 0){
      if (this.stroke.closed){
        var _nextPoint = _path[_path.length-2]; //first and last points are the same when the stroke is closed
      }else{
        return null;
      }
    }else{
      var _nextPoint = _path[_index];
    }

    var vector = this.$.oVector.fromPoints(_nextPoint, this);
    var angle = vector.degreesAngle;
    // if (angle < 0) angle += 360 //ensuring only positive values
    return angle
  }
})


/**
 * @private
 */
$.oVertex.prototype.toString = function(){
 return "oVertex : { index:"+this.index+", x: "+this.x+", y: "+this.y+", onCurve: "+this.onCurve+", strokePosition: "+this.strokePosition+" }"
}



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
 * @property {Object}  thicknessPathObject   the description of the shape of the stencil
 */
$.oStencil = function (name, type, thicknessPathObject) {
  this.name = name;
  this.type = type;
  this.thicknessPathObject = thicknessPathObject;
  // log("thicknessPath: " + JSON.stringify(this.thicknessPathObject))
}


/**
 * The minimum thickness of the line using this stencil
 * @name $.oStencil#minThickness
 * @type {float}
 */
Object.defineProperty($.oStencil.prototype, "minThickness", {
  get: function(){
    return this.thicknessPathObject.minThickness;
  },
  set: function(newMinThickness){
    this.thicknessPathObject.minThickness = newMinThickness;
    // TODO: also change in thicknessPath.keys
  }
})


/**
 * The maximum thickness of the line using this stencil
 * @name $.oStencil#maxThickness
 * @type {float}
 */
Object.defineProperty($.oStencil.prototype, "maxThickness", {
  get: function(){
    return this.thicknessPathObject.maxThickness;
  },
  set: function(newMaxThickness){
    this.thicknessPathObject.maxThickness = newMaxThickness;
    // TODO: also change in thicknessPath.keys
  }
})


/**
 * Parses the xml string of the stencil xml description to create an object with all the information from it.
 * @private
 */
$.oStencil.getFromXml = function (xmlString) {
  var object = this.prototype.$.oStencil.getSettingsFromXml(xmlString)

  var maxThickness = object.mainBrushShape.sizeRange.maxValue
  var minThickness = object.mainBrushShape.sizeRange.minPercentage * maxThickness

  var thicknessPathObject = {
    maxThickness:maxThickness,
    minThickness:minThickness,
    keys: [
      {t:0},
      {t:1}
    ]
  }

  var _stencil = new this.$.oStencil(object.name, object.style, thicknessPathObject)
  for (var i in object) {
    try{
      // attempt to set values from the object
      _stencil[i] = _settings[i];
    }catch(err){
      this.$.log(err)
    }
  }
  return _stencil;
}


/**
 * Parses the xml string of the stencil xml description to create an object with all the information from it.
 * @private
 */
$.oStencil.getSettingsFromXml = function (xmlString) {
  var object = {};
  var objectRE = /<(\w+)>([\S\s]*?)<\/\1>/igm
  var match;
  var string = xmlString + "";
  while (match = objectRE.exec(xmlString)) {
    object[match[1]] = this.prototype.$.oStencil.getSettingsFromXml(match[2]);
    // remove the match from the string to parse the rest as properties
    string = string.replace(match[0], "");
  }

  var propsRE = /<(\w+) value="([\S\s]*?)"\/>/igm
  var match;
  while (match = propsRE.exec(string)) {
    // try to convert the value to int, float or bool
    var value = match[2];
    var intValue = parseInt(value, 10);
    var floatValue = parseFloat(value);
    if (value == "true" || value == "false") {
      value = !!value;
    } else if (!isNaN(floatValue)) {
      if (intValue == floatValue) {
        value = intValue;
      } else {
        value = floatValue;
      }
    }

    object[match[1]] = match[2];
  }

  return object;
}

$.oStencil.prototype.toString = function (){
  return "$.oStencil: '" + this.name + "'"
}