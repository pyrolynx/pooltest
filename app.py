import asyncio
import contextlib
import logging

import aiopg
import psycopg2
from aiohttp import web
import config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('app')


class PoolManager:
    async def monitor(self):
        while not self._pool.closed:
            log.info(f'Pool: free - {self._pool.freesize}, used - {len(self._pool._used)}')
            await asyncio.sleep(1)
        log.info(f'pool closed')

    def __init__(self, pool):
        self._pool: aiopg.pool.Pool = pool

    async def acquire(self):
        return await self._pool.acquire()

    @contextlib.asynccontextmanager
    async def __call__(self):
        conn = await self.acquire()
        try:
            yield conn
        finally:
            self._pool.release(conn)


db: PoolManager


async def get(request: web.Request):
    id = int(request.query.get('id') or 0)
    query = f"SELECT id, value FROM kv"
    args = tuple()
    if id:
        query = f"{query} WHERE id=%s"
        args = (id,)
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, args)
            data = await cur.fetchall()
    return web.json_response(data)


async def put(request: web.Request):
    value = request.query.get('value')
    if value is None:
        raise web.HTTPBadRequest
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"INSERT INTO kv (value) VALUES (%s)", (value,))
    raise web.HTTPOk


async def post(request: web.Request):
    params = request.query.get('value'), int(request.query.get('id') or 0)
    if not all(params):
        raise web.HTTPBadRequest
    async with db() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(f"UPDATE kv SET value = %s WHERE id=%s", params)
            except psycopg2.DatabaseError:
                log.exception('db error')
                raise web.HTTPInternalServerError
    raise web.HTTPOk


async def delete(request: web.Request):
    id = int(request.query.get('id') or 0)
    if not id:
        raise web.HTTPBadRequest
    async with db() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute(f"DELETE FROM kv WHERE id=%s", (id,))
            except psycopg2.DatabaseError:
                log.exception('db error')
                raise web.HTTPInternalServerError
    raise web.HTTPOk()


async def prepare_app(app: web.Application) -> web.Application:
    pool = await aiopg.create_pool(dsn=config.DB_DSN, pool_recycle=config.DB_POOL_RECYCLE)
    global db
    app['db'] = db = PoolManager(pool)
    loop = asyncio.get_running_loop()
    app['monitor'] = loop.create_task(db.monitor())
    return app


async def cleanup_app(app: web.Application) -> web.Application:
    app['db']._pool.close()
    await app['db']._pool.wait_closed()
    await asyncio.wait_for(app['monitor'], 2.0)
    return app


def get_app():
    app = web.Application()
    app.on_startup.append(prepare_app)
    app.on_shutdown.append(cleanup_app)

    app.router.add_get('/', get)
    app.router.add_post('/', post)
    app.router.add_put('/', put)
    app.router.add_delete('/', delete)
    return app


if __name__ == '__main__':
    app = get_app()
    web.run_app(app, host=config.HOST, port=config.PORT, shutdown_timeout=0, access_log=None)
