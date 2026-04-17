@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 第一步：将 DER 格式转换为 PEM
openssl x509 -inform DER -in cacert.der -out cacert.pem
if errorlevel 1 (
    echo 转换 DER 到 PEM 失败
    exit /b 1
)

REM 第二步：获取证书的 subject_hash_old 值（仅取第一行）
set "HASH="
for /f "usebackq delims=" %%i in (`openssl x509 -inform PEM -subject_hash_old -in cacert.pem 2^>nul`) do (
    if not defined HASH set "HASH=%%i"
)

if "%HASH%"=="" (
    echo 无法获取证书哈希值
    exit /b 1
)

REM 第三步：复制 cacert.pem 为 %HASH%.0
copy cacert.pem "%HASH%.0" >nul
if errorlevel 1 (
    echo 复制文件失败
    exit /b 1
)

echo 生成证书成功: %HASH%.0

REM 第四步：复制 %HASH%.0 到手机
adb push "%HASH%.0" /data/local/tmp/
if errorlevel 1 (
    echo 推送文件到手机失败
    exit /b 1
)
adb shell "su -c 'chmod 644 /data/local/tmp/%HASH%.0'"

REM 第五步：复制 %HASH%.0 到系统证书目录
adb shell "su -c 'set -e'"
REM Create a separate temp directory, to hold the current certificates
REM Without this, when we add the mount we can't read the current certs anymore.
adb shell "su -c 'mkdir -m 700 /data/local/tmp/htk-ca-copy'"
REM Copy out the existing certificates
adb shell "su -c 'cp /system/etc/security/cacerts/* /data/local/tmp/htk-ca-copy/'"
REM Create the in-memory mount on top of the system certs folder
adb shell "su -c 'mount -t tmpfs tmpfs /system/etc/security/cacerts'"
REM Copy the existing certs back into the tmpfs mount, so we keep trusting them
adb shell "su -c 'mv /data/local/tmp/htk-ca-copy/* /system/etc/security/cacerts/'"
REM Copy our new cert in, so we trust that too
adb shell "su -c 'cp /data/local/tmp/%HASH%.0 /system/etc/security/cacerts/'"
REM Update the perms & selinux context labels, so everything is as readable as before
adb shell "su -c 'chown root:root /system/etc/security/cacerts/*'"
adb shell "su -c 'chmod 644 /system/etc/security/cacerts/*'"
adb shell "su -c 'chcon u:object_r:system_file:s0 /system/etc/security/cacerts/*'"
REM Delete the temp cert directory & this script itself
adb shell "su -c 'rm -r /data/local/tmp/htk-ca-copy'"
echo "System cert successfully injected"



adb shell "su -c 'mv /data/local/tmp/%HASH%.0 /system/etc/security/cacerts/'"
if errorlevel 1 (
    echo 移动文件到系统目录失败
    exit /b 1
)
adb shell "su -c 'chmod 644 /system/etc/security/cacerts/%HASH%.0'"
if errorlevel 1 (  
    echo 设置文件权限失败
    exit /b 1
)
endlocal