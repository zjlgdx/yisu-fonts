"""python tools/check_fonts.py [OUT_DIR] [--private REGEX]

The checks before a pull request, on the built fonts in OUT_DIR (default out/):

- all three families are there, Regular and Bold, as .otf and .woff2;
- every font's head.fontRevision and version name are build.py's VERSION (the fonts are fresh);
- the OpenType Sanitizer passes every .otf;
- fontbakery check-universal, per family, has no FAIL or FATAL but the known
  ones (its full report goes to OUT_DIR/fontbakery-FAMILY.txt, one file per
  checkout, so checks can run side by side);
- each character holds its own script's form of every part (tools/hz_forms.py);
- no drawing sits worse than the baseline says it did: parts closer, strokes
  side by side on each other, ink narrower, the two scripts' forms merged, a
  drawing gone or no longer built of parts
  (tools/hz_gate.py, and its --selftest, which must see seeded defects fail);
- nothing new inside a part or between two characters: two characters with one
  drawing, a line drawn twice, a 點 through a stroke, a 豎提 turned the wrong
  way (tools/hz_inside.py and its --selftest);
- the ink gate still tells a join from a clear pair (tools/hz_ink.py
  --selftest; its survey of every form in the bold pens takes half an hour on
  all cores, so a change runs it with --chars on what it touched);
- no personal data: emails, home or temp paths, or anything --private matches
  (or the YISU_PRIVATE environment variable), wherever text can live in
  the .otf and .woff2 files: every table but the outlines, the decoded name
  records, the CFF strings, the glyph names, and the WOFF metadata.

Exits 1 if any of them fails. The known results, which the README explains,
are printed, not failed: file size (a WARN past 1 MB, and file_size's
massive-font FAIL past 9 MB, as a full set of common Chinese characters
runs past it) and, in Yinni, the CFF fonts' glyf error and the
double-width xAvgCharWidth.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
import _repo

ap = argparse.ArgumentParser()
ap.add_argument('out', nargs='?', default=str(_repo.ROOT / 'out'))
ap.add_argument('--private', default=os.environ.get('YISU_PRIVATE', ''))
a = ap.parse_args()
out = Path(a.out)
otfs = sorted(out.glob('*.otf'))
bad = []

# Every family in both weights and both formats: a partial build fails.
FAMILIES = ('YisuHuasha', 'YisuLouhen', 'YisuYinni')
missing = [f'{fam}-{w}.{ext}' for fam in FAMILIES for w in ('Regular', 'Bold') for ext in ('otf', 'woff2')
           if not (out / f'{fam}-{w}.{ext}').is_file()]
print('== files', 'all 12' if not missing else 'missing ' + ', '.join(missing))
if missing:
    bad.append('missing ' + ', '.join(missing))

from fontTools.ttLib import TTFont
import ots

from fontTools.misc.fixedTools import floatToFixed
import build
print('== versions', build.VERSION_TEXT)
for f in otfs:
    font = TTFont(f)
    rev, says = font['head'].fontRevision, font['name'].getDebugName(5)
    # fontRevision is 16.16 fixed point: compare it as stored, and the names as written
    if floatToFixed(rev, 16) != floatToFixed(build.VERSION, 16) or says != f'Version {build.VERSION_TEXT}':
        bad.append(f'{f.name} is {rev} ({says}), not {build.VERSION_TEXT}')
        print(' ', f.name, rev, says)

# The names a menu shows: English, and Chinese for zh-TW, zh-HK and zh-MO
# (Traditional) and zh-CN and zh-SG (Simplified), name IDs 1 and 4; ID 2 the
# weight (Regular and Bold are a style-linked pair); ID 6 the file's stem.
NAMES = {'YisuHuasha': ('Yisu Huasha', '一粟畫沙', '一粟画沙'), 'YisuLouhen': ('Yisu Louhen', '一粟漏痕', '一粟漏痕'),
         'YisuYinni': ('Yisu Yinni', '一粟印泥', '一粟印泥')}
print('== names')
for f in otfs:
    stem, weight = f.stem.split('-')
    en, hant, hans = NAMES[stem]
    want = {(1, 0x409): en, (2, 0x409): weight, (4, 0x409): f'{en} {weight}', (6, 0x409): f.stem}
    for lang, zh in ((0x0404, hant), (0x0C04, hant), (0x1404, hant), (0x0804, hans), (0x1004, hans)):
        want[1, lang], want[4, lang] = zh, f'{zh} {weight}'
    name = TTFont(f)['name']
    wrong = [f'ID {i} lang {lang:#06x}: {name.getName(i, 3, 1, lang)} for {v}'
             for (i, lang), v in want.items() if str(name.getName(i, 3, 1, lang)) != v]
    print(f'  {f.name}: {"ok" if not wrong else "; ".join(wrong)}')
    bad += [f'{f.name} {w}' for w in wrong]

print('== OTS')
for f in otfs:
    p = ots.sanitize(str(f), os.devnull, capture_output=True)
    print(f'  {f.name}: {"pass" if p.returncode == 0 else "FAIL " + (p.stderr or b"").decode()[:200]}')
    if p.returncode:
        bad.append(f'OTS {f.name}')

KNOWN_FAIL = ('[code: massive-font]',)   # the README explains each

print('== fontbakery check-universal')
fb = Path(sys.executable).with_name('fontbakery')
for fam in sorted({f.name.split('-')[0] for f in otfs}):
    log = out / f'fontbakery-{fam}.txt'
    with log.open('w') as fh:
        subprocess.run([str(fb), 'check-universal', *map(str, sorted(out.glob(f'{fam}-*.otf')))], stdout=fh, stderr=subprocess.STDOUT)
    txt = log.read_text(errors='replace')
    counts = dict(re.findall(r'\b(ERROR|FATAL|FAIL|WARN): (\d+)', txt))
    print(f'  {fam}: ' + ' '.join(f'{k} {v}' for k, v in counts.items()))
    fails = []
    for line in txt.splitlines():
        m = re.match(r'^\s*(?:[^\w\s]+\s*)?(FAIL|FATAL|ERROR|WARN)\s', line)   # not the legend's 'A FAIL is ...'
        if m:
            known = m.group(1) == 'FAIL' and any(k in line for k in KNOWN_FAIL)
            print('     ' + line.strip()[:100] + ('  (known)' if known else ''))
            if m.group(1) in ('FAIL', 'FATAL'):
                fails.append(known)
    # a FAIL counts unless its line names a known code; a count with no
    # matching line (a wrapped or new format) fails too
    if not all(fails) or len(fails) < int(counts.get('FAIL', 0)) + int(counts.get('FATAL', 0)):
        bad.append(f'fontbakery {fam}')

print('== personal data')
pat = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}|/Users/|/home/|/private/tmp|/tmp/|C:\\\\Users'
if a.private:
    pat += '|' + a.private
rx = re.compile(pat.encode(), re.I)
OUTLINES = {'CFF ', 'CFF2', 'glyf', 'gvar'}


def text_of(path):
    """The bytes where text can live: every table but the outlines (random
    outline bytes can look like an email), the CFF's strings and the glyph
    names, the name records decoded, and a WOFF's metadata and private blocks."""
    f = TTFont(path)
    parts = [f.reader[tag] for tag in f.reader.keys() if tag not in OUTLINES]
    if 'CFF ' in f:
        cff = f['CFF '].cff
        parts += [n.encode('latin-1', 'replace') for n in [*cff.fontNames, *cff.strings.strings]]
    parts += [n.encode('latin-1', 'replace') for n in f.getGlyphOrder()]
    # Windows name records are UTF-16BE, which the byte pattern can't see.
    if 'name' in f:
        parts += [r.toUnicode(errors='replace').encode('utf-8') for r in f['name'].names]
    parts += [getattr(f.reader, b, None) or b'' for b in ('metaData', 'privData')]
    return b'\n'.join(parts)


files = [*otfs, *sorted(out.glob('*.woff2'))]
hits = []
for f in files:
    m = rx.search(text_of(f))
    if m:
        hits.append(f'{f.name} ({m.group().decode("latin-1")!r})')
print('  hits:', ', '.join(hits) or 'none', f'({len(files)} files)')
if hits:
    bad.append('personal data in ' + ', '.join(hits))

print('== forms (tools/hz_forms.py)', flush=True)
if subprocess.run([sys.executable, str(Path(__file__).parent / 'hz_forms.py')]).returncode:
    bad.append('forms')

print('== parts (tools/hz_gate.py)', flush=True)
gate = str(Path(__file__).parent / 'hz_gate.py')
if subprocess.run([sys.executable, gate, '--selftest']).returncode:
    bad.append('the parts gate passed a seeded defect')
if subprocess.run([sys.executable, gate]).returncode:
    bad.append('parts')

print('== inside a part (tools/hz_inside.py)', flush=True)
inside = str(Path(__file__).parent / 'hz_inside.py')
if subprocess.run([sys.executable, inside, '--selftest']).returncode:
    bad.append('the inside gate missed a seeded defect')
if subprocess.run([sys.executable, inside]).returncode:
    bad.append('inside a part')

# The whole survey draws every form in three pens (about half an hour on all cores):
# run tools/hz_ink.py --chars on what a change touched. Here, only that it tells.
print('== ink in the bold pens (tools/hz_ink.py --selftest)', flush=True)
if subprocess.run([sys.executable, str(Path(__file__).parent / 'hz_ink.py'), '--selftest']).returncode:
    bad.append('the ink gate missed a seeded join')

print('== ' + ('FAILED: ' + '; '.join(bad) if bad else 'all passed'))
sys.exit(1 if bad else 0)
