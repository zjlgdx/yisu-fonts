#!/usr/bin/env python3
"""The gate on what is inside one part, and on two characters drawn as one.

    tools/hz_inside.py                 exit 1 on a finding the baseline lacks
    tools/hz_inside.py --batch A.py    with a round's draft batches
    tools/hz_inside.py --accept        write the baseline (tools/hz_inside.tsv)
    tools/hz_inside.py --selftest      seed known defects; each must be found
    tools/hz_inside.py --debt          list what the baseline holds today

hz_gate.py measures how sibling parts sit together. It does not look inside a
list of strokes, and it does not compare one character with another, so 0.991
shipped all of these with the gate green:

  same    two characters with the very same strokes, in any order (沈 was
          沉's, 剝 was 剥's, 朮 was 术's, 伫 was 佇's): one of the two is not
          its own form. Compared among Taiwan's forms and among the
          mainland's.
  twice   two strokes of one part that run along each other for 60 or more,
          12 or less apart and in the same direction: one line drawn twice
          (𠂤's middle bar, 官's), which the heavy pens draw as a blot.
          Level, upright, slanted or curved, in one piece or many.
  dot     a 點 that crosses another stroke of its part away from both ends.
          The 乂 of 区 and 网 is a 撇 and a 點 of about its length crossed
          in the middle and is left alone; a short dot through a 撇 (刃 was
          drawn so) or a dot through a bar is not that.
  flick   a stroke, not written as a 撇, that comes down upright for 250 or
          more and ends in a short tail that keeps falling, to the left. A
          豎提 turns up and to the right (民 and 氏 had it backwards); a hook
          turns up as it goes left and is not this.

twice, dot and flick are found in the list of strokes where they are drawn
(K, L or a character's own) and named by it, so one finding is one thing to
fix however many characters hold the part. A character built of several
unnamed lists has them numbered: C['字']#2.

The baseline keeps how many of each a part has. A part with more than the
baseline says fails, whether the baseline has it at all or not, so debt in a
part cannot hide a new fault beside it. One with fewer is reported as
cleared. --accept prints what it adds and drops, and is for after each
addition has been looked at on a sheet: the baseline's diff is what the
reviewer reads. Some of what the baseline holds is right as drawn (虫's dot
on the end of its 提); it stays there so that the count cannot grow.

--batch sees a draft before merge_round.py has run hanzi_strokes.py's own
last steps over it (the narrowed 辶 forms, the mainland forms), so `same` is
decided again by check_fonts.py after the merge. Run --selftest after
changing this file.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import _repo
from hz_gate import is_han, polyline

BASE = Path(__file__).with_name('hz_inside.tsv')
RUN, TWICE, STEP = 60, 12, 10
DROP, TAIL = 250, 260
CHECKS = ('same', 'twice', 'dot', 'flick')


def parts(h):
    """[(name, strokes)] for every list of strokes, named by the entry that
    is that list (C['官'], not the 管 built on it), else by the first that
    holds it; K before L before C. Lists that share a name are numbered."""
    seen = {}

    def walk(x, name):
        if isinstance(x, list):
            seen.setdefault(id(x), (name, x))
        elif isinstance(x, tuple) and x and x[0] == 'box':
            for p, _ in x[1]:
                walk(p, name)
        elif isinstance(x, tuple) and x and x[0] in ('lr', 'tb'):
            walk(x[1], name)
            walk(x[2], name)
    for own in (True, False):
        for d, tag in ((h.K, 'K'), (h.L, 'L'), (h.C, 'C'), (h.ZHS, 'ZHS')):
            for n, v in d.items():
                # kana, punctuation and symbols have their own rules
                if (tag in 'KL' or is_han(n)) and (isinstance(v, list) or not own):
                    walk(v, f"{tag}['{n}']")
    out, used = [], Counter()
    for name, strokes in seen.values():
        used[name] += 1
        out.append((name if used[name] == 1 else f'{name}#{used[name]}', strokes))
    return out


def length(pts):
    return sum(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** .5 for p, q in zip(pts, pts[1:]))


def samples(pts):
    """Points every STEP along a centre line, each with its unit direction."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5
        if not n:
            continue
        ux, uy = (x1 - x0) / n, (y1 - y0) / n
        k = max(1, int(n // STEP))
        out += [(x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k, ux, uy, n / k) for i in range(k)]
    return out


def along(a, b):
    """How far centre line a runs within TWICE of b and in b's direction
    (either way), in one stretch."""
    segs = [(p, q) for p, q in zip(b, b[1:]) if p != q]
    best = run = 0
    for x, y, ux, uy, step in samples(a):
        hit = False
        for (x0, y0), (x1, y1) in segs:
            vx, vy = x1 - x0, y1 - y0
            n = (vx * vx + vy * vy) ** .5
            t = max(0, min(1, ((x - x0) * vx + (y - y0) * vy) / (n * n)))
            if ((x - x0 - t * vx) ** 2 + (y - y0 - t * vy) ** 2) ** .5 <= TWICE and abs(ux * vx + uy * vy) / n >= .985:
                hit = True
                break
        run = run + step if hit else 0
        best = max(best, run)
    return best


def boxes_apart(a, b):
    return (min(p[0] for p in a) - max(p[0] for p in b) > TWICE or min(p[0] for p in b) - max(p[0] for p in a) > TWICE
            or min(p[1] for p in a) - max(p[1] for p in b) > TWICE or min(p[1] for p in b) - max(p[1] for p in a) > TWICE)


def twice(strokes):
    pl = [p for p in (polyline(d) for _, d in strokes) if len(p) > 1]
    return sum(1 for i in range(len(pl)) for j in range(i + 1, len(pl))
               if not boxes_apart(pl[i], pl[j]) and max(along(pl[i], pl[j]), along(pl[j], pl[i])) >= RUN)


def crosses(a, b):
    """Where polyline a crosses b away from the ends of both, as the share of
    each one's length, or None."""
    def lengths(pl):
        out = [0.0]
        for p, q in zip(pl, pl[1:]):
            out.append(out[-1] + ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** .5)
        return out
    la, lb = lengths(a), lengths(b)
    if not la[-1] or not lb[-1]:
        return None
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = a[i], a[i + 1], b[j], b[j + 1]
            d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
            if abs(d) < 1e-9:
                continue
            t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
            u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
            if 0 <= t <= 1 and 0 <= u <= 1:
                fa = (la[i] + t * (la[i + 1] - la[i])) / la[-1]
                fb = (lb[j] + u * (lb[j + 1] - lb[j])) / lb[-1]
                if .15 < fa < .85 and .03 < fb < .97:
                    return fa, fb
    return None


def dot(strokes):
    pl = [(k, polyline(d)) for k, d in strokes]
    n = 0
    for k, p in pl:
        if k != 'D' or len(p) < 2:
            continue
        for kq, q in pl:
            at = crosses(p, q) if q is not p and len(q) > 1 else None
            # 乂: a 撇 and a 點 of about its length, through each other's middle
            if at and not (kq == 'P' and length(p) >= .45 * length(q) and .2 <= at[0] <= .8 and .2 <= at[1] <= .8):
                n += 1
    return n


def flick(strokes):
    n = 0
    for kind, d in strokes:
        pts = polyline(d)
        if kind == 'P' or len(pts) < 3:
            continue
        # the last point of an upright fall of DROP or more, then the tail
        for k in range(1, len(pts) - 1):
            j = k
            while j > 0 and abs(pts[j - 1][0] - pts[k][0]) <= 12 and pts[j - 1][1] < pts[j][1]:
                j -= 1
            tail = pts[k:]
            if (pts[k][1] - pts[j][1] >= DROP and tail[-1][0] - pts[k][0] <= -40 and tail[-1][1] > pts[k][1]
                    and length(tail) <= TAIL and all(q[0] <= p[0] and q[1] >= p[1] for p, q in zip(tail, tail[1:]))):
                n += 1
                break
    return n


def same(h, hanzi):
    """Pairs of characters with one drawing, among Taiwan's forms and among
    the mainland's (a ZHS form where there is one, the default otherwise)."""
    out = set()
    tw = {k: v for k, v in h.C.items() if is_han(k)}
    cn = {**tw, **{k: v for k, v in h.ZHS.items() if is_han(k)}}
    for forms in (tw, cn):
        by = {}
        for ch, v in forms.items():
            by.setdefault(repr(sorted(hanzi.flatten(v))), []).append(ch)
        for group in by.values():
            for ch in group[1:]:
                out.add(''.join(sorted((group[0], ch))))
    return out


def findings(h):
    """{(check, name): how many}"""
    import hanzi
    out = {('same', pair): 1 for pair in same(h, hanzi)}
    for name, strokes in parts(h):
        for check, fn in (('twice', twice), ('dot', dot), ('flick', flick)):
            n = fn(strokes)
            if n:
                out[check, name] = n
    return out


def baseline():
    out = {}
    if BASE.exists():
        for line in BASE.read_text(encoding='utf-8').splitlines():
            if line and not line.startswith('#'):
                check, name, n = line.split('\t')
                out[check, name] = int(n)
    return out


def listing(items):
    """items: {(check, name): text after the name}"""
    for check in CHECKS:
        names = sorted(n + t for (c, n), t in items.items() if c == check)
        if names:
            print(f'  {check} ({len(names)}): ' + ' '.join(names))


def compare(found, base):
    new = {k: (f'×{n}' if n > 1 else '') + (f'(was {base[k]})' if k in base else '') for k, n in found.items() if n > base.get(k, 0)}
    cleared = {k: (f'({n} to {found[k]})' if k in found else '') for k, n in base.items() if found.get(k, 0) < n}
    return new, cleared


def selftest():
    h = _repo.load()
    S, bad = h.S, 0
    taken = next(k for k in h.ZHS if is_han(k))
    seeds = [
        ('same', '㐀㐁', lambda: h.C.update({'㐀': S('E M100 500 L900 500; E M500 100 L500 900'), '㐁': S('E M500 100 L500 900; E M100 500 L900 500')})),
        # the same only as the mainland draws them
        ('same', ''.join(sorted(('㐂', taken))), lambda: (h.C.update({'㐂': S('E M100 200 L900 200')}), h.ZHS.update({'㐂': h.ZHS[taken]}))),
        ('twice', "K['seed-bar']", lambda: h.K.update({'seed-bar': S('E M160 120 L780 120 L780 470; E M160 470 L780 470; E M160 470 L780 470 L780 880')})),
        ('twice', "K['seed-wall']", lambda: h.K.update({'seed-wall': S('E M200 100 L200 800; P M208 300 L208 700 C200 800 150 880 80 940')})),
        ('twice', "K['seed-slant']", lambda: h.K.update({'seed-slant': S('E M70 300 L930 285; E M70 300 L930 285')})),
        ('twice', "K['seed-pieces']", lambda: h.K.update({'seed-pieces': S('E M200 200 L800 200; E M200 200 ' + ' '.join(f'L{x} 200' for x in range(250, 801, 50)))})),
        ('twice', "K['seed-curve']", lambda: h.K.update({'seed-curve': S('P M480 340 C400 560 260 720 70 840; P M480 340 C400 560 260 720 70 840')})),
        ('twice', "C['㐃']", lambda: h.C.update({'㐃': h.box((S('E M100 500 L900 500; E M100 500 L900 500'), h.FULL), (S('E M500 100 L500 900'), h.FULL))})),
        ('dot', "K['seed-dot']", lambda: h.K.update({'seed-dot': S('E M100 500 L900 500; D M450 400 C480 460 500 540 520 620')})),
        ('dot', "K['seed-dot-end']", lambda: h.K.update({'seed-dot-end': S('E M100 500 L900 500; D M140 420 C150 480 160 540 170 600')})),
        ('dot', "K['seed-刄']", lambda: h.K.update({'seed-刄': S('G M180 200 L820 200 L760 900; P M600 200 L200 800; D M300 400 L500 600')})),
        ('flick', "K['seed-flick']", lambda: h.K.update({'seed-flick': S('E M190 80 L190 780 L60 870')})),
        ('flick', "K['seed-flick-node']", lambda: h.K.update({'seed-flick-node': S('E M190 80 L190 760 L190 780 L60 870')})),
        ('flick', "K['seed-flick-curve']", lambda: h.K.update({'seed-flick-curve': S('E M190 80 L190 780 C150 810 100 840 60 870')})),
    ]
    clean = {
        'seed-ok-口': S('E M200 240 L200 760; E M200 240 L800 240 L800 760; E M200 750 L800 750'),
        'seed-ok-提': S('E M260 155 L260 780 L400 700'),
        'seed-ok-點': S('E M100 300 L900 300; D M480 60 C520 100 540 140 550 200'),
        'seed-ok-乂': S('P M700 200 L300 800; D M430 330 L830 730'),
        'seed-ok-月': S('P M200 320 L200 700 C190 830 140 900 60 950; G M200 320 L820 320 L820 900 L740 860'),
        'seed-ok-二': S('E M250 300 L750 300; E M100 720 L900 720'),
        'seed-ok-鉤': S('G M560 120 L860 120 L860 800 C860 880 820 890 760 860; G M300 100 L300 900 L220 850'),
    }
    for check, name, seed in seeds:
        seed()
        if (check, name) not in findings(h):
            print(f'  NOT FOUND: the seeded {check} defect {name}')
            bad += 1
    before = findings(h)
    h.K.update(clean)
    extra = {k for k in findings(h) if k not in before}
    if extra:
        print('  FOUND in a clean seed: ' + ' '.join(f'{c}:{n}' for c, n in sorted(extra)))
    # debt in a part must not hide another fault of the same kind beside it
    key = ('twice', "K['seed-bar']")
    was = before.get(key, 0)
    h.K['seed-bar'] += S('E M100 955 L880 955; E M100 955 L880 955')
    grew = findings(h).get(key, 0) > was > 0
    print(f'  {len(seeds) - bad} of {len(seeds)} seeded defects found; {len(clean)} clean seeds ' + ('FAIL' if extra else 'pass')
          + '; a second fault in one part ' + ('counted' if grew else 'MISSED'))
    return 1 if bad or extra or not grew else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    found, base = findings(_repo.load(a.batch)), baseline()
    new, cleared = compare(found, base)
    if a.accept:
        if a.batch:
            sys.exit('accept after the batch is merged')
        BASE.write_text('# tools/hz_inside.py --accept: findings looked at and left for now. check, the part or the pair, how many.\n'
                        + ''.join(f'{c}\t{n}\t{k}\n' for (c, n), k in sorted(found.items(), key=lambda f: (CHECKS.index(f[0][0]), f[0][1]))),
                        encoding='utf-8')
        if new:
            print(f'  added ({len(new)}):')
            listing(new)
        if cleared:
            print(f'  dropped ({len(cleared)}):')
            listing(cleared)
        print(f'  baseline written: {len(found)} findings')
        return
    if a.debt:
        listing({k: (f'×{n}' if n > 1 else '') for k, n in base.items() if k in found})
        print(f'  {sum(k in found for k in base)} in the baseline')
        return
    if cleared:
        print(f'  cleared since the baseline ({len(cleared)}; --accept drops them):')
        listing(cleared)
    if new:
        print(f'  NEW ({len(new)}): look at each on a sheet, then fix it or --accept')
        listing(new)
        sys.exit(1)
    print(f'  nothing new inside a part ({len(base)} in the baseline)')


if __name__ == '__main__':
    main()
