"use strict"
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
//         $.oDialog class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The base class for the $.oDialog.
 * @classdesc
 * $.oDialog Base Class -- helper class for showing GUI content.
 * @constructor
 */
$.oDialog = function( ){
}


/**
 * Prompts with a confirmation dialog (yes/no choice).
 * @name    $.oDialog#confirm
 * @function
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText]                 The text on the OK button of the dialog.
 * @param   {string}           [cancelButtonText]             The text on the CANCEL button of the dialog.
 *
 * @return  {bool}       Result of the confirmation dialog.
 */

$.oDialog.prototype.confirm = function( labelText, title, okButtonText, cancelButtonText ){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.confirm not supported in batch mode", this.$.DEBUG_LEVEL.WARNING)
    return;
  }

  if (typeof labelText === 'undefined')        var labelText = false;
  if (typeof title === 'undefined')            var title = "Confirmation";
  if (typeof okButtonText === 'undefined')     var okButtonText = "OK";
  if (typeof cancelButtonText === 'undefined') var cancelButtonText = "Cancel";

  var d = new Dialog();
      d.title            = title;
      d.okButtonText     = okButtonText;
      d.cancelButtonText = cancelButtonText;

  if( labelText ){
    var label = new Label;
    label.text = labelText;
  }

  d.add( label );

  if ( !d.exec() ){
    return false;
  }

  return true;
}


/**
 * Prompts with an alert dialog (informational).
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText]                 The text on the OK button of the dialog.
 *
 */
$.oDialog.prototype.alert = function( labelText, title, okButtonText ){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.alert not supported in batch mode", this.$.DEBUG_LEVEL.WARNING)
    return;
  }

  if (typeof labelText === 'undefined') var labelText = "Alert!";
  if (typeof title === 'undefined') var title = "Alert";
  if (typeof okButtonText === 'undefined') var okButtonText = "OK";

  this.$.debug(labelText, this.$.DEBUG_LEVEL.LOG)

  var d = new QMessageBox( false, title, labelText, QMessageBox.Ok );
  d.setWindowTitle( title );

  d.buttons()[0].text = okButtonText;

  if( labelText ){
    d.text = labelText;
  }

  if ( !d.exec() ){
    return;
  }
}


/**
 * Prompts with an alert dialog with a text box which can be selected (informational).
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [okButtonText="OK"]            The text on the OK button of the dialog.
 * @param   {bool}             [htmlSupport=false]
 */
$.oDialog.prototype.alertBox = function( labelText, title, okButtonText, htmlSupport){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.alert not supported in batch mode", this.$.DEBUG_LEVEL.WARNING)
    return;
  }

  if (typeof labelText === 'undefined') var labelText = "";
  if (typeof title === 'undefined') var title = "";
  if (typeof okButtonText === 'undefined') var okButtonText = "OK";
  if (typeof htmlSupport === 'undefined') var htmlSupport = false;

  this.$.debug(labelText, this.$.DEBUG_LEVEL.LOG)

  var d = new QDialog();

  if (htmlSupport){
    var label = new QTextEdit(labelText + "");
  }else{
    var label = new QPlainTextEdit(labelText + "");
  }
  label.readOnly = true;

  var button = new QPushButton(okButtonText);

  var layout = new QVBoxLayout(d);
  layout.addWidget(label, 1, Qt.Justify);
  layout.addWidget(button, 0, Qt.AlignHCenter);

  d.setWindowTitle( title );
  button.clicked.connect(d.accept);

  d.exec();
}


/**
 * Prompts with an toast alert. This is a small message that can't be clicked and only stays on the screen for the duration specified.
 * @param   {string}         labelText          The label/internal text of the dialog.
 * @param   {$.oPoint}       [position]         The position on the screen where the toast will appear (by default, slightly under the middle of the screen).
 * @param   {float}          [duration=2000]    The duration of the display (in milliseconds).
 * @param   {$.oColorValue}  [color="#000000"]  The color of the background (a 50% alpha value will be applied).
 */
$.oDialog.prototype.toast = function(labelText, position, duration, color){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.alert not supported in batch mode", this.$.DEBUG_LEVEL.WARNING);
    return;
  }

  if (typeof duration === 'undefined') var duration = 2000;
  if (typeof color === 'undefined') var color = new $.oColorValue(0,0,0);
  if (typeof position === 'undefined'){
    var center = QApplication.desktop().screen().rect.center();
    var position = new $.oPoint(center.x(), center.y()+UiLoader.dpiScale(150))
  }

  var toast = new QWidget()
  var flags = new Qt.WindowFlags(Qt.Popup|Qt.FramelessWindowHint|Qt.WA_TransparentForMouseEvents);
  toast.setWindowFlags(flags);
  toast.setAttribute(Qt.WA_TranslucentBackground);
  toast.setAttribute(Qt.WA_DeleteOnClose);

  var styleSheet = "QWidget {" +
  "background-color: rgba("+color.r+", "+color.g+", "+color.b+", 50%); " +
  "color: white; " +
  "border-radius: "+UiLoader.dpiScale(10)+"px; " +
  "padding: "+UiLoader.dpiScale(10)+"px; " +
  "font-family: Arial; " +
  "font-size: "+UiLoader.dpiScale(12)+"pt;}"

  toast.setStyleSheet(styleSheet);

  var layout = new QHBoxLayout(toast);
  layout.addWidget(new QLabel(labelText), 0, Qt.AlignHCenter);

  var timer = new QTimer()
  timer.singleShot = true;
  timer.timeout.connect(this, function(){
    toast.close();
  })

  toast.show();

  toast.move(position.x-toast.width/2, position.y);

  timer.start(duration);
}


/**
 * Prompts for a user input.
 * @param   {string}           [labelText]                    The label/internal text of the dialog.
 * @param   {string}           [title]                        The title of the confirmation dialog.
 * @param   {string}           [prefilledText]                The text to display in the input area.
 *
 */
$.oDialog.prototype.prompt = function( labelText, title, prefilledText){
  if (typeof labelText === 'undefined') var labelText = "enter value :";
  if (typeof title === 'undefined') var title = "Prompt";
  if (typeof prefilledText === 'undefined') var prefilledText = "";
  return Input.getText(labelText, prefilledText, title);
}


/**
 * Prompts with a file selector window
 * @param   {string}           [text="Select a file:"]       The title of the confirmation dialog.
 * @param   {string}           [filter="*"]                  The filter for the file type and/or file name that can be selected. Accepts wildcard charater "*".
 * @param   {string}           [getExisting=true]            Whether to select an existing file or a save location
 * @param   {string}           [acceptMultiple=false]        Whether or not selecting more than one file is ok. Is ignored if getExisting is falses.
 * @param   {string}           [startDirectory]              The directory showed at the opening of the dialog.
 *
 * @return  {string[]}         The list of selected Files, 'undefined' if the dialog is cancelled
 */
$.oDialog.prototype.browseForFile = function( text, filter, getExisting, acceptMultiple, startDirectory){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.browseForFile not supported in batch mode", this.$.DEBUG_LEVEL.WARNING)
    return;
  }

  if (typeof title === 'undefined') var title = "Select a file:";
  if (typeof filter === 'undefined') var filter = "*"
  if (typeof getExisting === 'undefined') var getExisting = true;
  if (typeof acceptMultiple === 'undefined') var acceptMultiple = false;


  if (getExisting){
    if (acceptMultiple){
      var _files = QFileDialog.getOpenFileNames(0, text, startDirectory, filter);
    }else{
      var _files = QFileDialog.getOpenFileName(0, text, startDirectory, filter);
    }
  }else{
    var _files = QFileDialog.getSaveFileName(0, text, startDirectory, filter);
  }

  for (var i in _files){
    _files[i] = _files[i].replace(/\\/g, "/");
  }

  this.$.debug(_files);
  return _files;
}


/**
 * Prompts with a browse for folder dialog (informational).
 * @param   {string}           [text]                        The title of the confirmation dialog.
 * @param   {string}           [startDirectory]              The directory showed at the opening of the dialog.
 *
 * @return  {string}           The path of the selected folder, 'undefined' if the dialog is cancelled
 */
$.oDialog.prototype.browseForFolder = function(text, startDirectory){
  if (this.$.batchMode) {
    this.$.debug("$.oDialog.browseForFolder not supported in batch mode", this.$.DEBUG_LEVEL.WARNING)
    return;
  }

  if (typeof title === 'undefined') var title = "Select a folder:";

  var _folder = QFileDialog.getExistingDirectory(0, text, startDirectory);
  _folder = _folder.split("\\").join("/");
  // this.$.alert(_folder)
  return _folder;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//     $.oProgressDialog class      //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oProgressDialog constructor.
 * @name        $.oProgressDialog
 * @constructor
 * @classdesc   An simple progress dialog to display the progress of a task.
 * To react to the user clicking the cancel button, connect a function to $.oProgressDialog.canceled() signal.
 * When $.batchmode is true, the progress will be outputed as a "Progress : value/range" string to the Harmony stdout.
 * @param       {string}              [labelText]                The text displayed above the progress bar.
 * @param       {string}              [range=100]                The maximum value that represents a full progress bar.
 * @param       {string}              [title]                    The title of the dialog
 * @param       {bool}                [show=false]               Whether to immediately show the dialog.
 *
 * @property    {bool}                wasCanceled                Whether the progress bar was cancelled.
 * @property    {$.oSignal}           canceled                   A Signal emited when the dialog is canceled. Can be connected to a callback.
 */
$.oProgressDialog = function( labelText, range, title, show ){
  if (typeof title === 'undefined') var title = "Progress";
  if (typeof range === 'undefined') var range = 100;
  if (typeof labelText === 'undefined') var labelText = "";

  this._value = 0;
  this._range = range;
  this._title = title;
  this._labelText = labelText;

  this.canceled = new this.$.oSignal();
  this.wasCanceled = false;

  if (!this.$.batchMode) {
    this.progress = new QProgressDialog();
    this.progress.title = this._title;
    this.progress.setLabelText( this._labelText );
    this.progress.setRange( 0, this._range );
    this.progress.setWindowFlags(Qt.Popup|Qt.WindowStaysOnTopHint)

    this.progress["canceled()"].connect( this, function(){this.wasCanceled = true; this.canceled.emit()} );

    if (show) this.show();
  }
}


// legacy compatibility
$.oDialog.Progress = $.oProgressDialog;


/**
 * The text displayed by the window.
 * @name $.oProgressDialog#label
 * @type {string}
 */
Object.defineProperty( $.oProgressDialog.prototype, 'label', {
  get: function(){
    return this._labelText;
  },
  set: function( val ){
    this._labelText = val;
    if (!this.$.batchMode) this.progress.setLabelText( val );
  }
});


/**
 * The maximum value that can be displayed by the progress dialog (equivalent to "finished")
 * @name $.oProgressDialog#range
 * @type {int}
 */
Object.defineProperty( $.oProgressDialog.prototype, 'range', {
    get: function(){
      return this._range;
    },
    set: function( val ){
      this._range = val;
      if (!this.$.batchMode) this.progress.setRange( 0, val );
    }
});


/**
 * The current value of the progress bar. Setting this to the value of 'range' will close the dialog.
 * @name $.oProgressDialog#value
 * @type {int}
 */
Object.defineProperty( $.oProgressDialog.prototype, 'value', {
    get: function(){
      return this._value;
    },
    set: function( val ){
      if (val > this.range) val = this.range;
      this._value = val;
      if (this.$.batchMode) {
        this.$.log("Progress : "+val+"/"+this._range)
      }else {
        this.progress.value = val;
      }

      // update the widget appearance
      QCoreApplication.processEvents();
    }
});


/**
 * Whether the Progress Dialog was cancelled by the user.
 * @name $.oProgressDialog#cancelled
 * @deprecated use $.oProgressDialog.wasCanceled to get the cancel status, or connect a function to the "canceled" signal.
 */
Object.defineProperty( $.oProgressDialog.prototype, 'cancelled', {
  get: function(){
    return this.wasCanceled;
  }
});


// oProgressDialog Class Methods

/**
 * Shows the dialog.
 */
$.oProgressDialog.prototype.show = function(){
  if (this.$.batchMode) {
    this.$.debug("$.oProgressDialog not supported in batch mode", this.$.DEBUG_LEVEL.ERROR)
    return;
  }

  this.progress.show();
}

/**
 * Closes the dialog.
 */
$.oProgressDialog.prototype.close = function(){
  this.value = this.range;
  this.$.log("Progress : "+this.value+"/"+this._range)

  if (this.$.batchMode) {
    this.$.debug("$.oProgressDialog not supported in batch mode", this.$.DEBUG_LEVEL.ERROR)
    return;
  }

  this.canceled.blocked = true;
  this.progress.close();
  this.canceled.blocked = false;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oPieMenu class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oPieMenu constructor.
 * @name        $.oPieMenu
 * @constructor
 * @classdesc   A type of menu with nested levels that appear around the mouse
 * @param       {string}              name                    The name for this pie Menu.
 * @param       {QWidget[]}           [widgets]               The widgets to display in the menu.
 * @param       {bool}                [show=false]            Whether to immediately show the dialog.
 * @param       {float}               [minAngle]              The low limit of the range of angles used by the menu, in multiples of PI (0 : left, 0.5 : top, 1 : right, -0.5 : bottom)
 * @param       {float}               [maxAngle]              The high limit of the  range of angles used by the menu, in multiples of PI (0 : left, 0.5 : top, 1 : right, -0.5 : bottom)
 * @param       {float}               [radius]                The radius of the menu.
 * @param       {$.oPoint}            [position]              The central position of the menu.
 *
 * @property    {string}              name                    The name for this pie Menu.
 * @property    {QWidget[]}           widgets                 The widgets to display in the menu.
 * @property    {float}               minAngle                The low limit of the range of angles used by the menu, in multiples of PI (0 : left, 0.5 : top, 1 : right, -0.5 : bottom)
 * @property    {float}               maxAngle                The high limit of the  range of angles used by the menu, in multiples of PI (0 : left, 0.5 : top, 1 : right, -0.5 : bottom)
 * @property    {float}               radius                  The radius of the menu.
 * @property    {$.oPoint}            position                The central position of the menu or button position for imbricated menus.
 * @property    {QWidget}             menuWidget              The central position of the menu or button position for imbricated menus.
 * @property    {QColor}              sliceColor              The color of the slices. Can set to any fill type accepted by QBrush
 * @property    {QColor}              backgroundColor         The background of the menu. Can set to any fill type accepted by QBrush
 * @property    {QColor}              linesColor              The color of the lines.
 * @example
// This example function creates a menu full of generated push buttons with callbacks, but any type of widget can be added.
// Normally it doesn't make sense to create buttons this way, and they will be created one by one to cater to specific needs,
// such as launching Harmony actions, or scripts, etc. Assign this function to a shortcut by creating a Harmony Package for it.

function openMenu(){
  MessageLog.clearLog()

  // we create a list of tool widgets for our submenu
  var toolSubMenuWidgets = [
    new $.oToolButton("select"),
    new $.oToolButton("brush"),
    new $.oToolButton("pencil"),
    new $.oToolButton("eraser"),
  ];
  // we initialise our submenu
  var toolSubMenu = new $.oPieSubMenu("tools", toolSubMenuWidgets);

  // we create a list of tool widgets for our submenu
  // (check out the scripts from http://raindropmoment.com and http://www.cartoonflow.com, they are great!)
  var ScriptSubMenuWidgets = [
    new $.oScriptButton(specialFolders.userScripts + "/CF_CopyPastePivots_1.0.1.js", "CF_CopyPastePivots" ),
    new $.oScriptButton(specialFolders.userScripts + "/ANM_Paste_In_Place.js", "ANM_Paste_In_Place"),
    new $.oScriptButton(specialFolders.userScripts + "/ANM_Set_Layer_Pivots_At_Center_Of_Drawings.js", "ANM_Set_Layer_Pivots_At_Center_Of_Drawings"),
    new $.oScriptButton(specialFolders.userScripts + "/DEF_Copy_Deformation_Values_To_Resting.js", "DEF_Copy_Deformation_Values_To_Resting"),
  ];
  var scriptsSubMenu = new $.oPieSubMenu("scripts", ScriptSubMenuWidgets);

  // we create a list of color widgets for our submenu
  var colorSubMenuWidgets = []
  var currentPalette = $.scn.selectedPalette
  var colors = currentPalette.colors
  for (var i in colors){
    colorSubMenuWidgets.push(new $.oColorButton(currentPalette.name, colors[i].name));
  }
  var colorSubMenu = new $.oPieSubMenu("colors", colorSubMenuWidgets);

  onionSkinSlider = new QSlider(Qt.Horizontal)
  onionSkinSlider.minimum = 0;
	onionSkinSlider.maximum = 256;
  onionSkinSlider.valueChanged.connect(function(value){
    preferences.setDouble("DRAWING_ONIONSKIN_MAX_OPACITY",
      value/256.0);
    view.refreshViews();
  })

  // widgets that will appear in the main menu
  var mainWidgets = [
    onionSkinSlider,
    toolSubMenu,
    colorSubMenu,
    scriptsSubMenu
  ]

  // we initialise our main menu. The numerical values are for the minimum and maximum angle of the
  // circle in multiples of Pi. Going clockwise, 0 is right, 1 is left, -0.5 is the bottom from the right,
  // and 1.5 is the bottom from the left side. 0.5 is the top of the circle.
  var menu = new $.oPieMenu("menu", mainWidgets, false, -0.2, 1.2);

  // configurating the look of it
  // var backgroundGradient = new QRadialGradient (menu.center, menu.maxRadius);
  // var menuBg = menu.backgroundColor
  // backgroundGradient.setColorAt(1, new QColor(menuBg.red(), menuBg.green(), menuBg.blue(), 255));
  // backgroundGradient.setColorAt(0, menuBg);

  // var sliceGradient = new QRadialGradient (menu.center, menu.maxRadius);
  // var menuColor = menu.sliceColor
  // sliceGradient.setColorAt(1, new QColor(menuColor.red(), menuColor.green(), menuColor.blue(), 20));
  // sliceGradient.setColorAt(0, menuColor);

  // menu.backgroundColor = backgroundGradient
  // menu.sliceColor = sliceGradient

  // we show it!
  menu.show();
}*/
$.oPieMenu = function( name, widgets, show, minAngle, maxAngle, radius, position, parent){
  this.name = name;
  this.widgets = widgets;

  if (typeof minAngle === 'undefined') var minAngle = 0;
  if (typeof maxAngle === 'undefined') var maxAngle = 1;
  if (typeof radius === 'undefined') var radius = this.getMenuRadius();
  if (typeof position === 'undefined') var position = this.$.app.globalMousePosition;
  if (typeof show === 'undefined') var show = false;
  if (typeof parent === 'undefined') var parent = this.$.app.mainWindow;
  this._parent = parent;

  // close all previously opened piemenu widgets
  if (!$._piemenu) $._piemenu = []
  while ($._piemenu.length){
    var pie = $._piemenu.pop();
    if (pie){
      // a menu was already open, we close it
      pie.closeMenu()
    }
  }

  QWidget.call(this, parent)
  this.objectName = "pieMenu_" + name;
  $._piemenu.push(this)

  this.radius = radius;
  this.minAngle = minAngle;
  this.maxAngle = maxAngle;
  this.globalCenter = position;

  // how wide outisde the icons is the slice drawn
  this._circleMargin = 30;

  // set these values before calling show() to customize the menu appearance
  this.sliceColor = new QColor(0, 200, 255, 200);
  this.backgroundColor = new QColor(40, 40, 40, 180);
  this.linesColor = new QColor(0,0,0,0);

  // create main button
  this.button = this.buildButton()

  // add buildWidget call before show(),
  // for some reason show() is not in QWidget.prototype ?
  this.qWidgetShow = this.show
  this.show = function(){
    this.buildWidget()
  }

  this.focusPolicy = Qt.StrongFocus;
  this.focusOutEvent = function(){
    this.deactivate()
  }

  var menu = this;
  this.button.clicked.connect(function(){return menu.deactivate()})

  if (show) this.show();
}
$.oPieMenu.prototype = Object.create(QWidget.prototype);


/**
 * function run when the menu button is clicked
 */
$.oPieMenu.prototype.deactivate = function(){
  this.closeMenu()
}

/**
 * Closes the menu and all its subWidgets
 * @private
 */
$.oPieMenu.prototype.closeMenu = function(){
  for (var i in this.widgets){
    this.widgets[i].close()
  }
  this.close();
}

/**
 * The top left point of the entire widget
 * @name $.oPieMenu#anchor
 * @type {$.oPoint}
 */
Object.defineProperty($.oPieMenu.prototype, "anchor", {
  get: function(){
    var point = this.globalCenter.add(-this.center.x, -this.center.y);
    return point;
  }
})


/**
 * The center of the entire widget
 * @name $.oPieMenu#center
 * @type {$.oPoint}
 */
Object.defineProperty($.oPieMenu.prototype, "center", {
  get: function(){
    return new this.$.oPoint(this.widgetSize/2, this.widgetSize/2)
  }
})


/**
 * The min radius of the pie background
 * @name $.oPieMenu#minRadius
 * @type {int}
 */
Object.defineProperty($.oPieMenu.prototype, "minRadius", {
  get: function(){
    return this._circleMargin;
  }
})


/**
 * The max radius of the pie background
 * @name $.oPieMenu#maxRadius
 * @type {int}
 */
Object.defineProperty($.oPieMenu.prototype, "maxRadius", {
  get: function(){
    return this.radius + this._circleMargin;
  }
})

/**
 * The widget size of the pie background (it's a square so it's both the width and the height.)
 * @name $.oPieMenu#widgetSize
 * @type {int}
 */
 Object.defineProperty($.oPieMenu.prototype, "widgetSize", {
  get: function(){
    return this.maxRadius*4;
  }
})


/**
 * Builds the menu's main button.
 * @returns {$.oPieButton}
 */
$.oPieMenu.prototype.buildButton = function(){
  // add main button in constructor because it needs to exist before show()
  var icon = specialFolders.resource + "/icons/brushpreset/defaultpresetellipse/ellipse03.svg"
  button = new this.$.oPieButton(icon, "", this);
  button.objectName = this.name+"_button";
  button.parentMenu = this;

  return button;
}

/**
 * Build and show the pie menu and its widgets.
 * @private
 */
$.oPieMenu.prototype.buildWidget = function(){
  // match the widget geometry with the main window/parent
  var anchor = this.anchor
  this.move(anchor.x, anchor.y);
  this.minimumHeight = this.maximumHeight = this.widgetSize;
  this.minimumWidth = this.maximumWidth = this.widgetSize;

  var flags = new Qt.WindowFlags(Qt.Popup|Qt.FramelessWindowHint|Qt.WA_TransparentForMouseEvents);
  this.setWindowFlags(flags);
  this.setAttribute(Qt.WA_TranslucentBackground);
  this.setAttribute(Qt.WA_DeleteOnClose);

  // draw background pie slice
  this.slice = this.drawSlice();
  this.qWidgetShow()
  // arrange widgets into half a circle around the center
  var center = this.center;

  for (var i=0; i < this.widgets.length; i++){
    var widget = this.widgets[i];
    widget.pieIndex = i;
    widget.setParent(this);

    var itemPosition = this.getItemPosition(i);
    var widgetPosition = new this.$.oPoint(center.x + itemPosition.x, center.y + itemPosition.y);

    widget.show();
    widget.move(widgetPosition.x - widget.width/2, widgetPosition.y - widget.height/2);
  }

  this.button.show();
  this.button.move(center.x - (this.button.width/2), center.y - (this.button.height/2));
}


/**
 * draws a background transparent slice and set up the mouse tracking.
 * @param {int}   [minRadius]      specify a minimum radius for the slice
 * @private
 */
$.oPieMenu.prototype.drawSlice = function(){
  var index = 0;

  // get the slice and background geometry
  var center = this.center;
  var angleSlice = this.getItemAngleRange(index);
  var slicePath = this.getSlicePath(center, angleSlice[0], angleSlice[1], this.minRadius, this.maxRadius);
  var contactPath = this.getSlicePath(center, this.minAngle, this.maxAngle, this.minRadius, this.maxRadius);

  // create a widget to paint into
  var sliceWidget = new QWidget(this);
  sliceWidget.objectName = "slice";
  // make widget background invisible
  sliceWidget.setStyleSheet("background-color: rgba(0, 0, 0, 0.5%);");
  var flags = new Qt.WindowFlags(Qt.FramelessWindowHint);
  sliceWidget.setWindowFlags(flags)
  sliceWidget.minimumHeight = this.height;
  sliceWidget.minimumWidth = this.width;
  sliceWidget.lower();

  var sliceWidth = angleSlice[1]-angleSlice[0];

  // painting the slice on sliceWidget.update()
  var sliceColor = this.sliceColor;
  var backgroundColor = this.backgroundColor;
  var linesColor = this.linesColor;

  sliceWidget.paintEvent = function(){
    var painter = new QPainter();
    painter.save();
    painter.begin(sliceWidget);

    // draw background
    painter.setRenderHint(QPainter.Antialiasing);
    painter.setPen(new QPen(linesColor));
    painter.setBrush(new QBrush(backgroundColor));

    painter.drawPath(contactPath);

    // draw slice and rotate around widget center
    painter.translate(center.x, center.y);
    painter.rotate(sliceWidth*index*(-180));
    painter.translate(-center.x, -center.y);
    painter.setPen(new QPen(linesColor));
    painter.setBrush(new QBrush(sliceColor));
    painter.drawPath(slicePath);
    painter.end();
    painter.restore();
  }

  //set up automatic following of the mouse
  sliceWidget.mouseTracking = true;

  var pieMenu = this;
  var currentDistance = false;
  sliceWidget.mouseMoveEvent = function(mousePos){
    // work out the index based on relative position to the center
    var position = new pieMenu.$.oPoint(mousePos.x(), mousePos.y());
    var angle = -position.add(-center.x, -center.y).polarCoordinates.angle/Math.PI;
    if (angle < (-0.5)) angle += 2; // our coordinates system uses continuous angle values with cutoff at the bottom (1.5/-0.5)
    var currentIndex = pieMenu.getIndexAtAngle(angle);
    var distance = position.distance(center);

    // on distance value change, if the distance is greater than the maxRadius, activate the widget
    var indexChanged = (index != currentIndex)
    var indexWithinRange = (currentIndex >= 0 && currentIndex < pieMenu.widgets.length)
    var distanceWithinRange = (distance > pieMenu.minRadius && distance < pieMenu.maxRadius)
    var distanceChanged = (distanceWithinRange != currentDistance)

    // react to distance/angle change when the mouse moves on the pieMenu
    if (indexWithinRange){
      var indexWidget = pieMenu.widgets[currentIndex];

      if (indexChanged && distance < pieMenu.maxRadius){
        index = currentIndex;
        sliceWidget.update();
        indexWidget.setFocus(true);
      }

      if (distanceChanged){
        currentDistance = distanceWithinRange;
        if (distance > pieMenu.maxRadius){
          // activate the button
          if (indexWidget.activate) indexWidget.activate();
        }else if (distance < pieMenu.minRadius){
          // cursor reentered the widget: close the subMenu
          if (indexWidget.deactivate) indexWidget.deactivate();
        }
        if (distance < pieMenu.minRadius){
          if (pieMenu.deactivate) pieMenu.deactivate();
        }
      }
    }
  }

  return sliceWidget;
}


/**
 * Generate a pie slice path to draw based on parameters
 * @param {$.oPoint}    center      the center of the slice
 * @param {float}       minAngle    a value between -0.5 and 1.5 for the lowest angle value for the pie slice
 * @param {float}       maxAngle    a value between -0.5 and 1.5 for the highest angle value for the pie slice
 * @param {float}       minRadius   the smallest circle radius
 * @param {float}       maxRadius   the largest circle radius
 * @private
 */
$.oPieMenu.prototype.getSlicePath = function(center, minAngle, maxAngle, minRadius, maxRadius){
  // work out the geometry
  var smallArcBoundingBox = new QRectF(center.x-minRadius, center.y-minRadius, minRadius*2, minRadius*2);
  var smallArcStart = new this.$.oPoint();
  smallArcStart.polarCoordinates = {radius: minRadius, angle:minAngle*(-Math.PI)}
  smallArcStart.translate(center.x, center.y);
  var smallArcAngleStart = minAngle*180;
  var smallArcSweep = (maxAngle-minAngle)*180; // convert values from 0-2 (radiant angles in multiples of pi) to degrees

  var bigArcBoundingBox = new QRectF(center.x-maxRadius, center.y-maxRadius, maxRadius*2, maxRadius*2);
  var bigArcAngleStart = maxAngle*180;
  var bigArcSweep = -smallArcSweep;

  // we draw the slice path
  var slicePath = new QPainterPath;
  slicePath.moveTo(new QPointF(smallArcStart.x, smallArcStart.y));
  slicePath.arcTo(smallArcBoundingBox, smallArcAngleStart, smallArcSweep);
  slicePath.arcTo(bigArcBoundingBox, bigArcAngleStart, bigArcSweep);

  return slicePath;
}


/**
 * Get the angle range for the item pie slice based on index.
 * @private
 * @param {int}     index         the index of the widget
 * @return {float[]}
 */
$.oPieMenu.prototype.getItemAngleRange = function(index){
  var length = this.widgets.length;
  var angleStart = this.minAngle+(index/length)*(this.maxAngle-this.minAngle);
  var angleEnd = this.minAngle+((index+1)/length)*(this.maxAngle-this.minAngle);

  return [angleStart, angleEnd];
}

/**
 * Get the angle for the item widget based on index.
 * @private
 * @param {int}     index         the index of the widget
 * @return {float}
 */
$.oPieMenu.prototype.getItemAngle = function(index){
  var angleRange = this.getItemAngleRange(index, this.minAngle, this.maxAngle);
  var angle = (angleRange[1] - angleRange[0])/2+angleRange[0]

  return angle;
}


/**
 * Get the widget index for the angle value.
 * @private
 * @param {float}     angle         the index of the widget
 * @return {float}
 */
$.oPieMenu.prototype.getIndexAtAngle = function(angle){
  var angleRange = (this.maxAngle-this.minAngle)/this.widgets.length
  return Math.floor((angle-this.minAngle)/angleRange);
}


/**
 * Get the position from the center for the item based on index.
 * @private
 * @param {int}     index         the index of the widget
 * @return {$.oPoint}
 */
$.oPieMenu.prototype.getItemPosition = function(index){
  // we add pi to the angle because of the inverted Y axis of widgets coordinates
  var pi = Math.PI;
  var angle = this.getItemAngle(index, this.minAngle, this.maxAngle)*(-pi);
  var _point = new this.$.oPoint();
  _point.polarCoordinates = {radius:this.radius, angle:angle}

  return _point;
}


/**
 * Get a pie menu radius setting for a given amount of items.
 * @private
 * @return {float}
 */
$.oPieMenu.prototype.getMenuRadius = function(){
  var itemsNumber = this.widgets.length
  var _maxRadius = UiLoader.dpiScale(200);
  var _minRadius = UiLoader.dpiScale(30);
  var _speed = 10; // the higher the value, the slower the progression

  // hyperbolic tangent function to determin the radius
  var exp = Math.exp(2*itemsNumber/_speed);
  var _radius = ((exp-1)/(exp+1))*_maxRadius+_minRadius;

  return _radius;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oPieSubMenu class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oPieSubMenu constructor.
 * @name        $.oPieSubMenu
 * @constructor
 * @classdesc   A menu with more options that opens/closes when the user clicks on the button.
 * @param       {string}              name                     The name for this pie Menu.
 * @param       {QWidget[]}           [widgets]                The widgets to display in the menu.
 *
 * @property    {string}              name                     The name for this pie Menu.
 * @property    {string}              widgets                  The widgets to display in the menu.
 * @property    {string}              menu                     The oPieMenu Object containing the widgets for the submenu
 * @property    {string}              itemAngle                a set angle for each items instead of spreading them across the entire circle
 * @property    {string}              extraRadius              using a set radius between each submenu levels
 * @property    {$.oPieMenu}          parentMenu               the parent menu for this subMenu. Set during initialisation of the menu.
 */
$.oPieSubMenu = function(name, widgets) {
  this.menuIcon = specialFolders.resource + "/icons/toolbar/menu.svg";
  this.closeIcon = specialFolders.resource + "/icons/toolbar/collapseopen.png";

  // min/max angle and radius will be set from parent during buildWidget()
  this.$.oPieMenu.call(this, name, widgets, false);

  // change these settings before calling show() to modify the look of the pieSubMenu
  this.itemAngle = 0.06;
  this.extraRadius = UiLoader.dpiScale(80);
  this.parentMenu = undefined;

  this.focusOutEvent = function(){} // delete focusOutEvent response from submenu
}
$.oPieSubMenu.prototype = Object.create($.oPieMenu.prototype)


/**
 * function called when main button is clicked
 */
$.oPieSubMenu.prototype.deactivate = function(){
  this.toggleMenu()
}

/**
 * The top left point of the entire widget
 * @name $.oPieSubMenu#anchor
 * @type {$.oPoint}
 */
Object.defineProperty($.oPieSubMenu.prototype, "anchor", {
  get: function(){
    var center = this.parentMenu.globalCenter;
    return center.add(-this.widgetSize/2, -this.widgetSize/2);
  }
})


/**
 * The min radius of the pie background
 * @name $.oPieSubMenu#minRadius
 * @type {int}
 */
Object.defineProperty($.oPieSubMenu.prototype, "minRadius", {
  get: function(){
    return this.parentMenu.maxRadius;
  }
})


/**
 * The max radius of the pie background
 * @name $.oPieSubMenu#maxRadius
 * @type {int}
 */
Object.defineProperty($.oPieSubMenu.prototype, "maxRadius", {
  get: function(){
    return this.minRadius + this.extraRadius;
  }
})


/**
 * activate the menu button when activate() is called on the menu
 * @private
 */
$.oPieSubMenu.prototype.activate = function(){
  this.showMenu(true);
  this.setFocus(true)
}


/**
 * In order for pieSubMenus to behave like other pie widgets, we reimplement
 * move() so that it only moves the button, and the slice will remain aligned with
 * the parent.
 * @param  {int}      x     The x coordinate for the button relative to the piewidget
 * @param  {int}      y     The x coordinate for the button relative to the piewidget
 * @private
 */
$.oPieSubMenu.prototype.move = function(x, y){
  // move the actual widget to its anchor, but move the button instead
  QWidget.prototype.move.call(this, this.anchor.x, this.anchor.y);

  // calculate the actual position for the button as if it was a child of the pieMenu
  // whereas it uses global coordinates
  var buttonPos = new this.$.oPoint(x, y)
  var parentAnchor = this.parentMenu.anchor;
  var anchorDiff = parentAnchor.add(-this.anchor.x, -this.anchor.y)
  var localPos = buttonPos.add(anchorDiff.x, anchorDiff.y)

  // move() is used by the pieMenu with half the widget size to center the button, so we have to cancel it out
  this.button.move(localPos.x+this.widgetSize/2-this.button.width/2, localPos.y+this.widgetSize/2-this.button.height/2 );
}


/**
 * sets a parent and assigns it to this.parentMenu.
 * using the normal setParent from QPushButton creates a weird bug
 * where calling parent() returns a QWidget and not a $.oPieButton
 * @private
 */
$.oPieSubMenu.prototype.setParent = function(parent){
  $.oPieMenu.prototype.setParent.call(this, parent);
  this.parentMenu = parent;
}


/**
 * build the main button for the menu
 * @private
 * @returns {$.oPieButton}
 */
$.oPieSubMenu.prototype.buildButton = function(){
  // add main button in constructor because it needs to exist before show()
  var button = new this.$.oPieButton(this.menuIcon, this.name, this);
  button.objectName = this.name+"_button";

  return button;
}


/**
 * Shows or hides the menu itself (not the button)
 * @param {*} visibility
 */
$.oPieSubMenu.prototype.showMenu = function(visibility){
  this.slice.visible = visibility;
  for (var i in this.widgets){
    this.widgets[i].visible = visibility;
  }
  var icon = visibility?this.closeIcon:this.menuIcon;
  UiLoader.setSvgIcon(this.button, icon);
}


/**
 * toggles the display of the menu
 */
$.oPieSubMenu.prototype.toggleMenu = function(){
  this.showMenu(!this.slice.visible);
}

/**
 * Function to initialise the widgets for the submenu
 * @private
 */
$.oPieSubMenu.prototype.buildWidget = function(){
  if (!this.parentMenu){
    throw new Error("must set parent first before calling $.oPieMenu.buildWidget()")
  }
  parentWidget = this.parentMenu;

  // submenu widgets calculate their range from to go on both sides of the button, at a fixed angle
  // (in order to keep the span of submenu options centered around the menu button)
  var widgetNum = this.widgets.length/2;
  var angle = parentWidget.getItemAngle(this.pieIndex);

  // create the submenu on top of the main menu
  this.radius = parentWidget.radius+this.extraRadius;
  this.minAngle = angle-widgetNum*this.itemAngle;
  this.maxAngle = angle+widgetNum*this.itemAngle;

  $.oPieMenu.prototype.buildWidget.call(this);

  this.showMenu(false)
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oPieButton class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oPieButton
 * @constructor
 * @classdesc This subclass of QPushButton provides an easy way to create a button for a PieMenu.<br>
 *
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   iconFile               The icon file for the button
 * @param {string}   text                   A text to display next to the icon
 * @param {QWidget}  parent                 The parent QWidget for the button. Automatically set during initialisation of the menu.
 *
 */
 $.oPieButton = function(iconFile, text, parent) {
  // if icon isnt provided
  if (typeof parent === 'undefined') var parent = $.app.mainWindow
  if (typeof text === 'undefined') var text = ""
  if (typeof iconFile === 'undefined') var iconFile = specialFolders.resource+"/icons/script/qtgeneric.svg"

  QPushButton.call(this, text, parent);

  this.minimumHeight = 24;
  this.minimumWidth = 24;

  // set during addition to the pie Menu
  this.pieIndex = undefined;

  UiLoader.setSvgIcon(this, iconFile)
  this.setIconSize(new QSize(this.minimumWidth, this.minimumHeight));
  this.cursor = new QCursor(Qt.PointingHandCursor);

  var styleSheet = "QPushButton{ background-color: rgba(0, 0, 0, 1%); }" +
  "QPushButton:hover{ background-color: rgba(0, 200, 255, 80%); }"+
  "QToolTip{ background-color: rgba(0, 255, 255, 100%); }"
  this.setStyleSheet(styleSheet);

  var button = this;
  this.clicked.connect(function(){button.activate()})
}
$.oPieButton.prototype = Object.create(QPushButton.prototype);


/**
 * Closes the parent menu of the button and all its subWidgets.
 */
$.oPieButton.prototype.closeMenu = function(){
  var menu = this.parentMenu;
  while (menu && menu.parentMenu){
    menu = menu.parentMenu;
  }
  menu.closeMenu()
}

/**
 * Reimplement this function in order to activate the button and also close the menu.
 */
$.oPieButton.prototype.activate = function(){
  // reimplement to change the behavior when the button is activated.
  // by default, will just close the menu.
  this.closeMenu();
}


/**
 * sets a parent and assigns it to this.parentMenu.
 * using the normal setParent from QPushButton creates a weird bug
 * where calling parent() returns a QWidget and not a $.oPieButton
 * @private
 */
$.oPieButton.prototype.setParent = function(parent){
  QPushButton.prototype.setParent.call(this, parent);
  this.parentMenu = parent;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oToolButton class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oToolButton
 * @name          $.oToolButton
 * @constructor
 * @classdescription This subclass of QPushButton provides an easy way to create a button for a tool.
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   toolName               The path to the script file that will be launched
 * @param {string}   scriptFunction           The function name to launch from the script
 * @param {QWidget}  parent                   The parent QWidget for the button. Automatically set during initialisation of the menu.
 *
 */
 $.oToolButton = function(toolName, iconFile, parent) {
  this.toolName = toolName;

  if (typeof iconFile === "undefined"){
    // find an icon for the function in the script-icons folder
    var scriptIconsFolder = new this.$.oFolder(specialFolders.resource+"/icons/drawingtool");
    var iconFiles = scriptIconsFolder.getFiles(toolName.replace(" ", "").toLowerCase() + ".*");

    if (iconFiles.length > 0){
      var iconFile = iconFiles[0].path;
    }else{
      // choose default toonboom "missing icon" script icon
      // currently svg icons seem unsupported?
      var iconFile = specialFolders.resource+"/icons/script/qtgeneric.svg";
    }
  }
  this.$.oPieButton.call(this, iconFile, parent);

  this.toolTip = this.toolName;
}
$.oToolButton.prototype = Object.create($.oPieButton.prototype);


$.oToolButton.prototype.activate = function(){
  this.$.app.currentTool = this.toolName;
  this.closeMenu()
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oActionButton class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oActionButton
 * @name          $.oActionButton
 * @constructor
 * @classdescription This subclass of QPushButton provides an easy way to create a button for a tool.
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   actionName               The action string that will be executed with Action.perform
 * @param {string}   responder                The responder for the action
 * @param {string}   text                     A text for the button display.
 * @param {string}   iconFile                 An icon path for the button.
 * @param {QWidget}  parent                   The parent QWidget for the button. Automatically set during initialisation of the menu.
 */
 $.oActionButton = function(actionName, responder, text, iconFile, parent) {
  this.action = actionName;
  this.responder = responder;

  if (typeof text === 'undefined') var text = "action";

  if (typeof iconFile === 'undefined') var iconFile = specialFolders.resource+"/icons/old/exec.png";

  this.$.oPieButton.call(this, iconFile, text, parent);
  this.toolTip = this.toolName;
}
$.oActionButton.prototype = Object.create($.oPieButton.prototype);


$.oActionButton.prototype.activate = function(){
  if (this.responder){
    // log("Validating : "+ this.actionName + " ? "+ Action.validate(this.actionName, this.responder).enabled)
    if (Action.validate(this.action, this.responder).enabled){
      Action.perform(this.action, this.responder);
    }
  }else{
    if (Action.Validate(this.action).enabled){
      Action.perform(this.action);
    }
  }
  view.refreshViews();
  this.closeMenu()
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oColorButton class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oColorButton
 * @name          $.oColorButton
 * @constructor
 * @classdescription This subclass of QPushButton provides an easy way to create a button to choose a color from a palette.
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   paletteName              The name of the palette that contains the color
 * @param {string}   colorName                The name of the color (if more than one is present, will pick the first match)
 * @param {bool}     showName                 Wether to display the name of the color on the button
 * @param {QWidget}  parent                   The parent QWidget for the button. Automatically set during initialisation of the menu.
 *
 */
 $.oColorButton = function(paletteName, colorName, showName, parent) {
  this.paletteName = paletteName;
  this.colorName = colorName;

  if (typeof showName === "undefined") var showName = false;

  this.$.oPieButton.call(this, "", showName?colorName:"", parent);

  var palette = this.$.scn.getPaletteByName(paletteName);
  var color = palette.getColorByName(colorName);
  var colorValue = color.value

  var iconMap = new QPixmap(this.minimumHeight,this.minimumHeight)
  iconMap.fill(new QColor(colorValue.r, colorValue.g, colorValue.b, colorValue.a))
  var icon = new QIcon(iconMap);

  this.icon = icon;

  this.toolTip = this.paletteName + ": " + this.colorName;
}
$.oColorButton.prototype = Object.create($.oPieButton.prototype);


$.oColorButton.prototype.activate = function(){
  var palette = this.$.scn.getPaletteByName(this.paletteName);
  var color = palette.getColorByName(this.colorName);

  this.$.scn.currentPalette = palette;
  palette.currentColor = color;
  this.closeMenu()
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oScriptButton class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oScriptButton
 * @name          $.oScriptButton
 * @constructor
 * @classdescription This subclass of QPushButton provides an easy way to create a button for a widget that will launch a function from another script file.<br>
 * The buttons created this way automatically load the icon named after the script if it finds one named like the funtion in a script-icons folder next to the script file.<br>
 * It will also automatically set the callback to lanch the function from the script.<br>
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   scriptFile               The path to the script file that will be launched
 * @param {string}   scriptFunction           The function name to launch from the script
 * @param {QWidget}  parent                   The parent QWidget for the button. Automatically set during initialisation of the menu.
 */
$.oScriptButton = function(scriptFile, scriptFunction, parent) {
  this.scriptFile = scriptFile;
  this.scriptFunction = scriptFunction;

  // find an icon for the function in the script-icons folder
  var scriptFile = new this.$.oFile(scriptFile)
  var scriptIconsFolder = new this.$.oFolder(scriptFile.folder.path+"/script-icons");
  var iconFiles = scriptIconsFolder.getFiles(scriptFunction+".*");
  if (iconFiles.length > 0){
    var iconFile = iconFiles[0].path;
  }else{
    // choose default toonboom "missing icon" script icon
    // currently svg icons seem unsupported?
    var iconFile = specialFolders.resource+"/icons/script/qtgeneric.svg";
  }

  this.$.oPieButton.call(this, iconFile, "", parent);

  this.toolTip = this.scriptFunction;
}
$.oScriptButton.prototype = Object.create($.oPieButton.prototype);

$.oScriptButton.prototype.activate = function(){
  include(this.scriptFile);
  eval(this.scriptFunction)();
  this.closeMenu()
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oPrefButton class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oPrefButton
 * @name          $.oPrefButton
 * @constructor
 * @classdescription This subclass of QPushButton provides an easy way to create a button to change a boolean preference.
 * This class is a subclass of QPushButton and all the methods from that class are available to modify this button.
 * @param {string}   preferenceString         The name of the preference to show/change.
 * @param {string}   text                     A text for the button display.
 * @param {string}   iconFile                 An icon path for the button.
 * @param {QWidget}  parent                   The parent QWidget for the button. Automatically set during initialisation of the menu.
 */
$.oPrefButton = function(preferenceString, text, iconFile, parent) {
  this.preferenceString = preferenceString;

  if (typeof iconFile === 'undefined') var iconFile = specialFolders.resource+"/icons/toolproperties/settings.svg";
  this.checkable = true;
  this.checked = preferences.getBool(preferenceString, true);

  $.oPieButton.call(this, iconFile, text, parent);

  this.toolTip = this.preferenceString;
}
$.oPrefButton.prototype = Object.create($.oPieButton.prototype);


$.oPrefButton.prototype.activate = function(){
  var value = preferences.getBool(this.preferenceString, true);
  this.checked != value;
  preferences.setBool(this.preferenceString, value);
  this.closeMenu()
}

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//      $.oStencilButton class      //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


// not currently working
$.oStencilButton = function(stencilName, parent) {
  this.stencilName = stencilName;

  var iconFile = specialFolders.resource+"/icons/brushpreset/default.svg";

  $.oPieButton.call(this, iconFile, stencilName, parent);

  this.toolTip = stencilName;
}
$.oStencilButton.prototype = Object.create($.oPieButton.prototype);

$.oStencilButton.prototype.activate = function(){
  this.$.app.currentStencil = this.stencilName;

  this.closeMenu()
}
