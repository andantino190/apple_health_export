# apple-health-export 仕様と実装計画

本書はツールの詳細仕様と、実装に向けた計画をまとめたものです。概要と使い方は [README.md](README.md) を参照してください。

## 1. 目的

Apple ヘルスケア書き出しの `export.xml` から、分析に使う部分集合だけを抽出し、他ツールへ持ち込みやすい表形式（および必要なら XML）へ変換する。

## 2. スコープ

### 対象

- 入力: Apple ヘルスケア書き出しの `export.xml`（HealthKit Export）
- 主要要素: `Record`、必要に応じて `Correlation`
- 子要素の平坦化: `MetadataEntry`（AutoSleep 等で重要）
- 設定: YAML
- 出力: csv / excel / parquet / xml（target ごとに必要なものだけ）

### 対象外（当面）

- `export_cda.xml`（HL7 CDA。参考資料として同梱されているだけ）
- `Workout` / `ActivitySummary` / `ClinicalRecord` / `Audiogram` / `VisionPrescription` の本格対応
- `HeartRateVariabilityMetadataList` 配下の `InstantaneousBeatsPerMinute` の展開（第1版では無視または将来課題）

## 3. データ前提

実データのおおよその規模:

- `export.xml`: 約 1.2GB、`Record` 約 277 万件
- そのため **DOM 一括読み込みは不可**。ストリーミングパースを前提とする

DTD 上の主要構造（抜粋）:

- `HealthData` → `ExportDate`, `Me`, (`Record` | `Correlation` | `Workout` | …)*
- `Record` → (`MetadataEntry` | `HeartRateVariabilityMetadataList`)*
- `Correlation` → (`MetadataEntry` | `Record`)*

注意: Correlation の子として現れる Record は、ドキュメント内にトップレベル Record としても重複して出現する。

## 4. 機能仕様

### 4.1 inspect

絞り込み条件を人が決めるための情報を出す。

必須相当の出力:

| 情報 | 内容 |
|------|------|
| ソース一覧 | `sourceName` とその件数 |
| ソースごとの type | 各 `sourceName` に紐づく `type` と件数 |
| ヘッダ候補 | `sourceName`（+ 任意で `type`）で絞り込んだときの列名。`MetadataEntry` の key を含む |
| YAML stub | 設定ファイルにコピーしやすい雛形 |

任意:

| オプション | 内容 |
|------------|------|
| `--source` | 特定ソースに限定 |
| `--split-xml DIR` | 検討用にソース名ごとの XML を出力 |

### 4.2 extract

YAML 設定を読み、各 `targets[]` について抽出・保存する。

#### 設定スキーマ

```yaml
input: export.xml          # 入力 XML パス
output: output             # 出力先ディレクトリ
targets:
  - source_name: 血圧ノート # 必須
    type: null             # 省略可。Record の type
    value: null            # 省略可。Record の value
    date_field: startDate  # startDate（デフォルト）| creationDate
    extraction_start: "2024-01-01"  # 省略可。この日以降
    extraction_end: null   # 省略可。この日以前（含むかは実装で明示）
    csv_output: bp.csv
    excel_output: bp.xlsx
    parquet_output: bp.parquet
    xml_output: bp.xml
```

ルール:

- `source_name` は必須
- 出力系キー（`csv_output` 等）は指定された形式だけ生成する。いずれも無い target はエラー
- フィールド名は snake_case に統一する（`record_type` ではなく `type`）

#### 抽出対象の決定

1. **`type` が指定されている場合**
   - 該当 `source_name` + `type` の `Record` を対象とする
   - さらに `value` があればそれで絞る
2. **`type` が省略されている場合**
   - 当該 `source_name` の `Correlation` を抽出し、子 `Record` を列として平坦化する
   - Correlation の子として現れる `type` と同じトップレベル `Record` は **出力しない**（重複排除）
   - Correlation に属さない `Record` はそのまま出力する（例: AutoSleep）

#### 日付フィルタ

- 既定の比較対象: `startDate`
- `date_field: creationDate` 指定時は `creationDate` を使う
- `extraction_start` / `extraction_end` は日付（時刻省略可）。タイムゾーンは入力値のオフセットを尊重する

#### 列の扱い

**MetadataEntry の平坦化**

入力例:

```xml
<Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="AutoSleep" ... value="HKCategoryValueSleepAnalysisInBed">
  <MetadataEntry key="Average RespRate" value="17.5455" />
  <MetadataEntry key="Recharge" value="43" />
</Record>
```

出力イメージ:

| … | value | Average RespRate | Recharge |
|---|-------|------------------|----------|
| … | HKCategoryValueSleepAnalysisInBed | 17.5455 | 43 |

**Correlation の平坦化**

- Correlation 自体の属性（`type`, `sourceName`, `startDate`, `endDate`, `creationDate` など）をベースにする
- 子 Record は、例えば type 名（または短い識別子）を列名に、`value`（必要なら `unit`）を載せる
- 子の `MetadataEntry` も衝突しない範囲で展開する（衝突時の規則は実装時に決め、SPEC を更新する）

**出力から除外する列**

設定で絞り込みに使った結果、値が単一になる列は出力から落とす。

- `source_name` 指定 → `sourceName` 列は出さない
- `type` 指定 → `type` 列は出さない
- `value` 指定 → `value` 列は出さない

#### 型変換

書き出し前に可能なら:

- 日付列（`creationDate`, `startDate`, `endDate` など）→ 日付/日時型
- 数値に見える列 → 数値型

変換できない値は欠損または元文字列として扱い、失敗で全体を止めない。

#### 出力形式

| キー | 形式 | 備考 |
|------|------|------|
| `csv_output` | CSV（カンマ区切り） | pandas |
| `excel_output` | Excel (`.xlsx`) | openpyxl 等 |
| `parquet_output` | Parquet | pyarrow 等 |
| `xml_output` | XML | 抽出後レコードを再シリアライズ |

## 5. CLI 仕様

```text
health-export inspect --input EXPORT_XML [--source NAME] [--split-xml DIR]
health-export extract --config CONFIG_YAML
```

終了コード:

- `0`: 成功
- 非 `0`: 設定不正、入力欠落、I/O エラーなど

## 6. 実装計画

### 6.1 技術選定

| 項目 | 選択 | 理由 |
|------|------|------|
| 言語 | Python 3.11+ | 指定どおり。現状環境は 3.15 |
| パッケージ管理 | uv | 指定どおり |
| 表データ | pandas | csv/excel/parquet への変換が容易 |
| 設定 | YAML + PyYAML | 人が読み書きしやすく、inspect stub と相性が良い |
| テスト | pytest | 指定どおり |
| XML | `xml.etree.ElementTree.iterparse` など | ストリーミング |

### 6.2 リポジトリ整備

現状の修正点:

- `src/ tests/`（スペース入り）→ プロジェクトルートの `tests/` へ移す（`pyproject.toml` の `testpaths` と一致させる）
- console script の entry point を実際の CLI 実装へ合わせる
- 依存追加: `pyyaml`、excel/parquet 用ライブラリ
- `README.md` / 本ファイルをソース・オブ・トゥルースにする（`memo.md` は下書き）

### 6.3 モジュール構成案

```text
src/apple_health_export/
  __init__.py
  cli.py           # argparse / サブコマンド
  config.py        # YAML 読み込み・検証
  xml_stream.py    # iterparse による Record/Correlation 走査
  flatten.py       # MetadataEntry / Correlation 子の列展開
  inspect_cmd.py   # inspect 実装
  extract_cmd.py   # extract 実装
  writers.py       # csv/excel/parquet/xml 書き出し
```

### 6.4 実装フェーズ

1. **ドキュメント**（README / SPEC / HANDOFF）— 完了
2. **プロジェクト整備** — tests 配置、依存、entry point — 完了
3. **パーサ + flatten** — 完了（`xml_stream` / `flatten`、fixture テストあり）
4. **inspect** — 完了
5. **extract** — 完了（csv/excel/parquet/xml）
6. **通し確認** — 実 `export.xml` での手動確認が残タスク

### 6.5 テスト方針

- 本番 `export.xml` はリポジトリに含めない（`.gitignore` 済み）
- `tests/fixtures/` に最小 XML を置き、次を検証する
  - MetadataEntry 平坦化（AutoSleep 相当）
  - `type` 省略時の Correlation 優先と Record 重複排除（血圧ノート相当）
  - `date_field` の `startDate` / `creationDate` 切替
  - 絞り込み列の出力除外
  - YAML 設定の検証エラー

## 7. 未決・将来課題と実装時の方針

方針: 実装・テストデータ準備の中で妥当なデフォルトが見えたらそれで一旦実装し、他候補はここに残す。まだ見えないものは候補が立った時点で追記する。

| 課題 | 一旦の方針 | 他候補・メモ |
|------|------------|--------------|
| Correlation 子 Record の列名 | type から `HKQuantityTypeIdentifier` / `HKCategoryTypeIdentifier` / `HKCorrelationTypeIdentifier` を除いた短い名前を列名にし、`value` を載せる。`unit` があれば `{short}_unit` | フル type 名を列名にする / `Systolic` のようなさらに短い別名辞書 |
| 子 Record の MetadataEntry | `{short}__{metadata_key}` で衝突回避 | 無視する / 親と同じフラット名前空間 |
| HRV `InstantaneousBeatsPerMinute` | 第1版では無視（親 Record の属性と MetadataEntry のみ） | 別テーブル出力 / JSON 列に配列格納 |
| `extraction_end` の境界 | 日付のみ指定時は当該日の終端まで含む（その日のレコードを残す） | 半開区間 `[start, end)` |
| Workout 等 | 未対応 | 需要が出てから |
| `device` 属性 | 生文字列のまま出力 | 構造化パース |
| `sourceName` の NBSP ゆれ | 文字列をそのまま扱う。inspect は repr 相当で差分が分かるようにする | 正規化オプション |

## 8. 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-11-10 | 初版。memo と仕様議論を反映して作成 |
| 2026-11-10 | 未決課題に一旦の実装方針を追記 |
