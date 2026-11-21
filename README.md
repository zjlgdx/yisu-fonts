<p align="center">
  <a href="https://yisu.aixie.de">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.svg">
      <img src="docs/logo-light.svg" alt="一粟 Yisu" width="420">
    </picture>
  </a>
</p>

<p align="center">
  Three open-source fonts for Chinese and Latin, drawn a stroke at a time.<br>
  三套一筆一筆畫出來的開源字型，繁體、簡體與拉丁字母。
</p>

<p align="center">
  <a href="https://github.com/zjlgdx/yisu-fonts/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/zjlgdx/yisu-fonts?label=release&color=b3362b"></a>
  <a href="LICENSE"><img alt="Fonts: SIL OFL 1.1" src="https://img.shields.io/badge/fonts-OFL%201.1-1d1c1b"></a>
  <a href="LICENSE-MIT"><img alt="Code: MIT" src="https://img.shields.io/badge/code-MIT-1d1c1b"></a>
  <a href="https://yisu.aixie.de"><img alt="Website" src="https://img.shields.io/badge/see%20them%20write-yisu.aixie.de-d9b45a"></a>
</p>

<p align="center">
  <a href="https://github.com/zjlgdx/yisu-fonts/releases/latest"><b>Download</b></a> ·
  <a href="https://yisu.aixie.de">Website</a> ·
  <a href="README.zh-Hant.md">中文說明</a> ·
  <a href="#how-a-glyph-is-made">How they're made</a> ·
  <a href="https://github.com/zjlgdx/yisu-fonts/milestones">Roadmap</a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.png">
  <img src="docs/hero-light.png" alt="寄蜉蝣於天地，渺滄海之一粟, from 蘇軾's 《前赤壁賦》, and an English translation, set in Yisu Yinni, Huasha and Louhen">
</picture>

一粟, one grain of millet, is from 蘇軾's 《前赤壁賦》: 渺滄海之一粟. The three fonts are named for calligraphy's three images of a stroke, 如印印泥, 如錐畫沙 and 如屋漏痕, and all three are written from one set of skeletons, each with its own pen. Every outline is drawn in this repository; nothing is traced or converted from another font.

## The fonts

| | Pen | Latin | Chinese |
| --- | --- | --- | --- |
| **Yinni**<br>印泥<br><sub>the Typewriter</sub> | A round pen with slab serifs, struck through an inked ribbon | Monospaced, one width for every glyph; the zero has a dot. Draws a terminal's box drawing, blocks and Powerline separators. | 仿宋 metal type, after the Chinese typewriter's slugs. Two cells wide. |
| **Huasha**<br>畫沙<br><sub>the Ballpoint</sub> | A fine round pen leaning about 9° | Handwriting: three drawings of every lowercase letter take turns, so words read as written, not set. | A hand's 楷書: pressure that comes and goes, each stroke a little off its place. |
| **Louhen**<br>漏痕<br><sub>the Marker</sub> | A chisel nib held at 35° | Upright handwriting, thick on the downstrokes and thin across, with the same alternates. | Thick and thin from the nib, as in its Latin. |

The full names are 一粟印泥 Yisu Yinni, 一粟畫沙 Yisu Huasha and 一粟漏痕 Yisu Louhen; a Chinese menu lists the Chinese ones. Each family has a **Regular** and a **Bold**, style-linked, so an app's Bold button picks the real Bold.

## What's in them

| | Covered |
| --- | --- |
| **Chinese** | So far, every character in the first 6679 rows of [`hanzi_order.tsv`](hanzi_order.tsv): 8324 in all, Simplified and Traditional, with 26 more for the texts on the website and 31 common Hong Kong Cantonese characters (`嘅 喺 啲 咗 佢 冇 嘢 咁 諗 搵 攞 畀 …`). All of Taiwan's 4,808 common characters, the 3,500 of mainland China's first level and the 5,401 of Big5's first level, and the 3,755 of GB 2312's first level. Each in its own standard's form: Taiwan's 說, the mainland's 说. |
| **Kana** | All 182 Hiragana and Katakana: voiced and semi-voiced, small kana, the prolonged sound mark `ー` and the iteration marks. In a column `ー` stands upright and the small kana move up and to the right. |
| **Punctuation** | Full-width `。，、；：？！「」『』（）《》〈〉・`, set as Taiwan sets it, or as the mainland does in text tagged Simplified Chinese; forms for vertical text. |
| **Zhuyin** | All 37 symbols of 注音符號, the Ministry's four extra, and the tone marks. |
| **Latin** | ASCII, Latin-1 and all of Latin Extended-A: Western, Central European, Baltic, Turkish, Maltese, Welsh and Esperanto, and Romanian `Ș Ț`. Combining marks for any letter. |
| **Symbols** | Currency, math, arrows, check marks. |
| **Terminal** (Yinni only) | Box drawing and block elements made to the cell, the marks Claude Code prints, and Powerline's separators. Programming ligatures `->` `<-` `=>` `!=` `<=` `>=`, still two cells wide, off unless you turn on `dlig` (`font-feature = +dlig` in Ghostty, `"editor.fontLigatures": "'dlig'"` in VS Code). |

Not yet: Greek, Cyrillic, Vietnamese as precomposed letters, and Chinese past the lists above. Text the fonts don't have falls back to another font.

<img src="docs/specimen.png" width="720" alt="Yisu Huasha, Louhen and Yinni: spacing strings, kerning pairs, accented letters, symbols, Bold, and Yinni as a terminal">

## Install

Download the fonts from the [latest release](https://github.com/zjlgdx/yisu-fonts/releases/latest): `.otf` to install, `.woff2` for the web. Install both weights of a family.

- **macOS**: double-click each `.otf` and choose Install Font.
- **Windows**: right-click each `.otf` and choose Install.
- **Linux**: copy them to `~/.local/share/fonts` and run `fc-cache -f`.

On the web:

```css
@font-face { font-family: 'Yisu Huasha'; src: url(YisuHuasha-Regular.woff2) format('woff2'); font-weight: 400; }
@font-face { font-family: 'Yisu Huasha'; src: url(YisuHuasha-Bold.woff2) format('woff2'); font-weight: 700; }
```

Shared characters take Taiwan's forms. Tag Simplified Chinese text with `lang="zh-Hans"` (or `zh-CN`) and the fonts switch to the mainland's forms and punctuation. In a terminal, set Yisu Yinni with a line height of 1.0 so box drawing joins.

## How a glyph is made

1. `skeleton.py` holds each letter's centre line as an SVG path on a 1000-unit canvas, with y pointing down. An accented letter is its base letter's skeleton plus a mark; a few letters (`Ø Ð Đ Ħ Ł Ŧ Ŀ` and their lowercase, `¢`) are a base letter plus a stroke. The same placement gives the combining marks their anchors.
2. `build.py` draws that line with a pen on a large bitmap: a round pen, a chisel nib, or a round pen plus slab serifs and ribbon ink. A closed path ending in `F` is filled as well as drawn (`● ■ ▶`).
3. potrace traces the bitmap back into curves, which become a CFF outline. The whole font is then lifted by its pen's reach below the skeleton's baseline, so flat letters stand on it.
4. The glyph is spaced from its own profile, kerned against every other glyph, and written out. In the `.otf`, shared runs of outline become CFF subroutines (`cffsubr`); the `.woff2` leaves them out, since Brotli compresses plain outlines smaller.
5. The Bold draws the same skeletons with a wider pen, and goes through steps 3 and 4 again.
6. `cells.py` builds Yinni's box drawing, block elements and Powerline separators as exact rectangles, triangles and quarter circles, with no pen and no ribbon.
7. Chinese (`hanzi.py`, with the characters in `hanzi_strokes.py`) is centre lines too, built in three layers. Strokes (筆畫) each carry how the pen moves along them: lighter where 撇 and 提 lift, pressed then lifted in 捺, lifted at a hook's tip. Components (部件) are made of strokes, and characters of components placed in boxes. A component scales into its box but the pen doesn't, so every stroke keeps one weight. Each family's cut (`hanzi.CUTS`) then writes it: the pen, its pressure along each kind of stroke, how far horizontals climb (Yinni 5.5°, Huasha 4.5°, Louhen 3°), the lean (Huasha's 4°, to sit with its Latin), and how much each stroke strays. Yinni's ribbon inks it like any other key.

## Build them

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
brew install potrace
.venv/bin/python build.py      # out/*.otf and out/*.woff2, Regular and Bold
.venv/bin/python audit.py      # overshoot, stems, spacing, contours, metrics
.venv/bin/python sheet.py      # out/sheet.png: spacing, kerning, alternates and the character set, shaped by Chrome
.venv/bin/python sheet.py docs/specimen.png
.venv/bin/python tools/readme_art.py   # docs/logo-*.svg and docs/hero-*.png, from out/
```

[AGENTS.md](AGENTS.md) says how to work on the fonts, and `tools/` takes a round of Chinese from draft to release.

Two scripts serve the [Pinboard](https://github.com/zjlgdx/claude-theme-pinboard) theme. Each reads the words to draw as JSON on stdin:

- `outline.py` writes those letters as compact SVG outlines, with the fonts' advances and kerning. Claude's desktop app won't load a font inside a backdrop SVG, so Pinboard draws its labels from these paths.
- `subset.py` cuts the fonts down to those letters, as WOFF2 data URIs, for a surface that does load embedded fonts.

## Which characters, in what order

Characters are drawn most frequent first, in the order in [`hanzi_order.tsv`](hanzi_order.tsv). `order.py` makes it from the Unicode Han Database ([Unihan](https://www.unicode.org/reports/tr38/), Unicode License v3), facts about characters only. It ranks by kHanyuPinlu, each character's count in the corpus of 《現代漢語頻率詞典》 (1.8 million characters). Each Simplified character's Traditional forms share its row: its kTraditionalVariant forms that are in the first plane of CNS 11643 (kIRG_TSource T1), Taiwan's common characters. The first 6,679 rows are 8,324 characters across both scripts, and cover 100.0% of the corpus.

The corpus list ends at row 2,849. After it, with a count of 0, come the characters the fonts still owed: the rest of the first level of mainland China's 通用规范汉字表 (Unihan kTGH, index 1–3500), and the rest of Taiwan's 常用國字標準字體表, the Ministry of Education's 4,808 common characters (1982). They are sorted by radical, then strokes (kRSUnicode), so one round draws a radical's family. A character only Taiwan's list has gets `-` for a Simplified form the first level doesn't hold. The 4,808 are in [`moe_4808.tsv`](moe_4808.tsv): each one's MOE number and code point, from the [Wikisource transcription](https://zh.wikisource.org/wiki/常用國字標準字體表), public domain under Article 9 of Taiwan's Copyright Act, checked against the Ministry's own list (`4808.pdf`, 2026): the same code points in the same order. Number A02149 is coded 汩 there but printed 汨, so both are drawn. Rows 4,824–5,364 are the rest of the first level of Big5 (Unihan kBigFive A440–C67E): its 5,401 common characters, the Traditional set of text from older systems, sorted the same way. Their Simplified column holds the mainland's form when 通用规范汉字表 lists it at any level and it has no row of its own; otherwise `-`. Drawn so far: 4,808 of Taiwan's 4,808, 3,500 of the first level's 3,500 and 5,401 of Big5's 5,401. Rows 5,365–5,489 are the rest of the first level of GB 2312 (Unihan kGB0, rows 16–55), the Simplified set of text from older systems: 125 characters, mostly chemistry and place names (胺 醛 邯), that the corpus and 通用规范汉字表's first level leave out. All 3,755 are drawn. Rows 5,490–7,183 are the rest of 通用规范汉字表's second level (Unihan kTGH, index 3501–6500): 3,000 more characters for names, places, science and literary words. Their Traditional forms are rarer, so a form counts as Taiwan's there when it is in either of CNS 11643's first two planes (kIRG_TSource T1 or T2). Of the second level's 3,000, 2,497 are drawn so far.

Past both lists, a character is drawn when a text set in the fonts needs it. There are 26 so far, in their Traditional forms: `禊 暎 俛` for 王羲之's 《蘭亭集序》, `蜉 蝣` for 蘇軾's 《前赤壁賦》, and `軫 棨 襜 驂 騑 闥 甍 紆 舸 舳 鶩 遄 睢 鄴 睇 眄 溟 閽 愨 笏 滕` for 王勃's 《滕王閣序》. Five of them, `甍 紆 睢 鄴 滕`, are in Big5 and so are also rows past 4,823, drawn ahead of their round; the rest are not rows of `hanzi_order.tsv`. The rows' count above leaves all 26 out until a round reaches them.

Zhuyin follows the Ministry of Education's 《國語注音符號手冊》 ([digital edition](https://language.moe.gov.tw/001/Upload/files/site_content/M0001/juyin/html_ch/index.html), CC BY-ND 3.0 TW), looked at, not traced or measured: its stroke counts and notes (末筆不鉤, 末筆不捺, ㄡ 左上不封口 …), drawn again in each family's own strokes; the handbook's stroke animations are not used.

<details>
<summary><b>The full character set</b></summary>

All three fonts cover:

- ASCII, Latin-1 and Windows-1252: every accented letter of Western European languages (`À`–`ÿ`, `Š š Ž ž Ÿ Œ œ`), `Æ Ð Ø Þ ß æ ð ø þ ı`, and the punctuation and signs `¡ ¿ « » ‹ › ‚ „ † ‡ ‰ § ¶ © ® ™ ª º ¹ ² ³ ¼ ½ ¾ ¦ ¤ ƒ`, plus `… ° • ·`, curly quotes, dashes and a no-break space
- Latin Extended-A, the whole block (U+0100–017F), for Central European, Baltic, Turkish, Maltese, Welsh and Esperanto: `Ą Ć Č Ď Ę Ě Ğ Ģ Ħ İ Ķ Ł Ľ Ń Ő Ř Ś Ş Ţ Ů Ű Ź Ż Ŋ Ĳ` and their lowercase, plus Romanian `Ș ș Ț ț` and dotless `ȷ`
- combining marks (U+0300–0328 as Latin uses them: grave, acute, circumflex, tilde, macron, breve, dot, diaeresis, ring, double acute, caron, turned comma, comma below, cedilla, ogonek), placed on any letter by anchors and stacked on each other, above the letter and below it, with `◌` to show one alone; and the spacing accents `´ ¨ ¯ ¸ ˆ ˜ ˘ ˚ ˛ ˝` (`ˇ ˙` are Zhuyin's tone marks, below)
- currency: `$ ¢ £ ¥ €`
- math: `+ − × ÷ ± = ≠ ≈ < > ≤ ≥ ¬`, all on one width
- arrows and marks: `← → ↑ ↓ ↔ ↕ ✓ ✗ ● ○`
- Chinese, the rows and texts above (`的 一 了 是 不 我 在 有 人 这/這 他 们/們 …`), and the full-width punctuation `。，、；：？！「」『』（）《》〈〉・`, with its forms for vertical text (`﹁﹂﹃﹄︵︶︽︾︿﹀`)
- Zhuyin (注音符號, Bopomofo): the 37 symbols `ㄅ`–`ㄩ` (U+3105–3129), the four the Ministry's chart adds, `ㄪ ㄫ ㄬ` (國音不用) and `ㄭ` (空韻), and the tone marks `ˉ ˊ ˇ ˋ ˙`. A symbol is set on the full em, as East Asian Wide, and drawn about three quarters the size of a character, so a line of 注音 is lighter than the characters it spells. `ㄧ` lies flat, as the handbook writes it in both directions. The tone marks are half a symbol tall, up by the top of the symbols, with `ˇ` a check mark; they take half an em (one cell in Yinni, as their East Asian Width A), so `ㄓㄨˋ` sets tight.

Yinni adds what a terminal draws:

- box drawing, the whole block (U+2500–257F): light, heavy and double lines, rounded corners `╭ ╮ ╰ ╯`, dashes and diagonals
- block elements, the whole block (U+2580–259F): halves, eighths, quadrants and shades `░ ▒ ▓`
- the marks Claude Code prints: `❯ ⏺ ⎿ ✻ ✽ ✶ ✳ ✢ ✓ ✔ ✗ ✘ ⏵ ⏸ ☐ ☒ ☑`, and `■ □ ◼ ◻ ▪ ▫ ◆ ◇ ▶ ◀ ▲ ▼ ▸ ◯ ◉ ⚠ ↵ ⏎ ⌘ ⌥ ⌃ ⇧ ∗ ↯ ★ ☆ ✦ ✧ ⧉ ⇅ ⎋ ⋯ ※ ➜ ⌫ ⚡`
- Powerline's separators (U+E0B0–E0B3), made to the cell so a prompt's segments join, and its branch, line-number and padlock marks (U+E0A0–E0A2)

Box drawing and blocks fill the whole cell, 600 units wide and the full 1.24 em line high, so lines join across columns and rows when the terminal's line height is 1.0 (the font's own line).

</details>

<details>
<summary><b>The type-design rules they follow</b></summary>

| Rule | How | Source |
| --- | --- | --- |
| Round shapes overshoot the lines they meet, by 1–3% | Curved parts of a skeleton are pushed 12 units past the baseline, x-height, cap height, ascender and descender. Jitter is kept smaller than that. | [Microsoft: lowercase](https://learn.microsoft.com/en-us/typography/develop/character-design-standards/lowercase), [uppercase](https://learn.microsoft.com/en-us/typography/develop/character-design-standards/uppercase) |
| Flat strokes stand on the baseline | A skeleton's lines are where the pen's centre runs, so the ink of a flat stroke reaches half a stroke past them: below the baseline, above the x-height and cap height. Each font is lifted by how far its own pen reaches below (the median foot of `x z H E I L T n m h u`), so flat feet stand on 0 within the hand's jitter, round ones overshoot below it, and every height is measured from the ink. Spacing, kerning and mark positions are unchanged by the lift. | [Microsoft: lowercase](https://learn.microsoft.com/en-us/typography/develop/character-design-standards/lowercase), [OpenType: OS/2 sxHeight](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#sxheight) |
| Horizontals slightly lighter than verticals | The round pens are 7% flatter than round. The chisel nib does this by its angle. | [Typographica: optics in type design](https://typographica.org/on-typography/is-what-i-see-what-i-get-math-and-optics-in-type-design) |
| Space from shape: straight sides get the most, round sides less, open and diagonal sides least | Each side's average white over the x-height (or cap height) zone, at most 15% of the x-height deep, comes off a per-style target. A straight n side is about a third of n's counter, and o comes out at about 0.8 of n. A slanted letter is measured with its lean taken out. | [Glyphs: spacing](https://glyphsapp.com/learn/spacing) |
| Kern after spacing, only where two shapes leave a hole | Closest approach on the rows both letters share, against their spacing sidebearings, half the excess closed. Lowercase pairs capped at −40. | [Glyphs: spacing](https://glyphsapp.com/learn/spacing) |
| Kerning never makes shapes touch | Over every row both glyphs ink, tails and accents included, a kerned pair keeps at least 12 units of white. A pair that would collide unkerned (`qj`, `jj`) is spaced apart instead. | |
| Accented letters reuse their base letter | `é` is `e`'s own drawing plus an acute: same width, same sidebearings, and `e`'s kerning class. Where the accent alone would collide (`T` over `ï`), a glyph pair overrides the class. `i` and `j` take the dotless form under a mark. | [Glyphs: diacritics](https://glyphsapp.com/learn/diacritics) |
| Marks sit clear of the letter, and scale with the pen | A mark's foot sits a fixed gap above the overshoot, measured from where the pen's ink ends, so a heavier pen lifts it. Capital marks are flatter, so they fit under the line's ascender. Rings and cedillas grow with the pen so their eye and curl stay open. | [Microsoft: diacritics](https://learn.microsoft.com/en-us/typography/develop/character-design-standards/diacritics) |
| Each language's own form of a mark | Latvian `Ģ Ķ Ļ Ņ Ŗ` and Romanian `Ș Ț` take a comma below, Latvian `ģ` a turned comma above; Turkish `Ş Ţ` keep the cedilla. Czech and Slovak `ď ľ ť Ľ` take an apostrophe beside the stem, and the letter widens by what it adds. An ogonek grows from the stem or curve it hangs on, and `į` keeps its dot. | [Diacritics project](https://diacritics.typo.cz/) |
| Combining marks attach by anchors | Every letter has `top`, `bottom`, `cedilla` and `ogonek` anchors where the same code puts its precomposed marks, carried through the hand's own lean and jitter, so `x́` sits as `á` does. Marks have no width and are GDEF marks. `ccmp` drops the dot of `i` and `j` under a mark above and swaps in a flatter `.case` mark over a capital; `mkmk` stacks marks: above a letter, each on the one before; below it, a comma below hangs under the cedilla, ogonek or comma before it (or the one ş ą ţ already carry), whatever marks above come between; `calt` and `kern` look through them. | [OpenType: GPOS mark-to-base](https://learn.microsoft.com/en-us/typography/opentype/spec/gpos#lookup-type-4-mark-to-base-attachment-positioning-subtable), [Glyphs: diacritics](https://glyphsapp.com/learn/diacritics) |
| Legacy (spacing) accents are not marks | `´ ¨ ¯ ¸ ˆ ˜ ˇ ˘ ˙ ˚ ˛ ˝` have width and no anchors (`ˇ ˙` drawn as Zhuyin's tones). | Fontbakery `legacy_accents` |
| A Bold is a weight of the same design | Same skeletons, a wider pen: stems 1.4 to 1.6 times the Regular's (Huasha 48 → 77, Louhen 88 → 123, Yinni 62 → 96 units). The handwriting widens 8% so counters stay open, and Yinni's serifs give back a little so `m`'s feet stay apart. Spaced and kerned from its own outlines. | |
| Style-linked weights | Regular: `usWeightClass` 400, fsSelection REGULAR. Bold: 700, fsSelection BOLD, `head.macStyle` bold. Both share the family name, with the weight as subfamily (RIBBI), and share vertical metrics and underline, so lines don't jump between weights. | [OpenType: OS/2](https://learn.microsoft.com/en-us/typography/opentype/spec/os2), [Google Fonts: naming](https://googlefonts.github.io/gf-guide/statics.html) |
| Math signs share one width | `+ = < > × ~` are centred in one width. | Fontbakery `math_signs_width` |
| Monospace: one advance for every glyph, narrow letters widened, wide ones squeezed | Yinni: 600 everywhere, `.notdef` and box drawing included; combining marks are zero width, as a terminal expects, and hang over the cell before them. Symbols keep their proportions and only shrink to fit. `post.isFixedPitch` is set and PANOSE proportion is 9. | [Google Fonts requirements](https://googlefonts.github.io/gf-guide/requirements.html) |
| Box drawing joins | Lines are centred on the cell and run to its edges: 0 and 600 across, the typo descender and ascender up and down. Light lines are as heavy as a stem, heavy lines 1.9 times that. Double lines turn corners on their inner and outer lines. | [Unicode: box drawing](https://www.unicode.org/charts/PDF/U2500.pdf) |
| Chinese takes two cells and matches the Latin | In Yinni, characters of East Asian Width W and F advance two cells, 1200 units, and a character's face is 1060 units high (954 wide, as 仿宋 is narrow). In Huasha and Louhen, Chinese advances one em, 1000 units, with a face of 900 and 940. The face is centred in its advance and on the capitals. Bold writes Chinese with a lighter pen than its Latin (0.76 of it in Yinni, 0.85 in Huasha, 0.82 of Louhen's nib), so dense characters (國, 我) stay open. Chinese is not kerned. Full-width punctuation sits as Taiwan sets it by default: `。，、` in the middle of the box, `「」（）` against the text. In text tagged Simplified Chinese (`zh-Hans`, `zh-CN`), OpenType `locl` (script `hani`, language `ZHS`) sets `。，、` in the box's lower left and `；：？！` in its left half, as mainland China does; a terminal doesn't tag text, so it shows Taiwan's. Each script's own forms are drawn: Taiwan's 說 has 八 over 兄, mainland China's 说 has 丷. Chinese is left unhinted, since the Latin's blue zones would pull its strokes. Yinni's `xAvgCharWidth` stays one cell, as terminals size their cell by it. | [Unicode UAX #11](https://www.unicode.org/reports/tr11/), [W3C: Requirements for Chinese Text Layout](https://www.w3.org/TR/clreq/) |
| Marks that meet give up the blank half between them | A full-width mark's ink sits in half of its box: an opening mark `「『（《〈` in the right half, a closing mark `」』）》〉` in the left. With `chws`, a closing mark before another closing mark or an opening one loses its blank right half, and opening marks in a row lose the blank half between them (`」（` and `「『` close up). In text tagged Simplified Chinese the `locl` forms of `。，、；：？！` sit in the left half, so they close up the same way (`：「`, `。」`). In Yinni half a mark is 600 units, one cell, so a line set with `chws` stays on the grid. Huasha and Louhen also take a quarter off a centred Taiwan mark's side that faces a bracket (`：「`, `』。`). `halt` sets every mark half-width, for headings and tables. `vchw` and `vhal` do the same along a column (see the next rule). Browsers apply `chws` to CJK text by default (`text-spacing-trim`); terminals keep every character on its cells. | [W3C: Requirements for Japanese Text Layout](https://www.w3.org/TR/jlreq/), [W3C: Requirements for Chinese Text Layout](https://www.w3.org/TR/clreq/), [OpenType: chws](https://learn.microsoft.com/en-us/typography/opentype/spec/features_ae#tag-chws) |
| Chinese sets in a column | Every glyph is one em tall in vertical text (1200 units in Yinni, 1000 in the others; `vhea`, `vmtx`), and the vertical origin (`VORG`) is the top of the frame hanzi are drawn in, so they sit in a column as in a line. `vert` turns the brackets a quarter clockwise, `「」『』（）《》〈〉` to `﹁﹂﹃﹄︵︶︽︾︿﹀`: the opening one sits low in its em, against the character below, the closing one high. Each is written by the family's pen in a hand's stroke order (﹁ as 橫折, ﹂ as 豎折), not turned, so the pen's pressure and Louhen's chisel fall as they would writing a column, and each answers its own code point too (U+FE35–FE44). Taiwan keeps `。，、；：？！` centred and upright in a column, the same glyphs as in a line (重訂標點符號手冊). In text tagged Simplified Chinese they are set 置于相应文字之下偏右 (GB/T 15834-2011, 5.2.1): `。，、：；` in the upper right of the frame, and `？！`, as tall as a character, moved right. `vchw` is `chws` along the column, with the same quarter for Taiwan's marks in Huasha and Louhen; in Yinni half a mark is one cell, so a column stays on the grid. `vhal` sets every mark half-tall. | [教育部: 重訂標點符號手冊](https://language.moe.gov.tw/001/Upload/files/SITE_CONTENT/M0001/HAU/haushou.htm), [W3C: GB/T 15834-2011 §5 in English](https://www.w3.org/zh-hans/news/2013/translation-of-gb-t-15834-2011-part-5/), [OpenType: vert](https://learn.microsoft.com/en-us/typography/opentype/spec/features_uz#tag-vert), [OpenType: vchw](https://learn.microsoft.com/en-us/typography/opentype/spec/features_uz#tag-vchw) |
| A shared character takes Taiwan's form, the mainland's where text is Simplified | A character both scripts write with one code point is drawn in the form of Taiwan's 教育部 standard: 艹 in four strokes (十十, the 一 broken in the middle), 者 with its 點, 敖 with 方's 點, 戶 with a 平撇 on top. Where text is tagged Simplified Chinese, `locl` (language ZHS) gives the mainland's form of those parts (艹 in three, 者 and 敖 without the 點, 户 with a 點), as 通用规范汉字表 writes them, so 花 草 者 偏 read right in each. A character only one script has is drawn in that script's form. | [常用國字標準字體表 (Wikisource)](https://zh.wikisource.org/wiki/常用國字標準字體表), [OpenType: locl](https://learn.microsoft.com/en-us/typography/opentype/spec/features_ko#tag-locl) |
| Symbols read at terminal sizes | In Yinni, arrows run nearly the cell's width (`← →`) or the cap height (`↑ ↓`), with heads at 45°; `© ®` are ovals as tall as a capital, since a circle that fits the cell is far shorter; `™` hangs from the cap height and fills the cell; `✗` covers what `✓` covers. Arrows, `✓` and `✗` take a pen 1.2 times as heavy, so `✗` doesn't read as `x`. | |
| Tell 0 from O, and 1 from l from I, in a monospace | Yinni's zero has a dot. 1 has a flag and foot, l a tail, I two slabs. | |
| Outer contours counter-clockwise, no overlaps, points at extremes | potrace gives non-overlapping, correctly wound contours, and box-drawing pieces are merged into one outline. `ExtremaPen` splits every curve at its extremes. No contour is under 400 units²: a counter the Bold pen all but closes is filled. | [Adobe Type 1 spec §3.5, §4.1](https://adobe-type-tools.github.io/font-tech-notes/pdfs/T1_SPEC.pdf), [Glyphs: drawing good paths](https://glyphsapp.com/learn/drawing-good-paths) |
| Vertical metrics | `USE_TYPO_METRICS` is on, hhea equals typo, line gap 0. The line is 1.24 em with the caps centred in it, the same in both weights. The typo ascender clears `À`. The win metrics are the family's bounds. The underscore hangs 40 units under the baseline, clear of round letters' overshoot whatever the pen, and the Regular's underscore gives both weights their underline. | [Google Fonts: vertical metrics](https://googlefonts.github.io/gf-guide/metrics.html), [OpenType: OS/2](https://learn.microsoft.com/en-us/typography/opentype/spec/os2) |
| x-height and cap height | Measured from the flat tops of x (z for Huasha) and H, whose feet stand on the baseline, so each is the ink's full height. | [OpenType: OS/2](https://learn.microsoft.com/en-us/typography/opentype/spec/os2) |
| Names and versions | Windows names only: IDs 0–6, 11 for the repository and 13/14 for the OFL. IDs 1 and 4 also in Chinese: Traditional for zh-TW, zh-HK and zh-MO, Simplified for zh-CN and zh-SG. head.fontRevision matches nameID 5. post is 3.0, as CFF fonts use. | [OpenType: name](https://learn.microsoft.com/en-us/typography/opentype/spec/name), [recommendations](https://learn.microsoft.com/en-us/typography/opentype/spec/recom) |
| Slanted handwriting | Huasha leans 9° as part of the hand, as other script fonts do. It stays a Regular with italicAngle 0, so it needs no upright partner. | Fontbakery `italic_angle` |

The handwriting fonts carry two alternates of every lowercase letter, accented ones included, cycled by `calt`. In "bookkeeper" the two o's, the two k's and the e's are each drawn differently.

</details>

## Checks

`fontbakery check-universal`, with a family's Regular and Bold checked together, gives one FAIL, and it is deliberate: file size. `file_size` warns once a font passes 1 MB and fails it past 9 MB (`massive-font`). Every font is past 1 MB, and as the rounds add Chinese, one after another passes 9 MB: Yinni first (its Bold at 0.600), since its typed edge takes the most outline points. A set of common Chinese characters is that big. One weight of Noto Sans CJK, as an `.otf`, runs past 16 MB. The outlines are already as small as they can be without changing the strokes: integer coordinates, with shared runs as CFF subroutines. The `.woff2` web fonts are smaller still. Yinni also warns that `xAvgCharWidth` is one cell, which is deliberate (see the rules above). Fontbakery's `soft_dotted` check (from the Google Fonts profile) passes too: `i`, `j` and `į` lose their dot under any mark above. On each Yinni font one check errors: fontbakery 1.1's monospace check reads a `glyf` table, which a CFF font doesn't have. `audit.py` and the build cover what that check would test: one advance, `isFixedPitch`, PANOSE proportion 9, and `xAvgCharWidth`.

The fonts are hinted with AFDKO's `otfautohint`, from alignment zones and standard stems the build measures from the drawn glyphs (the baseline, x-height, cap height with ascenders, and descender zones; `StdVW`/`StdHW` from `l n H I h` and `H E z Z`). Windows and FreeType use the hints to snap those edges and stems to whole pixels at small sizes; macOS ignores them. Box drawing and block elements are left unhinted, so their edges stay on the cell's and rows keep joining. `subset.py` drops the hints, since the board's SVG has no use for them.

## History

The fonts were drawn for [Pinboard](https://github.com/zjlgdx/claude-theme-pinboard), a cork-board theme for Claude, and up to 0.730 were called Pinboard Typewriter, Pinboard Ballpoint and Pinboard Marker. From 0.740 the families, the files and this repository (formerly `pinboard-fonts`) carry the new names. Up to 0.510 the fonts were committed in `out/`; from 0.520 they are only on Releases, which keeps the repository small. Releases 0.430 and 0.431 had a terminal build, Pinboard Typewriter NF CN, with Chinese and icons merged in from LXGW WenKai and Nerd Fonts; it is retired, so that everything in these fonts is drawn here.

## Licence

The fonts are under the [SIL Open Font License 1.1](LICENSE): free to use, change and share, in personal and commercial work, and to bundle with software; they can't be sold on their own. The build scripts are under the [MIT License](LICENSE-MIT).
