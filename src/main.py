import sys
import argparse

from subDomain.CRTSHSubdomainFinder import CRTSHSubdomainFinder
from Domain.ICPMainDomainFinder import clean_subdomains, execute_icp_query, save_subdomains
from subDomain.VTSubdomainScanner import VTSubdomainScanner
from tools.TxtFileMerger import TxtFileMerger

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
                            required=True,
                           help='单位名称')
    
    #virustotal 命令
    vt_parser = subparsers.add_parser('vt', help='VirusTotal查询')
    vt_parser.add_argument('--api_key','-k',help='VirusTotal API密钥')
    vt_parser.add_argument('--domain','-d',help='要查询的域名')

    #txt合并去重
    txt_parser = subparsers.add_parser('txt_merge', help='TXT文件合并去重')
    txt_parser.add_argument('--input_files','-i',   
                            nargs='+',
                            required=True,
                            help='输入的TXT文件列表')

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
        import asyncio
        domain_list = asyncio.run(execute_icp_query(args.unit_name))
        print(f"ICP查询结果: {len(domain_list)} 个域名")
        cleaned_domains = clean_subdomains(domain_list)
        print(f"清理后共有: {len(cleaned_domains)} 个唯一域名")
        save_subdomains(args.unit_name,cleaned_domains,args.output)
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
    elif args.command == 'txt_merge':
        merger = TxtFileMerger()
        print("执行TXT文件合并去重")
        merger.process(
            input_paths=args.input_files,
            output_file="merged_result.txt",
            deduplicate=True,
            sort_lines=True
        )
    else:
        parser.print_help()
    