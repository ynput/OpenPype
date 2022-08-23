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
//          $.oColumn class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oColumn class.
 * @classdesc  Columns are the objects that hold all the animation information of an attribute. Any animated value in Harmony is so thanks to a column linked to the attribute representing the node parameter. Columns can be added from the scene class, or are directly created when giving a non 1 value when setting an attribute.
 * @constructor
 * @param   {string}                   uniqueName                  The unique name of the column.
 * @param   {$.oAttribute}             oAttributeObject            The oAttribute thats connected to the column.
 *
 * @property {string}                  uniqueName                  The unique name of the column.
 * @property {$.oAttribute}            attributeObject             The attribute object that the column is attached to.
 * @example
 * // You can get the entirety of the columns in the scene by calling:
 * var doc = $.scn;
 * var allColumns = doc.columns;
 *
 * // However, to get a specific column, you can retrieve it from its linked attribute:
 *
 * var myAttribute = doc.nodes[0].attributes.position.x
 * var mycolumn = myAttribute.column;
 *
 * // once you have the column, you can do things like remove duplicates keys to simplify an animation;
 * myColumn.removeDuplicateKeys();
 *
 * // you can extract all the keys to be able to iterate over it:
 * var keyFrames = myColumn.getKeyFrames();
 *
 * for (var i in keyFrames){
 *   $.log (keyFrames[i].frameNumber);
 * }
 *
 * // you can also link a given column to more than one attribute so they share the same animated values:
 *
 * doc.nodes[0].attributes.position.y.column = myColumn;  // now position.x and position.y will share the same animation on the node.
 */
$.oColumn = function( uniqueName, oAttributeObject ){
  var instance = this.$.getInstanceFromCache.call(this, uniqueName);
  if (instance) return instance;

  this._type = "column";

  this.uniqueName = uniqueName;
  this.attributeObject = oAttributeObject;

  this._cacheFrames = [];

  //Helper cache for subsequent actions.
  try{
    // fails when the column has no attribute
    if( !this.$.cache_columnToNodeAttribute ){ this.$.cache_columnToNodeAttribute = {}; }
    this.$.cache_columnToNodeAttribute[this.uniqueName] = { "node":oAttributeObject.node, "attribute": this.attributeObject, "date": (new Date()).getTime() };
  }catch(err){}
}


// $.oColumn Object Properties
/**
 * The name of the column.
 * @name $.oColumn#name
 * @type {string}
 */
Object.defineProperty( $.oColumn.prototype, 'name', {
    get : function(){
         return column.getDisplayName(this.uniqueName);
    },

    set : function(newName){
        var _success = column.rename(this.uniqueName, newName)
        if (_success){
          this.uniqueName = newName;
        }else{
          throw new Error("Failed to rename column "+this.uniqueName+" to "+newName+".")
        }
    }
});


/**
 * The type of the column. There are nine column types: drawing (DRAWING), sound (SOUND), 3D Path (3DPATH), Bezier Curve (BEZIER), Ease Curve (EASE), Expression (EXPR), Timing (TIMING) for timing columns, Quaternion path (QUATERNIONPATH) for 3D rotation and Annotation (ANNOTATION) for annotation columns.
 * @name $.oColumn#type
 * @readonly
 * @type {string}
 */
Object.defineProperty( $.oColumn.prototype, 'type', {
    get : function(){
        return column.type(this.uniqueName)
    }
});


/**
 * Whether the column is selected.
 * @name $.oColumn#selected
 * @type {bool}
 */
Object.defineProperty($.oColumn.prototype, 'selected', {
    get : function(){
        var sel_num = selection.numberOfColumnsSelected();
        for( var n=0;n<sel_num;n++ ){
          var col = selection.selectedColumn( n );
          if( col == this.uniqueName ){
            return true;
          }
        }

        return false;
    },
    set : function(){
      selection.addColumnToSelection(this.uniqueName);
    }
});


/**
 * An array of the oFrame objects provided by the column.
 * @name $.oColumn#frames
 * @type {$.oFrame[]}
 * @readonly
 */
Object.defineProperty($.oColumn.prototype, 'frames', {
    get : function(){
        while( this._cacheFrames.length < frame.numberOf()+1 ){
          this._cacheFrames.push( new this.$.oFrame( this._cacheFrames.length, this ) );
        }

        return this._cacheFrames;
    }
});


/**
 * An array of the keyframes provided by the column.
 * @name $.oColumn#keyframes
 * @readonly
 * @type {$.oFrame[]}
 */
Object.defineProperty($.oColumn.prototype, 'keyframes', {
    get : function(){
      return this.getKeyframes();
    }
});


/**
 * Provides the available subcolumns, based on the type of the column.
 * @name $.oColumn#subColumns
 * @readonly
 * @type {object}
 */
Object.defineProperty($.oColumn.prototype, 'subColumns', {
    get : function(){
      //CF Note: Not sure of this use.
      //MC > allows to loop through subcolumns if they exist
        if (this.type == "3DPATH"){
            return { x : 1,
                     y : 2,
                     z : 3,
                     velocity : 4}
        }
        return { a : 1 };
    }
});

/**
 * The type of easing used by the column
 * @name $.oColumn#subColumns
 * @readonly
 * @type {object}
 */
Object.defineProperty($.oColumn.prototype, 'easeType', {
    get : function(){
        switch(this.type){
            case "BEZIER":
                return "BEZIER";
            case "3DPATH":
                return column.velocityType( this.uniqueName );
            default:
                return null;
        }
    }
})


/**
 * An object with three int values : start, end and step, representing the value of the stepped section parameter (interpolation with non linear "step" parameter).
 * @name $.oColumn#stepSection
 * @type {object}
 */
Object.defineProperty($.oColumn.prototype, 'stepSection', {
  get : function(){
    var _columnName = this.uniqueName;
    var _section = {
      start: func.holdStartFrame (_columnName),
      end : func.holdStopFrame (_columnName),
      step : func.holdStep (_columnName)
    }
    return _section;
  },

  set : function(newSection){
    var _columnName = this.uniqueName;
    func.setHoldStartFrame (_columnName, newSection.start)
    func.setHoldStopFrame (_columnName, newSection.end)
    func.setHoldStep (_columnName, newSection.step)
  }
});


// $.oColumn Class methods

/**
 * Deletes the column from the scene. The column must be unlinked from any attribute first.
 */
$.oColumn.prototype.remove = function(){
  column.removeUnlinkedFunctionColumn(this.name);
  if (this.type) throw new Error("Couldn't remove column "+this.name+", unlink it from any attribute first.")
}


/**
 * Extends the exposure of the drawing's keyframes given the provided arguments.
 * @deprecated Use oDrawingColumn.extendExposures instead.
 * @param   {$.oFrame[]}  exposures            The exposures to extend. If UNDEFINED, extends all keyframes.
 * @param   {int}         amount               The amount to extend.
 * @param   {bool}        replace              Setting this to false will insert frames as opposed to overwrite existing ones.
 */
$.oColumn.prototype.extendExposures = function( exposures, amount, replace){
    if (this.type != "DRAWING") return false;
    // if amount is undefined, extend function below will automatically fill empty frames

    if (typeof exposures === 'undefined') var exposures = this.attributeObject.getKeyframes();

    for (var i in exposures) {
        if (!exposures[i].isBlank) exposures[i].extend(amount, replace);
    }

}



/**
 * Removes concurrent/duplicate keys from drawing layers.
 */
$.oColumn.prototype.removeDuplicateKeys = function(){
    var _keys = this.getKeyframes();

    var _pointsToRemove = [];
    var _pointC;

    // check the extremities
    var _pointA = _keys[0].value;
    var _pointB = _keys[1].value;
    if (JSON.stringify(_pointA) == JSON.stringify(_pointB)) _pointsToRemove.push(_keys[0].frameNumber);

    for (var k=1; k<_keys.length-2; k++){
        _pointA = _keys[k-1].value;
        _pointB = _keys[k].value;
        _pointC = _keys[k+1].value;

        MessageLog.trace(this.attributeObject.keyword+" pointA: "+JSON.stringify(_pointA)+" pointB: "+JSON.stringify(_pointB)+" pointC: "+JSON.stringify(_pointC));

        if (JSON.stringify(_pointA) == JSON.stringify(_pointB) && JSON.stringify(_pointB) == JSON.stringify(_pointC)){
            _pointsToRemove.push(_keys[k].frameNumber);
        }
    }

    _pointA = _keys[_keys.length-2].value;
    _pointB = _keys[_keys.length-1].value;
    if (JSON.stringify(_pointC) == JSON.stringify(_pointB)) _pointsToRemove.push(_keys[_keys.length-1].frameNumber);

    var _frames = this.frames;

    for (var i in _pointsToRemove){
        _frames[_pointsToRemove[i]].isKeyframe = false;
    }

}


/**
 * Duplicates a column. Because of the way Harmony works, specifying an attribute the column will be connected to ensures higher value fidelity between the original and the copy.
 * @param {$.oAttribute}     [newAttribute]         An attribute to link the column to upon duplication.
 *
 * @return {$.oColumn}                The column generated.
 */
$.oColumn.prototype.duplicate = function(newAttribute) {
  var _duplicateColumn = this.$.scene.addColumn(this.type, this.name);

  // linking to an attribute if one is provided
  if (typeof newAttribute !== 'undefined'){
    newAttribute.column = _duplicateColumn;
    _duplicateColumn.attributeObject = newAttribute;
  }

  var _duplicatedFrames = _duplicateColumn.frames;
  var _keyframes = this.keyframes;

  // we set the ease twice to avoid incompatibilities between ease parameters and yet unchanged points
  for (var i in _keyframes){
    var _duplicateFrame = _duplicatedFrames[_keyframes[i].frameNumber];
    _duplicateFrame.value = _keyframes[i].value;
  }

  for (var i in _keyframes){
    var _duplicateFrame = _duplicatedFrames[_keyframes[i].frameNumber];
    _duplicateFrame.ease = _keyframes[i].ease;
  }

  for (var i in _keyframes){
    var _duplicateFrame = _duplicatedFrames[_keyframes[i].frameNumber];
    _duplicateFrame.ease = _keyframes[i].ease;
  }

  _duplicateColumn.stepSection = this.stepSection;

  return _duplicateColumn;
}


/**
 * Filters out only the keyframes from the frames array.
 *
 * @return {$.oFrame[]}    Provides the array of frames from the column.
 */
$.oColumn.prototype.getKeyframes = function(){
  var _frames = this.frames;

  var _ease = this.easeType;
  if( _ease == "BEZIER" || _ease == "EASE" ){
    var _keyFrames = [];
    var _columnName = this.uniqueName;
    var _points = func.numberOfPoints(_columnName);

    for (var i = 0; i<_points; i++) {
      var _frameNumber = func.pointX( _columnName, i )
      _keyFrames.push( _frames[_frameNumber] );
    }

    return _keyFrames;
  }

  _frames = _frames.filter(function(x){return x.isKeyframe});
  return _frames;
}


/**
 * Filters out only the keyframes from the frames array.
 * @deprecated For case consistency, keyframe will never have a capital F
 * @return {$.oFrame[]}    Provides the array of frames from the column.
 */
$.oColumn.prototype.getKeyFrames = function(){
  this.$.debug("oColumn.getKeyFrames is deprecated. Use oColumn.getKeyframes instead.", this.$.DEBUG_LEVEL.ERROR);
  return this.keyframes;
}


/**
 * Gets the value of the column at the given frame.
 * @param {int}  [frame=1]       The frame at which to get the value
 * @return  {various}            The value of the column, can be different types depending on column type.
 */
$.oColumn.prototype.getValue = function(frame){
  if (typeof frame === 'undefined') var frame = 1;

  // this.$.log("Getting value of frame "+this.frameNumber+" of column "+this.column.name)
  if (this.attributeObject){
    return this.attributeObject.getValue(frame);
  }else{
    this.$.debug("getting unlinked column "+this.name+" value at frame "+frame, this.$.DEBUG_LEVEL.ERROR);
    this.$.debug("warning : getting a value from a column without attribute destroys value fidelity", this.$.DEBUG_LEVEL.ERROR);

    if (this.type == "3DPATH") {
      var _frame = new this.$.oFrame(frame, this, this.subColumns);
      return new this.$.oPathPoint(this, _frame);
    }

    return column.getEntry (this.uniqueName, 1, frame);
  }
}


/**
 * Sets the value of the column at the given frame.
 * @param {various}   newValue        The new value to set the column to
 * @param {int}       [frame=1]       The frame at which to get the value
 */
$.oColumn.prototype.setValue = function(newValue, frame){
  if (typeof frame === 'undefined') var frame = 1;

  if (this.attributeObject){
    this.attributeObject.setValue( newValue, frame);
  }else{
    this.$.debug("setting unlinked column "+this.name+" value to "+newValue+" at frame "+frame, this.$.DEBUG_LEVEL.ERROR);
    this.$.debug("warning : setting a value on a column without attribute destroys value fidelity", this.$.DEBUG_LEVEL.ERROR);

    if (this.type == "3DPATH") {
      column.setEntry (this.uniqueName, 1, frame, newValue.x);
      column.setEntry (this.uniqueName, 2, frame, newValue.y);
      column.setEntry (this.uniqueName, 3, frame, newValue.z);
      column.setEntry (this.uniqueName, 4, frame, newValue.velocity);
    }else{
      column.setEntry (this.uniqueName, 1, frame, newValue.toString());
    }
  }
}



/**
 * Retrieves the nodes index in the timeline provided.
 * @param   {oTimeline}   [timeline]     Optional: the timeline object to search the column Layer. (by default, grabs the current timeline)
 *
 * @return  {int}    The index within that timeline.
 */
$.oColumn.prototype.getTimelineLayer = function(timeline){
  if (typeof timeline === 'undefined') var timeline = this.$.scene.getTimeline();

  var _columnNames = timeline.allLayers.map(function(x){return x.column?x.column.uniqueName:null});
  return timeline.allLayers[_columnNames.indexOf(this.uniqueName)];
}


/**
 * @private
 */
$.oColumn.prototype.toString = function(){
  return "[object $.oColumn '"+this.name+"']"
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oDrawingColumn class      //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * the $.oDrawingColumn constructor. Only called internally by the factory function [scene.getColumnByName()]{@link $.oScene#getColumnByName};
 * @constructor
 * @classdesc  oDrawingColumn is a special case of column which can be linked to an [oElement]{@link $.oElement}. This type of column is used to display drawings and always is visible in the Xsheet window.
 * @augments   $.oColumn
 * @param   {string}                   uniqueName                  The unique name of the column.
 * @param   {$.oAttribute}             oAttributeObject            The oAttribute thats connected to the column.
 *
 * @property {string}                  uniqueName                  The unique name of the column.
 * @property {$.oAttribute}            attributeObject             The attribute object that the column is attached to.
 */
$.oDrawingColumn = function( uniqueName, oAttributeObject ) {
  // $.oDrawingColumn can only represent a column of type 'DRAWING'
    if (column.type(uniqueName) != 'DRAWING') throw new Error("'uniqueName' parameter must point to a 'DRAWING' type node");
    //MessageBox.information("getting an instance of $.oDrawingColumn for column : "+uniqueName)
    var instance = $.oColumn.call(this, uniqueName, oAttributeObject);
    if (instance) return instance;
}


// extends $.oColumn and can use its methods
$.oDrawingColumn.prototype = Object.create($.oColumn.prototype);
$.oDrawingColumn.prototype.constructor = $.oColumn;


/**
 * Retrieve and set the drawing element attached to the column.
 * @name $.oDrawingColumn#element
 * @type {$.oElement}
 */
Object.defineProperty($.oDrawingColumn.prototype, 'element', {
    get : function(){
        return new this.$.oElement(column.getElementIdOfDrawing( this.uniqueName), this);
    },

    set : function(oElementObject){
        column.setElementIdOfDrawing( this.uniqueName, oElementObject.id );
        oElementObject.column = this;
    }
})


/**
 * Extends the exposure of the drawing's keyframes by the specified amount.
 * @param   {$.oFrame[]}  [exposures]            The exposures to extend. If not specified, extends all keyframes.
 * @param   {int}         [amount]               The number of frames to add to each exposure. If not specified, will extend frame up to the next one.
 * @param   {bool}        [replace=false]        Setting this to false will insert frames as opposed to overwrite existing ones.(currently unsupported))
 */
$.oDrawingColumn.prototype.extendExposures = function( exposures, amount, replace){
    // if amount is undefined, extend function below will automatically fill empty frames
    if (typeof exposures === 'undefined') var exposures = this.getKeyframes();

    this.$.debug("extendingExposures "+exposures.map(function(x){return x.frameNumber})+" by "+amount, this.$.DEBUG_LEVEL.DEBUG)

    // can't extend blank exposures, so we remove them from the list to extend
    exposures = exposures.filter(function(x){return !x.isBlank})

    for (var i in exposures) {
      exposures[i].extend(amount, replace);
    }
}


/**
 * Duplicates a Drawing column.
 * @param {bool}          [duplicateElement=true]     Whether to also duplicate the element. Default is true.
 * @param {$.oAttribute}  [newAttribute]              Whether to link the new column to an attribute at this point.
 *
 * @return {$.oColumn}    The created column.
 */
$.oDrawingColumn.prototype.duplicate = function(newAttribute, duplicateElement) {
  // duplicate element?
  if (typeof duplicateElement === 'undefined') var duplicateElement = true;
  var _duplicateElement = duplicateElement?this.element.duplicate():this.element;

  var _duplicateColumn = this.$.scene.addColumn(this.type, this.name, _duplicateElement);

  // linking to an attribute if one is provided
  if (typeof newAttribute !== 'undefined'){
    newAttribute.column = _duplicateColumn;
    _duplicateColumn.attributeObject = newAttribute;
  }

  var _frames = this.frames;
  for (var i in _frames){
    var _duplicateFrame = _duplicateColumn.frames[i];
    _duplicateFrame.value = _frames[i].value;
    if (_frames[i].isKeyframe) _duplicateFrame.isKeyframe = true;
  }

  return _duplicateColumn;
}


/**
 * Renames the column's exposed drawings according to the frame they are first displayed at.
 * @param   {string}  [prefix]            a prefix to add to all names.
 * @param   {string}  [suffix]            a suffix to add to all names.
 */
$.oDrawingColumn.prototype.renameAllByFrame = function(prefix, suffix){
  if (typeof prefix === 'undefined') var prefix = "";
  if (typeof suffix === 'undefined') var suffix = "";

  // get exposed drawings
  var _displayedDrawings = this.getExposedDrawings();
  this.$.debug("Column "+this.name+" has drawings : "+_displayedDrawings.map(function(x){return x.value}), this.$.DEBUG_LEVEL.LOG);

  // remove duplicates
  var _seen = [];
  for (var i=0; i<_displayedDrawings.length; i++){
    var _drawing = _displayedDrawings[i].value;

    if (_seen.indexOf(_drawing.name) == -1){
      _seen.push(_drawing.name);
    }else{
      _displayedDrawings.splice(i,1);
      i--;
    }
  }

  // rename
  for (var i in _displayedDrawings){
    var _frameNum = _displayedDrawings[i].frameNumber;
    var _drawing = _displayedDrawings[i].value;
    this.$.debug("renaming drawing "+_drawing+" of column "+this.name+" to "+prefix+_frameNum+suffix, this.$.DEBUG_LEVEL.LOG);
    _drawing.name = prefix+_frameNum+suffix;
  }
}


/**
 * Removes unused drawings from the column.
 * @param   {$.oFrame[]}  exposures            The exposures to extend. If UNDEFINED, extends all keyframes.
 */
$.oDrawingColumn.prototype.removeUnexposedDrawings = function(){
  var _element = this.element;
  var _displayedDrawings = this.getExposedDrawings().map(function(x){return x.value.name;});
  var _element = this.element;
  var _drawings = _element.drawings;

  for (var i=_drawings.length-1; i>=0; i--){
    this.$.debug("removing drawing "+_drawings[i].name+" of column "+this.name+"? "+(_displayedDrawings.indexOf(_drawings[i].name) == -1), this.$.DEBUG_LEVEL.LOG);
    if (_displayedDrawings.indexOf(_drawings[i].name) == -1) _drawings[i].remove();
  }
}

$.oDrawingColumn.prototype.getExposedDrawings = function (){
  return this.keyframes.filter(function(x){return x.value != null});
}


/**
 * @private
 */
 $.oDrawingColumn.prototype.toString = function(){
  return "<$.oDrawingColumn '"+this.name+"'>";
}
