import sys
sys.path.insert(0, 'D:/edu-verify')
from ela_detector import ela_analysis

for path in ['D:/edu-verify/real.jpg', 'D:/edu-verify/fake.jpg']:
    r = ela_analysis(path)
    print(f'{path}:')
    print(f'  risk={r.get("risk_score",0):.4f}  level={r.get("risk_level")}')
    print(f'  noise={r.get("mean_noise",0):.1f}  anomaly={r.get("anomaly_ratio",0):.4f}  edge={r.get("edge_density",0):.4f}')
    print(f'  verdict: {r.get("verdict","error")}')
    print()
