import argparse
import datetime

from scanner.HttpScanner import HttpScanner

if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(
        description='这是一个参数解析示例',
        epilog='这是结尾的帮助信息'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    #http请求
    http_get_parser = subparsers.add_parser('http_get', help='HTTP GET请求工具')
    http_get_parser.add_argument('--input_file','-i',  
                            required=True,
                            help='url文件名')
    http_get_parser.add_argument('-t', '--timeout', 
                                 type=int,
                                 default=5, help='请求超时时间(秒) (默认: 5)')
    http_get_parser.add_argument('-w', '--workers', 
                                 type=int, default=10, help='最大并发数 (默认: 10)')
    
    # 通用参数
    for subparser in [http_get_parser]:
        subparser.add_argument('--output', '-o',
                               default=f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_results.txt',
                              help='输出文件')
        subparser.add_argument('--verbose', '-v',
                              action='store_true',
                              help='详细输出')

    # 解析参数
    args = parser.parse_args()

    if args.command == 'http_get':
        print("执行HTTP GET请求工具")
        scanner = HttpScanner()
        scanner.run(
            input_file=args.input_file,
            output_file=args.output,
            timeout=args.timeout,
            max_workers=args.workers
        )
    else:
        parser.print_help()
    