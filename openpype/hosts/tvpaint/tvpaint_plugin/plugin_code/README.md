README for TVPaint Avalon plugin
================================
Introduction
------------
This project is dedicated to integrate Avalon functionality to TVPaint.
This implementation is using TVPaint plugin (C/C++) which can communicate with python process. The communication should allow to trigger tools or pipeline functions from TVPaint and accept requests from python process at the same time.

Current implementation is based on websocket protocol, using json-rpc communication (specification 2.0). Project is in beta stage, tested only on Windows.

To be able to load plugin, environment variable `WEBSOCKET_URL` must be set otherwise plugin won't load at all. Plugin should not affect TVPaint if python server crash, but buttons won't work.

## Requirements - Python server
- python >= 3.6
- aiohttp
- aiohttp-json-rpc

### Windows
- pywin32 - required only for plugin installation

## Requirements - Plugin compilation
- TVPaint SDK - Ask for SDK on TVPaint support.
- Boost 1.72.0 - Boost is used across other plugins (Should be possible to use different version with CMakeLists modification)
- Websocket++/Websocketpp - Websocket library (https://github.com/zaphoyd/websocketpp)
- OpenSSL library - Required by Websocketpp
- jsonrpcpp - C++ library handling json-rpc 2.0 (https://github.com/badaix/jsonrpcpp)
- nlohmann/json - Required for jsonrpcpp (https://github.com/nlohmann/json)

### jsonrpcpp
This library has `nlohmann/json` as it's part, but current `master` has old version which has bug and probably won't be possible to use library on windows without using last `nlohmann/json`.

## TODO
- modify code and CMake to be able to compile on MacOS/Linux
- separate websocket logic from plugin logic
- hide buttons and show error message if server is closed
