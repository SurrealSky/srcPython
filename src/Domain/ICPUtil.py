import time
from typing import List, Dict, Optional
import openpyxl
from openpyxl.utils import column_index_from_string
import argparse
import csv
import pandas as pd

class ICPUtil:

    def __init__(
        self,
        scsv: List[str],
        dcsv: str,
        dsheet: str,
        dcolumn: str,
    ):
        """
        初始化参数
        """
        self.scsv = scsv
        self.ssheet = 1
        self.scolumn = 1
        self.dcsv = dcsv
        self.dsheet = dsheet
        self.dcolumn = dcolumn

    def get_domains_set(self) -> set:
        """从抓取的数据中提取所有 domain，返回一个集合"""
        return {item.get('domain') for item in self.data if item.get('domain')}

    def save_json(self, filename: str = "domains.json"):
        """
        将抓取的数据保存为 JSON 文件
        
        :param filename: 输出文件名
        """
        if not self.data:
            print("没有数据可保存，请先调用 fetch_all() 获取数据。")
            return
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")

    def save_csv(self, filename: str = "domains.csv"):
        """
        将抓取的数据保存为 CSV 文件（UTF-8 with BOM）
        
        :param filename: 输出文件名
        """
        if not self.data:
            print("没有数据可保存，请先调用 fetch_all() 获取数据。")
            return
        
        if not self.data:
            return
        keys = self.data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.data)
        print(f"数据已保存到 {filename}")

    def find_missing_data(self,csv_set, xlsx_file, xlsx_sheet, xlsx_column, header=True):
        """
        将传入的 set 与 Excel 指定列的数据进行比对，返回在 set 中存在但在 Excel 中不存在的值。

        参数：
            csv_set (set): 包含待查找数据的集合（例如从 CSV 中提取的唯一值）
            xlsx_file (str): Excel (.xlsx) 文件路径
            xlsx_sheet (str): 要读取的 sheet 名称
            xlsx_column (str 或 int): 指定列。
                - 如果为字符串，则视为列字母，例如 'A', 'B', 'AA'。
                - 如果为整数，则视为从 1 开始的列索引（1 表示第一列）。
            header (bool, optional): 是否将第一行视为表头而跳过。默认 True（跳过表头）。

        返回：
            list: 缺失值的列表（已去重）
        """
        # 加载工作簿（仅读取数据，不加载公式计算结果以外的内容）
        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        ws = wb[xlsx_sheet]

        # 确定列索引（openpyxl 中列索引从 1 开始）
        if isinstance(xlsx_column, str):
            # 将列字母转换为数字索引，如 'A' -> 1
            col_idx = column_index_from_string(xlsx_column)
        elif isinstance(xlsx_column, int):
            # 直接使用传入的整数作为列索引（必须 >=1）
            if xlsx_column < 1:
                raise ValueError("整数列索引必须从 1 开始")
            col_idx = xlsx_column
        else:
            raise TypeError("xlsx_column 必须是列字母（字符串）或从 1 开始的列索引（整数）")

        # 确定数据起始行
        start_row = 2 if header else 1

        # 收集指定列的所有非空单元格值
        xlsx_values = set()
        for row in ws.iter_rows(min_row=start_row, max_col=col_idx, values_only=True):
            cell_value = row[0]  # 因为只取一列，row 是长度为 1 的元组
            if cell_value is not None:  # 忽略空单元格
                # 注意：如果希望统一类型比较，可以在此处转换为字符串，例如 str(cell_value)
                xlsx_values.add(cell_value)

        print(f"从 xlsx 中读取的主域名数量: {len(xlsx_values)}")
        # 计算差集
        missing = csv_set - xlsx_values

        # 返回列表形式
        return list(missing)

    def run(self):
        """
        """
        _read_data = []
        for csvfile in self.scsv:
            print(f"正在处理文件: {csvfile}")
            df = pd.read_csv(csvfile,header=None,encoding='gbk')  # 或 encoding='utf-8'
            # 读取某一列
            column_a_values = df.iloc[:, 0].tolist()  # 第一列
            column_b_values = df.iloc[:, 1].tolist()  # 第二列
            print(f"从 {csvfile} 读取的域名数量: {len(column_b_values)}")
            print(column_a_values)
        '''
        missing_items = self.find_missing_data(_read_data,
            self.dfile,       # Excel 文件路径
            self.dsheet,
            self.dcolumn,        # 列字母
            True             # 第一行是表头，从第二行开始读
        )
        print("缺失的数据数量:", len(missing_items))
        print("缺失的数据:", missing_items)
        '''

# 使用示例: py -3 .\src\Domain\ICPUtil.py -s icp_20260421_102606_results.csv tyc_20260421_123540_results.csv -d SRC列表.xlsx -ds 科大讯飞资产 -dc 2
if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(description='这是一个示例程序')
    # 添加位置参数（必须按顺序提供）
    parser.add_argument('-s','--sfile',required=True, nargs='+', help='请输入要比对的源Excel文件路径(空格分隔多个文件)')
    parser.add_argument('-d','--dfile',required=True, help='请输入要比对的目的Excel文件路径')
    parser.add_argument('-ds','--dsheet', required=True,help='请输入要比对的目的Excel表单名称')
    parser.add_argument('-dc','--dcolumn', required=True,help='请输入要比对的目的Excel列（可以是列字母或从1开始的列索引）')
    # 解析参数
    args = parser.parse_args()
    crawler = ICPUtil(scsv=args.sfile,dcsv=args.dfile,dsheet=args.dsheet,dcolumn=args.dcolumn)
    crawler.run()