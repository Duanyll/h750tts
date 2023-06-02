from __future__ import annotations

from .algotithms import DepthPredicter
import multiprocessing as mp
import cv2
import time
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InferenceServer:
    def __init__(self, infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue):
        self.infer_queue = infer_queue
        self.info_queue = info_queue
        self.monitor_queue = monitor_queue
        self.depth_predicter = DepthPredicter()
        
        self.batch_size = 4

        self.depth_client_queues = {}
        self.depth_timeout = 1.0 # seconds

        self.frame_count = 0


    def process_depth(self, depth_results):
        # push to depth client queues
        for client_id, depth, timestamp in depth_results:
            if client_id not in self.depth_client_queues:
                self.depth_client_queues[client_id] = []
                logger.debug("New client %s for depth processing", client_id)
            self.depth_client_queues[client_id].append((depth, timestamp))

        # remove empty queues
        for client_id in list(self.depth_client_queues.keys()):
            while len(self.depth_client_queues[client_id]) > 0 and time.time() - self.depth_client_queues[client_id][0][1] > self.depth_timeout:
                self.depth_client_queues[client_id].pop(0)
            if len(self.depth_client_queues[client_id]) == 0:
                self.depth_client_queues.pop(client_id)
                logger.debug("Client %s timed out for depth processing", client_id)

        # get depth results
        for client_id in self.depth_client_queues:
            depth_list = []
            for depth, timestamp in self.depth_client_queues[client_id]:
                depth_list.append(depth)
            result = np.mean(depth_list, axis=0)
            logger.debug("Update depth for client %s", client_id)
            self.monitor_queue.put({'type': 'directions', 'data': result, 'id': client_id })

    def run(self):
        logger.info("Inference server started")
        self.monitor_queue.put({'type': 'message', 'data': 'Inference server started'})
        while True:
            if self.infer_queue.qsize() > self.batch_size * 2:
                # drop old data
                logger.warning("Cannot process data fast enough, dropping old data")
                for _ in range(self.infer_queue.qsize() - self.batch_size):
                    self.infer_queue.get()
            if self.infer_queue.empty():
                time.sleep(0.01)
                continue
            # data format (client_id, data_bytes, timestamp)
            client_id_list = []
            data_list = []
            time_list = []
            # get at least one data
            client_id, data_bytes, timestamp = self.infer_queue.get()
            client_id_list.append(client_id)
            data_list.append(data_bytes)
            time_list.append(timestamp)
            # try to get more data (up to batch size) in non-blocking mode
            for _ in range(self.batch_size - 1):
                try:
                    client_id, data_bytes, timestamp = self.infer_queue.get(block=False)
                    client_id_list.append(client_id)
                    data_list.append(data_bytes)
                    time_list.append(timestamp)
                except:
                    break
            # decode images
            images = []
            for data_bytes in data_list:
                images.append(cv2.imdecode(np.frombuffer(data_bytes, dtype=np.uint8), cv2.IMREAD_COLOR))
            logger.debug(f'Frame {self.frame_count} processing {len(images)} images')
            
            # predict depth
            depth_results = (zip(client_id_list, self.depth_predicter.predict_walkable_directions(images), time_list))
            self.process_depth(depth_results)

            logger.debug(f'Frame {self.frame_count} processed {len(images)} images')
            
            self.frame_count += 1
