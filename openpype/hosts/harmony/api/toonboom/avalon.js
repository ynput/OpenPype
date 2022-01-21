function Client()
{
  var self = this;
  self.socket = new QTcpSocket(this);
  self.received = "";

  self.log_debug = function(data)
  {
      message = typeof(data.message) != "undefined" ? data.message : data;
      MessageLog.trace("(DEBUG): " + message.toString());
  };


  self.log_info = function(data)
  {
      message = typeof(data.message) != "undefined" ? data.message : data;
      MessageLog.trace("(INFO): " + message.toString());
  };


  self.log_warning = function(data)
  {
      message = typeof(data.message) != "undefined" ? data.message : data;
      MessageLog.trace("(WARNING): " + message.toString());
  };


  self.log_error = function(data)
  {
      message = typeof(data.message) != "undefined" ? data.message : data;
      MessageLog.trace("(ERROR): " + message.toString());
  };

  self.process_request = function(request)
  {
    self.log_debug("Processing: " + JSON.stringify(request));
    var result = null;

    if (request["function"] != null)
    {
      try
      {
        var func = eval(request["function"]);

        if (request.args == null)
        {
          result = func();
        }else
        {
          result = func(request.args);
        }
      }

      catch (error)
      {
        result = "Error processing request.\nRequest:\n" + JSON.stringify(request) + "\nError:\n" + error;
      }
    }

    return result;
  };

  self.on_ready_read = function()
  {
    self.log_debug("Receiving data...");
    data = self.socket.readAll();

    if (data.size() != 0)
    {
      for ( var i = 0; i < data.size(); ++i)
      {
        self.received = self.received.concat(String.fromCharCode(data.at(i)));
      }
    }

    self.log_debug("Received: " + self.received);

    request = JSON.parse(self.received);
    self.log_debug("Request: " + JSON.stringify(request));

    request.result = self.process_request(request);

    if (!request.reply)
    {
      request.reply = true;
      self._send(JSON.stringify(request));
    }

    self.received = "";
  };

  self.on_connected = function()
  {
    self.log_debug("Connected to server.");
    self.socket.readyRead.connect(self.on_ready_read);
  };

  self._send = function(message)
  {
    self.log_debug("Sending: " + message);

    var data = new QByteArray();
    outstr = new QDataStream(data, QIODevice.WriteOnly);
    outstr.writeInt(0);
    data.append("UTF-8");
    outstr.device().seek(0);
    outstr.writeInt(data.size() - 4);
    var codec = QTextCodec.codecForUtfText(data);
    self.socket.write(codec.fromUnicode(message));
  };

  self.send = function(request, wait)
  {
    self._send(JSON.stringify(request));

    while (wait)
    {
      try
      {
        JSON.parse(self.received);
        break;
      }
      catch(err)
      {
        self.socket.waitForReadyRead(5000);
      }
    }

    self.received = "";
  };

  self.on_disconnected = function()
  {
    self.socket.close();
  };

  self.disconnect = function()
  {
    self.socket.close();
  };

  self.socket.connected.connect(self.on_connected);
  self.socket.disconnected.connect(self.on_disconnected);
}

function start()
{
  var self = this;
  var host = "127.0.0.1";
  var port = parseInt(System.getenv("AVALON_TOONBOOM_PORT"));

  // Attach the client to the QApplication to preserve.
  var app = QCoreApplication.instance();

  if (app.avalon_client == null)
  {
    app.avalon_client = new Client();
    app.avalon_client.socket.connectToHost(host, port);
  }

  var menu_bar = QApplication.activeWindow().menuBar();
  var menu = menu_bar.addMenu("Avalon");

  self.on_creator = function()
  {
    app.avalon_client.send(
      {
        "module": "avalon.toonboom",
        "method": "show",
        "args": ["creator"]
      },
      false
    );
  };
  var action = menu.addAction("Create...");
  action.triggered.connect(self.on_creator);

  self.on_workfiles = function()
  {
    app.avalon_client.send(
      {
        "module": "avalon.toonboom",
        "method": "show",
        "args": ["workfiles"]
      },
      false
    );
  };
  action = menu.addAction("Workfiles");
  action.triggered.connect(self.on_workfiles);

  self.on_load = function()
  {
    app.avalon_client.send(
        {
          "module": "avalon.toonboom",
          "method": "show",
          "args": ["loader"]
        },
        false
    );
  };
  action = menu.addAction("Load...");
  action.triggered.connect(self.on_load);

  self.on_publish = function()
  {
    app.avalon_client.send(
        {
          "module": "avalon.toonboom",
          "method": "show",
          "args": ["publish"]
        },
        false
    );
  };
  action = menu.addAction("Publish...");
  action.triggered.connect(self.on_publish);

  self.on_manage = function()
  {
    app.avalon_client.send(
        {
          "module": "avalon.toonboom",
          "method": "show",
          "args": ["sceneinventory"]
        },
        false
    );
  };
  action = menu.addAction("Manage...");
  action.triggered.connect(self.on_manage);

  // Watch scene file for changes.
  app.on_file_changed = function(path)
  {
    var app = QCoreApplication.instance();
    if (app.avalon_on_file_changed){
      app.avalon_client.send(
        {
          "module": "avalon.toonboom",
          "method": "on_file_changed",
          "args": [path]
        },
        false
      );
    }

    app.watcher.addPath(path);
  };

	app.watcher = new QFileSystemWatcher();
  extension = ".xstage";
  var product_name = about.productName();
  if (product_name.toLowerCase().indexOf("storyboard") !== -1){
  	extension = ".sboard";
  }
	scene_path = scene.currentProjectPath() + "/" + scene.currentVersionName() + extension;
	app.watcher.addPath(scene_path);
	app.watcher.fileChanged.connect(app.on_file_changed);
  app.avalon_on_file_changed = true;
}
