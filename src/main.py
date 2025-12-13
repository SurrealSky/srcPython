import sys
import argparse

from subDomain.CRTSHSubdomainFinder import CRTSHSubdomainFinder
from Domain.ICPMainDomainFinder import ICPQueryClient
from subDomain.VTSubdomainScanner import VTSubdomainScanner

if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(
        description='这是一个参数解析示例',
        epilog='这是结尾的帮助信息'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    # crtsh 命令
    crtsh_parser = subparsers.add_parser('crtsh', help='证书透明日志查询')
    crtsh_parser.add_argument('--domains','-d',
                             nargs='+',
                             help='要查询的域名列表')
    # icp 命令
    icp_parser = subparsers.add_parser('icp', help='ICP备案查询')
    icp_parser.add_argument('--unit_name','-n',
                           help='单位名称')
    
    #virustotal 命令
    vt_parser = subparsers.add_parser('vt', help='VirusTotal查询')
    vt_parser.add_argument('--api_key','-k',help='VirusTotal API密钥')
    vt_parser.add_argument('--domain','-d',help='要查询的域名')

    # 通用参数
    for subparser in [crtsh_parser, icp_parser,vt_parser]:
        subparser.add_argument('--output', '-o',
                              help='输出文件')
        subparser.add_argument('--verbose', '-v',
                              action='store_true',
                              help='详细输出')

    # 解析参数
    args = parser.parse_args()

    if args.command == 'icp':
        print(f"执行ICP查询: {args.unit_name}")
        # 这里调用实际的ICP查询代码
            # 配置信息
        uuid = '7bc58b7123e349efaeea231cdfdd8204'
        sign = 'eyJ0eXBlIjozLCJleHREYXRhIjp7InZhZnljb2RlX2ltYWdlX2tleSI6IjdiYzU4YjcxMjNlMzQ5ZWZhZWVhMjMxY2RmZGQ4MjA0In0sImUiOjE3NjU1MjMzMTUzNzJ9.Es4e3nvVxNEkKwn2-7XimueENN1D5Msau1-JIOWicv4'
        token = 'eyJ0eXBlIjoxLCJ1IjoiMDk4ZjZiY2Q0NjIxZDM3M2NhZGU0ZTgzMjYyN2I0ZjYiLCJzIjoxNzY1NTIyNjc3NDk4LCJlIjoxNzY1NTIzMTU3NDk4fQ.t7U-vSl39VMkcyDCPMMYy37gjVsVdJNX3-roSuvOPDs'
        # 可选代理配置
        proxies = {
            "http": "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080",
        }
        proxies = None  # 如果不使用代理则设置为None
        # 创建客户端实例
        client = ICPQueryClient(
            uuid=uuid,
            sign=sign,
            token=token,
            proxies=proxies,  # 可选
            verify_ssl=False  # 禁用SSL验证（与原始代码一致）
        )
        # 方法1: 简单查询并打印域名
        client.print_domains(unit_name="科大讯飞股份有限公司", with_details=False)

        # 方法2: 获取所有记录并自定义处理
        '''
        print("\n" + "="*50)
        print("自定义处理示例:")
        print("="*50)
        
        records = client.query_all_pages(unit_name="科大讯飞股份有限公司")
        domains = client.get_domains_from_records(records)
        
        for i, domain in enumerate(domains[:5], 1):  # 只显示前5个
            print(f"{i}. {domain}")
        '''
        # 方法3: 查询单个页面
        #print("\n" + "="*50)
        #print("单页查询示例:")
        #print("="*50)
        
        #page_data = client.query_by_condition(page=1, page_size = 9999,unit_name="科大讯飞股份有限公司")
        #if page_data.get('code') == 200:
        #    page_records = page_data.get('params', {}).get('list', [])
        #    print(f"查询到 {len(page_records)} 条记录")

    elif args.command == 'crtsh':
        print(f"执行CRTsh查询: {', '.join(args.domains)}")
        # 这里调用实际的CRTsh查询代码
        for i, domain in enumerate(args.domains, 1):
            print("-" * 50)
            print(f"开始寻找域名 {i}: {domain} 的子域名")
            finder = CRTSHSubdomainFinder(domain=domain)
            subdomains = finder.run()
            finder.save_subdomains(subdomains,args.output)
            print("-" * 50)
    elif args.command == 'vt':
        print("执行VirusTotal查询")
        # 这里调用实际的VirusTotal查询代码
        scanner = VTSubdomainScanner(args.api_key,args.domain)
        subdomains = scanner.run()
        scanner.save_subdomains(subdomains,args.output)
    else:
        parser.print_help()
    