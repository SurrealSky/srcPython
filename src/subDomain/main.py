import argparse
import datetime
from subDomain.CRTSHSubdomainFinder import CRTSHSubdomainFinder
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
    #virustotal 命令
    vt_parser = subparsers.add_parser('vt', help='VirusTotal查询')
    vt_parser.add_argument('--api_key','-k',required=True,help='VirusTotal API密钥')
    vt_parser.add_argument('--domain','-d',required=True,help='要查询的域名')

    # 通用参数
    for subparser in [crtsh_parser,vt_parser]:
        subparser.add_argument('--output', '-o',
                               default=f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_results.txt',
                              help='输出文件')
        subparser.add_argument('--verbose', '-v',
                              action='store_true',
                              help='详细输出')

    # 解析参数
    args = parser.parse_args()

    if args.command == 'crtsh':
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
    