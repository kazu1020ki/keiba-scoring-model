# race_id入力UI（フロントエンド + バックエンド）ローカル実行手順

このドキュメントは、`web/app.py` を使って **race_id を入力するだけで結果をUI表示** するための最小セットアップ手順です。

---

## 1. 必要環境（共通）

- Python 3.10+
- Google Chrome（crawler 実行時に使用）

> 既に `assets/race_<race_id>_..._course_scores.csv` が存在する race_id を使う場合、Chrome/Selenium を使わずに表示できるケースがあります。

---

## 2. 初回セットアップ（共通）

```bash
cd /workspace/keiba-scoring-model
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install flask pandas selenium webdriver-manager
```

---

## 3. バックエンド実行（API + テンプレート配信）

```bash
cd /workspace/keiba-scoring-model
source .venv/bin/activate
python web/app.py
```

- 起動URL: `http://localhost:8000`
- API: `POST /api/predict`
  - body: `{ "race_id": "202405020811" }`

### API を CLI で叩く例

```bash
curl -X POST http://localhost:8000/api/predict \
  -H 'Content-Type: application/json' \
  -d '{"race_id":"202405020811"}'
```

---

## 4. フロントエンド実行

このUIは Flask が配信する静的HTML/JSです。追加ビルドは不要です。

1. ブラウザで `http://localhost:8000` を開く
2. `race_id` を入力
3. 「取得する」をクリック
4. モデル順位（馬名・スコア）を表で確認

---

## 5. 失敗時の確認ポイント

- `race_id` は数字のみ入力
- 新しい race_id で crawler が動く場合は、実行に時間がかかることがあります
- Chrome が未インストールだと crawler 実行時に失敗します
- ログは画面下の「実行ログ」で確認できます
