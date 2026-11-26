#!/usr/bin/env python3
"""Move two parts of a form apart by measuring, not by eye.

    tools/hz_fit.py 嵐                  the parts of 嵐 and the ink between each two (hz_ink's measure)
    tools/hz_fit.py 寶 --pair 0,1+2     parts 1 and 2 together off part 0
    tools/hz_fit.py 嵐 --pair 0,1       try moves that part 0 off part 1; print the smallest that clears them
    tools/hz_fit.py 嵐 --pair 0,1 --write   and write it into hanzi_strokes.py
    tools/hz_fit.py S:巍 --node 1 --pair 0,1   the mainland form; parts inside top-level part 1's own box

hz_ink.py says which parts join under the bold pens; this finds how far to
move them. 1.004 and 1.005 cleared 山 off the part under it in 33 forms this
way (123,674 and 114,221 cells of ink to 190 and 1,368), where guessing a box
by eye had taken rounds per form.

A form is a box of parts, each in its rect. Of the two parts (or groups of
parts) named, the first stands above the second (--axis y) or to its left
(--axis x); the first gives up its far edge and the second its near edge,
each by shrinking (that edge moves) or shifting (the whole rect moves, and
stays on the grid; a part drawn on the full grid, as 宀 is, may shift off it,
as that is how it moves at all). Every move in --steps is drawn and measured as hz_ink.py measures:
the ink between the two parts in each bold pen, and every other pair.

A move clears the two when the ink between them, summed over the pens, is
--limit or less, no other pair joins in a pen it was clear in, and no other
pair gains a quarter (and hz_ink's RISE) in a pen. Of the moves that clear
it, the smallest (the two steps summed) wins; of those, the one that splits
it between the two parts, then the one that shrinks less. The winner must
then pass two more checks, else the next one is tried:

  - openings (hz_holes.py's measure): no part may lose an opening that part
    of the form had, the trap of 1.003 (回, 目 filled in) and 1.005 (巍's 女);
  - edges: no ink at the canvas edge in any of the six fonts (edges.py).

Changing a part in memory doesn't reach forms that were built from it when
hanzi_strokes was imported (凱 holds the 豈 it was made with), so those are
listed: measure them with hz_ink.py --chars after --write.

When the room has to come from a third part (宀 over 王 and 缶 over 貝 in 寶),
move one pair with --allow naming the next, then move the next.

--write finds the statement that defines the box (the form's own, or the
K/C/ZHS name the box is bound to) and changes the two rects in it; it
refuses when either rect's text isn't there exactly once.
"""
import argparse
import itertools
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import _repo

SRC = _repo.ROOT / 'hanzi_strokes.py'
PENS = ('yinni', 'huasha', 'louhen')


def form_of(key):
    """('C' or 'S', char) from 嵐 or S:巍."""
    if key.startswith('S:'):
        return 'S', key[2:]
    return 'C', key.removeprefix('C:')


def table(H, f):
    return H.ZHS if f == 'S' else H.C


def node_at(item, path):
    """(the box at path, the stroke number its first part starts at)."""
    import hanzi
    lo = 0
    for i in path:
        if not (isinstance(item, tuple) and item[0] == 'box'):
            raise SystemExit(f'not a box at {path}')
        for p, _ in item[1][:i]:
            lo += len(hanzi.flatten(p))
        item = item[1][i][0]
    if not (isinstance(item, tuple) and item[0] == 'box'):
        raise SystemExit(f'not a box at {path}')
    return item, lo


def ranges(node, lo):
    import hanzi
    out = []
    for p, _ in node[1]:
        n = len(hanzi.flatten(p))
        out.append((lo, lo + n))
        lo += n
    return out


def rebuilt(item, path, node):
    """item with the box at path replaced by node (new tuples on the way down; nothing shared is changed)."""
    if not path:
        return node
    parts = list(item[1])
    p, r = parts[path[0]]
    parts[path[0]] = (rebuilt(p, path[1:], node), r)
    return ('box', parts)


def moved(node, I, J, axis, d, e, di, dj):
    """The box with the parts in I giving up d at their far edge and those in J e at their near edge ('shrink' or 'shift')."""
    parts = list(node[1])
    a, b = (1, 3) if axis == 'y' else (0, 2)
    for ks, n, mode, near, far, sign in ((I, d, di, b, a, -1), (J, e, dj, a, b, 1)):
        for k in ks:
            p, r = parts[k]
            r = list(r)
            r[near] += sign * n
            if mode == 'shift':
                r[far] += sign * n
            parts[k] = (p, tuple(r))
    return ('box', parts)


def measure(job):
    """hz_ink's pairs {((lo, hi), (lo, hi)): ink per pen} for the form with the box at path swapped for node."""
    f, ch, path, node = job
    H = _repo.load()
    import hz_ink
    t = table(H, f)
    old = t[ch]
    if node is not None:
        t[ch] = rebuilt(old, path, node)
    try:
        g = hz_ink.work(('', [(f, ch)]))[f, ch]
    finally:
        t[ch] = old
    return {**g[1], **g[2]}


def openings(f, ch, path, node):
    import hz_holes
    H = _repo.load()
    t = table(H, f)
    old = t[ch]
    if node is not None:
        t[ch] = rebuilt(old, path, node)
    try:
        return hz_holes.measure([(f, ch)]).get(f + ch, {})
    finally:
        t[ch] = old


def cut(f, ch, path, node):
    """The fonts (style-weight) where the form's ink reaches the canvas edge."""
    H = _repo.load()
    import numpy as np
    import build
    t = table(H, f)
    old = t[ch]
    t[ch] = rebuilt(old, path, node)
    bad = []
    try:
        for style in PENS:
            for bold in (False, True):
                st = build.STYLES[style](bold=bold)
                e = np.asarray(st.draw(ch, build.canvas(st, ch), int(f == 'S')))
                if e[:2].any() or e[-2:].any() or e[:, :2].any() or e[:, -2:].any():
                    bad.append(f'{style}-{"bold" if bold else "regular"}')
    finally:
        t[ch] = old
    return bad


def between(pairs, ri, rj):
    v = pairs.get((ri, rj)) or pairs.get((rj, ri))
    return tuple(v) if v else (0, 0, 0)


def rose(base, now, skip):
    """Other pairs that join in a pen they were clear in, or gain a quarter and RISE there."""
    import hz_ink
    out = []
    for pq, v in now.items():
        if pq in skip:
            continue
        w = base.get(pq, (0, 0, 0))
        for pen, a, b in zip(PENS, w, v):
            if (a == 0 and b > 0) or (a and b > a * 1.25 and b - a > hz_ink.RISE):
                out.append(f'{pq} {pen} {a}->{b}')
    return out


def users(H, f, ch, node):
    """Forms other than this one whose drawing holds this box object."""
    seen = set()

    def holds(item):
        if item is node:
            return True
        if isinstance(item, tuple) and item[0] == 'box':
            if id(item) in seen:
                return False
            if any(holds(p) for p, _ in item[1]):
                return True
            seen.add(id(item))
        return False
    out = []
    for g, t in (('C', H.C), ('S', H.ZHS)):
        for c, item in t.items():
            if (g, c) != (f, ch) and (g == 'C' or item is not H.C.get(c)) and holds(item):
                out.append(c + ('(S)' if g == 'S' else ''))
    return out


def statements(src):
    """{start offset: text} of every top-level assignment to K[..], L[..], C[..] or ZHS[..]."""
    starts = [m.start() for m in re.finditer(r"^(?:K|L|C|ZHS)\['[^']+'\]\s*=", src, re.M)]
    ends = [m.start() for m in re.finditer(r'^\S', src, re.M)]
    out = {}
    for s in starts:
        e = next((x for x in ends if x > s), len(src))
        out[s] = src[s:e]
    return out


def rect_re(r):
    return re.compile(r'\(\s*' + r',\s*'.join(str(v) for v in r) + r'\s*\)')


def write(H, f, ch, path, node, new, ks):
    """Change the rects of parts ks in the statement that defines node; the text changed, or why not."""
    src = SRC.read_text(encoding='utf-8')
    names = [f"{n}['{k}']" for n in ('K', 'L', 'C', 'ZHS') for k, v in getattr(H, n).items() if v is node]
    top = f"{'ZHS' if f == 'S' else 'C'}['{ch}']"
    tried = []
    for name in names + [top]:
        for s, text in statements(src).items():
            if not text.startswith(name):
                continue
            ms = [list(rect_re(node[1][k][1]).finditer(text)) for k in ks]
            if any(len(m) != 1 for m in ms):
                tried.append(f'{name}: the rects are not there once each')
                continue
            edits = sorted(((m[0].start(), m[0].end(), new[1][k][1]) for m, k in zip(ms, ks)), reverse=True)
            out = text
            for a, b, r in edits:
                out = out[:a] + '(' + ', '.join(map(str, r)) + ')' + out[b:]
            SRC.write_text(src[:s] + out + src[s + len(text):], encoding='utf-8')
            return out.rstrip()
    return 'not written: ' + ('; '.join(tried) or 'no statement defines this box')


def pen_ink(v):
    return ' '.join(f'{p[0]}{x}' for p, x in zip(PENS, v))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('form', help='a character (Taiwan or shared form), or S:char for the mainland form')
    ap.add_argument('--node', default='', help='the box to work in: indices from the top, e.g. 1 or 1,0 (default the top)')
    ap.add_argument('--pair', help='the parts of that box to move apart, the upper (or left) first: 0,1, or 0,1+2 to move 1 and 2 together off 0')
    ap.add_argument('--axis', choices=('y', 'x'), default='y', help='y: the first stands above the second; x: to its left')
    ap.add_argument('--allow', help='parts whose ink may rise, to be moved apart next: 1+2,3')
    ap.add_argument('--steps', default='0,20,40,60', help='the moves to try at each edge (grid units)')
    ap.add_argument('--limit', type=int, default=60, help='ink left between the two, summed over the pens, that counts as clear')
    ap.add_argument('--no-shift', action='store_true', help='only shrink, never move a whole rect')
    ap.add_argument('--write', action='store_true', help='write the winning move into hanzi_strokes.py')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    a = ap.parse_args()

    f, ch = form_of(a.form)
    H = _repo.load()
    import hz_holes
    if ch not in table(H, f):
        raise SystemExit(f'{a.form}: not drawn')
    if f == 'S' and H.ZHS[ch] is H.C.get(ch):
        raise SystemExit(f'{a.form}: the mainland shares the Taiwan form; name {ch}')
    path = [int(x) for x in a.node.split(',') if x != '']
    item = table(H, f)[ch]
    node, lo = node_at(item, path)
    rs = ranges(node, lo)
    base = measure((f, ch, path, None))

    if not a.pair:
        print(f'{a.form}: parts of the box at [{a.node}] (strokes, rect)')
        for k, ((x, y), (_, r)) in enumerate(zip(rs, node[1])):
            print(f'  {k}: strokes {x + 1}-{y}  {r}')
        print('ink between parts, per bold pen:')
        rows = sorted(((sum(between(base, rs[p], rs[q])), p, q) for p, q in itertools.combinations(range(len(rs)), 2)), reverse=True)
        for tot, p, q in rows:
            print(f'  {p},{q}: {tot:6}  ({pen_ink(between(base, rs[p], rs[q]))})')
        inner = sum(sum(v) for pq, v in base.items()) - sum(r[0] for r in rows)
        print(f'  other pairs in the form: {inner}')
        return

    I, J = ([int(x) for x in side.split('+')] for side in a.pair.split(','))
    axis = a.axis
    lo_edge, hi_edge = (1, 3) if axis == 'y' else (0, 2)
    pairs = [(rs[p], rs[q]) for p in I for q in J]
    skip = set(pairs) | {pq[::-1] for pq in pairs}
    if a.allow:
        P, Q = ([int(x) for x in side.split('+')] for side in a.allow.split(','))
        skip |= {(rs[p], rs[q]) for p in P for q in Q} | {(rs[q], rs[p]) for p in P for q in Q}

    def gap(m):
        return tuple(map(sum, zip(*(between(m, *pq) for pq in pairs))))
    was = gap(base)

    def gap2(m):
        P, Q = ([int(x) for x in side.split('+')] for side in a.allow.split(','))
        return tuple(map(sum, zip(*(between(m, rs[p], rs[q]) for p in P for q in Q))))
    name = lambda ks: '+'.join(f'{k} {node[1][k][1]}' for k in ks)
    print(f'{a.form}: {name(I)} then {name(J)} along {axis}; ink between: {sum(was)} ({pen_ink(was)})')
    if sum(was) <= a.limit:
        print('already clear')
        return
    steps = [int(x) for x in a.steps.split(',')]
    modes = ('shrink',) if a.no_shift else ('shrink', 'shift')
    full = lambda r: (r[lo_edge], r[hi_edge]) == (0, 1000)
    tries = []
    for d, e in itertools.product(steps, steps):
        if d == e == 0:
            continue
        for di in (modes if d else ('shrink',)):
            for dj in (modes if e else ('shrink',)):
                # a shift stays on the grid, but for a part drawn on the full grid (宀), which moves no other way
                if di == 'shift' and any(node[1][k][1][lo_edge] - d < 0 and full(node[1][k][1]) is False for k in I):
                    continue
                if dj == 'shift' and any(node[1][k][1][hi_edge] + e > 1000 and full(node[1][k][1]) is False for k in J):
                    continue
                if any(node[1][k][1][hi_edge] - d <= node[1][k][1][lo_edge] + 100 for k in I) or \
                        any(node[1][k][1][lo_edge] + e >= node[1][k][1][hi_edge] - 100 for k in J):
                    continue
                tries.append((d + e, max(d, e), (di == 'shrink') + (dj == 'shrink'), d, e, di, dj))
    tries.sort()
    nodes = [moved(node, I, J, axis, d, e, di, dj) for *_, d, e, di, dj in tries]
    with ProcessPoolExecutor(a.jobs) as ex:
        got = list(ex.map(measure, [(f, ch, path, n) for n in nodes]))
    holes0 = None
    win = None
    for t, n, m in zip(tries, nodes, got):
        *_, d, e, di, dj = t
        left = gap(m)
        tag = f'{d:3} {di:6} / {e:3} {dj:6}: between {sum(left):6} ({pen_ink(left)})'
        if sum(left) > a.limit or rose(base, m, skip):
            continue
        if holes0 is None:
            holes0 = openings(f, ch, path, None)
        holes = openings(f, ch, path, n)
        lost = [(k, hz_holes.worse(holes0[k], holes[k])) for k in holes0 if k in holes]
        lost = [(k, w) for k, w in lost if w]
        if lost:
            print(f'  {tag}  openings worse: ' + '; '.join(f'{k}: {w}' for k, w in lost))
            continue
        c = cut(f, ch, path, n)
        if c:
            print(f'  {tag}  cut in {", ".join(c)}')
            continue
        print(f'  {tag}  clear; openings and edges pass')
        if a.allow:
            print(f'  --allow {a.allow}: now {sum(gap2(m))} ({pen_ink(gap2(m))}), was {sum(gap2(base))}; move them next')
        win = n
        break
    if win is None:
        print(f'no move in --steps {a.steps} clears it within --limit {a.limit}; the nearest:')
        for t, m in sorted(zip(tries, got), key=lambda tg: (sum(gap(tg[1])), tg[0]))[:5]:
            *_, d, e, di, dj = t
            bad = rose(base, m, skip)
            print(f'  {d:3} {di:6} / {e:3} {dj:6}: between {sum(gap(m)):6} ({pen_ink(gap(m))})'
                  + (f'  rises: {"; ".join(bad[:3])}' if bad else ''))
        sys.exit(1)
    print('new rects: ' + ', '.join(f'part {k} {win[1][k][1]}' for k in I + J))
    also = users(H, f, ch, node)
    if also:
        print('built from this box at import, measure after --write with hz_ink.py --chars:', ''.join(also))
    if a.write:
        print(write(H, f, ch, path, node, win, I + J))


if __name__ == '__main__':
    main()
