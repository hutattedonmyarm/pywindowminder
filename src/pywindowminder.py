import asyncio
import importlib.machinery
import datetime
from enum import Enum
import inspect
import logging
import glob
import os
import types
from typing import Any, Dict, Optional
from aiohttp import web

class Status(Enum):
    OPEN = 1
    CLOSED = 2
    UNDETERMINED = 3

class Pywindowminder:
    """Initializes Pywindowminder and configures receiver plugins
    Keyword Arguments:
        receiver_dir {Optional[os.PathLike]} -- Directory which contains additional receivers (default: {receivers})
        receiver_config {Optional[Dict[str, Any]]} -- Configuration for receivers (default: {None})
        required_open_seconds_per_hour {int} -- How many seconds per hour the window should be open (default: {5*60})
    """
    def __init__(
        self,
        receiver_dir: Optional[os.PathLike] = 'receivers',
        receiver_config: Optional[Dict[str, Any]] = None,
        required_open_seconds_per_hour: int = 5*60):

        self.receivers = []
        receivers_dirs = [
            os.path.join(os.path.dirname(__file__), 'receivers'),
        ]

        self.timeline = {}
        self.required_open_seconds_per_hour = required_open_seconds_per_hour

        if not receiver_config:
            receiver_config = {}

        if receiver_dir:
            receivers_dirs.append(receiver_dir)

        for receivers_dir in receivers_dirs:
            logging.info('Loading receivers from: %s', os.path.abspath(receivers_dir))
            for file in glob.iglob(f'{receivers_dir}/*.py'):
                loader = importlib.machinery.SourceFileLoader(os.path.basename(file), file)
                mod = types.ModuleType(loader.name)
                loader.exec_module(mod)
                if not (hasattr(mod, 'name') and hasattr(mod, 'version')):
                    logging.debug('Skipping %s', file)
                    continue
                logging.info('Found receiver: %s v%s', mod.name, mod.version) # pylint: disable=no-member
                if mod.name in receiver_config:  # pylint: disable=no-member
                    try:
                        mod.configure(receiver_config[mod.name]) # pylint: disable=no-member
                        self.receivers.append(mod)
                    except Exception as e:
                        logging.exception('Error configuring receiver %s. Disabling! %s', mod.name, e) # pylint: disable=no-member
                else:
                    self.receivers.append(mod)

    """Registers a window open event
    Keyword Arguments:
        timestamp {Optional[int]} -- Timestamp of the event. Uses the current time if None (default: {None})
    """
    def register_open(self, timestamp:Optional[int] = None):
        if not timestamp:
            timestamp = int(datetime.datetime.now().timestamp())

        self.timeline[timestamp] = Status.OPEN
        logging.info('Opened. Timestamp: %d', timestamp)

    """Registers a window close event
    Keyword Arguments:
        timestamp {Optional[int]} -- Timestamp of the event. Uses the current time if None (default: {None})
    """
    def register_close(self, timestamp:Optional[int] = None):
        if not timestamp:
            timestamp = int(datetime.datetime.now().timestamp())

        self.timeline[timestamp] = Status.CLOSED
        logging.info('Closed. Timestamp: %d', timestamp)

    def _seconds_open_last_hour(self) -> int:
        timestamp = int(datetime.datetime.now().timestamp())
        ts_hour_ago = timestamp - 60*60
        events_in_last_hour = {k : v for k, v in self.timeline.items() if k >= ts_hour_ago}
        seconds_window_open = 0
        last_event_ts = ts_hour_ago
        last_status = Status.UNDETERMINED

        if self.timeline and not events_in_last_hour:
            #No events in the last hour, but before. Check last known status
            last_event_ts = max(self.timeline)
            last_status = self.timeline[last_event_ts]
            logging.debug('No events during the last hour. Using last known status %s at %d', last_status, last_event_ts)
            return 60*60 if last_status == Status.OPEN else 0

        for ts in events_in_last_hour:
            status = events_in_last_hour[ts]
            if status == last_status:
                continue
            diff = ts - last_event_ts
            logging.debug('Event at %d: %s. Seconds since last: %d', ts, status, diff)
            if status == Status.CLOSED: #now closed, was open
                seconds_window_open += diff
            last_status = status
            last_event_ts = ts
        if last_status == Status.OPEN:
            seconds_window_open += timestamp - last_event_ts
        self.timeline = events_in_last_hour #Only save last hour of events
        return seconds_window_open

    """Checks window open duration and notifies all receivers"""
    def check_and_notify_block(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.check_and_notify())


    """Checks window open duration and notifies all receivers"""
    async def check_and_notify(self):
        logging.info('Checking...')
        seconds_window_open = self._seconds_open_last_hour()
        logging.info('Window was %ss opened during the last hour', seconds_window_open)
        needs_opening = seconds_window_open < self.required_open_seconds_per_hour
        for receiver in self.receivers:
            logging.info('Notifying receiver %s', receiver.name)
            try:
                is_coroutine = inspect.iscoroutinefunction(receiver.notify)
                sig = inspect.signature(receiver.notify)
                has_parameter = 'seconds_window_open' in sig.parameters and 'required_open_seconds_per_hour' in sig.parameters
                if is_coroutine and has_parameter:
                    await receiver.notify(needs_opening, seconds_window_open, self.required_open_seconds_per_hour)
                elif is_coroutine:
                    await receiver.notify(needs_opening)
                elif has_parameter:
                    receiver.notify(needs_opening, seconds_window_open, self.required_open_seconds_per_hour)
                else:
                    receiver.notify(needs_opening)
            except Exception as e:
                logging.error('Notifying receiver %s failed: %s', receiver.name, e)
