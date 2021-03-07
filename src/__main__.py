import asyncio
from pywindowminder import Server
import logging
import sys


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    server = Server()
    LOOP = asyncio.get_event_loop()
    LOOP.run_until_complete(server.start_server())
    LOOP.run_forever()
