"""
debug_rs.py — uruchom na swoim foto.png żeby zobaczyć co dzieje się w RS Analysis
python debug_rs.py sample_images/clean/foto.png
"""
import sys
import numpy as np
from PIL import Image

def noise(block): return float(np.sum(np.abs(np.diff(block))))

filepath = sys.argv[1] if len(sys.argv) > 1 else "sample_images/clean/foto.png"
image = Image.open(filepath).convert("L")
pixels = np.array(image, dtype=int)
flat = pixels.flatten()

n_blocks = len(flat) // 4
rm=sm=um=r_m=s_m=u_m=0

unusable_neg = []  # zbieramy przykłady bloków Unusable dla -M

for i in range(n_blocks):
    blk = flat[i*4:(i+1)*4].copy()
    f0 = noise(blk)

    # Maska M
    mM = blk.copy()
    mM[0] ^= 1; mM[2] ^= 1
    fM = noise(mM)
    if fM > f0: rm+=1
    elif fM < f0: sm+=1
    else: um+=1

    # Maska -M
    mN = blk.copy()
    for pos in [0, 2]:
        if mN[pos] % 2 == 0: mN[pos] = max(0, mN[pos]-1)
        else:                 mN[pos] = min(255, mN[pos]+1)
    fN = noise(mN)
    if fN > f0: r_m+=1
    elif fN < f0: s_m+=1
    else:
        u_m+=1
        if len(unusable_neg) < 5:
            unusable_neg.append((blk.tolist(), mN.tolist(), f0, fN))

t = n_blocks
print(f"Plik: {filepath}")
print(f"Pikseli: {len(flat):,}  Bloków: {t:,}")
print(f"")
print(f"Maska  M:  R={rm/t:.4f}  S={sm/t:.4f}  U={um/t:.4f}  (R+S+U={rm+sm+um})")
print(f"Maska -M:  R={r_m/t:.4f}  S={s_m/t:.4f}  U={u_m/t:.4f}  (R+S+U={r_m+s_m+u_m})")
print(f"")
print(f"rs_diff = {abs((rm-sm)/t - (r_m-s_m)/t):.4f}")
print(f"")
if unusable_neg:
    print(f"Przykłady bloków Unusable dla -M (f_neg == f_orig):")
    for blk, mN, f0, fN in unusable_neg:
        print(f"  blok={blk} → -M={mN}  noise: {f0} → {fN}")
else:
    print("Brak bloków Unusable dla -M.")