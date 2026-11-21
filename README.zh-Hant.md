<p align="center">
  <a href="https://yisu.aixie.de">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.svg">
      <img src="docs/logo-light.svg" alt="一粟 Yisu" width="420">
    </picture>
  </a>
</p>

<p align="center">三套一筆一筆畫出來的開源字型：印泥、畫沙、漏痕。繁體、簡體與拉丁字母。</p>

<p align="center">
  <a href="https://github.com/zjlgdx/yisu-fonts/releases/latest"><b>下載</b></a> ·
  <a href="https://yisu.aixie.de">網站</a> ·
  <a href="README.md">English</a> ·
  <a href="https://github.com/zjlgdx/yisu-fonts/milestones">進度</a>
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.png">
  <img src="docs/hero-light.png" alt="蘇軾《前赤壁賦》「寄蜉蝣於天地，渺滄海之一粟」與英譯，分別以一粟印泥、畫沙、漏痕排出">
</picture>

「一粟」出自蘇軾《前赤壁賦》「渺滄海之一粟」。三套字型取名自書法裡形容筆畫的三個比喻：如印印泥、如錐畫沙、如屋漏痕。三套共用同一副字骨，各用各的筆寫出來。每個字形都在這個倉庫裡畫成，沒有描摹或轉換任何其他字型。

## 三套字型

| | 筆 | 漢字 | 拉丁字母 |
| --- | --- | --- | --- |
| **印泥**<br>Yinni | 圓筆加襯線，隔著色帶打上去 | 仿宋，像中文打字機的鉛字；佔兩格 | 等寬，零中間有點；另有終端機用的框線、方塊與 Powerline 符號 |
| **畫沙**<br>Huasha | 細圓珠筆，斜約 9° | 手寫楷書，筆壓有輕有重，每筆略有偏差 | 手寫體，每個小寫字母有三種寫法輪流出現 |
| **漏痕**<br>Louhen | 斜切的麥克筆，握在 35° | 粗細由筆尖角度而來 | 直立的手寫體，直筆粗、橫筆細 |

全名是一粟印泥 Yisu Yinni、一粟畫沙 Yisu Huasha、一粟漏痕 Yisu Louhen。每套都有 Regular 和 Bold 兩種粗細，共六個字型。

## 收字

- **漢字**：<!-- hanzi -->7,520<!-- /hanzi --> 個，繁體與簡體。教育部常用國字 4,808 字、《通用规范汉字表》一級 3,500 字、Big5 常用字 5,401 字、GB 2312 一級字 3,755 字都已收齊，另有網站上幾篇文章用到的 26 字，和香港常用的粵語字 31 個（`嘅 喺 啲 咗 佢 冇 嘢 咁 諗 搵 攞 畀 …`）。各依自己的標準字形：台灣的「說」、大陸的「说」。
- **日文假名**：平假名、片假名共 182 個，含濁音、半濁音、小假名、長音符號 `ー` 和疊字號；直排時 `ー` 豎起、小假名移到右上。
- **標點**：全形標點，預設照台灣的位置；標成簡體中文的文字改用大陸的位置。直排標點也有。
- **注音符號**：37 個符號、教育部表上另外 4 個，以及聲調符號。
- **拉丁字母**：ASCII、Latin-1 與整個 Latin Extended-A，可組合的附加符號。
- **符號**：貨幣、數學、箭頭、勾叉；印泥另有終端機用的框線和方塊，以及程式連字 `->` `<-` `=>` `!=` `<=` `>=`（仍占兩格，預設關閉，打開 `dlig` 才有，例如 Ghostty 的 `font-feature = +dlig`）。

## 安裝與使用

到[最新版本](https://github.com/zjlgdx/yisu-fonts/releases/latest)下載：`.otf` 用來安裝，`.woff2` 用在網頁。一套字型請兩種粗細都裝。

- **macOS**：雙擊 `.otf`，按「安裝字體」。
- **Windows**：在 `.otf` 上按右鍵，選「安裝」。
- **Linux**：複製到 `~/.local/share/fonts`，再執行 `fc-cache -f`。

網頁：

```css
@font-face { font-family: 'Yisu Huasha'; src: url(YisuHuasha-Regular.woff2) format('woff2'); font-weight: 400; }
@font-face { font-family: 'Yisu Huasha'; src: url(YisuHuasha-Bold.woff2) format('woff2'); font-weight: 700; }
```

兩岸共用的字預設是台灣字形（例如「花」的艹寫四筆）。簡體文字請標上 `lang="zh-Hans"` 或 `zh-CN`，字型會換成大陸的字形和標點位置。

字型怎麼畫、怎麼建置、遵循哪些排版規則，請看[英文說明](README.md)。

## 授權

字型採用 [SIL Open Font License 1.1](LICENSE)：個人與商業用途都可以免費使用、修改、再散布，也可以隨軟體一起發佈，但不能單獨販售字型本身。建置程式採用 [MIT License](LICENSE-MIT)。
