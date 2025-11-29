# 競馬予想モデル/crawl/crawl_shutuba.py
import time
import csv
import logging
import argparse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ===== パス設定 =====
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)


def build_race_url(race_id):
    return f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"


def get_shutuba_list(driver, race_url):
    logging.info(f"出走表ページへアクセス: {race_url}")
    driver.get(race_url)
    time.sleep(3)

    horses = []
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.HorseList")

    for idx, row in enumerate(rows, 1):
        try:
            waku = ""
            try:
                waku = row.find_element(By.CSS_SELECTOR, 'td[class^="Waku"]').text
            except:
                logging.warning(f"{idx}行目: 枠番取得失敗")

            num = ""
            try:
                num = row.find_element(By.CSS_SELECTOR, 'td[class^="Umaban"]').text
            except:
                logging.warning(f"{idx}行目: 馬番取得失敗")

            name_tag = row.find_element(By.CSS_SELECTOR, "span.HorseName a")
            name = name_tag.text.strip()
            url = name_tag.get_attribute("href")

            odds = ""
            try:
                odds = row.find_element(By.CSS_SELECTOR, 'span[id^="odds-"]').text
            except:
                logging.warning(f"{idx}行目: オッズ取得失敗")

            horses.append({
                "枠番": waku,
                "馬番": num,
                "馬名": name,
                "オッズ": odds,
                "URL": url
            })

        except Exception as e:
            logging.error(f"{idx}行目: 出走表取得エラー: {e}")
            continue

    logging.info(f"✅ 出走馬 {len(horses)} 頭取得完了")
    return horses


def get_recent_races(driver, horse_url, num_races=5):
    logging.info(f"詳細ページ遷移: {horse_url}")
    driver.get(horse_url)
    time.sleep(2)

    try:
        table = driver.find_element(By.CSS_SELECTOR, "table.db_h_race_results")
    except:
        logging.error("成績テーブルが見つかりません")
        return []

    rows = table.find_elements(By.TAG_NAME, "tr")[1:num_races+1]
    results = []

    for idx, row in enumerate(rows, 1):
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 24:
            logging.warning(f"{idx}行目: 列不足でスキップ")
            continue

        results.append({
            "開催": cols[1].text,
            "距離": cols[14].text,
            "馬場": cols[16].text,
            "通過": cols[21].text,
            "タイム": cols[18].text,
            "上り": cols[23].text,
            "ペース": cols[22].text
        })

    return results


def save_to_csv(race_id, data):
    filename = ASSETS_DIR / f"race_{race_id}_raw.csv"
    fieldnames = data[0].keys()

    with filename.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    logging.info(f"✅ 出力完了: {filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    args = parser.parse_args()

    race_url = build_race_url(args.race_id)

    logging.basicConfig(level=logging.INFO)

    options = Options()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        horses = get_shutuba_list(driver, race_url)
        all_rows = []

        for idx, horse in enumerate(horses, 1):
            logging.info(f"[{idx}/{len(horses)}] {horse['馬名']}")

            base = {
                "枠番": horse["枠番"],
                "馬番": horse["馬番"],
                "馬名": horse["馬名"],
                "オッズ": horse["オッズ"]
            }

            races = get_recent_races(driver, horse["URL"], 5)
            while len(races) < 5:
                races.append({"開催": "", "距離": "", "馬場": "", "通過": "", "タイム": "", "上り": "", "ペース": ""})

            for i, r in enumerate(races, 1):
                for k, v in r.items():
                    base[f"{i}走前_{k}"] = v

            all_rows.append(base)

            time.sleep(1)

        save_to_csv(args.race_id, all_rows)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
