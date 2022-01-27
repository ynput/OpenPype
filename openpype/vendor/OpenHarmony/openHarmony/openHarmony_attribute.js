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
//        $.oAttribute class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * The constructor for the $.oAttribute class.
 * @classdesc
 * The $.oAttribute class holds the smart version of the parameter you can find in layer property.<br>
 * It is used internally to get and set values and link a oColumn to a parameter in order to animate it. (Users should never have to instantiate this class) <br>
 * For a list of attributes existing in each node type and their type, as well as examples of the values they can hold, refer to :<br>
 * {@link NodeType}.
 * @constructor
 * @param   {$.oNode}                  oNodeObject                The oNodeObject that the attribute is associated to.
 * @param   {attr}                     attributeObject            The internal harmony Attribute Object.
 * @param   {$.oAttribute}             parentAttribute            The parent attribute of the subattribute.
 *
 * @property {$.oNode}                 node                       The oNode this attribute belongs to.
 * @property {attr}                    attributeObject            The internal harmony Attribute Object.
 * @property {string}                  keyword                    The keyword describing this attribute. (always in lower case)
 * @property {string}                  shortKeyword               The full keyword describing this attribute, including parent attributes separated with a "." (always in lower case)
 * @property {$.oAttribute}            parentAttribute            The parent oAttribute object
 * @property {$.oAttribute[]}          subAttributes              The subattributes of this attribute.
 * @example
 * // oAttribute objects can be grabbed from the node .attributes object with dot notation, by calling the attribute keyword in lowercase.
 *
 * var myNode = $.scn.getSelectedNodes()[0];          // grab the first selected node
 * var Xattribute = myNode.attributes.position.x;     // gets the position.x attribute of the node if it has it (for example, PEG nodes have it)
 *
 * var Xcolumn = Xattribute.column;                   // retrieve the linked column to the element (The object that holds the animation)
 *
 * Xattribute.setValue(5, 5);                         // sets the value to 5 at frame 5
 *
 * // attribute values can also be set directly on the node when not animated:
 * myNode.position.x = 5;
 *
 */
$.oAttribute = function( oNodeObject, attributeObject, parentAttribute ){
  this._type = "attribute";

  this.node = oNodeObject;
  this.attributeObject = attributeObject;

  this._shortKeyword = attributeObject.keyword();

  if( attributeObject.fullKeyword ){
    this._keyword = attributeObject.fullKeyword();
  }else{
    this._keyword = (parentAttribute?(parentAttribute._keyword+"."):"") + this._shortKeyword;
  }

  this.parentAttribute = parentAttribute; // only for subAttributes

  // recursively add all subattributes as properties on the object
  this.createSubAttributes(attributeObject);
}


/**
 * Private function to create subAttributes in an oAttribute object at initialisation.
 * @private
 * @return  {void}   Nothing returned.
 */
$.oAttribute.prototype.createSubAttributes = function (attributeObject){
  var _subAttributes = [];

  // if harmony version supports getSubAttributes
  var _subAttributesList = [];
  if (attributeObject.getSubAttributes){
    _subAttributesList = attributeObject.getSubAttributes();
  }else{
    var sub_attrs = node.getAttrList( this.node.path, 1, this._keyword );

    if( sub_attrs && sub_attrs.length>0 ){
      _subAttributesList = sub_attrs;
    }
  }

  for (var i in _subAttributesList){
    var _subAttribute = new this.$.oAttribute( this.node, _subAttributesList[i], this );
    var _keyword = _subAttribute.shortKeyword;

    // creating a property on the attribute object with the subattribute name to access it
    this[_keyword] = _subAttribute;
    _subAttributes.push(_subAttribute)
  }

  // subAttributes is made available as an array for more formal access
  this.subAttributes = _subAttributes;
}


/**
 * Private function to add utility to subattributes on older versions of Harmony.
 * @private
 * @deprecated
 * @return  {void}   Nothing returned.
 */
$.oAttribute.prototype.getSubAttributes_oldVersion = function (){
  var sub_attrs = [];

  switch( this.type ){
      case "POSITION_3D" :
        //hard coded subAttr handler for POSITION_3D in older versions of Harmony.
        sub_attrs = [ 'SEPARATE', 'X', 'Y', 'Z'];
        break
      case "ROTATION_3D" :
        sub_attrs = [ 'SEPARATE', 'ANGLEX', 'ANGLEY', 'ANGLEZ', "QUATERNIONPATH" ];
        break
      case "SCALE_3D" :
        sub_attrs = [ 'SEPARATE', 'IN_FIELDS', 'XY', 'X', 'Y', 'Z' ];
        break
      case "DRAWING" :
        sub_attrs = [ 'ELEMENT', 'ELEMENT_MODE', 'CUSTOM_NAME'];
        break
      case "ELEMENT" :
        sub_attrs = [ 'LAYER' ]
        break
      case "CUSTOM_NAME" :
        sub_attrs = [ 'NAME', 'TIMING', 'EXTENSION', 'FIELD_CHART' ]
      default:
        break
  }

  var _node = this.node.path;
  var _keyword = this._keyword;

  sub_attrs = sub_attrs.map(function(x){return node.getAttr( _node, 1, _keyword+"."+x )})

  return sub_attrs;
}


/**
 * The display name of the attribute
 * @name $.oAttribute#name
 * @type {string}
 */
Object.defineProperty($.oAttribute.prototype, 'name', {
  get: function(){
    return this.attributeObject.name();
  }
})

/**
 * The full keyword of the attribute.
 * @name $.oAttribute#keyword
 * @type {string}
 */
Object.defineProperty($.oAttribute.prototype, 'keyword', {
    get : function(){
        // formatting the keyword for our purposes
        // hard coding a fix for 3DPath attribute name which starts with a number
        var _keyword = this._keyword.toLowerCase();
        if (_keyword == "3dpath") _keyword = "path3d";
        return _keyword;
    }
});


/**
 * The part of the attribute's keyword that is after the "." for subAttributes.
 * @name $.oAttribute#shortKeyword
 * @type {string}
 */
Object.defineProperty($.oAttribute.prototype, 'shortKeyword', {
    get : function(){
        // formatting the keyword for our purposes
        // hard coding a fix for 3DPath attribute name which starts with a number
        var _keyword = this._shortKeyword.toLowerCase();
        if (_keyword == "3dpath") _keyword = "path3d";
        return _keyword;
    }
});


/**
 * The type of the attribute.
 * @name $.oAttribute#type
 * @type {string}
 */
Object.defineProperty($.oAttribute.prototype, 'type', {
    get : function(){
        return this.attributeObject.typeName();
    }
});

/**
 * The column attached to the attribute.
 * @name $.oAttribute#column
 * @type {$.oColumn}
 * @example
// link a new column to an attribute by setting this value:
var myColumn = $.scn.addColumn("BEZIER");
myNode.attributes.position.x.column = myColumn; // values contained in "myColumn" now define the animation of our peg's x position

// to automatically create a column and link it to the attribute, use:
myNode.attributes.position.x.addColumn(); // if the column exist already, it will just be returned.

// to unlink a column, just set it to null/undefined:
myNode.attributes.position.x.column = null; // values are no longer animated.
 */
Object.defineProperty($.oAttribute.prototype, 'column', {
  get : function(){
    var _column = node.linkedColumn ( this.node.path, this._keyword );
    if( _column && _column.length ){
      return this.node.scene.$column( _column, this );
    }else{
      return null;
    }
  },

  set : function(columnObject){
    // unlink if provided with null value or empty string
    if (!columnObject){
      node.unlinkAttr(this.node.path, this._keyword);
    }else{
      node.linkAttr(this.node.path, this._keyword, columnObject.uniqueName);
      columnObject.attributeObject = this;
      // TODO: transfer current value of attribute to a first key on the column if column is empty
    }
  }
});


 /**
 * The frames array holding the values of the animation. Starts at 1, as array indexes correspond to frame numbers.
 * @name $.oAttribute#frames
 * @type {$.oFrame[]}
 */
Object.defineProperty($.oAttribute.prototype, 'frames', {
    get : function(){
         var _column = this.column
         if (_column != null){
            return _column.frames;
         }else{
          //Need a method to get frames of non-column values. Local Values.
            return [ new this.$.oFrame( 1, this, false ) ];
         }
    },

    set : function(){
      throw "Not implemented."
    }
});


/**
 * An array of only the keyframes (frames with a set value) of the animation.
 * @name $.oAttribute#keyframes
 * @type {$.oFrame[]}
 */
// MCNote: I would prefer if this could remain getKeyFrames()
Object.defineProperty($.oAttribute.prototype, 'keyframes', {
    get : function(){
      var col     = this.column;
      var frames  = this.frames;

      if( !col ){
        return frames[1];
      }

      return this.column.keyframes;
    },

    set : function(){
      throw "Not implemented."
    }
});

/**
 * WIP.
 * @name $.oAttribute#useSeparate
 * @type {bool}
 * @private
 */
//CF Note: Not sure if this should be a general attribute, or a subattribute.
Object.defineProperty($.oAttribute.prototype, "useSeparate", {
    get : function(){
        // TODO
        throw new Error("not yet implemented");
    },

    set : function( _value ){
        // TODO: when swapping from one to the other, copy key values and link new columns if missing
        throw new Error("not yet implemented");
    }
});


/**
 * Returns the default value of the attribute for most keywords
 * @name $.oAttribute#defaultValue
 * @type {bool}
 * @todo switch the implentation to types?
 * @example
 * // to reset an attribute to its default value:
 * // (mostly used for position/angle/skew parameters of pegs and drawing nodes)
 * var myAttribute = $.scn.nodes[0].attributes.position.x;
 *
 * myAttribute.setValue(myAttribute.defaultValue);
 */
Object.defineProperty($.oAttribute.prototype, "defaultValue", {
    get : function(){
        // TODO: we could use this to reset bones/deformers to their rest states
        var _keyword = this._keyword;

        switch (_keyword){
            case "OFFSET.X" :
            case "OFFSET.Y" :
            case "OFFSET.Z" :

            case "POSITION.X" :
            case "POSITION.Y" :
            case "POSITION.Z" :

            case "PIVOT.X":
            case "PIVOT.Y":
            case "PIVOT.Z":

            case "ROTATION.ANGLEX":
            case "ROTATION.ANGLEY":
            case "ROTATION.ANGLEZ":

            case "ANGLE":
            case "SKEW":

            case "SPLINE_OFFSET.X":
            case "SPLINE_OFFSET.Y":
            case "SPLINE_OFFSET.Z":

                return 0;

            case "SCALE.X" :
            case "SCALE.Y" :
            case "SCALE.Z" :
                return 1;

            case "OPACITY" :
                return 100;

            case "COLOR" :
                return new this.$.oColorValue();

            case "OFFSET.3DPATH":
                // pseudo oPathPoint
                // CFNote: is this supposed to be an object?
                // this is a fake object value that can be easily checked with a "==" operator.
                // oPathPoint will be converted to string for checking, and have the same format.
                // I made this to check if the value is default but I guess it's not ideal for assigning a default value, so maybe we should change it.
                return "{x:0, y:0, z:0}";

            default:
                return null; // for attributes that don't have a default value, we return null
        }
    }
});


// $.oAttribute Class methods

/**
 * Provides the keyframes of the attribute.
 * @return {$.oFrame[]}   The filtered keyframes.
 */
$.oAttribute.prototype.getKeyframes = function(){
    var _frames = this.frames;
    _frames = _frames.filter(function(x){return x.isKeyframe});
    return _frames;
}


/**
 * Provides the keyframes of the attribute.
 * @return {$.oFrame[]}   The filtered keyframes.
 * @deprecated For case consistency, keyframe will never have a capital F
 */
$.oAttribute.prototype.getKeyFrames = function(){
    this.$.debug("oAttribute.getKeyFrames is deprecated. Use oAttribute.getKeyframes instead.", this.$.DEBUG_LEVEL.ERROR);
    var _frames = this.frames;
    _frames = _frames.filter(function(x){return x.isKeyframe});
    return _frames;
}


/**
 * Recursively get all the columns linked to the attribute and its subattributes
 * @return {$.oColumn[]}    the list of columns linked to the subattributes
 */
$.oAttribute.prototype.getLinkedColumns = function(){
  var _columns = [];
  var _subAttributes = this.subAttributes;
  var _ownColumn = this.column;
  if (_ownColumn != null) _columns.push(_ownColumn);

  for (var i=0; i<_subAttributes.length; i++) {
    _columns = _columns.concat(_subAttributes[i].getLinkedColumns());
  }

  return _columns;
}


/**
 * Recursively sets an attribute to the same value as another. Both must have the same keyword.
 * @param {bool}    [duplicateColumns=false]      In the case that the attribute has a column, wether to duplicate the column before linking
 * @private
 */
$.oAttribute.prototype.setToAttributeValue = function(attributeToCopy, duplicateColumns){
  if (typeof duplicateColumns === 'undefined') var duplicateColumns = false;

  if (this.keyword !== attributeToCopy.keyword) return;
  var _subAttributes = this.subAttributes;

  var _column = attributeToCopy.column;
  if (_column == null) {
    var value = attributeToCopy.getValue();
    this.setValue(value);
  }else{
    if (duplicateColumns) var _column = _column.duplicate(this);
    this.column = _column;
  }

  var _subAttributesToCopy = attributeToCopy.subAttributes;
  for (var i=0; i<_subAttributes.length; i++){
    _subAttributes[i].setToAttributeValue(_subAttributesToCopy[i], duplicateColumns);
  }
}


//CFNote: Is it worth having a getValueType?
/**
 * Gets the value of the attribute at the given frame.
 * @param   {int}        frame                 The frame at which to set the value, if not set, assumes 1
 *
 * @return {object}      The value of the attribute in the native format of that attribute (contextual to the attribute).
 */
$.oAttribute.prototype.getValue = function (frame) {
    if (typeof frame === 'undefined') var frame = 1;
    this.$.debug('getting value of frame :'+frame+' of attribute: '+this._keyword+' of node '+this.node+' - type '+this.type, this.$.DEBUG_LEVEL.LOG)

    var _attr = this.attributeObject;
    var _type = this.type;
    var _value;
    var _column = this.column;

    // handling conversion of all return types into our own types
    switch (_type){
        case 'BOOL':
            _value = _attr.boolValueAt(frame)
            break;

        case 'INT':
            _value = _attr.intValueAt(frame)
            break;

        case 'DOUBLE':
        case 'DOUBLEVB':
            _value = _attr.doubleValueAt(frame)
            break;

        case 'STRING':
            _value = _attr.textValueAt(frame)
            break;

        case 'COLOR':
            _value = new this.$.oColorValue(_attr.colorValueAt(frame))
            break;

        case 'POSITION_2D':
            _value = _attr.pos2dValueAt(frame)
            _value = new this.$.oPoint(_value.x, _value.y)
            break;

        case 'POSITION_3D':
            _value = _attr.pos3dValueAt(frame)
            _value = new this.$.oPoint(_value.x, _value.y, _value.z)
            break;

        case 'SCALE_3D':
            _value = _attr.pos3dValueAt(frame)
            _value = new this.$.oPoint(_value.x, _value.y, _value.z)
            break;

        case 'PATH_3D':
            _attr = this.parentAttribute.attributeObject;
            var _frame = _column?(new this.$.oFrame(frame, _column)):(new this.$.oFrame(frame, _attr));
            if(_column && _frame.isKeyframe){
                _value = new this.$.oPathPoint(_column, _frame);
            }else{
                _value = _attr.pos3dValueAt(frame);
            }
            break;

        /*case 'DRAWING':
            // override with returning an oElement object
            this.$.debug( "DRAWING: " + this.keyword , this.$.DEBUG_LEVEL.LOG);

            value = _column.element;
            break;*/

        case 'ELEMENT':
            // an element always has a column, so we'll fetch it from there
            _value = column.getEntry(_column.uniqueName, 1, frame);

            // Convert to an instance of oDrawing, with a safety in case of psd import
            _drawing = _column.element.getDrawingByName(_value);
            if (_drawing) _value = _drawing;
            break;

        // TODO: How does QUATERNION_PATH work? subcolumns I imagine
        // TODO: How to get types SCALE_3D, ROTATION_3D, DRAWING, GENERIC_ENUM? -> maybe we don't need to, they don't have intrinsic values

        default:
            // enums, etc
            _value = _attr.textValueAt(frame);

            // in case of subattributes, create a fake string that can have properties so we can create getter setters on it for its subattrs
            if ( _attr.hasSubAttributes && _attr.hasSubAttributes() ){
                _value = { value:_value };
                _value.toString = function(){ return this.value };
            }else{
              var sub_attrs = node.getAttrList( this.node.path, 1, this._keyword );
              if( sub_attrs && sub_attrs.length>0 ){
                _value = { value:_value };
                _value.toString = function(){ return this.value };
              }
            }
    }

    return _value;
}


/**
 * Sets the value of the attribute at the given frame.
 * @param   {string}     value        The value to set on the attribute.
 * @param   {int}        [frame=1]    The frame at which to set the value, if not set, assumes 1
 */
$.oAttribute.prototype.setValue = function (value, frame) {
    var _attr = this.attributeObject;
    var _column = this.column;
    var _type = this.type;
    var _animate = false;

    if (!frame){
      // we don't animate
      var frame = 1;
    }else if (!_column){
      // generate a new column to be able to animate
      _column = this.addColumn();
    }

    if( _column ){
      _animate = true;
    }

    try{
      this.$.debug("setting attr "+this._keyword+" (type : "+this.type+") on node "+this.node+" to value "+JSON.stringify(value)+" at frame "+frame, this.$.DEBUG_LEVEL.LOG)
    }catch(err){
      this.$.debug("setting attr "+this._keyword+" at frame "+frame, this.$.DEBUG_LEVEL.LOG)
    };

    switch(_type){
        // TODO: sanitize input
        case "COLOR" :
            // doesn't work for burnin because it has color.Red, color.green etc and not .r .g ...
            value = (value instanceof this.$.oColorValue)?value: new this.$.oColorValue(value);
            value = ColorRGBA(value.r, value.g, value.b, value.a);
            _animate ? _attr.setValueAt(value, frame) : _attr.setValue(value);
            break;

        case "GENERIC_ENUM" :
            node.setTextAttr(this.node.path, this._keyword, frame, value);
            break;

        case "PATH_3D" :
          // check if frame is tied to a column or an attribute
          var _frame = _column?(new this.$.oFrame(frame, this.column)):(new this.$.oFrame(frame, _attr));
          if (_column){
            if (!_frame.isKeyframe) _frame.isKeyframe = true;
            var _point = new this.$.oPathPoint (this.column, _frame);
            _point.set(value);
          }else{
            // TODO: create keyframe?
            this.parentAttribute.setValue(value);
          }
          break;

        case "POSITION_2D":
            value = Point2d(value.x, value.y);
            _animate ? _attr.setValueAt(value, frame) : _attr.setValue(value);
            break;

        case "POSITION_3D":
            value = Point3d(value.x, value.y, value.z);
            _animate ? _attr.setValueAt(value, frame) : _attr.setValue(value);
            break;

        case "ELEMENT" :
            _column = this.column;
            value = (value instanceof this.$.oDrawing) ? value.name : value;
            column.setEntry(_column.uniqueName, 1, frame, value+"");
            break;

        case "QUATERNIONPATH" :
            // set quaternion paths as textattr until a better way is found

        default :
            try{
              _animate ? _attr.setValueAt( value, frame ) : _attr.setValue( value );
            }catch(err){
              this.$.debug("error setting attr "+this._keyword+" value "+value+": "+err, this.$.DEBUG_LEVEL.DEBUG);
              this.$.debug("setting text attr "+this._keyword+" value "+value+" as textAttr ", this.$.DEBUG_LEVEL.ERROR);
              node.setTextAttr( this.node.path, this._keyword, frame, value );
            }
    }
}


/**
 * Adds a column with a default name, based on the attribute type.
 * If a column already exists, it returns it.
 * @returns {$.oColumn} the created column
 */
$.oAttribute.prototype.addColumn = function(){
  var _column = this.column;
  if (_column) return _column;

  if (this.hasSubAttributes){
    throw new Error("Can't create columns for attribute "+this.keyword+", column must be created for its subattributes.");
  }

  var _type = this.type;
  var _columnType = "";
  var _columnName = this.node.name+": "+this.name.replace(/\s/g, "_");

  switch(_type){
    case 'INT':
    case 'DOUBLE':
    case 'DOUBLEVB':
      _columnType = "BEZIER";
      break;

    case "QUATERNIONPATH" :
      _columnName = "QUARTERNION";
      break;

      case "PATH_3D" :
      _columnName = "3DPATH";
      break;

    case "ELEMENT" :
      _columnType = "DRAWING";
      _columnName = this.node.name;
      break;

    default :
      throw new Error("Can't create columns for attribute "+this.keyword+", not supported by attribute type '"+_type+"'");
  }

  var _column = this.$.scn.addColumn(_columnType, _columnName);
  this.column = _column;

  if (!this.column) {
    _column.remove();
    throw new Error("Can't create columns for attribute "+this.keyword+", animation not supported.");
  }

  return this.column;
}


/**
 * Gets the value of the attribute at the given frame.
 * @param   {int}        frame                 The frame at which to set the value, if not set, assumes 1
 * @deprecated use oAttribute.getValue(frame) instead (see: function names as verbs)
 * @return {object}      The value of the attribute in the native format of that attribute (contextual to the attribute).
 */
$.oAttribute.prototype.value = function(frame){
  return this.getValue( frame );
}


/**
 * Represents an oAttribute object in string form
 * @private
 * @returns {string}
 */
$.oAttribute.prototype.toString = function(){
  return "[object $.oAttribute '"+this.keyword+(this.subAttributes.length?"' subAttributes: "+this.subAttributes.map(function(x){return x.shortKeyword}):"")+"]";
}