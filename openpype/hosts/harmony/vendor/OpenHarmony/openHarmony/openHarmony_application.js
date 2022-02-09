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
//          $.oApp class            //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * The constructor for the $.oApp class
 * @classdesc
 * The $.oApp class provides access to the Harmony application and its widgets.
 * @constructor
 */
$.oApp = function(){
}


/**
 * The Harmony version number
 * @name $.oApp#version
 * @type {int}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'version', {
  get : function(){
    return parseInt(about.getVersionInfoStr().split("version").pop().split(".")[0], 10);
  }
});


/**
 * The software flavour: Premium, Advanced, Essential
 * @name $.oApp#flavour
 * @type {string}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'flavour', {
  get : function(){
    return about.getFlavorString();
  }
});


/**
 * The Harmony Main Window.
 * @name $.oApp#mainWindow
 * @type {QWidget}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'mainWindow', {
  get : function(){
    var windows = QApplication.topLevelWidgets();
    for ( var i in windows) {
      if (windows[i] instanceof QMainWindow && !windows[i].parentWidget()) return windows[i];
    }
    return false
  }
});


/**
 * The Harmony UI Toolbars.
 * @name $.oApp#toolbars
 * @type {QToolbar}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'toolbars', {
  get : function(){
    var widgets = QApplication.allWidgets();
    var _toolbars = widgets.filter(function(x){return x instanceof QToolBar})

    return _toolbars
  }
});



/**
 * The Position of the mouse cursor in the toonboom window coordinates.
 * @name $.oApp#mousePosition
 * @type {$.oPoint}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'mousePosition', {
  get : function(){
    var _position = this.$.app.mainWindow.mapFromGlobal(QCursor.pos());
    return new this.$.oPoint(_position.x(), _position.y(), 0);
  }
});


/**
 * The Position of the mouse cursor in the screen coordinates.
 * @name $.oApp#globalMousePosition
 * @type {$.oPoint}
 * @readonly
 */
Object.defineProperty($.oApp.prototype, 'globalMousePosition', {
  get : function(){
    var _position = QCursor.pos();
    return new this.$.oPoint(_position.x(), _position.y(), 0);
  }
});


/**
 * Access the tools available in the application
 * @name $.oApp#tools
 * @type {$.oTool[]}
 * @readonly
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
Object.defineProperty($.oApp.prototype, 'tools', {
  get: function(){
    if (typeof this._toolsObject === 'undefined'){
      this._toolsObject = [];
      var _currentTool = this.currentTool;
      var i = 0;
      Tools.setToolSettings({currentTool:{id:i}})
      while(Tools.getToolSettings().currentTool.name){
        var tool = Tools.getToolSettings().currentTool;
        this._toolsObject.push(new this.$.oTool(tool.id,tool.name));
        i++;
        Tools.setToolSettings({currentTool:{id:i}});
      }
      this.currentTool = _currentTool;
    }
    return this._toolsObject;
  }
})


/**
 * The Position of the mouse cursor in the screen coordinates.
 * @name $.oApp#currentTool
 * @type {$.oTool}
 */
Object.defineProperty($.oApp.prototype, 'currentTool', {
  get : function(){
    var _tool = Tools.getToolSettings().currentTool.id;
    return _tool;
  },
  set : function(tool){
    if (tool instanceof this.$.oTool) {
      tool.activate();
      return
    }
    if (typeof tool == "string"){
      try{
        this.getToolByName(tool).activate();
        return
      }catch(err){
        this.$.debug("'"+ tool + "' is not a valid tool name. Valid: "+this.tools.map(function(x){return x.name}).join(", "))
      }
    }
    if (typeof tool == "number"){
      this.tools[tool].activate();
      return
    }
  }
});


/**
 * Gets access to a widget from the Harmony Interface.
 * @param   {string}   name              The name of the widget to look for.
 * @param   {string}   [parentName]      The name of the parent widget to look into, in case of duplicates.
 * @return  {QWidget}   The widget if found, or null if it doesn't exist.
 */
$.oApp.prototype.getWidgetByName = function(name, parentName){
  var widgets = QApplication.allWidgets();
  for( var i in widgets){
    if (widgets[i].objectName == name){
      if (typeof parentName !== 'undefined' && (widgets[i].parentWidget().objectName != parentName)) continue;
      return widgets[i];
    }
  }
  return null;
}


/**
 * Access the Harmony Preferences
 * @name $.oApp#preferences
 * @example
 * // To access the preferences of Harmony, grab the preference object in the $.oApp class:
 * var prefs = $.app.preferences;
 *
 * // It's then possible to access all available preferences of the software:
 * for (var i in prefs){
 *   log (i+" "+prefs[i]);
 * }
 *
 * // accessing the preference value can be done directly by using the dot notation:
 * prefs.USE_OVERLAY_UNDERLAY_ART = true;
 * log (prefs.USE_OVERLAY_UNDERLAY_ART);
 *
 * //the details objects of the preferences object allows access to more information about each preference
 * var details = prefs.details
 * log(details.USE_OVERLAY_UNDERLAY_ART.category+" "+details.USE_OVERLAY_UNDERLAY_ART.id+" "+details.USE_OVERLAY_UNDERLAY_ART.type);
 *
 * for (var i in details){
 *   log(i+" "+JSON.stringify(details[i]))       // each object inside detail is a complete oPreference instance
 * }
 *
 * // the preference object also holds a categories array with the list of all categories
 * log (prefs.categories)
 */
Object.defineProperty($.oApp.prototype, 'preferences', {
  get: function(){
    if (typeof this._prefsObject === 'undefined'){
      var _prefsObject = {};
      _categories = [];
      _details = {};

      Object.defineProperty(_prefsObject, "categories", {
        enumerable:false,
        value:_categories
      })

      Object.defineProperty(_prefsObject, "details", {
        enumerable:false,
        value:_details
      })

      var prefFile = (new oFile(specialFolders.resource+"/prefs.xml")).parseAsXml().children[0].children;

      var userPrefFile = new oFile(specialFolders.userConfig + "/Harmony Premium-pref.xml")
      // Harmony Pref file is called differently on the database userConfig
      if (!userPrefFile.exists) userPrefFile = new oFile(specialFolders.userConfig + "/Harmony-pref.xml")

      if (userPrefFile.exists){
        var userPref = {objectName: "category", id: "user", children:userPrefFile.parseAsXml().children[0].children};
        prefFile.push(userPref);
      }

      for (var i in prefFile){
        if (prefFile[i].objectName != "category" || prefFile[i].id == "Storyboard") continue;
        var category = prefFile[i].id;
        if (_categories.indexOf(category) == -1) _categories.push(category);

        var preferences = prefFile[i].children;

        // create a oPreference instance for each found preference and add a getter setter to the $.oApp._prefsObject
        for (var j in preferences){

          // evaluate condition for conditional preferences. For now only support Harmony Premium prefs
          if (preferences[j].objectName == "if"){
            var condition = preferences[j].condition;
            var regex = /(not essentials|not sboard|not paint)/
            if (regex.exec(condition)) preferences = preferences.concat(preferences[j].children)
            continue;
          }
          var type = preferences[j].objectName;
          var keyword = preferences[j].id;
          var description = preferences[j].shortDesc;
          var descriptionText = preferences[j].longDesc;
          if (type == "color"){
            if (typeof preferences[j].alpha === 'undefined') preferences[j].alpha = 255;
            var value = new ColorRGBA(preferences[j].red, preferences[j].green, preferences[j].blue, preferences[j].alpha)
          }else{
            var value = preferences[j].value;
          }
          // var docString = (category+" "+keyword+" "+type+" "+description)
          //
          var pref = this.$.oPreference.createPreference(category, keyword, type, value, description, descriptionText, _prefsObject);
          _details[pref.keyword] = pref;
        }
      }

      this._prefsObject = _prefsObject;
    }

    return this._prefsObject;
  }
})



/**
 * The list of stencils available in the Harmony UI.
 * @name $.oApp#stencils
 * @type {$.oStencil[]}
 * @example
 * // Access the stencils list through the $.app object.
 * var stencils = $.app.stencils
 *
 * // list all the properties of stencils
 * for (var i in stencils){
 *   log(" ---- "+stencils[i].type+" "+stencils[i].name+" ---- ")
 *   for(var j in stencils[i]){
 *     log (j);
 *   }
 * }
 */
Object.defineProperty($.oApp.prototype, 'stencils', {
  get: function(){
    if (typeof this._stencilsObject === 'undefined'){
      // parse stencil xml file penstyles.xml to get stencils info
      var stencilsFile = (new oFile(specialFolders.userConfig+"/penstyles.xml")).read();
      var penRegex = /<pen>([\S\s]*?)<\/pen>/igm
      var stencils = [];
      var stencilXml;
      while(stencilXml = penRegex.exec(stencilsFile)){
        var stencilObject = this.$.oStencil.getFromXml(stencilXml[1]);
        stencils.push(stencilObject);
      }
      this._stencilsObject = stencils;
    }
    return this._stencilsObject;
  }
})



/**
 * The currently selected stencil. Always returns the pencil tool current stencil.
 * @name $.oApp#currentStencil
 * @type {$.oStencil}
 */
Object.defineProperty($.oApp.prototype, 'currentStencil', {
  get: function(){
    return this.stencils[PaletteManager.getCurrentPenstyleIndex()];
  },
  set: function(stencil){
    if (stencil instanceof this.$.oStencil) var stencil = stencil.name
    this.$.debug("Setting current pen: "+ stencil)
    PenstyleManager.setCurrentPenstyleByName(stencil);
  }
})



// $.oApp Class Methods

/**
 * get a tool by its name
 * @return {$.oTool}   a oTool object representing the tool, or null if not found.
 */
$.oApp.prototype.getToolByName = function(toolName){
  var _tools  = this.tools;
  for (var i in _tools){
    if (_tools[i].name.toLowerCase() == toolName.toLowerCase()) return _tools[i];
  }
  return null;
}


/**
 * returns the list of stencils useable by the specified tool
 * @param {$.oTool}     tool      the tool object we want valid stencils for
 * @return {$.oStencil[]}    the list of stencils compatible with the specified tool
 */
$.oApp.prototype.getValidStencils = function (tool){
  if (typeof tool === 'undefined') var tool = this.currentTool;
  return tool.stencils;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oToolbar class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * The $.oToolbar constructor.
 * @name        $.oToolbar
 * @constructor
 * @classdesc   A toolbar that can contain any type of widgets.
 * @param       {string}     name              The name of the toolbar to create.
 * @param       {QWidget[]} [widgets]          The list of widgets to add to the toolbar.
 * @param       {QWidget}   [parent]           The parent widget to add the toolbar to.
 * @param       {bool}      [show]             Whether to show the toolbar instantly after creation.
 */
$.oToolbar = function( name, widgets, parent, show ){
  if (typeof parent === 'undefined') var parent = $.app.mainWindow;
  if (typeof widgets === 'undefined') var widgets = [];
  if (typeof show === 'undefined') var show = true;

  this.name = name;
  this._widgets = widgets;
  this._parent = parent;

  if (show) this.show();
}


/**
 * Shows the oToolbar.
 * @name    $.oToolbar#show
 */
$.oToolbar.prototype.show = function(){
  if (this.$.batchMode) {
    this.$.debug("$.oToolbar not supported in batch mode", this.$.DEBUG_LEVEL.ERROR)
    return;
  }

  var _parent = this._parent;
  var _toolbar = new QToolbar();
  _toolbar.objectName = this.name;

  for (var i in this.widgets){
    _toolbar.addWidget(this.widgets[i]);
  }

  _parent.addToolbar(_toolbar);
  this.toolbar = _toolbar;

  return this.toolbar;
}
