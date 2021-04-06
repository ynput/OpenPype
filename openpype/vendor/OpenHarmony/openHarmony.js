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
  batchMode : false,

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
 * @name    $#browseForFile
 * @param   {string}           [text="Select a file:"]       The title of the confirmation dialog.
 * @param   {string}           [filter="*"]                  The filter for the file type and/or file name that can be selected. Accepts wildcard character "*".
 * @param   {string}           [getExisting=true]            Whether to select an existing file or a save location
 * @param   {string}           [acceptMultiple=false]        Whether or not selecting more than one file is ok. Is ignored if getExisting is false.
 * @param   {string}           [startDirectory]              The directory showed at the opening of the dialog.
 *
 * @return  {string[]}         The list of selected Files, 'undefined' if the dialog is cancelled
 */
$.browseForFile = function(){ return $.dialog.browseForFile.apply( $.dialog, arguments ) };


/**
 * Prompts with a folder selector window.
 * @function
 * @name    $#browseForFolder
 * @param   {string}           [text]                        The title of the confirmation dialog.
 * @param   {string}           [startDirectory]              The directory showed at the opening of the dialog.
 *
 * @return  {string[]}         The path of the selected folder, 'undefined' if the dialog is cancelled
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
 * @param   {string}           undoName                                       The name of the operation that is being done in the undo accum.
 * @name $#beginUndo
 * @function
 * @see $.endUndo
 */
$.beginUndo = function( undoName ){
  //Using epoch as the temp name.
  if (typeof undoName === 'undefined') var undoName = ''+((new Date()).getTime());

  scene.beginUndoRedoAccum( undoName );
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
 * @name $#endUndo
 * @function
 * @see $.beginUndo
 */
$.endUndo = function( ){
  scene.endUndoRedoAccum( );
}

/**
 * 	Undoes the last n operations. If n is not specified, it will be 1
 * @name $#undo
 * @function
 * @param   {int}           n                                       The amount of operations to undo.
 */
$.undo = function( dist ){
  if (typeof dist === 'undefined'){ var dist = 1; }
  scene.undo( dist );
}

/**
 * 	Redoes the last n operations. If n is not specified, it will be 1
 * @name $#redo
 * @function
 * @param   {int}           n                                       The amount of operations to undo.
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
$.network     = new $.oNetwork( );
$.utils       = new $.oUtils( );
$.dialog      = new $.oDialog( );
$.global      = this;


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
      $.debug( "Error extending DOM access to : " + classItem, $.DEBUG_LEVEL.ERROR );
    }

    //Also extend it to the global object.
    this[classItem] = $[classItem];
  }
}