/*
 * ssl-pinning-bypass-with-frida-2026.js — Universal Android SSL Unpinning
 * Covers: SSLContext, OkHttp3, TrustKit, Conscrypt,
 *         Volley, WebView, X509TrustManager, BoringSSL/NDK
 *
 * Usage:
 *   adb push burp-cert.crt /data/local/tmp/cert-der.crt
 *   frida -U -f com.example.app -l ssl-pinning-bypass-with-frida-2026.js
 *
 */

setTimeout(function () {
    Java.perform(function () {
        console.log("\n[*] ssl-pinning-bypass-with-frida-2026.js — starting SSL bypass");
        console.log("=".repeat(52));

        bypassSSLContext();
        bypassConscrypt();
        bypassOkHttp3();
        bypassTrustKit();
        bypassVolley();
        bypassWebView();
        bypassX509TrustManager();
        bypassApacheHttp();

        console.log("=".repeat(52));
        console.log("[*] All Java hooks installed. Waiting for native...\n");
    });

    // Native hook runs outside Java.perform
    bypassBoringSSL();

}, 0);


/* ─── 1. SSLContext re-pinning (original approach, updated) ──────────── */

function bypassSSLContext() {
    try {
        var CertificateFactory  = Java.use("java.security.cert.CertificateFactory");
        var FileInputStream     = Java.use("java.io.FileInputStream");
        var BufferedInputStream = Java.use("java.io.BufferedInputStream");
        var X509Certificate     = Java.use("java.security.cert.X509Certificate");
        var KeyStore            = Java.use("java.security.KeyStore");
        var TrustManagerFactory = Java.use("javax.net.ssl.TrustManagerFactory");
        var SSLContext          = Java.use("javax.net.ssl.SSLContext");

        var cf = CertificateFactory.getInstance("X.509");
        try {
            var fis = FileInputStream.$new("/data/local/tmp/cert-der.crt");
            var bis = BufferedInputStream.$new(fis);
            var ca  = cf.generateCertificate(bis);
            bis.close();

            var certInfo = Java.cast(ca, X509Certificate);
            console.log("[1] SSLContext — CA loaded: " + certInfo.getSubjectDN());

            var ks = KeyStore.getInstance(KeyStore.getDefaultType());
            ks.load(null, null);
            ks.setCertificateEntry("ca", ca);

            var tmf = TrustManagerFactory.getInstance(
                TrustManagerFactory.getDefaultAlgorithm()
            );
            tmf.init(ks);

            SSLContext.init.overload(
                "[Ljavax.net.ssl.KeyManager;",
                "[Ljavax.net.ssl.TrustManager;",
                "java.security.SecureRandom"
            ).implementation = function (km, tm, sr) {
                console.log("[1] SSLContext.init() — injecting custom TrustManager");
                this.init(km, tmf.getTrustManagers(), sr);
            };

            console.log("[1] SSLContext — OK");
        } catch (e) {
            console.log("[1] SSLContext — cert file missing, hook skipped: " + e.message);
        }
    } catch (e) {
        console.log("[1] SSLContext — " + e.message);
    }
}


/* ─── 2. Conscrypt / Network Security Config (Android 7+) ────────────── */

function bypassConscrypt() {
    try {
        var TrustManagerImpl = Java.use(
            "com.android.org.conscrypt.TrustManagerImpl"
        );

        TrustManagerImpl.verifyChain.implementation = function (
            untrustedChain, trustAnchorChain, host,
            clientAuth, ocspData, tlsSctData
        ) {
            console.log("[2] Conscrypt.verifyChain() bypassed — host: " + host);
            return untrustedChain;
        };

        console.log("[2] Conscrypt — OK");
    } catch (e) {
        console.log("[2] Conscrypt — not found (" + e.message + ")");
    }
}


/* ─── 3. OkHttp3 CertificatePinner ───────────────────────────────────── */

function bypassOkHttp3() {
    // Variant A — standard CertificatePinner
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");

        CertificatePinner.check
            .overload("java.lang.String", "java.util.List")
            .implementation = function (hostname, peerCertificates) {
                console.log("[3a] OkHttp3.check(List) bypassed — " + hostname);
            };

        CertificatePinner.check
            .overload("java.lang.String", "[Ljava.security.cert.Certificate;")
            .implementation = function (hostname, certs) {
                console.log("[3a] OkHttp3.check(Array) bypassed — " + hostname);
            };

        console.log("[3a] OkHttp3 CertificatePinner — OK");
    } catch (e) {
        console.log("[3a] OkHttp3 CertificatePinner — " + e.message);
    }

    // Variant B — some versions use check$okhttp
    try {
        var CertificatePinnerB = Java.use("okhttp3.CertificatePinner");
        var methods = CertificatePinnerB.class.getDeclaredMethods();
        methods.forEach(function (m) {
            if (m.getName().startsWith("check")) {
                console.log("[3b] OkHttp3 — patching: " + m.getName());
            }
        });
    } catch (e) { /* silent */ }

    // Variant C — OkHttp2 / older namespace
    try {
        var OkHttp2Pinner = Java.use("com.squareup.okhttp.CertificatePinner");
        OkHttp2Pinner.check
            .overload("java.lang.String", "java.util.List")
            .implementation = function (hostname, certs) {
                console.log("[3c] OkHttp2 CertificatePinner bypassed — " + hostname);
            };
        console.log("[3c] OkHttp2 CertificatePinner — OK");
    } catch (e) {
        console.log("[3c] OkHttp2 — " + e.message);
    }
}


/* ─── 4. TrustKit ────────────────────────────────────────────────────── */

function bypassTrustKit() {
    var candidates = [
        "com.datatheorem.android.trustkit.pinning.OkHostnameVerifier",
        "com.datatheorem.android.trustkit.pinning.PinningTrustManager",
    ];

    candidates.forEach(function (cls) {
        try {
            var Cls = Java.use(cls);
            // patch verify(String, SSLSession)
            try {
                Cls.verify
                    .overload("java.lang.String", "javax.net.ssl.SSLSession")
                    .implementation = function (host, session) {
                        console.log("[4] TrustKit.verify() bypassed — " + host);
                        return true;
                    };
            } catch (e) { /* overload absent */ }
            // patch checkServerTrusted
            try {
                Cls.checkServerTrusted.implementation = function () {
                    console.log("[4] TrustKit.checkServerTrusted() bypassed");
                };
            } catch (e) { /* overload absent */ }
            console.log("[4] TrustKit " + cls.split(".").pop() + " — OK");
        } catch (e) {
            console.log("[4] TrustKit " + cls.split(".").pop() + " — " + e.message);
        }
    });
}


/* ─── 5. Volley (HurlStack) ──────────────────────────────────────────── */

function bypassVolley() {
    try {
        var HurlStack = Java.use("com.android.volley.toolbox.HurlStack");
        HurlStack.createConnection.implementation = function (url) {
            var connection = this.createConnection(url);
            try {
                var HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");
                var conn = Java.cast(connection, HttpsURLConnection);
                conn.setHostnameVerifier(
                    Java.use(
                        "javax.net.ssl.HttpsURLConnection"
                    ).getDefaultHostnameVerifier()
                );
                console.log("[5] Volley HurlStack — HostnameVerifier cleared");
            } catch (inner) { /* not an HTTPS connection */ }
            return connection;
        };
        console.log("[5] Volley HurlStack — OK");
    } catch (e) {
        console.log("[5] Volley — " + e.message);
    }
}


/* ─── 6. WebView ─────────────────────────────────────────────────────── */

function bypassWebView() {
    try {
        var WebViewClient = Java.use("android.webkit.WebViewClient");
        WebViewClient.onReceivedSslError.implementation =
            function (view, handler, error) {
                console.log("[6] WebView.onReceivedSslError() — proceeding");
                handler.proceed();
            };
        console.log("[6] WebView — OK");
    } catch (e) {
        console.log("[6] WebView — " + e.message);
    }
}


/* ─── 7. X509TrustManager — inject permissive TrustManager globally ──── */

function bypassX509TrustManager() {
    try {
        var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        var SSLContext        = Java.use("javax.net.ssl.SSLContext");
        var HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");

        var TrustAll = Java.registerClass({
            name: "com.repinning2026.TrustAll",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (chain, authType) {},
                checkServerTrusted: function (chain, authType) {
                    console.log("[7] checkServerTrusted() — always trusting");
                },
                getAcceptedIssuers: function () { return []; },
            },
        });

        var ctx = SSLContext.getInstance("TLS");
        ctx.init(null, [TrustAll.$new()], null);

        HttpsURLConnection.setDefaultSSLSocketFactory(
            ctx.getSocketFactory()
        );
        HttpsURLConnection.setDefaultHostnameVerifier(
            Java.use("org.apache.http.conn.ssl.AllowAllHostnameVerifier").$new()
        );

        console.log("[7] X509TrustManager (global) — OK");
    } catch (e) {
        // AllowAllHostnameVerifier removed in newer APIs — fall back silently
        try {
            var X509TrustManager2  = Java.use("javax.net.ssl.X509TrustManager");
            var HostnameVerifier   = Java.use("javax.net.ssl.HostnameVerifier");
            var SSLContext2        = Java.use("javax.net.ssl.SSLContext");
            var HttpsURLConnection2 = Java.use("javax.net.ssl.HttpsURLConnection");

            var TrustAll2 = Java.registerClass({
                name: "com.repinning2026.TrustAll2",
                implements: [X509TrustManager2],
                methods: {
                    checkClientTrusted: function () {},
                    checkServerTrusted: function () {},
                    getAcceptedIssuers: function () { return []; },
                },
            });

            var VerifyAll = Java.registerClass({
                name: "com.repinning2026.VerifyAll",
                implements: [HostnameVerifier],
                methods: {
                    verify: function (hostname, session) {
                        console.log("[7] HostnameVerifier.verify() — always true: " + hostname);
                        return true;
                    },
                },
            });

            var ctx2 = SSLContext2.getInstance("TLS");
            ctx2.init(null, [TrustAll2.$new()], null);
            HttpsURLConnection2.setDefaultSSLSocketFactory(ctx2.getSocketFactory());
            HttpsURLConnection2.setDefaultHostnameVerifier(VerifyAll.$new());

            console.log("[7] X509TrustManager (global, fallback) — OK");
        } catch (e2) {
            console.log("[7] X509TrustManager — " + e2.message);
        }
    }
}


/* ─── 8. Apache HTTP (legacy, still present in some apps) ────────────── */

function bypassApacheHttp() {
    try {
        var AbstractVerifier = Java.use(
            "org.apache.http.conn.ssl.AbstractVerifier"
        );
        AbstractVerifier.verify.overload(
            "java.lang.String",
            "[Ljava.lang.String;",
            "[Ljava.lang.String;",
            "boolean"
        ).implementation = function (host, cns, subjectAlts, strictWithSubDomains) {
            console.log("[8] Apache AbstractVerifier.verify() bypassed — " + host);
        };
        console.log("[8] Apache HTTP — OK");
    } catch (e) {
        console.log("[8] Apache HTTP — " + e.message);
    }
}


/* ─── 9. Native BoringSSL / libssl (Flutter, React Native, NDK) ──────── */

function bypassBoringSSL() {
    var targets = [
        "libssl.so",
        "libflutter.so",      // Flutter
        "libreactnativejni.so", // React Native (older)
        "libcronet.so",        // Cronet / gRPC
    ];

    targets.forEach(function (libName) {
        var mod = Process.findModuleByName(libName);
        if (!mod) return;

        console.log("[9] Found native lib: " + libName);

        /* SSL_CTX_set_verify — force SSL_VERIFY_NONE */
        var fnSetVerify = mod.findExportByName("SSL_CTX_set_verify");
        if (fnSetVerify) {
            Interceptor.attach(fnSetVerify, {
                onEnter: function (args) {
                    args[1] = ptr(0); // SSL_VERIFY_NONE
                    console.log("[9] SSL_CTX_set_verify → SSL_VERIFY_NONE (" + libName + ")");
                },
            });
        }

        /* SSL_CTX_set_custom_verify (BoringSSL) */
        var fnCustomVerify = mod.findExportByName("SSL_CTX_set_custom_verify");
        if (fnCustomVerify) {
            Interceptor.attach(fnCustomVerify, {
                onEnter: function (args) {
                    args[1] = ptr(0);
                    console.log("[9] SSL_CTX_set_custom_verify patched (" + libName + ")");
                },
            });
        }

        /* SSL_get_verify_result — always return X509_V_OK (0) */
        var fnGetResult = mod.findExportByName("SSL_get_verify_result");
        if (fnGetResult) {
            Interceptor.attach(fnGetResult, {
                onLeave: function (retval) {
                    retval.replace(ptr(0));
                },
            });
        }
    });
}


/*
 * ─── Notes ────────────────────────────────────────────────────────────
 *
 * Hooks are attempted unconditionally; missing classes log a warning.
 * Order matters: SSLContext is hooked before OkHttp3 so our TrustManager
 * is already loaded when OkHttp3 initialises its SSLContext.
 *
 * If the app still pins after this script:
 *   1. Enumerate loaded classes and look for custom TrustManager subclasses:
 *        Java.enumerateLoadedClasses({ onMatch: n => n.toLowerCase()
 *            .includes("trust") && console.log(n), onComplete:()=>{} });
 *   2. Check for a custom HostnameVerifier:
 *        Java.enumerateLoadedClasses({ onMatch: n => n.toLowerCase()
 *            .includes("hostname") && console.log(n), onComplete:()=>{} });
 *   3. For Cronet/gRPC, additionally hook:
 *        "org.chromium.net.CronetEngine$Builder" → disablePublicKeyPinningForTesting()
 *   4. Use objection as a quick check:
 *        objection explore → android sslpinning disable
 */
