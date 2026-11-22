#!/usr/bin/env python3
"""Every form a change touched, before and after, large enough to judge.

    tools/hz_diff.py REF OUT_PREFIX [--per 6] [--size 220] [--list-only]

Editing one part redraws every character that holds it, and the ones nobody
meant to change are where the damage is: 0.980 lifted 又 for 侵 and pushed it
onto 冖 in 寢. This draws all of them, not the ones the change was for.

It checks REF out beside this tree, compares every drawing in both (Taiwan's
and the mainland's), and writes OUT_PREFIX-NN.jpg: twelve changed characters a
sheet, REF's drawing in the upper half and this tree's in the lower, each from
its own tree's code. A mainland form that is its own drawing and changed gets
the same on OUT_PREFIX-s-NN.jpg. OUT_PREFIX.txt lists the characters, and any
drawn at REF that are gone now. A sheet of twelve
keeps a character about 300 pixels wide when the sheet is read at 2,000 across;
at forty-eight a sheet, two strokes run together look the same as two apart.

The reviewer is someone who did not make the change (a fresh agent with the
sheets and the checklist in the hanzi-round skill, no account of what was
intended).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DUMP = ('import sys, json, hashlib; sys.path.insert(0, "."); import hanzi_strokes as h; from hanzi import flatten; '
        'd = lambda v: hashlib.md5(repr(flatten(v)).encode()).hexdigest(); '
        'print(json.dumps({"C": {k: d(v) for k, v in h.C.items()}, "S": {k: d(v) for k, v in h.ZHS.items()}}))')


def forms(tree):
    return json.loads(subprocess.run([sys.executable, '-c', DUMP], cwd=tree, check=True, capture_output=True, text=True).stdout)


def sheet(tree, out, chars, per, size, mainland):
    subprocess.run([sys.executable, 'tools/hz_sheet.py', str(out), chars, '--per', str(per), '--size', str(size)]
                   + (['--mainland'] if mainland else []), cwd=tree, check=True, capture_output=True)
    return Image.open(out).convert('RGB')


def sheets(base, tmp, prefix, old, new, per, size, mainland):
    """Before above the band and after below for `old`; `new` as it is now."""
    step, n = per * 2, 0
    for i in range(0, len(old), step):
        chars = ''.join(old[i:i + step])
        top = sheet(base, tmp / 'a.jpg', chars, per, size, mainland)
        bottom = sheet(ROOT, tmp / 'b.jpg', chars, per, size, mainland)
        img = Image.new('RGB', (max(top.width, bottom.width), top.height + bottom.height + 28), (40, 58, 90))
        img.paste(top, (0, 0))
        img.paste(bottom, (0, top.height + 28))
        n += 1
        img.save(f'{prefix}-{n:02d}.jpg', quality=88)
    for i in range(0, len(new), step * 2):
        n += 1
        sheet(ROOT, Path(f'{prefix}-{n:02d}.jpg'), ''.join(new[i:i + step * 2]), per, size, mainland)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('out')
    ap.add_argument('--per', type=int, default=6)
    ap.add_argument('--size', type=int, default=220)
    ap.add_argument('--list-only', action='store_true')
    a = ap.parse_args()
    out = str(Path(a.out).resolve())
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / 'base'
        try:
            subprocess.run(['git', 'worktree', 'add', '-q', '--detach', str(base), a.ref], cwd=ROOT, check=True)
            was, now = forms(base), forms(ROOT)
            default = [k for k in now['C'] if len(k) == 1 and was['C'].get(k) != now['C'][k]]
            # a mainland form is drawn when it changed and is, or was, its own drawing
            mainland = [k for k in now['S'] if len(k) == 1 and was['S'].get(k) != now['S'][k]
                        and (k not in default or now['S'][k] != now['C'].get(k) or was['S'].get(k) != was['C'].get(k))]
            gone = [k for k in was['C'] if len(k) == 1 and k not in now['C']] + [f'{k}(S)' for k in was['S'] if len(k) == 1 and k not in now['S']]
            Path(out + '.txt').write_text(''.join(default) + '\n' + ''.join(f'{k}(S)' for k in mainland) + '\n'
                                          + ('gone: ' + ''.join(gone) + '\n' if gone else ''), encoding='utf-8')
            print(f"{len(default)} default forms changed ({len([k for k in default if k not in was['C']])} new), "
                  f'{len(mainland)} mainland forms of their own changed, {len(gone)} gone, since {a.ref}')
            if gone:
                print('GONE (drawn at', a.ref, 'and not now):', ''.join(gone))
            if a.list_only:
                return
            n = sheets(base, Path(tmp), out, [k for k in default if k in was['C']], [k for k in default if k not in was['C']],
                       a.per, a.size, False)
            m = sheets(base, Path(tmp), out + '-s', [k for k in mainland if k in was['S']], [k for k in mainland if k not in was['S']],
                       a.per, a.size, True)
            print(f'{n} sheets {out}-01.jpg ... and {m} of mainland forms {out}-s-01.jpg ...: before above the band, after below; list in {out}.txt')
        finally:
            if base.exists() and subprocess.run(['git', 'worktree', 'remove', '--force', str(base)], cwd=ROOT).returncode:
                print(f'could not remove the worktree {base}: run `git worktree prune`', file=sys.stderr)


if __name__ == '__main__':
    main()
