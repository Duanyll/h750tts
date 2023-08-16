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
        current_directions = algorithms.depth_predicter.predict_walkable_directions([
                                                                                    image])
        self.direction_result.append((current_directions[0], timestamp))

    def _classify_direction(self, result: list[float]) -> str:
        # 0 1 2 3 4 5 6 7 8 9 10 11
        # Center: 6 7
        n = len(result)
        center_score = np.average(result[4:8])
        side_score = np.max([np.max(result[0:4]) + np.max(result[8:12])])
        mean_position = (np.average(np.arange(n), weights=result) -
                         5.5) if np.sum(result) > 0 else 0
        logger.debug(
            f'center_score: {center_score}, side_score: {side_score}, mean_position: {mean_position}')
        if center_score > 0.2:
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
        current_time = time.time()
        while len(self.direction_result) > 0 and self.direction_result[0][1] < current_time - self.direction_timeout:
            self.direction_result.pop(0)
        if len(self.direction_result) == 0:
            return 'stop'
        else:
            result = np.average([result[0]
                                for result in self.direction_result], axis=0)
            return self._classify_direction(result)

    def get_monitor_data(self) -> dict:
        if len(self.direction_result) == 0:
            return {}
        else:
            result = np.average([result[0]
                                for result in self.direction_result], axis=0)
            return {
                'direction': self._classify_direction(result),
                'direction_histogram': result.tolist(),
            }


def lcs(a: str, b: str) -> int:
    # https://en.wikipedia.org/wiki/Longest_common_subsequence_problem
    # O(n^2) time, O(n) space
    if len(a) == 0 or len(b) == 0:
        return 0
    dp = [0 for _ in range(len(b) + 1)]
    for i in range(1, len(a) + 1):
        left_up = 0
        dp[0] = 0
        for j in range(1, len(b) + 1):
            left = dp[j-1]
            up = dp[j]
            if a[i-1] == b[j-1]:
                dp[j] = left_up + 1
            else:
                dp[j] = max([left, up])
            left_up = up
    return dp[len(b)]


class OCRResult:
    lcs_threshold = 0.6
    occurence_threshold = 3
    decay_time = 10.0  # seconds

    def __init__(self, text: str, timestamp: float, position: tuple[float, float]):
        self.text = text
        self.timestamp = timestamp
        self.position = position
        self.occurences = 1

    def matches(self, text: str):
        return lcs(self.text, text) / max([len(self.text), len(text)]) > self.lcs_threshold

    def update(self, text: str, timestamp: float, position: tuple[float, float]) -> bool:
        self.text = text
        self.timestamp = timestamp
        self.position = position
        self.occurences += 1
        return self.occurences == self.occurence_threshold

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.decay_time


class OCRBuffer:
    results: set[OCRResult]
    new_texts: list[str]
    boxes: list[list[list[float]]]
    focus_text: str | None

    focus_dist_threshold = 0.2
    focus_timeout = 2.0  # seconds

    def __init__(self):
        self.results = set()
        self.new_texts = []
        self.hand_pos = (None, None)
        self.focus_text = None
        self.focus_pos = None

    def _find_focused_text(self, image: np.ndarray):
        hand_x, hand_y = algorithms.hand_detector.detect_index_position(image)
        if hand_x is not None and hand_y is not None:
            self.hand_pos = (hand_x, hand_y)
            # find closest text
            text = ''
            min_distance = 1000000.0
            position = (0.0, 0.0)
            current_time = time.time()
            h, w, _ = image.shape
            dis_threshold = self.focus_dist_threshold * np.sqrt(h**2 + w**2)
            for result in self.results:
                distance = np.linalg.norm(
                    np.array(result.position) - np.array(self.hand_pos))
                if distance < min_distance and current_time - result.timestamp < self.focus_timeout:
                    text = result.text
                    min_distance = distance
                    position = result.position
            if min_distance < dis_threshold:
                return text, position
        else:
            self.hand_pos = None
        return None, None

    def add_image(self, image: np.ndarray, timestamp: float):
        results = algorithms.text_recognizer.recognize_text(image)
        self.boxes = []
        for result in results:
            # check if result is already in buffer
            text = result.ocr_text
            position = (np.average(result.box[:, 0]), np.average(result.box[:, 1]))  # type: ignore
            for existing_result in self.results:
                if existing_result.matches(text):
                    if existing_result.update(text, timestamp, position):
                        self.new_texts.append(text)
                    break
            else:
                self.results.add(OCRResult(text, timestamp, position))
            self.boxes.append(result.box.tolist())  # type: ignore

        last = self.focus_text
        self.focus_text, self.focus_pos = self._find_focused_text(
            image)
        if self.focus_text is not None and self.focus_text != last:
            self.new_texts = [self.focus_text]

    def get_new_texts(self) -> list[str]:
        res = self.new_texts
        self.new_texts = []
        # remove expired results
        self.results = {
            result for result in self.results if not result.is_expired()}
        if len(res) > 0:
            print(f'Text`   : {res}')
        return res

    def get_monitor_data(self) -> dict:
        return {
            'ocr_boxes': self.boxes,
            'hand_pos': self.hand_pos,
            'focus_pos': self.focus_pos,
        }


class Client:
    timeout = 30.0  # seconds
    mode = 'direction'  # 'idle', 'direction', 'ocr'
    direction_cooldown = 0.5  # seconds

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.last_update = time.time()
        self.mode = 'ocr'

        self.direction_classifier = DirectionClassifier()
        self.direction_last_update = time.time()

        self.ocr_buffer = OCRBuffer()

    def handle_image(self, image: np.ndarray, timestamp: float):
        self.last_update = timestamp
        if self.mode == 'direction':
            self.direction_classifier.add_image(image, timestamp)
        elif self.mode == 'ocr':
            self.ocr_buffer.add_image(image, timestamp)

    def handle_state(self, state: dict, timestamp: float):
        pass

    def get_monitor_data(self) -> dict:
        if self.mode == 'direction':
            return self.direction_classifier.get_monitor_data()
        elif self.mode == 'ocr':
            return self.ocr_buffer.get_monitor_data()
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
        elif self.mode == 'ocr':
            if self.ocr_buffer.focus_text is not None:
                res += [{'type': 'text', 'text': text, 'textType': 'focus'}
                        for text in self.ocr_buffer.get_new_texts()]
            else:
                res += [{'type': 'text', 'text': text, 'textType': 'background'}
                        for text in self.ocr_buffer.get_new_texts()]
        return res

    def is_expired(self) -> bool:
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

    def _handle_console_command(self, command: dict):
        if 'mode' in command:
            if command['mode'] == 'direction':
                for client in self.clients.values():
                    client.mode = 'direction'
            elif command['mode'] == 'ocr':
                for client in self.clients.values():
                    client.mode = 'ocr'
            elif command['mode'] == 'idle':
                for client in self.clients.values():
                    client.mode = 'idle'
                    
    def loop(self):
        try:
            if self.infer_queue.qsize() > self.batch_size * 2:
                # drop old data
                logger.debug(
                    "Cannot process data fast enough, dropping old data")
                for _ in range(self.infer_queue.qsize() - self.batch_size):
                    data = self.infer_queue.get()
                    if data['type'] == 'console':
                        self._handle_console_command(data)
            if self.infer_queue.empty():
                time.sleep(0.01)
                return

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
                    image = cv2.imdecode(np.frombuffer(
                        data['image'], dtype=np.uint8), cv2.IMREAD_COLOR)
                    image = cv2.rotate(image, cv2.ROTATE_180)
                    client.handle_image(image, data['timestamp'])
                if 'state' in data:
                    client.handle_state(data['state'], data['timestamp'])
            elif data['type'] == 'console':
                self._handle_console_command(data)

            for client_id in list(self.clients.keys()):
                if self.clients[client_id].is_expired():
                    del self.clients[client_id]
                else:
                    client = self.clients[client_id]
                    responses = client.get_response()
                    for response in responses:
                        self.info_queue.put((C.TYPE_JSON, json.dumps(
                            response).encode('utf-8'), client_id))

            self.frame_rate_counter.update()
            # get monitor data from first client
            if len(self.clients) > 0:
                monitor_data = self.clients[list(self.clients.keys())[
                    0]].get_monitor_data()
                monitor_data['fps'] = self.frame_rate_counter.get_fps()
                self.monitor_queue.put(monitor_data)
        except Exception as e:
            logger.exception(e)


    def run(self):
        logger.info("Inference server started")
        print("Inference server started")
        while True:
            self.loop()