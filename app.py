from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    make_response,
    url_for,
    send_from_directory,
)
from flask_cors import CORS
import requests
from flask_sslify import SSLify
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwcrypto import jwk
# 自定義函式
from oauth2_functions import *
from werkzeug.middleware.proxy_fix import ProxyFix


# 創建 Flask 應用，設定靜態資料夾與模板資料夾
app = Flask(__name__, static_folder="static", template_folder="templates")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

CORS(app, origins=ORIGIN, supports_credentials=True)
# 設定 SSL
sslify = SSLify(app)

# 設定 secret_key
app.secret_key = g_secret_key


# 路徑 "/static/images/favicon.png" favicon 圖片
# 這裡是用來顯示 favicon 圖片的路徑
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static/images'),
        'favicon.png',
        mimetype='image/png'
    )

# 路徑 "/" 主畫面
# 這裡是登入頁面
# 如果已經登入，直接重導向 dashboard
# 如果沒有登入，顯示登入頁面
@app.route("/")
def login_page():
    jwt_token = request.cookies.get("token")
    if jwt_token:
        # 如果已經登入，直接重導向 dashboard
        return redirect("/dashboard")
    # 如果沒有登入，顯示登入頁面
    return render_template("login.html")

# 路徑 "/dashboard" 使用者專屬頁面
# 這裡會顯示使用者的資訊，並驗證 JWT Token 是否有效
# 如果 JWT Token 無效，則清除 Cookie 並重導向登入頁面
# 如果 JWT Token 有效，則顯示使用者資訊
@app.route("/dashboard")
def dashboard():
    # 驗證使用者的 JWT Token
    jwt_token = request.cookies.get("token")
    if not jwt_token:
        return redirect("/")
    try:
        print("[DEBUG] 收到的使用者 JWT：", jwt_token)
        # 驗證 JWT Token
        user_jwt_payload, user_jwt_error = verify_user_jwt(jwt_token)

        if user_jwt_error:
            print("[DEBUG] 使用者 JWT 驗證失敗：", user_jwt_error)
            # 驗證失敗，清除 Cookie 並重導向登入頁面
            response = logout()
            return response

        print("[DEBUG] 使用者 JWT Payload：", user_jwt_payload)
        # 驗證成功，顯示使用者資訊
        return render_template("dashboard.html", payload=user_jwt_payload)
    except Exception as e:
        return f"❌ Dashboard 發生錯誤：{str(e)}", 500


# 路徑 "/logout" 登出頁面
# 這裡會清除 Cookie，並重導向登入頁面
# 這裡的登出是針對 B 的 JWT Token，不會影響 A 的 Token
@app.route("/logout", methods=["POST", "GET"])
def logout():
    print("🧼 清除 A 的 token cookie")
    response = make_response(
        """
        <html>
        <body>
            <script>
                // 清除 cookie 只是保險手段，讓 JS 強制做一次
                document.cookie = "token=; path=/; max-age=0; SameSite=None; Secure";
                window.location.href = "/";
            </script>
        </body>
        </html>
    """
    )
    response.set_cookie("token", "", max_age=0, secure=True, samesite="None", path="/")
    return response


# 產生 /jwks.json 路由公開 RSA 公鑰
@app.route("/jwks.json")
def jwks():
    with open("RSA_key/public_key.pem", "rb") as f:
         public_key = serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

    # 轉成 JWKS 格式（略簡化版）
    numbers = public_key.public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "enc",
        "alg": "RS256",
        "n": base64url_uint(numbers.n),
        "e": base64url_uint(numbers.e),
        "kid": "A1",  # 可自行定義金鑰 ID
    }
    return jsonify({"keys": [jwk]})

# vscode debug 不會執行到這行
# 要設定 launch.json
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=True,
    )
