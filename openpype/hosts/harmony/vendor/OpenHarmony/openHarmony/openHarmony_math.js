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
//          $.oPoint class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////



/**
 * The $.oPoint helper class - representing a 3D point.
 * @constructor
 * @classdesc  $.oPoint Base Class
 * @param     {float}              x                              Horizontal coordinate
 * @param     {float}              y                              Vertical coordinate
 * @param     {float}             [z]                             Depth Coordinate
 *
 * @property     {float}           x                              Horizontal coordinate
 * @property     {float}           y                              Vertical coordinate
 * @property     {float}           z                              Depth Coordinate
 */
$.oPoint = function(x, y, z){
    if (typeof z === 'undefined') var z = 0;

    this._type = "point";

    this.x = x;
    this.y = y;
    this.z = z;
}

/**
 * @name $.oPoint#polarCoordinates
 * an object containing {angle (float), radius (float)} values that represents polar coordinates (angle in radians) for the point's x and y value (z not yet supported)
 */
Object.defineProperty( $.oPoint.prototype, 'polarCoordinates', {
  get: function(){
    var _angle = Math.atan2(this.y, this.x)
    var _radius = Math.sqrt(this.x*this.x+this.y*this.y)
    return {angle: _angle, radius: _radius};
  },

  set: function(polarPoint){
    var _angle = polarPoint.angle;
    var _radius = polarPoint.radius;
    var _x = Math.cos(_angle)*_radius;
    var _y = Math.sin(_angle)*_radius;
    this.x = _x;
    this.y = _y;
  }
});


/**
 * Translate the point by the provided values.
 * @param   {int}       x                  the x value to move the point by.
 * @param   {int}       y                  the y value to move the point by.
 * @param   {int}       z                  the z value to move the point by.
 *
 * @returns { $.oPoint }                   Returns self (for inline addition).
 */
$.oPoint.prototype.translate = function( x, y, z){
  if (typeof x === 'undefined') var x = 0;
  if (typeof y === 'undefined') var y = 0;
  if (typeof z === 'undefined') var z = 0;

  this.x += x;
  this.y += y;
  this.z += z;

  return this;
}

/**
 * Translate the point by the provided values.
 * @param   {int}       x                  the x value to move the point by.
 * @param   {int}       y                  the y value to move the point by.
 * @param   {int}       z                  the z value to move the point by.
 *
 * @return: { $.oPoint }                   Returns self (for inline addition).
 */
 $.oPoint.prototype.add = function( x, y, z ){
  if (typeof x === 'undefined') var x = 0;
  if (typeof y === 'undefined') var y = 0;
  if (typeof z === 'undefined') var z = 0;

  var x = this.x + x;
  var y = this.y + y;
  var z = this.z + z;

  return new this.$.oPoint(x, y, z);
}

/**
 * The distance between two points.
 * @param {$.oPoint}     point            the other point to calculate the distance from.
 * @returns {float}
 */
$.oPoint.prototype.distance = function ( point ){
  var distanceX = point.x-this.x;
  var distanceY = point.y-this.y;
  var distanceZ = point.z-this.z;

  return Math.sqrt(distanceX*distanceX + distanceY*distanceY + distanceZ*distanceZ)
}

/**
 * Adds the point to the coordinates of the current oPoint.
 * @param   {$.oPoint}       add_pt                The point to add to this point.
 * @returns { $.oPoint }                           Returns itself (for inline addition).
 */
$.oPoint.prototype.pointAdd = function( add_pt ){
  this.x += add_pt.x;
  this.y += add_pt.y;
  this.z += add_pt.z;

  return this;
}

/**
 * Adds the point to the coordinates of the current oPoint and returns a new oPoint with the result.
 * @param {$.oPoint}   oPoint                The point to add to this point.
 * @returns {$.oPoint}
 */
$.oPoint.prototype.addPoint = function( point ){
  var x = this.x + point.x;
  var y = this.y + point.y;
  var z = this.z + point.z;

  return new this.$.oPoint(x, y, z);
}


/**
 * Subtracts the point to the coordinates of the current oPoint.
 * @param   {$.oPoint}       sub_pt                The point to subtract to this point.
 * @returns { $.oPoint }                           Returns itself (for inline addition).
 */
$.oPoint.prototype.pointSubtract = function( sub_pt ){
  this.x -= sub_pt.x;
  this.y -= sub_pt.y;
  this.z -= sub_pt.z;

  return this;
}


/**
 * Subtracts the point to the coordinates of the current oPoint and returns a new oPoint with the result.
 * @param {$.oPoint}   point                The point to subtract to this point.
 * @returns {$.oPoint} a new independant oPoint.
 */
$.oPoint.prototype.subtractPoint = function( point ){
  var x = this.x - point.x;
  var y = this.y - point.y;
  var z = this.z - point.z;

  return new this.$.oPoint(x, y, z);
}

/**
 * Multiply all coordinates by this value.
 * @param   {float}       float_val                Multiply all coordinates by this value.
 *
 * @returns { $.oPoint }                           Returns itself (for inline addition).
 */
$.oPoint.prototype.multiply = function( float_val ){
  this.x *= float_val;
  this.y *= float_val;
  this.z *= float_val;

  return this;
}

/**
 * Divides all coordinates by this value.
 * @param   {float}       float_val                Divide all coordinates by this value.
 *
 * @returns { $.oPoint }                           Returns itself (for inline addition).
 */
$.oPoint.prototype.divide = function( float_val ){
  this.x /= float_val;
  this.y /= float_val;
  this.z /= float_val;

  return this;
}

/**
 * Find average of provided points.
 * @param   {$.oPoint[]}       point_array         The array of points to get the average.
 *
 * @returns { $.oPoint }                           Returns the $.oPoint average of provided points.
 */
$.oPoint.prototype.pointAverage = function( point_array ){
  var _avg = new this.$.oPoint( 0.0, 0.0, 0.0 );
  for (var x=0; x<point_array.length; x++) {
    _avg.pointAdd(point_array[x]);
  }
  _avg.divide(point_array.length);

  return _avg;
}


/**
 * Converts a Drawing point coordinate into a scene coordinate, as used by pegs (since drawings are 2D, z is untouched)
 * @returns {$.oPoint}
 */
$.oPoint.prototype.convertToSceneCoordinates = function () {
  return new this.$.oPoint(this.x/this.$.scene.fieldVectorResolutionX, this.y/this.$.scene.fieldVectorResolutionY, this.z);
}


/**
 * Converts a scene coordinate point into a Drawing space coordinate, as used by Drawing tools and $.oShape (since drawings are 2D, z is untouched)
 * @returns {$.oPoint}
 */
$.oPoint.prototype.convertToDrawingSpace = function () {
  return new this.$.oPoint(this.x * this.$.scene.fieldVectorResolutionX, this.y * this.$.scene.fieldVectorResolutionY, this.z);
}


/**
 * Uses the scene settings to convert this as a worldspace point into an OpenGL point, used in underlying transformation operations in Harmony.
 * OpenGL units have a square aspect ratio and go from -1 to 1 vertically in the camera field.
 * @returns nothing
 */
$.oPoint.prototype.convertToOpenGL = function(){

  var qpt = scene.toOGL( new Point3d( this.x, this.y, this.z ) );

  this.x = qpt.x;
  this.y = qpt.y;
  this.z = qpt.z;

}


/**
 * Uses the scene settings to convert this as an OpenGL point into a Harmony worldspace point.
 * @returns nothing
 */
$.oPoint.prototype.convertToWorldspace = function(){

  var qpt = scene.fromOGL( new Point3d( this.x, this.y, this.z ) );

  this.x = qpt.x;
  this.y = qpt.y;
  this.z = qpt.z;

}


/**
 * Linearily Interpolate between this (0.0) and the provided point (1.0)
 * @param   {$.oPoint}       point                The target point at 100%
 * @param   {double}       perc                 0-1.0 value to linearily interp
 *
 * @return: { $.oPoint }                          The interpolated value.
 */
$.oPoint.prototype.lerp = function( point, perc ){
  var delta = new this.$.oPoint( point.x, point.y, point.z );

  delta = delta.pointSubtract( this );
  delta.multiply( perc );
  delta.pointAdd( this );

  return delta;
}


$.oPoint.prototype.toString = function(){
  return this._type+": {x:"+this.x+", y:"+this.y+", z:"+this.z+"}";
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//            $.oBox class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////



/**
 * The $.oBox helper class - representing a 2D box.
 * @constructor
 * @classdesc  $.oBox Base Class
 * @param      {float}       left                             left horizontal bound
 * @param      {float}       top                              top vertical bound
 * @param      {float}       right                            right horizontal bound
 * @param      {float}       bottom                           bottom vertical bound
 *
 * @property      {float}       left                             left horizontal bound
 * @property      {float}       top                              top vertical bound
 * @property      {float}       right                            right horizontal bound
 * @property      {float}       bottom                           bottom vertical bound
 */
$.oBox = function( left, top, right, bottom ){
  this._type = "box";

  if (typeof top === 'undefined') var top = Infinity
  if (typeof left === 'undefined') var left = Infinity
  if (typeof right === 'undefined') var right = -Infinity
  if (typeof bottom === 'undefined') var bottom = -Infinity

  this.top = top;
  this.left = left;
  this.right = right;
  this.bottom = bottom;
}


/**
 * The width of the box.
 * @name $.oBox#width
 * @type {float}
 */
Object.defineProperty($.oBox.prototype, 'width', {
  get : function(){
    return this.right - this.left + 1; //Inclusive size.
  }
})


/**
 * The height of the box.
 * @name $.oBox#height
 * @type {float}
 */
Object.defineProperty($.oBox.prototype, 'height', {
  get : function(){
    return this.bottom - this.top;
  }
})


/**
 * The center of the box.
 * @name $.oBox#center
 * @type {$.oPoint}
 */
Object.defineProperty($.oBox.prototype, 'center', {
  get : function(){
    return new this.$.oPoint(this.left+this.width/2, this.top+this.height/2);
  }
})


/**
 * Adds the input box to the bounds of the current $.oBox.
 * @param   {$.oBox}       box                The $.oBox to include.
 */
$.oBox.prototype.include = function(box){
  if (box.left < this.left) this.left = box.left;
  if (box.top < this.top) this.top = box.top;
  if (box.right > this.right) this.right = box.right;
  if (box.bottom > this.bottom) this.bottom = box.bottom;
}


/**
 * Checks wether the box contains another $.oBox.
 * @param   {$.oBox}       box                The $.oBox to check for.
 * @param   {bool}         [partial=false]    wether to accept partially contained boxes.
 */
$.oBox.prototype.contains = function(box, partial){
  if (typeof partial === 'undefined') var partial = false;

  var fitLeft = (box.left >= this.left);
  var fitTop = (box.top >= this.top);
  var fitRight =(box.right <= this.right);
  var fitBottom = (box.bottom <= this.bottom);

  if (partial){
    return (fitLeft || fitRight) && (fitTop || fitBottom);
  }else{
    return fitLeft && fitRight && fitTop && fitBottom;
  }

}

/**
 * Adds the bounds of the nodes to the current $.oBox.
 * @param   {oNode[]}       oNodeArray                An array of nodes to include in the box.
 */
$.oBox.prototype.includeNodes = function(oNodeArray){
  // convert to array if only one node is passed
  if (!Array.isArray(oNodeArray)) oNodeArray = [oNodeArray];

  for (var i in oNodeArray){
     var _node = oNodeArray[i];
     var _nodeBox = _node.bounds;
     this.include(_nodeBox);
  }
}

/**
 * @private
 */
$.oBox.prototype.toString = function(){
  return "{top:"+this.top+", right:"+this.right+", bottom:"+this.bottom+", left:"+this.left+"}"
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oMatrix class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * The $.oMatrix constructor.
 * @constructor
 * @classdesc The $.oMatrix is a subclass of the native Matrix4x4 object from Harmony. It has the same methods and properties plus the ones listed here.
 * @param {Matrix4x4} matrixObject a matrix object to initialize the instance from
 */
$.oMatrix = function(matrixObject){
  Matrix4x4.constructor.call(this);
  if (matrixObject){
    log(matrixObject)
    this.m00 = matrixObject.m00;
    this.m01 = matrixObject.m01;
    this.m02 = matrixObject.m02;
    this.m03 = matrixObject.m03;
    this.m10 = matrixObject.m10;
    this.m11 = matrixObject.m11;
    this.m12 = matrixObject.m12;
    this.m13 = matrixObject.m13;
    this.m20 = matrixObject.m20;
    this.m21 = matrixObject.m21;
    this.m22 = matrixObject.m22;
    this.m23 = matrixObject.m23;
    this.m30 = matrixObject.m30;
    this.m31 = matrixObject.m31;
    this.m32 = matrixObject.m32;
    this.m33 = matrixObject.m33;
  }
}
$.oMatrix.prototype = Object.create(Matrix4x4.prototype)


/**
 * A 2D array that contains the values from the matrix, rows by rows.
 * @name $.oMatrix#values
 * @type {Array}
 */
Object.defineProperty($.oMatrix.prototype, "values", {
  get:function(){
    return [
      [this.m00, this.m01, this.m02, this.m03],
      [this.m10, this.m11, this.m12, this.m13],
      [this.m20, this.m21, this.m22, this.m23],
      [this.m30, this.m31, this.m32, this.m33],
    ]
  }
})


/**
 * @private
 */
$.oMatrix.prototype.toString = function(){
  return "< $.oMatrix object : \n"+this.values.join("\n")+">";
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oVector class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oVector constructor.
 * @constructor
 * @classdesc The $.oVector is a replacement for the Vector3d objects of Harmony.
 * @param {float} x a x coordinate for this vector.
 * @param {float} y a y coordinate for this vector.
 * @param {float} [z=0] a z coordinate for this vector. If ommited, will be set to 0 and vector will be 2D.
 */
$.oVector = function(x, y, z){
  if (typeof z === "undefined" || isNaN(z)) var z = 0;

  // since Vector3d doesn't have a prototype, we need to cheat to subclass it.
  this._vector = new Vector3d(x, y, z);
}


/**
 * The X Coordinate of the vector.
 * @name $.oVector#x
 * @type {float}
 */
Object.defineProperty($.oVector.prototype, "x", {
  get: function(){
    return this._vector.x;
  },
  set: function(newX){
    this._vector.x = newX;
  }
})


/**
 * The Y Coordinate of the vector.
 * @name $.oVector#y
 * @type {float}
 */
Object.defineProperty($.oVector.prototype, "y", {
  get: function(){
    return this._vector.y;
  },
  set: function(newY){
    this._vector.y = newY;
  }
})


/**
 * The Z Coordinate of the vector.
 * @name $.oVector#z
 * @type {float}
 */
Object.defineProperty($.oVector.prototype, "z", {
  get: function(){
    return this._vector.z;
  },
  set: function(newX){
    this._vector.z = newX;
  }
})


/**
 * The length of the vector.
 * @name $.oVector#length
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVector.prototype, "length", {
  get: function(){
    return this._vector.length();
  }
})


/**
 * @static
 * A function of the oVector class (not oVector objects) that gives a vector from two points.
 */
$.oVector.fromPoints = function(pointA, pointB){
  return new $.oVector(pointB.x-pointA.x, pointB.y-pointA.y, pointB.z-pointA.z);
}


/**
 * Adds another vector to this one.
 * @param {$.oVector} vector2
 * @returns {$.oVector} returns itself.
 */
$.oVector.prototype.add = function (vector2){
  this.x += vector2.x;
  this.y += vector2.y;
  this.z += vector2.z;

  return this;
}


/**
 * Multiply this vector coordinates by a number (scalar multiplication)
 * @param {float} num
 * @returns {$.oVector} returns itself
 */
$.oVector.prototype.multiply = function(num){
  this.x = num*this.x;
  this.y = num*this.y;
  this.z = num*this.z;

  return this;
}


/**
 * The dot product of the two vectors
 * @param {$.oVector} vector2 a vector object.
 * @returns {float} the resultant vector from the dot product of the two vectors.
 */
$.oVector.prototype.dot = function(vector2){
  var _dot = this._vector.dot(new Vector3d(vector2.x, vector2.y, vector2.z));
  return _dot;
}

/**
 * The cross product of the two vectors
 * @param {$.oVector} vector2 a vector object.
 * @returns {$.oVector} the resultant vector from the dot product of the two vectors.
 */
$.oVector.prototype.cross = function(vector2){
  var _cross = this._vector.cross(new Vector3d(vector2.x, vector2.y, vector2.z));
  return new this.$.oVector(_cross.x, _cross.y, _cross.z);
}

/**
 * The projected vectors resulting from the operation
 * @param {$.oVector} vector2 a vector object.
 * @returns {$.oVector} the resultant vector from the projection of the current vector.
 */
$.oVector.prototype.project = function(vector2){
  var _projection = this._vector.project(new Vector3d(vector2.x, vector2.y, vector2.z));
  return new this.$.oVector(_projection.x, _projection.y, _projection.z);
}

/**
 * Normalize the vector.
 * @returns {$.oVector} returns itself after normalization.
 */
$.oVector.prototype.normalize = function(){
  this._vector.normalize();
  return this;
}


/**
 * The angle of this vector in radians.
 * @name $.oVector#angle
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVector.prototype, "angle", {
  get: function(){
    return Math.atan2(this.y, this.x);
  }
})


/**
 * The angle of this vector in degrees.
 * @name $.oVector#degreesAngle
 * @type {float}
 * @readonly
 */
Object.defineProperty($.oVector.prototype, "degreesAngle", {
  get: function(){
    return this.angle * (180 / Math.PI);
  }
})


/**
 * @private
 */
$.oVector.prototype.toString = function(){
  return "<$.oVector ["+this.x+", "+this.y+", "+this.z+"]>";
}

