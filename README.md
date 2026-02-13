# 🐎 競馬予想モデル（回収率特化型）

「的中率ではなく **回収率を最大化** する」ことを目的とした  
データドリブン型の競馬予想プロジェクトです。

---

## 🎯 目的（Goal）

本モデルは以下の思想で構築されています：

- 期待値（オッズの歪み）を狙う  
- “なんとなく買う”を排除し、判断軸を固定  
- 過去5走を **比較可能な標準スコア** に変換  
- コース適性を **重み付け** で統合  
- 最終的には **勝率 × オッズ = 期待値モデル** へ拡張可能

---

## 🧠 現在の仕様（コード準拠）

この README は、現在の実装（`run_pipeline_with_report.py` / `scoring` / `course`）に合わせて更新しています。

### 1) 入力とメタ情報の扱い

- 入力の正は `assets/race_*_raw.csv`（`crawl` の出力）
- レース条件（競馬場・芝ダ・距離・頭数）は **ファイル名から抽出**
- `run_pipeline_with_report.py` は raw が無ければ crawl を実行し、
  `score_past5` → `course_score` → レポート生成まで一括実行

### 2) 過去5走スコア（`scoring/score_past5.py`）

3軸（speed / closing / lead）を算出し、最後に偏差値化します。

#### speed
- 同馬場（芝/ダ一致）の過去走のみ使用
- タイムを目標距離へ換算（距離比 + 馬場別距離補正）
- 距離差が大きい走ほど信頼度を減衰
- とくに **短距離→長距離** の延長ローテは追加減衰
- 5走の古いレースほど寄与を下げる（近走ウェイト）
- 集約は単純平均ではなく **加重平均（信頼度 × 近走ウェイト）**

#### closing
- `60 - 上り` をベースに、ペース補正を加算
- 通過順（1角→最終角）からの位置取り改善度を反映
- 集約は speed 同様に加重平均

#### lead
- 通過順の先頭側割合を、
  「序盤位置（重め） + 最終位置（軽め）」で合成
- ペース補正を反映
- 先行して大きく失速したケースを減点
- 集約は speed / closing と同じ加重平均

### 3) コース適性スコア（`course/course_score.py`）

- `config/course_weight.json` の `speed / lead / closing` 重みを読込
- 当日バイアス（-2〜2）で各重みを倍率補正
- 補正後の重みを比率化し、`lead` の過剰支配を cap
- `speed_dev / lead_dev / closing_dev` の線形和を計算し、最終偏差値化

### 4) 出力

- 中間: `assets/race_{race_id}_{course}_{surface}{distance}m_5runs_scores.csv`
- 最終: `assets/race_{race_id}_{course}_{surface}{distance}m_course_scores.csv`
- レポート: `reports/report_{race_no}R_{course}_{surface}{distance}m_{race_id}.txt`

---

## 🚀 実行方法

### フルパイプライン

```bash
python run_pipeline_with_report.py --race_id <race_id>
```

任意で当日バイアスを指定できます。

```bash
python run_pipeline_with_report.py \
  --race_id <race_id> \
  --bias_speed 0 --bias_lead 1 --bias_closing -1
```


### ローカルフロントエンド（Material UI）

`webapp/` に FastAPI + React(Material UI) ベースのローカルUIを追加しています。

#### 1. バックエンドAPI起動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r webapp/requirements.txt
pip install pandas numpy pytest requests beautifulsoup4 lxml
uvicorn webapp.server:app --reload --host 127.0.0.1 --port 8000
```

#### 2. フロントエンド起動

別ターミナルで以下を実行します。

```bash
cd webapp/frontend
npm install
npm run dev
```

ブラウザで `http://127.0.0.1:5173` を開くと、`race_id` 入力フォームから予測実行できます。

#### 3. UIでできること

- race_id（12桁）入力で予測パイプラインを実行
- レポートの「モデル順位」部分を見やすく一覧表示
- レポート全文表示
- 最近実行した race_id 履歴（クリック再利用）

### 単体実行（例）

```bash
python -m scoring.score_past5 --race_id <race_id> --input_csv assets/race_..._raw.csv
python -m course.course_score --race_id <race_id> --course 東京 --surface 芝 --distance 1600
```

---

## 📁 ディレクトリ

```text
crawl/        # 出走表・過去走データ取得
preprocess/   # 距離/タイム/通過順などの変換ユーティリティ
scoring/      # 過去5走から speed/closing/lead を算出
course/       # コース重みを適用して最終スコア化
predict/      # 補助スクリプト
config/       # コース重み設定
assets/       # 中間CSV・出力CSV
reports/      # 最終テキストレポート
```

---

## 📝 補足

- 本READMEは「実装に追随する仕様書」の位置づけです。
- 仕様変更時は `README.md` と `config/course_weight.json` を合わせて更新してください。
