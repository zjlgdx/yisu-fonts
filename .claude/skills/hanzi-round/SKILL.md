---
name: hanzi-round
description: Draw the next rows of hanzi_order.tsv into the 一粟 (Yisu) fonts and ship them as a release — draft batches, edge check, merge, build, checks, proof, pull request, release. Use for a Chinese round or a milestone of them ("do the next 200 rows", "繼續處理下一批", an issue titled "Chinese rows A–B"). Not for Latin, symbols or the build's pens.
---

# A Chinese round

A round draws every form in a range of rows of `hanzi_order.tsv` (Simplified
and Traditional together) and ships it as one release. AGENTS.md's rules hold
throughout: everything original, the design board first, gitleaks before each
commit, no personal data in anything published, never force-push main, and the
maintainer decides merges.

The tools are in `tools/`; run them with `.venv/bin/python` from the checkout.
Drafts go in `work/` (ignored by git), never in a temp folder that a reboot
clears. `work/unihan/` keeps the Unihan files `order.py` reads.

## 1. Draft

1. `tools/hz_todo.py FIRST LAST` lists what the rows still need.
2. Write batches `work/rLAST_1.py`, `_2.py`, … (about 70 characters each). The
   first starts with `# ---- rows FIRST-LAST of hanzi_order.tsv`. Write them
   in hanzi_strokes.py's own terms: `C['字'] = lr(L['亻'], K['...'])`,
   `box((part, (x0, y0, x1, y1)), ...)`, `S('E M.. L..')`.
3. Reuse before drawing: `tools/hz_have.py CHARS work/rN_1.py,...` says what
   exists. `tools/hz_fixrefs.py work/rN_2.py work/rN_1.py` fixes K/C mix-ups
   and lists unknown parts.
4. Look at them: `tools/hz_sheet.py work/sheet.jpg --batch work/rN_1.py` (all
   three pens, and Huasha large). Fix what looks wrong and look again.
5. Draw each in its own standard's form: 教育部 standard forms for
   Traditional, 通用规范汉字表 for Simplified.
6. Before drawing one, check its parts and stroke count against Unihan
   (`kTotalStrokes` in `Unihan_IRGSources.txt`, `kRSUnicode`).
   `tools/hz_count.py --batch ...` counts every drawn part and character
   against it and lists the parts that are off first. Many of those only
   draw a turn as two items or two strokes as one (糸's 幺, 凵): see which with
   `tools/hz_strokes.py work/p.jpg NAMES`, which numbers each stroke. A part
   built from the wrong part is a real one: 番 had 采 (爫 over 木) where its top
   is 釆 (丿 over 米); 宿 added 百's 丿 to 白, which has its own. A font
   only shows a form's look; for a stroke's kind and order read the standard
   (通用规范汉字笔顺规范 for Simplified): read off a font, 尧's third stroke
   went in as a 點 where the standard has a 撇. Where the
   教育部 字樣說明 gives another count for a Traditional form, follow it. Give a
   Traditional character Taiwan's form of every part, a Simplified one the
   mainland's: 䍃 is `K['䍃TW']` (𠂊 and a dot) in 搖 謠 瑤, `K['䍃']` (爫) in
   谣 瑶; 糸, 言, 貝 against 纟, 讠, 贝.
7. A character both scripts write (花 草 部 偏, and 著 藉, which 通用规范汉字表
   has too) is drawn in Taiwan's form: `K['艹T']` (十十), `K['阝T']` and
   `K['⻏T']` (three strokes), `K['敖T']`, `K['戶']`. Add it to `_SHARED_TW` at the end of
   `hanzi_strokes.py`, which gives it the mainland's form for text tagged
   Simplified Chinese. A Simplified-only character built on a shared one
   draws `_mainland(C['苗'])`. Which a character is, `hanzi_order.tsv` says:
   the same character in both columns is shared; a `-` in the Traditional
   column (or another character there) means Taiwan doesn't write it, so it
   is Simplified only. `tools/hz_forms.py` checks all of this (`--batch` for
   drafts); `merge_round.py` runs it before it merges and `check_fonts.py`
   after the build.
8. The order strokes are drawn in is the order the site writes them, so draw
   them in the standard's order, `box()` parts included: a part drawn first in
   the list is written first. Look the order up for both scripts before
   drawing: MOE's 筆順學習網 (`searchW.jsp?ID2=1&WORD=字`) for Taiwan, zdic's
   stroke animation for the mainland. Where they differ, draw Taiwan's as
   `K['名T']` and the mainland's as `K['名']`, pair them in `_TW_PARTS`, and
   put the shared users in `_SHARED_TW` (敢 戎 出 凹 延 乏 黃, 肩 扇's 戶).
   - 辶 and 廴 are written last, after what they carry: `zou()` puts them
     last, and so must any box that holds one.
   - 凵 is two strokes, 豎折 then 豎, never a single stroke that turns back up.
     山 and 耑 write their middle 豎 first; Taiwan's 出 does too, while the
     mainland's 出 writes it third.
   - Taiwan counts 辶 as 4 strokes and 廴 as 3, where the mainland counts 3
     and 2: Taiwan parts the 橫折折撇 at its first turn. They are
     `K['辶T']`/`K['辶']` and `K['廴T']`/`K['廴']`, paired in `_TW_PARTS`.
   - A turn is one stroke, and so one `S()` item: 橫折, 撇折, 豎折折鉤 are
     drawn as one path that turns. Two strokes that meet at a corner are two
     items. Polish 5 found both mistakes many times: 糸 幺 幾 with each pair
     of 撇折 drawn as one zigzag, 匚 弓 鸟 with one turn drawn in pieces.
   - A shared part's order moves its whole family: 隹 writes its middle 豎
     before the bottom 橫, 門's right half is 豎 then 橫折鉤, the right 阝 is
     橫撇彎鉤 then 豎, 尸 is 橫折, 橫, 撇. Fix the part, not each character.
   - Unihan's `kTotalStrokes` mixes the two scripts' counts (鍋 16, 飯 13
     against 教育部's 17 and 12). For a Taiwan form the Ministry's frames
     decide. When a difference is understood, add the part to `KNOWN` in
     `tools/hz_count.py` with the reason, so its list keeps only what nobody
     has looked at yet.
   - For Traditional characters, count against 教育部 itself:
     `tools/hz_moe.py COUNTS.json` takes {character: frames}, counted while
     viewing 筆順學習網's frames in the browser (never save the images), and
     lists the characters off and the parts most of whose users are off.
     Polish 6 found 430 this way that Unihan hid. A strip over 16 strokes has
     two columns, read right column first; a tall character's last frame can
     spill into an extra slot, so a count one too high needs a look first.
   - Taiwan forms the standard has and fonts often don't: 阝 is 3 strokes
     (橫撇, 彎鉤, 豎), 者 has no 點 (8), 艹 is 豎 橫 橫 豎, and 㐬 充 育 have no
     點 over the 一 (流 9, 充 5). 衣 and the bottoms written like it (表 展 農
     長 袁 裹 喪 讓) put the small 撇 before the 捺.
   - A right count is not a right shape: 飞 drawn as 几 and 莫 reading as 其
     both had the right count. After a round, look at its characters on
     `tools/hz_grid.py` sheets, not only at the numbers: a wrong part (阝 for
     卩, 西 for 覀), the other script's form, and parts that collide.

### What goes wrong, and the fix

- **`box()` maps a part's whole 1000 grid into the rect, not its ink.** Parts
  drawn in place on the grid need the full frame or a stretched rect, or they
  come out tiny and flat: 爫 (y 30–290), 尚, 雨, 罒 (60–300), 冖 (80–220),
  宀, 穴, 广, 门, 門, ⺈, ⺮, 灬, 亍, 乚 (x 760), 乞 (x 560–940).
  Some are partial: K['甘'] is the top half, K['弗'] the top half, K['幺']
  y 40–570. To scale one up, give a rect bigger than the frame:
  甘 `(0, -60, 1000, 2000)`, 弗 `(0, 0, 1000, 1700)`, 幺 `(0, 0, 1000, 1700)`,
  乞 `(-375, 0, 1046, 1000)`.
- **A shared character takes Taiwan's part.** Where a part has a Taiwan form
  (`K['瓦T']`, `K['叟T']`, any name in `_TW_PARTS`), a character both scripts
  write uses that one, and goes in `_SHARED_TW` so Simplified text gets the
  mainland's. `hz_forms.py` fails on a Taiwan part with no ZHS form, and on
  a mainland part in a character Taiwan writes.
- **Draft only what `hz_todo.py` lists.** A row's Traditional form is often
  drawn already (rows 5,660–5,829 redrew 23 that were, and the later
  definition won, moving six glyphs). Take the characters from its output, not
  from the rows; `merge_round.py` refuses a batch that defines anything again,
  and `tools/hz_dupes.py BATCHES` lists them.
- **Stroke counts catch a wrong part.** In `hz_count.py --batch`'s list, look
  for the batch's own characters: 殇 came out one short because its right side
  is 𠂉 over 𠃓, not 伤's 力, and 毂 one over because, unlike 轂, it has no 一
  above 车. A part with the same count hides (昝's 卜 drawn as 人): look the
  unsure ones up.
- **The radical is not always on the left.** 媭 is 须 over 女, not 女 beside 须;
  a batch written a family at a time makes this easy to miss. Say each
  character's structure to yourself before `lr()`, and run `tools/hz_count.py
  --batch ...` on the batch: a part sliced short (彘's 彑 without its foot)
  shows as a count one off.
- **Nothing starts on the top edge.** A stroke at y < 30, or a part whose rect
  starts at y 0 with ink at its own top, is cut off by Yinni and
  Louhen (懼's 瞿 did this). Start at 30, or the rect at 40–50.
- **Stacked parts crowd.** 疊, 寧, 憋 needed their top parts smaller and the
  lower ones given more of the height.
- **A part boxed twice shrinks.** `K['髟']` drew its 镸 on the left of the
  grid and then boxed it into the left half again, so 鬆 髭 鬢 got a 镸 a
  quarter wide. Before boxing a part into part of the frame, look where its
  ink already sits.
- **A shared part's mistake spreads.** 豕 lacked its short right 丿, 罙 took
  穴's dot, 龠 lacked the 一 under 人, 奥 closed its 冂 and lost 米's lower
  strokes: each was found when a new character used the part and its count
  came out wrong. Count the part itself and fix it where it is defined, in
  `hanzi_strokes.py` (a batch cannot redraw a part: the gate and
  `merge_round.py` refuse it), with a before/after sheet of every character
  that uses the part (`hz_diff.py`).
- **Look-alike parts are different characters.** 夐 ends in 夂 (14 strokes,
  觼); 敻 ends in 攵 (15, 瓊). Check the code point, not the look.
- **A shell pipe can mangle the characters.** `grep | cut -c` on macOS cuts
  bytes, not characters; pull a batch's characters out with Python.
  `edges.py` fails when none of `--chars` is drawn, so a mangled list can't
  pass as clean.

- **A shared character drawn with the mainland's part.** 獾 took `K['雚']`
  (the mainland's 艹) as its default, so Traditional text got it too.
  `hz_forms.py` now fails on it: draw those with the Taiwan part (`K['雚T']`,
  `K['离T']`) and add the shared ones to `_SHARED_TW`.
- **Pair what differs, not the family's part.** A pair in `_TW_PARTS` says
  every character writes the part differently. Where one character does,
  pair its own part: only 釉 has 采 for 釆 in Taiwan (`K['釉旁T']`,
  `K['釉旁']`), only 蚤 has 㕚 for 叉 (`K['㕚']`, `K['蚤头']`), and 滿's top is
  卄, not 艹 (`K['卄']`). Paired as 釆 and 叉 themselves, the check listed 番's
  whole family and 杈 汊 釵, all right as drawn.
- **A check's noise is a finding.** That list of 36 "deliberate" ones hid
  three mistakes in the data, none in the 36 drawings: the pairs above, and
  89 rows of `hanzi_order.tsv` that held a Simplified character in the
  Traditional column too (`order.py` fell back to the character itself when
  no Traditional form passed its filter), which made 涝 馍 颧 look shared and
  left 25 Big5 forms (澇 饃 顴 …) undrawn. Before adding an exception to a
  check, find out why it fires; fix the data until it prints nothing, then
  make it fail the build.
- **Strokes that meet don't cross.** 癶's two 撇 rest on its 捺; drawn through
  it, 登's top read as an ㄨ until 0.970, in the proof's own first line. Nobody
  looks hard at a common character. `tools/hz_cross.py` lists a 撇 that
  crosses an earlier 捺 (run it on the batches); for the rest, look at each
  new part large (`hz_sheet.py --size 300`) beside the standard, asking of
  every junction: touch, cross, or apart?
- **One part, one drawing.** 登, 癸 and 發 each carried their own copy of 癶,
  so the mistake was in three places and 發's copy differed again. A top or
  side that two characters share is a `K[...]` part from the second use on.
- **Air between parts.** The first pitfall above, seen from the other side:
  a part whose ink sits low in its grid (心 from y 330, 皿 from 300), or a
  top boxed into a rect taller than it needs (卷's 龹 into 0–640), leaves an
  empty band between the parts. 0.980 closed it in 414 characters. After the
  sheet, run `tools/hz_balance.py CHARS` on the batch's characters and read
  its "widest empty band" lists: past about 130 across, lift the lower part's
  rect until the band is near 70 (its ink top is `y0 + a * (y1 - y0)`, with
  `a` where the part's ink starts in its own grid).
- **A top is not a character.** `K['士']` and `K['立']` are drawn in the upper
  half, for 志 and 音. Alone, beside a left part or at the bottom they were
  half a character high (士, 位 拉 粒, 笠 竖). Use `K['士全']`, `K['立全']`
  there, and read `hz_balance.py`'s "least height filled" list.
- **A stack is not narrower than its parts.** A top and bottom each boxed
  into a middle slice (員's 口 and 貝, 台's 厶 and 口) made a character three
  fifths of the square wide beside full-width neighbours. 0.990 stretched 41
  such definitions. Read `hz_balance.py`'s "least width filled" list: under
  600 across, widen the rects about x 500 until the ink is near 650. 目 申 自
  and a few more are narrow by nature.
- **Two level strokes need 70, not 40.** A gap that reads between slanted
  strokes closes between two 橫: the pens draw one thick bar (舅's 臼 on 男,
  賃, 房's 方 under 戶, 彙, 疊). `tools/hz_bars.py CHARS` lists the pairs; look
  at them on a sheet and keep about 70 between the strokes' centres.
- **A head with strokes inside hides what is under it.** `hz_balance.py`
  skips a part that encloses another, so 虍's 七 lay on every lower part
  (慮 膚 虜 虞, 52 characters) and 門's leaves on what stood inside (闡 闖 閘).
  Keep 60–75 between the head's last inside stroke and the first ink under
  it, measured on the ink (`hz_gate.py --where`), not on the rect. 虍's 七
  now ends at 415 and the part under it has its ink from 475. A character
  with something inside 門 uses `K['門框']`, whose leaves end at 360, with
  the inside part's ink over about x 215–780, y 435–935; `K['門']` with its
  long leaves is for 門 itself and for parts set beside it.
- **Better is not yet good.** 盧's 田 lay on 虍 (5 apart); the fix moved it
  down to 32 from 皿, and the gate, which compares with before, called that
  an improvement. It now lists every form a change moved that is still under
  a floor: bring each over the floor or name it in the commit.
- **Fixing a part breaks whoever worked around it.** 凯 placed the narrow 岂
  in a rect 1,100 wide to fill its half; once 岂 itself was widened it ran
  through 几. After changing a part's own size, compare every character's
  closest gap between parts before and after (`hz_balance.py`'s "parts
  closest together", on both trees) and look at each one that got tighter.
- **An inline redraw of a paired part loses the mainland form.** 房's 戶 was
  redrawn shorter as an inline `S(...)`; `_mainland()` swaps parts by
  identity, so the mainland 房 silently took Taiwan's 撇. A variant of a part
  in `_TW_PARTS` is itself a pair (`K['戶短']`, `K['户短']`). After a fix,
  check that no character's two forms became the same drawing.
- **Lifting a part can push it into the next.** 0.980's lift moved 𠬶's 又
  up onto its 冖 (寝 寢 浸). After a mechanical pass, look at every changed
  character large, not only the ones the pass was written for.
- **A fallback is a claim.** "No form found, so use the character itself"
  said Taiwan writes 线. When a rule finds nothing, write nothing (`-`).
- **Check only the round's characters at the edges.** `edges.py --batch` with
  no `--chars` draws every character there is (half an hour a font); pass the
  batches' own characters.

- **A family's template puts the radical in the wrong place.** Drafting a whole
  radical family from one left-right template drew 贳 貰 as 贝 beside 世 (世
  sits over 贝), 飙 飆 with 风 on the left (猋 is), and gave 痫 癇 the more
  common 间 間 for 闲 閒. Stroke counts don't catch a part in the wrong
  place or a look-alike with the same count: look up every character whose
  radical is not where its family's is, and every part that has a commoner
  look-alike, before the sheet.

## Acceptance: what counts as checked

A change is accepted on what a command printed and what a reviewer who did
not make it saw, never on "looked fine". Until 0.990 the scans were lists to
read, the sheets were read forty-eight to a page by whoever made the change,
and whole classes shipped: 思 on 虍's 七 in 慮 for two hundred versions, 又 on
冖 in 寢 from a pass that was meant to help. Copy this list and tick it:

```
- [ ] tools/hz_gate.py --selftest      every seeded defect fails
- [ ] tools/hz_gate.py [--batch ...]   "no form got worse" (it exits 1 otherwise)
- [ ] tools/hz_inside.py --selftest, then tools/hz_inside.py [--batch ...]   "nothing new"
- [ ] tools/hz_forms.py, tools/hz_cross.py    0 problems
- [ ] tools/hz_diff.py origin/main OUT  every changed form, before and after
- [ ] tools/edges.py --chars "$(cat OUT.txt)"   cut: none, six fonts, both scripts' forms
- [ ] tools/hz_ink.py --chars "$(cat OUT.txt)"   "no form joins more" in the three bold pens; it fails on an empty list
- [ ] the sheets reviewed by an agent that did not make the change
- [ ] the whole change reviewed on another vendor's model; and the tools too,
      if a tool changed ("Having the checks reviewed", below)
- [ ] each finding rerun, then fixed or answered; the gate green again
- [ ] the gate's "moved and still under a floor" list: each fixed or named
- [ ] tools/hz_gate.py --accept        only now; the .tsv's diff is in the commit
- [ ] tools/hz_ink.py --accept --chars "$(cat OUT.txt)"   the same for hz_ink.tsv (without --chars: every form, about half an hour)
```

- **The gate measures, the baseline remembers.** `hz_gate.py` measures every
  form (stroke against stroke between sibling parts at every level, with no
  pair skipped; level strokes of two parts; the ink's width and height;
  whether the two scripts' forms are different drawings) and fails when a
  form is worse than `tools/hz_gate.tsv` says it was. `--where CHARS` says
  where the closest strokes are. A form that was already tight is debt
  (`--debt`): it fails only if it gets worse, so old noise cannot hide a new
  defect, which is what happened to every list before it.
- **Ink is a third gate.** `hz_gate.py` measures centre lines; two parts 40
  apart pass it and the bold pens still draw them as one mark. 0.995 and
  0.996 each had a review panel find this after the gate passed (堯's three
  土, 火火 on 冖, 辯's middle on its right 辛, 艹 on 罒). `hz_ink.py` draws
  two sibling parts together and each alone, in the character's place and
  pen, in the three bold pens, and says whether ink of the one reaches ink
  of the other. Draw them together: 印泥 blurs the whole drawing before it
  cuts it, so two marks that never touch alone can close up. It follows each
  pair by its stroke numbers, so one pair parting never pays for another
  joining (a pair parted on paper that still touches in ink is listed, not
  failed: it stood closer than APART before), and the baseline is what main draws: compare a change against
  it before `--accept`, never write it from the change. `--where CHARS`
  says which strokes join in which pen; `--debt N` lists the forms with most
  ink between parts. The bold pens are 70 and more wide in a form of
  fourteen strokes, so bars 67 apart on paper (鼻's 自 on 田) still join:
  most of the baseline is that, a matter of the pens' weight in dense forms
  and not of one drawing. Widen a gap where a form reads wrong; do not chase
  the count form by form.
- **Inside a part is another gate.** `hz_gate.py` compares sibling parts, so
  it cannot see a fault within one list of strokes or between two
  characters. A review of 0.991 by three vendors' models and eleven sheet
  readers found what that let through: 沈 with 沉's drawing (and three more
  such pairs), 𠂤's bar drawn twice, 刃 and 飞 with the 點 through the 撇, 民
  and 氏 with the 豎提 turned down and left. `hz_inside.py` finds those four
  kinds, names the part, and fails when a part has more of one than
  `tools/hz_inside.tsv` says. Its own first review, by three vendors'
  models, got every kind past it (strokes in another order, a bar in
  pieces, a tail written as a curve) and found it skipping 120 unnamed
  lists; each of those is now a seed in its self-test.
  What it still cannot see is a form that is well made and is the wrong
  form (殳 with a hook, 今 with the mainland's dot in Taiwan's text): that
  takes the standard, looked at large beside ours, a class at a time.
- **Green before accept.** `--accept` rewrites the baseline, so it would also
  swallow a regression. Run it only when the gate is green, or when each
  remaining failure is one you can name in the commit message with its
  reason. The gate also lists what a change moved and left under a floor
  (33 forms in 0.990, the dense four-tier ones): fix each or name it too.
- **A check never seen failing proves nothing.** The gate's first self-test
  passed two of its seeded defects: they were compared with a baseline that
  already held them. A new check goes in with a seed that it fails on.
- **Review what changed, all of it, large.** `hz_diff.py` finds every form
  whose drawing differs from the ref (355 when 41 definitions were touched)
  and draws twelve to a sheet, before above and after below; the mainland
  forms that are their own drawings go on the `-s-` sheets, and forms that
  are gone are named. The list of what you meant to change is not the list
  of what changed.
- **The reviewer did not make the change.** Give a fresh agent the sheets and
  the questions (parts touching, level strokes read as one bar, a part tiny
  or squashed, worse than before, the heavy pen closing up), not what the
  change was for; another model is better still. Its brief forbids writing
  files and saving reference images. A finding is settled by the gate or a
  larger render, not by arguing.
- **A lesson becomes a check.** When something gets past all this, add the
  measurement to `hz_gate.py` and a seed to its self-test before fixing the
  glyph. A sentence here is the last resort, for what no script can see.

### Having the checks reviewed

The gate was written by the one whose misses it was meant to catch, and its
first three reviews, on three other models, each got a worse drawing past
it. What they found, 0.990:

| review | got past the gate |
|---|---|
| first | a deleted drawing; a new collision in a form whose parts already met (the gate kept one least per form); a self-test that never ran the gate's own path |
| second | a wall beside 月's upright 撇 (side-by-side strokes were only looked for in 橫 and 鉤); a built character rewritten as one list of strokes; a batch redrawing a part; mainland forms never drawn by the edge check; four reasons with no seed |
| third | two short bars 30 apart (runs under 100 long were not runs); two of three parts merged into one list; a gap of 25 beside an old crossing (the count stopped at 20); the redefinition check itself unseeded |
| a full review of the drawings | 盧's 田, moved off 虍 and onto 皿: better than before, so the gate passed it |

No two found the same holes, and none was found by the author. So:

1. **Two kinds of review, both needed.** One reads only the tools and is
   asked one question: can a drawing that got worse still pass, and what
   does the flow claim that it does not check? The other reads the whole
   change, most of all `hanzi_strokes.py`, draws what it doubts with
   `hz_sheet.py`, and looks for slips in rects, family members missed, and
   text that is no longer true. Neither stands in for the other.
2. **Other models, at least two vendors.** From this repository:
   `bash ~/.claude/skills/one-shot-pairing/scripts/review-panel.sh --base
   origin/main --members codex,agy,grok --note "..."` on the pushed commit;
   each member works in its own throwaway worktree. The note gives the
   question, the venv's python, and the rules (no build.py, no downloads, no
   reference images saved, no fonts installed).
3. **A finding is a command.** Each comes with a command and its output;
   rerun it before believing it, and fix only what reproduces.
4. **Fix the check, then measure again from main.** After a change to what
   the gate measures, rebuild the baseline from main with the new code (copy
   `hz_gate.py` into a worktree of `origin/main`, `--accept` there, copy the
   .tsv back) and run the gate on the branch: a stricter measure finds
   drawings the old one passed (阊, then 屑 茎 赣 鹇 鼉 in 0.990).
5. **Every reason has a seed.** A new way to fail goes in with a seeded
   defect that only it catches; the self-test fails when a reason has none.
   A threshold gets a seed just inside it (bars 70 long when the limit is
   60), or it can drift back unseen.
6. **Tools first, build last.** The reviews need no built fonts, and each
   one that changes a drawing restarts the hour's build (three times in
   0.990). Run the reviews on the pushed branch, fix, and build once the
   last report is in.

### Changing a part that is already drawn

A new batch only adds drawings. A change to `K[...]`, or a pass over many
definitions, redraws characters nobody is looking at.

1. Fix one by hand, and run the gate and `hz_diff.py` on it, before writing
   the script that does the rest.
2. Run the script in small brackets (one family at a time) with the gate
   after each, not once after 123 definitions.
3. Look for whoever worked around the part (a rect stretched to make up for
   its size) and fix them in the same change: the gate lists them as
   "tighter" or "narrower".
4. A variant of a part in `_TW_PARTS` is itself a pair. An inline redraw
   loses the mainland form; the gate reports it as "merged".

## 2. Check the edges, then merge

```
.venv/bin/python tools/hz_gate.py --batch work/rN_1.py,work/rN_2.py,...
.venv/bin/python tools/edges.py --batch work/rN_1.py,work/rN_2.py,...
```

The gate first (seconds): it fails on a new drawing whose parts are under
30 apart or whose level strokes are under 55, and on a batch that gives a
part or character already drawn a different drawing (the characters built
on the old one keep it, so change it in `hanzi_strokes.py`, where the gate
sees all of them). `merge_round.py` runs it again and refuses on red.

It draws every character in all six fonts on the build's own canvas
(`build.canvas`) and lists any whose ink reaches the edge; fix them first.
The pens' jitter depends on the canvas, and Yinni's is a cell wider,
so a check on any other canvas misses cuts.

Then in a branch `hanzi-LAST` from main:

```
.venv/bin/python tools/merge_round.py LAST NEW_VERSION work/rN_*.py
```

It adds the batches before the mainland block of hanzi_strokes.py, sets
`VERSION` (0.010 a round), and updates the README's counts. Coverage is whole
percents but one decimal past 99.5, so it never shows 100%.

## 3. Build and check

```
.venv/bin/python build.py              # about an hour; must print no "cut off"
.venv/bin/python audit.py
.venv/bin/python tools/check_fonts.py  # versions, OTS, fontbakery, personal data
```

`check_fonts.py` fails on a stale font, an OTS failure, a fontbakery FAIL, or
anything that looks personal (add your own name with `--private` or
`YISU_PRIVATE`). The known results, explained in the README, are printed
but pass: file size (the WARN past 1 MB, and `massive-font`'s FAIL past 9 MB,
marked `(known)`), and in Yinni fontbakery's CFF `glyf` error and the
double-width `xAvgCharWidth`. A new FAIL code is fixed, or explained in the
README and added to `KNOWN_FAIL` in `check_fonts.py`, once the maintainer agrees.

## 4. Proof and design board

`tools/round_proof.py FIRST LAST work/proofN.jpg` sets a line of Taiwan's
text and one of the mainland's in every font, then the round's characters.
Look at it. It goes on the design board (the Pinboard theme project) before
the pull request.

## 5. Pull request and release

```
tools/open_pr.sh ISSUE FIRST LAST ["one line on anything fixed"]
```

It runs gitleaks on the branch, pushes it, and opens the PR. Merge only when
the maintainer says so (with a merge commit). Then, from the checkout that
built the fonts:

```
tools/release.sh FIRST LAST ["the same fix line"]
```

It refuses unless main has this VERSION and every font in out/ says it, then
makes the tag `vVERSION` with the fonts and their SHA-256.

## Many rounds at once

`tools/stack.sh WORKTREES main work --build < spec`. Each line of the spec is
`ISSUE FIRST LAST VERSION PREFIX`. It makes one worktree per round, each
branch one commit on the one before, and builds them all at once (seven take
about two hours on 18 cores). Set `COMMIT_TRAILER` for a Co-Authored-By line.
Check, proof and ship them in order.

- Before stacking rounds drafted side by side, run `tools/hz_dupes.py` on all
  their batches in row order and keep one definition of each part (the
  earliest, as a rule). Then check that the one kept means the same thing to
  every user: one round's `K['贰']` had its 贝 and another's didn't, so the
  second's 贰 would have drawn 贝 twice. Redraw everything that uses a part
  you removed.
- The reviewer bot reads a pull request once, when it opens, and takes
  minutes where a build takes an hour. Open every round's pull request as
  soon as its batches are merged and checked, before the final builds; fix
  what it finds on the earliest branch that has the character, merge that
  branch forward, and build each round once. A fix pushed later is not
  reviewed: check it yourself (the sheet, `hz_count.py`, the standard).
- Check a claim about a part against the standard, in the browser: zdic's
  stroke code (1 橫 2 豎 3 撇 4 點 5 折) spells a character's parts in order
  (痫 ends in 闲's 木, not 间's 日), and 教育部's 筆順學習網 shows Taiwan's.
  Read them; save nothing.
- Merging a branch forward conflicts where both sides added `_SHARED_TW`
  lines: `tools/hz_resolve_shared.py` keeps both. `open_pr.sh` refuses a
  branch with conflict markers in it. In a script with `set -o pipefail`,
  `git log | head` fails the script; use `git log -1 | cat`.
- Once a PR merges, merge `origin/main` into the next branch (a merge commit;
  never rebase a branch others stack on), then run `check_fonts.py` there.
- Drafting the next round while one builds: load the earlier round's batches
  and fix file first, in every tool's batch list
  (`r5184_1.py,…,r5184_fix.py,r5364_1.py`), so the new batches use its parts.
- Other work can ship while a stack builds. Before opening a PR, look at
  main's `VERSION` and the latest tag: 0.730 was once taken by another
  branch's release while a round built as 0.730, and the round merged with no
  release of its own. `open_pr.sh` now refuses a version main has reached or
  a tag has; take the next free one. If main gained glyph changes, the fonts
  you built lack them: rebuild after merging.
- A worktree has no `work/`: write its proof into the main checkout's
  (`round_proof.py FIRST LAST /path/to/fontkit/work/proofV.jpg`).
  `release.sh` finds the main checkout's `.venv` and fetches the tags itself.
- A fix that later rounds need (a part redrawn in `hanzi_strokes.py`): commit
  it on its round's branch, then merge that branch into the later ones, and
  rebuild only what changed.

## Past the frequency list

The corpus counts end at row 2,849. Rows 2,850–4,823 (count 0) are the rest
of Taiwan's 常用國字標準字體表 (4,808, `moe_4808.tsv`, from Wikisource and
checked against the MOE's PDF; the README has the source and licence) and of
level 1 of 通用规范汉字表 (3,500, the last column of `hanzi_order.tsv`),
sorted by radical so a round draws whole families. Rows 4,824–5,364 are the
rest of Big5's first level (5,401, Unihan `kBigFive` A440–C67E), sorted the
same way, with the mainland's form where 通用规范汉字表 has it at any level.
Draw their Traditional forms as Taiwan's 次常用國字標準字體表 writes them. A `-`
in a column means that script has nothing to draw on that row. Rows 5,490–7,183 are the rest of
通用规范汉字表's second level (kTGH 3501–6500), with Traditional forms from
CNS planes 1 and 2. Since 0.970 the earlier rows hold those forms too where
the first plane had none (涝 澇), so `order.py`'s output can add characters
to rows already drawn: after changing it, `hz_todo.py 1 LAST` must print
nothing, or the new ones are a batch for the next release.
`merge_round.py` keeps the README's "Drawn so far" line for the three lists. Any new list needs its source
and licence checked and recorded in the README first.

## Past both lists

A text set in the fonts can need a character neither list has (《滕王閣序》's
`鶩`, say). Draw it the same way: a batch in `work/`, the sheet beside
characters of the same structure, `edges.py`, the design proof agreed first.
Check its form against its own standard, looked at, never traced. Merge with
the same ROWS as the last round (`merge_round.py 4823 NEW_VERSION batch.py`):
the rows' counts stay as they are, since they count only the rows' own
characters, and the README's "Past both lists" paragraph names each one and
the text it is for. `round_proof.py` and `open_pr.sh` are for rows; write
this proof and pull request by hand.
