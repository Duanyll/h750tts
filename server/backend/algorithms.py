from __future__ import annotations

import matplotlib.pyplot as plt
import cv2
import torch
import timm
import numpy as np
import torchvision.transforms as transforms
from einops import reduce, rearrange, repeat
import logging
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def max_pool(x, kernel_size = 32):
  return reduce(x, '(h k1) (w k2) -> h w', 'max', k1 = kernel_size, k2 = kernel_size)   

def avg_pool(x, kernel_size = 32):
    return reduce(x, '(h k1) (w k2) -> h w', 'mean', k1 = kernel_size, k2 = kernel_size)

class DepthPredicter:
    def __init__(self):
        self.midas = torch.hub.load('D:/source/MiDaS', 'DPT_Hybrid', source='local')
        self.midas = self.midas.to('cuda')
        # self.midas = torch.compile(self.midas)
        self.midas.eval()
        self.transforms = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        
        # forward model with a dummy input to initialize
        dummy_input = torch.randn(1, 3, 384, 288).to('cuda')
        with torch.no_grad():
            self.midas(dummy_input)
        
        logger.info('DepthPredicter initialized')
            

    def predict_depth(self, batched_img: list[np.ndarray]) -> np.ndarray:
        for i in range(len(batched_img)):
            batched_img[i] = self.transforms(batched_img[i])
        input_batch = torch.from_numpy(np.stack(batched_img, axis=0)).to('cuda')
        with torch.no_grad():
            prediction = self.midas(input_batch)

        out = prediction.cpu().numpy()
        a = reduce(out, 'b h w -> b 1 1', 'max')

        out = (out / a) * 255
        out = (out).astype(np.uint8)

        return out
    
    def predict_walkable_directions(self, images: list[np.ndarray]):
        n = len(images)
        # resize all image to h = 288, w = 384 and stack them to batch
        for i in range(n):
            images[i] = cv2.resize(images[i], (384, 288))
        # predict depth
        depth = self.predict_depth(images)
        # predict walkable directions
        result = []
        for i in range(n):
            # canny = cv2.Canny(depth[i], 50, 10)
            # score = max_pool(canny) / 8 + max_pool(depth[i])
            # grad1score = score[-1] - score[-2]
            # grad2score = np.abs(score[-1] + score[-3] - score[-2] * 2)
            # disscore = score[-2].copy()
            # disscore[grad1score < 20] = 1000
            # disscore[grad2score > 20] = 1000
            # walkable = (disscore < np.min(disscore) + 30) * (disscore < 1000)
            nlines = 12
            h, w = depth[i].shape
            x = np.linspace(0, w - 1, nlines, dtype=np.int64)
            sample_lines = depth[i, ::-1, x].astype(np.float32)
            sample_grad = np.zeros_like(sample_lines)
            for j in range(nlines):
                sample_grad[j] = np.gradient(sample_lines[j])
            dist = np.argmax(np.abs(sample_grad) > 1, axis=1)
            dist[dist == 0] = h - 1
            col = np.zeros_like(dist, dtype=np.float32)
            for j in range(nlines):
                col[j] = np.mean(sample_lines[j, :dist[j]])
            walkable = (col< np.min(col) + 50) * (dist.astype(np.float32) > h * 0.15)
            result.append(walkable)

        return result
    
import sys
sys.path.append(os.path.dirname(__file__))
from ppocronnx import TextSystem
from ppocronnx.predict_system import BoxedResult

class TextRecognizer:
    def __init__(self):
        self.text_system = TextSystem(ort_providers=['CPUExecutionProvider'])
        test_image = cv2.imread(os.path.join(os.path.dirname(__file__), 'ppocronnx/test.jpg'))
        self.text_system.detect_and_ocr(test_image)
        logger.info('TextRecognizer initialized')
        
    def recognize_text(self, image: np.ndarray) -> list[BoxedResult]:
        start_time = time.time()
        res = self.text_system.detect_and_ocr(image, drop_score=0.9)
        logger.debug(f'TextRecognizer recognize_text time: {time.time() - start_time}')
        return res 
    
import pupil_apriltags as apriltag

class AprilTagDetector:
    def __init__(self):
        self.detector = apriltag.Detector(families='tag36h11')
        logger.info('AprilTagDetector initialized')
        
    def detect_apriltags(self, image: np.ndarray):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return self.detector.detect(image)  # type: ignore

import mediapipe as mp
mp_hands = mp.solutions.hands # type: ignore
class HandDetector:
    def __init__(self) -> None:
        self.hands = mp_hands.Hands(model_complexity=0,
                                    min_detection_confidence=0.5,
                                    min_tracking_confidence=0.5)
        logger.info('HandDetector initialized')
        
    def detect_index_position(self, image: np.ndarray):
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image)
        if results.multi_hand_landmarks:
            h, w, _ = image.shape
            return int(results.multi_hand_landmarks[0].landmark[8].x * w), \
                   int(results.multi_hand_landmarks[0].landmark[8].y * h)
        else:
            return None, None

depth_predicter: DepthPredicter
text_recognizer: TextRecognizer
apriltag_detector: AprilTagDetector
hand_detector: HandDetector
def load():
    global depth_predicter, text_recognizer, apriltag_detector, hand_detector
    depth_predicter = DepthPredicter()
    text_recognizer = TextRecognizer()
    # apriltag_detector = AprilTagDetector()
    hand_detector = HandDetector()