from __future__ import annotations

import socket
import multiprocessing as mp
import asyncio
import threading
import time
import logging
import uuid

from . import protocol_constants as C

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StreamServer:
    host = ''
    port = 5000
    max_connections = 1
    infer_queue: mp.Queue
    info_queue: mp.Queue
    monitor_queue: mp.Queue | None
    server: asyncio.AbstractServer
    client_queues: dict
    info_queue_polling_thread: threading.Thread
    
    monitor_frame_rate: float = 0.01
    monitor_last_frame_time: float = 0.0

    def __init__(self, infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue | None = None):
        self.infer_queue = infer_queue
        self.info_queue = info_queue
        self.monitor_queue = monitor_queue
        self.client_queues = {}
    
    async def read_data_packet(self, reader):
        header = await reader.readexactly(6)
        if header[0:4] != C.HEADER:
            raise Exception('Invalid header')
        data_type = header[4]
        is_last = header[5] == 0x01
        if data_type == C.TYPE_TERMINATE or data_type == C.TYPE_NONE:
            return data_type, None, is_last
        length = int.from_bytes(await reader.readexactly(4), 'little')
        data_bytes = await reader.readexactly(length)
        return data_type, data_bytes, is_last
        
    
    async def write_data_packet(self, writer, data_type, data_bytes, is_last=True):
        header = C.HEADER + data_type.to_bytes(1, 'little') + (0x01 if is_last else 0x00).to_bytes(1, 'little')
        writer.write(header)
        if not (data_type == C.TYPE_TERMINATE or data_type == C.TYPE_NONE):
            writer.write(len(data_bytes).to_bytes(4, 'little'))
            writer.write(data_bytes)
        await writer.drain()
        

    async def handle_client_data(self, cliend_id, data_type, data_bytes):
        if data_type == C.TYPE_TERMINATE:
            # Terminating connection
            logger.info(f'Connection from {cliend_id} closed by client')
            raise Exception('Connection closed by client')
        elif data_type == C.TYPE_NONE:
            # None
            pass
        elif data_type == C.TYPE_IMAGE:
            # JPEG image
            logger.debug(f'Received image from {cliend_id}')
            self.infer_queue.put((cliend_id, data_bytes, time.time()))
            if self.monitor_queue is not None:
                if time.time() - self.monitor_last_frame_time > self.monitor_frame_rate:
                    self.monitor_last_frame_time = time.time()
                    self.monitor_queue.put({'type': 'image', 'data': data_bytes})
        elif data_type == C.TYPE_AUDIO:
            # WAV audio
            pass  # TODO: audio processing
        elif data_type == C.TYPE_JSON:
            # JSON
            pass  # TODO: JSON processing
        else:
            raise Exception('Invalid data type')

    async def handle_client(self, reader, writer):
        cliend_id = uuid.uuid4().hex
        addr = writer.get_extra_info('peername')
        logger.info(f'New clinet connection from {addr}, id: {cliend_id}')
        self.client_queues[cliend_id] = asyncio.Queue()
        try:
            while True:
                # read data
                is_last = False
                while not is_last:
                    data_type, data_bytes, is_last = await self.read_data_packet(reader)
                    await self.handle_client_data(cliend_id, data_type, data_bytes)
                
                # send data
                while not self.client_queues[cliend_id].empty():
                    logger.debug(f'Sending data to {cliend_id}')
                    data_type, data_bytes = await self.client_queues[cliend_id].get()
                    is_last = self.client_queues[cliend_id].empty()
                    await self.write_data_packet(writer, data_type, data_bytes, is_last)
                    if is_last:
                        break
                else:
                    await self.write_data_packet(writer, 0x01, None)

        except Exception as e:
            logger.exception(e)
        finally:
            del self.client_queues[cliend_id]
            writer.close()
            await writer.wait_closed()

    async def put_client_queue(self, data_type, data_bytes, cliend_id=None):
        if cliend_id is None:
            for cliend_id in self.client_queues:
                await self.client_queues[cliend_id].put((data_type, data_bytes))
        else:
            if cliend_id not in self.client_queues:
                return
            await self.client_queues[cliend_id].put((data_type, data_bytes))

    def poll_info_queue(self, loop):
        while True:
            data_type, data_bytes, client_id = self.info_queue.get()
            asyncio.run_coroutine_threadsafe(self.put_client_queue(data_type, data_bytes, client_id), loop=loop)

    async def run(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port, limit=self.max_connections)
        addr = self.server.sockets[0].getsockname()
        logger.info(f'Stream server serving on {addr}')
        
        if self.monitor_queue is not None:
            self.monitor_queue.put({'type': 'message', 'data': f'Stream server serving on {addr}'})

        # handle SIGKILL
        loop = asyncio.get_running_loop()
        # loop.add_signal_handler(9, lambda: asyncio.create_task(self.stop()))

        # start info queue polling thread
        self.info_queue_polling_thread = threading.Thread(target=self.poll_info_queue, args=(loop,))
        self.info_queue_polling_thread.start()

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()

