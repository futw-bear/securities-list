# 臺灣證券列表

本專案維護可程式化使用的臺灣證券列表，資料會從交易所來源擷取、解析，並輸出為穩定排序的 JSON 檔案，方便下游服務直接引用。

## API

目前在 `main` 分支提供兩個 Raw GitHub JSON endpoint：

- 精簡版：<https://raw.githubusercontent.com/futw-bear/securities-list/refs/heads/main/data/parsed/securities.json>
- 完整版：<https://raw.githubusercontent.com/futw-bear/securities-list/refs/heads/main/data/parsed/securities-full.json>

`securities.json` 適合只需要證券代號與名稱的情境，資料格式為物件陣列：

```json
[
  {
    "code": "1111",
    "name": "欣欣水泥"
  }
]
```

`securities-full.json` 保留較完整的解析結果與來源欄位，例如 ISIN Code、公開發行日、產業別、CFI Code、備註與原始欄位，適合需要稽核或更完整 metadata 的使用情境。

## 本地開發

專案使用 Python 與 `uv`。常用指令：

```sh
uv run download-twse-isin
uv run convert-raw-json
```

`download-twse-isin` 會下載交易所來源資料，`convert-raw-json` 會將原始資料轉成 `data/parsed/` 下的 JSON 輸出。
