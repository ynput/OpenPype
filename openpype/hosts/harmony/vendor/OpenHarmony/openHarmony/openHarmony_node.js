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

include(specialFolders.resource+"/scripts/TB_orderNetworkUp.js"  );
include(specialFolders.userScripts+"/TB_orderNetworkUp.js");       // for older versions of harmony

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oNode class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


//TODO: Smart pathing, network movement, better duplication handling
//TODO: Metadata, settings, aspect, camera peg, view.
//TODO: group's multi-in-ports, multi-out-port modules

/**
 * Constructor for $.oNode class
 * @classdesc
 * The oNode class represents a node in the Harmony scene. <br>
 * It holds the value of its position in the node view, and functions to link to other nodes, as well as set the attributes of the node.<br><br>
 * It uses a cache system, so a node for a given path will only be created once. <br>
 * If the nodes change path through other means than the openHarmony functions during the execution of the script, use oNode.invalidateCache() to create new nodes again.<br><br>
 * This constructor should not be invoqued by users, who should use $.scene.getNodeByPath() or $.scene.root.getNodeByName() instead.
 * @constructor
 * @param   {string}         path                          Path to the node in the network.
 * @param   {$.oScene}         [oSceneObject]                  Access to the oScene object of the DOM.
 * @see NodeType
 * @example
 * // To grab a node object from the scene, it's possible to create a new node object by calling the constructor:
 * var myNode = new $.oNode("Top/Drawing", $.scn)
 *
 * // However, most nodes will be grabbed directly from the scene object.
 * var doc = $.scn
 * var nodes = doc.nodes;                   // grabs the list of all the nodes in the scene
 *
 * // It's possible to grab a single node from the path in the scene
 * var myNode = doc.getNodeByPath("Top/Drawing")
 * var myNode = doc.$node("Top/Drawing")    // short synthax but same function
 *
 * // depending on the type of node, oNode objects returned by these functions can actually be an instance the subclasses
 * // oDrawingNode, oGroupNode, oPegNode...
 *
 * $.log(myNode instanceof $.oNode)           // true
 * $.log(myNode instanceof $.oDrawingNode)  // true
 *
 * // These other subclasses of nodes have other methods that are only shared by nodes of a certain type.
 *
 * // Not documented in this class, oNode objects have attributes which correspond to the values visible in the Layer Properties window.
 * // The attributes values can be accessed and set by using the dot notation on the oNode object:
 *
 * myNode.can_animate = false;
 * myNode.position.separate = true;
 * myNode.position.x = 10;
 *
 * // To access the oAttribute objects in the node, call the oNode.attributes object that contains them
 *
 * var attributes = myNode.attributes;
 */
$.oNode = function( path, oSceneObject ){
  var instance = this.$.getInstanceFromCache.call(this, path);
  if (instance) return instance;

  this._path = path;
  this.type  = node.type(this.path);
  this.scene = (typeof oSceneObject === 'undefined')?this.$.scene:oSceneObject;

  this._type = 'node';

  this.refreshAttributes();
}

/**
 * Initialize the attribute cache.
 * @private
 */
$.oNode.prototype.attributesBuildCache = function (){
  //Cache time can be used at later times, to check for auto-rebuild of caches. Not yet implemented.
  this._cacheTime = (new Date()).getTime();

  var _attributesList = node.getAttrList( this.path, 1 );
  var _attributes = {};

  for (var i in _attributesList){

      var _attribute = new this.$.oAttribute(this, _attributesList[i]);
      var _keyword = _attribute.keyword;

      _attributes[_keyword] = _attribute;
  }

  this._attributes_cached = _attributes;
}


/**
 * Private function to create attributes setters and getters as properties of the node
 * @private
 */
$.oNode.prototype.setAttrGetterSetter = function (attr, context){
    if (typeof context === 'undefined') context = this;
    // this.$.debug("Setting getter setters for attribute: "+attr.keyword+" of node: "+this.name, this.$.DEBUG_LEVEL.DEBUG)

    var _keyword = attr.shortKeyword;

    Object.defineProperty( context, _keyword, {
        enumerable : true,
        configurable : true,
        get : function(){
            // MessageLog.trace("getting attribute "+attr.keyword+". animated: "+(attr.column != null))
            var _subAttrs = attr.subAttributes;
            if (_subAttrs.length == 0){
                // if attribute has animation, return the frames
                if (attr.column != null) return attr.frames;
                // otherwise return the value
                var _value =  attr.getValue();
            }else{
                // if there are subattributes, create getter setters for each on the returned object
                // this means every result of attr.getValue must be an object.
                // For attributes that have a string return value, attr.getValue() actually returns a fake string object
                // which is an object with a value property and a toString() method returning the value.
                var _value = (attr.column != null)?new this.$.oList(attr.frames, 1):attr.getValue();
                for (var i in _subAttrs){
                    this.setAttrGetterSetter( _subAttrs[i], _value );
                }
            }
            return _value;
        },

        set : function(newValue){
            // this.$.debug("setting attribute through getter setter "+attr.keyword+" to value: "+newValue, this.$.DEBUG_LEVEL.DEBUG)
            // if attribute has animation, passed value must be a frame object
            var _subAttrs = attr.subAttributes;

            // setting the attribute directly if no subattributes are present, or if value is a color (exception)
            if (_subAttrs.length == 0 || attr.type == "COLOR"){
                if (attr.column != null) {
                    if (!newValue.hasOwnProperty("frameNumber")) {
                        // fallback to set frame 1
                        newValue = {value:newValue, frameNumber:1};
                    }
                    attr.setValue(newValue.value, newValue.frameNumber)
                }else{
                    return attr.setValue(newValue)
                }
            }else{
                var _frame = undefined;
                var _value = newValue;
                // dealing with value being an object with frameNumber for animated values
                if (attr.column != null) {
                    if (!(newValue instanceof oFrame)) {
                        // fallback to set frame 1
                        newValue = {value:newValue, frameNumber:1};
                    }

                    _frame = newValue.frameNumber;
                    _value = newValue.value;
                }

                // setting non animated attribute value
                for (var i in _subAttrs){
                    // set each subAttr individually based on corresponding values in the provided object
                    var _keyword = _subAttrs[i].shortKeyword;
                    if (_value.hasOwnProperty(_keyword)) _subAttrs[i].setValue(_value[_keyword], _frame);
                }
            }
        }
    });
};


/**
 * The derived path to the node.
 * @deprecated use oNode.path instead
 * @name $.oNode#fullPath
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oNode.prototype, 'fullPath', {
    get : function( ){
      return this._path;
    }
});


/**
 * The path of the node (includes all groups from 'Top' separated by forward slashes).
 * To change the path of a node, use oNode.moveToGroup()
 * @name $.oNode#path
 * @type {string}
 * @readonly
 */
Object.defineProperty($.oNode.prototype, 'path', {
    get : function( ){
      return this._path;
    }
});


/**
 * The type of the node.
 * @name $.oNode#type
 * @readonly
 * @type {string}
 */
Object.defineProperty( $.oNode.prototype, 'type', {
    get : function( ){
      return node.type( this.path );
    }
});


/**
 * Is the node a group?
 * @name $.oNode#isGroup
 * @readonly
 * @deprecated check if the node is an instance of oGroupNode instead
 * @type {bool}
 */
Object.defineProperty($.oNode.prototype, 'isGroup', {
    get : function( ){
      if( this.root ){
        //in a sense, its a group.
        return true;
      }

      return node.isGroup( this.path );
    }
});


/**
 * The $.oNode objects contained in this group. This is deprecated and was moved to oGroupNode
 * @DEPRECATED Use oGroupNode.children instead.
 * @name $.oNode#children
 * @readonly
 * @type {$.oNode[]}
 */
Object.defineProperty($.oNode.prototype, 'children', {
    get : function( ){
      if( !this.isGroup ){ return []; }

      var _children = [];
      var _subnodes = node.subNodes( this.path );
      for( var n=0; n<_subnodes.length; n++ ){
        _children.push( this.scene.getNodeByPath( _subnodes[n] ) );
      }

      return _children;
    },

    set : function( arr_children ){
      //Consider a way to have this group adopt the children, move content here?
      //this may be a bit tough to extend.
    }
});


/**
 * Does the node exist?
 * @name $.oNode#exists
 * @type {bool}
 * @readonly
 */
Object.defineProperty($.oNode.prototype, 'exists', {
    get : function(){
      if( this.type ){
        return true;
      }else{
        return false;
      }
    }
});


/**
 * Is the node selected?
 * @name $.oNode#selected
 * @type {bool}
 */
Object.defineProperty($.oNode.prototype, 'selected', {
    get : function(){
      for( var n=0;n<selection.numberOfNodesSelected;n++ ){
          if( selection.selectedNode(n) == this.path ){
            return true;
          }
      }

      return false;
    },

    //Add it to the selection.
    set : function( bool_exist ){
      if( bool_exist ){
        selection.addNodeToSelection( this.path );
      }else{
        selection.removeNodeFromSelection( this.path );
      }
    }

});


/**
 * The node's name.
 * @name $.oNode#name
 * @type {string}
 */
Object.defineProperty($.oNode.prototype, 'name', {
  get : function(){
     return node.getName(this.path);
  },

  set : function(newName){
    var _parent = node.parentNode(this.path);

    // create a node with the chosen name to get the safe name generated by Harmony
    var testName = node.add(_parent, newName, "", 0,0,0).split("/").pop()
    node.deleteNode(_parent + "/" + testName)

    // do the renaming and update the path
    node.rename(this.path, testName);
    this._path = _parent+'/'+testName;

    this.refreshAttributes();
  }
});


/**
 * The group containing the node.
 * @name $.oNode#group
 * @readonly
 * @type {oGroupNode}
 */
Object.defineProperty($.oNode.prototype, 'group', {
    get : function(){
         return this.scene.getNodeByPath( node.parentNode(this.path) )
    }
});


/**
 * The $.oNode object for the parent in which this node exists.
 * @name $.oNode#parent
 * @readonly
 * @type {$.oNode}
 */
Object.defineProperty( $.oNode.prototype, 'parent', {
    get : function(){
      if( this.root ){ return false; }

      return this.scene.getNodeByPath( node.parentNode( this.path ) );
    }
});


/**
 * Is the node enabled?
 * @name $.oNode#enabled
 * @type {bool}
 */
Object.defineProperty($.oNode.prototype, 'enabled', {
    get : function(){
         return node.getEnable(this.path)
    },

    set : function(enabled){
         node.setEnable(this.path, enabled)
    }
});


/**
 * Is the node locked?
 * @name $.oNode#locked
 * @type {bool}
 */
Object.defineProperty($.oNode.prototype, 'locked', {
    get : function(){
         return node.getLocked(this.path)
    },

    set : function(locked){
         node.setLocked(this.path, locked)
    }
});


/**
 * Is the node the root?
 * @name $.oNode#isRoot
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oNode.prototype, 'isRoot', {
    get : function(){
         return this.path == "Top"
    }
});



/**
 * The list of backdrops which contain this node.
 * @name $.oNode#containingBackdrops
 * @readonly
 * @type {$.oBackdrop[]}
 */
 Object.defineProperty($.oNode.prototype, 'containingBackdrops', {
  get : function(){
    var _backdrops = this.parent.backdrops;
    var _path = this.path;
    return _backdrops.filter(function(x){
      var _nodePaths = x.nodes.map(function(x){return x.path});
      return _nodePaths.indexOf(_path) != -1;
    })
  }
});


/**
 * The position of the node.
 * @name $.oNode#nodePosition
 * @type {oPoint}
 */
Object.defineProperty($.oNode.prototype, 'nodePosition', {
    get : function(){
      var _z = 0.0;
      try{ _z = node.coordZ(this.path); } catch( err ){this.$.debug("setting coordZ not implemented in Harmony versions before 17.", this.$.DEBUG_LEVEL.ERROR)}
      return new this.$.oPoint(node.coordX(this.path), node.coordY(this.path), _z );
    },

    set : function(newPosition){
        node.setCoord(this.path, newPosition.x, newPosition.y, newPosition.y);
    }
});


/**
 * The horizontal position of the node in the node view.
 * @name $.oNode#x
 * @type {float}
 */
Object.defineProperty($.oNode.prototype, 'x', {
    get : function(){
         return node.coordX(this.path)
    },

    set : function(x){
        var _pos = this.nodePosition;
        node.setCoord(this.path, x, _pos.y)
    }
});


/**
 * The vertical position of the node in the node view.
 * @name $.oNode#y
 * @type {float}
 */
Object.defineProperty($.oNode.prototype, 'y', {
    get : function(){
         return node.coordY(this.path)
    },

    set : function(y){
        var _pos = this.nodePosition;
        node.setCoord(this.path, _pos.x, y)
    }
});


/**
 * The depth position of the node in the node view.
 * @name $.oNode#z
 * @type {float}
 */
Object.defineProperty($.oNode.prototype, 'z', {
    get : function(){
        var _z = 0.0;
        try{ _z = node.coordZ(this.path); } catch( err ){ this.$.debug("setting coordZ not implemented in Harmony versions before 17.", this.$.DEBUG_LEVEL.ERROR)}

        return _z;
    },

    set : function(z){
        var _pos = this.nodePosition;
        node.setCoord( this.path, _pos.x, _pos.y, z );
    }
});


/**
 * The width of the node in the node view.
 * @name $.oNode#width
 * @readonly
 * @type {float}
 */
Object.defineProperty($.oNode.prototype, 'width', {
    get : function(){
         return node.width(this.path)
    }
});



/**
 * The height of the node in the node view.
 * @name $.oNode#height
 * @readonly
 * @type {float}
 */
Object.defineProperty($.oNode.prototype, 'height', {
    get : function(){
         return node.height(this.path)
    }
});



/**
 * The list of oNodeLinks objects descibing the connections to the inport of this node, in order of inport.
 * @name $.oNode#inLinks
 * @readonly
 * @deprecated returns $.oNodeLink instances but $.oLink is preferred. Use oNode.getInLinks() instead.
 * @type {$.oNodeLink[]}
 */
Object.defineProperty($.oNode.prototype, 'inLinks', {
    get : function(){
        var nodeRef = this;
        var newList = new this.$.oList( [], 0, node.numberOfInputPorts(this.path),
                                           function( listItem, index ){ return new this.$.oNodeLink( false, false, nodeRef, index, false ); },
                                           function(){ throw new ReferenceError("Unable to set inLinks"); },
                                           false
                                         );
        return newList;
    }
});


/**
 * The list of nodes connected to the inport of this node, in order of inport.
 * @name $.oNode#inNodes
 * @readonly
 * @type {$.oNode[]}
 * @deprecated returns $.oNodeLink instances but $.oLink is preferred. Use oNode.linkedInNodes instead.
*/
Object.defineProperty($.oNode.prototype, 'inNodes', {
    get : function(){
        var _inNodes = [];
        var _inPorts = this.inPorts;
        // TODO: ignore/traverse groups
        for (var i = 0; i < _inPorts; i++){
            var _node = this.getLinkedInNode(i);
            if (_node != null) _inNodes.push(_node)
        }
        return _inNodes;
    }
});


/**
 * The number of link ports on top of the node, connected or not.
 * @name $.oNode#inPorts
 * @readonly
 * @type {int}
*/
Object.defineProperty($.oNode.prototype, 'inPorts', {
  get : function(){
    return node.numberOfInputPorts(this.path);
  }
});


/**
 * The list of nodes connected to the outports of this node
 * @name $.oNode#outNodes
 * @readonly
 * @type {$.oNode[][]}
 * @deprecated  returns $.oNodeLink instances but $.oLink is preferred. Use oNode.linkedOutNodes instead.
*/
Object.defineProperty($.oNode.prototype, 'outNodes', {
    get : function(){
        var _outNodes = [];
        var _outPorts = this.outPorts;

        for (var i = 0; i < _outPorts; i++){
            var _outLinks = [];
            var _outLinksNumber = this.getOutLinksNumber(i);
            for (var j = 0; j < _outLinksNumber; j++){
                var _node = this.getLinkedOutNode(i, j);

                if (_node != null) _outLinks.push(_node);
            }

            //Always return the list of links for consistency.
            _outNodes.push(_outLinks);
        }
        return _outNodes;
    }
});


/**
 * The number of link ports at the bottom of the node, connected or not.
 * @name $.oNode#outPorts
 * @readonly
 * @type {int}
*/
Object.defineProperty($.oNode.prototype, 'outPorts', {
  get : function(){
    return node.numberOfOutputPorts(this.path);
  }
});


/**
 * The list of oNodeLinks objects descibing the connections to the outports of this node, in order of outport.
 * @name $.oNode#outLinks
 * @readonly
 * @type {$.oNodeLink[]}
 * @deprecated  returns $.oNodeLink instances but $.oLink is preferred. Use oNode.getOutLinks instead.
 */
Object.defineProperty($.oNode.prototype, 'outLinks', {
    get : function(){
        var nodeRef = this;

        var lookup_list = [];
        for (var i = 0; i < node.numberOfOutputPorts(this.path); i++){
          if( node.numberOfOutputLinks(this.path, i) > 0 ){
            for (var j = 0; j < node.numberOfOutputLinks(this.path, i); j++){
              lookup_list.push( [i,j] );
            }
          }else{
            lookup_list.push( [i,0] );
          }
        }

        var newList = new this.$.oList( [], 0, lookup_list.length,
                                           function( listItem, index ){ return new this.$.oNodeLink( nodeRef, lookup_list[index][0], false, false, lookup_list[index][1] ); },
                                           function(){ throw new ReferenceError("Unable to set inLinks"); },
                                           false
                                         );
        return newList;
    }
});


/**
 * The list of nodes connected to the inport of this node, as a flat list, in order of inport.
 * @name $.oNode#linkedOutNodes
 * @readonly
 * @type {$.oNode[]}
 */
Object.defineProperty($.oNode.prototype, 'linkedOutNodes', {
  get: function(){
    var _outNodes = this.getOutLinks().map(function(x){return x.inNode});
    return _outNodes;
  }
})


/**
 * The list of nodes connected to the inport of this node, as a flat list, in order of inport.
 * @name $.oNode#linkedInNodes
 * @readonly
 * @type {$.oNode[]}
 */
Object.defineProperty($.oNode.prototype, 'linkedInNodes', {
  get: function(){
    var _inNodes = this.getInLinks().map(function(x){return x.outNode});
    return _inNodes
  }
})


/**
 * The list of nodes connected to the inport of this node, in order of inport. Similar to oNode.inNodes
 * @name $.oNode#ins
 * @readonly
 * @type {$.oNode[]}
 * @deprecated alias for deprecated oNode.inNodes property
*/
Object.defineProperty($.oNode.prototype, 'ins', {
    get : function(){
      return this.inNodes;
    }
});


/**
 * The list of nodes connected to the outport of this node, in order of outport and links. Similar to oNode.outNodes
 * @name $.oNode#outs
 * @readonly
 * @type {$.oNode[][]}
 * @deprecated alias for deprecated oNode.outNodes property
*/
Object.defineProperty($.oNode.prototype, 'outs', {
    get : function(){
      return this.outNodes;
    }
});


/**
 * An object containing all attributes of this node.
 * @name $.oNode#attributes
 * @readonly
 * @type {oAttribute}
 * @example
 * // You can get access to the actual oAttribute object for a node parameter by using the dot notation:
 *
 * var myNode = $.scn.$node("Top/Drawing")
 * var drawingAttribute = myNode.attributes.drawing.element
 *
 * // from there, it's possible to set/get the value of the attribute, get the column, the attribute keyword etc.
 *
 * drawingAttribute.setValue ("1", 5);           // creating an exposure of drawing 1 at frame 5
 * var drawingColumn = drawingAttribute.column;  // grabbing the column linked to the attribute that holds all the animation
 * $.log(drawingAttribute.keyword);              // "DRAWING.ELEMENT"
 *
 * // for a more direct way to access an attribute, it's possible to also call:
 *
 * var drawingAttribute = myNode.getAttributeByName("DRAWING.ELEMENT");
*/
Object.defineProperty($.oNode.prototype, 'attributes', {
  get : function(){
      return this._attributes_cached;
  }
});


/**
 * The bounds of the node rectangle in the node view.
 * @name $.oNode#bounds
 * @readonly
 * @type {oBox}
*/
Object.defineProperty( $.oNode.prototype, 'bounds', {
  get : function(){
    return new this.$.oBox(this.x, this.y, this.x+this.width, this.y+this.height);
  }
});


/**
 * The transformation matrix of the node at the currentFrame.
 * @name $.oNode#matrix
 * @readonly
 * @type {oMatrix}
*/
Object.defineProperty( $.oNode.prototype, 'matrix', {
  get : function(){
    return this.getMatrixAtFrame(this.scene.currentFrame);
  }
});


/**
 * The list of all columns linked across all the attributes of this node.
 * @name $.oNode#linkedColumns
 * @readonly
 * @type {oColumn[]}
*/
Object.defineProperty($.oNode.prototype, 'linkedColumns', {
  get : function(){
    var _attributes = this.attributes;
    var _columns = [];

    for (var i in _attributes){
      _columns = _columns.concat(_attributes[i].getLinkedColumns());
    }
    return _columns;
  }
})



/**
 * Whether the node can create new in-ports.
 * @name $.oNode#canCreateInPorts
 * @readonly
 * @type {bool}
*/
Object.defineProperty($.oNode.prototype, 'canCreateInPorts', {
  get : function(){
    return ["COMPOSITE",
            "GROUP",
            "MultiLayerWrite",
            "TransformGate",
            "TransformationSwitch",
            "DeformationCompositeModule",
            "MATTE_COMPOSITE",
            "COMPOSITE_GENERIC",
            "ParticleBkerComposite",
            "ParticleSystemComposite",
            "ParticleRegionComposite",
            "PointConstraintMulti",
            "MULTIPORT_OUT"]
            .indexOf(this.type) != -1;
  }
})


/**
 * Whether the node can create new out-ports.
 * @name $.oNode#canCreateOutPorts
 * @readonly
 * @type {bool}
*/
Object.defineProperty($.oNode.prototype, 'canCreateOutPorts', {
  get : function(){
    return ["GROUP",
            "MULTIPORT_IN"]
            .indexOf(this.type) != -1;
  }
})


/**
 * Returns the number of links connected to an in-port
 * @param   {int}      inPort      the number of the port to get links from.
 */
$.oNode.prototype.getInLinksNumber = function(inPort){
  if (this.inPorts < inPort) return null;
  return node.isLinked(this.path, inPort)?1:0;
}


/**
 * Returns the oLink object representing the connection of a specific inPort
 * @param   {int}      inPort      the number of the port to get links from.
 * @return  {$.oLink}  the oLink Object representing the link connected to the inport
 */
$.oNode.prototype.getInLink = function(inPort){
  if (this.inPorts < inPort) return null;
  var _info = node.srcNodeInfo(this.path, inPort);
  // this.$.log(this.path+" "+inPort+" "+JSON.stringify(_info))

  if (!_info) return null;

  var _inNode = this.scene.getNodeByPath(_info.node);
  var _inLink = new this.$.oLink(_inNode, this, _info.port, inPort, _info.link, true);

  // this.$.log("inLink: "+_inLink)
  return _inLink;
}


/**
 * Returns all the valid oLink objects describing the links that are connected into this node.
 * @return {$.oLink[]}  An array of $.oLink objects.
 */
$.oNode.prototype.getInLinks = function(){
  var _inPorts = this.inPorts;
  var _inLinks = [];

  for (var i = 0; i<_inPorts; i++){
    var _link = this.getInLink(i);
    if (_link != null) _inLinks.push(_link);
  }

  return _inLinks;
}


/**
 * Returns a free unconnected in-port
 * @param  {bool}  [createNew=true]  Whether to allow creation of new ports
 * @return {int} the port number that isn't connected
 */
$.oNode.prototype.getFreeInPort = function(createNew){
  if (typeof createNew === 'undefined') var createNew = true;

  var _inPorts = this.inPorts;

  for (var i=0; i<_inPorts; i++){
    if (this.getInLinksNumber(i) == 0) return i;
  }
  if (_inPorts == 0 && this.canCreateInPorts) return 0;
  if (createNew && this.canCreateInPorts) return _inPorts;
  this.$.debug("can't get free inPort for node "+this.path, this.$.DEBUG_LEVEL.ERROR);
  return null
}


/**
 * Links this node's inport to the given module, at the inport and outport indices.
 * @param   {$.oNode}   nodeToLink             The node to link this one's inport to.
 * @param   {int}       [ownPort]              This node's inport to connect.
 * @param   {int}       [destPort]             The target node's outport to connect.
 * @param   {bool}      [createPorts]          Whether to create new ports on the nodes.
 *
 * @return  {bool}    The result of the link, if successful.
 */
$.oNode.prototype.linkInNode = function( nodeToLink, ownPort, destPort, createPorts){
  if (!(nodeToLink instanceof this.$.oNode)) throw new Error("Incorrect type for argument 'nodeToLink'. Must provide an $.oNode.")

  var _link = (new this.$.oLink(nodeToLink, this, destPort, ownPort)).getValidLink(createPorts, createPorts);
  if (_link == null) return;
  this.$.debug("linking "+_link, this.$.DEBUG_LEVEL.LOG);

  return _link.connect();
};


/**
 * Searches for and unlinks the $.oNode object from this node's inNodes.
 * @param   {$.oNode}   oNodeObject            The node to link this one's inport to.
 * @return  {bool}    The result of the unlink.
 */
$.oNode.prototype.unlinkInNode = function( oNodeObject ){

  var _node = oNodeObject.path;

  var _links = this.getInLinks();

  for (var i in _links){
    if (_links[i].outNode.path == _node) return _links[i].disconnect();
  }

  throw new Error (oNodeObject.name + " is not linked to node " + this.name + ", can't unlink.");
};


/**
 * Unlinks a specific port from this node's inport.
 * @param   {int}       inPort                 The inport to disconnect.
 *
 * @return  {bool}    The result of the unlink, if successful.
 */
$.oNode.prototype.unlinkInPort = function( inPort ){
  // Default values for optional parameters
  if (typeof inPort === 'undefined') inPort = 0;

  return node.unlink( this.path, inPort );
};


/**
 * Returns the node connected to a specific in-port
 * @param   {int}        inPort      the number of the port to get the linked Node from.
 * @return  {$.oNode}                The node connected to this in-port
 */
$.oNode.prototype.getLinkedInNode = function(inPort){
  if (this.inPorts < inPort) return null;
  return this.scene.getNodeByPath(node.srcNode(this.path, inPort));
}


/**
 * Returns the number of links connected to an outPort
 * @param   {int}      outPort      the number of the port to get links from.
 * @return  {int}    the number of links
 */
$.oNode.prototype.getOutLinksNumber = function(outPort){
  if (this.outPorts < outPort) return null;
  return node.numberOfOutputLinks(this.path, outPort);
}


/**
 * Returns the $.oLink object representing the connection of a specific outPort / link
 * @param   {int}      outPort      the number of the port to get the link from.
 * @param   {int}      [outLink]    the index of the link.
 * @return {$.oLink}   The link object describing the connection
 */
$.oNode.prototype.getOutLink = function(outPort, outLink){
  if (typeof outLink === 'undefined') var outLink = 0;

  if (this.outPorts < outPort) return null;
  if (this.getOutLinksNumber(outPort) < outLink) return null;

  var _info = node.dstNodeInfo(this.path, outPort, outLink);
  if (!_info) return null;

  var _outNode = this.scene.getNodeByPath(_info.node);
  var _outLink = new this.$.oLink(this, _outNode, outPort, _info.port, outLink, true);

  return _outLink;
}


/**
 * Returns all the valid oLink objects describing the links that are coming out of this node.
 * @return {$.oLink[]}  An array of $.oLink objects.
 */
$.oNode.prototype.getOutLinks = function(){
  var _outPorts = this.outPorts;
  var _links = [];

  for (var i = 0; i<_outPorts; i++){
    var _outLinks = this.getOutLinksNumber(i);
    for (var j = 0; j<_outLinks; j++){
      var _link = this.getOutLink(i, j);
      if (_link != null) _links.push(_link);
    }
  }

  return _links;
}


/**
 * Returns a free unconnected out-port
 * @param  {bool}  [createNew=true]  Whether to allow creation of new ports
 * @return {int} the port number that isn't connected
 */
$.oNode.prototype.getFreeOutPort = function(createNew){
  if (typeof createNew === 'undefined') var createNew = false;

  var _outPorts = this.outPorts;
  for (var i=0; i<_outPorts; i++){
    if (this.getOutLinksNumber(i) == 0) return i;
  }

  if (_outPorts == 0 && this.canCreateOutPorts) return 0;

  if (createNew && this.canCreateOutPorts) return _outPorts;

  return _outPorts-1; // if no empty outPort can be found, return the last one
}


/**
 * Links this node's out-port to the given module, at the inport and outport indices.
 * @param   {$.oNode} nodeToLink             The node to link this one's outport to.
 * @param   {int}     [ownPort]              This node's outport to connect.
 * @param   {int}     [destPort]             The target node's inport to connect.
 * @param   {bool}    [createPorts]          Whether to create new ports on the nodes.
 *
 * @return  {bool}    The result of the link, if successful.
 */
$.oNode.prototype.linkOutNode = function(nodeToLink, ownPort, destPort, createPorts){
  if (!(nodeToLink instanceof this.$.oNode)) throw new Error("Incorrect type for argument 'nodeToLink'. Must provide an $.oNode.")

  var _link = (new this.$.oLink(this, nodeToLink, ownPort, destPort)).getValidLink(createPorts, createPorts)
  if (_link == null) return;
  this.$.debug("linking "+_link, this.$.DEBUG_LEVEL.LOG);

  return _link.connect();
}


/**
 * Links this node's out-port to the given module, at the inport and outport indices.
 * @param   {$.oNode}   oNodeObject            The node to unlink from this node's outports.
 *
 * @return  {bool}    The result of the link, if successful.
 */
$.oNode.prototype.unlinkOutNode = function( oNodeObject ){
  var _node = oNodeObject.path;

  var _links = this.getOutLinks();

  for (var i in _links){
    if (_links[i].inNode.path == _node) return _links[i].disconnect();
  }

  throw new Error (oNodeObject.name + " is not linked to node " + this.name + ", can't unlink.");
};


/**
 * Returns the node connected to a specific outPort
 * @param   {int}      outPort      the number of the port to get the node from.
 * @param   {int}      [outLink=0]  the index of the link.
 * @return  {$.oNode}   The node connected to this outPort and outLink
 */
$.oNode.prototype.getLinkedOutNode = function(outPort, outLink){
  if (typeof outLink == 'undefined') var outLink = 0;
  if (this.outPorts < outPort || this.getOutLinksNumber(outPort) < outLink) return null;
  return this.scene.getNodeByPath(node.dstNode(this.path, outPort, outLink));
}


/**
 * Unlinks a specific port/link from this node's output.
 * @param   {int}     outPort                 The outPort to disconnect.
 * @param   {int}     outLink                 The outLink to disconnect.
 *
 * @return  {bool}    The result of the unlink, if successful.
 */
$.oNode.prototype.unlinkOutPort = function( outPort, outLink ){
    // Default values for optional parameters
    if (typeof outLink === 'undefined') outLink = 0;

    try{
      var dstNodeInfo = node.dstNodeInfo(this.path, outPort, outLink);
      if (dstNodeInfo) node.unlink(dstNodeInfo.node, dstNodeInfo.port);
      return true;
    }catch(err){
      this.$.debug("couldn't unlink port "+outPort+" of node "+this.path, this.$.DEBUG_LEVEL.ERROR)
      return false;
    }
};


/**
 * Inserts the $.oNodeObject provided as an innode to this node, placing it between any existing nodes if the link already exists.
 * @param   {int}     inPort                 This node's inport to connect.
 * @param   {$.oNode} oNodeObject            The node to link this one's outport to.
 * @param   {int}     inPortTarget           The target node's inPort to connect.
 * @param   {int}     outPortTarget          The target node's outPort to connect.
 *
 * @return  {bool}    The result of the link, if successful.
 */
$.oNode.prototype.insertInNode = function( inPort, oNodeObject, inPortTarget, outPortTarget ){
    var _node = oNodeObject.path;

    //QScriptValue
    if( this.ins[inPort] ){
      //INSERT BETWEEN.
      var node_linkinfo = node.srcNodeInfo( this.path, inPort );
      node.link( node_linkinfo.node, node_linkinfo.port, _node, inPortTarget, true, true );
      node.unlink( this.path, inPort );
      return node.link( oNodeObject.path, outPortTarget, this.path, inPort, true, true );
    }

    return this.linkInNode( oNodeObject, inPort, outPortTarget );
};


/**
 * Moves the node into the specified group. This doesn't create any composite or links to the multiport nodes. The node will be unlinked.
 * @param   {oGroupNode}   group      the group node to move the node into.
 */
$.oNode.prototype.moveToGroup = function(group){
  var _name = this.name;
  if (group instanceof oGroupNode) group = group.path;

  if (this.group != group){
    this.$.beginUndo("oH_moveNodeToGroup_"+_name)

    var _groupNodes = node.subNodes(group);

    node.moveToGroup(this.path, group);
    this._path = group+"/"+_name;

    // detect creation of a composite and remove it
    var _newNodes = node.subNodes(group)
    if (_newNodes.length > _groupNodes.length+1){
      for (var i in _newNodes){
        if (_groupNodes.indexOf(_newNodes[i]) == -1 && _newNodes[i] != this.path) {
           var _comp = this.scene.getNodeByPath(_newNodes[i]);
           if (_comp && _comp.type == "COMPOSITE") _comp.remove();
           break;
        }
      }
    }

    // remove automated links
    var _inPorts = this.inPorts;
    for (var i=0; i<_inPorts; i++){
      this.unlinkInPort(i);
    }

    var _outPorts = this.outPorts;
    for (var i=0; i<_outPorts; i++){
      var _outLinks = this.getOutLinksNumber(i);
      for (var j=_outLinks-1; j>=0; j--){
        this.unlinkOutPort(i, j);
      }
    }

    this.refreshAttributes();

    this.$.endUndo();
  }
}


/**
 * Get the transformation matrix for the node at the given frame
 * @param {int} frameNumber
 * @returns {oMatrix}  the matrix object
 */
$.oNode.prototype.getMatrixAtFrame = function (frameNumber){
  return new this.$.oMatrix(node.getMatrix(this.path, frameNumber));
}


/**
 * Retrieves the node layer in the timeline provided.
 * @param   {oTimeline}   [timeline]     Optional: the timeline object to search the column Layer. (by default, grabs the current timeline)
 *
 * @return  {int}    The index within that timeline.
 */
 $.oNode.prototype.getTimelineLayer = function(timeline){
  if (typeof timeline === 'undefined') var timeline = this.$.scene.currentTimeline;

  var _nodeLayers = timeline.layers.map(function(x){return x.node.path});
  if (_nodeLayers.indexOf(this.path)<timeline.layers.length && _nodeLayers.indexOf(this.path)>0){
    return timeline.layers[_nodeLayers.indexOf(this.path)];
  }
  return null
}


/**
 * Retrieves the node index in the timeline provided.
 * @param   {oTimeline}   [timeline]     Optional: the timeline object to search the column Layer. (by default, grabs the current timeline)
 *
 * @return  {int}    The index within that timeline.
 */
$.oNode.prototype.timelineIndex = function(timeline){
  if (typeof timeline === 'undefined') var timeline = this.$.scene.currentTimeline;

  var _nodes = timeline.compositionLayersList;
  return _nodes.indexOf(this.path);
}


/**
 * obtains the nodes contained in the group, allows recursive search. This method is deprecated and was moved to oGroupNode
 * @DEPRECATED
 * @param   {bool}   recurse           Whether to recurse internally for nodes within children groups.
 *
 * @return  {$.oNode[]}    The subbnodes contained in the group.
 */
$.oNode.prototype.subNodes = function(recurse){
    if (typeof recurse === 'undefined') recurse = false;
    var _nodes = node.subNodes(this.path);
    var _subNodes = [];
    for (var _node in _nodes){
        var _oNodeObject = new this.$.oNode( _nodes[_node] );
        _subNodes.push(_oNodeObject);
        if (recurse && node.isGroup(_nodes[_node])) _subNodes = _subNodes.concat(_$.oNodeObject.subNodes(recurse));
    }

    return _subNodes;
};


 /**
 * Place a node above one or more nodes with an offset.
 * @param   {$.oNode[]}     oNodeArray                The array of nodes to center this above.
 * @param   {float}         xOffset                   The horizontal offset to apply after centering.
 * @param   {float}         yOffset                   The vertical offset to apply after centering.
 *
 * @return  {oPoint}   The resulting position of the node.
 */
$.oNode.prototype.centerAbove = function( oNodeArray, xOffset, yOffset ){
  if (!oNodeArray) throw new Error ("An array of nodes to center node '"+this.name+"' above must be provided.")

  // Defaults for optional parameters
    if (typeof xOffset === 'undefined') var xOffset = 0;
    if (typeof yOffset === 'undefined') var yOffset = -30;

    // Works with nodes and nodes array
    if (oNodeArray instanceof this.$.oNode) oNodeArray = [oNodeArray];
    if (oNodeArray.filter(function(x){return !x}).length) throw new Error ("Can't center node '"+ this.name+ "' above nodes "+ oNodeArray + ", invalid nodes found.")

    var _box = new this.$.oBox();
    _box.includeNodes( oNodeArray );

    this.x = _box.center.x - this.width/2 + xOffset;
    this.y = _box.top - this.height + yOffset;

    return new this.$.oPoint(this.x, this.y, this.z);
};


 /**
 * Place a node below one or more nodes with an offset.
 * @param   {$.oNode[]} oNodeArray           The array of nodes to center this below.
 * @param   {float}     xOffset              The horizontal offset to apply after centering.
 * @param   {float}     yOffset              The vertical offset to apply after centering.
 *
 * @return  {oPoint}   The resulting position of the node.
 */
$.oNode.prototype.centerBelow = function( oNodeArray, xOffset, yOffset){
    if (!oNodeArray) throw new Error ("An array of nodes to center node '"+this.name+"' below must be provided.")

    // Defaults for optional parameters
    if (typeof xOffset === 'undefined') var xOffset = 0;
    if (typeof yOffset === 'undefined') var yOffset = 30;

    // Works with nodes and nodes array
    if (oNodeArray instanceof this.$.oNode) oNodeArray = [oNodeArray];
    if (oNodeArray.filter(function(x){return !x}).length) throw new Error ("Can't center node '"+ this.name+ "' below nodes "+ oNodeArray + ", invalid nodes found.")

    var _box = new this.$.oBox();
    _box.includeNodes(oNodeArray);

    this.x = _box.center.x - this.width/2 + xOffset;
    this.y = _box.bottom + yOffset;

    return new this.$.oPoint(this.x, this.y, this.z);
}


 /**
 * Place at center of one or more nodes with an offset.
 * @param   {$.oNode[]} oNodeArray           The array of nodes to center this below.
 * @param   {float}     xOffset              The horizontal offset to apply after centering.
 * @param   {float}     yOffset              The vertical offset to apply after centering.
 *
 * @return  {oPoint}   The resulting position of the node.
 */
$.oNode.prototype.placeAtCenter = function( oNodeArray, xOffset, yOffset ){
    // Defaults for optional parameters
    if (typeof xOffset === 'undefined') var xOffset = 0;
    if (typeof yOffset === 'undefined') var yOffset = 0;

    // Works with nodes and nodes array
    if (typeof oNodeArray === 'oNode') oNodeArray = [oNodeArray];

    var _box = new this.$.oBox();
    _box.includeNodes(oNodeArray);

    this.x = _box.center.x - this.width/2 + xOffset;
    this.y = _box.center.y - this.height/2 + yOffset;

    return new this.$.oPoint(this.x, this.y, this.z);
}


 /**
 * Create a clone of the node.
 * @param   {string}    newName              The new name for the cloned module.
 * @param   {oPoint}    newPosition          The new position for the cloned module.
 */
$.oNode.prototype.clone = function( newName, newPosition ){
  // Defaults for optional parameters
  if (typeof newPosition === 'undefined') var newPosition = this.nodePosition;
  if (typeof newName === 'undefined') var newName = this.name+"_clone";

  this.$.beginUndo("oH_cloneNode_"+this.name);

  var _clonedNode = this.group.addNode(this.type, newName, newPosition);
  var _attributes = this.attributes;

  for (var i in _attributes){
    var _clonedAttribute = _clonedNode.getAttributeByName(_attributes[i].keyword);
    _clonedAttribute.setToAttributeValue(_attributes[i]);
  }

  var palettes = this.palettes
  for (var i in palettes){
    _clonedNode.linkPalette(palettes[i])
  }

  this.$.endUndo();

  return _clonedNode;
};


 /**
 * Duplicates a node by creating an independent copy.
 * @param   {string}    [newName]              The new name for the duplicated node.
 * @param   {oPoint}    [newPosition]          The new position for the duplicated node.
 */
$.oNode.prototype.duplicate = function(newName, newPosition){
  if (typeof newPosition === 'undefined') var newPosition = this.nodePosition;
  if (typeof newName === 'undefined') var newName = this.name+"_duplicate";

  this.$.beginUndo("oH_cloneNode_"+this.name);

  var _duplicateNode = this.group.addNode(this.type, newName, newPosition);
  var _attributes = this.attributes;

  for (var i in _attributes){
    var _duplicateAttribute = _duplicateNode.getAttributeByName(_attributes[i].keyword);
    _duplicateAttribute.setToAttributeValue(_attributes[i], true);
  }

  var palettes = this.palettes
  for (var i in palettes){
    _duplicateNode.linkPalette(palettes[i])
  }

  this.$.endUndo();

  return _duplicateNode;
};


 /**
 * Removes the node from the scene.
 * @param   {bool}    deleteColumns              Should the columns of drawings be deleted as well?
 * @param   {bool}    deleteElements             Should the elements of drawings be deleted as well?
 *
 * @return  {void}
 */
$.oNode.prototype.remove = function( deleteColumns, deleteElements ){
  if (typeof deleteFrames === 'undefined') var deleteColumns = true;
  if (typeof deleteElements === 'undefined') var deleteElements = true;

  this.$.beginUndo("oH_deleteNode_"+this.name)
  // restore links for special types;
  if (this.type == "PEG"){
    var inNodes = this.inNodes; //Pegs can only have one inNode but we'll implement the general case for other types
    var outNodes = this.outNodes;
    for (var i in inNodes){
      for (var j in outNodes){
        for( var k in outNodes[j] ){
          inNodes[i].linkOutNode(outNodes[j][k]);
        }
      }
    }
  }

  node.deleteNode(this.path, deleteColumns, deleteElements);
  this.$.endUndo();
}


 /**
 * Provides a matching attribute based on provided keyword name. Keyword can include "." to get subattributes.
 * @param   {string}    keyword                    The attribute keyword to search.
 * @return  {oAttribute}   The matched attribute object, given the keyword.
 */
$.oNode.prototype.getAttributeByName = function( keyword ){
  keyword = keyword.toLowerCase();
  keyword = keyword.split(".");

  // we go through the keywords, trying to access an attribute corresponding to the name
  var _attribute = this.attributes;
  for (var i in keyword){
    var _keyword = keyword[i];

    // applying conversion to the name 3dpath
    if (_keyword == "3dpath") _keyword = "path3d";

    if (!(_keyword in _attribute)) return null;

    _attribute = _attribute[_keyword];
  }

  if (_attribute instanceof this.$.oAttribute) return _attribute;
  return null;
}


 /**
 * Used in converting the node to a string value, provides the string-path.
 * @return  {string}   The node path's as a string.
 */
$.oNode.prototype.toString = function(){
    return this.path;
}


 /**
 * Provides a matching attribute based on the column name provided. Assumes only one match at the moment.
 * @param   {string}       columnName                    The column name to search.
 * @return  {oAttribute}   The matched attribute object, given the column name.
 */
$.oNode.prototype.getAttributeByColumnName = function( columnName ){
  // var attribs = [];

  //Initially check for cache.
  var cdate = (new Date()).getTime();
  if( this.$.cache_columnToNodeAttribute[columnName] ){
    if( ( cdate - this.$.cache_columnToNodeAttribute[columnName].date ) < 5000 ){
      //Cache is in form : { "node":oAttributeObject.node, "attribute": this, "date": (new Date()).getTime() }
      // attribs.push( this.$.cache_columnToNodeAttribute[columnName].attribute );
      return this.$.cache_columnToNodeAttribute[columnName].attribute;
    }
  }

  var _attributes = this.attributes;

  for( var n in _attributes){
    var t_attrib = _attributes[n];
    if( t_attrib.subAttributes.length>0 ){
      //Also check subattributes.
      for( var t=0; t<t_attrib.subAttributes.length; t++ ){
        var t_attr = t_attrib.subAttributes[t];
        if( t_attr.column && t_attr.column.uniqueName == columnName) return t_attr;
      }
    }

    if( t_attrib.column && t_attrib.column.uniqueName == columnName) return t_attrib;
  }
  // return attribs;
}


 /**
 * Provides a column->attribute lookup table for timeline building.
 * @private
 * @return  {object}   The column_name->attribute object LUT.  {colName: { "node":oNode, "column":oColumn } }
 */
$.oNode.prototype.getAttributesColumnCache = function( obj_lut ){
  if (typeof obj_lut === 'undefined') obj_lut = {};

  for( var n in this.attributes ){
    var t_attrib = this.attributes[n];
    if( t_attrib.subAttributes.length>0 ){
      //Also check subattributes.
      for( var t=0;t<t_attrib.subAttributes.length;t++ ){
        var t_attr = t_attrib.subAttributes[t];
        if( t_attr.column ){
          obj_lut[ t_attr.column.uniqueName ] = { "node":this, "attribute":t_attr };
        }
      }
    }

    if( t_attrib.column ){
      obj_lut[ t_attr.column.uniqueName ] = { "node":this, "attribute":t_attr };
    }
  }

  return obj_lut;
}


/**
 * Creates an $.oNodeLink and connects this node to the target via this nodes outport.
 * @param   {oNode}         nodeToLink                          The target node as an in node.
 * @param   {int}           ownPort                             The out port on this node to connect to.
 * @param   {int}           destPort                            The in port on the inNode to connect to.
 *
 * @return {$.oNodeLink}    the resulting created link.
 * @example
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Group/Peg2" );
 *  var newLink  = peg1.addOutLink( peg2, 0, 0 );
 */
$.oNode.prototype.addOutLink = function( nodeToLink, ownPort, destPort ){
  if (typeof ownPort == 'undefined') var ownPort = 0;
  if (typeof destPort == 'undefined') var destPort = 0;

  var newLink = new this.$.oNodeLink( this, ownPort, nodeToLink, destPort );
  newLink.apply();

  return newLink;
};

/**
 * Creates a new dynamic attribute in the node.
 * @param   {string}   attrName                   The attribute name to create.
 * @param   {string}   [type="string"]            The type of the attribute ["string", "bool", "double", "int"]
 * @param   {string}   [displayName=attrName]     The visible attribute name to the GUI user.
 * @param   {bool}     [linkable=false]           Whether the attribute can be linked to a column.
 *
 * @return  {$.oAttribute}     The resulting attribute created.
 */
$.oNode.prototype.createAttribute = function( attrName, type, displayName, linkable ){
  if( !attrName ){ return false; }
  attrName = attrName.toLowerCase();

  if (typeof type === 'undefined') type = 'string';
  if (typeof displayName === 'undefined') displayName = attrName;
  if (typeof linkable === 'undefined') linkable = false;

  var res = node.createDynamicAttr( this.path, type.toUpperCase(), attrName, displayName, linkable );
  if( !res ){
    return false;
  }

  this.refreshAttributes();

  var res_split = attrName.split(".");
  if( res_split.length>0 ){
    //Its a sub attribute created.
    try{
      var sub_attr = this.attributes[ res_split[0] ];
      for( x = 1; x<res_split.length;x++ ){
        sub_attr = sub_attr[ res_split[x] ];
      }
      return sub_attr;

    }catch( err ){
      return false;
    }
  }

  var res = this.attributes[ attrName ];
  return this.attributes[ attrName ];
}


/**
 * Removes an existing dynamic attribute in the node.
 * @param   {string}   attrName                   The attribute name to remove.
 *
 * @return  {bool}     The result of the removal.
 */
$.oNode.prototype.removeAttribute = function( attrName ){
  attrName = attrName.toLowerCase();
  return node.removeDynamicAttr( this.path, attrName );
}


/**
 * Refreshes/rebuilds the attributes and getter/setters.
 * @param   {$.oNode}   oNodeObject            The node to link this one's inport to.
 * @return  {bool}    The result of the unlink.
 */
$.oNode.prototype.refreshAttributes = function( ){
    // generate properties from node attributes to allow for dot notation access
    this.attributesBuildCache();

    // for each attribute, create a getter setter as a property of the node object
    // that handles the animated/not animated duality
    var _attributes = this.attributes
    for (var i in _attributes){
      var _attr = _attributes[i];
      this.setAttrGetterSetter(_attr);
    }
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//          $.oPegNode class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for the $.oPegNode class
 * @classdesc
 * $.oPegNode is a subclass of $.oNode and implements the same methods and properties as $.oNode. <br>
 * It represents peg nodes in the scene.
 * @constructor
 * @augments   $.oNode
 * @classdesc  Peg Moudle Class
 * @param   {string}         path                          Path to the node in the network.
 * @param   {oScene}         oSceneObject                  Access to the oScene object of the DOM.
 */
$.oPegNode = function( path, oSceneObject ) {
    if (node.type(path) != 'PEG') throw "'path' parameter must point to a 'PEG' type node";
    var instance = this.$.oNode.call( this, path, oSceneObject );
    if (instance) return instance;

    this._type = 'pegNode';
}
$.oPegNode.prototype = Object.create( $.oNode.prototype );
$.oPegNode.prototype.constructor = $.oPegNode;



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oDrawingNode class      //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for the $.oDrawingNode class
 * @classdesc
 * $.oDrawingNode is a subclass of $.oNode and implements the same methods and properties as $.oNode. <br>
 * It represents 'read' nodes or Drawing nodes in the scene.
 * @constructor
 * @augments   $.oNode
 * @param   {string}           path                          Path to the node in the network.
 * @param   {$.oScene}         oSceneObject                  Access to the oScene object of the DOM.
 * @example
 * // Drawing Nodes are more than a node, as they do not work without an associated Drawing column and element.
 * // adding a drawing node will automatically create a column and an element, unless they are provided as arguments.
 * // Creating an element makes importing a drawing file possible.
 *
 * var doc = $.scn;
 *
 * var drawingName = "myDrawing";
 * var myElement = doc.addElement(drawingName, "TVG");                      // add an element that holds TVG(Toonboom Vector Drawing) files
 * var myDrawingColumn = doc.addColumn("DRAWING", drawingName, myElement);  // create a column and link the element created to it
 *
 * var sceneRoot = doc.root;                                                // grab the scene root group
 *
 * // Creating the Drawing node and linking the previously created element and column
 * var myDrawingNode = sceneRoot.addDrawingNode(drawingName, new $.oPoint(), myDrawingColumn, myElement);
 *
 * // This also works:
 *
 * var myOtherNode = sceneRoot.addDrawingNode("Drawing2");
 */
$.oDrawingNode = function(path, oSceneObject) {
    // $.oDrawingNode can only represent a node of type 'READ'
    if (node.type(path) != 'READ') throw "'path' parameter must point to a 'READ' type node";
    var instance = this.$.oNode.call(this, path, oSceneObject);
    if (instance) return instance;

    this._type = 'drawingNode';
}
$.oDrawingNode.prototype = Object.create($.oNode.prototype);
$.oDrawingNode.prototype.constructor = $.oDrawingNode;


/**
 * The element that holds the drawings displayed by the node.
 * @name $.oDrawingNode#element
 * @type {$.oElement}
 */
Object.defineProperty($.oDrawingNode.prototype, "element", {
  get : function(){
    var _column = this.attributes.drawing.element.column;
    return ( new this.$.oElement( node.getElementId(this.path), _column ) );
  },

  set : function( oElementObject ){
    var _column = this.attributes.drawing.element.column;
    column.setElementIdOfDrawing( _column.uniqueName, oElementObject.id );
  }
});


/**
 * The column that holds the drawings displayed by the node.
 * @name $.oDrawingNode.timingColumn
 * @type {$.oDrawingColumn}
 */
Object.defineProperty($.oDrawingNode.prototype, "timingColumn", {
  get : function(){
    var _column = this.attributes.drawing.element.column;
    return _column;
  },

  set : function (oColumnObject){
    var _attribute = this.attributes.drawing.element;
    _attribute.column = oColumnObject;
  }
});


/**
 * An array of the colorIds contained within the drawings displayed by the node.
 * @name $.oDrawingNode#usedColorIds
 * @type {int[]}
 */
Object.defineProperty($.oDrawingNode.prototype, "usedColorIds", {
  get : function(){
    // this.$.log("used colors in node : "+this.name)
    var _drawings = this.element.drawings;
    var _colors = [];

    for (var i in _drawings){
      var _drawingColors = _drawings[i].usedColorIds;
      for (var c in _drawingColors){
        if (_colors.indexOf(_drawingColors[c]) == -1) _colors.push(_drawingColors[c]);
      }
    }

    return _colors;
  }
});


/**
 * An array of the colors contained within the drawings displayed by the node, found in the palettes.
 * @name $.oDrawingNode#usedColors
 * @type {$.oColor[]}
 */
Object.defineProperty($.oDrawingNode.prototype, "usedColors", {
  get : function(){
    // get unique Color Ids
    var _ids = this.usedColorIds;

    // look in both element and scene palettes
    var _palettes = this.palettes.concat(this.$.scn.palettes);

    // build a palette/id list to speedup massive palettes/palette lists
    var _colorIds = {}
    for (var i in _palettes){
      var _palette = _palettes[i];
      var _colors = _palette.colors;
      _colorIds[_palette.name] = {};
      for (var j in _colors){
        _colorIds[_palette.name][_colors[j].id] = _colors[j];
      }
    }

    // for each id on the drawing, identify the corresponding color
    var _usedColors = _ids.map(function(id){
      for (var paletteName in _colorIds){
        if (_colorIds[paletteName][id]) return _colorIds[paletteName][id];
      }
      throw new Error("Missing color found for id: "+id+". Color doesn't belong to any palette in the scene or element.");
    })

    return _usedColors;
  }
})


/**
 * The drawing.element keyframes.
 * @name $.oDrawingNode#timings
 * @type {$.oFrames[]}
 * @example
 * // The timings hold the keyframes that display the drawings across time.
 *
 * var timings = $.scn.$node("Top/Drawing").timings;
 * for (var i in timings){
 *   $.log( timings.frameNumber+" : "+timings.value);      // outputs the frame and the value of each keyframe
 * }
 *
 * // timings are keyframe objects, so they are dynamic.
 * timings[2].value = "5";                                 // sets the displayed image of the second key to the drawing named "5"
 *
 * // to set a new value to a frame that wasn't a keyframe before, it's possible to use the attribute keyword like so:
 *
 * var myNode = $.scn.$node("Top/Drawing");
 * myNode.drawing.element = {frameNumber: 5, value: "10"}             // setting the value of the frame 5
 * myNode.drawing.element = {frameNumber: 6, value: timings[1].value} // setting the value to the same as one of the timings
 */
Object.defineProperty($.oDrawingNode.prototype, "timings", {
    get : function(){
        return this.attributes.drawing.element.getKeyframes();
    }
})


/**
 * The element palettes linked to the node.
 * @name $.oDrawingNode#palettes
 * @type {$.oPalette[]}
 */
Object.defineProperty($.oDrawingNode.prototype, "palettes", {
  get : function(){
    var _element = this.element;
    return _element.palettes;
  }
})


// Class Methods

/**
 * Gets the drawing name at the given frame.
 * @param {int} frameNumber
 * @return {$.oDrawing}
 */
$.oDrawingNode.prototype.getDrawingAtFrame = function(frameNumber){
  if (typeof frame === "undefined") var frame = this.$.scene.currentFrame;

  var _attribute = this.attributes.drawing.element
  return _attribute.getValue(frameNumber);
}


 /**
 * Gets the list of palettes containing colors used by a drawing node. This only gets palettes with the first occurence of the colors.
 * @return  {$.oPalette[]}   The palettes that contain the color IDs used by the drawings of the node.
 */
$.oDrawingNode.prototype.getUsedPalettes = function(){
  var _palettes = {};
  var _usedPalettes = [];

  var _usedColors = this.usedColors;
  // build an object of palettes under ids as keys to remove duplicates
  for (var i in _usedColors){
    var _palette = _usedColors[i].palette;
    _palettes[_palette.id] = _palette;
  }
  for (var i in _palettes){
    _usedPalettes.push(_palettes[i]);
  }

  return _usedPalettes;
}


/**
 * Displays all the drawings from the node's element onto the timeline
 * @param {int} [framesPerDrawing=1]   The number of frames each drawing will be shown for
 */
$.oDrawingNode.prototype.exposeAllDrawings = function(framesPerDrawing){
  if (typeof framesPerDrawing === 'undefined') var framesPerDrawing = 1;

  var _drawings = this.element.drawings;
  var frameNumber = 1;
  for (var i=0; i < _drawings.length; i++){
    //log("showing drawing "+_drawings[i].name+" at frame "+i)
    this.showDrawingAtFrame(_drawings[i], frameNumber);
    frameNumber+=framesPerDrawing;
  }

  var _column = this.attributes.drawing.element.column;
  var _exposures = _column.getKeyframes();
  _column.extendExposures(_exposures, framesPerDrawing-1);
}


/**
 * Displays the given drawing at the given frame
 * @param {$.oDrawing} drawing
 * @param {int} frameNum
 */
$.oDrawingNode.prototype.showDrawingAtFrame = function(drawing, frameNum){
  var _column = this.attributes.drawing.element.column;
  _column.setValue(drawing.name, frameNum);
}


 /**
 * Links a palette to a drawing node as Element Palette.
 * @param {$.oPalette}     oPaletteObject      the palette to link to the node
 * @param {int}            [index]             The index of the list at which the palette should appear once linked
 *
 * @return  {$.oPalette}   The linked element Palette.
 */
$.oDrawingNode.prototype.linkPalette = function(oPaletteObject, index){
  return this.element.linkPalette(oPaletteObject, index);
}


 /**
 * Unlinks an Element Palette from a drawing node.
 * @param {$.oPalette}     oPaletteObject      the palette to unlink from the node
 *
 * @return {bool}          The success of the unlink operation.
 */
$.oDrawingNode.prototype.unlinkPalette = function(oPaletteObject){
  return this.element.unlinkPalette(oPaletteObject);
}




 /**
 * Duplicates a node by creating an independent copy.
 * @param   {string}    [newName]              The new name for the duplicated node.
 * @param   {oPoint}    [newPosition]          The new position for the duplicated node.
 * @param   {bool}      [duplicateElement]     Wether to also duplicate the element.
 */
$.oDrawingNode.prototype.duplicate = function(newName, newPosition, duplicateElement){
  if (typeof newPosition === 'undefined') var newPosition = this.nodePosition;
  if (typeof newName === 'undefined') var newName = this.name+"_1";
  if (typeof duplicateElement === 'undefined') var duplicateElement = true;

  var _duplicateElement = duplicateElement?this.element.duplicate(this.name):this.element;

  var _duplicateNode = this.group.addDrawingNode(newName, newPosition, _duplicateElement);
  var _attributes = this.attributes;

  for (var i in _attributes){
    var _duplicateAttribute = _duplicateNode.getAttributeByName(_attributes[i].keyword);
    _duplicateAttribute.setToAttributeValue(_attributes[i], true);
  }

  var _duplicateAttribute = _duplicateNode.getAttributeByName(_attributes[i].keyword);
  _duplicateAttribute.setToAttributeValue(_attributes[i], true);

  return _duplicateNode;
};


 /**
 * Updates the imported drawings in the node.
 * @param {$.oFile}   sourcePath        the oFile object pointing to the source to update from
 * @param {string}    [drawingName]       the drawing to import the updated bitmap into
 * @todo implement a memory of the source through metadata
 */
$.oDrawingNode.prototype.update = function(sourcePath, drawingName){
  if (!this.element) return; // no element means nothing to update, import instead.
  if (typeof drawingName === 'undefined') var drawingName = this.element.drawings[0].name;

  var _drawing = this.element.getDrawingByName(drawingName);

  _drawing.importBitmap(sourcePath);
  _drawing.refreshPreview();
}


 /**
 * Extracts the position information on a drawing node, and applies it to a new peg instead.
 * @return  {$.oPegNode}   The created peg.
 */
$.oDrawingNode.prototype.extractPeg = function(){
    var _drawingNode = this;
    var _peg = this.group.addNode("PEG", this.name+"-P");
    var _columns = _drawingNode.linkedColumns;

    _peg.position.separate = _drawingNode.offset.separate;
    _peg.scale.separate = _drawingNode.scale.separate;

    // link each column that can be to the peg instead and reset the drawing node
    for (var i in _columns){
        var _attribute = _columns[i].attributeObject;
        var _keyword = _attribute._keyword;

        var _nodeAttribute = _drawingNode.getAttributeByName(_keyword);

        if (_keyword.indexOf("OFFSET") != -1) _keyword = _keyword.replace("OFFSET", "POSITION");

        var _pegAttribute = _peg.getAttributeByName(_keyword);

        if (_pegAttribute !== null){
            _pegAttribute.column = _columns[i];
            _nodeAttribute.column = null;
            _drawingNode[_keyword] = _attribute.defaultValue;
        }
    }

    _drawingNode.offset.separate = false; // doesn't work?
    _drawingNode.can_animate = false;

    _peg.centerAbove(_drawingNode, -1, -30)
    _drawingNode.linkInNode(_peg)

    return _peg;
}


 /**
 * Gets the contour curves of the drawing, as a concave hull.
 * @param   {int}          [count]                          The number of points on the contour curve to derive.
 * @param   {int}          [frame]                          The frame to derive the contours.
 *
 * @return  {oPoint[][]}   The contour curves.
 */
$.oDrawingNode.prototype.getContourCurves = function( count, frame ){

  if (typeof frame === 'undefined') var frame = this.scene.currentFrame;
  if (typeof count === 'undefined') var count = 3;

  var res = EnvelopeCreator().getDrawingBezierPath( this.path,
                           frame,      //FRAME
                           2.5,        //DISCRETIZER
                           0,          //K
                           count,      //DESIRED POINT COUNT
                           0,          //BLUR
                           0,          //EXPAND
                           false,      //SINGLELINE
                           true,       //USE MIN POINTS,
                           0,          //ADDITIONAL BISSECTING

                           false
                        );
  if( res.success ){
    var _curves = res.results.map(function(x){return [
                                                      new this.$.oPoint( x[0][0], x[0][1], 0.0 ),
                                                      new this.$.oPoint( x[1][0], x[1][1], 0.0 ),
                                                      new this.$.oPoint( x[2][0], x[2][1], 0.0 ),
                                                      new this.$.oPoint( x[3][0], x[3][1], 0.0 )
                                                    ]; } );
    return _curves;
  }

  return [];
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//   $.oTransformSwitchNode class   //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for the $.oTransformSwitchNode class
 * @classdesc
 * $.oTransformSwitchNode is a subclass of $.oNode and implements the same methods and properties as $.oNode. <br>
 * It represents transform switches in the scene.
 * @constructor
 * @augments   $.oNode
 * @param   {string}         path            Path to the node in the network.
 * @param   {oScene}         oSceneObject    Access to the oScene object of the DOM.
 * @property {$.oTransformNamesObject} names An array-like object with static indices (starting at 0) for each transformation name, which can be retrieved/set directly.
 * @example
 * // Assuming the existence of a Deformation group applied to a 'Drawing' node at the root of the scene
 * var myNode = $.scn.getNodeByPath("Top/Deformation-Drawing/Transformation-Switch");
 *
 * myNode.names[0] = "B";                              // setting the value for the first transform drawing name to "B"
 *
 * var drawingNames = ["A", "B", "C"]                  // example of iterating over the existing names to set/retrieve them
 * for (var i in myNode.names){
 *   $.log(i+": "+myNode.names[i]);
 *   $.log(myNode.names[i] = drawingNames[i]);
 * }
 *
 * $.log("length: " + myNode.names.length)             // the number of names
 * $.log("names: " + myNode.names)                     // prints the list of names
 * $.log("indexOf 'B': " + myNode.names.indexOf("B"))  // can use methods from Array
 */
$.oTransformSwitchNode = function( path, oSceneObject ) {
  if (node.type(path) != 'TransformationSwitch') throw "'path' parameter ("+path+") must point to a 'TransformationSwitch' type node. Got: "+node.type(path);
  var instance = this.$.oNode.call( this, path, oSceneObject );
  if (instance) return instance;

  this._type = 'transformSwitchNode';
  this.names = new this.$.oTransformNamesObject(this);
}
$.oTransformSwitchNode.prototype = Object.create( $.oNode.prototype );
$.oTransformSwitchNode.prototype.constructor = $.oTransformSwitchNode;


/**
 * Constructor for the $.oTransformNamesObject class
 * @classdesc
 * $.oTransformNamesObject is an array like object with static length that exposes getter setters for
 * each transformation name used by the oTransformSwitchNode. It can use the same methods as any array.
 * @constructor
 * @param {$.oTransformSwitchNode} instance the transform Node instance using this object
 * @property {int} length the number of valid elements in the object.
 */
$.oTransformNamesObject = function(transformSwitchNode){
  Object.defineProperty(this, "transformSwitchNode", {
    enumerable:false,
    get: function(){
      return transformSwitchNode;
    },
  })

  this.refresh();
}
$.oTransformNamesObject.prototype = Object.create(Array.prototype);


/**
 * creates a $.oTransformSwitch.names property with an index for each name to get/set the name value
 * @private
 */
Object.defineProperty($.oTransformNamesObject.prototype, "createGetterSetter", {
  enumerable:false,
  value: function(index){
    var attrName = "transformation_" + (index+1);
    var transformNode = this.transformSwitchNode;

    Object.defineProperty(this, index, {
      enumerable:true,
      configurable:true,
      get: function(){
        return transformNode.transformationnames[attrName];
      },
      set: function(newName){
        newName = newName+""; // convert to string
        this.$.debug("setting "+attrName+" to drawing "+newName+" on "+transformNode.path, this.$.DEBUG_LEVEL.DEBUG)
        if (newName instanceof this.$.oDrawing) newName = newName.name;
        transformNode.transformationnames[attrName] = newName;
      }
    })
  }
})


/**
 * The length of the array of names on the oTransformSwitchNode node. Corresponds to the transformationnames.size subAttribute.
 * @name $.oTransformNamesObject#length
 * @type {int}
 */
 Object.defineProperty($.oTransformNamesObject.prototype, "length", {
  enumerable:false,
  get: function(){
    return this.transformSwitchNode.transformationnames.size;
  },
})


/**
 * A string representation of the names list
 * @private
 */
Object.defineProperty($.oTransformNamesObject.prototype, "toString", {
  enumerable:false,
  value: function(){
    return this.join(",");
  }
})


/**
 * @private
 */
Object.defineProperty($.oTransformNamesObject.prototype, "refresh", {
  enumerable:false,
  value:function(){
    for (var i in this){
      delete this[i];
    }
    for (var i=0; i<this.length; i++){
      this.createGetterSetter(i);
    }
  }
})


/**
 * @private
 */
$.oTransformSwitchNode.prototype.refreshNames = function(){
  this.refreshAttributes();
  this.names.refresh();
}


/**
 * Links this node's inport to the given module, at the inport and outport indices.
 * Refreshes attributes to update for the changes of connected transformation.
 * @param   {$.oNode}   nodeToLink             The node to link this one's inport to.
 * @param   {int}       [ownPort]              This node's inport to connect.
 * @param   {int}       [destPort]             The target node's outport to connect.
 * @param   {bool}      [createPorts]          Whether to create new ports on the nodes.
 *
 * @return  {bool}    The result of the link, if successful.
 */
$.oTransformSwitchNode.prototype.linkInNode = function(nodeToLink, ownPort, destPort, createPorts){
  this.$.oNode.prototype.linkInNode.apply(this, arguments);
  this.refreshNames()
}

/**
 * Searches for and unlinks the $.oNode object from this node's inNodes.
 * @param   {$.oNode}   oNodeObject            The node to link this one's inport to.
 * @return  {bool}    The result of the unlink. Refreshes attributes to update for the changes of connected transformation.
 */
$.oTransformSwitchNode.prototype.unlinkInNode = function( oNodeObject ){
  this.$.oNode.prototype.unlinkInNode.apply(this, arguments);
  this.refreshNames()
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//    $.oColorOverrideNode class    //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for the $.oColorOverrideNode class
 * @classdesc
 * $.oColorOverrideNode is a subclass of $.oNode and implements the same methods and properties as $.oNode. <br>
 * It represents color overrides in the scene.
 * @constructor
 * @augments   $.oNode
 * @param   {string}         path                          Path to the node in the network.
 * @param   {oScene}         oSceneObject                  Access to the oScene object of the DOM.
 */
 $.oColorOverrideNode = function(path, oSceneObject) {
  // $.oDrawingNode can only represent a node of type 'READ'
  if (node.type(path) != 'COLOR_OVERRIDE_TVG') throw "'path' parameter must point to a 'COLOR_OVERRIDE_TVG' type node";
  var instance = this.$.oNode.call(this, path, oSceneObject);
  if (instance) return instance;

  this._type = 'colorOverrideNode';
  this._coObject = node.getColorOverride(path)
}
$.oColorOverrideNode.prototype = Object.create($.oNode.prototype);
$.oColorOverrideNode.prototype.constructor = $.oColorOverrideNode;


/**
 * The list of palette overrides in this color override node
 * @name $.oColorOverrideNode#palettes
 * @type {$.oPalette[]}
 * @readonly
 */
Object.defineProperty($.oColorOverrideNode.prototype, "palettes", {
  get: function(){
    this.$.debug("getting palettes", this.$.DEBUG_LEVEL.LOG)
    if (!this._palettes){
      this._palettes = [];

      var _numPalettes = this._coObject.getNumPalettes();
      for (var i=0; i<_numPalettes; i++){
        var _palettePath = this._coObject.palettePath(i) + ".plt";
        var _palette = this.$.scn.getPaletteByPath(_palettePath);
        if (_palette) this._palettes.push(_palette);
      }
    }

    return this._palettes;
  }
})

/**
 * Add a new palette to the palette list (for now, only supports scene palettes)
 * @param {$.oPalette} palette
*/
$.oColorOverrideNode.prototype.addPalette = function(palette){
  var _palettes = this.palettes // init palettes cache to add to it

  this._coObject.addPalette(palette.path.path);
  this._palettes.push(palette);
}

/**
 * Removes a palette to the palette list (for now, only supports scene palettes)
 * @param {$.oPalette} palette
 */
$.oColorOverrideNode.prototype.removePalette = function(palette){
  this._coObject.removePalette(palette.path.path);
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oGroupNode class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for the $.oGroupNode class
 * @classdesc
 * $.oGroupNode is a subclass of $.oNode and implements the same methods and properties as $.oNode. <br>
 * It represents groups in the scene. From this class, it's possible to add nodes, and backdrops, import files and templates into the group.
 * @constructor
 * @augments   $.oNode
 * @param   {string}         path                          Path to the node in the network.
 * @param   {oScene}         oSceneObject                  Access to the oScene object of the DOM.
 * @example
 * // to add a new node, grab the group it'll be created in first
 * var doc = $.scn
 * var sceneRoot = doc.root;                                              // grab the scene root group
 *
 * var myGroup = sceneRoot.addGrop("myGroup", false, false);              // create a group in the scene root, with a peg and composite but no nodes
 * var MPO = myGroup.multiportOut;                                        // grab the multiport in of the group
 *
 * var myNode = myGroup.addDrawingNode("myDrawingNode");                  // add a drawing node inside the group
 * myNode.linkOutNode(MPO);                                               // link the newly created node to the multiport
 * myNode.centerAbove(MPO);
 *
 * var sceneComposite = doc.$node("Top/Composite");                       // grab the scene composite node
 * myGroup.linkOutNode(sceneComposite);                                   // link the group to it
 *
 * myGroup.centerAbove(sceneComposite);
 */
$.oGroupNode = function(path, oSceneObject) {
    // $.oDrawingNode can only represent a node of type 'READ'
    if (node.type(path) != 'GROUP') throw "'path' parameter must point to a 'GROUP' type node";
    var instance = this.$.oNode.call(this, path, oSceneObject);
    if (instance) return instance;

    this._type = 'groupNode';
}
$.oGroupNode.prototype = Object.create($.oNode.prototype);
$.oGroupNode.prototype.constructor = $.oGroupNode;

/**
 * The multiport in node of the group. If one doesn't exist, it will be created.
 * @name $.oGroupNode#multiportIn
 * @readonly
 * @type {$.oNode}
 */
Object.defineProperty($.oGroupNode.prototype, "multiportIn", {
    get : function(){
        if (this.isRoot) return null
        var _MPI = this.scene.getNodeByPath(node.getGroupInputModule(this.path, "Multiport-In", 0,-100,0),this.scene)
        return (_MPI)
    }
})


/**
 * The multiport out node of the group. If one doesn't exist, it will be created.
 * @name $.oGroupNode#multiportOut
 * @readonly
 * @type {$.oNode}
 */
Object.defineProperty($.oGroupNode.prototype, "multiportOut", {
    get : function(){
        if (this.isRoot) return null
        var _MPO = this.scene.getNodeByPath(node.getGroupOutputModule(this.path, "Multiport-Out", 0, 100,0),this.scene)
        return (_MPO)
    }
});

 /**
 * All the nodes contained within the group, one level deep.
 * @name $.oGroupNode#nodes
 * @readonly
 * @type {$.oNode[]}
 */
Object.defineProperty($.oGroupNode.prototype, "nodes", {
  get : function() {
    var _path = this.path;
    var _nodes = node.subNodes(_path);

    var self = this;
    return _nodes.map(function(x){return self.scene.getNodeByPath(x)});
  }
});



 /**
 * All the backdrops contained within the group.
 * @name $.oGroupNode#backdrops
 * @readonly
 * @type {$.oBackdrop[]}
 */
Object.defineProperty($.oGroupNode.prototype, "backdrops", {
  get : function() {
    var _path = this.path;
    var _backdropObjects = Backdrop.backdrops(this.path);
    var _backdrops = _backdropObjects.map(function(x){return new this.$.oBackdrop(_path, x)});

    return _backdrops;
  }
});


 /**
 * Returns a node from within a group based on its name.
 * @param   {string}      name           The name of the node.
 *
 * @return  {$.oNode}     The node, or null if can't be found.
 */
$.oGroupNode.prototype.getNodeByName = function(name){
  var _path = this.path+"/"+name;

  return this.scene.getNodeByPath(_path);
}


 /**
 * Returns all the nodes of a certain type in the group.
 * Pass a value to recurse to look into the groups as well.
 * @param   {string}        typeName      The type of the nodes.
 * @param   {bool}          recurse       Wether to look inside the groups.
 *
 * @return  {$.oNode[]}     The nodes found.
 */
$.oGroupNode.prototype.getNodesByType = function(typeName, recurse){
  if (typeof recurse === 'undefined') var recurse = false;
  return this.subNodes(recurse).filter(function(x){return x.type == typeName});
}


 /**
 * Returns a child node in a group based on a search.
 * @param   {string}      name           The name of the node.
 *
 * @return  {$.oNode}     The node, or null if can't be found.
 */
$.oGroupNode.prototype.$node = function(name){
  return this.getNodeByName(name);
}


 /**
 * Gets all the nodes contained within the group.
 * @param   {bool}    [recurse=false]             Whether to recurse the groups within the groups.
 *
 * @return  {$.oNode[]}   The nodes in the group
 */
$.oGroupNode.prototype.subNodes = function(recurse){
    if (typeof recurse === 'undefined') recurse = false;

    var _nodes = node.subNodes(this.path);
    var _subNodes = [];

    for (var i in _nodes){
        var _oNodeObject = this.scene.getNodeByPath(_nodes[i]);
        _subNodes.push(_oNodeObject);
        if (recurse && node.isGroup(_nodes[i])) _subNodes = _subNodes.concat(_oNodeObject.subNodes(recurse));
    }

    return _subNodes;
}


 /**
 * Gets all children of the group.
 * @param   {bool}    [recurse=false]             Whether to recurse the groups within the groups.
 *
 * @return  {$.oNode[]}   The nodes in the group
 */
$.oGroupNode.prototype.children = function(recurse){
  return this.subNodes(recurse);
}



 /**
 * Creates an in-port on top of a group
 * @param   {int}         portNum            The port number where a port will be added
 * @type    {string}
 *
 * @return  {int}   The number of the created port in case the port specified was not correct (for example larger than the current number of ports + 1)
 */
$.oGroupNode.prototype.addInPort = function(portNum, type){
  var _inPorts = this.inPorts;

  if (typeof portNum === 'undefined') var portNum = _inPorts;
  if (portNum > _inPorts) portNum = _inPorts;

  var _type = (type=="transform")?"READ":"none"
  var _dummyNode = this.addNode(_type, "dummy_add_port_node");
  var _MPI = this.multiportIn;
  _dummyNode.linkInNode(_MPI, 0, portNum, true);
  _dummyNode.unlinkInNode(_MPI);
  _dummyNode.remove();

  return portNum;
}


 /**
 * Creates an out-port at the bottom of a group. For some reason groups can have many unconnected in-ports but only one unconnected out-port.
 * @param   {int}         [portNum]            The port number where a port will be added
 * @type    {string}
 *
 * @return  {int}   The number of the created port in case the port specified was not correct (for example larger than the current number of ports + 1)
 */
$.oGroupNode.prototype.addOutPort = function(portNum, type){
  var _outPorts = this.outPorts;

  if (typeof portNum === 'undefined') var portNum = _outPorts;
  if (portNum > _outPorts) portNum = _outPorts;

  var _type = (type=="transform")?"PEG":"none"
  var _dummyNode = this.addNode(_type, "dummy_add_port_node");
  var _MPO = this.multiportOut;

  _dummyNode.linkOutNode(_MPO, 0, portNum, true);
  _dummyNode.unlinkOutNode(_MPO);
  _dummyNode.remove();

  return portNum;
}

 /**
 * Gets all children of the group.
 * @param   {bool}    [recurse=false]             Whether to recurse the groups within the groups.
 *
 * @return  {$.oNode[]}   The nodes in the group
 */
$.oGroupNode.prototype.children = function(recurse){
  return this.subNodes(recurse);
}



 /**
 * Sorts out the node view inside the group
 * @param   {bool}    [recurse=false]             Whether to recurse the groups within the groups.
 */
$.oGroupNode.prototype.orderNodeView = function(recurse){
    if (typeof recurse === 'undefined') var recurse = false;

    TB_orderNetworkUpBatchFromList( node.subNodes(this.path) );

    if (!this.isRoot){
        var _MPO = this.multiportOut;
        var _MPI = this.multiportIn;

        _MPI.x = _MPO.x
    }

    if (recurse){
        var _subNodes = this.subNodes().filter(function(x){return x.type == "GROUP"});
        for (var i in _subNodes){
            _subNodes[i].orderNodeView(recurse);
        }
    }
}


/**
 * Adds a node to the group.
 * @param   {string}        type                   The type-name of the node to add.
 * @param   {string}        [name=type]            The name of the newly created node.
 * @param   {$.oPoint}      [nodePosition={0,0,0}] The position for the node to be placed in the network.
 *
 * @return {$.oNode}   The created node, or bool as false.
 * @example
 * // to add a node, simply call addNode on the group you want the node to be added to.
 * var sceneRoot = $.scn.root; // grab the scene root group ("Top")
 *
 * var peg = sceneRoot.addNode("PEG", "MyNewlyCreatedPeg");           // adding a peg
 *
 * // Now we'll also create a drawing node to connect under the peg
 * var sceneComposite = $.scn.getNodeByPath("Top/Composite");         // can also use $.scn.$node("Top/Composite") for shorter synthax
 *
 * var drawingNode = sceneRoot.addDrawingNode("myNewDrawingNode");
 * drawingNode.linkOutNode(sceneComposite);
 * drawingNode.can_animate = false                // setting some attributes on the newly created Node
 *
 * peg.linkOutNode(drawingNode);
 *
 * //through all this we didn't specify nodePosition parameters so we'll sort evertything at once
 *
 * sceneRoot.orderNodeView();
 *
 * // we can also do:
 *
 * peg.centerAbove(drawingNode);
 *
 */
$.oGroupNode.prototype.addNode = function( type, name, nodePosition ){
  // Defaults for optional parameters
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);
  if (typeof name === 'undefined') var name = type[0]+type.slice(1).toLowerCase();
  if (typeof name !== 'string') name = name+"";

  var _group = this.path;

  // create node and return result (this sanitizes/increments the name, so we only create the oNode with the returned value)
  var _path = node.add(_group, name, type, nodePosition.x, nodePosition.y, nodePosition.z);
  _node = this.scene.getNodeByPath(_path);

  return _node;
}


/**
 * Adds a drawing layer to the group, with a drawing column and element linked. Possible to specify the column and element to use.
 * @param   {string}     name                     The name of the newly created node.
 * @param   {$.oPoint}   [nodePosition={0,0,0}]   The position for the node to be placed in the network.
 * @param   {$.object}   [element]                The element to attach to the column.
 * @param   {object}     [drawingColumn]          The column to attach to the drawing module.

 * @return {$.oNode}     The created node, or bool as false.
 */

$.oGroupNode.prototype.addDrawingNode = function( name, nodePosition, oElementObject, drawingColumn){
  // add drawing column and element if not passed as parameters
  this.$.beginUndo("oH_addDrawingNode_"+name);

  // Defaults for optional parameters
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);
  if (typeof name === 'undefined') var name = type[0]+type.slice(1).toLowerCase();

  // creating the node first to get the "safe name" returned by harmony
  var _node = this.addNode("READ", name, nodePosition);

  if (typeof oElementObject === 'undefined') var oElementObject = this.scene.addElement(_node.name);
  if (typeof drawingColumn === 'undefined'){
    // first look for a column in the element
    if (!oElementObject.column) {
      var drawingColumn = this.scene.addColumn("DRAWING", _node.name, oElementObject);
    }else{
      var drawingColumn = oElementObject.column;
    }
  }

  // setup the node
  // setup animate mode/separate based on preferences?
  _node.attributes.drawing.element.column = drawingColumn;

  this.$.endUndo();

  return _node;
}


/**
 * Adds a new group to the group, and optionally move the specified nodes into it.
 * @param   {string}     name                           The name of the newly created group.
 * @param   {$.oPoint}   [addComposite=false]           Whether to add a composite.
 * @param   {bool}       [addPeg=false]                 Whether to add a peg.
 * @param   {$.oNode[]}  [includeNodes]                 The nodes to add to the group.
 * @param   {$.oPoint}   [nodePosition={0,0,0}]         The position for the node to be placed in the network.

 * @return {$.oGroupNode}   The created node, or bool as false.
 */
$.oGroupNode.prototype.addGroup = function( name, addComposite, addPeg, includeNodes, nodePosition ){
    // Defaults for optional parameters
    if (typeof addPeg === 'undefined') var addPeg = false;
    if (typeof addComposite === 'undefined') var addComposite = false;
    if (typeof includeNodes === 'undefined') var includeNodes = [];

    this.$.beginUndo("oH_addGroup_"+name);

    var nodeBox = new this.$.oBox();
    includeNodes = includeNodes.filter(function(x){return !!x}) // filter out all invalid types
    if (includeNodes.length > 0) nodeBox.includeNodes(includeNodes);

    if (typeof nodePosition === 'undefined') var nodePosition = includeNodes.length?nodeBox.center:new this.$.oPoint(0,0,0);

    var _group = this.addNode( "GROUP", name, nodePosition );

    var _MPI = _group.multiportIn;
    var _MPO = _group.multiportOut;

    if (addComposite){
      var _composite = _group.addNode("COMPOSITE", name+"_Composite");
      _composite.composite_mode = "Pass Through"; // get preference?
      _composite.linkOutNode(_MPO);
      _composite.centerAbove(_MPO);
    }

    if (addPeg){
      var _peg = _group.addNode("PEG", name+"-P");
      _peg.linkInNode(_MPI);
      _peg.centerBelow(_MPI);
    }

    // moves nodes into the created group and recreates their hierarchy and links
    if (includeNodes.length > 0){
      includeNodes = includeNodes.sort(function(a, b){return a.timelineIndex()>=b.timelineIndex()?1:-1})

      var _links = this.scene.getNodesLinks(includeNodes);

      for (var i in includeNodes){
        includeNodes[i].moveToGroup(_group);
      }

      for (var i in _links){
        _links[i].connect();
      }

      // link all unconnected nodes to the peg/MPI and comp/MPO
      var _topNode = _peg?_peg:_MPI;
      var _bottomNode = _composite?_composite:_MPO;

      for (var i in includeNodes){
        for (var j=0; j < includeNodes[i].inPorts; j++){
          if (includeNodes[i].getInLinksNumber(j) == 0) includeNodes[i].linkInNode(_topNode);
        }

        for (var j=0; j < includeNodes[i].outPorts; j++){
          if (includeNodes[i].getOutLinksNumber(j) == 0) includeNodes[i].linkOutNode(_bottomNode,0,0);
        }
      }

      //shifting MPI/MPO/peg/comp out of the way of included nodes
      if (_peg){
        _peg.centerAbove(includeNodes);
        includeNodes.push(_peg);
      }

      if (_composite){
        _composite.centerBelow(includeNodes);
        includeNodes.push(_composite);
      }

      _MPI.centerAbove(includeNodes);
      _MPO.centerBelow(includeNodes);
    }

    this.$.endUndo();
    return _group;
}


/**
 * Imports the specified template into the scene.
 * @param   {string}           tplPath                                        The path of the TPL file to import.
 * @param   {$.oNode[]}        [destinationNodes=false]                       The nodes affected by the template.
 * @param   {bool}             [extendScene=true]                             Whether to extend the exposures of the content imported.
 * @param   {$.oPoint}         [nodePosition={0,0,0}]                         The position to offset imported new nodes.
 * @param   {object}           [pasteOptions]                                 An object containing paste options as per Harmony's standard paste options.
 *
 * @return {$.oNode[]}         The resulting pasted nodes.
 */
$.oGroupNode.prototype.importTemplate = function( tplPath, destinationNodes, extendScene, nodePosition, pasteOptions ){
  if (typeof nodePosition === 'undefined') var nodePosition = new oPoint(0,0,0);
  if (typeof destinationNodes === 'undefined' || destinationNodes.length == 0) var destinationNodes = false;
  if (typeof extendScene === 'undefined') var extendScene = true;

  if (typeof pasteOptions === 'undefined') var pasteOptions = copyPaste.getCurrentPasteOptions();
  pasteOptions.extendScene = extendScene;

  this.$.beginUndo("oH_importTemplate");

  var _group = this.path;

  if(tplPath instanceof this.$.oFolder) tplPath = tplPath.path;

  this.$.debug("importing template : "+tplPath, this.$.DEBUG_LEVEL.LOG);

  var _copyOptions = copyPaste.getCurrentCreateOptions();
  var _tpl = copyPaste.copyFromTemplate(tplPath, 0, 999, _copyOptions); // any way to get the length of a template before importing it?

  if (destinationNodes){
    // TODO: deal with import options to specify frames
    copyPaste.paste(_tpl, destinationNodes.map(function(x){return x.path}), 0, 999, pasteOptions);
    var _nodes = destinationNodes;
  }else{
    var oldBackdrops = this.backdrops;
    copyPaste.pasteNewNodes(_tpl, _group, pasteOptions);
    var _scene = this.scene;
    var _nodes = selection.selectedNodes().map(function(x){return _scene.$node(x)});
    for (var i in _nodes){
      // only move the root nodes
      if (_nodes[i].parent.path != this.path) continue

      _nodes[i].x += nodePosition.x;
      _nodes[i].y += nodePosition.y;
    }

    // move backdrops present in the template
    var backdrops = this.backdrops.slice(oldBackdrops.length);
    for (var i in backdrops){
      backdrops[i].x += nodePosition.x;
      backdrops[i].y += nodePosition.y;
    }
    
    // move waypoints in the top level of the template
    for (var i in _nodes) {
      var nodePorts = _nodes[i].outPorts;
      for (var p = 0; p < nodePorts; p++) {
        var theseWP = waypoint.childWaypoints(_nodes[i], p);
        if (theseWP.length > 0) {
          for (var w in theseWP) {
            var x = waypoint.coordX(theseWP[w]);
            var y = waypoint.coordY(theseWP[w]);
            x += nodePosition.x;
            y += nodePosition.y;
            waypoint.setCoord(theseWP[w],x,y);
          }
        }
      }
    }
    
  }

  this.$.endUndo();
  return _nodes;
}


/**
 * Adds a backdrop to a group in a specific position.
 * @param   {string}           [title="Backdrop"]                The title of the backdrop.
 * @param   {string}           [body=""]                         The body text of the backdrop.
 * @param   {$.oColorValue}    [color="#323232ff"]               The oColorValue of the node.
 * @param   {float}            [x=0]                             The X position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            [y=0]                             The Y position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            [width=30]                        The Width of the backdrop, a padding value if nodes are specified.
 * @param   {float}            [height=30]                       The Height of the backdrop, a padding value if nodes are specified.
 *
 * @return {$.oBackdrop}       The created backdrop.
 */
$.oGroupNode.prototype.addBackdrop = function(title, body, color, x, y, width, height ){
  if (typeof color === 'undefined') var color = new this.$.oColorValue("#323232ff");
  if (typeof body === 'undefined') var body = "";

  if (typeof x === 'undefined') var x = 0;
  if (typeof y === 'undefined') var y = 0;
  if (typeof width === 'undefined') var width = 30;
  if (typeof height === 'undefined') var height = 30;

  var position = {"x":x, "y":y, "w":width, "h":height};

  var groupPath = this.path;

  if(!(color instanceof this.$.oColorValue)) color = new this.$.oColorValue(color);


  // incrementing title so that two backdrops can't have the same title
  if (typeof title === 'undefined') var title = "Backdrop";

  var _groupBackdrops = Backdrop.backdrops(groupPath);
  var names = _groupBackdrops.map(function(x){return x.title.text})
  var count = 0;
  var newTitle = title;

  while (names.indexOf(newTitle) != -1){
    count++;
    newTitle = title+"_"+count;
  }
  title = newTitle;


  var _backdrop = {
  "position"    : position,
  "title"       : {"text":title, "color":4278190080, "size":12, "font":"Arial"},
  "description" : {"text":body, "color":4278190080, "size":12, "font":"Arial"},
  "color"       : color.toInt()
  }

  Backdrop.addBackdrop(groupPath, _backdrop)
  return new this.$.oBackdrop(groupPath, _backdrop)
};


/**
 * Adds a backdrop to a group around specified nodes
 * @param   {$.oNode[]}        nodes                             The nodes that the backdrop encompasses.
 * @param   {string}           [title="Backdrop"]                The title of the backdrop.
 * @param   {string}           [body=""]                         The body text of the backdrop.
 * @param   {$.oColorValue}    [color=#323232ff]                 The oColorValue of the node.
 * @param   {float}            [x=0]                             The X position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            [y=0]                             The Y position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            [width=20]                        The Width of the backdrop, a padding value if nodes are specified.
 * @param   {float}            [height=20]                       The Height of the backdrop, a padding value if nodes are specified.
 *
 * @return {$.oBackdrop}       The created backdrop.
 * @example
 * function createColoredBackdrop(){
 *  // This script will prompt for a color and create a backdrop around the selection
 *  $.beginUndo()
 *
 *  var doc = $.scn; // grab the scene
 *  var nodes = doc.getSelectedNodes(); // grab the selection
 *
 *  if(!nodes) return    // exit the function if no nodes are selected
 *
 *  var color = pickColor(); // prompt for color
 *
 *  var group = nodes[0].group // get the group to add the backdrop to
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
$.oGroupNode.prototype.addBackdropToNodes = function( nodes, title, body, color, x, y, width, height ){
  if (typeof color === 'undefined') var color = new this.$.oColorValue("#323232ff");
  if (typeof body === 'undefined') var body = "";
  if (typeof x === 'undefined') var x = 0;
  if (typeof y === 'undefined') var y = 0;
  if (typeof width === 'undefined') var width = 20;
  if (typeof height === 'undefined') var height = 20;


  // get default size from node bounds
  if (typeof nodes === 'undefined') var nodes = [];

  if (nodes.length > 0) {
    var _nodeBox = new this.$.oBox();
    _nodeBox.includeNodes(nodes);

    x = _nodeBox.left - x - width;
    y = _nodeBox.top - y - height;
    width = _nodeBox.width  + width*2;
    height = _nodeBox.height + height*2;
  }

  var _backdrop = this.addBackdrop(title, body, color, x, y, width, height)

  return _backdrop;
};


/**
 * Imports a PSD into the group.
 * This function is not available when running as harmony in batch mode.
 * @param   {string}         path                          The PSD file to import.
 * @param   {bool}           [separateLayers=true]         Separate the layers of the PSD.
 * @param   {bool}           [addPeg=true]                 Whether to add a peg.
 * @param   {bool}           [addComposite=true]           Whether to add a composite.
 * @param   {string}         [alignment="ASIS"]            Alignment type.
 * @param   {$.oPoint}       [nodePosition={0,0,0}]        The position for the node to be placed in the node view.
 *
 * @return {$.oNode[]}     The nodes being created as part of the PSD import.
 * @example
 * // This example browses for a PSD file then import it in the root of the scene, then connects it to the main composite.
 *
 * function importCustomPSD(){
 *   $.beginUndo("importCustomPSD");
 *   var psd = $.dialog.browseForFile("get PSD", "*.psd");       // prompt for a PSD file
 *
 *   if (!psd) return;                                           // dialog was cancelled, exit the function
 *
 *   var doc = $.scn;                                            // get the scene object
 *   var sceneRoot = doc.root                                    // grab the scene root group
 *   var psdNodes = sceneRoot.importPSD(psd);                    // import the psd with default settings
 *   var psdComp = psdNodes.pop()                                // get the composite node at the end of the psdNodes array
 *   var sceneComp = doc.$node("Top/Composite")                  // get the scene main composite
 *   psdComp.linkOutNode(sceneComp);                             // ... and link the two.
 *   sceneRoot.orderNodeView();                                  // orders the node view inside the group
 *   $.endUndo();
 * }
 */
$.oGroupNode.prototype.importPSD = function( path, separateLayers, addPeg, addComposite, alignment, nodePosition){
  if (typeof alignment === 'undefined') var alignment = "ASIS" // create an enum for alignments?
  if (typeof addComposite === 'undefined') var addComposite = true;
  if (typeof addPeg === 'undefined') var addPeg = true;
  if (typeof separateLayers === 'undefined') var separateLayers = true;
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);

  if (this.$.batchMode){
    this.$.debug("Error: can't import PSD file "+_psdFile.path+" in batch mode.", this.$.DEBUG_LEVEL.ERROR);
    return null
  }

  var _psdFile = (path instanceof this.$.oFile)?path:new this.$.oFile( path );
  if (!_psdFile.exists){
    this.$.debug("Error: can't import PSD file "+_psdFile.path+" because it doesn't exist", this.$.DEBUG_LEVEL.ERROR);
    return null;
  }

  this.$.beginUndo("oH_importPSD_"+_psdFile.name);

  var _elementName = _psdFile.name;

  var _xSpacing = 45;
  var _ySpacing = 30;

  var _element = this.scene.addElement(_elementName, "PSD");

  // save scene otherwise PSD is copied correctly into the element
  // but the TGA for each layer are not generated
  // TODO: how to go around this to avoid saving?
  scene.saveAll();
  var _drawing = _element.addDrawing(1);

  if (addPeg) var _peg = this.addNode("PEG", _elementName+"-P", nodePosition);
  if (addComposite) var _comp = this.addNode("COMPOSITE", _elementName+"-Composite", nodePosition);

  // Import the PSD in the element
  CELIO.pasteImageFile({ src : _psdFile.path, dst : { elementId : _element.id, exposure : _drawing.name}});
  var _layers = CELIO.getLayerInformation(_psdFile.path);
  var _info = CELIO.getInformation(_psdFile.path);

  // create the nodes for each layer
  var _nodes = [];
  if (separateLayers){

    var _scale = _info.height/scene.defaultResolutionY();
    var _x = nodePosition.x - _layers.length/2*_xSpacing;
    var _y = nodePosition.y - _layers.length/2*_ySpacing;

    for (var i in _layers){
      // generate nodes and set them to show the element for each layer
      var _layer = _layers[i];
      var _layerName = _layer.layerName.split(" ").join("_");
      var _nodePosition = new this.$.oPoint(_x+=_xSpacing, _y +=_ySpacing, 0);

      // get/build the group
      var _group = this;
      var _groupPathComponents = _layer.layerPathComponents;
      var _destinationPath = this.path;
      var _groupPeg = _peg;
      var _groupComp = _comp;

      // recursively creating groups if they are missing
      for (var i in _groupPathComponents){
        var _destinationPath = _destinationPath + "/" + _groupPathComponents[i];
        var _nextGroup = this.$.scene.getNodeByPath(_destinationPath);

        if (!_nextGroup){
          _nextGroup = _group.addGroup(_groupPathComponents[i], true, true, [], _nodePosition);
          if (_groupPeg) _nextGroup.linkInNode(_groupPeg);
          if (_groupComp) _nextGroup.linkOutNode(_groupComp, 0, 0);
        }
        // store the peg/comp for next iteration or layer node
        _group = _nextGroup;
        _groupPeg = _group.multiportIn.linkedOutNodes[0];
        _groupComp = _group.multiportOut.linkedInNodes[0];
      }

      var _column = this.scene.addColumn("DRAWING", _layerName, _element);
      var _node = _group.addDrawingNode(_layerName, _nodePosition, _element, _column);

      _node.enabled = _layers[i].visible;
      _node.can_animate = false; // use general pref?
      _node.apply_matte_to_color = "Straight";
      _node.alignment_rule = alignment;
      _node.scale.x = _scale;
      _node.scale.y = _scale;

      _column.setValue(_layer.layer != ""?"1:"+_layer.layer:1, 1);
      _column.extendExposures();

      if (_groupPeg) _node.linkInNode(_groupPeg);
      if (_groupComp) _node.linkOutNode(_groupComp, 0, 0);

      _nodes.push(_node);
    }
  }else{
    this.$.endUndo();
    throw new Error("importing PSD as a flattened layer not yet implemented");
  }

  if (addPeg){
    _peg.centerAbove(_nodes, 0, -_ySpacing )
    _nodes.unshift(_peg)
  }

  if (addComposite){
    _comp.centerBelow(_nodes, 0, _ySpacing )
    _nodes.push(_comp)
  }
  // TODO how to display only one node with the whole file
  this.$.endUndo()

  return _nodes
}


/**
 * Updates a PSD previously imported into the group
 * @param   {string}       path                          The updated psd file to import.
 * @param   {bool}         [separateLayers=true]         Separate the layers of the PSD.
 *
 * @return  {$.oNode[]}    The nodes that have been updated/created
 */
$.oGroupNode.prototype.updatePSD = function( path, separateLayers ){
  if (typeof separateLayers === 'undefined') var separateLayers = true;

  var _psdFile = (path instanceof this.$.oFile)?path:new this.$.oFile(path);
  if (!_psdFile.exists){
    this.$.debug("Error: can't import PSD file "+_psdFile.path+" for update because it doesn't exist", this.$.DEBUG_LEVEL.ERROR);
    return null;
  }

  this.$.beginUndo("oH_updatePSD_"+_psdFile.name)

  // get info from the PSD
  var _info = CELIO.getInformation(_psdFile.path);
  var _layers = CELIO.getLayerInformation(_psdFile.path);
  var _scale = _info.height/scene.defaultResolutionY();

  // use layer information to find nodes from precedent export
  if (separateLayers){
    var _nodes = this.subNodes(true).filter(function(x){return x.type == "READ"});
    var _nodeNames = _nodes.map(function(x){return x.name});

    var _psdNodes = [];
    var _missingLayers = [];
    var _PSDelement = "";
    var _positions = new Array(_layers.length);
    var _scale = _info.height/scene.defaultResolutionY();

    // for each layer find the node by looking at the column name
    for (var i in _layers){
      var _layer = _layers[i];
      var _layerName = _layers[i].layerName.split(" ").join("_");
      var _found = false;

      // find the node
      for (var j in _nodes){
        if (_nodes[j].element.format != "PSD") continue;

        var _drawingColumn = _nodes[j].attributes.drawing.element.column;

        // update the node if found
        if (_drawingColumn.name == _layer.layerName){
          _psdNodes.push(_nodes[j]);
          _found = true;

           // update scale in case PSDfile size changed
          _nodes[j].scale.x = _scale;
          _nodes[j].scale.y = _scale;

          _positions[_layer.position] = _nodes[j];

          // store the element
          _PSDelement = _nodes[j].element

          break;
        }
        // if not found, add to the list of layers to import
        _found = false;
      }

      if (!_found) _missingLayers.push(_layer);
    }


    if (_psdNodes.length == 0){
      // PSD was never imported, use import instead?
      this.$.debug("can't find a PSD element to update", this.$.DEBUG_LEVEL.ERROR);
      this.$.endUndo();
      return null;
    }

    // pasting updated PSD into element
    CELIO.pasteImageFile({ src : _psdFile.path, dst : { elementId : _PSDelement.id, exposure : "1"}})

    for (var i in _missingLayers){
      // find previous import Settings re: group/alignment etc
      var _layer = _missingLayers[i];
      var _layerName = _layer.layerName.split(" ").join("_");

      var _layerIndex = _layer.position;
      var _nodePosition = new this.$.oPoint(0,0,0);
      var _group = _psdNodes[0].group;
      var _alignment = _psdNodes[0].alignment_rule;
      var _scale = _psdNodes[0].scale.x;
      var _peg = _psdNodes[0].inNodes[0];
      var _comp = _psdNodes[0].outNodes[0];
      var _scale = _info.height/scene.defaultResolutionY()
      var _port;

      //TODO: set into right group according to PSD organisation
      // looking for the existing node below and get the comp port from it
      for (var j = _layerIndex-1; j>=0; j--){
        if (_positions[j] != undefined) break;
      }
      var _nodeBelow = _positions[j];

      var _compNodes = _comp.inNodes;

      for (var j=0; j<_compNodes.length; j++){
        if (_nodeBelow.path == _compNodes[j].path){
          _port = j+1;
          _nodePosition = _compNodes[j].nodePosition;
          _nodePosition.x -= 35;
          _nodePosition.y -= 25;
        }
      }

      // generate nodes and set them to show the element for each layer
      var _node = this.addDrawingNode(_layerName, _nodePosition, _PSDelement);

      _node.enabled = _layer.visible;
      _node.can_animate = false; // use general pref?
      _node.apply_matte_to_color = "Straight";
      _node.alignment_rule = _alignment;
      _node.scale.x = _scale;
      _node.scale.y = _scale;

      _node.attributes.drawing.element.setValue(_layer.layer != ""?"1:"+_layer.layer:1, 1);
      _node.attributes.drawing.element.column.extendExposures();

      // find composite/peg to connect to based on other layers

      //if (addPeg) _node.linkInNode(_peg)
      if (_port) _node.linkOutNode(_comp, 0, _port)

      _nodes.push(_node);
    }
    this.$.endUndo();
    return nodes;
  } else{
      this.$.endUndo();
      throw new Error("updating a PSD imported as a flattened layer not yet implemented");
  }
}


/**
 * Import a generic image format (PNG, JPG, TGA etc) as a read node.
 * @param {string} path The image file to import.
 * @param {string} [alignment="ASIS"] Alignment type.
 * @param {$.oPoint} [nodePosition={0,0,0}] The position for the node to be placed in the node view.
 *
 * @return  {$.oNode}    The node for the imported image
 */
$.oGroupNode.prototype.importImage = function( path, alignment, nodePosition, convertToTvg){
  if (typeof alignment === 'undefined') var alignment = "ASIS"; // create an enum for alignments?
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);

  var _imageFile = (path instanceof this.$.oFile)?path:new this.$.oFile( path );
  var _elementName = _imageFile.name;

  var _elementType = convertToTvg?"TVG":_imageFile.extension.toUpperCase();
  var _element = this.scene.addElement(_elementName, _elementType);
  var _column = this.scene.addColumn("DRAWING", _elementName, _element);
  _element.column = _column;

  if (_imageFile.exists) {
    var _drawing = _element.addDrawing(1, 1, _imageFile.path, convertToTvg);
  }else{
    this.$.debug("Image file to import "+_imageFile.path+" could not be found.", this.$.DEBUG_LEVEL.ERROR);
  }

  var _imageNode = this.addDrawingNode(_elementName, nodePosition, _element);

  _imageNode.can_animate = false; // use general pref?
  _imageNode.apply_matte_to_color = "Straight";
  _imageNode.alignment_rule = alignment;

  var _scale = CELIO.getInformation(_imageFile.path).height/this.scene.defaultResolutionY;
  _imageNode.scale.x = _scale;
  _imageNode.scale.y = _scale;

  _imageNode.attributes.drawing.element.setValue(_drawing.name, 1);
  _imageNode.attributes.drawing.element.column.extendExposures();

  // TODO how to display only one node with the whole file
  return _imageNode;
}


/**
 * imports an image as a tvg drawing.
 * @param {$.oFile} path                         the image file to import
 * @param {string} [alignment="ASIS"]            the alignment mode for the imported image
 * @param {$.oPoint} [nodePosition={0,0,0}]      the position for the created node.
 */
$.oGroupNode.prototype.importImageAsTVG = function(path, alignment, nodePosition){
  if (!(path instanceof this.$.oFile)) path = new this.$.oFile(path);

  var _imageNode = this.importImage(_convertedFilePath, alignment, nodePosition, true);
  _imageNode.name = path.name;

  return _imageNode;
}


/**
 * imports an image sequence as a node into the current group.
 * @param {$.oFile[]} imagePaths           a list of paths to the images to import (can pass a list of strings or $.oFile)
 * @param {number}    [exposureLength=1]   the number of frames each drawing should be exposed at. If set to 0/false, each drawing will use the numbering suffix of the file to set its frame.
 * @param {boolean}   [convertToTvg=false] wether to convert the files to tvg during import
 * @param {string}    [alignment="ASIS"]   the alignment to apply to the node
 * @param {$.oPoint}  [nodePosition]       the position of the node in the nodeview
 *
 * @returns {$.oDrawingNode} the created node
 */
$.oGroupNode.prototype.importImageSequence = function(imagePaths, exposureLength, convertToTvg, alignment, nodePosition, extendScene) {
  if (typeof exposureLength === 'undefined') var exposureLength = 1;
  if (typeof alignment === 'undefined') var alignment = "ASIS"; // create an enum for alignments?
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);

  if (typeof extendScene === 'undefined') var extendScene = false;

  // match anything but capture trailing numbers and separates punctuation preceeding it
  var numberingRe = /(.*?)([\W_]+)?(\d*)$/i;

  // sanitize imagePaths
  imagePaths = imagePaths.map(function(x){
    if (x instanceof this.$.oFile){
      return x;
    } else {
      return new this.$.oFile(x);
    }
  })

  var images = [];

  if (!exposureLength) {
  // figure out scene length based on exposure and extend the scene if needed
    var sceneLength = 0;
    var image = {frame:0, path:""};

    for (var i in imagePaths){
      var imagePath = imagePaths[i];
      if (!(imagePath instanceof this.$.oFile)) imagePath = new this.$.oFile(imagePath);
      var nameGroups = imagePath.name.match(numberingRe);

      if (nameGroups[3]){
        // use trailing number as frame number
        var frameNumber = parseInt(nameGroups[3], 10);
        if (frameNumber > sceneLength) sceneLength = frameNumber;

        images.push({frame: frameNumber, path:imagePath});
      }
    }
  } else {
    // simply create a list of numbers based on exposure
    images = imagePaths.map(function(x, index){
      var frameNumber = index * exposureLength + 1;
      return ({frame:frameNumber, path:x});
    })
    var sceneLength = images[images.length-1].frame + exposureLength - 1;
  }

  if (extendScene){
    if (this.scene.length < sceneLength) this.scene.length = sceneLength;
  }

  // create a node to hold the image sequence
  var firstImage = imagePaths[0];
  var name = firstImage.name.match(numberingRe)[1]; // match anything before trailing digits
  var drawingNode = this.importImage(firstImage, alignment, nodePosition, convertToTvg);
  drawingNode.name = name;

  for (var i in images){
    var image = images[i];
    drawingNode.element.addDrawing(image.frame, image.frame, image.path, convertToTvg);
  }

  drawingNode.timingColumn.extendExposures();

  return drawingNode;
}

/**
 * Imports a QT into the group
 * @param   {string}         path                          The palette file to import.
 * @param   {bool}           [importSound=true]            Whether to import the sound
 * @param   {bool}           [extendScene=true]            Whether to extend the scene to the duration of the QT.
 * @param   {string}         [alignment="ASIS"]            Alignment type.
 * @param   {$.oPoint}       [nodePosition]                The position for the node to be placed in the network.
 *
 * @return {$.oNode}        The imported Quicktime Node.
 */
$.oGroupNode.prototype.importQT = function( path, importSound, extendScene, alignment, nodePosition){
  if (typeof alignment === 'undefined') var alignment = "ASIS";
  if (typeof extendScene === 'undefined') var extendScene = true;
  if (typeof importSound === 'undefined') var importSound = true;
  if (typeof nodePosition === 'undefined') var nodePosition = new this.$.oPoint(0,0,0);

  var _QTFile = (path instanceof this.$.oFile)?path:new this.$.oFile(path);
  if (!_QTFile.exists){
    throw new Error ("Import Quicktime failed: file "+_QTFile.path+" doesn't exist");
  }

  var _movieName = _QTFile.name;
  this.$.beginUndo("oH_importQT_"+_movieName);

  var _element = this.scene.addElement(_movieName, "PNG");
  var _elementName = _element.name;

  var _movieNode = this.addDrawingNode(_movieName, nodePosition, _element);
  var _column = _movieNode.attributes.drawing.element.column;
  _element.column = _column;

  // setup the node
  _movieNode.can_animate = false;
  _movieNode.alignment_rule = alignment;

  // create the temp folder
  var _tempFolder = new this.$.oFolder(this.$.scn.tempFolder.path + "/movImport/" + _element.id);
  _tempFolder.create();

  var _tempFolderPath = _tempFolder.path;
  var _audioPath = _tempFolder.path + "/" + _movieName + ".wav";

  // progressDialog will display an infinite loading bar as we don't have precise feedback
  var progressDialog = new this.$.oProgressDialog("Importing video...", 0, "Import Movie", true);

  // setup import
  MovieImport.setMovieFilename(_QTFile.path);
  MovieImport.setImageFolder(_tempFolder);
  MovieImport.setImagePrefix(_movieName);
  if (importSound) MovieImport.setAudioFile(_audioPath);
  this.$.log("converting movie file to pngs...");
  MovieImport.doImport();
  this.$.log("conversion finished");

  progressDialog.range = 100;
  progressDialog.value = 80;

  var _movielength = MovieImport.numberOfImages();

  if (extendScene && this.scene.length < _movielength) this.scene.length = _movielength;

  // create a drawing for each frame
  for (var i=1; i<=_movielength; i++) {
    _drawingPath = _tempFolder + "/" + _movieName + "-" + i + ".png";
    _element.addDrawing(i, i, _drawingPath);
  }

  progressDialog.value = 95;

  // creating an audio column for the sound
  if (importSound && MovieImport.isAudioFileCreated() ){
    var _soundName = _elementName + "_sound";
    var _soundColumn = this.scene.addColumn("SOUND", _soundName);
    column.importSound( _soundColumn.name, 1, _audioPath);
  }

  progressDialog.value = 100;

  this.$.endUndo();
  return _movieNode;
}

