import cv2
import numpy as np
import multiprocessing as mp


class Monitor:
    width = 1280
    height = 720

    base_image: np.ndarray
    message: str = ''
    directions: list[float]

    def __init__(self, monitor_queue: mp.Queue) -> None:
        self.monitor_queue = monitor_queue
        self.base_image = np.zeros(
            (self.height, self.width, 3), dtype=np.uint8)
        self.directions = [0] * 12

    def get_score_color(self, score: float) -> tuple[int, int, int]:
        # Transit 0 -> 1, Red -> Green
        score = 1 - score
        return (int(score * 255), int((1 - score) * 255), 0)

    def draw(self):
        image = self.base_image.copy()
        # draw message: top left
        cv2.putText(image, self.message, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # draw directions: histogram overlay on bottom of image
        histogram_width = self.width // len(self.directions)
        histogram_height = self.height // 4
        for i in range(len(self.directions)):
            cv2.rectangle(image, (i * histogram_width, int(self.height - histogram_height *
                          self.directions[i])), ((i + 1) * histogram_width, self.height), self.get_score_color(self.directions[i]), -1)
        return image

    def run(self):
        while (True):
            data = self.monitor_queue.get()
            if data['type'] == 'image':
                self.base_image = cv2.imdecode(np.frombuffer(
                    data['data'], dtype=np.uint8), cv2.IMREAD_COLOR)
                self.base_image = cv2.resize(
                    self.base_image, (self.width, self.height))
            elif data['type'] == 'message':
                self.message = data['data']
            elif data['type'] == 'directions':
                self.directions = data['data']

            cv2.imshow('Monitor', self.draw())
            cv2.waitKey(1)
