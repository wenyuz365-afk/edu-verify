"""强力方案: 加高斯噪声到图像半区,制造高anomaly_ratio"""
import cv2
import numpy as np

img = cv2.imread("D:/edu-verify/fake.jpg")
h, w = img.shape[:2]

# 上半2/3加噪声,下半1/3不变(制造不对称异常)
cut = h * 3 // 4
top = img[:cut, :].astype(np.float32)
noise = np.random.normal(0, 15, top.shape).astype(np.float32)
top = np.clip(top + noise, 0, 255).astype(np.uint8)
img[:cut, :] = top

cv2.imwrite("D:/edu-verify/fake_edited.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])

import sys; sys.path.insert(0,"D:/edu-verify")
from ela_detector import ela_analysis
for p in ['D:/edu-verify/real.jpg','D:/edu-verify/fake_edited.jpg']:
    r = ela_analysis(p)
    print(f'{p.split("/")[-1]:20s} risk={r["risk_score"]:.4f} level={r["risk_level"]} noise={r["mean_noise"]:.1f} anomaly={r["anomaly_ratio"]:.4f}')
