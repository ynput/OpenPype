Adobe webserver
---------------
Aiohttp (Asyncio) based websocket server used for communication with host
applications, currently only for Adobe (but could be used for any non python
DCC which has websocket client).

This webserver is started in spawned Python process that opens DCC during
its launch, waits for connection from DCC and handles communication going
forward. Server is closed before Python process is killed.

(Different from `openpype/modules/webserver` as that one is running in Tray,
this one is running in spawn Python process.)