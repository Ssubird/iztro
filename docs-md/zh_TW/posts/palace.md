- 用途
  
  判斷一個宮位是否為空宮（沒有主星），有些派別在宮位內有某些星曜的情況下，是不會將該宮位判斷為空宮的。所以加入一個參數來傳入星曜。
- 定義
  
  ts```
  type isEmpty = (excludeStars?: StarName[]) => boolean;
  ```
- 參數
  
  | 參數 | 類型 | 是否必填 | 默認值 | 說明 |
  | --- | --- | --- | --- | --- |
  | excludeStars | [`StarName[]`](./../type-definition.md#starname) | `false` | - | 星曜名稱數組 |
- 返回值
  
  `boolean`

- 用途
  
  獲取當前宮位所在的星盤對象。
- 定義
  
  ts```
  type astrolabe = () => IFunctionalAstrolabe | undefined;
  ```
- 參數
  
  無
- 返回值

[`IFunctionalAstrolabe`](./astrolabe.md#functionalastrolabe) | `undefined`;

- 用途
  
  獲取當前宮位產生四化的4個宮位數組，下標分別對【祿，權，科，忌】
- 定義
  
  ts```
  type mutagedPlaces = () => (IFunctionalPalace | undefined)[];
  ```
- 參數
  
  無
- 返回值
  
  ([`IFunctionalPalace`](#functionalpalace) | `undefined`)[]
