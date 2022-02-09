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
//         $.oThread class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The base class for the $.oThread -- WIP, NOT TRULY THREADED AS THE EVENT MANAGER DOESNT ALLOW FOR THREADS YET.
 * @constructor
 * @classdesc  $.oThread Base Class
 * @param   {function}                 kernel                The kernel that is iterating.
 * @param   {object[]}                 list                  The list of elements to iterate upon.
 * @param   {int}                      [threadCount]         The amount of threads to initiate. Default: 5
 * @param   {bool}                     [start]               Whether to start on instantiation, or to wait until prompted. Default: false
 * @param   {int}                      [timeout]             Timeout in MS
 * @param   {bool}                     [reserveThread]       Whether to reserve a thread for this to process while blocking.
 *
 * @property {int}                     threadCount           The amount of threads to initiate.
 * @property {QTimer[]}                threads               The underlying QTimers that behave as threads.
 * @property {object[]}                results_thread        The results from the kernel, should match indices of provided list.
 * @property {string[]}                error_thread          The errors from the kernel, in the event there are code errors.
 * @property {bool[]}                  complete_thread       The completion (note: not success) state of the thread. Success state would be the result.
 * @property {bool}                    started               The start state of all threads.
 * @property {int}                     timeout               MS timeout for blocking processes.
 */
$.oThread = function( kernel, list, threadCount, start, timeout, reserveThread ){
  if (typeof threadCount === 'undefined') var threadCount = "2";
  if (typeof start === 'undefined') var start = false;
  if (typeof reserveThread === 'undefined') reserveThread = true;

  threadCount = Math.min( threadCount, list.length );

  this.list               = list;
  this.threadCount        = threadCount;
  this.threads            = [];
  this.started_thread     = [];
  this.results_thread     = [];
  this.error_thread       = [];
  this.complete_thread    = [];

  this.started     = false;

  this.startAtInstantiation = start;
  this.threads_available    = false;
  this.reserveThread        = reserveThread;
  this.reservedThread       = false;

  this.timeout     = 1000.0 * 60.0;
  if ( timeout ) this.timeout = timeout;

  //Instantiate the results.
  for( var n=0;n<list.length;n++ ){
    this.results_thread.push( false );
    this.complete_thread.push( false );
    this.error_thread.push( false );
  }

  var context = {
                  "kernel"   : kernel,
                  "list"     : list,
                  "results"  : this.results_thread,
                  "complete" : this.complete_thread,
                  "error"    : this.error_thread
                };

  this.kernel = function( thread, from, to ){
    var local_context = context;
    for( var n=from;n<to;n++ ){
      try{
        var result = local_context["kernel"]( local_context["list"][n] );
        local_context["results"][n]   = result;
        local_context["complete"][n]  = true;
        local_context["error"][n]     = true;
      }catch( err ){
        System.println( err + " (" +err.lineNumber+ " " + err.fileName + ")" );
        local_context["results"][n]   = false;
        local_context["complete"][n]  = true;
        local_context["error"][n]     = ( err + " (" +err.lineNumber+ " " + err.fileName + ")" );
      }
    }
  };

}

/**
 * The completion state of all the threads.
 * @name $.oThread#complete
 * @type {bool}
 */
Object.defineProperty($.oThread.prototype, 'complete', {
    get : function(){
        if( !this.started ){
          System.println( "Not yet started" );
          return false;
        }

        for( var n=0;n<this.complete_thread.length;n++ ){
          if( !this.complete_thread[n] ){
            return false;
          }
        }

        return true;
    }
});

/**
 * The indices that have completed results.
 * @name $.oThread#completedIndices
 * @type {int[]}
 */
Object.defineProperty($.oThread.prototype, 'completedIndices', {
    get : function(){
        var indices = [];
        for( var n=0;n<this.complete_thread.length;n++ ){
          if( this.complete_thread[n] ){
            indices.push( n );
          }
        }

        return indices;
    }
});

/**
 * The errors, if any, in form { "index" : int, "error" : string }
 * @name $.oThread#errorsWithIndex
 * @type {object[]}
 */
Object.defineProperty($.oThread.prototype, 'errorsWithIndex', {
    get : function(){
        var errors = [];
        for( var n=0;n<this.error_thread.length;n++ ){
          if( this.error_thread[n] ){
            errors.push( { "index" : n, "error":this.error_thread[n] } );
          }
        }

      return errors;
    }
});

/**
 * The results, if any, in form { "index" : int, "results" : object }
 * @name $.oThread#resultsWithIndex
 * @type {object[]}
 */
Object.defineProperty($.oThread.prototype, 'resultsWithIndex', {
    get : function(){
        var results = [];
        for( var n=0;n<this.results_thread.length;n++ ){
          if( this.results_thread[n] ){
            results.push( { "index" : n, "results":this.results_thread[n] } );
          }
        }

      return results;
    }
});

/**
 * The errors, matching index of input list.
 * @name $.oThread#errors
 * @type {string[]}
 */
Object.defineProperty($.oThread.prototype, 'errors', {
    get : function(){
      return this.error_thread;
    }
});

/**
 * The errors, matching index of input list.
 * @name $.oThread#results
 * @type {object[]}
 */
Object.defineProperty($.oThread.prototype, 'results', {
    get : function(){
      return this.results_thread;
    }
});


/**
 * Start the thread and block if necessary.
 * @param   {bool}         block                    Whether the process should block and wait for completion.
 */
$.oThread.prototype.start = function( block ){
  if (typeof block === 'undefined') block = true;

  if( !this.threads_available ){
    if( !this.prepareThreads() ){
      return;
    }
  }

  for( var n=0;n<this.threads.length;n++ ){
    // System.println( "THREAD STARTING: " + n );
    if( this.started_thread[ n ] ){
      continue;
    }

    this.threads[n].start( 0 );
    QCoreApplication.processEvents();

    this.started_thread[ n ] = true;
  }

  this.started = true;

  if( block ){
    this.wait();
  }
}


/**
 * If threads are not yet prepared, this will prepare them.
 * @param   {bool}         [block]                    Whether the process should block and wait for completion.
 */
$.oThread.prototype.prepareThreads = function( start ){
  if (start) this.startAtInstantiation = start;

  if( this.threads_available ){
    return false;
  }

  try{
    for( var thread_num=0;thread_num<this.threadCount;thread_num++ ){
      this.started_thread.push( false );

      var from_val  = Math.floor( ( thread_num / this.threadCount ) * this.list.length );
      var to_val    = Math.floor( ( (thread_num+1) / this.threadCount ) * this.list.length );

      if( this.reserveThread && thread_num == this.threadCount-1 ){
        this.reservedThread = eval( 'kernel = function(){ this.kernel('+thread_num+', '+from_val+','+to_val+') }'  );
        continue;
      }

      this.threads.push( new QTimer() );
      this.threads[thread_num].singleShot = true;
      this.threads[thread_num]["timeout"].connect( this, eval( 'kernel = function(){ this.kernel('+thread_num+', '+from_val+','+to_val+') }'  ) );

      if( this.startAtInstantiation ){
        this.threads[thread_num].start(0);
        QCoreApplication.processEvents();
        this.started = true;
        this.started_thread[ thread_num ] = true;
      }
    }
  }catch(err){
    System.println( err + " (" +err.lineNumber+ " " + err.fileName + ")" );
  }

  this.threads_available    = true;
  return true;
}


/**
 * If started, will block until completion or timeout.
 * @param   {int}         block_time                    The MS time to block.
 */
$.oThread.prototype.wait = function( block_time ){
    if ( block_time ) this.timeout = block_time;

    if( this.reserveThread && this.reservedThread ){
      this.reservedThread();
    }

    if( !this.started ){
      return;
    }

    var start_time = (new Date()).getTime();
    var curr_time  = (new Date()).getTime();

    var completed  = false;
    while( (curr_time - start_time) < this.timeout ){
      QCoreApplication.processEvents();
      if( this.complete ){
        completed = true;
        break;
      }
      curr_time  = (new Date()).getTime();
    }
}

/**
 * If started, will block until completion or timeout.
 */
$.oThread.prototype.runSingleThreaded = function( ){
  this.started = true;
  for( var n=0;n<this.list.length;n++ ){
    this.kernel( 0, n, n+1 );
  }
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oProcess class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oProcess.
 * @name        $.oProcess
 * @classdesc
 * Process class that allows user to launch executables outside harmony and get feedback from them.
 * @constructor
 * @param    {string}    bin          The path to the binary executable that will be launched.
 * @param    {string[]}  queryArgs    A string array of the different arguments given to the command.
 *
 * @property {$.oSignal} readyRead    A $.oSignal that can be connected to a callback, emitted every time new messages are outputted by the oProcess. Signature: readyRead(stdout (string))
 * @property {$.oSignal} finished     A $.oSignal that can be connected to a callback, emitted when the oProcess has finished. Signature: finished(returnCode(int), stdout(string))
 * @property {QProcess}  process      the QProcess object wrapped by the $.oProcess object.
 * @property {string}    bin          The path to the binary executable that will be launched.
 * @property {string[]}  queryArgs    A string array of the different arguments given to the command.
 * @property {string}    log          The full log of all the messages outputted over the course of the process lifetime.
 */
$.oProcess = function(bin, queryArgs){
  this.readyRead = new this.$.oSignal()
  this.finished = new this.$.oSignal()
  this.bin = bin;
  this.queryArgs = queryArgs;
  this.process = new QProcess();
  this.readChannel = "All";
  this.log = "";
}


/**
 * Which channel will the process read from. Set before launching the process. can take the values "All", "Output" and "Error".
 * @name $.oProcess#readChannel
 * @type {string}
 */
Object.defineProperty($.oProcess.prototype, 'readChannel', {
  get : function(){
    var merged = (this.process.processChannelMode() == QProcess.MergedChannels);
    if (merged) return "All";
    if (this.process.readChannel == QProcess.StandardOutput) return "Output";
    if (this.process.readChannel == QProcess.StandardError) return "Error";
  },

  set : function(channel){
    if (channel == "All") {
      this.process.setProcessChannelMode(QProcess.MergedChannels);
      this.process.readChannel = QProcess.StandardOutput;
    }else if (channel == "Output"){
      this.process.setProcessChannelMode(QProcess.SeparateChannels);
      this.process.readChannel = QProcess.StandardOutput;
    }else if (channel == "Error"){
      this.process.setProcessChannelMode(QProcess.SeparateChannels);
      this.process.readChannel = QProcess.StandardError;
    }
  }
});


/**
 * kills the process instantly (useful for hanging processes, etc).
 */
$.oProcess.prototype.kill = function(){
  if (!this.process) return;
  this.process.kill()
}

/**
 * Attempts to terminate the process execution by asking it to close itself.
 */
$.oProcess.prototype.terminate = function(){
  if (!this.process) return;
  this.process.terminate()
}

/**
 * Execute a process and read the result as a string.
 * @param {function} [readCallback]         User can provide a function to execute when new info can be read. This function's first argument will contain the available output from the process.
 * @param {function} [finishedCallback]     User can provide a function to execute when new process has finished
 * @example
 * // This example from the openHarmony oScene.renderWriteNodes() function code
 * // uses the oProcess class to launch an async process and print its progress
 * // to the MessageLog.
 *
 * // declaring the binary called by the process
 * var harmonyBin = specialFolders.bin+"/HarmonyPremium";
 *
 * // building the list of arguments based on user provided input
 * var args = ["-batch", "-frames", startFrame, endFrame, "-res", resX, resY];
 *
 * // different arguments depending on wether the scene is stored on the database or offline
 * if (this.online){
 *   args.push("-env");
 *   args.push(this.environnement);
 *   args.push("-job");
 *   args.push(this.job);
 *   args.push("-scene");
 *   args.push(this.name);
 * }else{
 *   args.push(this.stage);
 * }
 *
 * // Create the process with the arguments above
 * var p = new this.$.oProcess(harmonyBin, args);
 * p.readChannel = "All"; // specifying which channel of the process we will listen to: here we listen to both stdout and error.
 *
 * // creating an async process
 * if (renderInBackground){
 *   var length = endFrame - startFrame;
 *
 *   // Creating a function to respond to new readable information on the output channel.
 *   // This function takes a "message" argument which will contain the returned output of the process.
 *
 *   var progressDialogue = new this.$.oProgressDialog("Rendering : ",length,"Render Write Nodes", true);
 *   var self = this;
 *
 *   var renderProgress = function(message){
 *     // parsing the message to find a Rendered frame number.
 *     var progressRegex = /Rendered Frame ([0-9]+)/igm;
 *     var matches = [];
 *     while (match = progressRegex.exec(message)) {
 *       matches.push(match[1]);
 *     }
 *     if (matches.length!=0){
 *       // if a number is found, we compare it to the total frames in the render to deduce a completion percentage.
 *       var progress = parseInt(matches.pop(),10)
 *       progressDialogue.label = "Rendering Frame: "+progress+"/"+length
 *       progressDialogue.value = progress;
 *       var percentage = Math.round(progress/length*100);
 *       self.$.log("render : "+percentage+"% complete");
 *     }
 *   }
 *
 *   // Creating a function that will trigger when process exits.
 *   // This function can take an "exit code" argument that will tell if the process terminated without problem.
 *
 *   var renderFinished = function(exitCode){
 *     // here we simply output that the render completed successfully.
 *     progressDialogue.label = "Rendering Finished"
       progressDialogue.value = length;
 *     self.$.log(exitCode+" : render finished");
 *   }
 *
 *   // launching the process in async mode by providing true as first argument, and then the functions created above.
 *
 *   p.launchAndRead(renderProgress, renderFinished);
 *   this.$.log("Starting render of scene "+this.name);

 * }else{
 *
 *   // if we don't want to use an async process and prefer to freeze the execution while waiting, we can simply call:
 *   var readout  = p.execute();
 * }
 *
 * // we return the output of the process in case we didn't use async.
 * return readout
 *
 */
$.oProcess.prototype.launchAndRead = function(readCallback, finishedCallback){
  if (typeof timeOut === 'undefined') var timeOut = -1;

  var bin = this.bin.split("/");
	var app = bin.pop();
	var directory = bin.join("\\");

  var p = this.process;
	p.setWorkingDirectory(directory);

  this.$.debug("Executing Process with arguments : "+this.bin+" "+this.queryArgs.join(" "), this.$.DEBUG_LEVEL.LOG);

  // start process and attach functions to "readyRead" and "finished" signals
  function onRead(){
    var stdout = this.read();
    this.readyRead.emit(stdout);
  }

  function onFinished(returnCode){
    var stdout = this.read(); // reading any extra messages issued since last read() call to add to log
    this.finished.emit(returnCode, this.log);
  }

  p.readyRead.connect(this, onRead);
  p["finished(int)"].connect(this, onFinished);

  if (typeof readCallback !== 'undefined') this.readyRead.connect(readCallback);
  if (typeof finishedCallback !== 'undefined') this.finished.connect(onFinished);

  p.start(app, this.queryArgs);
}


/**
 * read the output of a process.
 * @return {string}   The lines as returned by the process since the last "read" instruction
 */
$.oProcess.prototype.read = function (){
  var p = this.process;
  if (p.readChannel == QProcess.StandardOutput){
    var readOut = p.readAllStandardOutput();
  }else {
    var readOut = p.readAllStandardError();
  }

  var output = new QTextStream(readOut).readAll();
  while(output.slice(-1)== "\n" || output.slice(-1)== "\r"){
    output = output.slice (0, -1);
  }

  this.log += output;

  return output;
}


/**
 * Execute a process and waits for the end of the execution.
 * @return {string}   The lines as returned by the process.
 */
$.oProcess.prototype.execute = function(){
  this.$.debug("Executing Process with arguments : "+this.bin+" "+this.queryArgs.join(" "), this.$.DEBUG_LEVEL.LOG);

  var p = this.process;
	p.start( this.bin, this.queryArgs );
	p.waitForFinished(-1);
  var result = this.read();
  return result;
}


/**
 * Execute a process as a separate application, which doesn't block the script execution and stops the script from interacting with it further.
 */
$.oProcess.prototype.launchAndDetach = function(){
  QProcess.startDetached(this.bin, this.queryArgs);
}



//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//         $.oSignal class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for $.oSignal.
 * @name        $.oSignal
 * @classdesc
 * A Qt like custom signal that can be defined, connected and emitted.
 * As this signal is not actually threaded, the connected callbacks will be executed
 * directly when the signal is emited, and the rest of the code will execute after.
 * @constructor
 */
$.oSignal = function(type){
  // this.emitType = type;
  this.connexions = [];
  this.blocked = false;
}


/**
 * Register the calling object and the slot.
 * @param {object} context
 * @param {function} slot
 */
$.oSignal.prototype.connect = function (context, slot){
  // support slot.connect(callback) synthax
  if (typeof slot === 'undefined'){
    var slot = context;
    var context = null;
  }
  this.connexions.push ({context: context, slot:slot});
}


/**
 * Remove a connection registered with this Signal.
 * @param {function} [slot] the function to disconnect from the signal. If not specified, all connexions will be removed.
 */
$.oSignal.prototype.disconnect = function(slot){
  if (typeof slot === "undefined"){
    this.connexions = [];
    return
  }

  for (var i in this.connexions){
    if (this.connexions[i].slot == slot){
      this.connexions.splice(i, 1);
    }
  }
}


/**
 * Call the slot function using the provided context and and any arguments.
 */
$.oSignal.prototype.emit = function () {
  if (this.blocked) return;

  // if (!(value instanceof this.type)){ // can't make it work for primitives, might try to fix later?
  //   throw new error ("Signal can't emit type "+ (typeof value) + ". Must be : " + this.type)
  // }

  var args = [];
  for (var i=0; i<arguments.length; i++){
    args.push(arguments[i]);
  }

  this.$.debug("emiting signal with "+ args, this.$.DEBUG_LEVEL.LOG);

  for (var i in this.connexions){
    var context = this.connexions[i].context;
    var slot = this.connexions[i].slot;

    // support connecting signals to each other
    if (slot instanceof this.$.oSignal){
      slot.emit.apply(context, args)
    }else{
      slot.apply(context, args);
    }
  }
}


$.oSignal.prototype.toString = function(){
  return "Signal";
}

