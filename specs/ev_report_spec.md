# EVレポート仕様書

本ドキュメントは `predict/ev_report.py` および `predict/calc_wide_ev.py` の期待値計算に関する仕様を整理したものです。

## 1. 単勝EV（`outputs/race_{race_id}_win_all.csv`）

### 1.1 確率関連の変数

- `score`
  - **意味**: コース適性スコア。
  - **役割**: softmax の入力値。

- `p_raw`
  - **意味**: `score` を温度付き softmax で確率化した値。
  - **役割**: モデルが見積もる基礎勝率。

- `temperature`（`EVConfig.temperature`）
  - **意味**: softmax の温度パラメータ。
  - **役割**: 値が大きいほど確率分布を平滑化し、小さいほど上位馬に確率が集中。

- `beta_used`
  - **意味**: オッズ帯ごとに選択される混合係数（`beta_bands` 由来）。
  - **役割**: `p_raw` と一様確率 `u=1/N` の混合比を決定する。

- `p_mix`
  - **意味**: `beta_used * p_raw + (1 - beta_used) * u`。
  - **役割**: モデル確率を保守化した中間確率。

- `p_mkt`
  - **意味**: 市場オッズ由来の粗い確率 `1 / win_odds`。
  - **役割**: モデル確率の上限を作るための基準値。

- `cap_ratio_used`
  - **意味**: オッズ帯ごとに選択されるキャップ倍率（`cap_ratio_bands` 由来）。
  - **役割**: `p_cap = p_mkt * cap_ratio_used` を形成し、オッズ帯別の上限制約を調整。

- `p_adj`
  - **意味**: 最終的にEV計算へ使う調整後勝率。
  - **役割**: `min(p_mix, p_cap)` により極端な確率上振れを抑える。

### 1.2 期待値・判定関連の変数

- `ev_win`
  - **意味**: 単勝期待値。
  - **式**: `ev_win = p_adj * win_odds - 1`。
  - **役割**: 投資効率の中核指標。

- `m_required`
  - **意味**: オッズ帯ごとの最低要求期待値（`m_required_bands` 由来）。
  - **役割**: BUY/NO_BUY の判定しきい値。

- `decision`
  - **意味**: 投資判定（`BUY` / `NO_BUY`）。
  - **役割**: `ev_win >= m_required` で `BUY`、それ以外は `NO_BUY`。

- `ev_risk_adj`
  - **意味**: リスク調整後期待値。
  - **式**: `ev_risk_adj = ev_win - lambda_risk * log(win_odds)`。
  - **役割**: 高オッズ偏重を緩和した表示順位用指標。

- `lambda_risk`（`EVConfig.lambda_risk`）
  - **意味**: リスク調整の強さ。
  - **役割**: 値が大きいほど高オッズ側のスコアを強く減衰。

### 1.3 ランキング列

- `rank_ev`: `ev_win` 降順の順位。
- `rank_risk`: `ev_risk_adj` 降順の順位。
- `score_rank`: `score` 降順の順位。
- `pop_rank`: `win_odds` 昇順（人気順に近い）の順位。

---

## 2. ワイド事前計算（`outputs/race_{race_id}_wide_input.csv`）

### 2.1 生成対象

- `score` 上位5頭（同点時は `score` 降順 → `umaban` 昇順）。
- 10ペア（A-B, A-C, ..., D-E）を作成。

### 2.2 成立確率

- `p_wide`
  - **意味**: ペア2頭が同時に3着内へ入る確率。
  - **役割**: ワイドEVの基礎確率。
  - **算出法**: Plackett–Luce 準拠の着順シミュレーション（1〜3着逐次抽選）。

- `n_sim`（`EVConfig.n_sim`）
  - **意味**: シミュレーション回数。
  - **役割**: 推定精度と計算コストのトレードオフを調整。

- `random_seed`（`EVConfig.random_seed`）
  - **意味**: 乱数シード。
  - **役割**: 出力再現性の担保。

### 2.3 オッズ目安・優先度

- `m_wide`（`EVConfig.m_wide`）
  - **意味**: ワイドの要求期待値。
  - **役割**: 最低必要オッズの算出基準。

- `o_min`
  - **意味**: 最低必要ワイドオッズ。
  - **式**: `o_min = (1 + m_wide) / p_wide`。
  - **役割**: 手入力前に「必要オッズ水準」を示す。

- `priority`
  - **意味**: 優先フラグ（上位ペア=1）。
  - **役割**: `p_wide` 上位から重点確認対象を選別。

- `wide_odds`, `ev_wide`, `decision`
  - **意味**: 手入力/再計算用列。
  - **役割**: 事前シートでは空欄で出力し、後段で再計算可能。

---

## 3. ワイド再計算（`predict/calc_wide_ev.py`）

- 入力: `race_{race_id}_wide_input.csv`（`wide_odds` を手入力済み）
- 計算:
  - `ev_wide = p_wide * wide_odds - 1`
  - `decision = BUY if ev_wide >= m_wide else NO_BUY`
- 出力: 指定CSVへ保存。

---

## 4. 欠損・不正値時の挙動（要点）

- 単勝で `win_odds` が欠損/非数の場合:
  - EV関連は `NaN`
  - `decision` は `NO_BUY`
  - 警告ログ出力

- ワイドで頭数不足/シミュレーション不能の場合:
  - `p_wide`, `o_min` は `NaN`
  - CSV自体は生成
