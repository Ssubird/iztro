- 用途
  
  判断一个宫位是否为空宫（没有主星），有些派别在宫位内有某些星曜的情况下，是不会将该宫位判断为空宫的。所以加入一个参数来传入星曜。
- 定义
  
  ts```
  type isEmpty = (excludeStars?: StarName[]) => boolean;
  ```
- 参数
  
  | 参数 | 类型 | 是否必填 | 默认值 | 说明 |
  | --- | --- | --- | --- | --- |
  | excludeStars | [`StarName[]`](./../type-definition.md#starname) | `false` | - | 星曜名称数组 |
- 返回值
  
  `boolean`

- 用途
  
  获取当前宫位所在的星盘对象。
- 定义
  
  ts```
  type astrolabe = () => IFunctionalAstrolabe | undefined;
  ```
- 参数
  
  无
- 返回值

[`IFunctionalAstrolabe`](./astrolabe.md#functionalastrolabe) | `undefined`;

- 用途
  
  获取当前宫位产生四化的4个宫位数组，下标分别对【禄，权，科，忌】
- 定义
  
  ts```
  type mutagedPlaces = () => (IFunctionalPalace | undefined)[];
  ```
- 参数
  
  无
- 返回值
  
  ([`IFunctionalPalace`](#functionalpalace) | `undefined`)[]
