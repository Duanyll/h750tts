from typing import Any
import cv2
import numpy as np
import multiprocessing as mp


class Monitor:
    width = 800
    height = 600

    def __init__(self, monitor_queue: mp.Queue) -> None:
        self.monitor_queue = monitor_queue
        self.state = {
            'message': '',
            'image': np.zeros((self.height, self.width, 3), dtype=np.uint8),
            'direction': '',
            'direction_histogram': [0] * 12,
            'fps': 0,
            'nw_fps': 0,
            'ocr_boxes': [],
            'hand_pos': None,
            'focus_pos': None
        }
        self.w_scale = 1.
        self.h_scale = 1.

    def get_score_color(self, score: float) -> tuple[int, int, int]:
        # Transit 0 -> 1, Red -> Green
        score = 1 - score
        return (int(score * 255), int((1 - score) * 255), 0)

    def draw(self):
        image = self.state['image'].copy()
        # draw fps: top right
        cv2.putText(image, f'FPS: {self.state["fps"]:.2f}', (self.width - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(image, f'RX: {self.state["nw_fps"]:.2f}', (self.width - 200, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # draw message: top left
        cv2.putText(image, self.state['message'], (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # draw direction histogram: histogram overlay on bottom of image
        hdata = self.state['direction_histogram']
        hwidth = self.width // len(hdata)
        hheight = self.height // 4
        for i in range(len(hdata)):
            cv2.rectangle(image, 
                          (i * hwidth, int(self.height - hheight * hdata[i])), # type: ignore
                          ((i + 1) * hwidth, self.height), 
                          self.get_score_color(hdata[i]), 
                          -1)
        # draw direction: bottom left
        cv2.putText(image, self.state['direction'], (10, self.height - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # draw ocr boxes: overlay on image
        if len(self.state['ocr_boxes']) > 0:
            boxes = np.array(self.state['ocr_boxes'])
            boxes[:, :, 0] *= self.w_scale
            boxes[:, :, 1] *= self.h_scale
            cv2.polylines(image, boxes.astype(np.int32), True, (0, 255, 0), 2)
        # draw hand position: circle on image
        if self.state['hand_pos'] is not None:
            hand_pos = (int(self.state['hand_pos'][0] * self.w_scale), int(self.state['hand_pos'][1] * self.h_scale))
            cv2.circle(image, hand_pos, 10, (0, 0, 255), -1)
            # draw line to focus position
            if self.state['focus_pos'] is not None:
                focus_pos = (int(self.state['focus_pos'][0] * self.w_scale), int(self.state['focus_pos'][1] * self.h_scale))
                cv2.line(image, hand_pos, focus_pos, (0, 0, 255), 2)
        return image

    def run(self):
        while (True):
            data = self.monitor_queue.get()
            if 'image_bytes' in data:
                data['image'] = cv2.imdecode(np.frombuffer(data['image_bytes'], dtype=np.uint8), cv2.IMREAD_COLOR)
                data['image'] = cv2.rotate(data['image'], cv2.ROTATE_180)
                data_height, data_width, _ = data['image'].shape
                self.w_scale = self.width / data_width
                self.h_scale = self.height / data_height
                data['image'] = cv2.resize(data['image'], (self.width, self.height))
                del data['image_bytes']
            self.state.update(data)

            cv2.imshow('Monitor', self.draw())
            cv2.waitKey(1)
