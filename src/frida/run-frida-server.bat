adb shell "su -c '/data/tmp/frida-server-17.3.2-android-arm64 &'"
adb forward tcp:27042 tcp:27042
adb forward tcp:27043 tcp:27043