# 星盘


## 前言

紫微斗数星盘又叫紫微斗数命盘，是由 `十二个宫位` 和一个 `中宫` 构成，宫位的 `地支` 是固定的，并且是由 `寅` 开始，而不是由 `子` 开始。这是因为农历的正月是寅月，这就是所谓的 `正月建寅`。在 `iztro` 里面，`寅宫` 的索引是 `0`，`卯宫` 的索引是 `1`，如此按照顺时针的方向排列。如下面表格所示：

|  |  |  |  |
| --- | --- | --- | --- |
| 巳 `3` | 午 `4` | 未 `5` | 申 `6` |
| 辰 `2` | 中宫 | 酉 `7` |  |
| 卯 `1` | 戌 `8` |  |  |
| 寅 `0` | 丑 `11` | 子 `10` | 亥 `9` |

`中宫` 通常可以用来展示任何你想展示的信息，一般不会对整个星盘产生影响。周围的 `十二宫` 用于存放星曜，四化，运限，宫位名称等信息。关于 `宫位` 的详细信息，可以进入 [宫位传送门](./palace.md) 查看详细介绍，本页面主要关注星盘的信息。紫微斗数星盘是由宫位和星曜组成的，如果你还没有建立起它们的概念，我们强烈推荐你进入 [基础知识扫盲](/learn/basis.md) 开始学习有趣的紫微斗数知识。

在安装好 `iztro` 依赖以后你可以用如下代码将 `星盘(astro)` 对象引入你的代码。如果你还不知道如何安装 `iztro`，请点击 [安装iztro](/quick-start.md#安装) 跳转到相关说明文档。


## `astro` 的静态方法

要使用该对象的静态方法，请先将该对象 `import` 到你的代码里

用途

获取运限数据。如果只是想获取调用时的运限数据，可以不传任何参数，该方法会获取系统当前时间进行计算。

注意

- 当 `date` 为 `YYYY-M-D` 格式的字符串而没有传 `timeIndex` 参数时，会取 `date` 当日 `早子时` 的时间点作为 `流时` 的时间
- 当 `date` 为 `YYYY-M-D HH` 格式时间或是一个 `Date` 实例而没有传 `timeIndex` 参数时，会将 `date` 里的小时转化为时辰作为 `流时` 的时间
- 当传入 `timeIndex` 参数时，会优先使用该参数定义

ts```
type horoscope = (date?: string | Date, timeIndex?: number) => FunctionalHoroscope;
```参数

| 参数 | 类型 | 是否必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| date | `string` | `Date` | `false` | `new Date()` | 阳历日期【YYYY-M-D】 |
| timeIndex | `number` | `false` | `0` | 时辰索引【0~12】 |返回值

[`FunctionalHoroscope`](./horoscope.md#functionalhoroscope)

注意

返回值已经在 `v1.3.4` 从 `Horoscope` 改为 `FunctionalHoroscope`，但使用上是向后兼容的。注意

该方法已经在 `v1.2.0` 废弃，请使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [have()](./palace.md#have) 方法代替- 用途
  
  判断某一个宫位 `三方四正` 是否包含目标 `星曜`，必须要**全部**包含才会返回 `true`
- 定义
  
  ts```
  type isSurrounded = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 参数
  
  | 参数 | 类型 | 是否必填 | 默认值 | 说明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宫位索引或者宫位名称 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名称数组 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判断 `寅宫` 三方四正是否含有 `天府` 星、`红鸾` 星和 `禄存` 星nconst palace = astrolabe.isSurrounded(0, ["天府", "红鸾", "禄存"]);nn// 判断 `命宫` 三方四正是否含有 `天府` 星、`红鸾` 星和 `禄存` 星nconst soulPalace = astrolabe.isSurrounded("命宫", ["天府", "红鸾", "禄存"]);
  ```

---

注意

该方法已经在 `v1.2.0` 废弃，请使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [haveOneOf()](./palace.md#haveoneof) 方法代替- 用途
  
  判断指定宫位 `三方四正` 内是否有传入星曜的 `其中一个`，只要命中 `一个` 就会返回 `true`
- 定义
  
  ts```
  type isSurroundedOneOf = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 参数
  
  | 参数 | 类型 | 是否必填 | 默认值 | 说明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宫位索引或者宫位名称 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名称数组 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判断 `寅宫` 三方四正是否含有 `天府` 星、`红鸾` 星和 `禄存` 星中的一颗nconst palace = astrolabe.isSurroundedOneOf(0, ["天府", "红鸾", "禄存"]);nn// 判断 `命宫` 三方四正是否含有 `天府` 星、`红鸾` 星和 `禄存` 星中的一颗nconst soulPalace = astrolabe.isSurroundedOneOf("命宫", ["天府", "红鸾", "禄存"]);
  ```

---

注意

该方法已经在 `v1.2.0` 废弃，请使用 [FunctionalSurpalaces](./palace.md#functionalsurpalaces) 的 [notHave()](./palace.md#nothave-1) 方法代替- 用途
  
  判断指定宫位 `三方四正` 是否 `不含` 目标星曜，必须要全部都 `不在` 三方四正内含才会返回 `true`
- 定义
  
  ts```
  type notSurrounded = (n  indexOrName: number | PalaceName,n  stars: StarName[]n) => boolean;
  ```
- 参数
  
  | 参数 | 类型 | 是否必填 | 默认值 | 说明 |
  | --- | --- | --- | --- | --- |
  | indexOrName | `number` | [`PalaceName`](./../type-definition.md#palacename) | `true` | - | 宫位索引或者宫位名称 |
  | stars | [`StarName[]`](./../type-definition.md#starname) | `true` | - | 星曜名称数组 |
- 返回值
  
  `boolean`
- 示例
  
  ts```
  import { astro } from "iztro";nnconst astrolabe = astro.astrolabeBySolarDate("2000-8-16", 2, "女", true, "zh-CN");nn// 判断 `寅宫` 三方四正是否不含有 `天府` 星、`红鸾` 星和 `禄存` 星nconst palace = astrolabe.notSurrounded(0, ["天府", "红鸾", "禄存"]);nn// 判断 `命宫` 三方四正是否不含有 `天府` 星、`红鸾` 星和 `禄存` 星nconst soulPalace = astrolabe.notSurrounded("命宫", ["天府", "红鸾", "禄存"]);
  ```
