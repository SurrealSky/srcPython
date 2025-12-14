import os
import glob
from typing import List, Union


class TxtFileMerger:
    """实用的TXT文件合并去重工具"""
    
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
        self.stats = {
            'files_processed': 0,
            'total_lines': 0,
            'unique_lines': 0
        }
    
    def load_file(self, filepath: str) -> List[str]:
        """加载文件内容"""
        try:
            with open(filepath, 'r', encoding=self.encoding) as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return [line.strip() for line in f if line.strip()]
            except:
                print(f"⚠️  无法读取文件: {filepath}")
                return []
        except FileNotFoundError:
            print(f"❌ 文件不存在: {filepath}")
            return []
    
    def process(self, 
                input_paths: Union[str, List[str]], 
                output_file: str,
                deduplicate: bool = True,
                sort_lines: bool = False) -> List[str]:
        """
        主处理方法
        
        Args:
            input_paths: 输入路径，可以是文件、列表或通配符
            output_file: 输出文件路径
            deduplicate: 是否去重
            sort_lines: 是否排序
        
        Returns:
            处理后的行列表
        """
        # 1. 收集文件列表
        if isinstance(input_paths, str):
            if '*' in input_paths or '?' in input_paths:
                # 通配符模式
                file_list = glob.glob(input_paths)
            else:
                # 单个文件
                file_list = [input_paths]
        else:
            # 文件列表
            file_list = input_paths
        
        # 过滤只保留txt文件
        file_list = [f for f in file_list if f.lower().endswith('.txt')]
        
        if not file_list:
            print("❌ 没有找到txt文件")
            return []
        
        print(f"📂 找到 {len(file_list)} 个文件")
        
        # 2. 读取并合并所有文件
        all_lines = []
        for filepath in file_list:
            lines = self.load_file(filepath)
            self.stats['files_processed'] += 1
            self.stats['total_lines'] += len(lines)
            all_lines.extend(lines)
            print(f"  已加载: {os.path.basename(filepath)} ({len(lines)} 行)")
        
        # 3. 去重
        if deduplicate:
            seen = set()
            unique_lines = []
            for line in all_lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            result = unique_lines
        else:
            result = all_lines
        
        self.stats['unique_lines'] = len(result)
        
        # 4. 排序
        if sort_lines:
            result.sort()
        
        # 5. 保存
        self._save_result(result, output_file)
        
        # 6. 打印统计
        self._print_stats()
        
        return result
    
    def _save_result(self, lines: List[str], output_file: str):
        """保存结果到文件"""
        # 创建目录
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 写入文件
        with open(output_file, 'w', encoding=self.encoding) as f:
            for line in lines:
                f.write(line + '\n')
        
        print(f"✅ 结果已保存: {output_file}")
    
    def _print_stats(self):
        """打印统计信息"""
        print("\n📊 统计信息:")
        print(f"   处理文件数: {self.stats['files_processed']}")
        print(f"   总行数: {self.stats['total_lines']}")
        print(f"   去重后行数: {self.stats['unique_lines']}")
        if self.stats['total_lines'] > 0:
            rate = 1 - self.stats['unique_lines'] / self.stats['total_lines']
            print(f"   去重率: {rate:.1%}")


# 使用示例
if __name__ == "__main__":
    # 创建实例
    merger = TxtFileMerger()
    
    # 示例1: 合并多个文件
    print("示例1: 合并多个指定文件")
    merger.process(
        input_paths=["file1.txt", "file2.txt", "file3.txt"],
        output_file="merged_result.txt",
        deduplicate=True,
        sort_lines=True
    )
    
    # 示例2: 使用通配符
    print("\n示例2: 使用通配符合并所有txt文件")
    merger.process(
        input_paths="*.txt",
        output_file="all_files_merged.txt"
    )
    
    # 示例3: 不去重只合并
    print("\n示例3: 只合并不去重")
    merger.process(
        input_paths=["data1.txt", "data2.txt"],
        output_file="combined.txt",
        deduplicate=False,
        sort_lines=False
    )