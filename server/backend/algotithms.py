from __future__ import annotations

import matplotlib.pyplot as plt
import cv2
import torch
import timm
import numpy as np
import torchvision.transforms as transforms
from einops import reduce, rearrange, repeat
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def max_pool(x, kernel_size = 32):
  return reduce(x, '(h k1) (w k2) -> h w', 'max', k1 = kernel_size, k2 = kernel_size)   

def avg_pool(x, kernel_size = 32):
    return reduce(x, '(h k1) (w k2) -> h w', 'mean', k1 = kernel_size, k2 = kernel_size)

class DepthPredicter:
    def __init__(self):
        self.midas = torch.hub.load('D:/source/MiDaS', 'DPT_Hybrid', source='local')
        self.midas.to('cuda')
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
            canny = cv2.Canny(depth[i], 50, 10)
            score = max_pool(canny) / 8 + max_pool(depth[i])
            grad1score = score[-1] - score[-2]
            grad2score = np.abs(score[-1] + score[-3] - score[-2] * 2)
            disscore = score[-2].copy()
            disscore[grad1score < 20] = 1000
            disscore[grad2score > 20] = 1000
            walkable = (disscore < np.min(disscore) + 30) * (disscore < 1000)
            result.append(walkable)

        return result