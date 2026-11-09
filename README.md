# apple-health-export

Apple ヘルスケアの書き出しデータ（`export.xml`）から、使いたい部分だけを抽出し、分析しやすい形式へ変換するコマンドラインツールです。

ヘルスケアの書き出し ZIP を展開すると、しばしば GB 級の XML になります。本ツールは次の流れでそのデータを扱います。

1. **inspect** でソース名・タイプ・想定ヘッダなどの絞り込み情報を確認する
2. 人が YAML 設定ファイルを用意する（inspect の stub を流用可）
3. **extract** で設定に従い、複数ファイルへ抽出・保存する

## 要件

- Python 3.11 以上
- [uv](https://github.com/astral-sh/uv) によるパッケージ管理
- 依存: pandas, PyYAML, pytest（開発時）など

## セットアップ

```bash
uv sync
```

エントリポイント:

```bash
uv run health-export --help
```

## 使い方

### 1. データの探索（inspect）

```bash
uv run health-export inspect --input export.xml
```

主な用途:

- `sourceName` の一覧
- ソースごとの `type` / 代表的な `value`
- `sourceName` + `type` で絞り込んだ場合の CSV ヘッダ候補
- 設定ファイルに貼り付けやすい YAML stub の出力

ソース別に XML を分割して確認したい場合:

```bash
uv run health-export inspect --input export.xml --split-xml output/by_source
```

特定ソースだけ見る場合:

```bash
uv run health-export inspect --input export.xml --source AutoSleep
```

### 2. 設定ファイルを用意する

`source_name` は必須です。`type` / `value` / 期間 / 出力ファイル名は任意です。

```yaml
input: export.xml
output: output
targets:
  - source_name: 血圧ノート
    date_field: startDate
    extraction_start: "2024-01-01"
    csv_output: bp.csv
    excel_output: bp.xlsx

  - source_name: AutoSleep
    type: HKCategoryTypeIdentifierSleepAnalysis
    value: HKCategoryValueSleepAnalysisInBed
    extraction_start: "2024-01-01"
    csv_output: autosleep.csv

  - source_name: andantino190AppleWatch
    type: HKQuantityTypeIdentifierHeartRate
    csv_output: heart_rate.csv
```

設定項目の意味や抽出ルールの詳細は [SPEC.md](SPEC.md) を参照してください。

### 3. 抽出（extract）

```bash
uv run health-export extract --config config.yaml
```

指定した出力形式（csv / excel / parquet / xml）だけが、`output` 配下に作成されます。

## 出力のポイント

- `MetadataEntry`（例: AutoSleep）は親 Record の列として平坦化します
- `type` 未指定時は `Correlation` を優先して 1 行にまとめ、子 Record と重複するトップレベル Record は出しません
- 期間フィルタの基準はデフォルトで `startDate` です（設定で `creationDate` も選択可）
- 絞り込み条件として指定した項目（値が単一になる `source_name` や `type` など）は出力列から除外します
- 日付列・数値列は可能な範囲で型変換してから書き出します

## 対象外

- `export_cda.xml`（HL7 CDA）は対象外です。構造把握の参考用であり、本ツールの入力には使いません

## 開発

```bash
uv sync --group dev
uv run pytest
```

- 詳細仕様と実装計画: [SPEC.md](SPEC.md)
- エージェント引き継ぎ: [HANDOFF.md](HANDOFF.md)

## ライセンス

[MIT](LICENSE)
