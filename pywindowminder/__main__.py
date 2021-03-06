import asyncio
from pywindowminder.pywindowminder import Pywindowminder
import logging
import os
import sys
from typing import Optional

from aiohttp import web

PW: Pywindowminder = None

HOST_NAME = '0.0.0.0'
PORT_NUMBER = 8080
CHECK_INTERVAL = 60

async def _opened(request: Optional[web.Request] = None):
    if not PW:
        raise web.HTTPServiceUnavailable()
    PW.register_open()
    await _check(request)

async def _closed(request: Optional[web.Request] = None):
    if not PW:
        raise web.HTTPServiceUnavailable()
    PW.register_close()
    await _check(request)

async def _check(request: Optional[web.Request] = None):
    if not PW:
        raise web.HTTPServiceUnavailable()
    await PW.check_and_notify()
    raise web.HTTPAccepted()

async def _scheduled_check():
    try:
        await _check()
    except web.HTTPAccepted:
        pass
    except Exception as e:
        logging.error('Error during check: %s', e)
    await asyncio.sleep(CHECK_INTERVAL)
    task = asyncio.create_task(_scheduled_check())
    await task


def _create_runner() -> web.AppRunner:
    """
    Creates the Apprunner

    Returns:
        web.AppRunner -- Webrunner for the server
    """
    app = web.Application(client_max_size=30*1024**2) #30MB max
    app.add_routes([
        web.post('/opened', _opened),
        web.post('/closed', _closed),
        web.post('/check', _check),
    ])
    return web.AppRunner(app)

async def start_server(host: str = HOST_NAME, port: int = PORT_NUMBER):
    """Starts the server at the specified hostname and port.
    Does some basic setup (scheduling frequent checks)
    Keyword Arguments:
        host {str} -- Host address (default: {localhost})
        port {int} -- Port on which the server can be reached (default: {specified in config})
    """
    config = {
        'Das Keyboard local REST client': {
            'key': 'KEY_SCROLL_LOCK',
            'device': 'DK4QPID',
            'color_needs_open': '#FF0000',
            'color_enough_open': None,
            'effect_needs_open': 'BREATHE',
            'effect_enough_open': None,
        }
    }

    global PW
    PW = Pywindowminder(receiver_config=config)
    runner = _create_runner()
    await runner.setup()
    logging.info('Starting server on "%s:%d"', host, port)
    site = web.TCPSite(runner, host, port)
    _ = asyncio.create_task(_scheduled_check())
    await site.start()
    logging.info('Startup completed.')

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    LOOP = asyncio.get_event_loop()
    LOOP.run_until_complete(start_server())
    LOOP.run_forever()
