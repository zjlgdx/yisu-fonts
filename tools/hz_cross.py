"""tools/hz_cross.py [--batch A.py,B.py]

Lists the parts where a 撇 written after a 捺 crosses it. A 撇 comes before
the 捺 it meets, so this is two mistakes at once, in the order and in the
shape: 癶 was drawn 捺 first with both its 撇 through it (登 發 癸 and 25 more
carried that until 0.970), and 瞭's 丷 ran through 大's 捺. It prints nothing
when all is well; look at what it lists on a sheet.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo

ap = argparse.ArgumentParser()
ap.add_argument('--batch', default='')
h = _repo.load(ap.parse_args().batch)


def poly(d):
    t = re.findall(r'[MLC]|-?\d+(?:\.\d+)?', d); pts = []; i = 0; cur = None
    while i < len(t):
        c = t[i]; i += 1
        if c in 'ML':
            cur = (float(t[i]), float(t[i+1])); i += 2; pts.append(cur)
        elif c == 'C':
            p = [cur] + [(float(t[i+2*k]), float(t[i+2*k+1])) for k in range(3)]; i += 6
            for s in range(1, 9):
                u = s / 8; a = (1-u)**3; b = 3*u*(1-u)**2; c2 = 3*u*u*(1-u); e = u**3
                pts.append((a*p[0][0]+b*p[1][0]+c2*p[2][0]+e*p[3][0], a*p[0][1]+b*p[1][1]+c2*p[2][1]+e*p[3][1]))
            cur = p[3]
    return pts

def cross(a, b):
    """True when the polylines cross away from all four ends."""
    def frac(pl):
        L = [0]
        for p, q in zip(pl, pl[1:]): L.append(L[-1] + ((p[0]-q[0])**2 + (p[1]-q[1])**2) ** .5)
        return L
    la, lb = frac(a), frac(b)
    for i in range(len(a)-1):
        for j in range(len(b)-1):
            (x1,y1),(x2,y2),(x3,y3),(x4,y4) = a[i],a[i+1],b[j],b[j+1]
            d = (x2-x1)*(y4-y3)-(y2-y1)*(x4-x3)
            if abs(d) < 1e-9: continue
            t = ((x3-x1)*(y4-y3)-(y3-y1)*(x4-x3))/d; u = ((x3-x1)*(y2-y1)-(y3-y1)*(x2-x1))/d
            if 0 <= t <= 1 and 0 <= u <= 1:
                fa = (la[i]+t*(la[i+1]-la[i]))/la[-1]; fb = (lb[j]+u*(lb[j+1]-lb[j]))/lb[-1]
                if .2 < fa < .8 and .2 < fb < .8: return True
    return False

seen = {}
def walk(x, name):
    if isinstance(x, list):
        seen.setdefault(id(x), (name, x))
    elif isinstance(x, tuple) and x and x[0] == 'box':
        for p, _ in x[1]: walk(p, name)
    elif isinstance(x, tuple) and x and x[0] in ('lr', 'tb'):
        walk(x[1], name); walk(x[2], name)
for d, tag in ((h.K, 'K'), (h.L, 'L'), (h.C, 'C')):
    for n, v in d.items(): walk(v, n)
out = []
for name, strokes in seen.values():
    pl = [(k, poly(d)) for k, d in strokes]
    for i, (k1, p1) in enumerate(pl):
        for k2, p2 in pl[i + 1:]:
            if k1 == 'N' and k2 == 'P' and cross(p1, p2):
                out.append(name)
print(f'  {len(set(out))} with a 撇 through an earlier 捺' + (': ' + ' '.join(dict.fromkeys(out)) if out else ''))
sys.exit(1 if out else 0)
