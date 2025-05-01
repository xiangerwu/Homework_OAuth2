import requests
import base64
import jwt
import os
from jwt.algorithms import RSAAlgorithm
from datetime import datetime, timedelta, timezone

g_IP = "0.0.0.0"  # Flask 在 Render 上應該綁定所有 IP
# g_IP = "127.0.0.1"
RP_NAME = "My OAuth2.0 App"  # 可保持不變，或改成你的應用名稱

g_port = 5001  # 預設 Flask 埠號

# 設定 RP 相關資訊
RP_ID = "oauth.akitawan.moe"  # 改成你的正式域名
ORIGIN = "https://oauth.akitawan.moe"  # 改成你的正式域名，且使用 HTTPS
# ORIGIN = "https://localhost:5000"  # 測試用的 localhost 域名，且使用 HTTPS
# RP_ID = "localhost"  # 測試用的 localhost 域名，且使用 HTTPS

g_secret_key = os.urandom(24)
B_Client_id = "BtA-client"  # 這是 Server B與A 的 client_id


# 驗證來自 A 的 RS256 JWT Token
# 這個函式會從 A 的 JWKS 中抓對應的 RSA 公鑰，然後驗證 JWT Token
def verify_third_jwt(
    id_token: str,
    jwks_url: str = "https://fido2-web.akitawan.moe/oauth2/.well-known/jwks.json",
):
    """
    驗證來自 A 的 RS256 JWT Token

    參數:
        id_token (str): 從 A 拿到的 JWT
        expected_audience (str): 預期的 audience（client_id）

    回傳:
        tuple: (payload, None) 若成功
        (None, str) 若失敗，錯誤訊息為 str
    """
    try:
        # 解析 JWT header
        unverified_header = jwt.get_unverified_header(id_token)
        if not unverified_header:
            return None, "❌ JWT header 無法解析"
        # 取得 kid
        kid = unverified_header.get("kid")
        if not kid:
            return None, "❌ JWT 未含 kid，無法選擇對應公鑰"
        # 取得 A 的 JWKS，並從中選擇對應的 RSA 公鑰
        public_key = get_public_key_from_jwks(jwks_url, kid)

        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            issuer="https://fido2-web.akitawan.moe",
        )
        return payload, None

    except jwt.ExpiredSignatureError:
        return None, "❌ Token 已過期"
    except jwt.InvalidTokenError as e:
        return None, f"❌ Token 驗證失敗: {str(e)}"
    except Exception as e:
        return None, f"❌ 公鑰取得或驗證錯誤: {str(e)}"


# 這個函式會產生一個 JWT Token，並將其簽章
# 這個 Token 可以用來驗證使用者的身份
# 這個 Token 的有效時間為 expire_minutes 分鐘
def generate_user_jwt(
    username: str,
    aaguid: str = None,
    sign_count: int = None,
    role: str = "user",
    expire_minutes: int = 10,
    issuer: str = None,
) -> str:
    """
    產生 JWT Token

    參數:
        username (str): 使用者識別 ID
        aaguid (str): FIDO2 裝置的識別碼（可選）
        sign_count (int): FIDO2 裝置的簽名計數器（可選）
        role (str): 使用者權限（預設為 'user'）
        expire_minutes (int): Token 有效時間（分鐘）

    回傳:
        str: JWT 字串（已簽章）
    """
    # 取得當前時間
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=60)

    # 產生 JWT Token 的 payload
    payload = {
        "sub": username,
        "role": role,
        "iat": int(now.timestamp()),  # 簽發時間
        "exp": int(exp.timestamp()),  # 到期時間
        "iss": ORIGIN,  # 發行者
    }

    if aaguid:
        payload["aaguid"] = aaguid
    if sign_count is not None:
        payload["signCount"] = sign_count
    token = jwt.encode(payload, g_secret_key, algorithm="HS256")  # or RS256
    return token


# 這個函式會驗證使用者的 JWT Token
# 這個 Token 是由 Server B 簽章的
# 這個 Token 的有效時間為 expire_minutes 分鐘
def verify_user_jwt(jwt_token: str):
    """驗證 user 的 JWT Token"""
    try:
        payload = jwt.decode(
            jwt_token,
            g_secret_key,
            algorithms=["HS256"],
            issuer=ORIGIN,
        )

        return payload, None
    except jwt.ExpiredSignatureError:
        return None, str("Token 已過期")
    except jwt.InvalidTokenError:
        return None, str("無效的 Token")
    except jwt.InvalidSignatureError:
        return None, str("無效的簽名")
    except jwt.DecodeError:
        return None, str("解碼錯誤")
    except jwt.InvalidIssuerError:
        return None, str("無效的發行者")
    except Exception as e:
        return None, str(f"其他錯誤: {e}")


# 這個函式會將 base64url 編碼的字串轉換為 int
def base64url_to_long(data: str) -> int:
    """將 base64url 編碼轉換為 int"""
    padded = data + "=" * (4 - len(data) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(padded), "big")


# 這個函式會從 A 的 JWKS 中抓對應的 RSA 公鑰
# 這個 JWKS 是 A 提供的，通常是公開的
def get_public_key_from_jwks(jwks_url: str, kid: str):
    """從 A 的 JWKS 中抓對應的 RSA 公鑰"""
    res = requests.get(jwks_url, timeout=5)
    jwks = res.json()
    for key in jwks["keys"]:
        if key["kid"] == kid:
            n = base64url_to_long(key["n"])
            e = base64url_to_long(key["e"])
            return RSAAlgorithm.from_jwk({"kty": "RSA", "n": key["n"], "e": key["e"]})
    raise ValueError(f"找不到 kid={kid} 的公鑰")
