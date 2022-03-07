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
//        $.oPathPoint class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oPathPoint class.
 * @constructor
 * @classdesc  The $.oPathPoint Class represents a point on a column of type 3DPath. This class is used to access information about the curve that this point belongs to.
 * @param   {oColumn}                  oColumnObject         The 3DPath column that contains this information
 * @param   {oFrame}                   oFrameObject          The frame on which the point is placed
 *
 * @property {oColumn}                 column                The column this point belongs to
 * @property {oFrame}                  frame                 The frame on which the point is placed.
 */
$.oPathPoint = function(oColumnObject, oFrameObject){
    this.column = oColumnObject;
    this.frame = oFrameObject;
}


/**
 * The keyframe index of the frame/key at this point.
 * @name $.oPathPoint#pointIndex
 * @type {int}
 */
Object.defineProperty($.oPathPoint.prototype, 'pointIndex', {
    get : function(){
         return this.frame.keyframeIndex;
    }
})


/**
 * The X value of the path element.
 * @name $.oPathPoint#x
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'x', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         var _x = func.pointXPath3d(_column, _index);

         return _x;
    },

    set : function(newX){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;

        func.setPointPath3d (_column, _index, newX, this.y, this.z, this.tension, this.continuity, this.bias)
    }
})


/**
 * The Y value of the path element.
 * @name $.oPathPoint#y
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'y', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         var _y = func.pointYPath3d (_column, _index);

         return _y;
    },

    set : function(newY){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;

        func.setPointPath3d (_column, _index, this.x, newY, this.z, this.tension, this.continuity, this.bias)
    }
})


/**
 * The Z value of the path element.
 * @name $.oPathPoint#z
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'z', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         var _z = func.pointZPath3d (_column, _index);

         return _z;
    },

    set : function(newZ){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;

        func.setPointPath3d (_column, _index, this.x, this.y, newZ, this.tension, this.continuity, this.bias)
    }
})


/**
 * The tension at the current keyframe point.
 * @name $.oPathPoint#tension
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'tension', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         return func.pointTensionPath3d (_column, _index);
    },

    set : function(newTension){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;

        func.setPointPath3d (_column, _index, this.x, this.y, this.z, newTension, this.continuity, this.bias)
    }
})


/**
 * The continuity at the current keyframe point.
 * @name $.oPathPoint#continuity
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'continuity', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         return func.pointContinuityPath3d (_column, _index);
    },

    set : function(newContinuity){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;
        func.setPointPath3d (_column, _index, this.x, this.y, this.z, this.tension, newContinuity, this.bias)
    }

})


/**
 * The bias at the current keyframe point.
 * @name $.oPathPoint#bias
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'bias', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         return func.pointBiasPath3d (_column, _index);
    },

    set : function(newBias){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;
        var _point = this.point;
        func.setPointPath3d (_column, _index, this.x, this.y, this.z, this.tension, this.continuity, newBias)
    }

})


/**
 * The bezier lock at the current keyframe point.
 * @name $.oPathPoint#lock
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'lock', {
    get : function(){
         var _column = this.column.uniqueName;
         var _index = this.pointIndex;
         return func.pointLockedAtFrame (_column, _index);
    },

    set : function(newLockedFrame){
        var _column = this.column.uniqueName;
        var _index = this.pointIndex;

        throw new Error("$.oPathPoint.lock (set) - not yet implemented")
    }
})


/**
 * The velocity at the current keyframe point.
 * @name $.oPathPoint#velocity
 * @type {float}
 */
Object.defineProperty($.oPathPoint.prototype, 'velocity', {
    get : function(){
         var _column = this.column.uniqueName;
         return column.getEntry(this.column.uniqueName, 4, this.frame.frameNumber)
    },

    set : function(newVelocity){
        var _column = this.column.uniqueName;
        return column.setEntry(this.column.uniqueName, 4, this.frame.frameNumber, newVelocity)
    }
})


// $.oPathPoint class methods

/**
 * Matches this path point to the provided one.
 * @param   {$.oPathPoint}    pseudoPathPoint                The path point object to match this to.
 */
$.oPathPoint.prototype.set = function( pseudoPathPoint ){
    // Set a point by providing all values in an object corresponding to a dumb $.oPathPoint object with static values for each property;
    var _point = pseudoPathPoint;

    // default values for missing values in pseudoPathPoint
    var _x = (_point.x != undefined)?_point.x:0.0;
    var _y = (_point.y != undefined)?_point.y:0.0;
    var _z = (_point.z != undefined)?_point.z:0.0;
    var _tension = (_point.tension != undefined)?_point.tension:0.0;
    var _continuity = (_point.continuity != undefined)?_point.continuity:0.0;
    var _bias = (_point.bias != undefined)?_point.bias:0.0;

    var _column = this.column.uniqueName;
    var _index = this.pointIndex;

    func.setPointPath3d (_column, _index, _x, _y, _z, _tension, _continuity, _bias);
}

/**
 * Converts the pathpoint to a string.
 * @return {string}    The pathpoint represented as a string.
 */
$.oPathPoint.prototype.toString = function(){
    return "{x:"+this.x+", y:"+this.y+", z:"+this.z+"}"
}