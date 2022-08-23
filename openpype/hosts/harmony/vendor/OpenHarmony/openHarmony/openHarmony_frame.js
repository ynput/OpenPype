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
//          $.oFrame class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oFrame.
 * @constructor
 * @classdesc  Frames describe the frames of a oColumn, and allow to access the value, ease settings, as well as frameNumber.
 * @param   {int}                    frameNumber             The frame to which this references.
 * @param   {oColumn}                oColumnObject           The column to which this frame references.
 * @param   {int}                    subColumns              The subcolumn index.
 *
 * @property {int}                     frameNumber           The frame to which this references.
 * @property {oColumn}                 column                The oColumnObject to which this frame references.
 * @property {oAttribute}              attributeObject       The oAttributeObject to which this frame references.
 * @property {int}                     subColumns            The subcolumn index.
 * @example
 * // to access the frames of a column, simply call oColumn.frames:
 * var myColumn = $.scn.columns[O]      // access the first column of the list of columns present in the scene
 *
 * var frames = myColumn.frames;
 *
 * // then you can iterate over them to check their properties:
 *
 * for (var i in frames){
 *   $.log(frames[i].isKeyframe);
 *   $.log(frames[i].continuity);
 * }
 *
 * // you can get and set the value of the frame
 *
 * frames[1].value = 5;   // frame array values and frameNumbers are matched, so this sets the value of frame 1
 */
$.oFrame = function( frameNumber, oColumnObject, subColumns ){
  this._type = "frame";

  this.frameNumber = frameNumber;

  if( oColumnObject instanceof $.oAttribute ){  //Direct access to an attribute, when not keyable. We still provide a frame access for consistency.  > MCNote ?????
    this.column = false;
    this.attributeObject = oColumnObject;
  }else if( oColumnObject instanceof $.oColumn ){
    this.column = oColumnObject;

    if (this.column && typeof subColumns === 'undefined'){
      var subColumns = this.column.subColumns;
    }else{
      var subColumns = { a : 1 };
    }

    this.attributeObject = this.column.attributeObject;
  }

  this.subColumns = subColumns;
}


// $.oFrame Object Properties
/**
 * The value of the frame. Contextual to the attribute type.
 * @name $.oFrame#value
 * @type {object}
 * @todo Include setting values on column that don't have attributes linked?
 */
Object.defineProperty($.oFrame.prototype, 'value', {
  get : function(){
    if (this.attributeObject){
      this.$.debug("getting value of frame "+this.frameNumber+" through attribute object : "+this.attributeObject.keyword, this.$.DEBUG_LEVEL.LOG);
      return this.attributeObject.getValue(this.frameNumber);
    }else{
      this.$.debug("getting value of frame "+this.frameNumber+" through column object : "+this.column.name, this.$.DEBUG_LEVEL.LOG);
      return this.column.getValue(this.frameNumber);
    }
    /*
      // this.$.log("Getting value of frame "+this.frameNumber+" of column "+this.column.name)
    if (this.attributeObject){
      return this.attributeObject.getValue(this.frameNumber);
    }else{
      this.$.debug("getting unlinked column "+this.name+" value at frame "+this.frameNumber, this.$.DEBUG_LEVEL.ERROR);
      this.$.debug("warning : getting a value from a column without attribute destroys value fidelity", this.$.DEBUG_LEVEL.ERROR);
      if (this.
      return column.getEntry (this.name, 1, this.frameNumber);
    }*/
  },

  set : function(newValue){
    if (this.attributeObject){
      return this.attributeObject.setValue(newValue, this.frameNumber);
    }else{
      return this.column.setValue(newValue, this.frameNumber);
    }

    /*// this.$.log("Setting frame "+this.frameNumber+" of column "+this.column.name+" to value: "+newValue)
    if (this.attributeObject){
      this.attributeObject.setValue( newValue, this.frameNumber );
    }else{
      this.$.debug("setting unlinked column "+this.name+" value to "+newValue+" at frame "+this.frameNumber, this.$.DEBUG_LEVEL.ERROR);
      this.$.debug("warning : setting a value on a column without attribute destroys value fidelity", this.$.DEBUG_LEVEL.ERROR);

      var _subColumns = this.subColumns;
      for (var i in _subColumns){
        column.setEntry (this.name, _subColumns[i], this.frameNumber, newValue);
      }
    }*/
  }
});


/**
 * Whether the frame is a keyframe.
 * @name $.oFrame#isKeyframe
 * @type {bool}
 */
Object.defineProperty($.oFrame.prototype, 'isKeyframe', {
    get : function(){
      if( !this.column ) return true;
      if( this.frameNumber == 0 ) return false;  // frames array start at 0 but first index is not a real frame

      var _column = this.column.uniqueName;
      if (this.column.type == 'DRAWING' || this.column.type == 'TIMING'){
        if( column.getTimesheetEntry){
          return !column.getTimesheetEntry(_column, 1, this.frameNumber).heldFrame;
        }else{
          return false;   //No valid way to check for keys on a drawing without getTimesheetEntry
        }
      }else if (['BEZIER', '3DPATH', 'EASE', 'QUATERNION'].indexOf(this.column.type) != -1){
        return column.isKeyFrame(_column, 1, this.frameNumber);
      }
      return false;
    },

    set : function(keyframe){
      this.$.log("setting keyframe for frame "+this.frameNumber);
      var col = this.column;
      if( !col ) return;

      var _column = col.uniqueName;

      if( col.type == "DRAWING" ){
        if (keyframe){
          column.addKeyDrawingExposureAt( _column, this.frameNumber );
        }else{
          column.removeKeyDrawingExposureAt( _column, this.frameNumber );
        }
      }else{
        if (keyframe){
          //Sanity check, in certain situations, the setKeyframe resets to 0 (specifically if there is no pre-existing key elsewhere.)
          //This will check the value prior to the key, set the key, and enforce the value after.

          //var val = 0.0;
          // try{
          var val = this.value;
          // }catch(err){}
          //this.$.log("setting keyframe for frame "+this.frameNumber);
          column.setKeyFrame( _column, this.frameNumber );

          // try{
          //var post_val = this.value;
          //if (val != post_val) {
            this.value = val;
          //}
          // }catch(err){}
        }else{
          column.clearKeyFrame( _column, this.frameNumber );
        }
      }
    }
});


/**
 * Whether the frame is a keyframe.
 * @name $.oFrame#isKeyFrame
 * @deprecated For case consistency, keyframe will never have a capital F
 * @type {bool}
 */
Object.defineProperty($.oFrame.prototype, 'isKeyFrame', {
    get : function(){
      return this.isKeyframe;
    },

    set : function(keyframe){
      this.$.debug("oFrame.isKeyFrame is deprecated. Use oFrame.isKeyframe instead.", this.$.DEBUG_LEVEL.ERROR);
      this.isKeyframe = keyframe;
    }
});


/**
 * Whether the frame is a keyframe.
 * @name $.oFrame#isKey
 * @type {bool}
 */
Object.defineProperty($.oFrame.prototype, 'isKey', {
    get : function(){
      return this.isKeyframe;
    },

    set : function(keyFrame){
      this.isKeyframe = keyFrame;
    }
});


/**
 * The duration of the keyframe exposure of the frame.
 * @name $.oFrame#duration
 * @type {int}
 */
Object.defineProperty($.oFrame.prototype, 'duration', {
    get : function(){
        var _startFrame = this.startFrame;
        var _sceneLength = frame.numberOf()

        if( !this.column ){
          return _sceneLength;
        }

        // walk up the frames of the scene to the next keyFrame to determin duration
        var _frames = this.column.frames
        for (var i=this.frameNumber+1; i<_sceneLength; i++){
            if (_frames[i].isKeyframe) return _frames[i].frameNumber - _startFrame;
        }
        return _sceneLength - _startFrame;
    },

    set : function( val ){
      throw "Not implemented.";
    }
});


/**
 * Identifies if the frame is blank/empty.
 * @name $.oFrame#isBlank
 * @type {int}
 */
Object.defineProperty($.oFrame.prototype, 'isBlank', {
    get : function(){
      var col = this.column;
      if( !col ){
        return false;
      }

      if ( col.type != "DRAWING") return false;

      if( !column.getTimesheetEntry ){
        return (this.value == "");
      }

      return column.getTimesheetEntry( col.uniqueName, 1, this.frameNumber ).emptyCell;
    },

    set : function( val ){
      throw "Not implemented.";
    }
});


/**
 * Identifies the starting frame of the exposed drawing.
 * @name $.oFrame#startFrame
 * @type {int}
 * @readonly
 */
Object.defineProperty($.oFrame.prototype, 'startFrame', {
    get : function(){
      if( !this.column ){
        return 1;
      }

      if (this.isKeyframe) return this.frameNumber;
      if (this.isBlank) return -1;

      var _frames = this.column.frames;
      for (var i=this.frameNumber-1; i>=1; i--){
          if (_frames[i].isKeyframe) return _frames[i].frameNumber;
      }
      return -1;
    }
});


/**
 * Returns the drawing types used in the drawing column. K = key drawings, I = inbetween, B = breakdown
 * @name $.oFrame#marker
 * @type {string}
 */
Object.defineProperty($.oFrame.prototype, 'marker', {
    get : function(){
        if( !this.column ){
          return "";
        }

        var _column = this.column;
        if (_column.type != "DRAWING") return "";
        return column.getDrawingType(_column.uniqueName, this.frameNumber);
    },

    set: function( marker ){
        if( !this.column ){
          return;
        }

        var _column = this.column;
        if (_column.type != "DRAWING") throw "can't set 'marker' property on columns that are not 'DRAWING' type"
        column.setDrawingType( _column.uniqueName, this.frameNumber, marker );
    }
});


/**
 * Find the index of this frame in the corresponding columns keyframes. -1 if unavailable.
 * @name $.oFrame#keyframeIndex
 * @type {int}
 */
Object.defineProperty($.oFrame.prototype, 'keyframeIndex', {
    get : function(){
        var _kf = this.column.getKeyframes().map(function(x){return x.frameNumber});
        var _kfIndex = _kf.indexOf(this.frameNumber);
        return _kfIndex;
    }
});


/**
 * Find the the nearest keyframe to this, on the left. Returns itself if it is a key.
 * @name $.oFrame#keyframeLeft
 * @type {oFrame}
 */
Object.defineProperty($.oFrame.prototype, 'keyframeLeft', {
    get : function(){
      return (new this.$.oFrame(this.startFrame, this.column));
    }
});


/**
 * Find the the nearest keyframe to this, on the right.
 * @name $.oFrame#keyframeRight
 * @type {oFrame}
 */
Object.defineProperty($.oFrame.prototype, 'keyframeRight', {
    get : function(){
      return (new this.$.oFrame(this.startFrame+this.duration, this.column));
    }
});


/**
 * Access the velocity value of a keyframe from a 3DPATH column.
 * @name $.oFrame#velocity
 * @type {oFrame}
 */
Object.defineProperty($.oFrame.prototype, 'velocity', {
  get : function(){
    if (!this.column) return null;
    if (this.column.type != "3DPATH") return null;
    var _columnName = this.column.uniqueName;
    if (!this.isKeyframe) return column.getEntry(_columnName, 4, this.frameNumber);

    var index = this.keyframeIndex;

    var _y = func.pointY(_columnName, index);
    return _y;
  },

  set : function(newVelocity){
    var _curVelocity = this.velocity;
    throw new Error("setting oFrame.velocity is not yet implemented")
  }
});


/**
 * Gets a general ease object for the frame, which can be used to set frames to the same ease values. ease Objects contain the following properties:
 * x : frame number
 * y : position of the value of the column or velocity for 3dpath
 * easeIn : a $.oPoint object representing the left handle for bezier columns, or a {point, ease} object for ease columns.
 * easeOut : a $.oPoint object representing the left handle for bezier columns, or a {point, ease} object for ease columns.
 * continuity : the type of bezier used by the point.
 * constant : wether the frame is interpolated or a held value.
 * @name $.oFrame#ease
 * @type {oPoint/object}
 */
Object.defineProperty($.oFrame.prototype, 'ease', {
  get : function(){
    var _column = this.column;
    if (!_column) return null;
    if ( !this.isKeyFrame ) return null;
    if ( this.isBlank ) return null;

    var _columnName = _column.uniqueName;
    var _index = this.keyframeIndex;

    var ease = {
      x : func.pointX(_columnName, _index),
      y : func.pointY(_columnName, _index),
      constant : func.pointConstSeg(_columnName, _index),
      continuity : func.pointContinuity(_columnName, _index)
    }

    if( _column.easeType == "BEZIER" ){
      ease.easeIn = new this.$.oPoint(func.pointHandleLeftX(_columnName, _index), func.pointHandleLeftY(_columnName, _index),0);
      ease.easeOut = new this.$.oPoint(func.pointHandleRightX(_columnName, _index), func.pointHandleRightY(_columnName, _index),0);
    }

    if( _column.easeType == "EASE" ){
      ease.easeIn = {point:func.pointEaseIn(_columnName, _index), angle:func.angleEaseIn(_columnName, _index)};
      ease.easeOut = {point:func.pointEaseOut(_columnName, _index), angle:func.angleEaseOut(_columnName, _index)};
    }

    return ease;
  },

  set : function(newEase){
    if ( !this.isKeyFrame ) throw new Error("can't set ease on a non keyframe");;
    if (this.isBlank) throw new Error("can't set ease on an empty frame");

    var _column = this.column;
    if (!_column) throw new Error ("Can't set ease on a frame without a column");
    var _columnName = _column.uniqueName;

    if( _column.easeType == "BEZIER" ){
      if (!newEase.hasOwnProperty("x")) throw new Error("Incorrect ease type for a BEZIER column");
      func.setBezierPoint (_columnName, newEase.x, newEase.y, newEase.easeIn.x, newEase.easeIn.y, newEase.easeOut.x, newEase.easeOut.y, newEase.constant, newEase.continuity)
    }

    if (_column.easeType == "EASE" ){
      if (!newEase.hasOwnProperty("point")) throw new Error("Incorrect ease type for a EASE column");
      func.setEasePoint(_columnName, newEase.x, newEase.y, newEase.easeIn.point, newEase.easeIn.angle, newEase.easeOut.point, newEase.easeOut.angle, newEase.constant, newEase.continuity)
    }
  }
});


/**
 * Gets the ease parameter of the segment, easing into this frame.
 * @name $.oFrame#easeIn
 * @type {oPoint/object}
 */
Object.defineProperty($.oFrame.prototype, 'easeIn', {
  get : function(){
    return this.ease.easeIn;
  },

  set : function(newEaseIn){
    var _ease = this.ease;
    _ease.easeIn = newEaseIn;

    this.ease = ease;
  }
});


/**
 * Gets the ease parameter of the segment, easing out of this frame.
 * @name $.oFrame#easeOut
 * @type {oPoint/object}
 */
Object.defineProperty($.oFrame.prototype, 'easeOut', {
  get : function(){
    return this.ease.easeOut;
  },

  set : function(newEaseOut){
    var _ease = this.ease;
    _ease.easeOut = newEaseOut;

    this.ease = _ease;
  }
});


/**
 * Determines the frame's continuity setting. Can take the values "CORNER", (two independant bezier handles on each side), "SMOOTH"(handles are aligned) or "STRAIGHT" (no handles and in straight lines).
 * @name $.oFrame#continuity
 * @type {string}
 */
Object.defineProperty($.oFrame.prototype, 'continuity', {
  get : function(){
    var _frame = this.keyframeLeft;    //Works on the left keyframe, in the event that this is not a keyframe itself.

    return _frame.ease.continuity;
  },

  set : function( newContinuity ){
    var _frame = this.keyframeLeft;    //Works on the left keyframe, in the event that this is not a keyframe itself.
    var _ease = _frame.ease;
    _ease.continuity = newContinuity;

    _frame.ease = ease;
  }
});


/**
 * Whether the frame is tweened or constant. Uses nearest keyframe if this frame isnt.
 * @name $.oFrame#constant
 * @type {string}
 */
Object.defineProperty($.oFrame.prototype, 'constant', {
  get : function(){
    var _frame = this.keyframeLeft;    //Works on the left keyframe, in the event that this is not a keyframe itself.

    return _frame.ease.constant;
  },

  set : function( newConstant ){
    if( this.column ){
      var _frame = this.keyframeLeft;    //Works on the left keyframe, in the event that this is not a keyframe itself.

      var _ease = _frame.ease;
      _ease.constant = newConstant;
      _frame.ease = _ease;
    }
  }
});


/**
 * Identifies or sets whether there is a tween. Inverse of constant.
 * @name $.oFrame#tween
 * @type {string}
 */
Object.defineProperty($.oFrame.prototype, 'tween', {
  get : function(){
    return !this.constant;
  },
  set : function( new_tween ){
    this.constant = !new_tween;
  }
});



// oFrame Class Methods


/**
 * Extends the frames value to the specified duration, replaces in the event that replace is specified.
 * @param   {int}        duration              The duration to extend it to; if no duration specified, extends to the next available keyframe.
 * @param   {bool}       replace               Setting this to false will insert frames as opposed to overwrite existing ones.
 */
$.oFrame.prototype.extend = function( duration, replace ){
    if (typeof replace === 'undefined') var replace = true;
    // setting this to false will insert frames as opposed to overwrite existing ones

    if( !this.column ){
      return;
    }

    var _frames = this.column.frames;

    if (typeof duration === 'undefined'){
        // extend to next non blank keyframe if not set
        var duration = 0;
        var curFrameEnd = this.startFrame + this.duration;
        var sceneLength = this.$.scene.length;

        // find next non blank keyframe
        while ((curFrameEnd + duration) <= sceneLength && _frames[curFrameEnd + duration].isBlank){
            duration ++;
        }
    }

    var _value = this.value;
    var startExtending = this.startFrame+this.duration;

    for (var i = 0; i<duration; i++){
        if (!replace){
            // TODO : push all other frames back
        }
        _frames[startExtending+i].value = _value;
    }
}
