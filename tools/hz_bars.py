#!/usr/bin/env python3
"""Level strokes of two parts lying on each other.

    tools/hz_bars.py [CHARS] [--gap 55]

A box() of stacked parts can leave the bottom 橫 of one and the top 橫 of the
next so close that the pens draw one thick bar (舅's 臼 on 男, 慮's 思 under
虍's 七, 闡's 單 under 門's leaves).  Two level strokes need more room than a
gap between slanted ones: about 70 units from centre to centre.

For each character built by box(), this lists the nearest pair of level
segments from different parts that overlap sideways by 100 units or more and
are closer than --gap.  It is a list to look at on a sheet (hz_sheet.py), not
a gate: some forms have such a pair by nature.
"""
import argparse

import _repo  # noqa: F401  (puts the repository on the path)
import hanzi
from hz_balance import is_han, points


def bars(strokes):
    out = []
    for stroke in strokes:
        if stroke[0] not in 'EG':
            continue
        pts = points([stroke])
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if abs(x1 - x0) >= 120 and abs(y1 - y0) <= 25:
                out.append((min(x0, x1), max(x0, x1), (y0 + y1) / 2))
    return out


def nearest(item):
    parts = [bars(hanzi.flatten(p, b)) for p, b in item[1]]
    best = None
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            for a in parts[i]:
                for b in parts[j]:
                    if min(a[1], b[1]) - max(a[0], b[0]) >= 100:
                        d = abs(a[2] - b[2])
                        if best is None or d < best:
                            best = d
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chars', nargs='?', default='')
    ap.add_argument('--gap', type=float, default=55)
    a = ap.parse_args()
    hits = []
    for ch, item in hanzi.C.items():
        if not is_han(ch) or (a.chars and ch not in a.chars):
            continue
        if isinstance(item, tuple) and item and item[0] == 'box':
            d = nearest(item)
            if d is not None and d < a.gap:
                hits.append((d, ch))
    hits.sort()
    print('  '.join(f'{ch} {d:.0f}' for d, ch in hits))
    print(f'{len(hits)} with level strokes of two parts closer than {a.gap:g}')


if __name__ == '__main__':
    main()
