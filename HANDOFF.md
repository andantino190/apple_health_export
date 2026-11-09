# Agent Handoff

最終更新: 2026-11-10

次のエージェント向けの引き継ぎメモです。人間向けの使い方は [README.md](README.md)、仕様は [SPEC.md](SPEC.md) を正とします。

## いまの状態

- 仕様合意済み（YAML / `startDate` 既定 / Correlation 優先 / MetadataEntry 平坦化 / CDA 除外）
- CLI 実装済み: `health-export inspect` / `health-export extract`
- `uv run pytest` — 18 passed（2026-11-10 時点）
- 単体テスト用 fixture: [`tests/fixtures/sample_export.xml`](tests/fixtures/sample_export.xml)
- 実データ `export.xml` / `export_cda.xml` はローカルにあり gitignore（約 1.2GB / 0.9GB）

### 実装上の落とし穴

- `xml.etree.ElementTree.iterparse` で **全要素を end 時に `clear()` すると、MetadataEntry や Correlation 子 Record が親より先に消える**。トップレベルで yield した要素だけ `clear()` し、あわせて `HealthData` root も `clear()` してメモリを解放する（[`xml_stream.py`](src/apple_health_export/xml_stream.py)）。

## すぐ確認するコマンド

```bash
uv sync --group dev
uv run pytest
uv run health-export inspect --input tests/fixtures/sample_export.xml
uv run health-export extract --config <yaml>
```

実ファイルに対する手動確認例:

```bash
uv run health-export inspect --input export.xml --source AutoSleep
```

## パッケージ構成

```text
src/apple_health_export/
  cli.py           # エントリポイント
  config.py        # YAML ロード
  dates.py         # 日付境界
  xml_stream.py    # iterparse（Correlation 子 Record はスキップ）
  flatten.py       # MetadataEntry / Correlation 平坦化
  inspect_cmd.py
  extract_cmd.py   # type 省略時は Correlation 優先 + 子 type の Record 除外
  writers.py       # csv/excel/parquet/xml
```

## 実装時に決めたこと（SPEC §7 と同期）

- Correlation 子列名: type プレフィックス除去（例: `BloodPressureSystolic`）
- 子 MetadataEntry: `{short}__{key}`
- HRV の瞬間心拍リスト: 無視
- `extraction_end` の日付のみ指定: その日の 23:59:59 まで含む
- `record_type` は設定のエイリアスとして受理（正規名は `type`）

## 実データ通し確認（実施済み）

- `inspect --source AutoSleep`: 約 10 秒、7099 件、MetadataEntry ヘッダ検出 OK
- `extract` AutoSleep InBed + 血圧ノート（2024-01-01〜）: 約 18 秒で 2 target（ファイル dual scan）
  - AutoSleep InBed: 1564 rows
  - 血圧ノート（type 省略 → Correlation）: 1207 rows、収縮/拡張が列化されていることを確認

## 次にやると良さそうなこと

1. target 複数時にファイルを何度も全文スキャンしているので、必要なら1パス化
2. Excel/Parquet 出力の実データ確認
3. `device` や HRV など将来項目は需要が出てから
4. コミット（ユーザー依頼時のみ）

## 注意

- `*.xml` は gitignore。fixture だけ `!tests/fixtures/**/*.xml` で追跡可
- `memo.md` は下書き。仕様の正は SPEC.md
- ユーザー（Nobuhiro）はエージェント交代があり得る。大きな区切りでは本ファイルを更新すること
- 未決課題は「一旦の方針で実装 → 他候補を SPEC に残す」

## ユーザーからの運用メモ

- 未決は実装中に良い案が出たらそれで進める
- 他候補や後から見えた対処はドキュメントへ反映
- 引き継ぎ md を時折残してほしい
