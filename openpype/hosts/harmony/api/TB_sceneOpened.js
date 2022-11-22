/* global QTcpSocket, QByteArray, QDataStream, QTimer, QTextCodec, QIODevice, QApplication, include */
/* global QTcpSocket, QByteArray, QDataStream, QTimer, QTextCodec, QIODevice, QApplication, include */
/*
Avalon Harmony Integration - Client
-----------------------------------

This script implements client communication with Avalon server to bridge
gap between Python and QtScript.

*/
/* jshint proto: true */
var LD_OPENHARMONY_PATH = System.getenv('LIB_OPENHARMONY_PATH');
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH + '/openHarmony.js';
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH.replace(/\\/g, "/");
include(LD_OPENHARMONY_PATH);
this.__proto__['$'] = $;

function Client() {
    var self = this;
    /** socket */
    self.socket = new QTcpSocket(this);
    /** receiving data buffer */
    self.received = '';
    self.messageId = 1;
    self.buffer = new QByteArray();
    self.waitingForData = 0;


    /**
     * pack number into bytes.
     * @function
     * @param   {int} num 32 bit integer
     * @return  {string}
     */
    self.pack = function(num) {
        var ascii='';
        for (var i = 3; i >= 0; i--) {
          var hex = ((num >> (8 * i)) & 255).toString(16);
          if (hex.length < 2){
            ascii += "0";
          }
          ascii += hex;
        }
        return ascii;
    };

    /**
     * unpack number from string.
     * @function
     * @param   {string} numString bytes to unpack
     * @return  {int} 32bit unsigned integer.
     */
    self.unpack = function(numString) {
        var result=0;
        for (var i = 3; i >= 0; i--) {
            result += numString.charCodeAt(3 - i) << (8 * i);
        }
        return result;
    };

    /**
     * prettify json for easier debugging
     * @function
     * @param   {object} json json to process
     * @return  {string} prettified json string
     */
    self.prettifyJson = function(json) {
        var jsonString = JSON.stringify(json);
        return JSON.stringify(JSON.parse(jsonString), null, 2);
    };

    /**
     * Log message in debug level.
     * @function
     * @param {string} data - message
     */
    self.logDebug = function(data) {
        var message = typeof(data.message) != 'undefined' ? data.message : data;
        MessageLog.trace('(DEBUG): ' + message.toString());
    };

    /**
     * Log message in info level.
     * @function
     * @param {string} data - message
     */
    self.logInfo = function(data) {
        var message = typeof(data.message) != 'undefined' ? data.message : data;
        MessageLog.trace('(DEBUG): ' + message.toString());
    };

    /**
     * Log message in warning level.
     * @function
     * @param {string} data - message
     */
    self.logWarning = function(data) {
        var message = typeof(data.message) != 'undefined' ? data.message : data;
        MessageLog.trace('(INFO): ' + message.toString());
    };

    /**
     * Log message in error level.
     * @function
     * @param {string} data - message
     */
    self.logError = function(data) {
        var message = typeof(data.message) != 'undefined' ? data.message : data;
        MessageLog.trace('(ERROR): ' +message.toString());
    };

    /**
     * Show message in Harmony GUI as popup window.
     * @function
     * @param {string} msg - message
     */
    self.showMessage = function(msg) {
        MessageBox.information(msg);
    };

    /**
     * Implement missing setTimeout() in Harmony.
     * This calls once given function after some interval in milliseconds.
     * @function
     * @param {function} fc       function to call.
     * @param {int}      interval interval in milliseconds.
     * @param {boolean}  single   behave as setTimeout or setInterval.
     */
    self.setTimeout = function(fc, interval, single) {
        var timer = new QTimer();
        if (!single) {
            timer.singleShot = true; // in-case if setTimout and false in-case of setInterval
        } else {
            timer.singleShot = single;
        }
        timer.interval = interval; // set the time in milliseconds
        timer.singleShot = true; // in-case if setTimout and false in-case of setInterval
        timer.timeout.connect(this, function(){
            fc.call();
        });
        timer.start();
    };

    /**
     * Process recieved request. This will eval recieved function and produce
     * results.
     * @function
     * @param  {object} request - recieved request JSON
     * @return {object} result of evaled function.
     */
    self.processRequest = function(request) {
        var mid = request.message_id;
        if (typeof request.reply !== 'undefined') {
            self.logDebug('['+ mid +'] *** received reply.');
            return;
        }
        self.logDebug('['+ mid +'] - Processing: ' + self.prettifyJson(request));
        var result = null;

        if (typeof request.script !== 'undefined') {
            self.logDebug('[' + mid + '] Injecting script.');
            try {
                eval.call(null, request.script);
            } catch (error) {
                self.logError(error);
            }
        } else if (typeof request["function"] !== 'undefined') {
            try {
                var _func = eval.call(null, request["function"]);

                if (request.args == null) {
                    result = _func();
                } else {
                    result = _func(request.args);
                }
            } catch (error) {
                result = 'Error processing request.\n' +
                         'Request:\n' +
                         self.prettifyJson(request) + '\n' +
                         'Error:\n' + error;
            }
        } else {
            self.logError('Command type not implemented.');
        }

        return result;
    };

    /**
     * This gets called when socket received new data.
     * @function
     */
    self.onReadyRead = function() {
        var currentSize = self.buffer.size();
        self.logDebug('--- Receiving data ( '+ currentSize + ' )...');
        var newData = self.socket.readAll();
        var newSize = newData.size();
        self.buffer.append(newData);
        self.logDebug('  - got ' + newSize + ' bytes of new data.');
        self.processBuffer();
    };

    /**
     * Process data received in buffer.
     * This detects messages by looking for header and message length.
     * @function
     */
    self.processBuffer = function() {
        var length = self.waitingForData;
        if (self.waitingForData == 0) {
            // read header from the buffer and remove it
            var header_data = self.buffer.mid(0, 6);
            self.buffer = self.buffer.remove(0, 6);

            // convert header to string
            var header = '';
            for (var i = 0; i < header_data.size(); ++i) {
                // data in QByteArray come out as signed bytes.
                var unsigned = header_data.at(i) & 0xff;
                header = header.concat(String.fromCharCode(unsigned));
            }

            // skip 'AH' and read only length, unpack it to integer
            header = header.substr(2);
            length = self.unpack(header);
        }

        var data = self.buffer.mid(0, length);
        self.logDebug('--- Expected: ' + length + ' | Got: ' + data.size());
        if (length > data.size()) {
            // we didn't received whole message.
            self.waitingForData = length;
            self.logDebug('... waiting for more data (' + length + ') ...');
            return;
        }
        self.waitingForData = 0;
        self.buffer.remove(0, length);

        for (var j = 0; j < data.size(); ++j) {
            self.received = self.received.concat(String.fromCharCode(data.at(j)));
        }

        // self.logDebug('--- Received: ' + self.received);
        var to_parse = self.received;
        var request = JSON.parse(to_parse);
        var mid = request.message_id;
        // self.logDebug('[' + mid + '] - Request: ' + '\n' + JSON.stringify(request));
        self.logDebug('[' + mid + '] Recieved.');

        request.result = self.processRequest(request);
        self.logDebug('[' + mid + '] Processing done.');
        self.received = '';

        if (request.reply !== true) {
            request.reply = true;
            self.logDebug('[' + mid + '] Replying.');
            self._send(JSON.stringify(request));
        }

        if ((length < data.size()) || (length < self.buffer.size())) {
            // we've received more data.
            self.logDebug('--- Got more data to process ...');
            self.processBuffer();
        }
    };

    /**
     * Run when Harmony connects to server.
     * @function
     */
    self.onConnected = function() {
        self.logDebug('Connected to server ...');
        self.lock = false;
        self.socket.readyRead.connect(self.onReadyRead);
        var app = QCoreApplication.instance();

        app.avalonClient.send(
            {
                'module': 'openpype.lib',
                'method': 'emit_event',
                'args': ['application.launched']
            }, false);
    };

    self._send = function(message) {
      /** Harmony 21.1 doesn't have QDataStream anymore.

      This means we aren't able to write bytes into QByteArray so we had
      modify how content lenght is sent do the server.
      Content lenght is sent as string of 8 char convertible into integer
      (instead of 0x00000001[4 bytes] > "000000001"[8 bytes]) */
      var codec_name = new QByteArray().append("UTF-8");

      var codec = QTextCodec.codecForName(codec_name);
      var msg = codec.fromUnicode(message);
      var l = msg.size();
      var header = new QByteArray().append('AH').append(self.pack(l));
      var coded = msg.prepend(header);

      self.socket.write(coded);
      self.logDebug('Sent.');
    };

    self.waitForLock = function() {
        if (self._lock === false) {
            self.logDebug('>>> Unlocking ...');
            return;
        } else {
            self.logDebug('Setting timer.');
            self.setTimeout(self.waitForLock, 300);
        }
    };

    /**
     * Send request to server.
     * @param {object} request - json encoded request.
     */
    self.send = function(request) {
        request.message_id = self.messageId;
        if (typeof request.reply == 'undefined') {
            self.logDebug("[" + self.messageId + "] sending:\n" + self.prettifyJson(request));
        }
        self._send(JSON.stringify(request));
    };

    /**
     * Executed on disconnection.
     */
    self.onDisconnected = function() {
        self.socket.close();
    };

    /**
     * Disconnect from server.
     */
    self.disconnect = function() {
        self.socket.close();
    };

    self.socket.connected.connect(self.onConnected);
    self.socket.disconnected.connect(self.onDisconnected);
}

/**
 * Entry point, creating Avalon Client.
 */
function start() {
    var self = this;
    /** hostname or ip of server - should be localhost */
    var host = '127.0.0.1';
    /** port of the server */
    var port = parseInt(System.getenv('AVALON_HARMONY_PORT'));

    // Attach the client to the QApplication to preserve.
    var app = QCoreApplication.instance();

    if (app.avalonClient == null) {
        app.avalonClient = new Client();
        app.avalonClient.socket.connectToHost(host, port);
    }
    var mainWindow = null;
    var widgets = QApplication.topLevelWidgets();
    for (var i = 0 ; i < widgets.length; i++) {
      if (widgets[i] instanceof QMainWindow){
          mainWindow = widgets[i];
      }
    }
    var menuBar = mainWindow.menuBar();
    var actions = menuBar.actions();
    app.avalonMenu = null;

    for (var i = 0 ; i < actions.length; i++) {
        label = System.getenv('AVALON_LABEL');
        if (actions[i].text == label) {
            app.avalonMenu = true;
        }
    }

    var menu = null;
    if (app.avalonMenu == null) {
        menu = menuBar.addMenu(System.getenv('AVALON_LABEL'));
    }
    // menu = menuBar.addMenu('Avalon');

    /**
     * Show creator
     */
    self.onCreator = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['creator']
        }, false);
    };

    var action = menu.addAction('Create...');
    action.triggered.connect(self.onCreator);


    /**
     * Show Workfiles
     */
    self.onWorkfiles = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['workfiles']
        }, false);
    };
    if (app.avalonMenu == null) {
        action = menu.addAction('Workfiles...');
        action.triggered.connect(self.onWorkfiles);
    }

    /**
     * Show Loader
     */
    self.onLoad = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['loader']
        }, false);
    };
    // add Loader item to menu
    if (app.avalonMenu == null) {
        action = menu.addAction('Load...');
        action.triggered.connect(self.onLoad);
    }

    /**
     * Show Publisher
     */
    self.onPublish = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['publish']
        }, false);
    };
    // add Publisher item to menu
    if (app.avalonMenu == null) {
        action = menu.addAction('Publish...');
        action.triggered.connect(self.onPublish);
    }

    /**
     * Show Scene Manager
     */
    self.onManage = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['sceneinventory']
        }, false);
    };
    // add Scene Manager item to menu
    if (app.avalonMenu == null) {
        action = menu.addAction('Manage...');
        action.triggered.connect(self.onManage);
    }

    /**
      * Show Subset Manager
      */
    self.onSubsetManage = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['subsetmanager']
        }, false);
    };
    // add Subset Manager item to menu
    if (app.avalonMenu == null) {
        action = menu.addAction('Subset Manager...');
        action.triggered.connect(self.onSubsetManage);
    }

    /**
      * Show Experimental dialog
      */
    self.onExperimentalTools = function() {
        app.avalonClient.send({
            'module': 'openpype.hosts.harmony.api.lib',
            'method': 'show',
            'args': ['experimental_tools']
        }, false);
    };
    // add Subset Manager item to menu
    if (app.avalonMenu == null) {
        action = menu.addAction('Experimental Tools...');
        action.triggered.connect(self.onExperimentalTools);
    }

    // FIXME(antirotor): We need to disable `on_file_changed` now as is wreak
    // havoc when "Save" is called multiple times and zipping didn't finished yet
    /*

    // Watch scene file for changes.
    app.onFileChanged = function(path)
    {
      var app = QCoreApplication.instance();
      if (app.avalonOnFileChanged){
        app.avalonClient.send(
          {
            'module': 'avalon.harmony.lib',
            'method': 'on_file_changed',
            'args': [path]
          },
          false
        );
      }

      app.watcher.addPath(path);
    };


	app.watcher = new QFileSystemWatcher();
	scene_path = scene.currentProjectPath() +"/" + scene.currentVersionName() + ".xstage";
	app.watcher.addPath(scenePath);
	app.watcher.fileChanged.connect(app.onFileChanged);
  app.avalonOnFileChanged = true;
  */
    app.onFileChanged = function(path) {
        // empty stub
        return path;
    };
}

function ensureSceneSettings() {
  var app = QCoreApplication.instance();
  app.avalonClient.send(
    {
      "module": "openpype.hosts.harmony.api",
      "method": "ensure_scene_settings",
      "args": []
    },
    false
  );
}

function TB_sceneOpened()
{
  start();
}
