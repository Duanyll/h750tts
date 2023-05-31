import matplotlib.pyplot as plt
import cv2
import torch
import timm
import numpy as np
from einops import reduce, rearrange, repeat

midas = torch.hub.load('D:/source/MiDaS', 'DPT_Hybrid', source='local')
midas.to('cuda')
midas.eval()

transforms = torch.hub.load('D:/source/MiDaS', 'transforms', source='local')
transform = transforms.dpt_transform

def max_pool(x, kernel_size = 32):
  return reduce(x, '(h k1) (w k2) -> h w', 'max', k1 = kernel_size, k2 = kernel_size)   

def avg_pool(x, kernel_size = 32):
    return reduce(x, '(h k1) (w k2) -> h w', 'mean', k1 = kernel_size, k2 = kernel_size)

def predict_depth(img):
    input_batch = transform(img).to('cuda')
    with torch.no_grad():
        prediction = midas(input_batch)

        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    out = prediction.cpu().numpy()
    a = out.max()

    out = (out / a) * 255
    out = (out).astype(np.uint8)

    return out


def predict_walkable_directions(img):
    h, w, _ = img.shape
    kernel_size = w // 12
    h32 = (h + kernel_size - 1) // kernel_size * kernel_size
    w32 = (w + kernel_size - 1) // kernel_size * kernel_size
    img = cv2.resize(img, (w32, h32))
    out = predict_depth(img)
    canny = cv2.Canny(out, 50, 10)
    score = max_pool(canny, kernel_size) / 8 + max_pool(out, kernel_size)
    grad1score = score[-1] - score[-2]
    grad2score = np.abs(score[-1] + score[-3] - score[-2] * 2)
    disscore = score[-2].copy()
    disscore[grad1score < 20] = 1000
    disscore[grad2score > 20] = 1000
    walkable = (disscore < np.min(disscore) + 30) * (disscore < 1000)
    return walkable