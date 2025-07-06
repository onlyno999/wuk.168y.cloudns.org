import time
import datetime
import requests
import json
import logging
from collections import defaultdict

# API 地址
API_URL = "https://wuk.168y.cloudns.org/"
# 日志文件名称
LOG_FILE = "calculation_log.txt"
# 需要获取的数据条数，也将是用于计算的数据条数
FETCH_AND_CALC_COUNT = 10


# 配置日志
# level=logging.INFO 表示记录 INFO, WARNING, ERROR, CRITICAL 级别的消息
# format 定义了日志消息的格式 (时间 - 级别 - 消息)
# handlers 定义了日志输出到哪里：
#   - FileHandler 将日志写入指定文件 (encoding='utf-8' 确保中文正常显示)
#   - StreamHandler 将日志输出到控制台
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE, encoding='utf-8'), # 将日志写入文件
                        logging.StreamHandler() # 同时将日志输出到控制台
                    ])

# 定义计算函数
def calculate_probability(data):
    """
    根据提供的多组10位数字数据，计算并找出最有几率的号码。
    此版本使用输入数据中的所有记录进行计算。
    """
    if not data:
        logging.warning("没有数据可用于计算。")
        return None

    logging.info(f"正在使用获取到的 {len(data)} 条数据进行计算。")

    # 存储每个数字的出现次数和后7位出现次数
    total_counts = defaultdict(int)
    last_7_counts = defaultdict(int)
    # 存储每个数字出现的位置总和
    position_sums = defaultdict(int)
    # 存储每个数字的总出现次数（用于计算平均位置）
    total_appearances = defaultdict(int)

    valid_entries_count = 0
    for entry in data: # 直接遍历获取到的所有数据
        # 检查数据条目是否包含 'number' 键，并且其值是长度为10的字符串
        if 'number' in entry and isinstance(entry['number'], str) and len(entry['number']) == 10:
            valid_entries_count += 1
            numbers_str = entry['number']
            for i in range(10):
                try:
                    digit = int(numbers_str[i])
                    position = i + 1 # 位置从1到10

                    # 计算总出现次数
                    total_counts[digit] += 1
                    total_appearances[digit] += 1
                    position_sums[digit] += position

                    # 计算后7位出现次数 (位置 4-10)
                    if position >= 4:
                        last_7_counts[digit] += 1
                except ValueError:
                     # 如果字符串中的字符不是数字，记录警告并跳过该字符
                     logging.warning(f"数据中的数字 '{numbers_str[i]}' 不是有效数字，跳过。")
                     continue # 跳过当前数字，继续处理下一个

        else:
             # 如果数据条目格式不符合预期，记录警告并跳过该条记录
             logging.warning(f"数据格式异常，跳过此条记录: {entry}")

    # 检查是否有任何有效的记录被处理
    if valid_entries_count == 0:
         logging.warning("获取到的数据中没有有效的记录用于计算。")
         return None

    # 如果有效记录少于获取到的总记录，记录警告
    if valid_entries_count < len(data):
         logging.warning(f"获取到的 {len(data)} 条数据中，有效记录不足 ({valid_entries_count} 条)。计算将基于这 {valid_entries_count} 条有效记录。")


    # 计算跳动频率
    jump_frequencies = {}
    for digit in range(10): # 遍历数字 0-9
        if total_counts[digit] > 0:
            jump_frequencies[digit] = last_7_counts[digit] / total_counts[digit]
        else:
            jump_frequencies[digit] = 0 # 如果数字从未出现，其跳动频率为0

    # 按跳动频率从大到小排序
    # sorted() 返回一个列表，列表中的元素是 (数字, 跳动频率) 的元组
    # key=lambda item: item[1] 表示按元组的第二个元素（跳动频率）排序
    # reverse=True 表示降序排序
    sorted_by_frequency = sorted(jump_frequencies.items(), key=lambda item: item[1], reverse=True)

    # 找出最高跳动频率
    if not sorted_by_frequency:
        logging.warning("没有可用于计算跳动频率的数据。")
        return None # 没有数据，无法计算

    max_frequency = sorted_by_frequency[0][1] # 最高频率是排序后第一个元素的频率

    # 找出所有拥有最高跳动频率的数字
    # 遍历排序后的列表，收集所有频率等于最高频率的数字
    top_frequency_digits = [digit for digit, freq in sorted_by_frequency if freq == max_frequency]

    # 如果只有一个数字拥有最高频率，它就是结果
    if len(top_frequency_digits) == 1:
        logging.info(f"最高跳动频率为 {max_frequency:.4f}，唯一数字为 {top_frequency_digits[0]}。")
        return top_frequency_digits[0]

    # 如果有多个数字拥有相同的最高跳动频率，计算它们的平均位置
    logging.info(f"多个数字拥有最高跳动频率 ({max_frequency:.4f}): {top_frequency_digits}。进行平均位置筛选。")
    average_positions = {}
    for digit in top_frequency_digits:
        if total_appearances[digit] > 0:
            average_positions[digit] = position_sums[digit] / total_appearances[digit]
        else:
            # 理论上拥有最高频率的数字至少出现过一次，但为了健壮性处理
            average_positions[digit] = 0
            logging.warning(f"数字 {digit} 拥有最高频率但总出现次数为0，这不符合预期。")

    # 在这些拥有最高频率的数字中，选择平均位置最大的那个
    max_avg_pos = -1 # 初始化一个较小的值
    result_digit = None

    # 遍历平均位置字典，找到平均位置最大的数字
    # 如果有多个数字平均位置相同且最大，取字典遍历到的第一个（通常是数字较小的那个，取决于字典内部实现，但对于0-9数字通常是按数字大小遍历）
    # 如果需要特定规则（如取数字最小的），需要更复杂的排序逻辑
    for digit, avg_pos in average_positions.items():
        if avg_pos > max_avg_pos:
            max_avg_pos = avg_pos
            result_digit = digit
        # 如果平均位置相同，保持原有的 result_digit，即取先找到的那个
        # 如果需要相同平均位置取数字最小的，可以修改为:
        # elif avg_pos == max_avg_pos and (result_digit is None or digit < result_digit):
        #     result_digit = digit

    if result_digit is not None:
         logging.info(f"在拥有最高频率的数字中，平均位置最大的是 {result_digit} (平均位置: {max_avg_pos:.4f})。")
    else:
         logging.warning("未能从拥有最高频率的数字中确定唯一的最终结果。")


    return result_digit


def fetch_data_from_api(url, limit=None):
    """
    从指定的API地址获取数据，可选择限制条数。
    """
    try:
        log_message = f"正在从 {url} 获取数据..."
        params = {}
        if limit is not None and limit > 0:
            params['limit'] = limit # 添加 limit 参数到请求参数中
            log_message = f"正在从 {url} 获取最近 {limit} 条数据..."

        logging.info(log_message) # 状态提示

        # 发起GET请求，带上params参数，设置超时时间
        response = requests.get(url, params=params, timeout=15)
        # raise_for_status() 会在请求失败时（例如 404 或 500 错误）抛出异常
        response.raise_for_status()
        # 解析JSON响应体
        data = response.json()
        logging.info(f"数据获取完成。共获取到 {len(data)} 条记录。") # 状态提示
        return data
    except requests.exceptions.Timeout:
        # 捕获请求超时异常
        logging.error(f"获取数据超时 ({url})。")
        return None
    except requests.exceptions.RequestException as e:
        # 捕获其他requests库相关的异常（如连接错误，HTTP错误等）
        logging.error(f"获取数据失败: {e}")
        return None
    except json.JSONDecodeError:
        # 捕获JSON解析错误
        logging.error("数据解析失败，API返回的不是有效的JSON格式。")
        return None
    except Exception as e:
        # 捕获其他未知异常
        logging.error(f"发生未知错误: {e}")
        return None

# 主循环，实现定时执行
logging.info("脚本启动，目标在每小时的 :00, :05, :10, ... 分执行计算。")

while True:
    try:
        # --- 定时逻辑 ---
        current_ts = time.time() # 获取当前时间戳
        interval_seconds = 300 # 5分钟等于 300 秒

        # 计算当前时间戳距离 epoch (1970-01-01 00:00:00 UTC) 过去了多少个完整的 5分钟间隔
        intervals_since_epoch = current_ts // interval_seconds

        # 下一个 5分钟刻度的时间戳就是 (intervals_since_epoch + 1) * interval_seconds
        next_mark_ts = (intervals_since_epoch + 1) * interval_seconds

        # 计算需要等待的时间 (下一个刻度时间戳 - 当前时间戳)
        sleep_duration = next_mark_ts - current_ts

        # 如果计算出的等待时间小于等于0 (可能因为系统时间回跳或计算耗时过长)，
        # 则等待到再下一个间隔，确保至少等待一段时间
        if sleep_duration <= 0:
             sleep_duration = next_mark_ts + interval_seconds - current_ts
             next_mark_ts += interval_seconds # 更新下一次执行时间戳用于日志

        # 将下一次执行的时间戳转换为易读的日期时间字符串
        next_run_time_str = datetime.datetime.fromtimestamp(next_mark_ts).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"等待直到 {next_run_time_str} ({sleep_duration:.2f} 秒)...")

        # 等待直到下一个整 5 分钟刻度
        time.sleep(sleep_duration)

        # --- 执行数据获取和计算任务 ---
        logging.info("开始执行本期计算任务。")

        # 调用 fetch_data_from_api 并指定获取 FETCH_AND_CALC_COUNT 条数据
        # fetch_data_from_api 会处理API调用、错误和JSON解析
        data = fetch_data_from_api(API_URL, limit=FETCH_AND_CALC_COUNT)

        # 检查是否成功获取到数据
        if data:
            logging.info("计算中...") # 状态提示

            # --- 获取并计算下期期号 ---
            next_period_number = "未知" # 默认值，如果无法确定期号则显示未知
            # 检查获取到的数据是否非空，并且第一条记录（最新记录）是否包含 'period' 键
            if data and len(data) > 0 and 'period' in data[0]:
                try:
                    # 尝试将最新期号转换为整数并加1
                    latest_period = int(data[0]['period'])
                    next_period_number = latest_period + 1
                    logging.info(f"根据最新期号 {latest_period}，下期期号预计为 {next_period_number}")
                except ValueError:
                    # 如果期号不是有效的整数，记录警告
                    logging.warning(f"无法将最新期号 '{data[0]['period']}' 转换为数字，下期期号将显示为未知。")
                except Exception as e:
                    # 捕获其他获取或计算期号时的异常
                    logging.warning(f"获取或计算下期期号时发生错误: {e}")
            else:
                # 如果数据为空或最新记录没有期号，记录警告
                logging.warning("无法从获取的数据中找到最新期号，下期期号将显示为未知。")
            # --- 期号获取结束 ---


            # 调用计算函数，传入获取到的数据
            # calculate_probability 函数内部会使用所有有效的记录进行计算
            result = calculate_probability(data)
            logging.info("计算完成。") # 状态提示

            # 输出最终结果，包含计算出的下期期号
            if result is not None:
                 logging.info(f"下期期号 {next_period_number} 的最有几率的号码是: {result}") # 记录并输出结果
            else:
                 # 如果计算函数返回None，表示未能计算出结果
                 logging.warning("未能计算出本期最有几率的号码 (可能数据不足或格式问题)。")
        else:
            # 如果 fetch_data_from_api 返回None，表示获取数据失败
            logging.error("未获取到有效数据，跳过本次计算。")

        # 每次计算完成后，循环会自动回到顶部，计算下一个等待时间并休眠

    except KeyboardInterrupt:
        # 捕获用户按下 Ctrl+C 的中断信号
        logging.info("用户中断脚本运行。")
        break # 退出循环，脚本结束
    except Exception as e:
        # 捕获主循环中发生的其他未处理的异常
        # logging.exception 会打印错误信息和堆栈跟踪，有助于调试
        logging.exception("主循环发生未捕获的错误:")
        # 发生错误后，脚本不会停止，而是继续循环，等待下一个定时执行时间

# 脚本正常退出时打印结束信息
logging.info("脚本结束。")
