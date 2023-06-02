from __future__ import annotations

import multiprocessing as mp
import websockets.server
import asyncio
import json
import base64
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitorServer:
    def __init__(self, monitor_queue: mp.Queue):
        self.monitor_queue = monitor_queue
        self.clients = set()
        self.monitor_queue_polling_thread = None

    async def serve(self, websocket):
        self.clients.add(websocket)
        logger.info(f'New monitor connection from {websocket.remote_address}')
        # Never close the connection
        await asyncio.Future()

    async def broadcast(self, data):
        # Possible data types:
        #   - image: {'type': 'image', 'data': bytes}
        #   - directions: {'type': 'directions', 'data': float[12], 'id': str}
        logger.debug(f'Sending data {data["type"]} to {len(self.clients)} clients')
        if data['type'] == 'image':
            data['data'] = base64.b64encode(data['data']).decode('ascii')
        elif data['type'] == 'directions':
            data['data'] = [float(i) for i in data['data']]
        data = json.dumps(data)
        for client in self.clients:
            await client.send(data)

    def poll_monitor_queue(self, loop):
        while True:
            data = self.monitor_queue.get()
            logger.debug(f'Got data {data["type"]} from monitor queue')
            asyncio.run_coroutine_threadsafe(self.broadcast(data), loop)

    async def run(self, host='', port=5001):
        loop = asyncio.get_running_loop()
        self.monitor_queue_polling_thread = threading.Thread(target=self.poll_monitor_queue, args=(loop,))
        self.monitor_queue_polling_thread.start()

        # handle SIGKILL
        # loop.add_signal_handler(9, lambda: asyncio.create_task(self.stop()))
        logger.info('Monitor server started')

        async with websockets.server.serve(self.serve, host, port):
            await asyncio.Future()

    async def stop(self):
        for client in self.clients:
            await client.close()
