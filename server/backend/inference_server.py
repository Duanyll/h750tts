from __future__ import annotations

# from .algotithms import DepthPredicter, TextRecognizer
import multiprocessing as mp
import cv2
import time
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientInferenceState:
    total_timeout = 30.0 # seconds
    
    direction_result: list[tuple[np.ndarray, float]]
    direction_timeout = 1.0 # seconds
    last_update: float
    
    last_ocr_time: float = 0.0
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.direction_result = []
        self.last_update = time.time()
        
    def insert_direction_result(self, direction_result: np.ndarray, timestamp: float):
        self.last_update = timestamp
        self.direction_result.append((direction_result, timestamp))
        # remove old results
        while len(self.direction_result) > 0 and self.direction_result[0][1] < timestamp - self.direction_timeout:
            self.direction_result.pop(0)
            
    def insert_ocr_result(self, results: list[str], timestamp: float):
        self.last_ocr_time = timestamp
        self.last_update = timestamp
        pass
            
    def report_results(self, info_queue: mp.Queue, monitor_queue: mp.Queue | None = None):
        if len(self.direction_result) != 0:
            # calculate average
            result = np.average([result[0] for result in self.direction_result], axis=0)
            # info_queue.put((self.client_id, result))
            if monitor_queue is not None:
                monitor_queue.put({'type': 'directions', 'data': result, 'client_id': self.client_id})
    
    def should_be_removed(self) -> bool:
        return self.last_update < time.time() - self.total_timeout

class InferenceServer:
    clients: dict[str, ClientInferenceState]
    batch_size = 4
    def __init__(self, infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue):
        self.infer_queue = infer_queue
        self.info_queue = info_queue
        self.monitor_queue = monitor_queue
        # self.depth_predicter = DepthPredicter()
        # self.text_recognizer = TextRecognizer()
        self.clients = {}
        
        self.frame_count = 0


    def process_depth(self, data_list: list[tuple[str, np.ndarray, float]]):
        # data format (client_id, image, timestamp)
        # All images are used to predict depth and direction
        results = self.depth_predicter.predict_walkable_directions([data[1] for data in data_list])
        for i, data in enumerate(data_list):
            self.clients[data[0]].insert_direction_result(results[i], data[2])
            
    def process_text(self, data_list: list[tuple[str, np.ndarray, float]]):
        # Only use image with more than 1 second interval and wider than 800 px
        for client_id, image, timestamp in data_list:
            if timestamp - self.clients[client_id].last_ocr_time > 1.0 and image.shape[1] > 800:
                result = self.text_recognizer.recognize_text(image)
                self.clients[client_id].insert_ocr_result(result, timestamp)
                

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
            
            for client_id in client_id_list:
                if client_id not in self.clients:
                    logger.info(f'New client {client_id} connected to inference server')
                    self.clients[client_id] = ClientInferenceState(client_id)
            
            data_list = list(zip(client_id_list, images, time_list))
            self.process_depth(data_list)
            self.process_text(data_list)

            logger.debug(f'Frame {self.frame_count} processed {len(images)} images')
            
            self.frame_count += 1
            
            for client_id in list(self.clients.keys()):
                self.clients[client_id].report_results(self.info_queue, self.monitor_queue)
                if self.clients[client_id].should_be_removed():
                    logger.info(f'Have not received data from client {client_id} for {ClientInferenceState.total_timeout} seconds, removing client')
                    self.clients.pop(client_id)
