import time
import re
import csv
import logging
import argparse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from preprocess.race_filename import build_raw_filename


# ===== パス設定 =====
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)


# ==============================
# URL / race meta helpers
# ==============================
def build_race_url(race_id: str) -> str:
    return f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"


def detect_course_from_race_id(race_id: str) -> str:
    """
    race_id から開催場を解決（netkeiba仕様）
    """
    code = race_id[4:6]
    mapping = {
        "01": "札幌",
        "02": "函館",
        "03": "福島",
        "04": "新潟",
        "05": "東京",
        "06": "中山",
        "07": "中京",
        "08": "京都",
        "09": "阪神",
        "10": "小倉",
    }
    return mapping.get(code, "不明")


def get_race_condition(driver):
    """
    出馬表ページ上部から 馬場 / 距離 を取得
    """
    text = driver.find_element(By.CSS_SELECTOR, "div.RaceData01").text

    m = re.search(r"(芝|ダ)(\d+)m", text)
    if not m:
        raise RuntimeError(f"距離情報を取得できません: {text}")

    surface = m.group(1)
    distance = int(m.group(2))

    return surface, distance


# ==============================
# Crawl functions
# ==============================
def get_shutuba_list(driver, race_url):
    logging.info(f"出走表ページへアクセス: {race_url}")
    driver.get(race_url)
    time.sleep(3)

    horses = []
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.HorseList")

    for idx, row in enumerate(rows, 1):
        try:
            waku = row.find_element(By.CSS_SELECTOR, 'td[class^="Waku"]').text
            num = row.find_element(By.CSS_SELECTOR, 'td[class^="Umaban"]').text

            name_tag = row.find_element(By.CSS_SELECTOR, "span.HorseName a")
            name = name_tag.text.strip()
            url = name_tag.get_attribute("href")

            try:
                odds = row.find_element(By.CSS_SELECTOR, 'span[id^="odds-"]').text
            except:
                odds = ""

            horses.append({
                "枠番": waku,
                "馬番": num,
                "馬名": name,
                "オッズ": odds,
                "URL": url,
            })

        except Exception as e:
            logging.warning(f"{idx}行目: 出走表取得失敗: {e}")

    logging.info(f"✅ 出走馬 {len(horses)} 頭取得完了")
    return horses


def get_recent_races(driver, horse_url, num_races=5):
    logging.info(f"詳細ページ遷移: {horse_url}")
    driver.get(horse_url)
    time.sleep(2)

    try:
        table = driver.find_element(By.CSS_SELECTOR, "table.db_h_race_results")
    except:
        logging.warning("成績テーブルが見つかりません")
        return []

    rows = table.find_elements(By.TAG_NAME, "tr")[1:num_races + 1]
    results = []

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 24:
            continue

        results.append({
            "開催": cols[1].text,
            "距離": cols[14].text,
            "馬場": cols[16].text,
            "通過": cols[21].text,
            "タイム": cols[18].text,
            "上り": cols[23].text,
            "ペース": cols[22].text,
        })

    return results


# ==============================
# CSV writer
# ==============================
def save_to_csv(path: Path, rows: list):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    logging.info(f"✅ 出力完了: {path}")


# ==============================
# main
# ==============================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    options = Options()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    try:
        race_url = build_race_url(args.race_id)

        # ---- race meta ----
        course = detect_course_from_race_id(args.race_id)

        driver.get(race_url)
        time.sleep(3)
        surface, distance = get_race_condition(driver)

        horses = get_shutuba_list(driver, race_url)
        field_size = len(horses)

        # ---- build filename ----
        filename = build_raw_filename(
            race_id=args.race_id,
            course=course,
            surface=surface,
            distance=distance,
            field_size=field_size,
        )
        out_path = ASSETS_DIR / filename

        all_rows = []

        for idx, horse in enumerate(horses, 1):
            logging.info(f"[{idx}/{field_size}] {horse['馬名']}")

            base = {
                "枠番": horse["枠番"],
                "馬番": horse["馬番"],
                "馬名": horse["馬名"],
                "オッズ": horse["オッズ"],
            }

            races = get_recent_races(driver, horse["URL"], 5)
            while len(races) < 5:
                races.append({
                    "開催": "",
                    "距離": "",
                    "馬場": "",
                    "通過": "",
                    "タイム": "",
                    "上り": "",
                    "ペース": "",
                })

            for i, r in enumerate(races, 1):
                for k, v in r.items():
                    base[f"{i}走前_{k}"] = v

            all_rows.append(base)
            time.sleep(1)

        save_to_csv(out_path, all_rows)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
