function openHarmony_install_main(){
  try{
    var d = new Dialog();
    d.title = "Install/Update OpenHarmony";
    d.cancelButtonText = "Cancel";
    
    //Standard install paths.
    var install_base = specialFolders.userScripts;
    var library_base = install_base;
    
    var libdir = new Dir(library_base);
    var label = new Label;
        label.text = "Install openHarmony libraries?\n";
    
    d.add( label );
    
    if ( !d.exec() ){
      return;
    }
    
    if( !libdir.exists ){
      MessageBox.information( "Failed to create folders for openHarmony - please check permissions." );
    }
    
    var apic = api_call( "https://api.github.com/repos/cfourney/OpenHarmony/branches" );
    if( !apic ){
      MessageBox.information( "API Error - Failed to get available branches." );
      return;
    }
    
    var branch_names = apic.map(function(x, index){return index+": "+x.name.toUpperCase()})
    
    var res = Input.getItem( "Which Branch", branch_names );
    if( !res ){ return; }

    var branch_data = false;
    var fnd = false;
    for( var x=0;x<apic.length;x++ ){
      var fname = (x+1)+": "+apic[x].name.toUpperCase();
      if( fname == res ){
        
        fnd = apic[x]["commit"]["sha"];
        
        branch_data = apic[x].name.toUpperCase();        
        branch_data = branch_data + "\n" + fnd;
        branch_data = branch_data + "\n" + new Date();
        break;
      }
    }
    
    if( !fnd ){
      MessageBox.information( "Error - This shouldn't have happened." );
      return;
    }
    
    var contents_url = "https://api.github.com/repos/cfourney/OpenHarmony/contents?ref="+fnd;
    
    var apic = api_call( contents_url );
    if( !apic ){
      MessageBox.information( "API Error - Failed to get available branch content." );
      return;
    }
    
    if( apic && apic.length ){
      //Download the files.
      var progress = new QProgressDialog();
      progress.setLabelText( "Downloading files..." );
      progress.show();
      progress.setRange( 0, 100 );
      
      var file_download_listing = recurse_files( apic, [] );
      progress.setRange( 0, file_download_listing.length );

      
      
      var oh_install = specialFolders.userScripts + "/" + "openHarmony_install";
      var libdir = new Dir( oh_install );
      if( !libdir.exists ) libdir.mkdirs();

      if( libdir.exists ){
        var oh_install_file = oh_install + "/" + "OpenHarmony";
        
        var file = new File( oh_install_file );
        try {
          var content = [ fnd ];
          for( var n=0;n<file_download_listing.length;n++ ){
            var path    = file_download_listing[n][1];
            var local_path = library_base+'/'+path;
            
            content.push( local_path );
          }
          
          file.open(FileAccess.WriteOnly);
          file.write( content.join("\n") );
          file.close();
        } catch (err) {}
      }
      
      
      for( var n=0;n<file_download_listing.length;n++ ){
        progress.setValue( n );
        QCoreApplication.processEvents();
        
        var raw_url = file_download_listing[n][0];
        var path    = file_download_listing[n][1];
        
        var local_path = library_base+'/'+path;
        
        if( path.slice( 0, path.indexOf("/") ) == "tools" ){
          //Dont include the tools directory, these will be installed as needed.
          continue;
        }

        if( path.slice( 0, path.indexOf("/") ) == "docs" ){
          //Dont include the docs directory, these will be installed as needed.
          continue;
        }

        
        var local_dir  = local_path.slice( 0, local_path.lastIndexOf("/") );
        
        var libdir = new Dir(local_dir);
        if( !libdir.exists ){
          libdir.mkdirs();
        }
        
        if( !libdir.exists ){
          MessageBox.information( "Failed to create openHarmony directory: " + local_dir );
          progress.accept();
          return;
        }
        
        //Override path of active scripts to ensure they're accessible to the user.
        //----------------------------------------------------------------------------
        var downloaded = download( raw_url, local_path );
        if( !downloaded ){
          MessageBox.information( "Failed to create openHarmony file: " + local_path );
          progress.accept();
          return;
        }
      }
      
      progress.accept();
      
      if( (new File( local_dir + "/" + "openHarmony.js" )).exists ){
        MessageBox.information( "OpenHarmony successfully installed." );
        preferences.setString( 'openHarmonyInclude', ( local_dir + "/" + "openHarmony.js" ) );
        preferences.setString( 'openHarmonyPath', ( local_dir ) );
        
        try {
          var install_path = local_dir + "/" + "INSTALL";
          var file = new File(install_path);
          file.open(FileAccess.Append);
          file.write( branch_data );
          file.close();
        }catch (err){
        }
      }else{
        MessageBox.information( "Unable to find OpenHarmony in install path: " + (local_dir + "/" + "openHarmony.js") );
      }
    }
  }catch( err ){
    MessageBox.information( "Failed to install: " + err + " ("+ err.lineNumber +")" );
  }
  
  
  function recurse_files( contents, arr_files ){
    for( var n=0;n<contents.length;n++ ){
      var tfl = contents[n];
      
      if( contents[n].type == "file" ){
        arr_files.push( [tfl["download_url"], tfl["path"]] );
        
      }else if( contents[n].type == "dir" ){
        //Get more contents.
        QCoreApplication.processEvents();
        var apic = api_call( tfl["url"] );
        if( apic ){
          arr_files = recurse_files( apic, arr_files );
        }else{
          return false;
        }
      }
    }
    
    return arr_files;
  }


  function api_call( address ){
    try{
    
      var avail_paths = [ 
                          "c:\\Windows\\System32\\curl.exe"
                        ];
      if( !about.isWindowsArch() ){
        avail_paths = [ 
                        "/usr/bin/curl",
                        "/usr/local/bin/curl"
                      ];
      }
      
      var curl_path = false;
      for( var n=0;n<avail_paths.length;n++ ){
        if( ( new File(avail_paths[n]) ).exists ){
          curl_path = avail_paths[n];
          break;
        }
      }

      if (!curl_path){
        MessageBox.information("curl is required and is not found on this machine. Install curl to continue.\n\n Download available at : "+(about.isWindowsArch?"https://curl.haxx.se/windows/":"https://curl.haxx.se/download.html"))
        return false;
      }

      var cmdline = [ "-L", address ];
      
      var p = new QProcess();
      // p.setWorkingDirectory( pathToTemplate ); 
      p.start( curl_path, cmdline );  
      p.waitForFinished( 10000 );
      
      try{
        var readOut = JSON.parse((new QTextStream(p.readAllStandardOutput())).readAll());
        return readOut;
      }catch(err){
        return false;
      }    
    }catch( err ){
      System.println( err + " ("+address.lineNumber+")" );
      MessageLog.trace( err + " ("+address.lineNumber+")" );
    }
  }


  function download( address, target ){
    try{
    
      var avail_paths = [ 
                          "c:\\Windows\\System32\\curl.exe"
                       ];
      if( !about.isWindowsArch() ){
        avail_paths = [ 
                        "/usr/bin/curl",
                        "/usr/local/bin/curl"
                      ];
      }
      
      var curl_path = false;
      for( var n=0;n<avail_paths.length;n++ ){
        if( ( new File(avail_paths[n]) ).exists ){
          curl_path = avail_paths[n];
          break;
        }
      }
      
      if( !curl_path ){
        MessageBox.information( "Unable to find application for web hook." );
        return false;
      }
      
      var file = new File( target );
      if( file.exists ){
        file.remove();
      }
      
      var cmdline = [ "-L", "-o", target, address ];
      
      var p = new QProcess();
      p.start( curl_path, cmdline );  
      p.waitForFinished( 10000 );
      
      var file = new File( target );
      return file.exists;
      
    }catch( err ){
      System.println( err + "("+err.lineNumber+")" );
      MessageLog.trace( err + " ("+address.lineNumber+")" );
    }
  }  
}

