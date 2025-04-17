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
from cryptography.hazmat.backends import default_backend

# 自定義函式
from oauth2_functions import *


# 創建 Flask 應用，設定靜態資料夾與模板資料夾
app = Flask(__name__, static_folder="static", template_folder="templates")

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


# 路徑 "/oauth/callback" 授權回調頁面
# 這裡會處理 A 的授權碼，並換取 access_token
# 然後產生 B 的 JWT Token，並寫入 Cookie
@app.route("/oauth/callback")
def oauth_callback():
    # 取得授權碼
    code = request.args.get("code")
    if not code:
        return redirect(url_for("login_page", error="missing_code"))

    print("[DEBUG] 收到的授權碼：", code)

    try:
        print("[INFO] 向 A 的 /token 換取 access_token...")
        response = requests.post(
            url="https://fido2-web.akitawan.moe/oauth2/Code2Token",
            json={
                "code": code,
                "client_id": B_Client_id,
                "redirect_uri": request.url_root.replace("http://", "https://").rstrip("/") + "/oauth/callback",
                "grant_type": "authorization_code",
            },
            timeout=5,
        )

        print("[DEBUG] A 回傳狀態碼：", response.status_code)
        print("[DEBUG] 回應內容：", response.text)

        if response.status_code != 200:
            
            return jsonify({"error": response.text}), 401

        result = response.json()
        id_token = result.get("id_token")  # A 回傳的 JWT

        if not id_token:
            return "❌ 未取得 id_token", 401

        A_jwt_payload, A_jwt_error = verify_third_jwt(id_token)
        if A_jwt_error:
            return A_jwt_error, 401
        print("[DEBUG] A 的 JWT Payload：", A_jwt_payload)

        # 驗證成功，產出 B 的使用者專屬 JWT
        user_id = A_jwt_payload.get("sub")
        user_role = A_jwt_payload.get("role", "user")
        user_signCount = A_jwt_payload.get("signCount", 0)
        user_aaguid = A_jwt_payload.get("aaguid", None)
        user_jwt = generate_user_jwt(
            username=user_id,
            aaguid=user_aaguid,
            sign_count=user_signCount,
            role=user_role,
            expire_minutes=60,
        )

        # 重導向使用者的 dashboard 頁面
        responseToUser = make_response(redirect("/dashboard"))
        # 寫入 Cookie
        responseToUser.set_cookie(
            "token",
            user_jwt,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=3600,
        )
        return responseToUser

    except Exception as e:
        return f"❌ 發生錯誤：{str(e)}", 500


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


# vscode debug 不會執行到這行
# 要設定 launch.json
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=True,
    )
