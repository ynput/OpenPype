/**
 *  Load the Open Harmony Library as needed.
 */

try{
  var oh_incl = preferences.getString( 'openHarmonyIncludeDebug', false );
  if( oh_incl=="false" ) oh_incl = preferences.getString( 'openHarmonyInclude', false );
  if( oh_incl=="false" ) oh_incl = "openHarmony.js";
  include(oh_incl);
}catch(err){
  MessageBox.information ("OpenHarmony is not installed. Get it here: \nhttps://github.com/cfourney/OpenHarmony")
}

/**
 *  Finds and removes all unnecessary asset files from the filesystem.
 */
function oh_rigging_removeUnnecesaryPaletteFiles(){
  var palette_list = $.scene.palettes;
  var registered_palette_files = {};
  
  //Find the path of all registered palettes. Add it to a group for easy lookup.
  for( var n=0;n<palette_list.length;n++ ){
    //-- Find the files for the palettes.
    var t_pal = palette_list[n];
    registered_palette_files[ t_pal.path ] = t_pal;
    
  }
  
  //The scene path of this file.
  var scene_path = $.scene.path;
  
  //Look the all files in the plugin folder that are left over for some reason.
  
  var unreferenced_palettes = [];
  
  //Find the palette_library 
  var palette_folder = scene_path.get( "palette-library" );
  if( !palette_folder ){
    $.dialog.alert( "Palette Details", "Unable to find the palette-library." );
    return;
  }
  
  //Find all palette files within the palette folder (*.plt)
  var fls = palette_folder.files;
  for( var n=0;n<fls.length;n++ ){
    var t_fl = fls[n];
    if( t_fl.extension.toUpperCase() == "PLT" ){
      if( !registered_palette_files[ t_fl.path ] ){
        unreferenced_palettes.push( t_fl );
        
      }
    }
  }
  
  if( unreferenced_palettes.length == 0 ){
    $.dialog.alert( "Palette Details", "No unnecessary palettes to remove." );
    return;
  }
  
  //Confirm the action
  var labelText = 'Remove ' + unreferenced_palettes.length + ' unnecessary palette(s)?\n';
      for( var n=0;n<Math.min( unreferenced_palettes.length, 3 ); n++ ){
        labelText += '      '+unreferenced_palettes[n].fullName + '\n';
      }
      if( unreferenced_palettes.length>3 ){
        labelText += '\n      and '+(unreferenced_palettes.length-3)+' more . . .';
      }
      
  var confirmation = $.dialog.confirm( "Remove Palettes", labelText );
  
  if( confirmation ){
    //Delete all palettes from disk.
    var prog = new $.dialog.Progress( "Removing Palettes", unreferenced_palettes.length, true );
      
    for( var n=0;n<unreferenced_palettes.length; n++ ){
      var t_pal_fl = unreferenced_palettes[n];
      
      prog.text = "Removing: " + t_pal_fl.fullName;
      prog.value = n;
      
      t_pal_fl.remove();
    }
    
    prog.close();
  }
}

/**
 *  Adds a peg with a pivot at the center of the selected drawings module(s).
 */
function oh_rigging_addCenterWeightedPeg(){
  scene.beginUndoRedoAccum( "oh_rigging_addCenterWeightedPeg" );
  
  //Work only on SELECTED READ modules.
  var nodes = $.scene.nodeSearch( "#READ(SELECTED)" );
  
  for( var n=0;n<nodes.length;n++ ){
    
    //Get a curve representation of the drawing.
    var curves = nodes[n].getContourCurves( 250 );
    var avg = new oPoint( 0.0, 0.0, 0.0 );
    var cnt = 0;
    
    //Get the average of the curve end points.
    for( var x=0;x<curves.length;x++ ){
      avg.pointAdd( curves[x][0] );
      cnt+=1;

      if( x==curves.length-1 ){
        avg.pointAdd( curves[x][3] );
        cnt+=1;
      }
    }
    
    //The average of all the points.
    avg.divide( cnt );
    
    //Get the in node of the drawing.
    var innode  = nodes[n].ins[0];
    
    //Create the node, increment if the name already exists.
    var res = $.scene.addNode( "PEG", nodes[n].name+"-P", nodes[n].parent, new oPoint(0.0, 0.0, 0.0), true );
    res.pivot = avg;
    
    res.centerAbove( [nodes[n]], 0.0, -50.0 );
    if( innode ){ 
      res.y = ((innode.y - nodes[n].y)*0.25) + nodes[n].y;
    }
    
    //Insert it in, add it between the existing modules if necessary.
    nodes[n].insertInNode( 0, res, 0, 0 );
  }
  
  scene.endUndoRedoAccum( );
}


/**
 *  Adds a backdrop with specified color, to selected nodes in the node-view.
 */
function oh_rigging_addBackdropToSelected(){
  scene.beginUndoRedoAccum( "oh_rigging_addBackdropToSelected" );

  //The path to the UI should be here:
  var oh_colorPicker = specialFolders.userScripts + "/openHarmony_basic_backdropPicker.ui";
  var ui_file = new $.oFile( oh_colorPicker );

  if( !ui_file.exists ){
    MessageBox.information( "Unable to find UI file for the command -- please ensure it was installed properly." );
    return;
  }

  var backdropGUI = function(){
    this.gui = UiLoader.load( oh_colorPicker );
    
    this.gui_labelColor  = this.gui.backdropColor;
    this.gui_buttonColor = this.gui.backdropColorButton;
    this.gui_name        = this.gui.backdropName;
    this.gui_text        = this.gui.backdropText;
    
    //When the change color button is clicked.
    this.changeColor = function( ev ){
      try{
        var colorDialog = new QColorDialog( new QColor( this.color.r, this.color.g, this.color.b ) );
        var color_res = colorDialog.exec();
        
        if( !color_res ){
          return;
        }
        
        var qcol = colorDialog.currentColor;
        this.color.r = qcol.red(); this.color.g = qcol.green(); this.color.b = qcol.blue(); this.color.alpha = qcol.alpha();
        
        var hex_color = this.color.toString().slice( 0, 7 );
          
        this.gui_labelColor.setStyleSheet("QLabel { background-color : "+hex_color+"; color : blue; opacity:0}");
        this.gui_labelColor.update();
      }catch(err){
        System.println( err + " ("+err.fileName+" "+err.lineNumber+")" );
      }
    }
    
    this.gui_buttonColor["clicked"].connect( this, this.changeColor );
    
    //When the dialog comes into view, select the input area immediately.
    var gui_focuser  = this.gui;
    var text_focuser = this.gui_name;
    this.focusInput = function( ev ){
    
      try{
        gui_focuser.activateWindow();
        gui_focuser.raise();
        gui_focuser.setFocus();
        
        text_focuser.setFocus();
        text_focuser.selectAll();
      }catch( err ){
        System.println( err );
      }
    }
    
    //WHEN LAUNCHING THE DIALOG, INITIALIZE IT.
    this.exec = function( name, text, color ){
      this.color = new $.oColorValue( Math.random()*256|0, Math.random()*256|0, Math.random()*256|0 );
      var hex_color = this.color.toString().slice( 0, 7 );
      
      this.gui_name.text = name;
      this.gui_text.text = text;
      
      this.gui_labelColor.setStyleSheet("QLabel { background-color : "+hex_color+"; color : blue; opacity:0}");
      
      //QTimer::singleShot(0, line, SLOT(setFocus()));
      var focusTimer = new QTimer();
          focusTimer.singleShot = true;
          focusTimer["timeout"].connect( this, this.focusInput );
          focusTimer.start( 50 );
      
      var result = this.gui.exec();
      
      if( !result ){
        return false;
      }
      
      
      return { 
                "name"  : this.gui_name.text, 
                "text"  : this.gui_text.plainText,
                "color" : this.color
              };
    }
  }

  var color_selector = new backdropGUI();
  
  var equivalent = {
                      "HAND"  : "ARM",
                      "FOOT"  : "LEG",
                      
                      "EYE"     : "FEATURES",
                      "EYES"    : "FEATURES",
                      "NOSE"    : "FEATURES",
                      "MOUTH"   : "FEATURES",
                      "PUPIL"   : "FEATURES",
                      
                      "EYE"     : "HEAD",
                      "EYES"    : "HEAD",
                      "NOSE"    : "HEAD",
                      "MOUTH"   : "HEAD",
                      "PUPIL"   : "HEAD",
                      "EAR"     : "HEAD",
                      "HAIR"    : "HEAD",
                      "BROW"    : "HEAD",
                      "EYEBROW" : "HEAD",
                    };
  
  //Separate selections into common groups.
  var group_items = {};
  
  var nodes = $.scene.nodeSearch( "(SELECTED)" );
  
  //Iterate the nodes, and separate them into common groups.
  for( var n=0;n<nodes.length;n++ ){
    var tnode = nodes[n];
    if( !group_items[tnode.group] ){
      group_items[tnode.group] = [];
    }
    
    group_items[tnode.group].push( tnode );
  }
  
  //Now, with each group in mind, lets provide an interface to colour, ect.
  for( var grp in group_items ){
    var grp_items = group_items[ grp ];
    var laststring = false;
    var common_substrings = {};
    
    var numNodes = grp_items.length;
    
    // Find the longest common substring. This accumulates the common substrings, and makes a 'voting' system that will subsequently name
    // the backdrop based on the common result (as 'voted').
    for (i = 0; i < numNodes; ++i){
      var node = grp_items[i];
      
      var bnm = node.name.toUpperCase();
          
      if( bnm.slice( bnm.length-2 ).toUpperCase() == ("-P") ){
        bnm = bnm.slice( 0, bnm.length-2 );
      }
          
      if( laststring ){
        var lcs = $.utils.longestCommonSubstring( bnm, laststring );
        
        if( lcs.length>2 ){
          var clean_lcs = lcs.sequence;
          
          if( clean_lcs.slice( clean_lcs.length-1 ) == ("_") ){
            clean_lcs = clean_lcs.slice( 0, clean_lcs.length-1 );
          }
            
          if( clean_lcs.slice( 0,1 ) == ("_") ){
            clean_lcs = clean_lcs.slice( 1 );
          }
          
          if(!common_substrings[clean_lcs]){
            common_substrings[clean_lcs] = 0;
          }
          
          common_substrings[clean_lcs]++;
        }
      }
      
      laststring = bnm;
    }

    var names = [];
    for( var n in common_substrings ){
      names.push( n );
    }
    
    //Now compare cleaned LCS and accumulate them as votes as well.
    for( var n=0;n<names.length;n++ ){
      for( var x=n+1;x<names.length;x++ ){
        var lcs = $.utils.longestCommonSubstring(names[n], names[x]);
        if( lcs.length>2 ){
          var clean_lcs = lcs.sequence;
          
          if( clean_lcs.slice( clean_lcs.length-1 ) == ("_") ){
            clean_lcs = clean_lcs.slice( 0, clean_lcs.length-1 );
          } 
          if( clean_lcs.slice( 0,1 ) == ("_") ){
            clean_lcs = clean_lcs.slice( 1 );
          }
          
          if(!common_substrings[clean_lcs]){
            common_substrings[clean_lcs] = 0;
          }
          common_substrings[clean_lcs]++;
          
          if( equivalent[clean_lcs] ){
            var clean_lcs2 = equivalent[clean_lcs];
            if(!common_substrings[clean_lcs2]){
              common_substrings[clean_lcs2] = 0;
            }
            common_substrings[clean_lcs2]++;
          }
        }
      }
    }
    
    //Find the highest voted LCS.
    var highest    = 0;
    var common_name = 'Backdrop';
    for( var n in common_substrings ){
      if( common_substrings[n] > highest ){
        if( n.toUpperCase()=="DRAWING" ){
          continue;
        }
        
        highest    = common_substrings[n];
        common_name = n;
      }
    }
    
    var res = color_selector.exec( common_name, "", "" );
    if( !res ){ //A cancel option was selected.
      continue;
    }
    
    //Add that beautiful backdrop.
    $.scene.addBackdropToNodes( grp, grp_items, res.name, res.text, res.color, 0, 0, 35, 35 );
  }
  
  scene.endUndoRedoAccum( );
}


/**
 *  Sets the peg's pivot based on a clicked position in the interface.
 */
function oh_rigging_setSelectedPegPivotWithClick(){
  var nodes = $.scene.nodeSearch( "#PEG(SELECTED)" );
  
  if( nodes.length == 0 ){
    $.dialog.alert( "No peg selected." );
    return;
  }
  
  Action.perform( "onActionChoosePencilTool()" );
  var context = this;
  
    var setPiv = function( res ){
      var $    = context.$;
      var m    = context;
          
      $.beginUndo();
      try{
        for( var n=0;n<nodes.length;n++ ){
          nodes[n].pivot = new $.oPoint( res[0][0], res[0][1], 0.0 );
        }
      }catch( err ){
        System.println( err + " " + err.lineNumber + " " + err.fileName );
      }
      Action.perform( "onActionChooseSpTransformTool()" );
      $.endUndo();
    }
  
    //We're using the EnvelopeCreator interface for a click interface. This may have been removed in newer versions of Harmony.
    var en  = new EnvelopeCreator();
    en.drawPathOverlay( setPiv, 1 );
  
}