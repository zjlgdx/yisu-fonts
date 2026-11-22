"""tools/hz_balance.py [--top 25] [CHARS]

Leads for a polish round, read from the strokes alone (nothing is drawn):

1. Parts that crowd each other: in a character put together with box(), the two
   parts whose strokes come closest, or overlap, measured between the boxes
   their strokes fill. A part that encloses another (門, 囗, 辶) is skipped.
2. Characters whose centre of strokes sits furthest from the middle of the square.
3. Parts too far apart: the widest band no stroke enters, across the character
   (a top and a bottom apart) and down it (a left and a right apart). box()
   maps a part's whole grid, not its ink, so a part drawn low in its grid
   leaves a band above it: 卷's top was squeezed into the upper third with
   air below, and 心 under 思 忘 念 sat a fifth of the square away.
4. Characters of five strokes or more that fill the least of the square's
   height or width: a part drawn as a top (士, 立) used alone or as a side.

二 三 川 and the like are apart by nature, and 元 云 示 hold a 二.

A lead, not a verdict: look at the character on a sheet before changing it.
"""
import argparse
import re

import _repo  # noqa: F401  (puts the repository on the path)
import hanzi

NUM = re.compile(r'-?[\d.]+')


def points(strokes):
    out = []
    for _kind, d in strokes:
        nums = [float(x) for x in NUM.findall(d)]
        out += list(zip(nums[0::2], nums[1::2]))
    return out


def extent(strokes):
    """Box of a part's strokes, and their centre weighted by length (a rough
    measure of where the ink sits: control points stand in for the curve)."""
    xs, ys, mx, my, total = [], [], 0.0, 0.0, 0.0
    for stroke in strokes:
        pts = points([stroke])
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            mx, my, total = mx + n * (x0 + x1) / 2, my + n * (y0 + y1) / 2, total + n
    if not xs:
        return None
    if not total:
        mx, my, total = sum(xs), sum(ys), len(xs)
    return min(xs), min(ys), max(xs), max(ys), mx / total, my / total


def band(spans):
    """The widest gap between spans (lo, hi) once they are merged."""
    spans = sorted(spans)
    best, end = 0, spans[0][1]
    for lo, hi in spans[1:]:
        best, end = max(best, lo - end), max(end, hi)
    return best


def gap(a, b):
    """Room between two parts' boxes: positive is clear space, negative is overlap."""
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def encloses(a, b):
    return a[0] <= b[4] <= a[2] and a[1] <= b[5] <= a[3] and (a[2] - a[0]) * (a[3] - a[1]) > (b[2] - b[0]) * (b[3] - b[1])


def is_han(ch):
    cp = ord(ch)
    return 0x3400 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chars', nargs='?', default='')
    ap.add_argument('--top', type=int, default=20)
    a = ap.parse_args()

    crowded, off, across, down, short, narrow = [], [], [], [], [], []
    for ch, item in hanzi.C.items():
        if not is_han(ch) or (a.chars and ch not in a.chars):
            continue
        whole = extent(hanzi.flatten(item))
        if not whole:
            continue
        off.append((((whole[4] - 500) ** 2 + (whole[5] - 500) ** 2) ** 0.5, ch, whole[4], whole[5]))
        strokes = [points([s]) for s in hanzi.flatten(item)]
        if len(strokes) >= 5:
            across.append((band([(min(y for _, y in s), max(y for _, y in s)) for s in strokes]), ch))
            down.append((band([(min(x for x, _ in s), max(x for x, _ in s)) for s in strokes]), ch))
            short.append((whole[3] - whole[1], ch))
            narrow.append((whole[2] - whole[0], ch))
        if isinstance(item, tuple) and item[0] == 'box' and len(item[1]) >= 2:
            parts = [extent(hanzi.flatten(p, b)) for p, b in item[1]]
            best = None
            for i in range(len(parts)):
                for j in range(i + 1, len(parts)):
                    p, q = parts[i], parts[j]
                    if not p or not q or encloses(p, q) or encloses(q, p):
                        continue
                    g = gap(p, q)
                    if best is None or g < best[0]:
                        best = (g, i + 1, j + 1)
            if best:
                crowded.append((best[0], ch, best[1], best[2]))

    crowded.sort()
    off.sort(reverse=True)
    print(f'{len(off)} characters\n\n== parts closest together (part numbers in box() order)')
    for g, ch, i, j in crowded[:a.top]:
        print(f'  {ch}  {g:+6.0f}  parts {i} and {j}')
    print('\n== centres furthest from the middle')
    for dist, ch, cx, cy in off[:a.top]:
        print(f'  {ch}  {dist:5.0f}  at ({cx:.0f}, {cy:.0f})')
    for title, rows in (('widest empty band across (top and bottom apart)', sorted(across, reverse=True)),
                        ('widest empty band down (left and right apart)', sorted(down, reverse=True)),
                        ('least height filled', sorted(short)), ('least width filled', sorted(narrow))):
        print(f'\n== {title}\n  ' + '  '.join(f'{ch} {n:.0f}' for n, ch in rows[:a.top]))


if __name__ == '__main__':
    main()
