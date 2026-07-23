"""
ELA (Error Level Analysis) 图片篡改检测
原理：JPEG 图片不同区域压缩误差水平不同。
被 PS 修改过的区域会有异常的压缩噪声，ELA 可以高亮这些区域。
"""
import cv2
import numpy as np
from PIL import Image
import io
from pathlib import Path


def ela_analysis(image_path: str, quality: int = 90,
                 threshold_high: float = 0.40, threshold_med: float = 0.30) -> dict:
    """
    对图片执行 ELA 分析
    返回篡改风险评分和可视化结果
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"error": f"无法读取图片: {image_path}", "tamper_risk": 0, "score": 0}

    h, w = img.shape[:2]

    # 限制大图尺寸（>4000px会慢）
    max_dim = 2000
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 保存临时文件（模拟 JPEG 重新压缩）
    temp_path = Path(image_path).parent / "_ela_temp.jpg"
    cv2.imwrite(str(temp_path), img, [cv2.IMWRITE_JPEG_QUALITY, quality])

    # 读取重新压缩后的图像
    recompressed = cv2.imread(str(temp_path), cv2.IMREAD_GRAYSCALE)
    temp_path.unlink(missing_ok=True)

    if recompressed is None:
        return {"error": "ELA recompression failed", "tamper_risk": 0}

    # ELA = |原图 - 重压缩图| 的差值放大
    diff = cv2.absdiff(gray, recompressed)
    ela = cv2.convertScaleAbs(diff, alpha=5, beta=0)

    mean_noise = float(np.mean(ela))
    std_noise = float(np.std(ela))

    threshold = mean_noise + 3.0 * std_noise
    anomaly_mask = ela > threshold
    total_pixels = ela.size
    anomaly_ratio = int(np.sum(anomaly_mask)) / total_pixels

    edges = cv2.Canny(ela, 65, 185)
    edge_density = float(np.sum(edges > 0)) / total_pixels

    risk = min(1.0, anomaly_ratio * 12 + edge_density * 6 + mean_noise / 65)

    if risk > threshold_high:
        level, verdict = "high", "检测到疑似篡改痕迹"
    elif risk > threshold_med:
        level, verdict = "medium", "图片存在轻微异常"
    else:
        level, verdict = "low", "未检测到明显篡改痕迹"

    return {
        "mean_noise": round(mean_noise, 2),
        "anomaly_ratio": round(anomaly_ratio, 4),
        "edge_density": round(edge_density, 4),
        "risk_score": round(risk, 4),
        "risk_level": level,
        "verdict": verdict,
    }


def quick_tamper_check(image_path: str) -> tuple:
    """快速检测：返回(是否可疑, 风险分, 描述)"""
    result = ela_analysis(image_path)
    if "error" in result:
        return False, 0, result["error"]
    return (
        result["risk_level"] == "high",
        result["risk_score"],
        result["verdict"],
    )
