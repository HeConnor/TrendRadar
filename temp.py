#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2026/2/24
# @File    : temp.py
# @Software: PyCharm
# @Version  : Python-
# @TASK:
import re
from typing import Dict, List, Tuple, Any, Optional


def run():
    from trendradar.__main__ import main
    main()


def parse_db():
    from trendradar.storage.local import LocalStorageBackend
    lsb = LocalStorageBackend(enable_txt=False, enable_html=False)
    out = lsb.get_today_all_data('2026-02-24')
    pass


# --------------------------------------------
def load_titles_from_file(file_path: str) -> Tuple[Dict, Dict, List]:
    """
    从文件中读取标题数据，恢复为原始的三个数据结构

    Args:
        file_path: 要读取的文件路径

    Returns:
        Tuple[results, id_to_name, failed_ids]
    """
    # 初始化要返回的数据结构
    results: Dict[str, Dict[str, Any]] = {}
    id_to_name: Dict[str, str] = {}
    failed_ids: List[str] = []

    # 正则表达式用于解析排名行
    rank_line_pattern = re.compile(
        r'^(?P<rank>\d+)\. (?P<title>.+?)(?: \[URL:(?P<url>.+?)\])?(?: \[MOBILE:(?P<mobile_url>.+?)\])?$'
    )

    current_id = None
    in_failed_section = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]  # 去除空行和首尾空白

            for line in lines:
                # 检查是否进入失败ID区域
                if line == "==== 以下ID请求失败 ====":
                    in_failed_section = True
                    continue

                # 处理失败ID
                if in_failed_section:
                    failed_ids.append(line)
                    continue

                # 处理ID行（主数据区）
                if "|" in line:
                    # 格式：id | name
                    parts = line.split("|", 1)
                    current_id = parts[0].strip()
                    name = parts[1].strip()
                    id_to_name[current_id] = name
                    # 初始化该ID的结果字典
                    results[current_id] = {}
                elif not line.startswith(tuple('0123456789')):
                    # 纯ID行（不以数字开头，排除排名行）
                    current_id = line.strip()
                    # 初始化该ID的结果字典（name为空）
                    results[current_id] = {}
                else:
                    # 处理排名标题行
                    if current_id is None:
                        continue  # 异常情况：排名行没有对应的ID，跳过

                    match = rank_line_pattern.match(line)
                    if match:
                        groups = match.groupdict()
                        rank = int(groups["rank"])
                        title = groups["title"]
                        url = groups["url"] or ""
                        mobile_url = groups["mobile_url"] or ""

                        # 恢复原始的title_data结构
                        # 注意：原函数中clean_title会清洗标题，这里恢复的是清洗后的标题
                        results[current_id][title] = {
                            "ranks": [rank],
                            "url": url,
                            "mobileUrl": mobile_url
                        }

    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
    except Exception as e:
        print(f"读取文件时发生错误：{e}")

    return results, id_to_name, failed_ids


def extract_time_from_filename(filename: str) -> Optional[str]:
    """
    从文件名（如"03时03分.txt"）中提取时间，返回 HH-MM 格式的字符串

    Args:
        filename: 包含时间的文件名

    Returns:
        格式化后的时间字符串（HH-MM），格式不匹配返回 None
    """
    # 正则匹配 XX时XX分 格式，捕获小时和分钟
    time_pattern = re.compile(r'(\d{1,2})时(\d{1,2})分')
    match = time_pattern.search(filename)

    if not match:
        print(f"错误：文件名 {filename} 未匹配到 时/分 格式的时间信息")
        return None

    # 提取并补零（确保两位数字，如 3时3分 → 03-03）
    hour = match.group(1).zfill(2)
    minute = match.group(2).zfill(2)

    return f"{hour}-{minute}"


def extract_date_from_string(date_str: str) -> Optional[str]:
    """
    从字符串（如"2026年02月24日"）中提取日期，返回 YYYY-MM-DD 格式的字符串

    Args:
        date_str: 包含日期的字符串

    Returns:
        格式化后的日期字符串（YYYY-MM-DD），格式不匹配返回 None
    """
    # 正则匹配 XXXX年XX月XX日 格式，捕获年、月、日
    date_pattern = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日')
    match = date_pattern.search(date_str)

    if not match:
        print(f"错误：字符串 {date_str} 未匹配到 年/月/日 格式的日期信息")
        return None

    # 提取并补零（确保月、日为两位数字，如 2026年2月4日 → 2026-02-04）
    year = match.group(1)
    month = match.group(2).zfill(2)
    day = match.group(3).zfill(2)

    return f"{year}-{month}-{day}"


def convert_txt2db():
    import os
    from trendradar.storage import convert_crawl_results_to_news_data
    from trendradar.storage.local import LocalStorageBackend

    folder = r'.\output'
    save_folder = r'.\output\news'
    for sub_folder in os.listdir(folder):
        crawl_date = extract_date_from_string(sub_folder)
        if crawl_date is None:
            continue
        save_file = os.path.join(save_folder, f'{crawl_date}.db')
        if os.path.exists(save_file):
            continue
        lsb = LocalStorageBackend(enable_txt=False, enable_html=False)

        txt_folder = os.path.join(folder, sub_folder, 'txt')
        for file in os.listdir(txt_folder):
            crawl_time = extract_time_from_filename(file)
            file_path = os.path.join(txt_folder, file)
            results, id_to_name, failed_ids = load_titles_from_file(file_path)

            news_data = convert_crawl_results_to_news_data(
                results, id_to_name, failed_ids, crawl_time, crawl_date
            )
            cur_time = f'{crawl_date} {crawl_time.replace("-", ":")}:10'
            lsb.save_news_data(news_data, cur_time)
        lsb.cleanup()
    pass


if __name__ == '__main__':
    run()

    # parse_db()
    # convert_txt2db()
    print('done')
