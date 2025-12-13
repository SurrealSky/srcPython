import requests
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time


class CRTSHSubdomainFinder:
    def __init__(self, domain="logitech.com"):
        self.domain = domain
        self.subdomains = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_crtsh_data(self, wildcard=False):
        """
        从crt.sh获取证书数据
        """
        base_url = "https://crt.sh/"
        
        if wildcard:
            # 使用通配符搜索
            params = {
                'q': f'%.{self.domain}',
                'output': 'json'
            }
        else:
            # 精确域名搜索
            params = {
                'q': self.domain,
                'output': 'json'
            }
        
        try:
            print(f"[*] 正在查询 crt.sh: {params['q']}")
            response = self.session.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            if response.text.strip():
                return response.json()
            else:
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"[!] 请求失败: {e}")
            return []
        except json.JSONDecodeError:
            print(f"[!] JSON解析失败，响应内容: {response.text[:200]}")
            return []
    
    def extract_subdomains_from_entry(self, entry):
        """
        从单个证书条目中提取子域名
        """
        found_subdomains = set()
        
        # 从common_name字段提取
        if 'common_name' in entry and entry['common_name']:
            cn = entry['common_name'].lower()
            if self.domain in cn:
                found_subdomains.add(cn)
        
        # 从name_value字段提取（可能包含多个域名，用换行符分隔）
        if 'name_value' in entry and entry['name_value']:
            names = entry['name_value'].lower()
            # 处理换行符分隔的多个域名
            for name in names.split('\n'):
                name = name.strip()
                if self.domain in name:
                    found_subdomains.add(name)
        
        return found_subdomains
    
    def extract_all_subdomains(self, data):
        """
        从所有证书数据中提取子域名
        """
        all_subdomains = set()
        
        if not data:
            return all_subdomains
        
        print(f"[*] 处理 {len(data)} 个证书条目")
        
        # 使用多线程加速处理
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_entry = {
                executor.submit(self.extract_subdomains_from_entry, entry): entry 
                for entry in data
            }
            
            for future in as_completed(future_to_entry):
                try:
                    subdomains = future.result()
                    all_subdomains.update(subdomains)
                except Exception as e:
                    print(f"[!] 处理条目时出错: {e}")
        
        return all_subdomains
    
    def is_valid_subdomain(self, subdomain):
        """
        验证是否为有效的子域名
        """
        # 基本的域名验证
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
        return re.match(pattern, subdomain) is not None
    
    def clean_subdomains(self, subdomains):
        """
        清理和过滤子域名
        """
        cleaned = set()
        
        for subdomain in subdomains:
            # 移除通配符
            subdomain = subdomain.replace('*.', '')
            
            # 验证域名格式
            if self.is_valid_subdomain(subdomain):
                # 确保包含目标域名
                if self.domain in subdomain and subdomain.endswith(self.domain):
                    cleaned.add(subdomain)
        
        return cleaned
    
    def save_subdomains(self, subdomains,output_file=None):
        """
        保存子域名到文件
        """
        if len(subdomains)==0:
            print("[!] 无子域名可保存")

        if output_file is None:
            output_file = f"{self.domain}_CRTSH_subdomains.txt"
        # 排序以便阅读
        sorted_subdomains = sorted(subdomains, key=lambda x: (len(x.split('.')), x))
        print(f"[+] 找到 {len(sorted_subdomains)} 个唯一子域名")
        # 保存到文本文件
        with open(output_file, 'w', encoding='utf-8') as f:
            for subdomain in sorted_subdomains:
                f.write(f"{subdomain}\n")
        print(f"[+] 子域名已保存到: {output_file}")
        #显示统计信息
        self.print_statistics(sorted_subdomains)
            
    def print_statistics(self, subdomains):
        """
        打印统计信息
        """
        if not subdomains:
            print("[!] 未找到子域名")
            return
        
        print("\n" + "="*50)
        print("子域名统计信息:")
        print("="*50)
        
        # 按子域名深度统计
        depth_count = {}
        for sub in subdomains:
            parts = sub.split('.')
            depth = len(parts) - 2  # 减去主域名部分
            depth_count[depth] = depth_count.get(depth, 0) + 1
        
        print("\n按层级分布:")
        for depth in sorted(depth_count.keys()):
            print(f"  {depth+1}级子域名: {depth_count[depth]}个")
        
        # 显示前20个子域名
        print(f"\n前20个子域名示例:")
        for i, sub in enumerate(subdomains[:20], 1):
            print(f"  {i:2d}. {sub}")
        
        if len(subdomains) > 20:
            print(f"  ... 还有 {len(subdomains) - 20} 个子域名")
        
        print("="*50)
    
    def run(self):
        """
        主执行函数
        """
        print(f"[*] 开始搜索 {self.domain} 的子域名")
        print(f"[*] 来源: crt.sh 证书透明度日志")
        
        # 获取证书数据
        data = self.fetch_crtsh_data(wildcard=True)
        
        if not data:
            print("[!] 未获取到数据，尝试非通配符搜索...")
            data = self.fetch_crtsh_data(wildcard=False)
        
        if not data:
            print("[!] 无法从crt.sh获取数据")
            return []
        
        # 提取所有子域名
        raw_subdomains = self.extract_all_subdomains(data)
        
        if not raw_subdomains:
            print("[!] 未提取到子域名")
            return []
        
        print(f"[*] 提取到 {len(raw_subdomains)} 个原始域名")
        
        # 清理和过滤
        cleaned_subdomains = self.clean_subdomains(raw_subdomains)
        print(f"[*] 清理后得到 {len(cleaned_subdomains)} 个有效子域名")
        return cleaned_subdomains
