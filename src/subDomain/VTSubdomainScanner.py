import requests
import sys
import json

class VTSubdomainScanner:
    def __init__(self, api_key,domain):
        """
        初始化 VTSubdomainScanner 类
        
        Args:
            api_key: VirusTotal API 密钥
            domain: 要查询的域名
        """
        self.api_key = api_key
        self.domain = domain
        self.limit = 40
        cursor = ""
        self.base_url = f'https://www.virustotal.com/api/v3/domains/{self.domain}/subdomains?limit={self.limit}&cursor={cursor}'
    
    def get_subdomains(self):
        """
        获取指定域名的子域名
         
        Returns:
            list: 排序后的子域名列表，如果出错返回空列表
        """
        
        try:
            headers = {
                'x-apikey': self.api_key
            }
            response = requests.get(self.base_url,headers=headers)
            response.raise_for_status()
            jdata = response.json()
            
            if 'subdomains' in jdata:
                return sorted(jdata['subdomains'])
            else:
                print(f"No subdomains found for {self.domain}", file=sys.stderr)
                return []
                
        except requests.exceptions.ConnectionError:
            print("Could not connect to www.virustotal.com", file=sys.stderr)
            return []
        except requests.exceptions.RequestException as e:
            print(f"HTTP request failed: {e}", file=sys.stderr)
            return []
        except json.JSONDecodeError:
            print("Failed to parse JSON response", file=sys.stderr)
            return []
    
    def get_all_subdomains(self):
        """
        获取所有子域名，处理分页
        
        Returns:
            list: 排序后的所有子域名列表
        """
        all_subdomains = []
        cursor = ""
        
        while True:
            url = f'https://www.virustotal.com/api/v3/domains/{self.domain}/subdomains?limit={self.limit}&cursor={cursor}'
            #print(f"正在获取： {url}", file=sys.stderr)
            try:
                headers = {
                    'x-apikey': self.api_key
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                jdata = response.json()
                
                if 'data' in jdata:
                    subdomains = [item['id'] for item in jdata['data']]
                    all_subdomains.extend(subdomains)
                    print(f"已获取/总数：{len(all_subdomains)} / {jdata['meta']['count']}", file=sys.stderr)
                    # 检查是否有下一页
                    if 'links' in jdata and 'next' in jdata['links']:
                        #print(f"cursor: {jdata['meta']['cursor']}", file=sys.stderr)
                        cursor = jdata['meta']['cursor']
                    else:
                        break
                else:
                    break
                    
            except requests.exceptions.RequestException as e:
                print(f"HTTP request failed: {e}", file=sys.stderr)
                break
            except json.JSONDecodeError:
                print("Failed to parse JSON response", file=sys.stderr)
                break
        
        return sorted(set(all_subdomains))

    def run(self):
        subdomains = self.get_all_subdomains()
        print(f"\nTotal subdomains found: {len(subdomains)}", file=sys.stderr)
        return subdomains
    
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
    
    def save_subdomains(self, subdomains,output_file=None):
        """
        保存子域名到文件
        """
        if len(subdomains)==0:
            print("[!] 无子域名可保存")

        if output_file is None:
            output_file = f"{self.domain}_VT_subdomains.txt"
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
        