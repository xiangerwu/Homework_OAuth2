// 這段程式碼是用來處理 OAuth2.0 的登入流程，
// 主要是與 Server A 進行授權，並在成功後取得 token，

const ImgPathname =  window.location.pathname;
// 提前綁定 message listener
// 這樣當 Server A 回傳訊息時，B 端就能接收到
// 這段程式碼會在 Server B 的登入頁面中執行，
window.addEventListener("message", function (event) {

    console.log("[B] 收到來自 A 的訊息：", event.data);

    const origin_state      = localStorage.getItem("oauth_state");
    const received_JWT      = event.data.token;
    const received_state    = event.data.state;
    const received_status   = event.data.status;

    console.log("A →", received_state, "B →", origin_state);
    console.log(received_state === origin_state); // 應為 true

    if (received_state !== origin_state) {
        alert("⚠ 驗證失敗：state 不一致，可能為偽造請求！");
        console.warn("[警告] 收到不合法的 state！原始：", origin_state, " 實際：", received_state);
        return;
    }
    // ✅ state 驗證通過，處理登入結果
    if (received_status === "login_success") {

        if (!received_JWT) {
            alert("⚠ 登入失敗：未收到 JWT");
            return;
        }

        // ✅ 寫入 B 端 cookie，便於後續驗證
        document.cookie = `token=${received_JWT}; path=/; max-age=3600; SameSite=Strict`;

        // ✅ 登入成功
       
    } else {
        alert("⚠ 登入失敗：status 為非 login_success");
        console.warn("[B] 非預期狀態：", received_status);
        return;
    }  
});

// 當 DOM 內容載入完成後，檢查 URL 參數
window.addEventListener("DOMContentLoaded", function () {
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");

    // 判斷不同的錯誤狀況
    if (error === "access_denied") {
        alert("⚠ 使用者拒絕授權！");
    } else if (error === "invalid_request") {
        alert("⚠ 無效的請求！請檢查網址或聯絡管理員。");
    } else if (error === "server_error") {
        alert("⚠ 伺服器錯誤，請稍後再試。");
    } else if (error === "unauthorized_client") {
        alert("⚠ 未經授權的客戶端！請聯絡管理員。");
    } else if (error === "invalid_token") {    
        alert("⚠ 無效的 token！請重新登入。");
    } else if (error === "missing_code") {
        alert("⚠  未提供JWT，請重新登入。");
    }
    // 如果有錯誤，則清除 token cookie
    if(error) {
    document.cookie = "token=; path=/; max-age=0"; // 清除 token cookie
    }
});


// 這裡是登入按鈕的點擊事件
// 會彈出一個視窗，並導向 Server A 的登入頁面
// 這個視窗會在 Server A 完成授權後關閉，並回傳JWT
function redirectToAuth() {
    // source 是 用來分辨登入要求來源網站
    const source = "oauth.akitawan.moe";
    // dist 是 用來寫入驗證目的網站
    const dist = source; // 單一網站所以來源跟目的是同一個
    // redirectUri 是 Server B 的回調網址，當 Server A 完成授權後會導向這個網址
    const redirectUri = encodeURIComponent(`${window.location.origin}/oauth/callback`);
    // responseType 是 Server A 要回傳的 token 類型，這裡使用 Code
    // code != JWT
    const responseType = "JWT"; 
    // scope 是 Server A 要授權的範圍，這裡使用 openid
    const scope = "openid";
    // state 是用來防止 CSRF 攻擊的隨機字串，
    // 這裡使用 crypto.randomUUID() 生成一個隨機的 UUID
    const state = crypto.randomUUID();

    // 將 state 儲存到 localStorage，便於驗證
    localStorage.setItem("oauth_state", state);

    // ✅ 建立參數物件
    const params = new URLSearchParams({
        source: source,
        dist:dist,
        redirect_uri: redirectUri,
        response_type: responseType,
        scope: scope,
        state: state,
        });
    // ✅ 組合網址
    const authUrl = `https://proxy.akitawan.moe/wu/fido2/oauth2/authorize?${params.toString()}`;

    console.log("[B] 打開授權頁 URL：", authUrl);
    
    // 開啟 popup 視窗
    const popup = window.open(
        authUrl,
        "oauth_popup",
        "width=750,height=400,resizable=no,scrollbars=yes"
    );

    if (popup) {
        popup.focus();
    }

    // ⏱️ Optional：監控視窗是否關閉
    const timer = setInterval(() => {
        if (popup && popup.closed) {
            clearInterval(timer);
            console.log("[B] 授權視窗已關閉");
            window.location.reload(); // 重新載入頁面
        }
    }, 1000);
}


// 以下是背景特效
let isLight = false;  // 預設是關燈狀態

export const darkImages = [];
export const lightImages = [];



for (let i = 1; i < 3 ; i++) {
    darkImages.push(`${ImgPathname}static/images/dark${i}.png`);
}
for (let i = 1; i < 3; i++) {
    lightImages.push(`${ImgPathname}static/images/light${i}.png`);
}

// 通用 preload 函式
export function preloadImages(imageList) {
    imageList.forEach(src => {
        const img = new Image();
        img.src = src;
    });
}

// 執行預載
preloadImages([...darkImages, ...lightImages]);
// 預載完成後，隨機選擇一張圖片作為背景
async function toggleLight() {
    isLight = !isLight;
    const images = isLight ? lightImages : darkImages;
    const randomIndex = Math.floor(Math.random() * images.length);
    switchBackground(images[randomIndex]);
    // document.body.style.backgroundImage = `url("${images[randomIndex]}")`;
}

window.toggleLight = toggleLight; // 將函式綁定到 window 物件上，便於在 HTML 中使用
window.redirectToAuth = redirectToAuth; // 將函式綁定到 window 物件上，便於在 HTML 中使用
export { toggleLight, redirectToAuth }; // 將函式導出，便於在其他模組中使用


let currentLayer = true;

function switchBackground(url) {
    const layer1 = document.getElementById('bg-layer-1');
    const layer2 = document.getElementById('bg-layer-2');

    if (currentLayer) {
        layer2.style.backgroundImage = `url(${url})`;
        layer2.style.zIndex = -1;
        layer1.style.zIndex = -2;
    } else {
        layer1.style.backgroundImage = `url(${url})`;
        layer1.style.zIndex = -1;
        layer2.style.zIndex = -2;
    }

    currentLayer = !currentLayer;
}
