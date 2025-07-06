import time
import datetime
import requests
import logging
from collections import defaultdict
import sys

# ------------------- 配置 -------------------
WEB_PAGE_URL = "https://wuk.168y.cloudns.org/"
LOG_FILE = "calculation_log.txt"
FETCH_AND_CALC_COUNT = 10  # 抓取并用于计算的最新数据条数
INTERVAL_SECONDS = 300     # 定时周期（单位：秒），300 = 每5分钟执行一次

# ------------------- 日志配置 -------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ------------------- 计算函数 -------------------
def calculate_probability(data):
    if not data:
        logging.warning("没有数据可用于计算。")
        return None

    logging.info(f"使用 {len(data)} 条数据进行计算。")

    total_counts = defaultdict(int)
    last_7_counts = defaultdict(int)
    position_sums = defaultdict(int)
    total_appearances = defaultdict(int)

    valid_entries_count = 0
    for entry in data:
        if 'number' in entry and isinstance(entry['number'], str) and len(entry['number']) == 10:
            valid_entries_count += 1
            numbers_str = entry['number']
            for i in range(10):
                try:
                    digit = int(numbers_str[i])
                    position = i + 1
                    total_counts[digit] += 1
                    total_appearances[digit] += 1
                    position_sums[digit] += position
                    if position >= 4:
                        last_7_counts[digit] += 1
                except ValueError:
                    logging.warning(f"非数字字符跳过：'{numbers_str[i]}'")
                    continue
        else:
            logging.warning(f"无效格式，跳过：{entry}")

    if valid_entries_count == 0:
        logging.warning("数据中无有效记录。")
        return None

    if valid_entries_count < len(data):
        logging.warning(f"仅有 {valid_entries_count} 条有效记录，跳过 {len(data) - valid_entries_count} 条无效。")

    jump_frequencies = {}
    for digit in range(10):
        total = total_counts[digit]
        jump_frequencies[digit] = last_7_counts[digit] / total if total else 0

    sorted_by_frequency = sorted(jump_frequencies.items(), key=lambda x: x[1], reverse=True)
    if not sorted_by_frequency:
        logging.warning("无跳动频率可计算。")
        return None

    max_freq = sorted_by_frequency[0][1]
    top_digits = [d for d, f in sorted_by_frequency if f == max_freq]

    if len(top_digits) == 1:
        logging.info(f"唯一跳动最高：{top_digits[0]}，频率={max_freq:.4f}")
        return top_digits[0]

    logging.info(f"多数字跳动最高：{top_digits}，频率={max_freq:.4f}，进行平均位置筛选。")
    average_positions = {
        d: position_sums[d] / total_appearances[d] if total_appearances[d] else 0
        for d in top_digits
    }

    result = max(average_positions, key=average_positions.get)
    logging.info(f"最终选择平均位置最大者：{result}（平均位置={average_positions[result]:.4f}）")
    return result

# ------------------- 抓取数据函数 -------------------
def fetch_data_from_webpage(url, limit=None):
    try:
        logging.info(f"请求网页数据：{url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()

        extracted_data = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) != 3:
                logging.warning(f"行格式错误，跳过：{line}")
                continue

            period = parts[0].strip()
            numbers_str = parts[2].strip()
            digits = []

            for num in numbers_str.split(','):
                try:
                    val = int(num.strip())
                    if val == 10:
                        digits.append('0')
                    elif 0 <= val <= 9:
                        digits.append(str(val))
                except:
                    logging.warning(f"数字异常跳过：{num} in line: {line}")
                    continue

            if len(digits) == 10:
                extracted_data.append({'period': period, 'number': ''.join(digits)})
            else:
                logging.warning(f"数字不足10位，跳过：{line}")

            if limit and len(extracted_data) >= limit:
                break

        if not extracted_data:
            logging.warning("网页未提取到任何有效数据。")
        return extracted_data

    except requests.exceptions.RequestException as e:
        logging.error(f"网页请求失败：{e}")
        return None

# ------------------- 主任务逻辑 -------------------
def run_calculation():
    data = fetch_data_from_webpage(WEB_PAGE_URL, limit=FETCH_AND_CALC_COUNT)

    if not data:
        logging.error("数据抓取失败，本轮跳过。")
        return

    try:
        latest_period = int(data[0]['period'])
        next_period = latest_period + 1
    except:
        next_period = "未知"

    logging.info(f"预计下期期号：{next_period}")
    result = calculate_probability(data)

    if result is not None:
        logging.info(f"下期({next_period})最有几率的号码是：{result}")
    else:
        logging.warning("计算结果为空。")

# ------------------- 定时循环 -------------------
def start_loop():
    logging.info("开始首次计算")
    run_calculation()
    logging.info("进入循环，定时每 5 分钟执行")

    while True:
        try:
            now = time.time()
            next_time = ((now // INTERVAL_SECONDS) + 1) * INTERVAL_SECONDS
            sleep_time = next_time - now

            while sleep_time > 1:
                print(f"下次执行时间：{datetime.datetime.fromtimestamp(next_time)}，剩余 {int(sleep_time)} 秒", end='\r', flush=True)
                time.sleep(1)
                sleep_time = next_time - time.time()

            run_calculation()
        except KeyboardInterrupt:
            logging.info("用户中断，脚本退出。")
            break
        except Exception as e:
            logging.exception("循环中出现异常：")

# ------------------- 入口 -------------------
if __name__ == "__main__":
    start_loop()
