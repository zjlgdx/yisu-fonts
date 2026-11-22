#!/usr/bin/env python3
"""The gate on how parts sit together: measured, compared with a baseline.

    tools/hz_gate.py                 exit 1 when a drawing got worse
    tools/hz_gate.py --batch A.py    with a round's draft batches
    tools/hz_gate.py --accept        write the baseline (tools/hz_gate.tsv)
    tools/hz_gate.py --selftest      seed known defects; each must fail
    tools/hz_gate.py --debt          list what is under the floors today
    tools/hz_gate.py --where 慮閾     where each form's closest strokes are

The scans before this one (hz_balance.py, hz_bars.py) print lists to look at.
A list nobody must clear is not a check: 0.980 shipped 寢 with 又 on 冖, and
慮's 思 lay on 虍's 七 for two hundred versions, while every scan "passed".
This one measures every form, keeps the numbers in a file, and fails when a
form gets worse than the file says it was.

For every node of a drawing (box, lr, tb), each pair of sibling parts, in the
character's own frame:

  clear   least distance between the strokes of two parts, centre line to
          centre line. Nothing is skipped: a part that encloses another
          (虍, 門, 宀) is measured stroke against stroke like any other.
  bars    least distance between two level strokes of different parts that
          overlap sideways by 100 or more, or two upright ones that overlap
          by 100 up and down. Strokes that run side by side need more room
          than slanted ones before the pens draw one thick bar (舅's 臼 on
          男) or a double wall (阃's 困 along 门's right side).

and for the whole form: width and height of the ink, and whether the
mainland form is a different drawing from Taiwan's.

Fails, against the baseline:
  tighter   clear fell by more than 8 and is now under 60
  bars      bars fell by more than 8 and is now under 70
  narrower  the ink lost more than 30 of width (or height) and is under 620
  merged    the two forms were different drawings and are now the same
  new       a form the baseline lacks is under a floor (clear 30, bars 55)

A form that was already tight stays in the baseline as debt (--debt lists
it); it fails only if it gets worse. A change meant to be so is accepted
with --accept, and the baseline's diff then shows the reviewer every number
that moved. Run --selftest after changing this file: a gate that has not
been seen to fail proves nothing.
"""
import argparse
import re
import sys
from pathlib import Path

import _repo

BASE = Path(__file__).with_name('hz_gate.tsv')
TOK = re.compile(r'[A-Za-z]|-?\d+\.?\d*')
CLEAR_DROP, CLEAR_ZONE, CLEAR_FLOOR = 8, 60, 30
BARS_DROP, BARS_ZONE, BARS_FLOOR = 8, 70, 55
SIZE_DROP, SIZE_ZONE = 30, 620
FAR = 999


def polyline(d):
    """A path's centre line as points; curves sampled."""
    t, i, cmd, pts, cur = TOK.findall(d), 0, None, [], (0.0, 0.0)
    while i < len(t):
        if t[i].isalpha():
            cmd = t[i]
            i += 1
            continue
        if cmd in 'ML':
            cur = (float(t[i]), float(t[i + 1]))
            pts.append(cur)
            i += 2
        elif cmd == 'l':
            cur = (cur[0] + float(t[i]), cur[1] + float(t[i + 1]))
            pts.append(cur)
            i += 2
        elif cmd == 'C':
            p = [cur] + [(float(t[i + k]), float(t[i + k + 1])) for k in (0, 2, 4)]
            for s in range(1, 9):
                u = s / 8
                v = 1 - u
                pts.append(tuple(v ** 3 * p[0][a] + 3 * v * v * u * p[1][a] + 3 * v * u * u * p[2][a] + u ** 3 * p[3][a]
                                 for a in (0, 1)))
            cur = p[3]
            i += 6
        else:
            raise ValueError(f'path command {cmd!r} in {d!r}')
    return pts


def seg_dist(a, b, c, d):
    """Least distance between segments ab and cd."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    def point(p, s, e):
        vx, vy = e[0] - s[0], e[1] - s[1]
        n = vx * vx + vy * vy
        u = 0 if not n else max(0, min(1, ((p[0] - s[0]) * vx + (p[1] - s[1]) * vy) / n))
        return ((p[0] - s[0] - u * vx) ** 2 + (p[1] - s[1] - u * vy) ** 2) ** 0.5
    if (cross(a, b, c) > 0) != (cross(a, b, d) > 0) and (cross(c, d, a) > 0) != (cross(c, d, b) > 0):
        return 0.0
    return min(point(a, c, d), point(b, c, d), point(c, a, b), point(d, a, b))


def shape(strokes):
    """[(kind, points, bbox)] of flattened strokes."""
    out = []
    for kind, d in strokes:
        pts = polyline(d)
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((kind, pts, (min(xs), min(ys), max(xs), max(ys))))
    return out


def pair(p, q, limit=120):
    """(clear, bars, where) between two parts' shapes; where is the middle of
    the two closest segments."""
    clear, bars, where = FAR, FAR, None
    for ka, a, ba in p:
        for kb, b, bb in q:
            if ba[0] - bb[2] > limit or bb[0] - ba[2] > limit or ba[1] - bb[3] > limit or bb[1] - ba[3] > limit:
                continue
            for i in range(len(a) - 1):
                for j in range(len(b) - 1):
                    d = seg_dist(a[i], a[i + 1], b[j], b[j + 1])
                    if d < clear:
                        clear = d
                        where = tuple(round((a[i][k] + a[i + 1][k]) / 2) for k in (0, 1)) + tuple(round((b[j][k] + b[j + 1][k]) / 2) for k in (0, 1))
                    if ka in 'EG' and kb in 'EG':
                        (x0, y0), (x1, y1), (u0, v0), (u1, v1) = a[i], a[i + 1], b[j], b[j + 1]
                        if abs(x1 - x0) >= 120 and abs(y1 - y0) <= 25 and abs(u1 - u0) >= 120 and abs(v1 - v0) <= 25:
                            if min(max(x0, x1), max(u0, u1)) - max(min(x0, x1), min(u0, u1)) >= 100:
                                bars = min(bars, abs((y0 + y1) / 2 - (v0 + v1) / 2))
                        if abs(y1 - y0) >= 120 and abs(x1 - x0) <= 25 and abs(v1 - v0) >= 120 and abs(u1 - u0) <= 25:
                            if min(max(y0, y1), max(v0, v1)) - max(min(y0, y1), min(v0, v1)) >= 100:
                                bars = min(bars, abs((x0 + x1) / 2 - (u0 + u1) / 2))
    return clear, bars, where


def measure(item, hanzi, count=None, where=None):
    """(clear, bars, width, height) of one form. `where`, a list, gets the
    closest pair's two points."""
    best = [FAR, FAR]

    def walk(node, box):
        if isinstance(node, list):
            return
        x0, y0, x1, y1 = box
        sx, sy = (x1 - x0) / 1000, (y1 - y0) / 1000

        def into(b):
            return (x0 + b[0] * sx, y0 + b[1] * sy, x0 + b[2] * sx, y0 + b[3] * sy)
        if node[0] == 'lr':
            kids = [(node[1], into((0, 0, 1000 * node[3], 1000))), (node[2], into((1000 * node[3], 0, 1000, 1000)))]
        elif node[0] == 'tb':
            kids = [(node[1], into((0, 0, 1000, 1000 * node[3]))), (node[2], into((0, 1000 * node[3], 1000, 1000)))]
        else:
            kids = [(p, into(b)) for p, b in node[1]]
        shapes = [shape(hanzi.flatten(p, b)) for p, b in kids]
        for i in range(len(shapes)):
            for j in range(i + 1, len(shapes)):
                c, b, at = pair(shapes[i], shapes[j])
                if c < best[0] and where is not None:
                    where[:] = [at]
                best[0], best[1] = min(best[0], c), min(best[1], b)
                if count is not None:
                    count['pairs'] += 1
        if count is not None:
            count['nodes'] += 1
        for p, b in kids:
            walk(p, b)
    walk(item, (0, 0, 1000, 1000))
    whole = shape(hanzi.flatten(item))
    if not whole:
        return None
    w = max(s[2][2] for s in whole) - min(s[2][0] for s in whole)
    h = max(s[2][3] for s in whole) - min(s[2][1] for s in whole)
    return round(best[0]), round(best[1]), round(w), round(h)


def is_han(ch):
    return len(ch) == 1 and (0x3400 <= ord(ch) <= 0x9FFF or 0x20000 <= ord(ch) <= 0x3FFFF)


def survey(H, hanzi, count=None):
    """{(form, ch): (clear, bars, w, h, differs)}; form C is Taiwan's or the shared drawing, S the mainland's."""
    out = {}
    for ch, item in H.C.items():
        if is_han(ch):
            m = measure(item, hanzi, count)
            if m:
                out['C', ch] = m + (0,)
    for ch, item in H.ZHS.items():
        if is_han(ch):
            m = measure(item, hanzi, count)
            if m:
                differs = int(ch not in H.C or hanzi.flatten(item) != hanzi.flatten(H.C[ch]))
                out['S', ch] = m + (differs,)
    return out


def read_base():
    base = {}
    for line in BASE.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            f, ch, *n = line.split('\t')
            base[f, ch] = tuple(int(v) for v in n)
    return base


def judge(key, now, was):
    """Reasons this form fails, given its baseline row (None when new)."""
    clear, bars, w, h, differs = now
    why = []
    if was is None:
        if clear < CLEAR_FLOOR:
            why.append(f'new, parts {clear} apart (floor {CLEAR_FLOOR})')
        if bars < BARS_FLOOR:
            why.append(f'new, side-by-side strokes {bars} apart (floor {BARS_FLOOR})')
        return why
    if clear < was[0] - CLEAR_DROP and clear < CLEAR_ZONE:
        why.append(f'tighter: parts {was[0]} -> {clear} apart')
    if bars < was[1] - BARS_DROP and bars < BARS_ZONE:
        why.append(f'bars: side-by-side strokes {was[1]} -> {bars} apart')
    if w < was[2] - SIZE_DROP and w < SIZE_ZONE:
        why.append(f'narrower: {was[2]} -> {w} wide')
    if h < was[3] - SIZE_DROP and h < SIZE_ZONE:
        why.append(f'shorter: {was[3]} -> {h} high')
    if key[0] == 'S' and was[4] and not differs:
        why.append("merged: the mainland form is now Taiwan's drawing")
    return why


def selftest(H, hanzi):
    """Seed the defects this gate exists for, each as a change to today's
    drawing; every one must fail."""
    box = H.box
    seeds = [
        ('lower part pushed up into the head (慮)', 'C', '慮',
         box((H.K['虍'], H.FULL), (H.C['思'], (240, 330, 960, 1000))), 'tighter'),
        ('level strokes of two parts on each other (舅)', 'C', '舅',
         box((H.K['臼'], (57, 0, 943, 520)), (H.C['男'], (-21, 440, 1021, 1000))), 'bars'),
        ('a widened part run through its neighbour (凯)', 'C', '凯',
         box((H.C['岂'], (-200, 0, 900, 1000)), (H.K['几'], (520, 100, 1000, 1000))), 'tighter'),
        ('a stack squeezed narrow (員)', 'C', '員',
         box((H.C['員'], (250, 0, 750, 1000))), 'narrower'),
        ('a frame inside a frame, wall along wall (阃)', 'C', '阃',
         box((H.K['门'], H.FULL), (H.C['困'], (300, 240, 880, 880))), 'bars'),
        ('what stands inside 門 pushed up onto the leaves (問)', 'C', '問',
         box((H.K['門框'], H.FULL), (H.K['口'], (320, 300, 680, 800))), 'tighter'),
    ]
    bad = 0
    for name, form, ch, item, want in seeds:
        why = judge((form, ch), measure(item, hanzi) + (0,), measure(H.C[ch], hanzi) + (0,))
        ok = any(w.startswith(want) for w in why)
        bad += not ok
        print(f"  {'red ' if ok else 'GREEN'}  {name}: {'; '.join(why) or 'passed'}")
    was = measure(H.ZHS['房'], hanzi) + (1,)
    why = judge(('S', '房'), was[:4] + (0,), was)
    ok = any(w.startswith('merged') for w in why)
    bad += not ok
    print(f"  {'red ' if ok else 'GREEN'}  the mainland form lost to an inline redraw (房): {'; '.join(why) or 'passed'}")
    print('selftest: every seeded defect fails' if not bad else f'selftest: {bad} seeded defects PASSED the gate')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', action='store_true')
    ap.add_argument('--where', default='')
    a = ap.parse_args()
    H = _repo.load(a.batch)
    import hanzi
    if a.selftest:
        sys.exit(1 if selftest(H, hanzi) else 0)
    if a.where:
        for ch in a.where:
            for f, table in (('default', H.C), ('mainland', H.ZHS)):
                if ch in table:
                    at = []
                    m = measure(table[ch], hanzi, where=at)
                    print(f'{ch} ({f}): parts {m[0]} apart, side-by-side strokes {m[1]}, ink {m[2]} x {m[3]}; closest at {at[0] if at else None}')
        return
    count = {'nodes': 0, 'pairs': 0}
    now = survey(H, hanzi, count)
    if a.accept:
        lines = ['# tools/hz_gate.py --accept. form (C Taiwan/shared, S mainland), character, clear, bars, width, height, differs']
        lines += ['\t'.join([f, ch] + [str(v) for v in m]) for (f, ch), m in sorted(now.items())]
        BASE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'baseline written: {len(now)} forms')
        return
    base = read_base()
    fails = [(k, why) for k, m in sorted(now.items()) for why in [judge(k, m, base.get(k))] if why]
    gone = [k for k in base if k not in now]
    tight = sorted((m[0], k[1]) for k, m in now.items() if m[0] < CLEAR_FLOOR)
    flat = sorted((m[1], k[1]) for k, m in now.items() if m[1] < BARS_FLOOR)
    print(f"measured {len(now)} forms: {count['nodes']} nodes, {count['pairs']} pairs of parts, none skipped; "
          f"{len([k for k in now if k not in base])} new, {len(gone)} gone from the baseline")
    print(f'debt (in the baseline, fails only if worse): {len(tight)} forms with parts under {CLEAR_FLOOR} apart, '
          f'{len(flat)} with side-by-side strokes under {BARS_FLOOR}')
    if a.debt:
        print('  parts:', '  '.join(f'{ch} {v}' for v, ch in tight))
        print('  side by side:', '  '.join(f'{ch} {v}' for v, ch in flat))
    for (f, ch), why in fails:
        print(f"FAIL {ch} ({'mainland' if f == 'S' else 'default'}): {'; '.join(why)}")
    print(f'{len(fails)} forms got worse' if fails else 'no form got worse')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
