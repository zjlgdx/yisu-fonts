#!/usr/bin/env python3
"""Every form a change touched, before and after, large enough to judge.

    tools/hz_diff.py REF OUT_PREFIX [--per 6] [--size 220] [--list-only]

Editing one part redraws every character that holds it, and the ones nobody
meant to change are where the damage is: 0.980 lifted 又 for 侵 and pushed it
onto 冖 in 寢. This draws all of them, not the ones the change was for.

It checks REF out beside this tree, compares every drawing in both (Taiwan's
and the mainland's), and writes OUT_PREFIX-NN.jpg: twelve changed characters a
sheet, REF's drawing in the upper half and this tree's in the lower, each from
its own tree's code. OUT_PREFIX.txt lists the characters. A sheet of twelve
keeps a character about 300 pixels wide when the sheet is read at 2,000 across;
at forty-eight a sheet, two strokes run together look the same as two apart.

The reviewer is someone who did not make the change (a fresh agent with the
sheets and the checklist in the hanzi-round skill, no account of what was
intended). hz_sheet.py draws the default form; a mainland form that changed
alone is listed with (S) and needs round_proof.py or the built font.
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


def sheet(tree, out, chars, per, size):
    subprocess.run([sys.executable, 'tools/hz_sheet.py', str(out), chars, '--per', str(per), '--size', str(size)],
                   cwd=tree, check=True, capture_output=True)
    return Image.open(out).convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('out')
    ap.add_argument('--per', type=int, default=6)
    ap.add_argument('--size', type=int, default=220)
    ap.add_argument('--list-only', action='store_true')
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / 'base'
        subprocess.run(['git', 'worktree', 'add', '-q', '--detach', str(base), a.ref], cwd=ROOT, check=True)
        try:
            was, now = forms(base), forms(ROOT)
            default = [k for k in now['C'] if len(k) == 1 and was['C'].get(k) != now['C'][k]]
            mainland = [k for k in now['S'] if len(k) == 1 and was['S'].get(k) != now['S'][k] and k not in default]
            new = [k for k in default if k not in was['C']]
            Path(a.out + '.txt').write_text(''.join(default) + '\n' + ''.join(f'{k}(S)' for k in mainland) + '\n', encoding='utf-8')
            print(f'{len(default)} default forms changed ({len(new)} new), {len(mainland)} mainland forms changed alone, since {a.ref}')
            if a.list_only:
                return
            old = [k for k in default if k in was['C']]
            step, n = a.per * 2, 0
            for i in range(0, len(old), step):
                chars = ''.join(old[i:i + step])
                top = sheet(base, Path(tmp) / 'a.jpg', chars, a.per, a.size)
                bottom = sheet(ROOT, Path(tmp) / 'b.jpg', chars, a.per, a.size)
                w = max(top.width, bottom.width)
                img = Image.new('RGB', (w, top.height + bottom.height + 28), (40, 58, 90))
                img.paste(top, (0, 0))
                img.paste(bottom, (0, top.height + 28))
                n += 1
                img.save(f'{a.out}-{n:02d}.jpg', quality=88)
            if new:
                for i in range(0, len(new), step * 2):
                    n += 1
                    sheet(ROOT, Path(f'{a.out}-{n:02d}.jpg'), ''.join(new[i:i + step * 2]), a.per, a.size)
            print(f'{n} sheets: {a.out}-01.jpg ..., before above the band and after below; list in {a.out}.txt')
        finally:
            subprocess.run(['git', 'worktree', 'remove', '--force', str(base)], cwd=ROOT)


if __name__ == '__main__':
    main()
