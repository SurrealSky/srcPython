import sys
import hashlib

#钉钉文件解密
# py -3 passwd.py 8.5.0-Release.260817002
# 8.5.0-Release.260817002是版本号，在DingDing\main\current_new\configurations\staticconfig.xml文件中

if __name__ == '__main__':
    if len(sys.argv) == 2:    
        args = sys.argv[1:]
        version = args[0]
        md5 = hashlib.md5()
        md5.update(version.encode('utf-8'))
        ver_hash = md5.hexdigest()
        print(ver_hash[3:12])
