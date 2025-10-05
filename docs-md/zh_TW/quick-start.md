# IZTRO

一套輕量級獲取紫微鬥數排盤信息的 Javascript 開源庫。
## 前言

歡迎使用 `iztro` 開發文檔！本頁將向你介紹如何集成、如何獲取數據、以及如何快速得到紫微鬥數裏一張星盤上的所有數據。如果你只是基礎使用者，閱讀完本篇文檔將足夠你日常使用。 如果你已經掌握了本頁內容，可以到其他頁面進行更深入的探索。如果你對紫微鬥數感興趣，但是有沒有相關基礎，可以點擊 [基礎知識掃盲](/learn/basis.md) 進行掃盲學習。

你將獲取到以下信息：

- 如何將 `iztro` 安裝和集成到你的代碼裏
- 如何獲取到一張星盤
- 如何基於星盤開始分析宮位
- 如何基於宮位開始分析星曜
## 产品

|  | 名稱 | 連結 | 語言 | 作者 |
| --- | --- | --- | --- | --- |
| ![iztro](https://img.shields.io/github/stars/sylarlong/iztro.svg?style=social&label=Star) | iztro | [GitHub](https://github.com/sylarlong/iztro) ｜ [Gitee](https://gitee.com/sylarlong/iztro) | Typescript | [SylarLong](https://github.com/SylarLong) |
| ![react-iztro](https://img.shields.io/github/stars/sylarlong/react-iztro.svg?style=social&label=Star) | react-iztro | [GitHub](https://github.com/sylarlong/react-iztro) ｜ [Gitee](https://gitee.com/sylarlong/react-iztro) | React | [SylarLong](https://github.com/SylarLong) |
| ![iztro-hook](https://img.shields.io/github/stars/sylarlong/iztro-hook.svg?style=social&label=Star) | iztro-hook | [GitHub](https://github.com/sylarlong/iztro-hook) ｜ [Gitee](https://gitee.com/sylarlong/iztro-hook) | React | [SylarLong](https://github.com/SylarLong) |
| ![py-iztro](https://img.shields.io/github/stars/x-haose/py-iztro.svg?style=social&label=Star) | py-iztro | [GitHub](https://github.com/x-haose/py-iztro) ｜ [Gitee](https://gitee.com/x-haose/py-iztro) | Python | [昊色居士](https://github.com/x-haose) |
| ![py-iztro](https://img.shields.io/github/stars/EdwinXiang/dart_iztro.svg?style=social&label=Star) | dart_iztro | [GitHub](https://github.com/EdwinXiang/dart_iztro) ｜ [Gitee](https://gitee.com/EdwinXiang/dart_iztro) | Dart | [EdwinXiang](https://github.com/EdwinXiang) |


## 安裝


### 使用包管理安裝

你可以使用任意一種你熟悉的包管理工具進行安裝

在 `v2.0.4` 版本以後，編譯了 `umd` 的純Javascript庫。可以下載 [release](https://github.com/SylarLong/iztro/releases) 資源文件中的 `🗜️iztro-min-js.tar.gz` 壓縮包，裏面包含了一個 `iztro` 壓縮混淆過的js文件和對應的sourcemap文件。

當然，我們更推薦你直接使用 `CDN` 加速鏈接，你可以在下面列表中選擇一個，在沒有指定版本號的時候，會自動指向最新版本的代碼庫

- jsdelivr
  
    - https://cdn.jsdelivr.net/npm/iztro/dist/iztro.min.js
    - https://cdn.jsdelivr.net/npm/iztro@2.0.5/dist/iztro.min.js
- unpkg
  
    - https://unpkg.com/iztro/dist/iztro.min.js
    - https://unpkg.com/iztro@2.0.5/dist/iztro.min.js

你也可以使用如下規則來指定版本：

- `iztro@2`
- `iztro@^2.0.5`
- `iztro@2.0.5`


## 開始使用


### 引入代碼

你可以根據下列方式將`iztro`引入你的代碼

獲取星盤數據 ​在獲取紫微鬥數星盤的時候，可以根據`農歷`或者`陽歷`日期來獲取，`iztro`提供了這兩種獲取方式，你可以根據你的需求使用，但我們更推薦你使用`陽歷`的方式來使用。 放心，陽歷和農歷在程序內部獲取到的數據是統一的。

使用 `陽歷` 有如下便利性：

- 可以很方便的在出生證上查到
- 可以使用日歷組件進行日期選擇
- 現在很多人都無法記住農歷日期
- 可以避免因為忽略了閏月而帶來的一系列問題
