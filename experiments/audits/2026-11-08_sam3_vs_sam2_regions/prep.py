"""Audit set: per segment the 2 frames with the most SAM2/SAM3 disagreement (at least 15 frames
apart); each disagreement region (connected component >= 400 px) numbered on the image.
Writes img/<seg>_<i>.jpg (left: frame, right: frame with numbered regions) and regions.json."""
import json
from pathlib import Path
import cv2, numpy as np
C = Path('/home/student/yuanliu-hawaii/work/cache'); OUT = Path(__file__).parent
regions = []
for s in [f'ep{k:02d}' for k in range(30)]:
    a = np.unpackbits(np.load(C / f'masks/86471818888012b6/{s}/masked.npz')['masked'], axis=-1, count=960).astype(bool)
    b = np.unpackbits(np.load(C / f'masks/44820ccc66cd62ec/{s}/masked.npz')['masked'], axis=-1, count=960).astype(bool)
    dis = (a ^ b).sum((1, 2))
    picks = []
    for i in np.argsort(-dis):
        if all(abs(int(i) - p) >= 15 for p in picks):
            picks.append(int(i))
        if len(picks) == 2:
            break
    for i in picks:
        img = cv2.imread(str(C / f'preprocess/65ab0510375aa8cd/{s}/images/{i:06d}.jpg'))
        o = img.astype(np.float32)
        for m, col in ((a[i] & ~b[i], (255, 230, 0)), (b[i] & ~a[i], (255, 0, 220)), (a[i] & b[i], (40, 190, 40))):
            o[m] = 0.5 * o[m] + 0.5 * np.array(col, np.float32)
        o = o.astype(np.uint8)
        rid = 0
        for kind, m in (('sam2_only', a[i] & ~b[i]), ('sam3_only', b[i] & ~a[i])):
            n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
            for c in range(1, n):
                area = int(st[c, cv2.CC_STAT_AREA])
                if area < 400:
                    continue
                rid += 1
                ys, xs = np.nonzero(lab == c)
                k = len(xs) // 2; x, y = int(xs[k]), int(ys[k])          # a pixel inside the region
                cv2.circle(o, (x, y), 15, (0, 0, 0), -1); cv2.circle(o, (x, y), 15, (255, 255, 255), 2)
                cv2.putText(o, str(rid), (x - 9 if rid < 10 else x - 13, y + 7), 0, 0.65, (255, 255, 255), 2)
                regions.append({'segment': s, 'i': i, 'region': rid, 'kind': kind, 'area_px': area,
                                'area_frac': area / m.size, 'x': x, 'y': y})
        cv2.putText(o, f'{s} i={i}', (10, 30), 0, 0.9, (255, 255, 255), 2)
        cv2.imwrite(str(OUT / 'img' / f'{s}_{i:06d}.jpg'), np.hstack([img, o]), [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(regions, open(OUT / 'regions.json', 'w'), indent=1)
print(len(regions), 'regions in', len(set((r['segment'], r['i']) for r in regions)), 'frames;',
      sum(r['kind'] == 'sam2_only' for r in regions), 'SAM2-only,', sum(r['kind'] == 'sam3_only' for r in regions), 'SAM3-only')
