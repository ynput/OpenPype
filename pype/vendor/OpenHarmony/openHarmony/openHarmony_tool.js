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
//          $.oTool class           //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oTool class
 * @constructor
 * @classdec
 * The $.oTool Class describes a single tool available. It can be activated through this class.
 * @param {int}   id     The id of the tool
 * @param {name}  name   The name of the tool
 * @property {int}   id     The id of the tool
 * @property {name}  name   The name of the tool
 * @example
 * // Access the list of currently existing tools by using the $.app object
 * var tools = $.app.tools;
 * 
 * // output the list of tools names and ids
 * for (var i in tools){
 *   log(i+" "+tools[i].name)
 * }
 * 
 * // To get a tool by name, use the $.app.getToolByName() function
 * var brushTool = $.app.getToolByName("Brush");
 * log (brushTool.name+" "+brushTool.id)            // Output: Brush 9
 * 
 * // it's also possible to activate a tool in several ways:
 * $.app.currentTool = 9;         // using the tool "id"
 * $.app.currentTool = brushTool  // by passing a oTool object
 * $.app.currentTool = "Brush"    // using the tool name
 * 
 * brushTool.activate()           // by using the activate function of the oTool class
 */
$.oTool = function(id, name){
  this.id = id;
  this.name = name;
}


/**
 * The list of stencils this tool can use. Not currently supported by custom tools.
 * @name $.oTool#stencils
 * @type {$.oStencil[]}
 */
Object.defineProperty($.oTool, "stencils", {
  get: function(){
    // an object describing what tool can use what stencils
    var _stencilTypes = {
      pencil:["Ellipse", "Line", "Pencil", "Polyline", "Rectangle"],
      penciltemplate:["Ellipse", "Line", "Pencil", "Polyline", "Rectangle"],
      brush:["Brush"],
      texture:["Brush"],
      bitmapbrush:["Brush"],
      bitmaperaser:["Eraser"]
    }

    var _stencils = this.$.app.stencils;
    var stencilsTypeList = [];
    var stencilsList = [];

    for (var i in _stencilTypes){
      if (_stencilTypes[i].indexOf(this.name) != -1) stencilsTypeList.push(i);
    }

    for (var i in _stencils){
      if (stencilsTypeList.indexOf(_stencils[i].type) != -1) stencilsList.push(_stencils[i]);
    }

    return stencilsList;
  }
})

/**
 * Activates the tool.
 */
$.oTool.prototype.activate = function(){
  Tools.setToolSettings({currentTool:{id:this.id}});
}
