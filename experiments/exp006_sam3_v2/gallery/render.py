"""v1 | v2 side-by-side three-colour images (vs SAM2) for the frames of the v1 gallery."""
import json, sys
from pathlib import Path
import cv2, numpy as np
C = Path('/home/student/yuanliu-hawaii/work/cache')
K = {'sam2': '86471818888012b6', 'v1': '44820ccc66cd62ec', 'v2': '93ead78627ecc88e'}
idx = json.load(open('/home/student/yuanliu-hawaii/work/runs/exp002_sam3_masks/main/overlays/sam3_vs_sam2/index.json'))
out = Path(sys.argv[1]); rows = []
def load(k, s):
    return np.unpackbits(np.load(C / f'masks/{K[k]}/{s}/masked.npz')['masked'], axis=-1, count=960).astype(bool)
cache = {}
def iou(a, b):
    u = (a | b).sum(); return 1.0 if u == 0 else float((a & b).sum() / u)
def panel(img, ref, cand, title):
    o = img.astype(np.float32)
    for m, col in ((ref & ~cand, (255, 230, 0)), (cand & ~ref, (255, 0, 220)), (ref & cand, (40, 190, 40))):
        o[m] = 0.45 * o[m] + 0.55 * np.array(col, np.float32)
    o = cv2.resize(o.astype(np.uint8), (640, 357), interpolation=cv2.INTER_AREA)
    band = np.zeros((28, 640, 3), np.uint8); cv2.putText(band, title, (8, 20), 0, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([band, o])
for e in idx:
    s, i = e['segment'], e['i']
    if s not in cache:
        cache = {s: {k: load(k, s) for k in K}}
    m = cache[s]
    img = cv2.imread(str(C / f'preprocess/65ab0510375aa8cd/{s}/images/{i:06d}.jpg'))
    a, b = iou(m['sam2'][i], m['v1'][i]), iou(m['sam2'][i], m['v2'][i])
    im = np.hstack([panel(img, m['sam2'][i], m['v1'][i], f'v1 (exp002)   IoU vs SAM2 {a:.2f}'), np.zeros((385, 8, 3), np.uint8),
                    panel(img, m['sam2'][i], m['v2'][i], f'v2 (exp006)   IoU vs SAM2 {b:.2f}')])
    name = f'{s}_{i:06d}.jpg'; cv2.imwrite(str(out / 'img' / name), im, [cv2.IMWRITE_JPEG_QUALITY, 78])
    rows.append({'segment': s, 'i': i, 'kind': e['kind'], 'iou_v1': a, 'iou_v2': b, 'src': f'img/{name}', 'w': im.shape[1], 'h': im.shape[0]})
json.dump(rows, open(out / 'rows.json', 'w'))
print(len(rows))
