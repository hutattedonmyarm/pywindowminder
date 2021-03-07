import asyncio
from pywindowminder.pywindowminder import Pywindowminder
import logging
import os
import sys
from typing import Any, Dict, Optional

from aiohttp import web

class Server:
    """Initializes the server
    Keyword Arguments:
        host {str} -- Host address (default: {'0.0.0.0'})
        port_number {int} -- Port on which the server can be reached (default: {8080})
        check_interval {int} -- Time in seconds between automated checks (default: {60})
        receiver_config {Optional[Dict[str, Any]]} -- Port on which the server can be reached (default: {{
            'Das Keyboard local REST client': {
                'key': 'KEY_SCROLL_LOCK',
                'device': 'DK4QPID',
                'color_needs_open': '#FF0000',
                'color_enough_open': None,
                'effect_needs_open': 'BREATHE',
                'effect_enough_open': None,
            }
        }})

    """
    def __init__(
        self,
        host: str = '0.0.0.0',
        port_number: int = 8080,
        check_interval: Optional[int] = 60,
        receiver_config: Optional[Dict[str, Any]] = None,
        route_opened: str = '/opened',
        route_closed: str = '/closed',
        route_check: str = '/check'):

        self.host = host
        self.port_number = port_number
        self.check_interval = check_interval
        self.receiver_config = receiver_config or {
            'Das Keyboard local REST client': {
                'key': 'KEY_SCROLL_LOCK',
                'device': 'DK4QPID',
                'color_needs_open': '#FF0000',
                'color_enough_open': None,
                'effect_needs_open': 'BREATHE',
                'effect_enough_open': None,
            }
        }
        self.pw = Pywindowminder(receiver_config=self.receiver_config)
        self.app = web.Application(client_max_size=30*1024**2) #30MB max
        self.app.add_routes([
            web.post(route_opened, self._opened),
            web.post(route_closed, self._closed),
            web.post(route_check, self._check),
        ])


    async def _opened(self, request: Optional[web.Request] = None):
        self.pw.register_open()
        await self._check(request)

    async def _closed(self, request: Optional[web.Request] = None):
        self.pw.register_close()
        await self._check(request)

    async def _check(self, request: Optional[web.Request] = None):
        await self.pw.check_and_notify()
        raise web.HTTPAccepted()

    async def _scheduled_check(self):
        if not self.check_interval:
            return
        try:
            await self._check()
        except web.HTTPAccepted:
            pass
        except Exception as e:
            logging.error('Error during check: %s', e)
        await asyncio.sleep(self.check_interval)
        task = asyncio.create_task(self._scheduled_check())
        await task

    async def start_server(self):
        """Starts the server and schedules regular checks"""

        runner = web.AppRunner(self.app)
        logging.info('Starting server on "%s:%d"', self.host, self.port_number)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port_number)
        _ = asyncio.create_task(self._scheduled_check())
        await site.start()
        logging.info('Startup completed.')