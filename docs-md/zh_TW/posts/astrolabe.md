# 星盤


## 前言

紫微鬥數星盤又叫紫微鬥數命盤，是由 `十二個宮位` 和壹個 `中宮` 構成，宮位的 `地支` 是固定的，並且是由 `寅` 開始，而不是由 `子` 開始。這是因為農歷的正月是寅月，這就是所謂的 `正月建寅`。在 `iztro` 裏面，`寅宮` 的索引是 `0`，`卯宮` 的索引是 `1`，如此按照順時針的方向排列。如下面表格所示：

|  |  |  |  |
| --- | --- | --- | --- |
| 巳 `3` | 午 `4` | 未 `5` | 申 `6` |
| 辰 `2` | 中宮 | 酉 `7` |  |
| 卯 `1` | 戌 `8` |  |  |
| 寅 `0` | 丑 `11` | 子 `10` | 亥 `9` |

`中宮` 通常可以用來展示任何妳想展示的信息，壹般不會對整個星盤產生影響。周圍的 `十二宮` 用於存放星曜，四化，運限，宮位名稱等信息。關於 `宮位` 的詳細信息，可以進入 [紫微鬥數宮位](./palace.md) 查看詳細介紹，本頁面主要關註星盤的信息。紫微鬥數星盤是由宮位和星曜組成的，如果妳還沒有建立起它們的概念，我們強烈推薦妳進入 [紫微鬥數基礎](/learn/basis.md) 開始學習有趣的紫微鬥數知識。

在安裝好 `iztro` 依賴以後妳可以用如下代碼將 `星盤(astro)` 對象引入妳的代碼。如果妳還不知道如何安裝 `iztro`，請點擊 [傳送門](/quick-start.md#安裝) 跳轉到相關說明文檔。


## `astro` 的靜態方法

要使用該對象的靜態方法，請先將該對象 `import` 到妳的代碼裏

用途

獲取運限數據。如果隻是想獲取調用時的運限數據，可以不傳任何參數，該方法會獲取係統當前時間進行計算。

註意

- 當 `date` 為 `YYYY-M-D` 格式的字符串而沒有傳 `timeIndex` 參數時，會取 `date` 當日 `早子時` 的時間點作為 `流時` 的時間
- 當 `date` 為 `YYYY-M-D HH` 格式時間或是壹個 `Date` 實例而沒有傳 `timeIndex` 參數時，會將 `date` 裏的小時轉化為時辰作為 `流時` 的時間
- 當傳入 `timeIndex` 參數時，會優先使用該參數定義

ts```
type horoscope = (date?: string | Date, timeIndex?: number) => Horoscope;
```參數

| 參數 | 類型 | 是否必填 | 默認值 | 說明 |
| --- | --- | --- | --- | --- |
| date | `string` | `Date` | `false` | `new Date()` | 陽歷日期【YYYY-M-D】 |
| timeIndex | `number` | `false` | `0` | 時辰索引【0~12】 |返回值

[`Horoscope`](./../type-definition.md#horoscope)註意

該方法已經在 `v1.2.0` 廢棄，請使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [have()](./palace.md#have) 方法代替- 用途
  
  判斷某壹個宮位 `三方四正` 是否包含目標 `星曜`，必須要**全部**包含才會返回 `true`
- 定義
  
  ts```
  type isSurrounded = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 參數
  
  | 參數 | 類型 | 是否必填 | 默認值 | 說明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宮位索引或者宮位名稱 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名稱數組 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判斷 `寅宮` 三方四正是否含有 `天府` 星、`紅鸞` 星和 `祿存` 星nconst palace = astrolabe.isSurrounded(0, ["天府", "紅鸞", "祿存"]);nn// 判斷 `命宮` 三方四正是否含有 `天府` 星、`紅鸞` 星和 `祿存` 星nconst soulPalace = astrolabe.isSurrounded("命宮", ["天府", "紅鸞", "祿存"]);
  ```

---

註意

該方法已經在 `v1.2.0` 廢棄，請使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [haveOneOf()](./palace.md#haveoneof) 方法代替- 用途
  
  判斷指定宮位 `三方四正` 內是否有傳入星曜的 `其中壹個`，隻要命中 `壹個` 就會返回 `true`
- 定義
  
  ts```
  type isSurroundedOneOf = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 參數
  
  | 參數 | 類型 | 是否必填 | 默認值 | 說明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宮位索引或者宮位名稱 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名稱數組 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判斷 `寅宮` 三方四正是否含有 `天府` 星、`紅鸞` 星和 `祿存` 星中的壹顆nconst palace = astrolabe.isSurroundedOneOf(0, ["天府", "紅鸞", "祿存"]);nn// 判斷 `命宮` 三方四正是否含有 `天府` 星、`紅鸞` 星和 `祿存` 星中的壹顆nconst soulPalace = astrolabe.isSurroundedOneOf("命宮", ["天府", "紅鸞", "祿存"]);
  ```

---

註意

該方法已經在 `v1.2.0` 廢棄，請使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [notHave()](./palace.md#nothave-1) 方法代替- 用途
  
  判斷指定宮位 `三方四正` 是否 `不含` 目標星曜，必須要全部都 `不在` 三方四正內含才會返回 `true`
- 定義
  
  ts```
  type notSurrounded = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 參數
  
  | 參數 | 類型 | 是否必填 | 默認值 | 說明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宮位索引或者宮位名稱 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名稱數組 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判斷 `寅宮` 三方四正是否不含有 `天府` 星、`紅鸞` 星和 `祿存` 星nconst palace = astrolabe.notSurrounded(0, ["天府", "紅鸞", "祿存"]);nn// 判斷 `命宮` 三方四正是否不含有 `天府` 星、`紅鸞` 星和 `祿存` 星nconst soulPalace = astrolabe.notSurrounded("命宮", ["天府", "紅鸞", "祿存"]);
  ```
