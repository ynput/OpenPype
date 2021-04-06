//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library v0.01
//
//
//         Developped by Mathieu Chaptel, ...
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
//             TOOLS                //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

//-- Standalone Tool for openHarmony tool installation and management.
//--------------------------------------------------------------------

function oh_load(){
  try{
    var oh_incl = preferences.getString( 'openHarmonyInclude', false );
    if( !this["$"] ){  
      include( oh_incl );
    }
    if( !this["$"] ){  
      MessageBox.warning( "Unable to load the openHarmony library. Is it installed?" );
    }
  }catch(err){
    System.println( err + " : " + err.lineNumber + " " + err.fileName );
  }
}

function openHarmony_toolInstaller(){
  oh_load();  
    var tool_installer_gui = function(){
      try{
        
        this.$ = $;
        var oh_path = preferences.getString( 'openHarmonyPath', false );
        this.loaded = false;
        this.ui_path = oh_path + "/openHarmony/openHarmony_toolInstall.ui";
        
        var branch_list = "https://api.github.com/repos/cfourney/OpenHarmony/branches";
        
        if( !(new $.oFile(this.ui_path).exists) ){
          return;
        }
        
        this.ui = UiLoader.load( this.ui_path );
        
        this.loaded = true;
        
        this.branchList    = this.ui.toolListGroupBox.branchCombo;
        this.installList   = this.ui.toolListGroupBox.installList;
        this.installButton = this.ui.detailGroupbox.installButton;
        this.installLabel  = this.ui.detailGroupbox.installLabel;
        this.detailText    = this.ui.detailGroupbox.detailArea;
        
        this.branchList.clear();
        this.branchList.addItems( [ "LOADING. . ." ] );
        
        this.detailText.readOnly = true;
        
        var context = this;
        
        this.installButton.setEnabled( false ); 
        
        //INSTALL DETAILS
        var oh_install        = specialFolders.userScripts + "/" + "openHarmony_install";
        var oh_install_folder = ( new $.oFolder(oh_install) );
        if( !oh_install_folder.exists ){
          //CREATE IT.
          oh_install_folder.create();
        }
        
        this.ref_cache = {};
        
        this.install_type = 'install';
         
        //----------------------------------------------
        //-- CHECK TO SEE IF THE FILE IS ALREADY INSTALLED.
        this.getInstalledStatus = function( item ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              //A file is written here if it is installed.
              var install_detail_script = oh_install + "/" + item["name"];
              var install_file = new $.oFile( install_detail_script );
              
              if( install_file.exists ){
                //--The file exists. It might be an remove if same version, or an upgrade.
                var read_file = install_file.read().split("\n");
                if( read_file[0] == item["sha"] ){
                 return 'remove';
                }else{
                 return 'update';
                }
              }else{
                return 'install';
              } 
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
              return 'install';
            }
          }
        }
        
        //----------------------------------------------
        //-- UPDATE THE INSTALLED STATUS OF THE SELECTED PLUGIN
        this.updateInstalledStatus = function( item ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var install_status = m.getInstalledStatus( item );
              
              switch( install_status ){
                case 'install':
                  m.install_type = install_status;
                  m.installButton.text = "INSTALL";
                  m.installButton.setEnabled( true );
                  break;
                  
                case 'update':
                  m.install_type = install_status;
                  m.installButton.text = "UPDATE";
                  m.installButton.setEnabled( true );
                  break;
                  
                case 'remove':
                  m.install_type = install_status;
                  m.installButton.text = "REMOVE";
                  m.installButton.setEnabled( true );
                  break;
                  
                default:
                  m.install_type = "install";
                  m.installButton.text = "INSTALL/UPDATE";
                  m.installButton.setEnabled( false );
                  break;
                  
              }

            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        this.readme_cache  = {};
        this.install_cache = {};
        this.content_cache = {};
        
        //----------------------------------------------
        //-- RETRIEVE THE SELECTED ITEM
        this.getItem = function(){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var indx = m.installList.currentRow;
              if( indx >= m.availableItems.length ){
                return false;
              }
              var item = m.availableItems[ indx ];
              return item;
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        
        //----------------------------------------------
        //-- GET THE FILE CONTENTS IN A DIRCTORY ON GIT
        this.recurse_files = function( contents, arr_files ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              for( var n=0;n<contents.length;n++ ){
                var tfl = contents[n];
                
                if( contents[n].type == "file" ){
                  arr_files.push( [tfl["download_url"], tfl["path"]] );
                  
                }else if( contents[n].type == "dir" ){
                  //Get more contents.
                  QCoreApplication.processEvents();
                  var apic = new api_call( tfl["url"] );
                  if( apic ){
                    arr_files = m.recurse_files( apic, arr_files );
                  }
                }
              }
              
              return arr_files;
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        //----------------------------------------------
        //-- STANDARD DIALO CONFIRMATION
        this.confirmDialog = function( d_title, d_str, ok_text, cancel_text ){
            if (typeof ok_text === 'undefined') var ok_text = "Okay";
            if (typeof cancel_text === 'undefined') var cancel_text = "Cancel";            
          
            var d = new Dialog();
            d.title = d_title;
            
            //Standard install paths.
            var install_base = specialFolders.userScripts;
            var library_base = install_base + '/openHarmony';
            
            var libdir = new Dir(library_base);
            var label = new Label;
            label.text = d_str;
            d.okButtonText     = ok_text;
            d.cancelButtonText = cancel_text;
            d.add( label );
            
            if ( !d.exec() ){
              return false;
            }
            
          return true;
        }
        
        //----------------------------------------------
        //-- FILES ARE DOWNLOADED
        this.downloadFiles = function( file_download_listing, overwrite ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var item = m.getItem();
              if( !item ){ return; }
              
              var install_type = m.install_cache[ item["url"] ];
              
              // $.debug( file_download_listing, $.DEBUG_LEVEL["ERROR"] );
              
              var path_download = [];
              var install_base  = specialFolders.userScripts;
              
              var ignore_files = {  
                                    "README"  : true, 
                                    "INSTALL" : true
                                 };
                    
              // $.debug( item, $.DEBUG_LEVEL["ERROR"] );
              
              var script_files         = [];
              var install_instructions = [];
              var install_files        = [];
              for( var n=0; n<file_download_listing.length; n++ ){
                var tfl = file_download_listing[n];
                
                var url  = tfl[0];
                var file = tfl[1];
                
                try{
                  var local_path = file.slice( item["path"].length+1 );
                  if( ignore_files[ local_path ] ){
                    continue; //Skipped file.
                  }
                  
                  if( local_path.split("/").length > 0 && local_path.toUpperCase().indexOf(".JS")>0 ){
                    script_files.push( local_path );
                  }
                  
                  var lpth = install_base + "/" + local_path;
                  install_files.push( lpth );
                  
                  var lfl = new $.oFile( lpth );
                  if( lfl.exists && !overwrite ){
                    //Confirm deletion?
                    if( !confirmDialog( "Overwrite File", "Overwrite " + lpth, "Overwrite", "Cancel" ) ){ continue; }
                  }
                  
                  install_instructions.push( { "url": url, "path": lpth } );
                }catch(err){
                  continue;
                }
              }
              
              var downloaded = $.network.downloadMulti( install_instructions, true );
              
              var all_success = true;
              for( var x=0;x<downloaded.length;x++ ){
                if( !downloaded[x] ){
                  all_success = false;
                }
              }
              
              if( !all_success ){
                MessageBox.information( "Failed to download " + item["name"] +", try again later." );
                return;
              }
              
              var str = '    No Script Files Available.';
              if( script_files.length>0 ){
                var str_limited = [];
                for( var t=0;t<( Math.min(script_files.length,4) );t++ ){
                  str_limited.push( "    " + script_files[t] );
                }              
                if( script_files.length>4 ){
                  str_limited.push( "         " + "And More!" );
                }
                str = str_limited.join( "\n" );
              }
              
              m.installButton.text = "INSTALLED!";
              m.installButton.setEnabled( false );
              MessageBox.information( "Installed " + item["name"] + "!\n\nThe installed scripts include:\n" + str );
              
              //TODO: Create the install script with details.
              var install_detail_script = oh_install + "/" + item["name"];
              var install_details_text = [];
              
              var install_fl = new $.oFile( install_detail_script );
              install_fl.write( item["sha"] + "\n" + install_files.join( "\n" ) );
              
              m.get_tools();
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        this.basePath = '';
        
        this.removeAction = function( ev ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var item = m.getItem();
              if( !item ){
                $.debug( "Failed to install - no item seems to be selected.", $.DEBUG_LEVEL["ERROR"] );
                return;
              }
              
              var install_detail_script = oh_install + "/" + item["name"];
              var install_file = new $.oFile( install_detail_script );
              
              if( install_file.exists ){
                //--The file exists. It might be an remove if same version, or an upgrade.
                var read_file = install_file.read().split("\n");
                
                for( var n=1;n<read_file.length;n++ ){
                  var fl = read_file[n];
                  
                  var flobj = new $.oFile( fl );
                  if( flobj.exists ){
                    $.debug( "Removing file: " + fl, $.DEBUG_LEVEL["ERROR"] );
                    flobj.remove();
                  }
                }
                
                if( install_file.exists ){
                  $.debug( "Removing file: " + install_detail_script, $.DEBUG_LEVEL["ERROR"] );
                  install_file.remove();
                }
                
                m.get_tools();
                MessageBox.information( "Removed the " + item["name"] + " plugin." );
                
              }else{
                MessageBox.information( "Unable to find the installed plugin." );
                
              }
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        //----------------------------------------------
        //-- THE INSTALL BUTTON WAS CLICK.
        this.installAction = function( ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var item = m.getItem();
              if( !item ){
                $.debug( "Failed to install - no item seems to be selected.", $.DEBUG_LEVEL["ERROR"] );
                return;
              }
                       
              if( m.install_type == "remove" ){
                //Iterate the files and remove them.
                m.removeAction();
                return;
              }
                       
              if( !m.content_cache[ item["url"] ] ){
                $.debug( "Failed to install - cache contents should be available already.", $.DEBUG_LEVEL["ERROR"] );
                return;
              }
              
              var files = m.recurse_files( m.content_cache[ item["url"] ], [] );
              $.debug( "FILES TO INSTALL: "+files.length, $.DEBUG_LEVEL["LOG"] );

              m.downloadFiles( files, false );
              
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        this.installButton["clicked"].connect( this, this.installAction );
        
        //----------------------------------------------
        //-- GET THE README DETAILS TO SHOW TO THE USER
        this.getReadme = function( results ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
            
              var item = m.getItem();
              if( !item ){ return; }
            
              m.install_cache[ item["url"] ] = "script";
            
              if( !results ){
                m.detailText.setText( "Failed to load description." );
                return;
              }
            
              m.content_cache[ item["url"] ] = results;
              m.installLabel.text = 'SCRIPT';
              
              //Standardize the types.
              var install_types = {
                                    "script" : "SCRIPT"
                                  };
              
              var set_readme = false;
              for( var n=0;n<results.length;n++ ){
                //--- 
                var item = results[ n ];
                if( item["name"].toUpperCase() == "README" ){
                  //README WAS FOUND
                  var download_item = item["download_url"]; //download_item
                  var query = $.network.webQuery( download_item, false, false );
                  if( query ){
                    m.detailText.setHtml( query );
                    m.readme_cache[ item["url"] ] = query;
                    set_readme = true;
                  }
                }else if( item["name"].toUpperCase() == "INSTALL" ){
                  //INSTALL WAS FOUND
                  var download_item = item["download_url"];
                  var query = $.network.webQuery( download_item, false, false );
                  if( query ){
                    //INSTALL TYPES ARE script, package, ect.
                    
                    if( install_types[ m.install_cache[ item["url"] ] ] ){
                      m.installLabel.text = install_types[ m.install_cache[ item["url"] ] ];
                    }else{
                      m.installLabel.text = "SCRIPT";
                    }
                    
                    m.install_cache[ item["url"] ] = query.toLowerCase();
                  }
                }
              }
                                   
              if( !install_types[ m.install_cache[ item["url"] ] ] ){
                m.install_cache[ item["url"] ] = "script";
              }
              
              if( !set_readme ){
                m.detailText.setText( "No README available." );
              }
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        //----------------------------------------------
        //-- TOOL IS SELECTED, QUERY OTHER DETAILS
        this.select_tool = function( item, item ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              m.detailText.setText( "" );
              m.installButton.setEnabled( false );
              m.installButton.text = "INSTALL/REMOVE";
              
              var item = m.getItem();
              if( !item ){
                return;
              }
              
              m.detailText.setText( "Loading. . ." );
              m.updateInstalledStatus( item );
              
              if( !m.readme_cache[ item["url"] ] ){
                var query = $.network.webQuery( item["url"], this.getReadme, true );
              }else{
                m.detailText.setHtml( m.readme_cache[ item["url"] ] );
              }
            }catch(err){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        this.installList["itemSelectionChanged()"].connect( this, this.select_tool );
        
        
        //----------------------------------------------
        //-- SHOW THE TOOLS
        this.tool_dir_cache = {};
        this.show_tools = function( results ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              m.availableItems = [];
              m.installList.clear();
              
              var c_sha = m.branches[ m.branchList.currentIndex ];
              m.ref_cache[ c_sha ] = results;
              
              if(! results){
                //NO OPTIONS
                m.installList.addItem( "None Available" );
                m.detailText.setHtml( "" );
                return;
              }
              
              var tool_dir = false;
              //FIND THE TOOLS DIRECTORY IN THE DEPLOYMENT.
              for( var n=0;n<results.length;n++ ){
                if( results[n].name.toUpperCase() == "TOOLS" && results[n].type == "dir" ){
                  tool_dir = results[n];
                }
              }
              
              if(!tool_dir){
                m.installList.addItem( "None Available" );
                m.detailText.setHtml( "" );
                return;
              }
              
              if( m.tool_dir_cache[ tool_dir["url"] ] ){
                query = m.tool_dir_cache[ tool_dir["url"] ];
              }else{              
                var query = $.network.webQuery( tool_dir["url"], false, true );
                if( !query ){
                  m.installList.addItem( "None Available" );
                  return;
                }
                m.tool_dir_cache[ tool_dir["url"] ] = query;
              }
              
              //List and color the tool listing.
              for( var n=0;n<query.length; n++ ){
                m.installList.addItem( query[n]["name"] );
                var stat = m.getInstalledStatus( query[n] );
                
                switch( stat ){
                  case "remove":
                    var t_item = m.installList.item( n );
                    t_item.setForeground( new QBrush( new QColor( new QColor( 0, 125, 0, 255 ) ) ) );
                    break;
                    
                  case "update":
                    var t_item = m.installList.item( n );
                    t_item.setForeground( new QBrush( new QColor( new QColor( 125, 0, 0, 255 ) ) ) );
                    break;
                }

                m.availableItems.push( query[n] );
              }
            }catch( err ){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        
        //----------------------------------------------
        //-- GET THE TOOLS
        this.get_tools = function( ev ){
          with( context.$.global ){
            try{
              var $    = context.$;
              var m    = context;
              
              var c_sha = m.branches[ m.branchList.currentIndex ];
              
              m.installList.clear();
              m.installList.addItem( "Loading. . ." );
              m.detailText.setHtml( "" );
              
              if( !c_sha ){
                m.installList.addItem( "" );
                return;
              }
              
              if( !m.ref_cache[ c_sha ] ){
                var contents_url = "https://api.github.com/repos/cfourney/OpenHarmony/contents?ref="+c_sha;             
                var query = $.network.webQuery( contents_url, this.show_tools, true );
              }else{
                m.show_tools( m.ref_cache[ c_sha ] );
              }
              
            }catch( err ){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          }
        }
        
        this.branchList["currentIndexChanged(int)"].connect( this, this.get_tools );
        
        
        //----------------------------------------------
        //-- GET THE BRANCHES AND DISPLAY THEM IN THE PULLDOWN
        this.get_branches = function( results ){
          with( context.$.global ){
            try{
              
              var $    = context.$;
              var m    = context;
              
              m.branches = [];
              m.branchList.clear();
              m.detailText.setHtml( "" );
              if( results.length == 0 ){
                this.branchList.addItems( [ "NO BRANCHES" ] )
              }else{
                for( var n=0;n<results.length;n++ ){
                  m.branches.push( results[n]["commit"]["sha"] );
                  m.branchList.insertItem(n, results[n]["name"].toUpperCase(), results[n]["commit"]["sha"] );
                  
                }
              }
              
            }catch( err ){
              $.debug( err + " ("+err.fileName+" "+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
            }
          context.get_tools();
          }
        }
        
        var query = $.network.webQuery( branch_list, this.get_branches, true );
        this.ui.show();

      }catch(err){
        $.debug( err + " ("+err.lineNumber+")", $.DEBUG_LEVEL["ERROR"] );
      }
    };
    
  var tool_instaler = new tool_installer_gui();
}