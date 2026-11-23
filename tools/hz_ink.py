#!/usr/bin/env python3
"""The gate on ink: parts that stand apart on paper and join under the bold pens.

    tools/hz_ink.py                  exit 1 when a form joins more than the baseline says
    tools/hz_ink.py --chars 辯蔑      only these (what a change touched); fails when none is drawn
    tools/hz_ink.py --accept         write the baseline (tools/hz_ink.tsv); with --chars, only their rows
    tools/hz_ink.py --debt 60        the forms that join most (from the baseline; measured with --chars or --batch)
    tools/hz_ink.py --where 辯蔑      which parts join, in which pen
    tools/hz_ink.py --selftest       seeded joins and clear pairs, and the verdicts; each must be told

hz_gate.py measures centre lines. Two parts 40 apart pass it, and the bold
pens, 30 and more wide, still draw them as one mark: 0.995 and 0.996 each
had a review panel find 堯's three 土, 火火 on 冖, the middle of 辯 on its
right 辛 and 艹 on 罒 this way, after the gate had passed them.

For every node of a drawing (box, lr, tb), each pair of sibling parts whose
centre lines are APART or more from each other is meant to stand apart. In
each of the three bold pens the two are drawn together, with nothing else,
in the whole character's place, pen width and hand, and each alone. The
pair is joined in that pen when ink of the one reaches ink of the other
through the drawing of both: the pens are not sums of their strokes (印泥
blurs the whole drawing before it cuts it, so two marks 120 apart can close
up though neither alone reaches the other), which is why the two are drawn
together. How much is the ink of that drawing within REACH of both parts.

Kept per form and pen: pairs joined, and that ink. Fails, against the
baseline: a form new to the list, more pairs joined in a pen, or a quarter
more ink in a pen (and RISE more). A pair that closes to under APART on
paper leaves this tool's count and is hz_gate's to fail ("tighter"), so run
both. Parts drawn to meet are not measured here.

It draws every form many times: about half an hour on all cores.
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import _repo

BASE = Path(__file__).with_name('hz_ink.tsv')
APART = 25      # centre lines this far apart are two marks on paper
REACH = 3       # cells; ink within this of both parts lies between them
RISE = 15       # cells of ink a pen must gain before a quarter more fails
STYLES = ('yinni', 'huasha', 'louhen')
SEED = '\ufffd'


def siblings(item, lo=0):
    """(strokes, [[(lo, hi) of each sibling part] for every node])."""
    if isinstance(item, list):
        return len(item), []
    kids = [item[1], item[2]] if item[0] in ('lr', 'tb') else [p for p, _ in item[1]]
    here, below, at = [], [], lo
    for k in kids:
        n, sub = siblings(k, at)
        here.append((at, at + n))
        below += sub
        at += n
    return at - lo, [here] + below


def apart(item, hanzi, gate):
    """The sibling pairs ((lo, hi), (lo, hi)) that stand APART or more on paper."""
    strokes = hanzi.flatten(item)
    out = []
    for node in siblings(item)[1]:
        shapes = [gate.shape(strokes[a:b]) for a, b in node]
        for i in range(len(node)):
            for j in range(i + 1, len(node)):
                if shapes[i] and shapes[j] and gate.pair(shapes[i], shapes[j])[0] >= APART:
                    out.append((node[i], node[j]))
    return out


def grow(m, np, n=1):
    """A mask grown by n cells, up, down and sideways."""
    for _ in range(n):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def reaches(a, b, ink, np):
    """Whether ink of a reaches ink of b through `ink` (the two drawn together)."""
    if (a & b).any():
        return True
    seen = a & ink
    target = b & ink
    n = int(seen.sum())
    while n:
        seen = grow(seen, np, 6) & ink
        if (seen & target).any():
            return True
        m = int(seen.sum())
        if m == n:
            return False
        n = m
    return False


def shared(ch, form, pairs, hanzi, build, np):
    """[(pair, pen, cells)] for the pairs joined in a pen. A cell is two grid
    units square."""
    from unittest.mock import patch
    table = (hanzi.C, hanzi.ZHS)[form]
    whole = hanzi.flatten(table[ch])
    real = hanzi.placed
    cell = max(1, round(2 * build.S))
    out = []
    for key in STYLES:
        st = build.STYLES[key](bold=True)
        scale = hanzi.density_scale(ch, whole, True)
        masks = {}

        def mask(*rngs):
            if rngs not in masks:
                def some(*a, **kw):
                    strokes, warp, r = real(*a, **kw)
                    return [s for lo, hi in rngs for s in strokes[lo:hi]], warp, r
                with patch.object(hanzi, 'placed', some), patch.object(hanzi, 'density_scale', return_value=scale):
                    masks[rngs] = np.asarray(st.draw(ch, build.canvas(st, ch), form).reduce(cell)) > 64
            return masks[rngs]
        for p, q in pairs:
            a, b, both = mask(p), mask(q), mask(p, q)
            if reaches(a, b, both, np):
                out.append(((p, q), key, max(1, int(np.count_nonzero(both & grow(a, np, REACH) & grow(b, np, REACH))))))
    return out


def work(job):
    batch, keys = job
    H = _repo.load(batch)
    import numpy as np
    import build
    import hanzi
    import hz_gate
    out = {}
    for f, ch in keys:
        form = int(f == 'S')
        pairs = apart((H.C, H.ZHS)[form][ch], hanzi, hz_gate)
        if pairs:
            hits = shared(ch, form, pairs, hanzi, build, np)
            out[f, ch] = (tuple(sum(1 for _, k, _ in hits if k == key) for key in STYLES)
                          + tuple(sum(n for _, k, n in hits if k == key) for key in STYLES), hits)
    return out


def survey(batch='', only=None, jobs=None):
    """{(form, ch): (joined, pixels, hits)} for every form with a pair meant apart."""
    import os
    H = _repo.load(batch)
    import hanzi
    import hz_gate
    keys = [('C', ch) for ch in H.C if hz_gate.is_han(ch) and (only is None or ch in only)]
    keys += [('S', ch) for ch, item in H.ZHS.items() if hz_gate.is_han(ch) and (only is None or ch in only)
             and (ch not in H.C or hanzi.flatten(item) != hanzi.flatten(H.C[ch]))]
    jobs = jobs or max(1, (os.cpu_count() or 2) - 2)
    if len(keys) < 40:
        return work((batch, keys))
    out = {}
    with ProcessPoolExecutor(jobs) as ex:
        for part in ex.map(work, [(batch, keys[i::jobs * 8]) for i in range(jobs * 8)]):
            out.update(part)
    return out


def read_base():
    base = {}
    if BASE.exists():
        for line in BASE.read_text(encoding='utf-8').splitlines():
            if line and not line.startswith('#'):
                f, ch, *n = line.split('\t')
                base[f, ch] = tuple(int(v) for v in n)
    return base


def judge(now, was):
    """Why this form fails: now and was are (joined per pen x3, ink per pen x3); was None when it is not in the baseline."""
    if not any(now[:3]):
        return None
    if was is None:
        return 'new: joined in ' + ', '.join(f'{k} {j}' for k, j in zip(STYLES, now[:3]) if j)
    why = []
    for i, key in enumerate(STYLES):
        if now[i] > was[i]:
            why.append(f'{key}: pairs joined {was[i]} -> {now[i]}')
        elif now[3 + i] > was[3 + i] * 1.25 and now[3 + i] - was[3 + i] > RISE:
            why.append(f'{key}: ink between parts {was[3 + i]} -> {now[3 + i]}')
    return '; '.join(why) or None


def selftest():
    H = _repo.load()
    import hanzi
    full = (0, 0, 1000, 1000)
    bad = 0

    def told(label, item, want, form='C'):
        nonlocal bad
        (H.ZHS if form == 'S' else H.C)[SEED] = item
        if form == 'S':
            H.C[SEED] = [('E', 'M100 500 L900 500')]
        got = work(('', [(form, SEED)])).get((form, SEED), ((0,) * 6, []))[0][:3]
        H.C.pop(SEED, None)
        H.ZHS.pop(SEED, None)
        ok = all(bool(g) == want for g in got)
        print(f'  {label}: ' + ' '.join(f'{k} {"joined" if g else "apart"}' for k, g in zip(STYLES, got)) + ('' if ok else '  <- WRONG'))
        bad += not ok

    def up(x):
        return [('E', f'M{x} 150 L{x} 850')]
    told('two uprights 40 apart, a box', ('box', [(up(300), full), (up(340), full)]), True)
    told('two uprights 300 apart, a box', ('box', [(up(300), full), (up(600), full)]), False)
    told('two uprights 40 apart, lr', ('lr', up(960), up(60), 0.5), True)
    told('two bars 40 apart, tb', ('tb', [('E', 'M150 960 L850 960')], [('E', 'M150 40 L850 40')], 0.5), True)
    told('two uprights 40 apart, nested', ('box', [(('box', [(up(300), full), (up(340), full)]), full), (up(800), full)]), True)
    told('two uprights 40 apart, a mainland form', ('box', [(up(300), full), (up(340), full)]), True, 'S')
    assert SEED not in hanzi.C and SEED not in hanzi.ZHS
    was = (1, 0, 2, 40, 0, 90)
    for label, now, want in (('the same', was, False), ('nothing joined', (0,) * 6, False),
                             ('one more pair in a pen', (1, 1, 2, 40, 5, 90), True),
                             ('one pen better, another worse', (0, 0, 3, 0, 0, 90), True),
                             ('a quarter more ink in a pen', (1, 0, 2, 40, 0, 130), True),
                             ('a little more ink', (1, 0, 2, 44, 0, 95), False),
                             ('less ink', (1, 0, 1, 20, 0, 30), False)):
        got = bool(judge(now, was))
        print(f'  verdict, {label}: {"fails" if got else "passes"}' + ('' if got == want else '  <- WRONG'))
        bad += got != want
    for label, now, want in (('a new form that joins', (0, 1, 0, 0, 8, 0), True), ('a new form that is clear', (0,) * 6, False)):
        got = bool(judge(now, None))
        print(f'  verdict, {label}: {"fails" if got else "passes"}' + ('' if got == want else '  <- WRONG'))
        bad += got != want
    return bad


def name(ch, f):
    return ch + ('(S)' if f == 'S' else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--chars', default=None)
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', type=int, default=0)
    ap.add_argument('--where', default='')
    ap.add_argument('--jobs', type=int, default=0)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if a.where:
        H = _repo.load(a.batch)
        import hanzi
        got = survey(a.batch, set(a.where))
        if not got:
            sys.exit('none of these is drawn with parts meant apart')
        for (f, ch), (m, hits) in sorted(got.items(), key=lambda kv: a.where.index(kv[0][1])):
            strokes = hanzi.flatten((H.C, H.ZHS)[f == 'S'][ch])
            print(f'{name(ch, f)}: {sum(m[:3])} joined' if any(m[:3]) else f'{name(ch, f)}: nothing joined')
            for ((a0, a1), (b0, b1)), key, n in hits:
                print(f'   {key} bold: strokes {a0 + 1}-{a1} and {b0 + 1}-{b1} of {len(strokes)}, {n} cells of ink between')
        return
    measured = a.chars is not None or bool(a.batch) or a.accept or not a.debt
    now = {k: v[0] for k, v in survey(a.batch, set(a.chars) if a.chars is not None else None, a.jobs).items()} if measured else read_base()
    if a.chars is not None and not now:
        sys.exit('--chars: none of these is drawn with parts meant apart (an empty or mangled list?)')
    if a.accept:
        if a.batch:
            sys.exit('--accept is for what is merged: run it without --batch')
        kept = {} if a.chars is None else {k: v for k, v in read_base().items() if k[1] not in a.chars}
        rows = sorted([(f, ch) + m for (f, ch), m in now.items() if any(m[:3])] + [(f, ch) + m for (f, ch), m in kept.items()])
        BASE.write_text('# tools/hz_ink.py --accept. form (C Taiwan/shared, S mainland), character, pairs joined in the bold '
                        + ', '.join(STYLES) + ' pens, cells of ink between the joined parts in each\n'
                        + ''.join('\t'.join(map(str, r)) + '\n' for r in rows), encoding='utf-8')
        print(f'baseline written: {len(rows)} forms join' + (f', of {len(now)} with parts meant apart' if a.chars is None else f'; {len(now)} measured again'))
        return
    if a.debt:
        worst = sorted(((sum(m[3:]), sum(m[:3]), f, ch) for (f, ch), m in now.items() if any(m[:3])), reverse=True)
        print(f'{len(worst)} forms join in a bold pen' + ('' if measured else ' (the baseline)') + f'; the {min(a.debt, len(worst))} with most ink between parts:')
        print('  ' + '  '.join(f'{name(ch, f)} {j}/{p}' for p, j, f, ch in worst[:a.debt]))
        return
    base = read_base()
    fails = [(name(ch, f), why) for (f, ch), m in sorted(now.items()) for why in [judge(m, base.get((f, ch)))] if why]
    better = [name(ch, f) for (f, ch), m in sorted(now.items()) if (f, ch) in base and sum(m[:3]) < sum(base[f, ch][:3])]
    joined = sum(1 for m in now.values() if any(m[:3]))
    print(f'drawn {len(now)} forms with parts meant apart in the three bold pens: {joined} join'
          + (f' ({len(base)} in the baseline)' if a.chars is None else ''))
    if better:
        print(f'  join less than the baseline ({len(better)}): ' + ''.join(better[:80]))
    for who, why in fails:
        print(f'FAIL {who}: {why}')
    print(f'{len(fails)} forms join more' if fails else 'no form joins more')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
