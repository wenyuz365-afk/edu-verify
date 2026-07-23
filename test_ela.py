"""测试两张证书的ELA分数"""
import sys, os
sys.path.insert(0, 'D:/edu-verify')
from ela_detector import ela_analysis

files = [
    ('真证', 'D:/edu-verify/真证.jpg'),
    ('假证', 'D:/edu-verify/假证.jpg'),
]

for label, path in files:
    print(f"\n{'='*50}")
    print(f"  {label}: {path}")
    print(f"  exists: {os.path.exists(path)}")
    r = ela_analysis(path)
    print(f"  risk: {r.get('risk_score',0):.4f}")
    print(f"  level: {r.get('risk_level')}")
    print(f"  noise: {r.get('mean_noise',0):.1f}")
    print(f"  anomaly: {r.get('anomaly_ratio',0):.4f}")
    print(f"  edge: {r.get('edge_density',0):.4f}")
    print(f"  verdict: {r.get('verdict','error')}")
print()
