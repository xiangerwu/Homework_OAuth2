import requests
import base64
import jwt
import os
import json
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from base64 import urlsafe_b64encode,urlsafe_b64decode

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


# 函式名稱: base64url_uint
# 作用: 將整數轉換為 Base64URL 編碼的字串（無符號）
# 參數: 整數
def base64url_uint(val: int) -> str:
    """
    將整數轉換為 Base64URL 編碼的字串（無符號）
    - 去掉 '=' padding
    - 使用 URL-safe base64 編碼
    """
    byte_length = (val.bit_length() + 7) // 8
    byte_array = val.to_bytes(byte_length, 'big')  # 轉成 byte
    b64 = base64.urlsafe_b64encode(byte_array).rstrip(b"=")  # URL-safe + 無填充
    return b64.decode("utf-8")

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

# 
def verify_user_jwt(jwt_token: str):
    """
    驗證來自 A 的 RS256 JWT，並使用 B 的私鑰解密 payload

    回傳:
        payload (dict), None：驗證成功
        None, error (str)：任一階段失敗
    """
    try:
        print("開始執行驗證 JWT 函式")
        # 1️⃣ 讀取 A 網站的公開金鑰（從 JWKS 取得）
        unverified_header = jwt.get_unverified_header(jwt_token)
        kid = unverified_header.get("kid")

        if not kid:
            return None, "❌ JWT 未含 kid，無法選擇對應公鑰"
        # 
        print("下載公開金鑰")
        public_key = get_public_key_from_jwks(
            "https://fido2-web.akitawan.moe/oauth2/.well-known/jwks.json", kid
        )

        # 2️⃣ 驗證簽章是否正確（RS256）
        try:
            print("用公鑰 A 驗證簽章")
            jws_payload = jwt.decode(
                jwt_token,
                public_key,
                algorithms=["RS256"],
                issuer="https://fido2-web.akitawan.moe",
            )
        except jwt.ExpiredSignatureError:
            return None, "❌ Token 已過期"
        except jwt.InvalidTokenError as e:
            return None, f"❌ Token 驗證失敗: {str(e)}"
        except jwt.InvalidSignatureError:
            return None, str("無效的簽名")
        except jwt.DecodeError:
            return None, str("解碼錯誤")
        except jwt.InvalidIssuerError:
            return None, str("無效的發行者")
        except Exception as e:
            return None, str(f"其他錯誤: {e}")

        # 3️⃣ 讀取 B 自己的私鑰（PEM）
        print("讀取私鑰 B讀取私鑰 B")
        with open("RSA_key/private_key.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        # 4️⃣ 用 RS256 解密 payload（實際是 base64url 編碼的亂碼字串）
        print("先解出 base64 編碼為 byte")
        encrypted_bytes = urlsafe_b64decode(jws_payload + '==')
        print("將 payload 解碼")
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            )
        )
        payload = json.loads(decrypted.decode("utf-8"))
        return payload, None

    except Exception as e:
        return None, f"❌ 解密或驗章過程錯誤：{str(e)}"
