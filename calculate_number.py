import time
import datetime
import requests
import json
import logging
from collections import defaultdict
import sys

API_URL = "https://wuk.168y.cloudns.org/"
LOG_FILE = "calculation_log.txt"
FETCH_AND_CALC_COUNT = 10

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE, encoding='utf-8'),
                        logging.StreamHandler()
                    ])

def calculate_probability(data):
    if not data:
        logging.warning("没有数据可用于计算。")
        return None

    logging.info(f"正在使用获取到的 {len(data)} 条数据进行计算。")

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
                    logging.warning(f"数据中的数字 '{numbers_str[i]}' 不是有效数字，跳过。")
                    continue
        else:
            logging.warning(f"数据格式异常，跳过此条记录: {entry}")

    if valid_entries_count == 0:
        logging.warning("获取到的数据中没有有效的记录用于计算。")
        return None

    if valid_entries_count < len(data):
        logging.warning(f"获取到的 {len(data)} 条数据中，有效记录不足 ({valid_entries_count} 条)。计算将基于这 {valid_entries_count} 条有效记录。")

    jump_frequencies = {}
    for digit in range(10):
        if total_counts[digit] > 0:
            jump_frequencies[digit] = last_7_counts[digit] / total_counts[digit]
        else:
            jump_frequencies[digit] = 0

    sorted_by_frequency = sorted(jump_frequencies.items(), key=lambda item: item[1], reverse=True)

    if not sorted_by_frequency:
        logging.warning("没有可用于计算跳动频率的数据。")
        return None

    max_frequency = sorted_by_frequency[0][1]
    top_frequency_digits = [digit for digit, freq in sorted_by_frequency if freq == max_frequency]

    if len(top_frequency_digits) == 1:
        logging.info(f"最高跳动频率为 {max_frequency:.4f}，唯一数字为 {top_frequency_digits[0]}。")
        return top_frequency_digits[0]

    logging.info(f"多个数字拥有最高跳动频率 ({max_frequency:.4f}): {top_frequency_digits}。进行平均位置筛选。")
    average_positions = {}
    for digit in top_frequency_digits:
        if total_appearances[digit] > 0:
            average_positions[digit] = position_sums[digit] / total_appearances[digit]
        else:
            average_positions[digit] = 0
            logging.warning(f"数字 {digit} 拥有最高频率但总出现次数为0，这不符合预期。")

    max_avg_pos = -1
    result_digit = None
    for digit, avg_pos in average_positions.items():
        if avg_pos > max_avg_pos:
            max_avg_pos = avg_pos
            result_digit = digit

    if result_digit is not None:
        logging.info(f"在拥有最高频率的数字中，平均位置最大的是 {result_digit} (平均位置: {max_avg_pos:.4f})。")
    else:
        logging.warning("未能从拥有最高频率的数字中确定唯一的最终结果。")

    return result_digit

def fetch_data_from_api(url, limit=None):
    try:
        log_message = f"正在从 {url} 获取数据..."
        params = {}
        if limit is not None and limit > 0:
            params['limit'] = limit
            log_message = f"正在从 {url} 获取最近 {limit} 条数据..."

        logging.info(log_message)

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        # 修复 UTF-8 BOM 问题
        data = json.loads(response.content.decode('utf-8-sig'))

        logging.info(f"数据获取完成。共获取到 {len(data)} 条记录。")
        return data
    except requests.exceptions.Timeout:
        logging.error(f"获取数据超时 ({url})。")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"获取数据失败: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("数据解析失败，API返回的不是有效的JSON格式。")
        return None
    except Exception as e:
        logging.error(f"发生未知错误: {e}")
        return None

logging.info("脚本启动，开始执行首次计算任务。")

try:
    data = fetch_data_from_api(API_URL, limit=FETCH_AND_CALC_COUNT)

    if data:
        next_period_number = "未知"
        if data and len(data) > 0 and 'period' in data[0]:
            try:
                latest_period = int(data[0]['period'])
                next_period_number = latest_period + 1
                logging.info(f"根据最新期号 {latest_period}，下期期号预计为 {next_period_number}")
            except ValueError:
                logging.warning(f"无法将最新期号 '{data[0]['period']}' 转换为数字，下期期号将显示为未知。")
            except Exception as e:
                logging.warning(f"获取或计算下期期号时发生错误: {e}")
        else:
            logging.warning("无法从获取的数据中找到最新期号，下期期号将显示为未知。")

        logging.info("计算中...")
        result = calculate_probability(data)
        logging.info("计算完成。")

        if result is not None:
            logging.info(f"下期期号 {next_period_number} 的最有几率的号码是: {result}")
        else:
            logging.warning("未能计算出首次最有几率的号码 (可能数据不足或格式问题)。")
    else:
        logging.error("未获取到有效数据进行首次计算。")

except Exception as e:
    logging.exception("首次计算发生未捕获的错误:")

logging.info("首次计算完成。进入定时循环，目标在每小时的 :00, :05, :10, ... 分执行计算。")

while True:
    try:
        current_ts = time.time()
        interval_seconds = 300
        intervals_since_epoch = current_ts // interval_seconds
        next_mark_ts = (intervals_since_epoch + 1) * interval_seconds
        sleep_duration = next_mark_ts - current_ts

        if sleep_duration <= 0:
            current_ts_now = time.time()
            intervals_since_epoch_now = current_ts_now // interval_seconds
            next_mark_ts = (intervals_since_epoch_now + 1) * interval_seconds
            sleep_duration = next_mark_ts - current_ts_now
            if sleep_duration <= 0:
                next_mark_ts += interval_seconds
                sleep_duration = next_mark_ts - current_ts_now

        next_run_time_str = datetime.datetime.fromtimestamp(next_mark_ts).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"等待直到 {next_run_time_str}...")

        countdown_interval = 1
        remaining_time = sleep_duration

        while remaining_time > countdown_interval:
            print(f"等待直到 {next_run_time_str}... 剩余 {int(remaining_time)} 秒 ", end='\r', file=sys.stdout, flush=True)
            time.sleep(countdown_interval)
            remaining_time = next_mark_ts - time.time()

        print(f"等待直到 {next_run_time_str}... 剩余 {int(max(0, remaining_time))} 秒 ", end='\r', file=sys.stdout, flush=True)

        if remaining_time > 0:
            time.sleep(remaining_time)
        print("", file=sys.stdout, flush=True)

        logging.info("等待结束，开始执行计算。")
        logging.info("开始执行本期计算任务。")

        data = fetch_data_from_api(API_URL, limit=FETCH_AND_CALC_COUNT)

        if data:
            next_period_number = "未知"
            if data and len(data) > 0 and 'period' in data[0]:
                try:
                    latest_period = int(data[0]['period'])
                    next_period_number = latest_period + 1
                    logging.info(f"根据最新期号 {latest_period}，下期期号预计为 {next_period_number}")
                except ValueError:
                    logging.warning(f"无法将最新期号 '{data[0]['period']}' 转换为数字，下期期号将显示为未知。")
                except Exception as e:
                    logging.warning(f"获取或计算下期期号时发生错误: {e}")
            else:
                logging.warning("无法从获取的数据中找到最新期号，下期期号将显示为未知。")

            logging.info("计算中...")
            result = calculate_probability(data)
            logging.info("计算完成。")

            if result is not None:
                logging.info(f"下期期号 {next_period_number} 的最有几率的号码是: {result}")
            else:
                logging.warning("未能计算出本期最有几率的号码 (可能数据不足或格式问题)。")
        else:
            logging.error("未获取到有效数据，跳过本次计算。")

    except KeyboardInterrupt:
        logging.info("\n用户中断脚本运行。")
        break
    except Exception as e:
        logging.exception("主循环发生未捕获的错误:")

logging.info("脚本结束。")
