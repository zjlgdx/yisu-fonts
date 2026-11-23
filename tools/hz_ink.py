#!/usr/bin/env python3
"""The gate on ink: parts that stand apart on paper and join under the bold pens.

    tools/hz_ink.py                  exit 1 when a form joins more than the baseline says
    tools/hz_ink.py --chars 辯蔑      only these (what a change touched)
    tools/hz_ink.py --accept         write the baseline (tools/hz_ink.tsv); with --chars, only their rows
    tools/hz_ink.py --debt 60        the forms that join most today
    tools/hz_ink.py --where 辯蔑      which parts join, in which pen
    tools/hz_ink.py --selftest       seed a join and a clear pair; each must be told

hz_gate.py measures centre lines. Two parts 40 apart pass it, and the bold
pens, 30 and more wide, still draw them as one mark: 0.995 and 0.996 each
had a review panel find 堯's three 土, 火火 on 冖, the middle of 辯 on its
right 辛 and 艹 on 罒 this way, after the gate had passed them.

For every node of a drawing (box, lr, tb), each pair of sibling parts whose
centre lines are APART or more from each other is meant to stand apart. Each
of the two is drawn alone, in the whole character's place, with its pen
width and its hand, in the three bold pens; the pixels both ink are counted.
A pair that shares MIN or more in a pen is joined there.

Kept per form: joined (pairs times pens) and the pixels shared. Fails,
against the baseline: a form new to the list, more joined than before, or
half as many pixels again (and 500 more). Parts that are drawn to meet
(under APART on paper) are hz_gate's to judge, not this tool's.

It draws every form several times: about ten minutes on all cores.
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import _repo

BASE = Path(__file__).with_name('hz_ink.tsv')
APART = 25      # centre lines this far apart are two marks on paper
MIN = 50        # shared pixels under this are a kiss of the pen's jitter
STYLES = ('yinni', 'huasha', 'louhen')
SEED = '�'


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


def shared(ch, form, pairs, hanzi, build, np):
    """[(pair, pen, pixels)] for the pairs that share MIN or more."""
    from unittest.mock import patch
    table = (hanzi.C, hanzi.ZHS)[form]
    whole = hanzi.flatten(table[ch])
    real = hanzi.placed
    out = []
    for key in STYLES:
        st = build.STYLES[key](bold=True)
        scale = hanzi.density_scale(ch, whole, True)
        masks = {}

        def mask(rng):
            if rng not in masks:
                def some(*a, **kw):
                    strokes, warp, r = real(*a, **kw)
                    return strokes[rng[0]:rng[1]], warp, r
                with patch.object(hanzi, 'placed', some), patch.object(hanzi, 'density_scale', return_value=scale):
                    masks[rng] = np.asarray(st.draw(ch, build.canvas(st, ch), form)) > 127
            return masks[rng]
        for p, q in pairs:
            n = int(np.count_nonzero(mask(p) & mask(q)))
            if n >= MIN:
                out.append(((p, q), key, n))
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
            out[f, ch] = (len(hits), sum(n for _, _, n in hits), hits)
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
                f, ch, joined, px = line.split('\t')
                base[f, ch] = (int(joined), int(px))
    return base


def judge(now, was):
    joined, px = now[:2]
    if not joined:
        return None
    if was is None:
        return f'new: {joined} joined, {px} pixels shared'
    if joined > was[0]:
        return f'joined {was[0]} -> {joined}'
    if px > was[1] * 1.5 and px - was[1] > 500:
        return f'pixels shared {was[1]} -> {px}'
    return None


def selftest():
    H = _repo.load()
    import hanzi
    full = (0, 0, 1000, 1000)
    bad = 0
    for gap, want in ((40, True), (300, False)):
        H.C[SEED] = ('box', [([('E', 'M300 150 L300 850')], full), ([('E', f'M{300 + gap} 150 L{300 + gap} 850')], full)])
        got = bool(work(('', [('C', SEED)])).get(('C', SEED), (0,))[0])
        print(f'  two uprights {gap} apart: {"joined" if got else "apart"}' + ('' if got == want else '  <- WRONG'))
        bad += got != want
    del H.C[SEED]
    assert SEED not in hanzi.C
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
        for (f, ch), (joined, px, hits) in sorted(survey(a.batch, set(a.where)).items(), key=lambda kv: a.where.index(kv[0][1])):
            strokes = hanzi.flatten((H.C, H.ZHS)[f == 'S'][ch])
            print(f'{name(ch, f)}: {joined} joined, {px} pixels' if joined else f'{name(ch, f)}: nothing joined')
            for ((a0, a1), (b0, b1)), key, n in hits:
                print(f'   {key} bold: strokes {a0 + 1}-{a1} and {b0 + 1}-{b1} of {len(strokes)} share {n}')
        return
    now = survey(a.batch, set(a.chars) if a.chars is not None else None, a.jobs)
    if a.accept:
        if a.batch:
            sys.exit('--accept is for what is merged: run it without --batch')
        kept = {} if a.chars is None else {k: v for k, v in read_base().items() if k[1] not in a.chars}
        rows = sorted([(f, ch, m[0], m[1]) for (f, ch), m in now.items() if m[0]] + [(f, ch, j, p) for (f, ch), (j, p) in kept.items()])
        BASE.write_text('# tools/hz_ink.py --accept. form (C Taiwan/shared, S mainland), character, joined (pairs x bold pens), pixels shared\n'
                        + ''.join(f'{f}\t{ch}\t{j}\t{p}\n' for f, ch, j, p in rows), encoding='utf-8')
        print(f'baseline written: {len(rows)} forms join' + (f', of {len(now)} with parts meant apart' if a.chars is None else f'; {len(now)} measured again'))
        return
    if a.debt:
        worst = sorted(((m[1], m[0], f, ch) for (f, ch), m in now.items() if m[0]), reverse=True)
        print(f'{len(worst)} forms join in a bold pen; the {min(a.debt, len(worst))} that share most:')
        print('  ' + '  '.join(f'{name(ch, f)} {j}/{p}' for p, j, f, ch in worst[:a.debt]))
        return
    base = read_base()
    fails = [(name(ch, f), why) for (f, ch), m in sorted(now.items()) for why in [judge(m, base.get((f, ch)))] if why]
    better = [name(ch, f) for (f, ch), m in sorted(now.items()) if (f, ch) in base and m[0] < base[f, ch][0]]
    joined = sum(1 for m in now.values() if m[0])
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
