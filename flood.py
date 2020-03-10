import asyncio
import logging
import random
import string

import aiohttp

import config as server_config

logging.basicConfig(level=logging.DEBUG)
base_url = f'http://{server_config.HOST}:{server_config.PORT}/'

TOTAL = 1


async def generate_kv(size: int = 1000):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
        for _ in range(size):
            try:
                value = generate_value()
                response = await session.put(base_url, params={'value': value})
                response.raise_for_status()
                logging.info(f'value {value} set')
            except asyncio.TimeoutError:
                logging.warning(f'timeout error')


def generate_value(length: int = 10):
    return ''.join(random.sample(string.ascii_letters, k=length))


async def api_request(method, params=None, session: aiohttp.ClientSession = None, on_success: str = None):
    local_session = session is None
    if local_session:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1))
    try:
        response = await session.request(method, base_url, params=params or {})
        response.raise_for_status()
        if on_success:
            logging.info(on_success)
        return await response.json()
    except aiohttp.ContentTypeError:
        pass
    except aiohttp.ClientError as e:
        logging.warning(f'client error {e} on {method}')
    except asyncio.TimeoutError:
        logging.warning(f'timeout error')
    finally:
        if local_session:
            await session.close()


async def generate_insert(session: aiohttp.ClientSession = None):
    value = generate_value()
    await api_request('PUT', {'value': value}, session=session, on_success=f'value {value} set')


async def generate_get(session: aiohttp.ClientSession = None):
    result = await api_request('GET', session=session, on_success='values selected')
    global TOTAL
    TOTAL = len(result)


async def generate_update(session: aiohttp.ClientSession = None):
    id = random.randint(1, TOTAL)
    value = generate_value()
    return await api_request('POST', {'id': id, 'value': value},
                             session=session, on_success=f'value with {id} was updated')


async def generate_delete(session: aiohttp.ClientSession = None):
    id = random.randint(1, TOTAL)
    return await api_request('DELETE', {'id': id}, session=session, on_success=f'value with {id} was deleted')


async def run():
    async with aiohttp.ClientSession() as session:
        size = 1000
        tasks = []
        tasks.extend(generate_insert(session) for _ in range(size))
        tasks.extend(generate_update(session) for _ in range(size))
        tasks.extend(generate_get(session) for _ in range(size))
        tasks.extend(generate_delete(session) for _ in range(size))
        random.shuffle(tasks)
        return await asyncio.wait(tasks)


asyncio.run(run())
