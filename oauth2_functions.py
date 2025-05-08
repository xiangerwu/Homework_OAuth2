import requests
import base64
import os
import json
from jwcrypto import jwk, jwt, jwe
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from base64 import urlsafe_b64decode


g_IP = "0.0.0.0"                        # Flask 在 Render 上應該綁定所有 IP
RP_NAME = "My OAuth2.0 App"             # 可保持不變，或改成你的應用名稱
g_port = 5001                           # 預設 Flask 埠號
# RP_ID = "oauth.akitawan.moe"            # 改成你的正式域名
RP_ID = "proxy.akitawan.moe"  # Fido2 用到
ORIGIN = "akitawan.moe" # 改成你的正式域名，且使用 HTTPS

g_secret_key = os.urandom(24)
B_Client_id = "BtA-client"              # 這是 Server B與A 的 client_id

# 取得公開金鑰
def get_public_key_from_jwks(jwks_url: str, kid: str):
    res = requests.get(jwks_url, timeout=5)
    jwks_data = res.json()
    for key in jwks_data["keys"]:
        if key.get("kid") == kid:
            return jwk.JWK(**key)
    raise ValueError(f"找不到 kid={kid} 的公鑰")

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

# 驗證與解密 JWT
def verify_user_jwt(jwt_token: str):
    """
    驗證來自 A 的 RS256 JWT，並使用 B 的私鑰解密 payload

    回傳:
        payload (dict), None：驗證成功
        None, error (str)：任一階段失敗
    """
    try:
        print("開始執行驗證 JWT 函式")
        # 讀取 A 網站的公開金鑰（從 JWKS 取得）
        print("下載公鑰 A")
        public_key = get_public_key_from_jwks(
            "https://proxy.akitawan.moe/wu/fido2/oauth2/jwks.json", "A1"
        )
        # 讀取 B 的私鑰並解密
        print("讀取私鑰 B")
        with open("RSA_key/private_key.pem", "rb") as f:
            private_key = jwk.JWK.from_pem(f.read())
        
        # 驗證簽章是否正確（RS256）
        print("用公鑰 A 驗證簽章")
        token_verified = jwt.JWT(jwt=jwt_token, key=public_key)

        print("📦 取得加密的 JWE Payload")
        encrypted_jwe_str = token_verified.claims
        jwe_token = jwe.JWE()
        print("解密 payload")
        jwe_token.deserialize(encrypted_jwe_str, key=private_key)

        # Step 4: 解析 payload 為 JSON
        payload = json.loads(jwe_token.payload.decode("utf-8"))
        print("✅ 解密完成，Payload:", payload)


        return payload, None
    
    except jwt.JWTExpired as e:
        return None, f"❌ JWT 過期: {str(e)}"
    except jwt.JWTInvalidClaimFormat as e:
        return None, f"❌ Claim 格式錯誤: {str(e)}"
    except jwk.JWException as e:
        return None, f"❌ 金鑰錯誤: {str(e)}"
    except Exception as e:
        return None, f"❌ 驗證或解密失敗: {str(e)}"
