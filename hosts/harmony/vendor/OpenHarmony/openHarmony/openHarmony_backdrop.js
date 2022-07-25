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
//        $.oBackdrop class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for  the $.oBackdrop class.
 * @constructor
 * @classdesc  The $.oBackdrop Class represents a backdrop in the node view, and allows users to add, remove and modify existing Backdrops. Accessing these functions is done through the oGroupNode class.
 * @param   {string}                 groupPath                   The path to the object in which this backdrop is placed.
 * @param   {backdropObject}         backdropObject              The harmony-internal backdrop object associated with this oBackdrop.
 * @example
 * function createColoredBackdrop(){
 *  // This script will prompt for a color and create a backdrop around the selection
 *  $.beginUndo()
 *
 *  var doc = $.scn; // grab the scene
 *  var nodes = doc.selectedNodes; // grab the selection
 *
 *  if(!nodes) return    // exit the function if no nodes are selected
 *
 *  var color = pickColor(); // prompt for color
 *
 *  var group = doc.root // get the group to add the backdrop to
 *  var backdrop = group.addBackdropToNodes(nodes, "BackDrop", "", color)
 *
 *  $.endUndo();
 *
 *  // function to get the color chosen by the user
 *  function pickColor(){
 *    var d = new QColorDialog;
 *    d.exec();
 *    var color = d.selectedColor();
 *    return new $.oColorValue({r:color.red(), g:color.green(), b:color.blue(), a:color.alpha()})
 *  }
 * }
 */
$.oBackdrop = function( groupPath, backdropObject ){
  this.group = ( groupPath instanceof this.$.oGroupNode )? groupPath.path: groupPath;
	this.backdropObject = backdropObject;
}


/**
 * The index of this backdrop in the current group.
 * @name $.oBackdrop#index
 * @type {int}
 */
Object.defineProperty($.oBackdrop.prototype, 'index', {
    get : function(){
      var _groupBackdrops = Backdrop.backdrops(this.group).map(function(x){return x.title.text})
		  return _groupBackdrops.indexOf(this.title)
    }
})


/**
 * The title of the backdrop.
 * @name $.oBackdrop#title
 * @type {string}
 */
Object.defineProperty($.oBackdrop.prototype, 'title', {
  get : function(){
    var _title = this.backdropObject.title.text;
    return _title;
  },

  set : function(newTitle){
    var _backdrops = Backdrop.backdrops(this.group);

    // incrementing to prevent two backdrops to have the same title
    var names = _backdrops.map(function(x){return x.title.text})
    var count = 0;
    var title = newTitle

    while (names.indexOf(title) != -1){
      count++;
      title = newTitle+"_"+count;
    }
    newTitle = title;

    var _index = this.index;

    _backdrops[_index].title.text = newTitle;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The body text of the backdrop.
 * @name $.oBackdrop#body
 * @type {string}
 */
Object.defineProperty($.oBackdrop.prototype, 'body', {
    get : function(){
         var _title = this.backdropObject.description.text;
         return _title;
    },

    set : function(newBody){
        var _backdrops = Backdrop.backdrops(this.group);

		var _index = this.index;
        _backdrops[_index].description.text = newBody;

		this.backdropObject = _backdrops[_index];
        Backdrop.setBackdrops(this.group, _backdrops);
    }
})


/**
 * The title font of the backdrop in form { family:"familyName", "size":int, "color": oColorValue }
 * @name $.oBackdrop#titleFont
 * @type {object}
 */
Object.defineProperty($.oBackdrop.prototype, 'titleFont', {
    get : function(){
         var _font = {family : this.backdropObject.title.font,
                      size : this.backdropObject.title.size,
                      color : ( new oColorValue() ).parseColorFromInt(this.backdropObject.title.color)}
         return _font;
    },

    set : function(newFont){
        var _backdrops = Backdrop.backdrops(this.group);
		var _index = this.index;

        _backdrops[_index].title.font = newFont.family;
        _backdrops[_index].title.size = newFont.size;
        _backdrops[_index].title.color = newFont.color.toInt();

        this.backdropObject = _backdrops[_index];
        Backdrop.setBackdrops(this.group, _backdrops);
    }
})


/**
 * The body font of the backdrop in form { family:"familyName", "size":int, "color": oColorValue }
 * @name $.oBackdrop#bodyFont
 * @type {object}
 */
Object.defineProperty($.oBackdrop.prototype, 'bodyFont', {
    get : function(){
         var _font = {family : this.backdropObject.description.font,
                      size : this.backdropObject.description.size,
                      color : ( new oColorValue() ).parseColorFromInt(this.backdropObject.description.color)}
         return _font;
    },

    set : function(newFont){
        var _backdrops = Backdrop.backdrops(this.group);
		var _index = this.index;

        _backdrops[_index].title.font = newFont.family;
        _backdrops[_index].title.size = newFont.size;
        _backdrops[_index].title.color = newFont.color.toInt();

		this.backdropObject = _backdrops[_index];
        Backdrop.setBackdrops(this.group, _backdrops);
    }
})


/**
 * The nodes contained within this backdrop
 * @name $.oBackdrop#parent
 * @type {$.oNode[]}
 * @readonly
 */
 Object.defineProperty($.oBackdrop.prototype, 'parent', {
  get : function(){
    if (!this.hasOwnProperty("_parent")){
      this._parent = this.$.scn.getNodeByPath(this.group);
    }
    return this._parent
  }
})


/**
 * The nodes contained within this backdrop
 * @name $.oBackdrop#nodes
 * @type {$.oNode[]}
 * @readonly
 */
Object.defineProperty($.oBackdrop.prototype, 'nodes', {
  get : function(){
    var _nodes = this.parent.nodes;
    var _bounds = this.bounds;
    _nodes = _nodes.filter(function(x){
      return _bounds.contains(x.bounds);
    })

    return _nodes;
  }
})

/**
 * The position of the backdrop on the horizontal axis.
 * @name $.oBackdrop#x
 * @type {float}
 */
Object.defineProperty($.oBackdrop.prototype, 'x', {
  get : function(){
    var _x = this.backdropObject.position.x;
    return _x;
  },

  set : function(newX){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.x = newX;

    this.backdropObject = _backdrops[_index];
        Backdrop.setBackdrops(this.group, _backdrops);
    }
})


/**
 * The position of the backdrop on the vertical axis.
 * @name $.oBackdrop#y
 * @type {float}
 */
Object.defineProperty($.oBackdrop.prototype, 'y', {
  get : function(){
    var _y = this.backdropObject.position.y;
    return _y;
  },

  set : function(newY){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.y = newY;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The width of the backdrop.
 * @name $.oBackdrop#width
 * @type {float}
 */
Object.defineProperty($.oBackdrop.prototype, 'width', {
  get : function(){
    var _width = this.backdropObject.position.w;
    return _width;
  },

  set : function(newWidth){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.w = newWidth;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The height of the backdrop.
 * @name $.oBackdrop#height
 * @memberof $.oBackdrop#
 * @type {float}
 */
Object.defineProperty($.oBackdrop.prototype, 'height', {
  get : function(){
    var _height = this.backdropObject.position.h;
    return _height;
  },

  set : function(newHeight){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.h = newHeight;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The position of the backdrop.
 * @name $.oBackdrop#position
 * @type {oPoint}
 */
Object.defineProperty($.oBackdrop.prototype, 'position', {
  get : function(){
    var _position = new oPoint(this.x, this.y, this.index)
    return _position;
  },

  set : function(newPos){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.x = newPos.x;
    _backdrops[_index].position.y = newPos.y;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The bounds of the backdrop.
 * @name $.oBackdrop#bounds
 * @type {oBox}
 */
Object.defineProperty($.oBackdrop.prototype, 'bounds', {
  get : function(){
    var _box = new oBox(this.x, this.y, this.width+this.x, this.height+this.y)
    return _box;
  },

  set : function(newBounds){
    var _backdrops = Backdrop.backdrops(this.group);
    var _index = this.index;

    _backdrops[_index].position.x = newBounds.top;
    _backdrops[_index].position.y = newBounds.left;
    _backdrops[_index].position.w = newBounds.width;
    _backdrops[_index].position.h = newBounds.height;

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})


/**
 * The color of the backdrop.
 * @name $.oBackdrop#color
 * @type {oColorValue}
 */
Object.defineProperty($.oBackdrop.prototype, 'color', {
  get : function(){
    var _color = this.backdropObject.color;
    // TODO: get the rgba values from the int
    return _color;
  },

  set : function(newOColorValue){
    var _color = new oColorValue(newOColorValue);
    var _index = this.index;

    var _backdrops = Backdrop.backdrops(this.group);
    _backdrops[_index].color = _color.toInt();

    this.backdropObject = _backdrops[_index];
    Backdrop.setBackdrops(this.group, _backdrops);
  }
})