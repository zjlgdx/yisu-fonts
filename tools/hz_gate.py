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
  bars    least distance between two level runs of different parts that
          overlap sideways by 60 or more, or two upright ones that overlap
          by 60 up and down, whatever the stroke is called (月's left side
          is a 撇 that stands upright for 570). Strokes side by side need more room
          than slanted ones before the pens draw one thick bar (舅's 臼 on
          男) or a double wall (阃's 困 along 门's right side).

and for the whole form: width and height of the ink, and whether the
mainland form is a different drawing from Taiwan's.

Fails, against the baseline:
  tighter   clear fell by more than 8 and is now under 60
  bars      bars fell by more than 8 and is now under 70
  narrower  the ink lost more than 30 of width (or height) and is under 620
  merged    the two forms were different drawings and are now the same
  touching  more pairs of strokes of different parts lie under 20 apart
            than before. clear and bars are each form's least, so a form
            whose parts already meet somewhere would hide a new collision
            elsewhere; the counts do not
  near      the same count under 40 apart: a gap of 25 is one stroke to
            the heavy pen and is not touching
  flat      the same count for side-by-side runs under 45 apart
  unbuilt   fewer pairs of parts are measured than before: two parts were
            written as one list of strokes, and what is inside a list is
            not measured
  gone      a form in the baseline is no longer drawn
  redefined (--batch) the batch gives a part or character that is already
            drawn a different drawing. The characters built on the old one
            keep it, in the batch and after a merge, so the two would differ:
            redraw it in hanzi_strokes.py
  new       a form the baseline lacks is under a floor (clear 30, bars 55)

The zones are where the pens start to run strokes together: a form that goes
from 156 to 60 apart got tighter and still passes, on purpose. --batch
measures a draft's default forms only; the mainland forms are derived when
the batch is merged, so the gate runs again after merge_round.py (in
check_fonts.py).

A form that was already tight stays in the baseline as debt (--debt lists
it); it fails only if it gets worse. One that a change moved and that is
still under a floor is listed on every run until the baseline is accepted:
盧's 田 went from 5 off 虍 to 32 off 皿, which is better and still one bar. A change meant to be so is accepted
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
TOUCH, NEAR, FLAT, RUN = 20, 40, 45, 60
REASONS = ('tighter', 'bars', 'narrower', 'shorter', 'merged', 'touching', 'near', 'flat', 'unbuilt', 'gone', 'redefined', 'new, parts', 'new, side')
FAR = 999


def polyline(d):
    """A path's centre line as points; curves sampled."""
    t, i, cmd, pts, cur = TOK.findall(d), 0, None, [], (0.0, 0.0)
    while i < len(t):
        if t[i].isalpha():
            cmd = t[i]
            i += 1
            if cmd in 'Zz' and pts:
                pts.append(pts[0])
            elif cmd not in 'MLlC' or (cmd == 'M' and pts):
                raise ValueError(f'path command {cmd!r} in {d!r}: one M, then L, l, C or Z')
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
    """(clear, bars, where, touching, flat, near) between two parts' shapes;
    where is the middle of the two closest segments; touching, near and flat
    count the pairs of strokes under TOUCH and NEAR apart and side by side
    under FLAT."""
    clear, bars, where, touching, near_n, flat = FAR, FAR, None, 0, 0, 0
    for ka, a, ba in p:
        for kb, b, bb in q:
            if ba[0] - bb[2] > limit or bb[0] - ba[2] > limit or ba[1] - bb[3] > limit or bb[1] - ba[3] > limit:
                continue
            near, side = FAR, FAR
            for i in range(len(a) - 1):
                for j in range(len(b) - 1):
                    d = seg_dist(a[i], a[i + 1], b[j], b[j + 1])
                    near = min(near, d)
                    if d < clear:
                        clear = d
                        where = tuple(round((a[i][k] + a[i + 1][k]) / 2) for k in (0, 1)) + tuple(round((b[j][k] + b[j + 1][k]) / 2) for k in (0, 1))
                    (x0, y0), (x1, y1), (u0, v0), (u1, v1) = a[i], a[i + 1], b[j], b[j + 1]
                    if abs(x1 - x0) >= RUN and abs(y1 - y0) <= 25 and abs(u1 - u0) >= RUN and abs(v1 - v0) <= 25:
                        if min(max(x0, x1), max(u0, u1)) - max(min(x0, x1), min(u0, u1)) >= RUN:
                            side = min(side, abs((y0 + y1) / 2 - (v0 + v1) / 2))
                    if abs(y1 - y0) >= RUN and abs(x1 - x0) <= 25 and abs(v1 - v0) >= RUN and abs(u1 - u0) <= 25:
                        if min(max(y0, y1), max(v0, v1)) - max(min(y0, y1), min(v0, v1)) >= RUN:
                            side = min(side, abs((x0 + x1) / 2 - (u0 + u1) / 2))
            bars = min(bars, side)
            touching += near < TOUCH
            near_n += near < NEAR
            flat += side < FLAT
    return clear, bars, where, touching, flat, near_n


def measure(item, hanzi, count=None, where=None):
    """(clear, bars, width, height, touching, flat, pairs, near) of one form;
    pairs is how many pairs of sibling parts were measured. `where`, a list,
    gets the closest pair's two points."""
    best = [FAR, FAR, 0, 0, 0, 0]

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
                c, b, at, t, f, n = pair(shapes[i], shapes[j])
                if c < best[0] and where is not None:
                    where[:] = [at]
                best[:] = min(best[0], c), min(best[1], b), best[2] + t, best[3] + f, best[4] + 1, best[5] + n
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
    return round(best[0]), round(best[1]), round(w), round(h), best[2], best[3], best[4], best[5]


def is_han(ch):
    return len(ch) == 1 and (0x3400 <= ord(ch) <= 0x9FFF or 0xF900 <= ord(ch) <= 0xFAFF or 0x20000 <= ord(ch) <= 0x3FFFF)


def survey(H, hanzi, count=None, only=None):
    """{(form, ch): (clear, bars, w, h, differs, touching, flat, pairs, near)}; form C is
    Taiwan's or the shared drawing, S the mainland's. `only` keeps it to
    some characters."""
    out = {}
    for ch, item in H.C.items():
        if is_han(ch) and (only is None or ch in only):
            m = measure(item, hanzi, count)
            if m:
                out['C', ch] = m[:4] + (0,) + m[4:]
    for ch, item in H.ZHS.items():
        if is_han(ch) and (only is None or ch in only):
            m = measure(item, hanzi, count)
            if m:
                differs = int(ch not in H.C or hanzi.flatten(item) != hanzi.flatten(H.C[ch]))
                out['S', ch] = m[:4] + (differs,) + m[4:]
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
    if now is None:
        return ['gone: in the baseline and no longer drawn']
    clear, bars, w, h, differs, touching, flat, pairs, near = now
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
    if touching > was[5]:
        why.append(f'touching: {was[5]} -> {touching} pairs of strokes of different parts under {TOUCH} apart')
    if flat > was[6]:
        why.append(f'flat: {was[6]} -> {flat} pairs of side-by-side strokes under {FLAT} apart')
    if near > was[8]:
        why.append(f'near: {was[8]} -> {near} pairs of strokes of different parts under {NEAR} apart')
    if pairs < was[7]:
        why.append(f'unbuilt: {was[7]} -> {pairs} pairs of parts measured; what is written as one list of strokes is not measured')
    return why


def redefinitions(H, drawn, hanzi):
    """Names in `drawn`, [(table, key, item)] taken before the batches ran,
    that the batches gave a different drawing."""
    return [f"{t}['{k}']" for t, k, v in drawn if getattr(H, t).get(k) is not v
            and (k not in getattr(H, t) or hanzi.flatten(getattr(H, t)[k]) != hanzi.flatten(v))]


def verdict(now, base):
    """[(key, reasons)] for every form that fails: worse, or gone."""
    return [(k, why) for k in sorted(set(now) | set(base)) for why in [judge(k, now.get(k), base.get(k))] if why]


def selftest(H, hanzi):
    """Seed the defects this gate exists for and run each through the same
    survey and verdict as the gate; every one must fail, for the reason it
    was seeded for, and every reason the gate has must have a seed. A seed is
    (what, form, character, before, after, reason): before None is today's
    drawing, after None deletes it, a character None is one not drawn yet."""
    box, S, FULL = H.box, H.S, H.FULL
    bar = lambda y, x0=100, x1=900: S(f'E M{x0} {y} L{x1} {y}')
    wall = lambda x: S(f'E M{x} 100 L{x} 900')
    free = next(chr(c) for c in range(0x4E00, 0x9FFF) if chr(c) not in H.C and chr(c) not in H.ZHS)
    seeds = [
        ('lower part pushed up into the head (慮)', 'C', '慮', None,
         box((H.K['虍'], FULL), (H.C['思'], (240, 330, 960, 1000))), 'tighter'),
        ('level strokes of two parts on each other (舅)', 'C', '舅', None,
         box((H.K['臼'], (57, 0, 943, 520)), (H.C['男'], (-21, 440, 1021, 1000))), 'bars'),
        ('a widened part run through its neighbour (凯)', 'C', '凯', None,
         box((H.C['岂'], (-200, 0, 900, 1000)), (H.K['几'], (520, 100, 1000, 1000))), 'tighter'),
        ('a stack squeezed narrow (員)', 'C', '員', None, box((H.C['員'], (250, 0, 750, 1000))), 'narrower'),
        ('a stack squeezed flat (員)', 'C', '員', None, box((H.C['員'], (0, 250, 1000, 750))), 'shorter'),
        ('a frame inside a frame, wall along wall (阃)', 'C', '阃', None,
         box((H.K['门'], FULL), (H.C['困'], (300, 240, 880, 880))), 'bars'),
        ('a wall beside the upright run of a 撇 (月)', 'C', '月', box((H.C['月'], FULL), (wall(700), FULL)),
         box((H.C['月'], FULL), (wall(245), FULL)), 'bars'),
        ('what stands inside 門 pushed up onto the leaves (問)', 'C', '問', None,
         box((H.K['門框'], FULL), (H.K['口'], (320, 300, 680, 800))), 'tighter'),
        ('a stroke across parts that already met elsewhere (國)', 'C', '國', None,
         box((H.C['國'], FULL), (S('P M330 330 L670 670'), FULL)), 'touching'),
        ('a second pair of bars as close as the first', 'C', '員', box((bar(300), FULL), (bar(340), FULL)),
         box((bar(300), FULL), (bar(340), FULL), (wall(950), FULL), (wall(990), FULL)), 'flat'),
        ('a built character redrawn as loose strokes (慮)', 'C', '慮', None,
         S('E M80 500 L920 500; E M80 505 L920 505; E M500 40 L500 960'), 'unbuilt'),
        ('the mainland form lost to an inline redraw (房)', 'S', '房', None, H.C['房'], 'merged'),
        ('a drawing deleted (房)', 'S', '房', None, None, 'gone'),
        ('a new character with parts on each other', 'C', None, None,
         box((S('P M200 200 L800 800'), FULL), (S('P M800 200 L200 800'), FULL)), 'new, parts'),
        ('a new character with two short bars as one', 'C', None, None,
         box((bar(300, 200, 270), FULL), (bar(330, 200, 270), FULL)), 'new, side'),
        ('two short walls 25 apart, far from where the parts already cross', 'C', None,
         box((S('P M50 50 L350 350'), FULL), (S('P M350 50 L50 350'), FULL), (S('E M700 700 L700 750'), FULL), (S('E M760 700 L760 750'), FULL)),
         box((S('P M50 50 L350 350'), FULL), (S('P M350 50 L50 350'), FULL), (S('E M700 700 L700 750'), FULL), (S('E M725 700 L725 750'), FULL)), 'near'),
        ('two parts of three written as one list', 'C', None,
         box((bar(300), FULL), (bar(370), FULL), (wall(50), FULL)),
         box((S('E M100 300 L900 300; E M100 330 L900 330'), FULL), (wall(50), FULL)), 'unbuilt'),
    ]
    bad = 0
    for name, form, ch, before, item, want in seeds:
        table = H.C if form == 'C' else H.ZHS
        ch = ch or free
        keep = table.get(ch)
        try:
            if before is not None:
                table[ch] = before
            was = survey(H, hanzi, only=ch)
            if item is None:
                del table[ch]
            else:
                table[ch] = item
            fails = dict(verdict(survey(H, hanzi, only=ch), was))
        finally:
            if keep is None:
                table.pop(ch, None)
            else:
                table[ch] = keep
        why = fails.get((form, ch), [])
        ok = any(w.startswith(want) for w in why)
        bad += not ok
        print(f"  {'red ' if ok else 'GREEN'}  {name}: {'; '.join(why) or 'passed'}")
    drawn, keep = [('K', '木', H.K['木'])], H.K['木']
    H.K['木'] = bar(500)
    ok = redefinitions(H, drawn, hanzi) == ["K['木']"]
    H.K['木'] = keep
    ok = ok and not redefinitions(H, drawn, hanzi)
    bad += not ok
    print(f"  {'red ' if ok else 'GREEN'}  a batch that redraws a part already drawn (木)")
    unseeded = [r for r in REASONS if r not in {x[-1] for x in seeds} | {'redefined'}]
    if unseeded:
        print('  no seed for:', ', '.join(unseeded))
    bad += len(unseeded)
    print('selftest: every seeded defect fails, and every reason has a seed' if not bad
          else f'selftest: {bad} seeded defects PASSED the gate or reasons have no seed')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', action='store_true')
    ap.add_argument('--where', default='')
    a = ap.parse_args()
    H = _repo.load()
    import hanzi
    drawn = [(t, k, v) for t in 'KC' for k, v in getattr(H, t).items()]
    H = _repo.load(a.batch)
    redefined = redefinitions(H, drawn, hanzi)
    if a.selftest:
        sys.exit(1 if selftest(H, hanzi) else 0)
    if a.where:
        for ch in a.where:
            for f, table in (('default', H.C), ('mainland', H.ZHS)):
                if ch in table:
                    at = []
                    m = measure(table[ch], hanzi, where=at)
                    if not m:
                        continue
                    print(f'{ch} ({f}): parts {m[0]} apart, side-by-side strokes {m[1]}, ink {m[2]} x {m[3]}, {m[4]} pairs of strokes under {TOUCH} and {m[7]} under {NEAR}, {m[5]} side by side under {FLAT}; closest at {at[0] if at else None}')
        return
    count = {'nodes': 0, 'pairs': 0}
    now = survey(H, hanzi, count)
    if a.accept:
        lines = ['# tools/hz_gate.py --accept. form (C Taiwan/shared, S mainland), character, clear, bars, width, height, differs, touching, flat, pairs, near']
        lines += ['\t'.join([f, ch] + [str(v) for v in m]) for (f, ch), m in sorted(now.items())]
        BASE.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'baseline written: {len(now)} forms')
        return
    base = read_base()
    fails = verdict(now, base)
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
    moved = [(k, m) for k, m in sorted(now.items()) if k in base and m[:2] != base[k][:2]
             and (m[0] < CLEAR_FLOOR or m[1] < BARS_FLOOR) and not judge(k, m, base[k])]
    if moved:
        print(f'moved and still under a floor ({len(moved)}; better than it was is not yet good, so fix each or name it):')
        print('  ' + '  '.join(f"{ch}{'(S)' if f == 'S' else ''} parts {base[f, ch][0]}->{m[0]} side {base[f, ch][1]}->{m[1]}" for (f, ch), m in moved))
    for (f, ch), why in fails:
        print(f"FAIL {ch} ({'mainland' if f == 'S' else 'default'}): {'; '.join(why)}")
    if redefined:
        print('FAIL redefined by the batch, while the characters built on the old drawing keep it: ' + ' '.join(redefined))
    print(f'{len(fails)} forms got worse' if fails else 'no form got worse')
    sys.exit(1 if fails or redefined else 0)


if __name__ == '__main__':
    main()
