This library allows you automatically remind you, to open your window.

The class `Pywindowminder` provides three entry points:
- `def register_open(self, timestamp:Optional[int] = None)` to be called, when a window has been opened
- `def register_close(self, timestamp:Optional[int] = None)` to be called, when a window has been closed
- `async def check_and_notify(self)` calculates how much time the window has been open and notifies the configured receivers. A blocking alternative is available as `def check_and_notify_block(self)`

Uses the current timestamp by default.

Receivers are a simple plugin-based system, allowing to notify devices of the current state.
An example receiver using the Das Keyboard REST API is provided.
A receiver plugin is a Python file, in the `receivers` directory. This directory is configurable in the `Pywindowminder` constructor. By default, it's `receivers`, in the working directory. It needs to define a `name` and `version`. It may contain function `def configure(configuration):` which is called during the initialization. A configuration can be provided to the contructor of `Pywindowminder`:

```
from pywindowminder import Pywindowminder
config = {
    'Das Keyboard local REST client': {
        'key': 'KEY_SCROLL_LOCK',
        'device': 'DK4QPID',
        'color_needs_open': '#FF0000',
        'color_enough_open': None,
        'effect_needs_open': 'BREATHE',
        'effect_enough_open': None,
        'enabled': True
    }
}
pw = Pywindowminder(receiver_config=config)
```

The key in the config dictionary is the name of the plugin, as defined in its `name` property.

A plugin needs to define a notify function. Accepted are any of the following signatures:
- `async def notify(needs_opening: bool, seconds_window_open: int, required_open_seconds_per_hour: int)`
- `async def notify(needs_opening: bool)`
- `def notify(needs_opening: bool, seconds_window_open: int, required_open_seconds_per_hour: int)`
- `def notify(needs_opening: bool)`

A more complete package can be found when using `Server`. Simply impoer `from pywindowminder import Server`, instantiate a new `Server` object, and call `server.start_server()`.
Note that `server.start_server()` is async, so it needs to be run suing an event loop.

A fully working example is provided with `__main__.py`. This sets up a webserver running on `0.0.0.0:8080` and accepts POST requests to `/opened`, `/closed`, and `/check`