# IZTRO

A lightweight Open-Source Javascript library of getting The Purple Star Astrology(Zi Wei Dou Shu) astrolabe information.
## Overview

Welcome to the `iztro` development documentation! This page will introduce you to how to integrate, how to retrieve data, and how to quickly obtain all the data on a natal chart in Zi Wei Dou Shu. If you are just a basic user, reading this document will be enough for your daily use. If you have mastered the content on this page, you can explore further on other pages.

You will obtain the following information:

- How to install and integrate iztro into your code
- How to retrieve a natal chart information
- How to analyze palace positions based on the natal chart information
- How to analyze star brilliance based on palace positions
## Products

|  | Name | Link | Language | Author |
| --- | --- | --- | --- | --- |
| ![iztro](https://img.shields.io/github/stars/sylarlong/iztro.svg?style=social&label=Star) | iztro | [GitHub](https://github.com/sylarlong/iztro) ｜ [Gitee](https://gitee.com/sylarlong/iztro) | Typescript | [SylarLong](https://github.com/SylarLong) |
| ![react-iztro](https://img.shields.io/github/stars/sylarlong/react-iztro.svg?style=social&label=Star) | react-iztro | [GitHub](https://github.com/sylarlong/react-iztro) ｜ [Gitee](https://gitee.com/sylarlong/react-iztro) | React | [SylarLong](https://github.com/SylarLong) |
| ![iztro-hook](https://img.shields.io/github/stars/sylarlong/iztro-hook.svg?style=social&label=Star) | iztro-hook | [GitHub](https://github.com/sylarlong/iztro-hook) ｜ [Gitee](https://gitee.com/sylarlong/iztro-hook) | React | [SylarLong](https://github.com/SylarLong) |
| ![py-iztro](https://img.shields.io/github/stars/x-haose/py-iztro.svg?style=social&label=Star) | py-iztro | [GitHub](https://github.com/x-haose/py-iztro) ｜ [Gitee](https://gitee.com/x-haose/py-iztro) | Python | [昊色居士](https://github.com/x-haose) |
| ![py-iztro](https://img.shields.io/github/stars/EdwinXiang/dart_iztro.svg?style=social&label=Star) | dart_iztro | [GitHub](https://github.com/EdwinXiang/dart_iztro) ｜ [Gitee](https://gitee.com/EdwinXiang/dart_iztro) | Dart | [EdwinXiang](https://github.com/EdwinXiang) |


## Installation

You can install `iztro` using any package management tool you are familiar with.


### Get astrolabe data

When retrieving a natal chart in Zi Wei Dou Shu, you can obtain it based on either the `lunar calendar` or the `solar calendar`. `iztro` provides both options, and you can choose according to your needs. However, we recommend using the `solar calendar` method. Rest assured, the data obtained internally by the program is consistent for both the `lunar` and `solar` calendars.

Using the `solar calendar` has the following advantages:

- It can be easily found on a birth certificate.
- You can use a calendar component for date selection.
- Many people nowadays cannot remember lunar calendar dates.
- It can avoid a series of issues caused by overlooking leap months.
