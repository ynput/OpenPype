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
//          $.oLayer class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for $.oLayer class
 * @classdesc
 * The $.oLayer class represents a single line in the timeline.
 * @constructor
 * @param   {oTimeline}                oTimelineObject       The timeline associated to this layer.
 * @param   {int}                      layerIndex            The index of the layer on the timeline (all layers included, node and columns).
 *
 * @property {int}                     index                 The index of the layer on the timeline.
 * @property {oTimeline}               timeline              The timeline associated to this layer.
 * @property {oNode}                   node                  The node associated to the layer.
 */
$.oLayer = function( oTimelineObject, layerIndex){
  this.timeline = oTimelineObject;
  this.index = layerIndex;
}


/**
 * The node associated to the layer.
 * @name $.oLayer#node
 * @type {$.oNode}
 */
Object.defineProperty($.oLayer.prototype, "node", {
  get: function(){
    if (this.$.batchMode){
      _node = this.timeline.nodes[this.index];
    } else {
      _node = this.$.scn.getNodeByPath(Timeline.layerToNode(this.index));
    }
    return _node
  }
})


/**
 * the parent layer for this layer in the timeline. Returns the root group if layer is top level.
 * @name $.oLayer#parent
 * @type {$.oLayer}
 */
Object.defineProperty($.oLayer.prototype, "parent", {
  get: function(){
    var _parentIndex = Timeline.parentNodeIndex(this.index);
    if (_parentIndex == -1) return $.scn.root;
    var _parent = this.timeline.allLayers[_parentIndex];

    return _parent;
  }
})


/**
 * wether or not the layer is selected.
 * @name $.oLayer#selected
 * @type {bool}
 * @readonly
 */
 Object.defineProperty($.oLayer.prototype, "selected", {
  get: function(){
    var selectionLength = Timeline.numLayerSel
    for (var i=0; i<selectionLength; i++){
      if (Timeline.selToLayer(i) == this.index) return true;
    }
    return false;
  },
  set:function(){
    throw new Error ("unnamed layers selection cannot be set.")
  }
})


/**
 * The name of this layer/node.
 * @name $.oLayer#name
 * @type {string}
 * @readonly
 */
 Object.defineProperty($.oLayer.prototype, "name", {
  get: function(){
    return "unnamed layer";
  }
})


/**
 * @private
 */
$.oLayer.prototype.toString = function(){
  return "<$.oLayer '"+this.name+"'>";
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oNodeLayer class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for $.oNodeLayer class
 * @classdesc
 * The $.oNodeLayer class represents a timeline layer corresponding to a node from the scene.
 * @constructor
 * @extends $.oLayer
 * @param   {oTimeline}                oTimelineObject       The timeline associated to this layer.
 * @param   {int}                      layerIndex            The index of the layer on the timeline.
 *
 * @property {int}                     index                 The index of the layer on the timeline.
 * @property {oTimeline}               timeline              The timeline associated to this layer.
 * @property {oNode}                   node                  The node associated to the layer.
 */
$.oNodeLayer = function( oTimelineObject, layerIndex){
  this.$.oLayer.apply(this, [oTimelineObject, layerIndex]);
}
$.oNodeLayer.prototype = Object.create($.oLayer.prototype);


/**
 * The name of this layer/node.
 * @name $.oNodeLayer#name
 * @type {string}
 */
Object.defineProperty($.oNodeLayer.prototype, "name", {
  get: function(){
    return this.node.name;
  },
  set: function(newName){
    this.node.name = newName;
  }
})


/**
 * The layer index when ignoring subLayers.
 * @name $.oNodeLayer#layerIndex
 * @type {int}
*/
Object.defineProperty($.oNodeLayer.prototype, "layerIndex", {
  get: function(){
    var _layers = this.timeline.layers.map(function(x){return x.node.path});
    return _layers.indexOf(this.node.path);
  }
})


/**
 * wether or not the layer is selected.
 * @name $.oNodeLayer#selected
 * @type {bool}
 */
Object.defineProperty($.oNodeLayer.prototype, "selected", {
  get: function(){
    if ($.batchMode) return this.node.selected;

    var selectionLength = Timeline.numLayerSel
    for (var i=0; i<selectionLength; i++){
      if (Timeline.selToLayer(i) == this.index) return true;
    }
    return false;
  },
  set: function(selected){
    this.node.selected = selected;
  }
})


/**
 * The column layers associated with this node.
 * @name $.oNodeLayer#subLayers
 * @type {$.oColumnLayer[]}
*/
Object.defineProperty($.oNodeLayer.prototype, "subLayers", {
  get: function(){
    var _node = this.node;
    var _nodeLayerType = this.$.oNodeLayer;
    return this.timeline.allLayers.filter(function (x){return x.node.path == _node.path && !(x instanceof _nodeLayerType)});
  }
})



/**
 * @private
 */
$.oNodeLayer.prototype.toString = function(){
  return "<$.oNodeLayer '"+this.name+"'>";
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oDrawingLayer class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * Constructor for $.oDrawingLayer class
 * @classdesc
 * The $.oDrawingLayer class represents a timeline layer corresponding to a 'READ' node (or Drawing in Toonboom UI) from the scene.
 * @constructor
 * @extends $.oNodeLayer
 * @param   {oTimeline}                oTimelineObject       The timeline associated to this layer.
 * @param   {int}                      layerIndex            The index of the layer on the timeline.
 *
 * @property {int}                     index                 The index of the layer on the timeline.
 * @property {oTimeline}               timeline              The timeline associated to this layer.
 * @property {oNode}                   node                  The node associated to the layer.
 */
$.oDrawingLayer = function( oTimelineObject, layerIndex){
  this.$.oNodeLayer.apply(this, [oTimelineObject, layerIndex]);
}
$.oDrawingLayer.prototype = Object.create($.oNodeLayer.prototype);


/**
 * The oFrame objects that hold the drawings for this layer.
 * @name oDrawingLayer#drawingColumn
 * @type {oFrame[]}
 */
 Object.defineProperty($.oDrawingLayer.prototype, "drawingColumn", {
  get: function(){
    return this.node.attributes.drawing.elements.column;
  }
})


/**
 * The oFrame objects that hold the drawings for this layer.
 * @name oDrawingLayer#exposures
 * @type {oFrame[]}
 */
Object.defineProperty($.oDrawingLayer.prototype, "exposures", {
  get: function(){
    return this.drawingColumn.frames;
  }
})


/**
 * @private
 */
 $.oDrawingLayer.prototype.toString = function(){
  return "<$.oDrawingLayer '"+this.name+"'>";
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oColumnLayer class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////
/**
 * Constructor for $.oColumnLayer class
 * @classdesc
 * The $.oColumnLayer class represents a timeline layer corresponding to the animated values of a column linked to a node.
 * @constructor
 * @extends $.oLayer
 * @param   {oTimeline}                oTimelineObject       The timeline associated to this layer.
 * @param   {int}                      layerIndex            The index of the layer on the timeline.
 *
 * @property {int}                     index                 The index of the layer on the timeline.
 * @property {oTimeline}               timeline              The timeline associated to this layer.
 * @property {oNode}                   node                  The node associated to the layer.
 */
$.oColumnLayer = function( oTimelineObject, layerIndex){
  this.$.oLayer.apply(this, [oTimelineObject, layerIndex]);
}
$.oColumnLayer.prototype = Object.create($.oLayer.prototype);


/**
 * The name of this layer.
 * (corresponding to the display name of the column, not the name displayed in timeline, not exposed by the Toonboom API).
 * @name $.oColumnLayer#name
 * @type {string}
 */
Object.defineProperty($.oColumnLayer.prototype, "name", {
  get: function(){
    return this.column.name;
  }
})



/**
 * the node attribute associated with this layer. Only available if the attribute has a column.
 * @name $.oColumnLayer#attribute
 * @type {$.oColumn}
 */
Object.defineProperty($.oColumnLayer.prototype, "attribute", {
  get: function(){
    if (!this._attribute){
      this._attribute = this.column.attributeObject;
    }
    return this._attribute
  }
})



/**
 * the node associated with this layer
 * @name $.oColumnLayer#column
 * @type {$.oColumn}
 */
Object.defineProperty($.oColumnLayer.prototype, "column", {
  get: function(){
    if (!this._column){
      var _name = Timeline.layerToColumn(this.index);
      var _attribute = this.node.getAttributeByColumnName(_name);
      this._column = _attribute.column;
    }
    return this._column;
  }
})


/**
 * The layer representing the node to which this column is linked
 */
Object.defineProperty($.oColumnLayer.prototype, "nodeLayer", {
  get: function(){
    var _node = this.node;
    var _nodeLayerType = this.$.oNodeLayer;
    this.timeline.allLayers.filter(function (x){return x.node == _node && x instanceof _nodeLayerType})[0];
  }
})



/**
 * @private
 */
 $.oColumnLayer.prototype.toString = function(){
  return "<$.oColumnLayer '"+this.name+"'>";
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oTimeline class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oTimeline constructor.
 * @constructor
 * @classdesc  The $.oTimeline class represents a timeline corresponding to a specific display.
 * @param   {string}      [display]  The display node's path. By default, the defaultDisplay of the scene.
 *
 * @property {string}     display    The display node's path.
 */
$.oTimeline = function(display){
  if (typeof display === 'undefined') var display = this.$.scn.defaultDisplay;
  if (display instanceof this.$.oNode) display = display.path;

  this.display = display;
}


/**
 * Gets the list of node layers in timeline.
 * @name $.oTimeline#layers
 * @type {$.oLayer[]}
 */
Object.defineProperty($.oTimeline.prototype, 'layers', {
  get : function(){
    var nodeLayer = this.$.oNodeLayer;
    return this.allLayers.filter(function (x){return x instanceof nodeLayer})
  }
});


/**
 * Gets the list of all layers in timeline, nodes and columns. In batchmode, will only return the nodes, not the sublayers.
 * @name $.oTimeline#allLayers
 * @type {$.oLayer[]}
 */
Object.defineProperty($.oTimeline.prototype, 'allLayers', {
  get : function(){
    if (!this._layers){
      var _layers = [];

      if (!$.batchMode){
        for( var i=0; i < Timeline.numLayers; i++ ){
          if (Timeline.layerIsNode(i)){
            var _layer = new this.$.oNodeLayer(this, i);
            if (_layer.node.type == "READ") var _layer = new this.$.oDrawingLayer(this, i);
          }else if (Timeline.layerIsColumn(i)) {
            var _layer = new this.$.oColumnLayer(this, i);
          }else{
            var _layer = new this.$.oLayer(this, i);
          }
          _layers.push(_layer);
        }
      } else {
        var _tl = this;
        var _layers = this.nodes.map(function(x, index){
          if (x.type == "READ") return new _tl.$.oDrawingLayer(_tl, index);
          return new _tl.$.oNodeLayer(_tl, index)
        })
      }

      this._layers = _layers;
    }
    return this._layers;
  }
});


/**
 * Gets the list of selected layers as oTimelineLayer objects.
 * @name $.oTimeline#selectedLayers
 * @type {oTimelineLayer[]}
 */
Object.defineProperty($.oTimeline.prototype, 'selectedLayers', {
  get : function(){
    return this.allLayers.filter(function(x){return x.selected});
  }
});




/**
 * The node layers in the scene, based on the timeline's order given a specific display.
 * @name $.oTimeline#compositionLayers
 * @type {oNode[]}
 * @deprecated use oTimeline.nodes instead if you want the nodes
 */
Object.defineProperty($.oTimeline.prototype, 'compositionLayers', {
  get : function(){
    return this.nodes;
  }
});


/**
 * The nodes present in the timeline.
 * @name $.oTimeline#nodes
 * @type {oNode[]}
 */
Object.defineProperty($.oTimeline.prototype, 'nodes', {
  get : function(){
    var _timeline = this.compositionLayersList;
    var _scene = this.$.scene;

    _timeline = _timeline.map( function(x){return _scene.getNodeByPath(x)} );

    return _timeline;
  }
});


/**
 * Gets the paths of the nodes displayed in the timeline.
 * @name $.oTimeline#nodesList
 * @type {string[]}
 * @deprecated only returns node path strings, use oTimeline.layers insteads
 */
Object.defineProperty($.oTimeline.prototype, 'nodesList', {
  get : function(){
    return this.compositionLayersList;
  }
});


/**
 * Gets the paths of the layers in order, given the specific display's timeline.
 * @name $.oTimeline#compositionLayersList
 * @type {string[]}
 * @deprecated only returns node path strings
 */
Object.defineProperty($.oTimeline.prototype, 'compositionLayersList', {
  get : function(){
    var _composition = this.composition;
    var _timeline = _composition.map(function(x){return x.node})

    return _timeline;
  }
});


/**
 * gets the composition for this timeline (array of native toonboom api 'compositionItems' objects)
 * @deprecated exposes native harmony api objects
 */
Object.defineProperty($.oTimeline.prototype, "composition", {
  get: function(){
    return compositionOrder.buildCompositionOrderForDisplay(this.display);
  }
})



/**
 * Refreshes the oTimeline's cached listing- in the event it changes in the runtime of the script.
 * @deprecated oTimeline.composition is now always refreshed when accessed.
 */
$.oTimeline.prototype.refresh = function( ){
  if (!node.type(this.display)) {
      this.composition = compositionOrder.buildDefaultCompositionOrder();
  }else{
      this.composition = compositionOrder.buildCompositionOrderForDisplay(this.display);
  }
}


/**
 * Build column to oNode/Attribute lookup cache. Makes the layer generation faster if using oTimeline.layers, oTimeline.selectedLayers
 * @deprecated
 */
$.oTimeline.prototype.buildLayerCache = function( forced ){
  if (typeof forced === 'undefined') forced = false;

  var cdate   = (new Date).getTime();
  var rebuild = forced;
  if( !this.$.cache_columnToNodeAttribute_date ){
    rebuild = true;
  }else if( !rebuild ){
    if( ( cdate - this.$.cache_columnToNodeAttribute_date ) > 1000*10 ){
      rebuild = true;
    }
  }

  if(rebuild){
    var nodeLayers = this.compositionLayers;

    if( this.$.cache_nodeAttribute ){
      this.$.cache_columnToNodeAttribute = {};
    }

    for( var n=0;n<nodeLayers.length;n++ ){
      this.$.cache_columnToNodeAttribute    = nodeLayers[n].getAttributesColumnCache( this.$.cache_columnToNodeAttribute );
    }
    this.$.cache_columnToNodeAttribute_date = cdate;
  }
}