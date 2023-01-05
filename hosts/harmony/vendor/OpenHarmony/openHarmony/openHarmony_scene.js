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
//          $.oScene class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


//TODO: Metadata, settings, aspect, camera peg, view.
/**
 * The constructor for $.oScene.
 * @classdesc
 * The base Class to access all the contents of the scene, and add elements. <br>This is the main class to do exporting operations as well as column/element/palette creation.
 * @constructor
 * @example
 * // Access to the direct dom object. Available and automatically instantiated as $.getScene, $.scene, $.scn, $.s
 * var doc = $.getScene ;
 * var doc = $.scn ;
 * ver doc = $.s ;         // all these are equivalents
 *
 * // To grab the scene from a QWidget Dialog callback, store the $ object in a local variable to access all the fonctions from the library.
 * function myCallBackFunction(){
 *   var this.$ = $;
 *
 *   var doc = this.$.scn;
 * }
 *
 *
 */
$.oScene = function( ){
    // $.oScene.nodes property is a class property shared by all instances, so it can be passed by reference and always contain all nodes in the scene

    //var _topNode = new this.$.oNode("Top");
    //this.__proto__.nodes = _topNode.subNodes(true);

  this._type = "scene";
}


//-------------------------------------------------------------------------------------
//--- $.oScene Objects Properties
//-------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------


/**
 * The folder that contains this scene.
 * @name $.oScene#path
 * @type {$.oFolder}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'path', {
  get : function(){
    return new this.$.oFolder( scene.currentProjectPathRemapped() );
  }
});

/**
 * The stage file of the scene.
 * @name $.oScene#stage
 * @type {$.oFile}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'stage', {
  get : function(){
    if (this.online) return this.path + "/stage/" + this.name + ".stage";
    return this.path + "/" + this.version + ".xstage";
  }
});

/**
 * The folder that contains this scene.
 * @name $.oScene#paletteFolder
 * @type {$.oFolder}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'paletteFolder', {
  get : function(){
    return new this.$.oFolder( this.path+"/palette-library" );
  }
});


/**
 * The temporary folder where files are created before being saved.
 * If the folder doesn't exist yet, it will be created.
 * @name $.oScene#tempFolder
 * @type {$.oFolder}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'tempFolder', {
  get : function(){
    if (!this.hasOwnProperty("_tempFolder")){
      this._tempFolder = new this.$.oFolder(scene.tempProjectPathRemapped());
      if (!this._tempFolder.exists) this._tempFolder.create()
    }
    return this._tempFolder;
  }
});

/**
 * The name of the scene.
 * @name $.oScene#name
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oScene.prototype, 'name', {
  get : function(){
    return scene.currentScene();
  }
});


/**
 * Wether the scene is hosted on a Toonboom database.
 * @name $.oScene#online
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oScene.prototype, 'online', {
  get : function(){
    return about.isDatabaseMode()
  }
});

/**
 * The name of the scene.
 * @name $.oScene#environnement
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oScene.prototype, 'environnement', {
  get : function(){
    if (!this.online) return null;
    return scene.currentEnvironment();
  }
});


/**
 * The name of the scene.
 * @name $.oScene#job
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oScene.prototype, 'job', {
  get : function(){
    if (!this.online) return null;
    return scene.currentJob();
  }
});


/**
 * The name of the scene.
 * @name $.oScene#version
 * @readonly
 * @type {string}
 */
Object.defineProperty($.oScene.prototype, 'version', {
  get : function(){
    return scene.currentVersionName();
  }
});


/**
 * The sceneName file of the scene.
 * @Deprecated
 * @readonly
 * @name $.oScene#sceneName
 * @type {string}
 */
Object.defineProperty($.oScene.prototype, 'sceneName', {
  get : function(){
    return this.name;
  }
});



/**
 * The startframe to the playback of the scene.
 * @name $.oScene#startPreview
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'startPreview', {
  get : function(){
    return scene.getStartFrame();
  },
  set : function(val){
    scene.setStartFrame( val );
  }
});

/**
 * The stopFrame to the playback of the scene.
 * @name $.oScene#stopPreview
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'stopPreview', {
  get : function(){
    return scene.getStopFrame()+1;
  },
  set : function(val){
    scene.setStopFrame( val-1 );
  }
});

/**
 * The frame rate of the scene.
 * @name $.oScene#framerate
 * @type {float}
 */
Object.defineProperty($.oScene.prototype, 'framerate', {
  get : function(){
    return scene.getFrameRate();
  },
  set : function(val){
    return scene.setFrameRate( val );
  }
});


/**
 * The Field unit aspect ratio as a coefficient (width/height).
 * @name $.oScene#unitsAspectRatio
 * @type {double}
 */
 Object.defineProperty($.oScene.prototype, 'unitsAspectRatio', {
  get : function(){
    return this.aspectRatioX/this.aspectRatioY;
  }
});


/**
 * The horizontal aspect ratio of Field units.
 * @name $.oScene#aspectRatioX
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'aspectRatioX', {
  get : function(){
    return scene.unitsAspectRatioX();
  },
  set : function(val){
    scene.setUnitsAspectRatio( val, this.aspectRatioY );
  }
});

/**
 * The vertical aspect ratio of Field units.
 * @name $.oScene#aspectRatioY
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'aspectRatioY', {
    get : function(){
        return scene.unitsAspectRatioY();
    },
    set : function(val){
        scene.setUnitsAspectRatio( this.aspectRatioY, val );
    }
});

/**
 * The horizontal Field unit count.
 * @name $.oScene#unitsX
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'unitsX', {
    get : function(){
        return scene.numberOfUnitsX();
    },
    set : function(val){
        scene.setNumberOfUnits( val, this.unitsY, this.unitsZ );
    }
});

/**
 * The vertical Field unit count.
 * @name $.oScene#unitsY
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'unitsY', {
    get : function(){
        return scene.numberOfUnitsY();
    },
    set : function(val){
        scene.setNumberOfUnits( this.unitsX, val, this.unitsZ );
    }
});

/**
 * The depth Field unit count.
 * @name $.oScene#unitsZ
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'unitsZ', {
    get : function(){
        return scene.numberOfUnitsZ();
    },
    set : function(val){
        scene.setNumberOfUnits( this.unitsX, this.unitsY, val );
    }
});


/**
 * The center coordinates of the scene.
 * @name $.oScene#center
 * @type {$.oPoint}
 */
Object.defineProperty($.oScene.prototype, 'center', {
    get : function(){
        return new this.$.oPoint( scene.coordAtCenterX(), scene.coordAtCenterY(), 0.0 );
    },
    set : function( val ){
        scene.setCoordAtCenter( val.x, val.y );
    }
});


/**
 * The amount of drawing units represented by 1 field on the horizontal axis.
 * @name $.oScene#fieldVectorResolutionX
 * @type {double}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'fieldVectorResolutionX', {
  get : function(){
    var yUnit = this.fieldVectorResolutionY;
    var unit = yUnit * this.unitsAspectRatio;
    return unit
  }
});


/**
 * The amount of drawing units represented by 1 field on the vertical axis.
 * @name $.oScene#fieldVectorResolutionY
 * @type {double}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'fieldVectorResolutionY', {
  get : function(){
    var verticalResolution = 1875 // the amount of drawing units for the max vertical field value
    var unit = verticalResolution/12; // the vertical number of units on drawings is always 12 regardless of $.scn.unitsY
    return unit
  }
});


/**
 * The horizontal resolution in pixels (for rendering).
 * @name $.oScene#resolutionX
 * @readonly
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'resolutionX', {
    get : function(){
        return scene.currentResolutionX();
    }
});

/**
 * The vertical resolution in pixels (for rendering).
 * @name $.oScene#resolutionY
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'resolutionY', {
    get : function(){
        return scene.currentResolutionY();
    }
});

/**
 * The default horizontal resolution in pixels.
 * @name $.oScene#defaultResolutionX
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'defaultResolutionX', {
    get : function(){
        return scene.defaultResolutionX();
    },
    set : function(val){
        scene.setDefaultResolution( val, this.defaultResolutionY, this.fov );
    }
});

/**
 * The default vertical resolution in pixels.
 * @name $.oScene#defaultResolutionY
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'defaultResolutionY', {
    get : function(){
        return scene.defaultResolutionY();
    },
    set : function(val){
        scene.setDefaultResolution( this.defaultResolutionX, val, this.fov );
    }
});

/**
 * The field of view of the scene.
 * @name $.oScene#fov
 * @type {double}
 */
Object.defineProperty($.oScene.prototype, 'fov', {
    get : function(){
        return scene.defaultResolutionFOV();
    },
    set : function(val){
        scene.setDefaultResolution( this.defaultResolutionX, this.defaultResolutionY, val );
    }
});


/**
 * The default Display of the scene.
 * @name $.oScene#defaultDisplay
 * @type {oNode}
 */
Object.defineProperty($.oScene.prototype, 'defaultDisplay', {
  get : function(){
    return this.getNodeByPath(scene.getDefaultDisplay());
  },

  set : function(newDisplay){
    node.setAsGlobalDisplay(newDisplay.path);
  }
});


/**
 * Whether the scene contains unsaved changes.
 * @name $.oScene#unsaved
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oScene.prototype, 'unsaved', {
    get : function(){
        return scene.isDirty();
    }
});


/**
 * The root group of the scene.
 * @name $.oScene#root
 * @type {$.oGroupNode}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'root', {
    get : function(){
        var _topNode = this.getNodeByPath( "Top" );
        return _topNode
    }
});


/**
 * Contains the list of all the nodes present in the scene.
 * @name $.oScene#nodes
 * @readonly
 * @type {$.oNode[]}
 */
Object.defineProperty($.oScene.prototype, 'nodes', {
    get : function(){
        var _topNode = this.root;
        return _topNode.subNodes( true );
    }
});


/**
 * Contains the list of columns present in the scene.
 * @name $.oScene#columns
 * @readonly
 * @type {$.oColumn[]}
 * @todo add attribute finding to get complete column objects
 */
Object.defineProperty($.oScene.prototype, 'columns', {
    get : function(){
        var _columns = [];
        for (var i=0; i<column.numberOf(); i++){
            _columns.push( this.$column(column.getName(i)) );
        }
        return _columns;
    }
});


/**
 * Contains the list of scene palettes present in the scene.
 * @name $.oScene#palettes
 * @readonly
 * @type {$.oPalette[]}
 */
Object.defineProperty($.oScene.prototype, 'palettes', {
  get : function(){
    var _paletteList = PaletteObjectManager.getScenePaletteList();

    var _palettes = [];
    for (var i=0; i<_paletteList.numPalettes; i++){
        _palettes.push( new this.$.oPalette( _paletteList.getPaletteByIndex(i), _paletteList ) );
    }
    return _palettes;
  }
});


/**
 * Contains the list of elements present in the scene. Element ids can appear more than once if they are used by more than one Drawing column
 * @name $.oScene#elements
 * @readonly
 * @type {$.oElement[]}
 */
Object.defineProperty($.oScene.prototype, 'elements', {
  get : function(){
    var _elements = [];
    var _columns = this.columns;
    var _ids = [];
    for (var i in _columns){
      if (_columns.type != "DRAWING") continue;
      var _element = _columns[i].element
      _elements.push(_element);
      if (_ids.indexOf(_element.id) == -1) _ids.push (_element.id);
    }

    // adding the elements not linked to columns
    var _elementNum = element.numberOf();
    for (var i = 0; i<_elementNum; i++){
      var _id = element.id(i);
      if (_ids.indexOf(_id) == -1) {
        _elements.push(new this.$.oElement(_id));
        _ids.push (_id)
      }
    }
    return _elements;
  }
});



/**
 * The length of the scene.
 * @name $.oScene#length
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'length', {
    get : function(){
        return frame.numberOf()
    },

    set : function (newLength){
        var _length = frame.numberOf();
        var _toAdd = newLength-_length;
        if (_toAdd>0){
            frame.insert(_length-1, _toAdd)
        }else{
            frame.remove(_length-1, _toAdd)
        }
    }
});


/**
 * The current frame of the scene.
 * @name $.oScene#currentFrame
 * @type {int}
 */
Object.defineProperty($.oScene.prototype, 'currentFrame', {
    get : function(){
        return frame.current();
    },

    set : function( frm ){
        return frame.setCurrent( frm );
    }
});


/**
 * Retrieve and change the selection of nodes.
 * @name $.oScene#selectedNodes
 * @type {$.oNode[]}
 */
Object.defineProperty($.oScene.prototype, 'selectedNodes', {
  get : function(){
    return this.getSelectedNodes();
  },

  set : function(nodesToSelect){
    selection.clearSelection ();
    for (var i in nodesToSelect){
      selection.addNodeToSelection(nodesToSelect[i].path);
    };
  }
});


/**
 * Retrieve and change the selected frames. This is an array with two values, one for the start and one for the end of the selection (not included).
 * @name $.oScene#selectedFrames
 * @type {int[]}
 */
Object.defineProperty($.oScene.prototype, 'selectedFrames', {
  get : function(){
    if (selection.isSelectionRange()){
      var _selectedFrames = [selection.startFrame(), selection.startFrame()+selection.numberOfFrames()];
    }else{
      var _selectedFrames = [this.currentFrame, this.currentFrame+1];
    }

    return _selectedFrames;
  },

  set : function(frameRange){
    selection.setSelectionFrameRange(frameRange[0], frameRange[1]-frameRange[0]);
  }
});


/**
 * Retrieve and set the selected palette from the scene palette list.
 * @name $.oScene#selectedPalette
 * @type {$.oPalette}
 */
Object.defineProperty($.oScene.prototype, "selectedPalette", {
  get: function(){
    var _paletteList = PaletteObjectManager.getScenePaletteList()
    var _id = PaletteManager.getCurrentPaletteId()
    if (_id == "") return null;
    var _palette = new this.$.oPalette(_paletteList.getPaletteById(_id), _paletteList);
    return _palette;
  },

  set: function(newSelection){
    var _id = newSelection.id;
    PaletteManager.setCurrentPaletteById(_id);
  }
})


/**
 * The selected strokes on the currently active Drawing
 * @name $.oScene#selectedShapes
 * @type {$.oStroke[]}
 */
Object.defineProperty($.oScene.prototype, "selectedShapes", {
  get : function(){
    var _currentDrawing = this.activeDrawing;
    var _shapes = _currentDrawing.selectedShapes;

    return _shapes;
  }
})


/**
 * The selected strokes on the currently active Drawing
 * @name $.oScene#selectedStrokes
 * @type {$.oStroke[]}
 */
Object.defineProperty($.oScene.prototype, "selectedStrokes", {
  get : function(){
    var _currentDrawing = this.activeDrawing;
    var _strokes = _currentDrawing.selectedStrokes;

    return _strokes;
  }
})


/**
 * The selected strokes on the currently active Drawing
 * @name $.oScene#selectedContours
 * @type {$.oContour[]}
 */
Object.defineProperty($.oScene.prototype, "selectedContours", {
  get : function(){
    var _currentDrawing = this.activeDrawing;
    var _strokes = _currentDrawing.selectedContours;

    return _strokes;
  }
})


/**
 * The currently active drawing in the harmony UI.
 * @name $.oScene#activeDrawing
 * @type {$.oDrawing}
 */
Object.defineProperty($.oScene.prototype, 'activeDrawing', {
  get : function(){
    var _curDrawing = Tools.getToolSettings().currentDrawing;
    if (!_curDrawing) return null;

    var _element = this.selectedNodes[0].element;
    var _drawings = _element.drawings;
    for (var i in _drawings){
      if (_drawings[i].id == _curDrawing.drawingId) return _drawings[i];
    }

    return null
  },

  set : function( newCurrentDrawing ){
    newCurrentDrawing.setAsActiveDrawing();
  }
});


/**
 * The current timeline using the default Display.
 * @name $.oScene#currentTimeline
 * @type {$.oTimeline}
 * @readonly
 */
Object.defineProperty($.oScene.prototype, 'currentTimeline', {
  get : function(){
    if (!this.hasOwnProperty("_timeline")){
      this._timeline = this.getTimeline();
    }
    return this._timeline;
  }
});




//-------------------------------------------------------------------------------------
//--- $.oScene Objects Methods
//-------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------


/**
 * Gets a node by the path.
 * @param   {string}   fullPath         The path of the node in question.
 *
 * @return {$.oNode}                    The node found given the query.
 */
$.oScene.prototype.getNodeByPath = function(fullPath){
    var _type = node.type(fullPath);
    if (_type == "") return null;

    var _node;
    switch(_type){
      case "READ" :
        _node = new this.$.oDrawingNode( fullPath, this );
        break;
      case "PEG" :
        _node = new this.$.oPegNode( fullPath, this );
        break;
      case "COLOR_OVERRIDE_TVG" :
        _node = new this.$.oColorOverrideNode( fullPath, this );
        break;
      case "TransformationSwitch" :
        _node = new this.$.oTransformSwitchNode( fullPath, this );
        break;
      case "GROUP" :
        _node = new this.$.oGroupNode( fullPath, this );
        break;
      default:
        _node = new this.$.oNode( fullPath, this );
    }

    return _node;
}

 /**
 * Returns the nodes of a certain type in the entire scene.
 * @param   {string}      typeName       The name of the node.
 *
 * @return  {$.oNode[]}     The nodes found.
 */
$.oScene.prototype.getNodesByType = function(typeName){
  return this.root.getNodesByType(typeName, true);
}

/**
 * Gets a column by the name.
 * @param  {string}             uniqueName               The unique name of the column as a string.
 * @param  {$.oAttribute}       oAttributeObject         The oAttributeObject owning the column.
 * @todo   cache and find attribute if it is missing
 *
 * @return {$.oColumn}                    The column found given the query.
 */
$.oScene.prototype.getColumnByName = function( uniqueName, oAttributeObject ){
    var _type = column.type(uniqueName);

    switch (_type) {
        case "" :
            return null;
        case "DRAWING" :
            return new this.$.oDrawingColumn(uniqueName, oAttributeObject);
        default :
            return new this.$.oColumn(uniqueName, oAttributeObject);
    }
}


/**
 * Gets an element by Id.
 * @param  {string}        id                         The unique name of the column as a string.
 * @param  {$.oColumn}     [oColumnObject]            The oColumn object linked to the element in case of duplicate.
 *
 * @return {$.oElement}                               The element found given the query. In case of an element linked to several column, only the first one will be returned, unless the column is specified
 */
$.oScene.prototype.getElementById = function( id, oColumnObject ){
  if (element.getNameById(id) == "") return null;

  var _sceneElements = this.elements.filter(function(x){return x.id == id});
  if (typeof oColumnObject !== 'undefined') _sceneElements = _sceneElements.filter(function(x){return x.column.uniqueName == oColumnObject.uniqueName});

  if (_sceneElements.length > 0) return _sceneElements[0];
  return null;
}


/**
 * Gets the selected Nodes.
 * @param  {bool}   recurse            Whether to recurse into groups.
 *
 * @return {$.oNode[]}                 The selected nodes.
 */
$.oScene.prototype.getSelectedNodes = function( recurse, sortResult ){
    if (typeof recurse === 'undefined') var recurse = false;
    if (typeof sort_result === 'undefined') var sortResult = false;     //Avoid sorting, save time, if unnecessary and used internally.

    var _selection = selection.selectedNodes();

    var _selectedNodes = [];
    for (var i = 0; i<_selection.length; i++){

        var _oNodeObject = this.$node(_selection[i])

        _selectedNodes.push(_oNodeObject)
        if (recurse && node.isGroup(_selection[i])){
            _selectedNodes = _selectedNodes.concat(_oNodeObject.subNodes(recurse))
        }
    }

    // sorting by timeline index
    if( sortResult ){
      var _timeline = this.getTimeline();
      _selectedNodes = _selectedNodes.sort(function(a, b){return a.timelineIndex(_timeline)-b.timelineIndex(_timeline)})
    }

    return _selectedNodes;
}


/**
 * Searches for a node based on the query.
 * @param   {string}   query            The query for finding the node[s].
 *
 * @return {$.oNode[]}                 The node[s] found given the query.
 */
$.oScene.prototype.nodeSearch = function( query, sort_result ){
  if (typeof sort_result    === 'undefined') var sort_result = true;     //Avoid sorting, save time, if unnecessary and used internally.

  //-----------------------------------
  //Breakdown with regexp as needed, find the query details.
  //-----------------------------------

  // NAME, NODE, WILDCARDS, ATTRIBUTE VALUE MATCHING, SELECTION/OPTIONS, COLOURS

  //----------------------------------------------
  // -- PATH/WILDCARD#TYPE[ATTRIBUTE:VALUE,ATTRIBUTE:VALUE][OPTION:VALUE,OPTION:VALUE]
  // ^(.*?)(\#.*?)?(\[.*\])?(\(.*\))?$

  //ALLOW USAGE OF AN INPUT LIST, LIST OF NAMES, OR OBJECTS,

  //--------------------------------------------------
  //-- EASY RETURNS FOR FAST OVERLOADS.

  //* -- OVERRIDE FOR ALL NODES

  if( query == "*" ){
    return this.nodes;

  //(SELECTED) SELECTED -- OVERRIDE FOR ALL SELECTED NODES
  }else if( query == "(SELECTED)" || query == "SELECTED" ){

    return this.getSelectedNodes( true, sort_result );

  //(NOT SELECTED) !SELECTED NOT SELECTED -- OVERRIDE FOR ALL SELECTED NODES

  }else if( query == "(NOT SELECTED)" ||
            query == "NOT SELECTED"   ||
            query == "(! SELECTED)"   ||
            query == "! SELECTED"     ||
            query == "(UNSELECTED)"   ||
            query == "UNSELECTED"
          ){

    var nodes_returned = [];

    var sel_list = {};
    for( var p=0;p<selection.numberOfNodesSelected();p++ ){
      sel_list[ selection.selectedNode(p) ] = true;
    }

    var all_nodes = this.nodes;
    for( var x=0;x<all_nodes.length;x++ ){
      if( !sel_list[ all_nodes[x].path ] ){
        var node_ret = this.getNodeByPath( all_nodes[x].path );
        if( node_ret && node_ret.exists ){
          nodes_returned.push( node_ret );
        }
      }
    }

    if( sort_result ){
      var _timeline = this.getTimeline();
      nodes_returned = nodes_returned.sort(function(a, b){return a.timelineIndex(_timeline)-b.timelineIndex(_timeline)})
    }
    return nodes_returned;
  }


  //FULL QUERIES.
  var regexp = /^(.*?)(\#.*?)?(\[.*\])?(\(.*\))?$/;
  var query_match = query.match( regexp );

  this.$.debug( "QUERYING: " + query, this.$.DEBUG_LEVEL.LOG );
  this.$.debug( "QUERYING: " + query_match.length, this.$.DEBUG_LEVEL.LOG );

  var nodes_returned = [];

  if( query_match && query_match.length > 1 && query_match[1] && query_match[1].length > 0 ){
    //CONSIDER A LIST, COMMA SEPARATION, AND ESCAPED COMMAS.
    var query_list = [];
    var last_str   = '';
    var split_list = query_match[1].split( "," );

    for( var n=0; n<split_list.length; n++ ){
      var split_val = split_list[n];
      if( split_val.slice( split_val.length-1, split_val.length ) == "\\" ){
        last_str += split_val + ",";

      }else{
        query_list.push( last_str + split_val );
        last_str = "";
      }
    }

    if( last_str.length>0 ){
      query_list.push( last_str );
    }

    this.$.debug( "GETTING NODE LIST FROM QUERY", this.$.DEBUG_LEVEL.LOG );
    //NOW DEAL WITH WILDCARDS

    var added_nodes = {}; //Add the full path to a list when adding/querying existing. Prevent duplicate attempts.
    var all_nodes = false;
    for( var x=0; x<query_list.length; x++ ){
      if( (query_list[x].indexOf("*")>=0) || (query_list[x].indexOf("?")>=0) ){
        //THERE ARE WILDCARDS.
        this.$.debug( "WILDCARD NODE QUERY: "+query_list[x], this.$.DEBUG_LEVEL.LOG );
        //Make a wildcard search for the nodes.

        if( all_nodes === false ){
          all_nodes = this.nodes;
        }

        //Run the Wildcard regexp against the available nodes.
        var regexp = query_list[x];
            regexp = regexp.split( "?" ).join( "." );
            regexp = regexp.split( "*" ).join( ".*?" );
            regexp = '^'+regexp+'$';

        this.$.debug( "WILDCARD QUERY REGEXP: "+regexp, this.$.DEBUG_LEVEL.LOG );

        var regexp_filter = RegExp( regexp, 'gi' );
        for( var n=0;n<all_nodes.length;n++ ){
          if( !added_nodes[all_nodes[n].path] ){
            this.$.debug( "WILDCARD NODE TEST: "+all_nodes[n].path, this.$.DEBUG_LEVEL.LOG );
            if( regexp_filter.test( all_nodes[n].path ) ){
              this.$.debug( "WILDCARD NODE TESTED SUCCESS: "+all_nodes[n].path, this.$.DEBUG_LEVEL.LOG );

              var node_ret = all_nodes[n]; //this.getNodeByPath( all_nodes[n].path ); //new this.$.oNode( this.$, all_nodes[n].path );
              if( node_ret && node_ret.exists ){
                this.$.debug( "WILDCARD NODE MATCH: "+all_nodes[n].path+"\n", this.$.DEBUG_LEVEL.LOG );
                nodes_returned.push( node_ret );
              }
              added_nodes[ all_nodes[n].path ] = true;
            }
          }
        }

      }else if( query_list[x].length >=3 && query_list[x]=="re:" ){
        //THERE ARE WILDCARDS.
        this.$.debug( "REGEXP NODE QUERY: "+query_list[x], this.$.DEBUG_LEVEL.LOG );
        //Make a wildcard search for the nodes.

        if( all_nodes === false ){
          all_nodes = this.nodes;
        }

        //Run the Wildcard regexp against the available nodes.
        var regexp = query_list[x];
        this.$.debug( "REGEXP QUERY REGEXP: "+regexp, this.$.DEBUG_LEVEL.LOG );

        var regexp_filter = RegExp( regexp, 'gi' );
        for( var n=0;n<all_nodes.length;n++ ){
          if( !added_nodes[all_nodes[n].path] ){
            this.$.debug( "REGEXP NODE TEST: "+all_nodes[n].path, this.$.DEBUG_LEVEL.LOG );
            if( regexp_filter.test( all_nodes[n].path ) ){
              this.$.debug( "REGEXP NODE TESTED SUCCESS: "+all_nodes[n].path, this.$.DEBUG_LEVEL.LOG );

              var node_ret = all_nodes[n]; //new this.$.oNode( this.$, all_nodes[n].path );
              if( node_ret && node_ret.exists ){
                this.$.debug( "REGEXP NODE MATCH: "+all_nodes[n].path+"\n", this.$.DEBUG_LEVEL.LOG );
                nodes_returned.push( node_ret );
              }
              added_nodes[ all_nodes[n].path ] = true;
            }
          }
        }
      }else{
        //ITS JUST THE EXACT NODE.
        this.$.debug( "EXACT NODE QUERY: "+query_list[x], this.$.DEBUG_LEVEL.LOG );

        var node_ret = this.getNodeByPath( query_list[x] ); //new this.$.oNode( this.$, query_list[x] );
        if( !added_nodes[ query_list[x] ] ){
          if( node_ret && node_ret.exists ){
            this.$.debug( "EXACT NODE MATCH: "+query_list[x]+"\n", this.$.DEBUG_LEVEL.LOG );
            nodes_returned.push( node_ret );
          }
          added_nodes[ query_list[x] ] = true;
        }
      }
    }
  }else{
    nodes_returned = this.nodes;
  }

  this.$.debug( "FILTER CODE", this.$.DEBUG_LEVEL.LOG );

  //-----------------------------------------------------
  //IT HAS SOME SORT OF FILTER ASSOCIATED WITH THE QUERY.
  if( query_match.length > 2 ){
    var filtered_nodes = nodes_returned;
    for( var n=2;n<query_match.length;n++ ){
      //RUN THE FITERS.

      if( !query_match[n] ){
        continue;
      }

      if( query_match[n].slice(0, 1) == "#" ){         //TYPE
        this.$.debug( "TYPE FILTER INIT: " + query_match[n], this.$.DEBUG_LEVEL.LOG );

        var res_nodes = [];
        var match_val = query_match[n].slice(1,query_match[n].length).toUpperCase();
        for( var x=0;x<filtered_nodes.length;x++ ){
          if( filtered_nodes[x].type == match_val ){
            res_nodes.push( filtered_nodes[x] );
          }
        }

        filtered_nodes = res_nodes;
      }else if( query_match[n].slice(0, 1) == "[" ){   //ATTRIBUTES
        var split_attrs = query_match[n].toUpperCase().slice( 1, query_match[n].length-1 ).split(",");
        for( var t=0;t<split_attrs.length;t++ ){
          var res_nodes = [];

          var split_attrs = split_attrs[t].split( ":" );
          if( split_attrs.length==1 ){
            //It simply just must have this attribute.
            //res_nodes.push( filtered_nodes[0] );

          }else{
            //You must compare values of the attribute -- currently only supports string, but should also use float/int comparisons and logic.


          }

          //filtered_nodes = res_nodes;
        }
      }else if( query_match[n].slice(0, 1) == "(" ){   //OPTIONS
        //SELECTED, ECT.

        var split_options = query_match[n].toUpperCase().slice( 1, query_match[n].length-1 ).split(",");

        for( var t=0;t<split_options.length;t++ ){
          var res_nodes = [];

          //THE OPTION FOR SELECTED NODES ONLY, COMPARE IT AGAINST THE LIST.
          if( split_options[t] == "SELECTED" ){
            this.$.debug( "TYPE FILTER SELECTION ONLY", this.$.DEBUG_LEVEL.LOG );

            //GET THE SELECTION LIST.
            var sel_list = {};
            for( var p=0;p<selection.numberOfNodesSelected();p++ ){
              sel_list[ selection.selectedNode(p) ] = true;
              this.$.debug( selection.selectedNode(p), this.$.DEBUG_LEVEL.LOG );
            }

            for( var x=0;x<filtered_nodes.length;x++ ){
              if( sel_list[ filtered_nodes[x].path ] ){
                res_nodes.push( filtered_nodes[x] );
              }
            }
          }

          //--- NOTSELECTED DESELECTED !SELECTED  NOT SELECTED
          //THE OPTION FOR SELECTED NODES ONLY, COMPARE IT AGAINST THE LIST.
          else if( split_options[t] == "NOT SELECTED" || split_options[t] == "NOTSELECTED" || split_options[t] == "DESELECTED" || split_options[t] == "!SELECTED" ){
            this.$.debug( "TYPE FILTER SELECTION ONLY", this.$.DEBUG_LEVEL.LOG );

            //GET THE SELECTION LIST.
            var sel_list = {};
            for( var p=0;p<selection.numberOfNodesSelected();p++ ){
              sel_list[ selection.selectedNode(p) ] = true;
            }

            for( var x=0;x<filtered_nodes.length;x++ ){
              if( !sel_list[ filtered_nodes[x].path ] ){
                res_nodes.push( filtered_nodes[x] );
              }
            }
          }

          filtered_nodes = res_nodes;
        }
      }
    }

    nodes_returned = filtered_nodes;
  }

  if( sort_result ){
    var _timeline = this.getTimeline();
    nodes_returned = nodes_returned.sort(function(a, b){return a.timelineIndex(_timeline)-b.timelineIndex(_timeline)})
  }
  return nodes_returned;
}


/**
 * Adds a node to the scene.
 * @Deprecated         use AddNode directly in the destination group by calling it on the oGroupNode
 * @param   {string}   type            The type-name of the node to add.
 * @param   {string}   name            The name of the newly created node.
 * @param   {string}   group           The groupname to add the node.
 * @param   {$.oPoint} nodePosition    The position for the node to be placed in the network.
 *
 * @return {$.oNode}   The created node
 */
$.oScene.prototype.addNode = function( type, name, group, nodePosition ){
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.addNode is deprecated. Use oGroupNode.addNode instead")
    var _node = _group.addNode(type, name, nodePosition)
    return _node;
  }else{
    if (group == undefined) throw new Error ("Group path not specified for adding node. Use oGroupNode.addNode() instead.")
    throw new Error (group+" is an invalid group to add the Node to.")
  }
}


/**
 * Adds a column to the scene.
 * @param   {string}   type                           The type of the column.
 * @param   {string}   name                           The name of the column.
 * @param   {$.oElement}   oElementObject             For Drawing column, the element that will be represented by the column.
 *
 * @return {$.oColumn}  The created column
 */

$.oScene.prototype.addColumn = function( type, name, oElementObject ){
    // Defaults for optional parameters
    if (!type) throw new Error ("Must provide a type when creating a new column.");

    if (typeof name === 'undefined'){
      if( column.generateAnonymousName ){
        var name = column.generateAnonymousName();
      }else{
        var name = "ATV"+(new Date()).getTime();
      }
    }

    var _increment = 1;
    var _columnName = name;

    // increment name if a column with that name already exists
    while (column.type(_columnName) != ""){
        _columnName = name+"_"+_increment;
        _increment++;
    }

    this.$.debug( "CREATING THE COLUMN: " + name, this.$.DEBUG_LEVEL.LOG );
    column.add(_columnName, type);

    if (column.type(_columnName)!= type) throw new Error ("Couldn't create column with name '"+name+"' and type "+type)

    var _column = new this.$.oColumn( _columnName );

    if (type == "DRAWING" && typeof oElementObject !== 'undefined'){
        oElementObject.column = this;// TODO: fix: this doesn't seem to actually work for some reason?
        this.$.debug( "set element "+oElementObject.id+" to column "+_column.uniqueName, this.$.DEBUG_LEVEL.LOG );
        column.setElementIdOfDrawing(_column.uniqueName, oElementObject.id);
    }

    return _column;
}


/**
 * Adds an element to the scene.
 * @param   {string}     name                    The name of the element
 * @param   {string}     [imageFormat="TVG"]     The image format in capital letters (ex: "TVG", "PNG"...)
 * @param   {int}        [fieldGuide=12]         The field guide .
 * @param   {string}     [scanType="COLOR"]      can have the values "COLOR", "GRAY_SCALE" or "BW".
 *
 * @return {$.oElement}  The created element
 */
$.oScene.prototype.addElement = function(name, imageFormat, fieldGuide, scanType){
    // Defaults for optional parameters
    if (typeof scanType === 'undefined') var scanType = "COLOR";
    if (typeof fieldGuide === 'undefined') var fieldGuide = 12;
    if (typeof imageFormat === 'undefined') var imageFormat = "TVG";

    var _fileFormat = (imageFormat == "TVG")?"SCAN":imageFormat;
    var _vectorFormat = (imageFormat == "TVG")?imageFormat:"None";

    // sanitize input to graciously handle forbidden characters
    name = name.replace(/[^A-Za-z\d_\-]/g, "_").replace(/ /g, "_");

    var _id = element.add(name, scanType, fieldGuide, _fileFormat, _vectorFormat);
    if (_id <0) throw new Error("Couldn't create an element with settings {name:'"+name+"', imageFormat:"+ imageFormat+", fieldGuide:"+fieldGuide+", scanType:"+scanType+"}")

    var _element = new this.$.oElement( _id )

    return _element;
}


/**
 * Adds a drawing layer to the scene, with a drawing column and element linked. Possible to specify the column and element to use.
 * @Deprecated Use oGroupNode.addDrawingNode instead
 * @param   {string}     name            The name of the newly created node.
 * @param   {string}     group           The group in which the node is added.
 * @param   {$.oPoint}   nodePosition    The position for the node to be placed in the network.
 * @param   {$.object}   element         The element to attach to the column.
 * @param   {object}     drawingColumn   The column to attach to the drawing module.
 * @param   {object}     options         The creation options, nothing available at this point.

 * @return {$.oDrawingNode}     The created node.
 */
$.oScene.prototype.addDrawingNode = function( name, group, nodePosition, oElementObject, drawingColumn, options ){
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.addDrawingNode is deprecated. Use oGroupNode.addDrawingNode instead")
    var _node = _group.addNode(name, nodePosition, oElementObject, drawingColumn, options )
    return _node;
  }else{
    throw new Error (group+" is an invalid group to add the Drawing Node to.")
  }
}


/**
 * Adds a group to the scene.
 * @Deprecated Use oGroupNode.addGroup instead
 * @param   {string}     name                   The name of the newly created group.
 * @param   {string}     includeNodes           The nodes to add to the group.
 * @param   {$.oPoint}   addComposite           Whether to add a composite.
 * @param   {bool}       addPeg                 Whether to add a peg.
 * @param   {string}     group                  The group in which the node is added.
 * @param   {$.oPoint}   nodePosition           The position for the node to be placed in the network.

 * @return {$.oGroupNode}   The created node.
 */
$.oScene.prototype.addGroup = function( name, includeNodes, addComposite, addPeg, group, nodePosition ){
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.addGroup is deprecated. Use oGroupNode.addGroup instead")
    var _node = _group.addGroup(name, includeNodes, addComposite, addPeg, nodePosition )
    return _node;
  }else{
    throw new Error (group+" is an invalid group to add the Group Node to.")
  }
}



/**
 * Grabs the timeline object for a specific display.
 * @param   {string}        [display]                The display node to build the timeline for.
 * @return {$.oTimeline}    The timelne object given the display.
 */
$.oScene.prototype.getTimeline = function(display){
    return new this.$.oTimeline( display, this );
}


/**
 * Gets a scene palette by the name.
 * @param   {string}   name            The palette name to query and find.
 *
 * @return  {$.oPalette}                 The oPalette found given the query.
 */
$.oScene.prototype.getPaletteByName = function(name){
  var _palettes = this.palettes;
  for (var i in _palettes){
    if (_palettes[i].name == name) return _palettes[i];
  }
  return null;
}

/**
 * Gets a scene palette by the path of the plt file.
 * @param   {string}   path              The palette path to find.
 * @return  {$.oPalette}                 The oPalette or null if not found.
 */
$.oScene.prototype.getPaletteByPath = function(path){
  var _palettes = this.palettes;
  for (var i in _palettes){
    if (_palettes[i].path.path == path) return _palettes[i];
  }
  return null;
}


/**
 * Grabs the selected palette.
 * @return {$.oPalette}   oPalette with provided name.
 * @deprecated
 */
$.oScene.prototype.getSelectedPalette = function(){
    var _paletteList = PaletteManager.getScenePaletteList();
    var _id = PaletteManager.getCurrentPaletteId()
    var _palette = new this.$.oPalette(_paletteList.getPaletteById(_id), _paletteList);
    return _palette;
}


/**
 * Add a palette object to the scene palette list and into the specified location.
 * @param   {string}         name                          The name for the palette.
 * @param   {string}         index                         Index at which to insert the palette.
 * @param   {string}         paletteStorage                Storage type: environment, job, scene, element, external.
 * @param   {$.oElement}     storeInElement                The element to store the palette in. If paletteStorage is set to "external", provide a destination folder for the palette here.
 *
 * @return {$.oPalette}   newly created oPalette with provided name.
 */
$.oScene.prototype.addPalette = function(name, insertAtIndex, paletteStorage, storeInElement){
  if (typeof paletteStorage === 'undefined') var paletteStorage = "scene";
  if (typeof insertAtIndex === 'undefined') var insertAtIndex = 0;

  var _list = PaletteObjectManager.getScenePaletteList();

  if (typeof storeInElement === 'undefined'){
    if (paletteStorage == "external") throw new Error("Element parameter should point to storage path if palette destination is External")
    if (paletteStorage == "element") throw new Error("Element parameter cannot be omitted if palette destination is Element")
    var storeInElement = 1;
  }

  var _destination = $.oPalette.location[paletteStorage]
  if (paletteStorage == "element") var storeInElement = storeInElement.id;

  this.$.log(paletteStorage+" "+_destination)

  if (paletteStorage == "external") var _palette = new this.$.oPalette(_list.createPalette(storeInElement+"/"+name, insertAtIndex), _list);

  // can fail if database lock wasn't released
  var _palette = new this.$.oPalette(_list.createPaletteAtLocation(_destination, storeInElement, name, insertAtIndex), _list);
  log("created palette : "+_palette.path)
  return _palette;
}



/**
 * Imports a palette to the scene palette list and into the specified storage location.
 * @param   {string}      path               The palette file to import.
 * @param   {string}      name               The name for the palette.
 * @param   {string}      index              Index at which to insert the palette.
 * @param   {string}      paletteStorage     Storage type: environment, job, scene, element, external.
 * @param   {$.oElement}  storeInElement     The element to store the palette in. If paletteStorage is set to "external", provide a destination folder for the palette here.
 *
 * @return {$.oPalette}   oPalette with provided name.
 */
$.oScene.prototype.importPalette = function(filename, name, index, paletteStorage, storeInElement){
  var _paletteFile = new this.$.oFile(filename);
  if (!_paletteFile.exists){
    throw new Error ("Cannot import palette from file "+filename+" because it doesn't exist", this.$.DEBUG_LEVEL.ERROR);
  }

  if (typeof name === 'undefined') var name = _paletteFile.name;

  var _list = PaletteObjectManager.getScenePaletteList();
  if  (typeof index === 'undefined') var index = _list.numPalettes;
  if  (typeof paletteStorage === 'undefined') var paletteStorage = "scene";

  if (typeof storeInElement === 'undefined'){
    if (paletteStorage == "external") throw new Error("Element parameter should point to storage path if palette destination is External")
    if (paletteStorage == "element") throw new Error("Element parameter cannot be omitted if palette destination is Element")
    var storeInElement = 1;
  }

  var _location = this.$.oPalette.location;
  switch (paletteStorage){
    case 'environment' :
      var paletteFolder = fileMapper.toNativePath(PaletteObjectManager.Locator.folderForLocation(_location.environment,1));
      break;

    case 'job' :
      var paletteFolder = fileMapper.toNativePath(PaletteObjectManager.Locator.folderForLocation(_location.job,1))
      break;

    case 'scene' :
      var paletteFolder = fileMapper.toNativePath(PaletteObjectManager.Locator.folderForLocation(_location.scene,1))
      break;

    case 'element' :
      var paletteFolder = fileMapper.toNativePath(PaletteObjectManager.Locator.folderForLocation(_location.element, storeInElement.id))
      break;
  }

  var paletteFolder = new this.$.oFolder(paletteFolder);

  if (!paletteFolder.exists){
    try{
      paletteFolder.create();
    }catch(err){
      throw new Error ("Couldn't create missing palette folder " + paletteFolder +": " + err);
    }
  }

  if (_paletteFile.folder.path != paletteFolder.path) {
    _paletteFile = _paletteFile.copy(paletteFolder.path, name, true);
  }

  var _palette = _list.insertPalette(_paletteFile.toonboomPath.replace(".plt", ""), index);

  _newPalette = new this.$.oPalette(_palette, _list);

  return _newPalette;
}


/**
 * Creates a single palette containing all the individual colors used by an ensemble of nodes.
 * @param   {$.oNode[]}    nodes               The nodes to look at.
 * @param   {string}       [paletteName]       A custom name for the created palette.
 * @param   {string}       [colorName]         A custom name to give to the gathered colors.
 *
 * @return       {$.oLink[]}      An array of unique links existing between the nodes.
 */
$.oScene.prototype.createPaletteFromNodes = function(nodes, paletteName, colorName){
  if (typeof paletteName === 'undefined') var paletteName = this.name;
  if (typeof colorName ==='undefined') var colorName = false;

  // get unique Color Ids
  var _usedColors = {};
  for (var i in nodes){
    _colors = nodes[i].usedColors;
    for (var j in _colors){
      _usedColors[_colors[j].id] = _colors[j];
    }
  }
  _usedColors = Object.keys(_usedColors).map(function(x){return _usedColors[x]});

  // create single palette
  var _newPalette = this.addPalette(paletteName);
  _newPalette.colors[0].remove();

  for (var i=0; i<_usedColors.length; i++){
    var _colorCopy = _usedColors[i].copyToPalette(_newPalette);
    if (colorName) _colorCopy.name = colorName+" "+(i+1);
  }

  return _newPalette;
}


/**
 * Returns all the links existing between an ensemble of nodes.
 * @param   {$.oNode[]}      nodes                         The nodes to look at.
 *
 * @return  {$.oLink[]}      An array of unique links existing between the nodes.
 */
$.oScene.prototype.getNodesLinks = function (nodes){
  var _links = [];
  var _linkStrings = [];
  // var _nodePaths = nodes.map(function(x){return x.path});
  var _nodePaths = {};

  for (var i in nodes){
    _nodePaths[nodes[i].path] = nodes[i];
  }

  for (var i in nodes){
    var _inLinks = nodes[i].getInLinks();
    var _outLinks = nodes[i].getOutLinks();

    // add link only once and replace the node object for one from the passed arguments
    for (var j in _inLinks){
      var _link = _inLinks[j];
      var _path = _link.outNode.path;
      if (_nodePaths.hasOwnProperty(_path) && _linkStrings.indexOf(_link.toString()) == -1){
        _link.inNode = nodes[i];
        _link.outNode = _nodePaths[_path];
        _links.push(_link);
        _linkStrings.push(_link.toString());
      }
    }

    // add link only once and replace the inNode object for one from the passed arguments
    for (var j in _outLinks){
      var _link = _outLinks[j];
      var _path = _link.inNode.path;
      if (_nodePaths.hasOwnProperty(_link.inNode.path) && _linkStrings.indexOf(_link.toString()) == -1){
        _link.outNode = nodes[i];
        _link.inNode = _nodePaths[_link.inNode.path];
        _links.push(_link);
        _linkStrings.push(_link.toString());
      }
    }
  }

  return _links;
}


/**
 * Merges Drawing nodes into a single node.
 * @param   {$.oNode[]}      nodes                         The Drawing nodes to merge.
 * @param   {string}         resultName                    The Node name for the resulting node of the merged content.
 * @param   {bool}           deleteMerged                  Whether the original nodes be deleted.
 *
 * @return {$.oNode}        The resulting drawing node from the merge.
 */
$.oScene.prototype.mergeNodes = function (nodes, resultName, deleteMerged){
    // TODO: is there a way to do this without Action.perform?
    // pass a oNode object as argument for destination node instead of name/group?

    if (typeof resultName === 'undefined') var resultName = nodes[0].name+"_merged"
    if (typeof group === 'undefined') var group = nodes[0].group;
    if (typeof deleteMerged === 'undefined') var deleteMerged = true;

    // only merge READ nodes so we filter out other nodes from parameters
    nodes = nodes.filter(function(x){return x.type == "READ"})

    var _timeline = this.getTimeline()
    nodes = nodes.sort(function(a, b){return a.timelineIndex(_timeline) - b.timelineIndex(_timeline)})

    // create a new destination node for the merged result
    var _mergedNode = this.addDrawingNode(resultName);

    // connect the node to the scene base composite, TODO: handle better placement
    // also TODO: check that the composite is connected to the display currently active
    // also TODO: disable pegs that affect the nodes but that we don't want to merge
    var _composite = this.nodes.filter(function(x){return x.type == "COMPOSITE"})[0]

    _mergedNode.linkOutNode(_composite);

    // get  the individual keys of all nodes
    var _keys = []
    for (var i in nodes){
        var _timings = nodes[i].timings;
        var _frameNumbers = _keys.map(function (x){return x.frameNumber})
        for (var j in _timings){
            if (_frameNumbers.indexOf(_timings[j].frameNumber) == -1) _keys.push(_timings[j])
        }
    }


    // sort frame objects by frameNumber
    _keys = _keys.sort(function(a, b){return a.frameNumber - b.frameNumber})

    // create an empty drawing for each exposure of the nodes to be merged
    for (var i in _keys){
        var _frame = _keys[i].frameNumber
        _mergedNode.element.addDrawing(_frame)

        // copy paste the content of each of the nodes onto the mergedNode
        // code inspired by Bake_Parent_to_Drawings v1.2 from Yu Ueda (raindropmoment.com)
        frame.setCurrent( _frame );

        Action.perform("onActionChooseSelectTool()", "cameraView");
        for (var j=nodes.length-1; j>=0; j--){
            //if (nodes[j].attributes.drawing.element.frames[_frame].isBlank) continue;

            DrawingTools.setCurrentDrawingFromNodeName( nodes[j].path, _frame );
            Action.perform("selectAll()", "cameraView");

            // select all and check. If empty, operation ends for the current frame
            if (Action.validate("copy()", "cameraView").enabled){
                Action.perform("copy()", "cameraView");
                DrawingTools.setCurrentDrawingFromNodeName( _mergedNode.path, _frame );
                Action.perform("paste()", "cameraView");
            }
        }
    }

    _mergedNode.attributes.drawing.element.column.extendExposures();
    _mergedNode.placeAtCenter(nodes)

    // connect to the same composite as the first node, at the same place
    // delete nodes that were merged if parameter is specified
    if (deleteMerged){
        for (var i in nodes){
            nodes[i].remove();
        }
    }
    return _mergedNode;
}


/**
 * export a template from the specified nodes.
 * @param   {$.oNodes[]}  nodes                             The list of nodes included in the template.
 * @param   {bool}        [exportPath]                      The path of the TPL file to export.
 * @param   {string}      [exportPalettesMode='usedOnly']   can have the values : "usedOnly", "all", "createPalette"
 * @param   {string}      [renameUsedColors=]               if creating a palette, optionally set here the name for the colors (they will have a number added to each)
 * @param   {copyOptions} [copyOptions]                     An object containing paste options as per Harmony's standard paste options.
 *
 * @return {bool}         The success of the export.
 * @todo turn exportPalettesMode into an enum?
 * @example
 * // how to export a clean palette with no extra drawings and everything renamed by frame, and only the necessary colors gathered in one palette:
 *
 * $.beginUndo();
 *
 * var doc = $.scn;
 * var nodes = doc.getSelectedNodes();
 *
 * for (var i in nodes){
 *   if (nodes[i].type != "READ") continue;
 *
 *   var myColumn = nodes[i].element.column;      // we grab the column directly from the element of the node
 *   myColumn.removeUnexposedDrawings();          // remove extra unused drawings
 *   myColumn.renameAllByFrame();                 // rename all drawings by frame
 * }
 *
 * doc.exportTemplate(nodes, "C:/templateExample.tpl", "createPalette"); // "createPalette" value will create one palette for all colors
 *
 * $.endUndo();
 */
$.oScene.prototype.exportTemplate = function(nodes, exportPath, exportPalettesMode, renameUsedColors, copyOptions){
  if (typeof exportPalettesMode === 'undefined') var exportPalettesMode = "usedOnly";
  if (typeof copyOptions === 'undefined') var copyOptions = copyPaste.getCurrentCreateOptions();
  if (typeof renameUsedColors === 'undefined') var renameUsedColors = false;

  if (!Array.isArray(nodes)) nodes = [nodes];

  // add nodes included in groups as they'll get automatically exported
  var _allNodes = nodes;
  for (var i in nodes){
    if (nodes[i].type == "GROUP") _allNodes = _allNodes.concat(nodes[i].subNodes(true));
  }

  var _readNodes = _allNodes.filter(function (x){return x.type == "READ";});

  var _templateFolder = new this.$.oFolder(exportPath);
  while (_templateFolder.exists) _templateFolder = new this.$.oFolder(_templateFolder.path.replace(".tpl", "_1.tpl"));

  var _name = _templateFolder.name.replace(".tpl", "");
  var _folder = _templateFolder.folder.path;

  // create the palette with only the colors contained in the layers
  if (_readNodes.length > 0){
    if(exportPalettesMode == "usedOnly"){
      var _usedPalettes = [];
      var _usedPalettePaths = [];
      for (var i in _readNodes){
        var _palettes = _readNodes[i].getUsedPalettes();
        for (var j in _palettes){
          if (_usedPalettePaths.indexOf(_palettes[j].path.path) == -1){
            _usedPalettes.push(_palettes[j]);
            _usedPalettePaths.push(_palettes[j].path.path);
          }
        }
      }
      this.$.debug("found palettes : "+_usedPalettes.map(function(x){return x.name}), this.$.DEBUG_LEVEL.LOG);
    }

    if (exportPalettesMode == "createPalette"){
      var templatePalette = this.createPaletteFromNodes(_readNodes, _name, renameUsedColors);
      var _usedPalettes = [templatePalette];
    }
  }


  this.selectedNodes = _allNodes;
  this.selectedFrames = [this.startPreview, this.stopPreview];

  this.$.debug("exporting selection :"+this.selectedFrames+"\n\n"+this.selectedNodes.join("\n")+"\n\n to folder : "+_folder+"/"+_name, this.$.DEBUG_LEVEL.LOG)

  try{
    var success = copyPaste.createTemplateFromSelection (_name, _folder);
    if (success == "") throw new Error("export failed")
  }catch(error){
    this.$.debug("Export of template "+_name+" failed. Error: "+error, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  this.$.debug("export of template "+_name+" finished, cleaning palettes", this.$.DEBUG_LEVEL.LOG);

  if (_readNodes.length > 0 && exportPalettesMode != "all"){
    // deleting the extra palettes from the exported template
    var _paletteFolder = new this.$.oFolder(_templateFolder.path+"/palette-library");
    var _paletteFiles = _paletteFolder.getFiles();
    var _paletteNames = _usedPalettes.map(function(x){return x.name});

    for (var i in _paletteFiles){
      var _paletteName = _paletteFiles[i].name;
      if (_paletteNames.indexOf(_paletteName) == -1) _paletteFiles[i].remove();
    }

    // building the template palette list
    var _listFile = ["ToonBoomAnimationInc PaletteList 1"];

    if (exportPalettesMode == "createPalette"){
      _listFile.push("palette-library/"+_name+' LINK "'+_paletteFolder+"/"+_name+'.plt"');
    }else if (exportPalettesMode == "usedOnly"){
      for (var i in _usedPalettes){
        this.$.debug("palette "+_usedPalettes[i].name+" to be included in template", this.$.DEBUG_LEVEL.LOG);
        _listFile.push("palette-library/"+_usedPalettes[i].name+' LINK "'+_paletteFolder+"/"+_usedPalettes[i].name+'.plt"');
      }
    }

    var _paletteListFile = new this.$.oFile(_templateFolder.path+"/PALETTE_LIST");
    try{
      _paletteListFile.write(_listFile.join("\n"));
    }catch(err){
      this.$.debug(err, this.$.DEBUG_LEVEL.ERROR)
    }

    // remove the palette created for the template
    if (exportPalettesMode == "createPalette"){
      var _paletteFile = _paletteFolder.getFiles()[0];
      if (_paletteFile){
        _paletteFile.rename(_name);
        if (templatePalette) templatePalette.remove(true);
      }
    }
  }

  selection.clearSelection();
  return true;
}


/**
 * Imports the specified template into the scene.
 * @deprecated
 * @param   {string}           tplPath                                        The path of the TPL file to import.
 * @param   {string}           [group]                                        The path of the existing target group to which the TPL is imported.
 * @param   {$.oNode[]}        [destinationNodes]                             The nodes affected by the template.
 * @param   {bool}             [extendScene]                                  Whether to extend the exposures of the content imported.
 * @param   {$.oPoint}         [nodePosition]                                 The position to offset imported new nodes.
 * @param   {object}           [pasteOptions]                                 An object containing paste options as per Harmony's standard paste options.
 *
 * @return {$.oNode[]}         The resulting pasted nodes.
 */
$.oScene.prototype.importTemplate = function( tplPath, group, destinationNodes, extendScene, nodePosition, pasteOptions ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.importTemplate is deprecated. Use oGroupNode.importTemplate instead")
    var _node = _group.addNode(tplPath, destinationNodes, extendScene, nodePosition, pasteOptions )
    return _nodes;
  }else{
    throw new Error (group+" is an invalid group to import the template into.")
  }
}


/**
 * Exports a png of the selected node/frame. if no node is given, all layers will be visible.
 * @param {$.oFile}  path                        The path in which to save the image. Image will be outputted as PNG.
 * @param {$.oNode}  [includedNodes]             The nodes to include in the rendering. If no node is specified, all layers will be visible.
 * @param {int}      [exportFrame]               The frame at which to create the image. By default, the timeline current Frame.
 * @param {bool}     [exportCameraFrame=false]   Whether to export the camera frames
 * @param {bool}     [exportBackground=false]    Whether to add a white background.
 * @param {float}    [frameScale=1]              A factor by which to scale the frame. ex: 1.05 will add a 10% margin (5% on both sides)
 */
$.oScene.prototype.exportLayoutImage = function (path, includedNodes, exportFrame, exportCameraFrame, exportBackground, frameScale, format){
  if (typeof includedNodes === 'undefined') var includedNodes = [];
  if (typeof exportCameraFrame === 'undefined') var exportCameraFrame = false;
  if (typeof exportBackground === 'undefined') var exportBackground = false;
  if (typeof frameScale === 'undefined') var frameScale = 1;
  if (typeof frame === 'undefined') var frame = 1;
  if (typeof format === 'undefined') var format = "PNG4";
  if (typeof path != this.$.oFile) path = new $.oFile(path);

  var exporter = new LayoutExport();
  var params = new LayoutExportParams();
  params.renderStaticCameraAtSceneRes = true;
  params.fileFormat = format;
  params.borderScale = frameScale;
  params.exportCameraFrame = exportCameraFrame;
  params.exportAllCameraFrame = false;
  params.filePattern = path.name;
  params.fileDirectory = path.folder;
  params.whiteBackground = exportBackground;

  includedNodes = includedNodes.filter(function(x){return ["CAMERA", "READ", "COLOR_CARD", "GRADIENT"].indexOf(x.type) != -1 && x.enabled })
  var _timeline = new this.$.oTimeline();
  includedNodes = includedNodes.sort(function (a, b){return b.timelineIndex(_timeline) - a.timelineIndex(_timeline)})

  if (includedNodes.length == 0) {
    params.node = this.root;
    params.frame = exportFrame;
    params.layoutname = this.name;
    exporter.addRender(params);
    if (!exporter.save(params)) throw new Error("failed to export layer "+oNode.name+" at location "+path);
  }else{
    for (var i in includedNodes){
      var includedNode = includedNodes[i];
      params.whiteBackground = (i==0 && exportBackground);
      params.node = includedNode.path;
      params.frame = exportFrame;
      params.layoutname = includedNode.name;
      params.exportCameraFrame = ((i == includedNodes.length-1) && exportCameraFrame);
      exporter.addRender(params);
      if (!exporter.save(params)) throw new Error("failed to export layer "+oNode.name+" at location "+path);
    }
  }

  exporter.flush();

  return path;
}


/**
 * Export the scene as a single PSD file, with layers described by the layerDescription array. This function is not supported in batch mode.
 * @param {$.oFile}  path
 * @param {float}    margin                    a factor by which to increase the rendering area. for example, 1.05 creates a 10% margin. (5% on each side)
 * @param {Object[]} layersDescription          must be an array of objects {layer: $.oNode, frame: int} which describe all the images to export. By default, will include all visible layers of the timeline.
 */
$.oScene.prototype.exportPSD = function (path, margin, layersDescription){
  if (typeof margin === 'undefined') var margin = 1;
  if (typeof layersDescription === 'undefined') {
    // export the current frame for each drawing layer present in the default timeline.
    var _allNodes = this.nodes.filter(function(x){return ["READ", "COLOR_CARD", "GRADIENT"].indexOf(x.type) != -1 && x.enabled })
    var _timeline = new this.$.oTimeline();
    _allNodes = _allNodes.sort(function (a, b){return b.timelineIndex(_timeline) - a.timelineIndex(_timeline)})
    var _scene = this;
    var layersDescription = _allNodes.map(function(x){return ({layer: x, frame: _scene.currentFrame})})
  }
  if (typeof path != this.$.oFile) path = new $.oFile(path)
  var tempPath = new $.oFile(path.folder+"/"+path.name+"~")

  var errors = [];

  // setting up render
  var exporter = new LayoutExport();
  var params = new LayoutExportParams();
  params.renderStaticCameraAtSceneRes = true;
  params.fileFormat = "PSD4";
  params.borderScale = margin;
  params.exportCameraFrame = false;
  params.exportAllCameraFrame = false;
  params.filePattern = tempPath.name;
  params.fileDirectory = tempPath.folder;
  params.whiteBackground = false;

  // export layers
  for (var i in layersDescription){
    var _frame = layersDescription[i].frame;
    var _layer = layersDescription[i].layer;

    params.node = _layer.path;
    params.frame = _frame;
    params.layoutname = _layer.name;
    params.exportCameraFrame = (i == layersDescription.length-1);
    exporter.addRender(params);

    if (!exporter.save(params)) errors.push(params.layoutname);
  }

  if (errors.length > 0) throw new Error("errors during export of file "+path+" with layers "+errors)

  // write file
  exporter.flush();

  if (path.exists) path.remove();
  log(tempPath.exist+" "+tempPath);
  tempPath.rename(path.name+".psd");
}


/**
 * Imports a PSD to the scene.
 * @Deprecated use oGroupNode.importPSD instead
 * @param   {string}         path                          The palette file to import.
 * @param   {string}         [group]                       The path of the existing group to import the PSD into.
 * @param   {$.oPoint}       [nodePosition]                The position for the node to be placed in the network.
 * @param   {bool}           [separateLayers]              Separate the layers of the PSD.
 * @param   {bool}           [addPeg]                      Whether to add a peg.
 * @param   {bool}           [addComposite]                Whether to add a composite.
 * @param   {string}         [alignment]                   Alignment type.
 *
 * @return {$.oNode[]}     The nodes being created as part of the PSD import.
 */
$.oScene.prototype.importPSD = function( path, group, nodePosition, separateLayers, addPeg, addComposite, alignment ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.importPSD is deprecated. Use oGroupNode.importPSD instead")
    var _node = _group.importPSD(path, separateLayers, addPeg, addComposite, alignment, nodePosition)
    return _node;
  }else{
    throw new Error (group+" is an invalid group to import a PSD file to.")
  }
}


/**
 * Updates a previously imported PSD by matching layer names.
 * @deprecated
 * @param   {string}       path                          The PSD file to update.
 * @param   {bool}         [separateLayers]              Whether the PSD was imported as separate layers.
 *
 * @returns {$.oNode[]}    The nodes affected by the update
 */
$.oScene.prototype.updatePSD = function( path, group, separateLayers ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.updatePSD is deprecated. Use oGroupNode.updatePSD instead")
    var _node = _group.updatePSD(path, separateLayers)
    return _node;
  }else{
    throw new Error (group+" is an invalid group to update a PSD file in.")
  }
}


/**
 * Imports a sound into the scene
 * @param   {string}         path                          The sound file to import.
 * @param   {string}         layerName                     The name to give the layer created.
 *
 * @return {$.oNode}        The imported sound column.
 */
 $.oScene.prototype.importSound = function(path, layerName){
   var _audioFile = new this.$.oFile(path);
   if (typeof layerName === 'undefined') var layerName = _audioFile.name;

   // creating an audio column for the sound
    var _soundColumn = this.addColumn("SOUND", layerName);
    column.importSound( _soundColumn.name, 1, path);

    return _soundColumn;
 }


 /**
 * Exports a QT of the scene
 * @param   {string}         path                          The path to export the quicktime file to.
 * @param   {string}         display                       The name of the display to use to export.
 * @param   {double}         scale                         The scale of the export compared to the scene resolution.
 * @param   {bool}           exportSound                   Whether to include the sound in the export.
 * @param   {bool}           exportPreviewArea             Whether to only export the preview area of the timeline.
 *
 * @return {bool}        The success of the export
 */
$.oScene.prototype.exportQT = function( path, display, scale, exportSound, exportPreviewArea){
  if (typeof display === 'undefined') var display = node.getName(node.getNodes(["DISPLAY"])[0]);
  if (typeof exportSound === 'undefined') var exportSound = true;
  if (typeof exportPreviewArea === 'undefined') var exportPreviewArea = false;
  if (typeof scale === 'undefined') var scale = 1;

  if (display instanceof oNode) display = display.name;

  var _startFrame = exportPreviewArea?scene.getStartFrame():1;
  var _stopFrame = exportPreviewArea?scene.getStopFrame():this.length-1;
  var _resX = this.defaultResolutionX*scale
  var _resY= this.defaultResolutionY*scale
  return exporter.exportToQuicktime ("", _startFrame, _stopFrame, exportSound, _resX, _resY, path, display, true, 1);
}


/**
 * Imports a QT into the scene
 * @Deprecated
 * @param   {string}         path                          The quicktime file to import.
 * @param   {string}         group                         The group to import the QT into.
 * @param   {$.oPoint}       nodePosition                  The position for the node to be placed in the network.
 * @param   {bool}           extendScene                   Whether to extend the scene to the duration of the QT.
 * @param   {string}         alignment                     Alignment type.
 *
 * @return {$.oNode}        The imported Quicktime Node.
 */
$.oScene.prototype.importQT = function( path, group, importSound, nodePosition, extendScene, alignment ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.importQT is deprecated. Use oGroupNode.importQTs instead")
    var _node = _group.importQT(path, importSound, extendScene, alignment, nodePosition)
    return _node;
  }else{
    throw new Error (group+" is an invalid group to import a QT file to.")
  }
}


/**
 * Adds a backdrop to a group in a specific position.
 * @Deprecated
 * @param   {string}           groupPath                         The group in which this backdrop is created.
 * @param   {string}           title                             The title of the backdrop.
 * @param   {string}           body                              The body text of the backdrop.
 * @param   {$.oColorValue}    color                             The oColorValue of the node.
 * @param   {float}            x                                 The X position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            y                                 The Y position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            width                             The Width of the backdrop, a padding value if nodes are specified.
 * @param   {float}            height                            The Height of the backdrop, a padding value if nodes are specified.
 *
 * @return {$.oBackdrop}       The created backdrop.
 */
$.oScene.prototype.addBackdrop = function( groupPath, title, body, color, x, y, width, height ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode){
    this.$.log("oScene.addBackdrop is deprecated. Use oGroupNode.addBackdrop instead")
    var _backdrop = _group.addBackdrop(title, body, color, x, y, width, height)
    return _backdrop;
  }else{
    throw new Error (groupPath+" is an invalid group to add the BackDrop to.")
  }
};


/**
 * Adds a backdrop to a group around specified nodes
 * @Deprecated
 * @param   {string}           groupPath                         The group in which this backdrop is created.
 * @param   {$.oNode[]}        nodes                             The nodes that the backdrop encompasses.
 * @param   {string}           title                             The title of the backdrop.
 * @param   {string}           body                              The body text of the backdrop.
 * @param   {$.oColorValue}    color                             The oColorValue of the node.
 * @param   {float}            x                                 The X position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            y                                 The Y position of the backdrop, an offset value if nodes are specified.
 * @param   {float}            width                             The Width of the backdrop, a padding value if nodes are specified.
 * @param   {float}            height                            The Height of the backdrop, a padding value if nodes are specified.
 *
 * @return {$.oBackdrop}       The created backdrop.
 */
$.oScene.prototype.addBackdropToNodes = function( groupPath, nodes, title, body, color, x, y, width, height ){
  if (typeof group === 'undefined') var group = this.root;
  var _group = (group instanceof this.$.oGroupNode)?group:this.$node(group);

  if (_group != null && _group instanceof this.$.oGroupNode) {
    this.$.log("oScene.addBackdropToNodes is deprecated. Use oGroupNode.addBackdropToNodes instead")
    var _backdrop = _group.addBackdropToNodes(nodes, title, body, color, x, y, width, height)
    return _backdrop;
  }else{
    throw new Error (groupPath+" is an invalid group to add the BackDrop to.")
  }
};


/**
 * Saves the scene.
 */
$.oScene.prototype.save = function( ){
  scene.saveAll();
}


/**
 * Saves the scene in a different location (only available on offline scenes).
 * @param {string} newPath    the new location for the scene (must be a folder path and not a .xstage)
 */
$.oScene.prototype.saveAs = function(newPath){
  if (this.online) {
    this.$.debug("Can't use saveAs() in database mode.", this.$.DEBUG_LEVEL.ERROR);
    return;
  }

  if (newPath instanceof this.$.oFile) newPath = newPath.path;
  return scene.saveAs(newPath);
}


/**
 * Saves the scene as new version.
 * @param {string}      newVersionName      The name for the new version
 * @param {bool}        markAsDefault       Wether to make this new version the default version that will be opened from the database.
 */
$.oScene.prototype.saveNewVersion = function(newVersionName, markAsDefault){
  if (typeof markAsDefault === 'undefined') var markAsDefault = true;

  return scene.saveAsNewVersion (newVersionName, markAsDefault);
}


/**
 * Renders the write nodes of the scene. This action saves the scene.
 * @param {bool}   [renderInBackground=true]    Whether to do the render on the main thread and block script execution
 * @param {int}    [startFrame=1]               The first frame to render
 * @param {int}    [endFrame=oScene.length]     The end of the render (non included)
 * @param {int}    [resX]                       The horizontal resolution of the render. Uses the scene resolution by default.
 * @param {int}    [resY]                       The vertical resolution of the render. Uses the scene resolution by default.
 * @param {string} [preRenderScript]            The path to the script to execute on the scene before doing the render
 * @param {string} [postRenderScript]           The path to the script to execute on the scene after the render is finished
 * @return {$.oProcess} In case of using renderInBackground, will return the oProcess object doing the render
 */
$.oScene.prototype.renderWriteNodes = function(renderInBackground, startFrame, endFrame, resX, resY, preRenderScript, postRenderScript){
  if (typeof renderInBackground === 'undefined') var renderInBackground = true;
  if (typeof startFrame === 'undefined') var startFrame = 1;
  if (typeof endFrame === 'undefined') var endFrame = this.length+1;
  if (typeof resX === 'undefined') var resX = this.resolutionX;
  if (typeof resY === 'undefined') var resY = this.resolutionY;

  this.save();
  var harmonyBin = specialFolders.bin+"/HarmonyPremium.exe";

  var args = ["-batch", "-frames", startFrame, endFrame, "-res", resX, resY, this.fov];

  if (typeof preRenderScript !== 'undefined'){
    args.push("-preRenderScript");
    args.push(preRenderScript);
  }

  if (typeof postRenderScript !== 'undefined'){
    args.push("-postRenderScript");
    args.push(postRenderScript);
  }

  if (this.online){
    args.push("-env");
    args.push(this.environnement);
    args.push("-job");
    args.push(this.job);
    args.push("-scene");
    args.push(this.name);
  }else{
    args.push(this.stage);
  }

  var p = new this.$.oProcess(harmonyBin, args);
  p.readChannel = "All";

  this.$.log("Starting render of scene "+this.name);
  if (renderInBackground){
    var length = endFrame - startFrame + 1;

    var progressDialogue = new this.$.oProgressDialog("Rendering : ",length,"Render Write Nodes", true);

    var cancelRender = function(){
      p.kill();
      this.$.alert("Render was canceled.")
    }

    var renderProgress = function(message){
      // reporting progress to log window
      var progressRegex = /Rendered Frame ([0-9]+)/igm;
      var matches = [];
      while (match = progressRegex.exec(message)) {
        matches.push(match[1]);
      }
      if (matches.length!=0){
        var progress = parseInt(matches.pop(), 10) - startFrame;
        progressDialogue.label = "Rendering Frame: " + progress + "/" + length;
        progressDialogue.value = progress;
        var percentage = Math.round(progress/length * 100);
        this.$.log("render : " + percentage + "% complete");
      }
    }

    var renderFinished = function(exitCode){
      if (exitCode == 0){
        // render success
        progressDialogue.label = "Rendering Finished"
        progressDialogue.value = length;
        this.$.log(exitCode + " : render finished");
      }else{
        this.$.log(exitCode + " : render cancelled");
      }
    }

    progressDialogue.canceled.connect(this, cancelRender);
    p.readyRead.connect(this, renderProgress);
    p.finished.connect(this, renderFinished);
    p.launchAndRead();
    return p;
  }else{
    var readout  = p.execute();
    this.$.log("render finished");
    return readout;
  }
}

/**
 * Closes the scene.
 * @param   {bool}            [exit]                                       Whether it should exit after closing.
 */
$.oScene.prototype.close = function( exit ){
  if (typeof nodePosition === 'undefined') exit = false;

  if( exit ){
    scene.closeSceneAndExit();
  }else{
    scene.closeScene();
  }
}

/**
 * Gets the current camera matrix.
 *
 * @return {Matrix4x4}          The matrix of the camera.
 */
$.oScene.prototype.getCameraMatrix = function( ){
    return scene.getCameraMatrix();
}

/**
 * Gets the current projection matrix.
 *
 * @return {Matrix4x4}          The projection matrix of the camera/scene.
 */
$.oScene.prototype.getProjectionMatrix = function( ){
  var fov = this.fov;
  var f   = scene.toOGL( new Point3d( 0.0, 0.0, this.unitsZ ) ).z;
  var n   = 0.00001;

  //Standard pprojection matrix derivation.
  var S = 1.0 / Math.tan( ( fov/2.0 ) * ( $.pi/180.0 ) );
  var projectionMatrix = [  S,          0.0,                  0.0,     0.0,
                            0.0,          S,                  0.0,     0.0,
                            0.0,        0.0,       -1.0*(f/(f-n)),    -1.0,
                            0.0,        0.0,   -1.0*((f*n)/(f-n)),     0.0
                         ];

  var newMatrix = new Matrix4x4();
  for( var r=0;r<4;r++ ){
    for( var c=0;c<4;c++ ){
      newMatrix["m"+r+""+c] = projectionMatrix[ (c*4.0)+r ];
    }
  }
  return newMatrix;
}


/**
 * Gets the current scene's metadata.
 *
 * @see $.oMetadata
 * @return {$.oMetadata}          The metadata of the scene.
 */
$.oScene.prototype.getMetadata = function( ){
  return new this.$.oMetadata( );
}


// Short Notations

/**
 * Gets a node by the path.
 * @param   {string}   fullPath         The path of the node in question.
 *
 * @return  {$.oNode}                     The node found given the query.
 */
$.oScene.prototype.$node = function( fullPath ){
    return this.getNodeByPath( fullPath );
}

/**
 * Gets a column by the name.
 * @param  {string}             uniqueName               The unique name of the column as a string.
 * @param  {$.oAttribute}       oAttributeObject         The oAttribute object the column is linked to.
 *
 * @return {$.oColumn}          The node found given the query.
 */
$.oScene.prototype.$column = function( uniqueName, oAttributeObject ){
    return this.getColumnByName( uniqueName, oAttributeObject );
}


/**
 * Gets a palette by its name.
 * @param   {string}   name            The name of the palette.
 *
 * @return  {$.oPalette}               The node found given the query.
 */
$.oScene.prototype.$palette = function( name ){
    return this.getPaletteByName( name );
}
