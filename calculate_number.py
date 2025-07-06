import time
import datetime
import requests
import logging
from collections import defaultdict
import sys

# 网页地址
WEB_PAGE_URL = "https://wuk.168y.cloudns.org/"
# 日志文件名称
LOG_FILE = "calculation_log.txt"
# 需要获取的数据条数，也将是用于计算的数据条数
FETCH_AND_CALC_COUNT = 10 # 获取最新的10条数据

# 配置日志
# !!! 临时将 level=logging.INFO 改为 level=logging.DEBUG 来获取详细日志 !!!
logging.basicConfig(level=logging.INFO, # <-- 运行调试时请改为 logging.DEBUG
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE, encoding='utf-8'),
                        logging.StreamHandler()
                    ])

# 定义计算函数 (此函数无需修改，它期望的数据格式不变)
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
    sorted_by_frequency = sorted(jump_frequencies.items(), key=lambda item: item[1], reverse=True)

    # 找出最高跳动频率
    if not sorted_by_frequency:
        logging.warning("没有可用于计算跳动频率的数据。")
        return None

    max_frequency = sorted_by_frequency[0][1]

    # 找出所有拥有最高跳动频率的数字
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
            average_positions[digit] = 0
            logging.warning(f"数字 {digit} 拥有最高频率但总出现次数为0，这不符合预期。")

    # 在这些拥有最高频率的数字中，选择平均位置最大的那个
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


# 修改后的数据获取函数，用于从网页抓取数据，加入了伪装头
def fetch_data_from_webpage(url, limit=None):
    """
    从指定的网页地址获取数据，通过解析纯文本内容来提取数字。
    将数字 10 映射为 0。
    """
    try:
        logging.info(f"正在从 {url} 获取网页内容...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # 检查HTTP错误

        # 显式地使用 utf-8-sig 解码，以处理可能存在的 BOM
        raw_text = response.content.decode('utf-8-sig')
        logging.debug(f"获取到的原始文本前500字符: {raw_text[:500]}")
        
        extracted_data = []
        # 按行分割文本，并去除首尾空白行
        lines = raw_text.strip().splitlines()

        for i, line in enumerate(lines):
            line = line.strip() # 再次去除行首尾空白
            if not line: # 跳过空行
                logging.debug(f"跳过空行 (行号: {i+1})")
                continue
            
            logging.debug(f"处理行 {i+1}: {repr(line)}") # 打印行的原始表示

            parts = line.split('\t') # 按制表符分割
            logging.debug(f"行 {i+1} 分割为 {len(parts)} 部分: {parts}")

            if len(parts) == 3:
                period_str = parts[0].strip()
                # 尝试将期号转换为整数，如果失败则认为不是有效数据行
                try:
                    period_num = int(period_str)
                except ValueError:
                    logging.debug(f"跳过非数字期号行 (行号: {i+1}): {repr(line)}")
                    continue # 跳过此行，因为它不是一个有效的期号数据行

                # timestamp_str = parts[1].strip() # 时间戳目前不需要，但可以保留
                numbers_str_comma_separated = parts[2].strip()

                # 处理逗号分隔的数字字符串
                processed_digits_list = []
                try:
                    for num_part in numbers_str_comma_separated.split(','):
                        val = int(num_part.strip())
                        if val == 10: # 将 10 映射为 0
                            processed_digits_list.append('0')
                        elif 0 <= val <= 9: # 确保是单个数字 (0-9)
                            processed_digits_list.append(str(val))
                        else:
                            logging.warning(f"发现非单数字或非10的数字 '{val}'，跳过此数字。原始行: {repr(line)}")
                            continue
                    
                    # 检查处理后的数字列表是否正好有10个数字
                    if len(processed_digits_list) == 10:
                        number_string = "".join(processed_digits_list)
                        extracted_data.append({'period': period_str, 'number': number_string})
                    else:
                        logging.warning(f"处理后的数字列表长度不为10 ({len(processed_digits_list)}), 跳过此行。原始行: {repr(line)}")

                except ValueError as ve:
                    logging.warning(f"解析数字时发生错误: {ve}。原始行: {repr(line)}")
                    continue
                except Exception as e:
                    logging.warning(f"处理数字字符串时发生未知错误: {e}。原始行: {repr(line)}")
                    continue
            else:
                logging.warning(f"行格式不符合预期 (期望3个制表符分隔的部分)，跳过此行: {repr(line)}")
            
            if limit and len(extracted_data) >= limit:
                break # 达到限制数量，停止处理

        if not extracted_data:
            logging.warning("从网页中未能提取到任何有效数据。请检查网页内容和解析逻辑。")
        
        return extracted_data

    except requests.exceptions.Timeout:
        logging.error(f"获取网页内容超时 ({url})。")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"获取网页内容失败: {e}")
        return None
    except
