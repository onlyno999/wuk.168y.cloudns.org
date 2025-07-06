import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta

url = "https://wuk.168y.cloudns.org/"
output_file = "nibaba.json"

def fetch_and_save():
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[错误] 请求失败: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    all_rows = soup.select("tr")
    data_rows = all_rows[1:11]  # 跳过第1行，取接下来的10行数据

    results = []

    for row in data_rows:
        tds = row.find_all("td")
        if len(tds) >= 3:
            issue = tds[0].text.strip()
            time_str = tds[1].text.strip()
            numbers = [td.text.strip() for td in tds[2:]]
            result = {
                "issue": issue,
                "time": time_str,
                "numbers": numbers
            }
            results.append(result)

    if results:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[成功] 已保存最新 {len(results)} 条数据至 {output_file}\n")
    else:
        print("[提示] 没有提取到有效数据。\n")

def wait_until_next_5_min():
    now = datetime.now()
    minute = (now.minute // 5 + 1) * 5
    if minute >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=minute, second=0, microsecond=0)
    wait_seconds = (next_time - now).total_seconds()
    print(f"[等待] 距离下一次抓取还有 {int(wait_seconds)} 秒，将在 {next_time.strftime('%H:%M:%S')} 执行。")
    time.sleep(wait_seconds)

# 第一次立即执行
fetch_and_save()

# 后续每整5分钟执行一次
while True:
    wait_until_next_5_min()
    fetch_and_save()
