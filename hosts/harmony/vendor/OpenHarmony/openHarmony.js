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
//          $ (DOM) class           //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * All the classes can be accessed from it, and it can be passed to a different context.
 * @namespace
 * @classdesc The $ global object that holds all the functions of openHarmony.
 * @property {int}     debug_level               The debug level of the DOM.
 * @property {bool}    batchMode                 Deactivate all ui and incompatible functions to ensure scripts run in batch.
 * @property {string}  file                      The openHarmony base file - THIS!
 *
 * @property {$.oScene}    getScene                  The harmony scene.
 * @property {$.oScene}    scene                     The harmony scene.
 * @property {$.oScene}    scn                       The harmony scene.
 * @property {$.oScene}    s                         The harmony scene.
 * @property {$.oApp}      getApplication            The Harmony Application Object.
 * @property {$.oApp}      application               The Harmony Application Object.
 * @property {$.oApp}      app                       The Harmony Application Object.
 * @property {$.oNetwork}  network                   Access point for all the functions of the $.oNetwork class
 * @property {$.oUtils}    utils                     Access point for all the functions of the $.oUtils class
 * @property {$.oDialog}   dialog                    Access point for all the functions of the $.oDialog class
 * @property {Object}      global                    The global scope.
 *
 * @example
 * // To access the functions, first call the $ object. It is made available after loading openHarmony like so:
 *
 * include ("openHarmony.js");
 *
 * var doc = $.scn;                    // grabbing the scene document
 * $.log("hello");                     // prints out a message to the MessageLog.
 * var myPoint = new $.oPoint(0,0,0);  // create a new class instance from an openHarmony class.
 *
 * // function members of the $ objects get published to the global scope, which means $ can be ommited
 *
 * log("hello");
 * var myPoint = new oPoint(0,0,0);    // This is all valid
 * var doc = scn;                      // "scn" isn't a function so this one isn't
 *
 */
$ = {
  debug_level : 0,

 /**
 * Enum to set the debug level of debug statements.
 * @name    $#DEBUG_LEVEL
 * @enum
 */
  DEBUG_LEVEL : {
                 'ERROR'   : 0,
                 'WARNING' : 1,
                 'LOG'     : 2
                },
  file      : __file__,
  directory : false,
  pi        : 3.14159265359
};


/**
 * The openHarmony main Install directory
 * @name $#directory
 * @type {string}
 */
Object.defineProperty( $, "directory", {
  get : function(){
    var currentFile = __file__
    return currentFile.split("\\").join("/").split( "/" ).slice(0, -1).join('/');
  }
});


/**
 * Wether Harmony is run with the interface or simply from command line
 */
Object.defineProperty( $, "batchMode", {
  get: function(){
    // use a cache to avoid pulling the widgets every time
    if (!this.hasOwnProperty("_batchMode")){
      this._batchMode = true;

      // batchmode is false if there are any widgets visible in the application
      var _widgets = QApplication.topLevelWidgets();
      for (var i in _widgets){
        if (_widgets[i].visible) this._batchMode = false;
      }
    }
    return this._batchMode
  }
})

/**
 * Function to load openHarmony files from the %installdir%/openHarmony/ folder.
 * @name $#loadOpenHarmonyFiles
 * @private
 */
var _ohDirectory = $.directory+"/openHarmony/";
var _dir = new QDir(_ohDirectory);
_dir.setNameFilters(["openHarmony*.js"]);
_dir.setFilter( QDir.Files);
var _files = _dir.entryList();

for (var i in _files){
  include( _ohDirectory + "/" + _files[i]);
}




/**
 * The standard debug that uses logic and level to write to the messagelog. Everything should just call this to write internally to a log in OpenHarmony.
 * @function
 * @name    $#debug
 * @param   {obj}   obj            Description.
 * @param   {int}   level          The debug level of the incoming message to log.
 */
$.debug = function( obj, level ){
  if( level > this.debug_level ) return;

  try{
    if (typeof obj !== 'object') throw new Error();
    this.log(JSON.stringify(obj));
  }catch(err){
    this.log(obj);
  }
}


/**
 * Log the string to the MessageLog.
 * @function
 * @name    $#log
 * @param {string}  str            Text to log.
 */
$.log = function( str ){
  MessageLog.trace( str );
  System.println( str );
}


/**
 * Log the object and its contents.
 * @function
 * @name    $#logObj
 * @param   {object}   object            The object to log.
 * @param   {int}      debugLevel        The debug level.
 */
$.logObj = function( object ){
  for (var i in object){
    try {
      if (typeof object[i] === "function") continue;
      $.log(i+' : '+object[i])
      if (typeof object[i] == "Object"){
        $.log(' -> ')
        $.logObj(object[i])
        $.log(' ----- ')
      }
    }catch(error){}
  }
}


//---- App  --------------
$.app = new $.oApp();
$.application = $.app;
$.getApplication = $.app;


//---- Scene  --------------
$.s     = new $.oScene();
$.scn   = $.s;
$.scene = $.s;
$.getScene = $.s;


/**
 * Prompts with a confirmation dialog (yes/no choice).
 * @function
 * @name    $#confirm
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText]                 The text on the OK button of the dialog.
 * @param   {string}           [cancelButtonText]             The text on the CANCEL button of the dialog.
 *
 * @return  {bool}       Result of the confirmation dialog.
 */
$.confirm = function(){ return $.dialog.confirm.apply( $.dialog, arguments ) };


/**
 * Prompts with an alert dialog (informational).
 * @function
 * @name    $#alert
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText]                 The text on the OK button of the dialog.
 */
$.alert = function(){ return $.dialog.alert.apply( $.dialog, arguments ) };



/**
 * Prompts with an alert dialog with a text box which can be selected (informational).
 * @function
 * @name    $#alertBox
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText]                 The text on the OK button of the dialog.
 */
$.alertBox = function(){ return $.dialog.alertBox.apply( $.dialog, arguments ) };



/**
 * Prompts with an toast alert. This is a small message that can't be clicked and only stays on the screen for the duration specified.
 * @function
 * @name    $#toast
 * @param   {string}         labelText          The label/internal text of the dialog.
 * @param   {$.oPoint}       [position]         The position on the screen where the toast will appear (by default, slightly under the middle of the screen).
 * @param   {float}          [duration=2000]    The duration of the display (in milliseconds).
 * @param   {$.oColorValue}  [color="#000000"]  The color of the background (a 50% alpha value will be applied).
 */
$.toast = function(){ return $.dialog.toast.apply( $.dialog, arguments ) };



/**
 * Prompts for a user input.
 * @function
 * @name    $#prompt
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [prefilledText]                The text to display in the input area.
 */
$.prompt = function(){ return $.dialog.prompt.apply( $.dialog, arguments ) };


/**
 * Prompts with a file selector window
 * @function
 * @name $#browseForFile
 * @param {string} [text="Select a file:"] The title of the file select dialog.
 * @param {string} [filter="*"]            The filter for the file type and/or file name that can be selected. Accepts wildcard character "*".
 * @param {string} [getExisting=true]      Whether to select an existing file or a save location
 * @param {string} [acceptMultiple=false]  Whether or not selecting more than one file is ok. Is ignored if getExisting is false.
 * @param {string} [startDirectory]        The directory showed at the opening of the dialog.
 *
 * @return  {string[]}         The list of selected Files, 'undefined' if the dialog is cancelled
 */
$.browseForFile = function(){ return $.dialog.browseForFile.apply( $.dialog, arguments ) };


/**
 * Prompts with a folder selector window.
 * @function
 * @name $#browseForFolder
 * @param {string} [text]                The title of the confirmation dialog.
 * @param {string} [startDirectory]      The directory showed at the opening of the dialog.
 *
 * @return  {string}         The path of the selected folder, 'undefined' if the dialog is cancelled
 */
$.browseForFolder = function(){ return $.dialog.browseForFolder.apply( $.dialog, arguments ) };


/**
 * Gets access to a widget from the Harmony Interface.
 * @function
 * @name    $#getHarmonyUIWidget
 * @param   {string}   name              The name of the widget to look for.
 * @param   {string}   [parentName]      The name of the parent widget to look into, in case of duplicates.
 */
$.getHarmonyUIWidget = function(){ return $.app.getWidgetByName.apply( $.app, arguments ) }


//---- Cache Helpers ------
$.cache_columnToNodeAttribute = {};
$.cache_columnToNodeAttribute_date = (new Date()).getTime();
$.cache_oNode = {};


//------------------------------------------------
//-- Undo operations

/**
 * Starts the tracking of the undo accumulation, all subsequent actions are done in a single undo operation.<br>Close the undo accum with $.endUndo().
 * If this function is called multiple time, only the first time will count.
 * (this prevents small functions wrapped in their own undo block to interfere with global script undo)
 * @param   {string}           undoName        The name of the operation that is being done in the undo accum.
 * @name $#beginUndo
 * @function
 * @see $.endUndo
 */
$.beginUndo = function( undoName ){
  if ($.batchMode) return
  if (typeof undoName === 'undefined') var undoName = ''+((new Date()).getTime());
  if (!$.hasOwnProperty("undoStackSize")) $.undoStackSize = 0;
  if ($.undoStackSize == 0) scene.beginUndoRedoAccum( undoName );
  $.undoStackSize++;
}

/**
 * Cancels the tracking of the undo accumulation, everything between this and the start of the accumulation is undone.
 * @name $#cancelUndo
 * @function
 */
$.cancelUndo = function( ){
  scene.cancelUndoRedoAccum( );
}

/**
 * Stops the tracking of the undo accumulation, everything between this and the start of the accumulation behaves as a single undo operation.
 * If beginUndo function is called multiple time, each call must be matched with this function.
 * (this prevents small functions wrapped in their own undo block to interfere with global script undo)
 * @name $#endUndo
 * @function
 * @see $.beginUndo
 */
$.endUndo = function( ){
  if ($.batchMode) return

  if (!$.hasOwnProperty("undoStackSize")) $.undoStackSize = 1;
  $.undoStackSize--;
  if ($.undoStackSize == 0)   scene.endUndoRedoAccum();
}

/**
 * 	Undoes the last n operations. If n is not specified, it will be 1
 * @name $#undo
 * @function
 * @param   {int}           dist                                    The amount of operations to undo.
 */
$.undo = function( dist ){
  if (typeof dist === 'undefined'){ var dist = 1; }
  scene.undo( dist );
}

/**
 * 	Redoes the last n operations. If n is not specified, it will be 1
 * @name $#redo
 * @function
 * @param   {int}           dist                                    The amount of operations to undo.
 */
$.redo = function( dist ){
  if (typeof dist === 'undefined'){ var dist = 1; }
  scene.redo( dist );
}


/**
 * 	Gets the preferences from the Harmony stage.
 * @name $#getPreferences
 * @function
 */
$.getPreferences = function( ){
  return new $.oPreferences();
}

//---- Attach Helpers ------
$.network     = new $.oNetwork();
$.utils       = $.oUtils;
$.dialog      = new $.oDialog();
$.global      = this;


//---- Self caching -----

/**
 * change this value to allow self caching across openHarmony when initialising objects.
 * @name $#useCache
 * @type {bool}
 */
$.useCache = false;


/**
 * function to call in constructors of classes so that instances of this class
 * are cached and unique based on constructor arguments.
 * @returns a cached class instance or null if no cached instance exists.
 */
$.getInstanceFromCache = function(){
  if (!this.__proto__.hasOwnProperty("__cache__")) {
    this.__proto__.__cache__ = {};
  }
  var _cache = this.__proto__.__cache__;

  if (!this.$.useCache) return;

  var key = [];
  for (var i=0; i<arguments.length; i++){
    try{
      key.push(arguments[i]+"")
    }catch(err){} // ignore arguments that can't be converted to string
  }

  if (_cache.hasOwnProperty(key)) {
    this.$.log("instance returned from cache for "+key, this.$.DEBUG_LEVEL.ERROR)
    return _cache[key];
  }
  this.$.log("creating new instance for "+key, this.$.DEBUG_LEVEL.ERROR)
  _cache[key] = this;

  this.constructor.invalidateCache = function(){
    delete this.prototype.__cache__;
  }
  return
}


/**
 * invalidate all cache for classes that are self caching.
 * Will be run at each include('openHarmony.js') statement.
 */
$.clearOpenHarmonyCache = function(){
  // clear cache at openHarmony loading.
  for (var classItem in this.$){
    var ohClass = this.$[classItem]
    if (typeof ohClass === "function" && ohClass.prototype.hasOwnProperty('__cache__')){
      ohClass.invalidateCache();
    }
  }
}
$.clearOpenHarmonyCache();


//---- Instantiate Class $ DOM Access ------
function addDOMAccess( target, item ){
  Object.defineProperty( target, '$', {
    configurable: false,
    enumerable: false,
    value: item
  });
}

//Add the context as a local member of the classes.
for( var classItem in $ ){
  if( ( typeof $[classItem] ) == "function" ){
    try{
      addDOMAccess( $[classItem].prototype, $ );
    }catch(err){
      $.debug( "Error extending DOM access to : " + classItem + ": "+err, $.DEBUG_LEVEL.ERROR );
    }

    //Also extend it to the global object.
    this[classItem] = $[classItem];
  }
}


// Add global access to $ object
this.__proto__.$ = $