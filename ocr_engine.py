"""
学历证书 OCR 识别引擎
基于 PaddleOCR 本地引擎，针对证书场景深度优化：
- 红色印章去除（HSV 色彩空间）
- 自适应分辨率缩放
- 多通道预处理（灰度增强 + 原色彩色对比）
- 文字按位置排序
"""
import os
os.environ["KMP_AFFINITY"] = ""

import cv2
import numpy as np
from paddleocr import PaddleOCR
from pathlib import Path
import re


class CertOCREngine:
    """学历证书 OCR 识别引擎 — 证书场景专项优化版"""

    def __init__(self, lang: str = "ch"):
        # 针对证书场景优化参数：
        # det_db_thresh: 降低检测阈值（默认0.3），证书文字可能较细
        # rec_batch_num: 提高识别批次
        # use_angle_cls: 开启角度分类，处理倾斜拍照
        self.ocr = PaddleOCR(
            lang=lang,
            use_angle_cls=True,
            det_db_thresh=0.2,
            det_db_box_thresh=0.15,
            rec_batch_num=6,
            use_gpu=False,
        )

    # ================================================================
    # 红色印章去除（学位证书最关键的处理）
    # ================================================================

    def remove_red_seal(self, img: np.ndarray) -> np.ndarray:
        """
        去除红色印章：HSV 色彩空间分离红色区域 → 替换为背景色
        学位证书的圆形红色印章是 OCR 的最大干扰源
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # 红色在 HSV 中有两个区间（色调0-10 和 156-180）
        lower_red1 = np.array([0, 30, 30])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([156, 30, 30])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # 膨胀 + 腐蚀（闭运算）填充印章内部空洞
        kernel = np.ones((5, 5), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        red_mask = cv2.dilate(red_mask, kernel, iterations=1)

        # 用图像的平均背景色填充红色区域
        result = img.copy()
        # 估计背景色：取图像边缘区域的众数颜色
        h, w = img.shape[:2]
        border_pixels = np.concatenate([
            img[0:20, :, :].reshape(-1, 3),
            img[h-20:h, :, :].reshape(-1, 3),
            img[:, 0:20, :].reshape(-1, 3),
            img[:, w-20:w, :].reshape(-1, 3),
        ])
        bg_color = np.median(border_pixels, axis=0).astype(np.uint8)

        result[red_mask > 0] = bg_color

        return result

    # ================================================================
    # 分辨率自适应缩放
    # ================================================================

    def resize_for_ocr(self, img: np.ndarray, max_dim: int = 2000) -> np.ndarray:
        """
        将大图缩放到合适尺寸。PaddleOCR 在 2000px 以内的图上表现最好。
        学位证书通常 4000-6000px，直接 OCR 会导致文字检测失败。
        """
        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            return img

        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # ================================================================
    # 灰度增强预处理
    # ================================================================

    def enhance_for_cert(self, img: np.ndarray) -> np.ndarray:
        """
        证书专用增强：
        1. 转灰度
        2. CLAHE 增强对比度（限制对比度防止过度放大噪声）
        3. 轻微降噪（保留文字边缘）
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # CLAHE: clipLimit 降低避免过度增强
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 非局部均值降噪（保留边缘）
        denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)

        return denoised

    # ================================================================
    # 主识别流程
    # ================================================================

    def recognize(self, image_path: str, use_preprocess: bool = True) -> dict:
        """
        证书 OCR 识别主流程：
        1. 读取原图 → 缩放
        2. 去印章 → 灰度增强 → OCR（主通道）
        3. 合并结果 → 去重 → 按位置排序
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        # Step 1: 自适应缩放
        img = self.resize_for_ocr(img, max_dim=2000)

        all_results = []

        # --- 通道1: 去印章 → 灰度增强 → OCR ---
        if use_preprocess:
            no_seal = self.remove_red_seal(img)
            enhanced = self.enhance_for_cert(no_seal)
            result1 = self._run_ocr_on_array(enhanced)
            all_results.extend(result1)

        # --- 通道2: 原图直接 OCR（作为兜底，有些文字不在印章区域） ---
        result2 = self._run_ocr_on_array(img)
        all_results.extend(result2)

        # --- 去重合并（按位置+文字去重） ---
        merged = self._deduplicate_results(all_results)

        # --- 按阅读顺序排序 ---
        merged.sort(key=lambda x: (x["center_y"], x["center_x"]))

        # --- 组装结果 ---
        full_text_parts = [m["text"] for m in merged]
        confidences = [m["confidence"] for m in merged]

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "full_text": "\n".join(full_text_parts),
            "lines": merged,
            "line_count": len(merged),
            "average_confidence": round(avg_conf, 4),
            "quality": self._judge_quality(avg_conf),
        }

    def _run_ocr_on_array(self, img: np.ndarray) -> list:
        """对 numpy 数组执行 OCR，返回统一格式的列表"""
        # 如果是灰度图，转回 BGR（PaddleOCR 内部会处理）
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        result = self.ocr.ocr(img, cls=True)

        lines = []
        if result and result[0] is not None:
            for page in result:
                if page is None:
                    continue
                for line_data in page:
                    if len(line_data) >= 2:
                        box = line_data[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                        text_info = line_data[1]

                        if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                            text = text_info[0]
                            score = float(text_info[1])
                        else:
                            text = str(text_info)
                            score = 0.5

                        # 计算文字框的中心点（用于排序）
                        if isinstance(box, (list, np.ndarray)) and len(box) >= 4:
                            xs = [p[0] for p in box]
                            ys = [p[1] for p in box]
                            center_x = sum(xs) / len(xs)
                            center_y = sum(ys) / len(ys)
                        else:
                            center_x, center_y = 0, 0

                        lines.append({
                            "text": text,
                            "confidence": score,
                            "center_x": center_x,
                            "center_y": center_y,
                        })

        return lines

    def _deduplicate_results(self, results: list) -> list:
        """
        去重：两条结果文字内容相同且位置接近 → 保留置信度更高的
        """
        if len(results) <= 1:
            return results

        merged = []
        used = set()

        for i, r1 in enumerate(results):
            if i in used:
                continue

            best = r1
            for j, r2 in enumerate(results):
                if j <= i or j in used:
                    continue
                # 文字相同 且 位置接近（中心点距离 < 50px）
                if r1["text"] == r2["text"]:
                    dist = ((r1["center_x"] - r2["center_x"]) ** 2 +
                            (r1["center_y"] - r2["center_y"]) ** 2) ** 0.5
                    if dist < 50:
                        if r2["confidence"] > best["confidence"]:
                            best = r2
                        used.add(j)

            merged.append(best)
            used.add(i)

        return merged

    def _judge_quality(self, confidence: float) -> str:
        """根据平均置信度判断识别质量"""
        if confidence >= 0.90:
            return "excellent"
        elif confidence >= 0.72:
            return "good"
        elif confidence >= 0.50:
            return "fair"
        else:
            return "poor"


# 单例
_ocr_engine = None


def get_ocr_engine() -> CertOCREngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = CertOCREngine(lang="ch")
    return _ocr_engine
