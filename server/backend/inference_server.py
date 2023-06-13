from __future__ import annotations

import multiprocessing as mp
import cv2
import time
import numpy as np
import logging
import json
from . import protocol_constants as C
from .utils import FrameRateCounter
from . import algorithms

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
    
class DirectionClassifier:
    direction_result: list[tuple[np.ndarray, float]]
    direction_timeout = 0.5  # seconds
    
    def __init__(self) -> None:
        self.direction_result = []
        
    def add_image(self, image: np.ndarray, timestamp: float):
        current_directions = algorithms.depth_predicter.predict_walkable_directions([image])
        self.direction_result.append((current_directions[0], timestamp))
        
    def _classify_direction(self, result: list[float]) -> str:
        # 0 1 2 3 4 5 6 7 8 9 10 11
        # Center: 6 7
        n = len(result)
        center_score = np.average(result[4:8])
        side_score = np.max([np.max(result[0:4]) + np.max(result[8:12])])
        mean_position = (np.average(np.arange(n), weights=result) - 5.5) if np.sum(result) > 0 else 0
        logger.debug(f'center_score: {center_score}, side_score: {side_score}, mean_position: {mean_position}')
        if center_score > 0.3:
            if mean_position < -1:
                return 'left'
            elif mean_position > 1:
                return 'right'
            else:
                return 'front'
        else:
            if side_score > 0.5:
                if mean_position < -3:
                    return 'far_left'
                elif mean_position > 3:
                    return 'far_right'
                elif mean_position < 0:
                    return 'left'
                else:
                    return 'right'
            else:
                return 'stop'
        
    def get_direction(self) -> str:
        # remove old results
        while len(self.direction_result) > 0 and self.direction_result[0][1] < time.time() - self.direction_timeout:
            self.direction_result.pop(0)
        if len(self.direction_result) == 0:
            return 'stop'
        else:
            result = np.average([result[0] for result in self.direction_result], axis=0)
            return self._classify_direction(result)
        
    def get_monitor_data(self) -> dict:
        if len(self.direction_result) == 0:
            return {}
        else:
            result = np.average([result[0] for result in self.direction_result], axis=0)
            return {
                'direction': self._classify_direction(result),
                'direction_histogram': result.tolist(),
            }
        
    
class Client:
    timeout = 30.0 # seconds
    mode = 'direction' # 'direction' or 'ocr'
    direction_cooldown = 0.5 # seconds
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.last_update = time.time()
        self.mode = 'direction'
        
        self.direction_classifier = DirectionClassifier()
        self.direction_last_update = time.time()
        
    def handle_image(self, image: np.ndarray, timestamp: float):
        self.last_update = timestamp
        if self.mode == 'direction':
            self.direction_classifier.add_image(image, timestamp)
    
    def handle_state(self, state: dict, timestamp: float):
        pass
    
    def get_monitor_data(self) -> dict:
        if self.mode == 'direction':
            return self.direction_classifier.get_monitor_data()
        else:
            return {}
    
    def get_response(self) -> list[dict]:
        res = []
        if self.mode == 'direction' and time.time() - self.direction_last_update > self.direction_cooldown:
            direction = self.direction_classifier.get_direction()
            res.append({
                'type': 'direction',
                'direction': direction,
            })
            self.direction_last_update = time.time()
            logger.debug(f'Client {self.client_id} direction: {direction}')
        return res
        
    
    def should_be_removed(self) -> bool:
        return self.last_update < time.time() - self.timeout

class InferenceServer:
    clients: dict[str, Client]
    batch_size = 4
    def __init__(self, infer_queue: mp.Queue, info_queue: mp.Queue, monitor_queue: mp.Queue):
        self.infer_queue = infer_queue
        self.info_queue = info_queue
        self.monitor_queue = monitor_queue
        self.clients = {}
        algorithms.load()
        self.frame_rate_counter = FrameRateCounter()

    def run(self):
        logger.info("Inference server started")
        while True:
            if self.infer_queue.qsize() > self.batch_size * 2:
                # drop old data
                logger.warning("Cannot process data fast enough, dropping old data")
                for _ in range(self.infer_queue.qsize() - self.batch_size):
                    self.infer_queue.get()
            if self.infer_queue.empty():
                time.sleep(0.01)
                continue
            
            # get data
            data = self.infer_queue.get()
            
            """
            data format: {
                'type': 'client'
                'client_id': str,
                'timestamp': float,
                'image'?: bytes,
                'state'?: dict,
            }
            """
            
            if data['type'] == 'client':
                if data['client_id'] not in self.clients:
                    self.clients[data['client_id']] = Client(data['client_id'])
                client = self.clients[data['client_id']]
                if 'image' in data:
                    # decode image
                    image = cv2.imdecode(np.frombuffer(data['image'], dtype=np.uint8), cv2.IMREAD_COLOR)
                    client.handle_image(image, data['timestamp'])
                if 'state' in data:
                    client.handle_state(data['state'], data['timestamp'])
            elif data['type'] == 'console':
                pass # TODO: handle console commands
            
            for client_id in list(self.clients.keys()):
                if self.clients[client_id].should_be_removed():
                    del self.clients[client_id]
                else:
                    client = self.clients[client_id]
                    responses = client.get_response()
                    for response in responses:
                        self.info_queue.put((C.TYPE_JSON, json.dumps(response).encode('utf-8'), client_id))
                        
            self.frame_rate_counter.update()
            # get monitor data from first client
            if len(self.clients) > 0:
                monitor_data = self.clients[list(self.clients.keys())[0]].get_monitor_data()
                monitor_data['fps'] = self.frame_rate_counter.get_fps()
                self.monitor_queue.put(monitor_data)