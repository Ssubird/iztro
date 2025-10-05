# IZTRO

一套轻量级获取紫微斗数排盘信息的 Javascript 开源库。
## 前言

欢迎使用 `iztro` 开发文档！本页将向你介绍如何集成、如何获取数据、以及如何快速得到紫微斗数里一张星盘上的所有数据。如果你只是基础使用者，阅读完本篇文档将足够你日常使用。 如果你已经掌握了本页内容，可以到其他页面进行更深入的探索。如果你对紫微斗数感兴趣，但是有没有相关基础，可以点击 [基础知识扫盲](/learn/basis.md) 进行扫盲学习。

你将获取到以下信息：

- 如何将 `iztro` 安装和集成到你的代码里
- 如何获取到一张星盘
- 如何基于星盘开始分析宫位
- 如何基于宫位开始分析星曜
## 产品

|  | 名称 | 链接 | 语言 | 作者 |
| --- | --- | --- | --- | --- |
| ![iztro](https://img.shields.io/github/stars/sylarlong/iztro.svg?style=social&label=Star) | iztro | [GitHub](https://github.com/sylarlong/iztro) ｜ [Gitee](https://gitee.com/sylarlong/iztro) | Typescript | [SylarLong](https://github.com/SylarLong) |
| ![react-iztro](https://img.shields.io/github/stars/sylarlong/react-iztro.svg?style=social&label=Star) | react-iztro | [GitHub](https://github.com/sylarlong/react-iztro) ｜ [Gitee](https://gitee.com/sylarlong/react-iztro) | React | [SylarLong](https://github.com/SylarLong) |
| ![iztro-hook](https://img.shields.io/github/stars/sylarlong/iztro-hook.svg?style=social&label=Star) | iztro-hook | [GitHub](https://github.com/sylarlong/iztro-hook) ｜ [Gitee](https://gitee.com/sylarlong/iztro-hook) | React | [SylarLong](https://github.com/SylarLong) |
| ![py-iztro](https://img.shields.io/github/stars/x-haose/py-iztro.svg?style=social&label=Star) | py-iztro | [GitHub](https://github.com/x-haose/py-iztro) ｜ [Gitee](https://gitee.com/x-haose/py-iztro) | Python | [昊色居士](https://github.com/x-haose) |
| ![py-iztro](https://img.shields.io/github/stars/EdwinXiang/dart_iztro.svg?style=social&label=Star) | dart_iztro | [GitHub](https://github.com/EdwinXiang/dart_iztro) ｜ [Gitee](https://gitee.com/EdwinXiang/dart_iztro) | Dart | [EdwinXiang](https://github.com/EdwinXiang) |


## 安装


### 使用包管理安装

你可以使用任意一种你熟悉的包管理工具进行安装

在 `v2.0.4` 版本以后，编译了 `umd` 的纯Javascript库。可以下载 [release](https://github.com/SylarLong/iztro/releases) 资源文件中的 `🗜️iztro-min-js.tar.gz` 压缩包，里面包含了一个 `iztro` 压缩混淆过的js文件和对应的sourcemap文件。

当然，我们更推荐你直接使用 `CDN` 加速链接，你可以在下面列表中选择一个，在没有指定版本号的时候，会自动指向最新版本的代码库

- jsdelivr
  
    - https://cdn.jsdelivr.net/npm/iztro/dist/iztro.min.js
    - https://cdn.jsdelivr.net/npm/iztro@2.0.5/dist/iztro.min.js
- unpkg
  
    - https://unpkg.com/iztro/dist/iztro.min.js
    - https://unpkg.com/iztro@2.0.5/dist/iztro.min.js

你也可以使用如下规则来指定版本：

- `iztro@2`
- `iztro@^2.0.5`
- `iztro@2.0.5`


## 开始使用


### 引入代码

你可以根据下列方式将`iztro`引入你的代码

获取星盘数据 ​在获取紫微斗数星盘的时候，可以根据`农历`或者`阳历`日期来获取，`iztro`提供了这两种获取方式，你可以根据你的需求使用，但我们更推荐你使用`阳历`的方式来使用。 放心，阳历和农历在程序内部获取到的数据是统一的。

使用 `阳历` 有如下便利性：

- 可以很方便的在出生证上查到
- 可以使用日历组件进行日期选择
- 现在很多人都无法记住农历日期
- 可以避免因为忽略了闰月而带来的一系列问题
