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
//        $.oNetwork methods        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * Network helper for HTTP methods.<br>Available under <b>$.network</b>
 * @constructor
 * @classdesc  Network Helper Class
 * @param   {dom}                  $         The connection back to the DOM.
 *
 */
$.oNetwork = function( ){
    //Expect a path for CURL.
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
    
    this.useCurl = true;
    this.curlPath = curl_path;
}


/**
 *  Connects to HTTP and gets the text response from a web site/API.<br><b>Note, Harmony has issues with HTTPS, useCurl=true prevents this</b>
 * @param   {string}       address                    The address for the web query.
 * @param   {function}     callback_func              Providing a callback function prevents blocking, and will respond on this function. The callback function is in form func( results ){}
 * @param   {bool}         use_json                   In the event of a JSON api, this will return an object converted from the returned JSON.
 *  
 * @return: {string/object}       The resulting object/string from the query -- otherwise a bool as false when an error occured..
 */
$.oNetwork.prototype.webQuery = function ( address, callback_func, use_json ){
  if (typeof callback_func === 'undefined') var callback_func = false;
  if (typeof use_json === 'undefined') var use_json = false;
  
  if( this.useCurl && this.curlPath ){
    try{
      var cmdline = [ "-L", address ];
      var p = new QProcess();
      if( !callback_func ){
        p.start( this.curlPath, cmdline );
        p.waitForFinished( 10000 );
        
        try{
          var readOut = ( new QTextStream( p.readAllStandardOutput() ) ).readAll();
          if( use_json ){
            readOut = JSON.parse( readOut );
          }
          return readOut;
          
        }catch(err){
          this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
          return false;
        }
      }else{
        p.start( this.curlPath, cmdline );
        
        var callback = function( status ){
          var readOut = ( new QTextStream( p.readAllStandardOutput() ) ).readAll();
          if( use_json ){
            readOut = JSON.parse( readOut );
          }
        
          callback_func( readOut );
        }
        p["finished(int)"].connect( this, callback );
        
        return true;
      }
    }catch( err ){
      this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
      return false;
    }
  }else{
    
    System.println( callback );
    
    var data            = new QByteArray( "" );
    var qurl            = new QUrl( address );
    var request         = new QNetworkRequest( qurl );
    var header          = new QByteArray("text/xml;charset=ISO-8859-1");
    var accessManager   = new QNetworkAccessManager();
    
    request.setHeader( QNetworkRequest.ContentTypeHeader,  header );
    request.setHeader( QNetworkRequest.ServerHeader, "application/json" );
    request.setHeader( QNetworkRequest.ContentLengthHeader, data.size() );
    request.setAttribute( QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.AlwaysNetwork );
    request.setAttribute( QNetworkRequest.FollowRedirectsAttribute, true );
    
    if( callback_func ){
      replyRecd = function( reply ){
        try{ 
          var statusCode = reply.attribute( QNetworkRequest.HttpStatusCodeAttribute );
          var reasonCode = reply.attribute( QNetworkRequest.HttpReasonPhraseAttribute );
          
          if( !statusCode ){
            callback_func( false );
            return;
          }
          
          if( statusCode == 301 ){
            callback_func( false );
            return;
          }

          var stream = new QTextStream( reply );
          var result = stream.readAll(); 
            
          if( use_json ){
            try{
              result = JSON.parse( result );
            }catch(err){
              this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
              callback_func( false );
            }
          }
          
          callback_func( result );
        }catch(err){
          this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
          callback_func( false );
        }
      }
      
      error = function( error ){
        switch( ""+error ){
          case "1":
            // MessageBox.information( "Connection Refused" );
            break;
            
          case "2":
            // MessageBox.information( "Remote Host Closed" );
            break;
            
          case "3":
            // MessageBox.information( "Host Not Found" );
            break;
            
          case "4":
            // MessageBox.information( "Timeout Error" );
            break;
            
          case "5":
            // MessageBox.information( "Operation Cancelled" );
            break;
            
          case "6":
            // MessageBox.information( "SSL Handshake Failed" );
            break;
        }
        
        callback( false );
      }
    
    
      accessManager["finished(QNetworkReply*)"].connect( this, replyRecd );
      var send_reply = accessManager.get( request );
      send_reply["error(QNetworkReply::NetworkError)"].connect( this, error );
      
      return true;
    }else{
      System.println( "STARTING" );
      var wait    = new QEventLoop();
      var timeout = new QTimer();
      
          timeout["timeout"].connect( this, wait["quit"] );
      accessManager["finished(QNetworkReply*)"].connect( this, wait["quit"] );
      
      var send_reply = accessManager.get( request );
      timeout.start( 10000 );
      wait.exec();
      timeout.stop();
      
      try{ 
        var statusCode = send_reply.attribute( QNetworkRequest.HttpStatusCodeAttribute );
        var reasonCode = send_reply.attribute( QNetworkRequest.HttpReasonPhraseAttribute );
        
        if( !statusCode ){
          return false;
        }
        
        if( statusCode == 301 ){
          return false;
        }

        var stream = new QTextStream( send_reply );
        var result = stream.readAll(); 
          
        if( use_json ){
          try{
            result = JSON.parse( result );
          }catch(err){
            this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
          }
        }
        
        return( result );
      }catch(err){
        System.println( err );
        this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
      }
      
      return( false );
    }
  }
}


/**
 *  Downloads a file from the internet at the given address<br><b>Note, only implemented with useCurl=true.</b>
 * @param   {string}       address                    The address for the file to be downloaded.
 * @param   {function}     path                       The local file path to save the download.
 * @param   {bool}         replace                    Replace the file if it exists.
 *  
 * @return: {string/object}       The resulting object/string from the query -- otherwise a bool as false when an error occured..
 */
$.oNetwork.prototype.downloadSingle = function ( address, path, replace ){
  if (typeof replace === 'undefined') var replace = false;
  
  try{
    if( this.useCurl && this.curlPath ){            
      var file = new this.$.oFile( path );
      if( file.exists ){
        if( replace ){
          file.remove();
        }else{
          this.$.debug( "File already exists- unable to replace: " + path, this.$.DEBUG_LEVEL["ERROR"] );
          return false;
        }
      }
      
      var cmdline = [ "-L", "-o", path, address ];
      
      var p = new QProcess();
      p.start( this.curlPath, cmdline );  
      p.waitForFinished( 10000 );
      
      var file = new this.$.oFile( path );
      return file.exists;
      
    }else{
      this.$.debug( "Downloads without curl are not implemented.", this.$.DEBUG_LEVEL["ERROR"] );
      return false;
    }
  }catch( err ){
    this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
    return false;
  }
}


/**
 *  Threads multiple downloads at a time [10 concurrent].  Downloads a from the internet at the given addresses<br><b>Note, only implemented with useCurl=true.</b>
 * @param   {object[]}     instructions               The instructions for download, in format [ { "path": localPathOnDisk, "url":"DownloadPath" } ]
 * @param   {bool}         replace                    Replace the file if it exists.
 *  
 * @return: {bool[]}       The results of the download, for each file in the instruction bool[]
 */
$.oNetwork.prototype.downloadMulti = function ( address_path, replace ){
  if (typeof replace === 'undefined') var replace = false;
  
  var progress = new QProgressDialog();
  progress.setLabelText( "Downloading files..." );
  progress.show();
  progress.setRange( 0, address_path.length );
  
  var complete_process = function( val ){ 
  }
  
  var dload_cnt = 0;
  try{
    if( this.useCurl && this.curlPath ){
      var in_proc = [];
      var skipped = [];
      for( var x=0;x<address_path.length;x++ ){
        var add_grp = address_path[x];
        
        skipped.push( false );
        try{
          var url  = add_grp.url;
          var path = add_grp.path;
          
          while( in_proc.length >= 10 ){  //Allow 10 concurrent processes.
            var procs = [];
            for( var n=0;n<in_proc.length;n++ ){     //Cull the finished processes.
              QCoreApplication.processEvents();
              if( parseInt( ""+ in_proc[n].state() ) > 0 ){
                procs.push( in_proc[n] );
              }else{
                dload_cnt++;
                progress.setValue( dload_cnt );
              }
            } 
            in_proc = procs;
          }
          
          var file = new this.$.oFile( path );
          if( file.exists ){
            if( replace ){
              file.remove();
            }else{
              this.$.debug( "File already exists- unable to replace: " + path, this.$.DEBUG_LEVEL["ERROR"] );
              skipped[x] == true;
              continue;
            }
          }
          
          var cmdline = [ "-L", "-o", path, url ];
          var p = new QProcess();
          p["finished(int)"].connect( this, complete_process );
          p.start( this.curlPath, cmdline );  
          in_proc.push( p );
          
          progress.setLabelText( "Downloading file: "+path );
          
          QCoreApplication.processEvents();
        }catch(err){
          this.$.debug( err + " : " + err.lineNumber + " : " + err.fileName, this.$.DEBUG_LEVEL["ERROR"] );
        }
      }
      
      while( in_proc.length > 0 ){  //Allow 5 concurrent processes.
        var procs = [];
        for( var n=0;n<in_proc.length;n++ ){     //Cull the finished processes.
          QCoreApplication.processEvents();
          if( parseInt( ""+ in_proc[n].state() ) > 0 ){
            procs.push( in_proc[n] );
          }else{
            dload_cnt++;
            progress.setValue( dload_cnt );
          }
          
          progress.setLabelText( "Downloading "+in_proc.length+" File(s)" );
        } 
        
        in_proc = procs;
      }

      progress.accept();
      
      var file_results = [];
      for( var x=0;x<address_path.length;x++ ){
        file_results.push( false );
        if( skipped[x] ){
          continue;
        }
        
        var add_grp = address_path[x];
        var file = new this.$.oFile( add_grp.path );
        if( file.exists ){
          file_results[x] = true;
        }
      }
      
      return file_results;
    }else{
      this.$.debug( "Downloads without curl are not implemented.", this.$.DEBUG_LEVEL["ERROR"] );
      return false;
    }
  }catch( err ){
    this.$.debug( err + " ("+err.lineNumber+")", this.$.DEBUG_LEVEL["ERROR"] );
    return false;
  }
}