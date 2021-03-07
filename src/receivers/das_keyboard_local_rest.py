import aiohttp
import logging

name = 'Das Keyboard local REST client'
version = 0.1

config = {
    'key': 'KEY_SCROLL_LOCK',
    'device': 'DK4QPID',
    'color_needs_open': '#FF0000',
    'color_enough_open': None,
    'effect_needs_open': 'BREATHE',
    'effect_enough_open': None,
    'enabled': True
}

_last_signal = None

def configure(configuration):
    global config
    config.update(configuration)

async def notify(
    needs_opening: bool,
    seconds_window_open: int,
    required_open_seconds_per_hour: int):

    global _last_signal
    global config

    if not config['enabled']:
        pass
    delete_needs_open = config['color_needs_open'] is None or config['effect_needs_open'] is None
    delete_enough_open = config['color_enough_open'] is None or config['effect_enough_open'] is None

    backend_url = 'http://localhost:27301/api/1.0/signals'
    if needs_opening and delete_needs_open or (not needs_opening) and delete_enough_open:
        if not _last_signal:
            logging.debug('Should delete last signal. but not last signal exists')
            return
        logging.debug('Deleting last signal')
        async with aiohttp.ClientSession() as session:
            async with session.delete(f'{backend_url}/{_last_signal}') as p:
                if not p.ok:
                    if p.status == 404: #Signal already deletet
                        pass
                    else:
                        r = await p.read()
                        logging.warning('Error deleting last signal %s', r)
                return


    color = config['color_needs_open'] if needs_opening else config['color_enough_open']
    effect = config['effect_needs_open'] if needs_opening else config['effect_enough_open']
    signal = {
        'zoneId': config['key'],
        'color': color,
        'effect': effect,
        'pid': config['device'],
        'clientName': 'pyWindowminder',
        'message': 'Your window has been closed for too long',
        'name': 'Open your window'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            backend_url,
            json=signal) as p:
                if p.ok:
                    j = await p.json()
                    _last_signal = j['id']
                else:
                    r = await p.read()
                    logging.warning('Error sending %s', r)
                    return

    pass
