import asyncio

from wsrpc_aiohttp import WSRPCClient

"""
    Simple testing Python client for wsrpc_aiohttp
    Calls sequentially multiple methods on server
"""

loop = asyncio.get_event_loop()


async def main():
    print("main")
    client = WSRPCClient("ws://127.0.0.1:8099/ws/",
                         loop=asyncio.get_event_loop())

    client.add_route('notify', notify)
    await client.connect()
    print("connected")
    print(await client.proxy.ExternalApp1.server_function_one())
    print(await client.proxy.ExternalApp1.server_function_two())
    print(await client.proxy.ExternalApp1.server_function_three())
    print(await client.proxy.ExternalApp1.server_function_four(foo="one"))
    await client.close()


def notify(socket, *args, **kwargs):
    print("called from server")


if __name__ == "__main__":
    # loop.run_until_complete(main())
    asyncio.run(main())
