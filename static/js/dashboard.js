export let dash = true;  // 預設是 1 狀態
export const dashImages = [];
export { toggleDash, logout }; // 將函式導出，便於在其他模組中使用

let currentLayer = true;
window.toggleDash = toggleDash; // 將函式綁定到 window 物件上，便於在 HTML 中使用
window.logout = logout; // 將函式綁定到 window 物件上，便於在 HTML 中使用   

document.getElementById("user-title").innerText = `歡迎回來，${htmlUnescape(user.sub)}`;
// 執行預載
preloadImages([ ...dashImages]);
// document.body.style.backgroundImage = `url("${dashImages[1]}")`;


// 將 html 轉換為可讀的文字
function htmlUnescape(str) {
    const div = document.createElement("div");
    div.innerHTML = str;
    return div.textContent;
}

// 顯示使用者資訊

// ➤ 改為漂亮的條列式資訊展示
const userInfoDiv = document.getElementById("user-info");
userInfoDiv.innerHTML = `
    <div><span class="key">🙋 使用者名稱：</span><span class="value">${htmlUnescape(user.sub)}</span></div>
    <div><span class="key">🧑‍💼 角色：</span><span class="value">${user.role}</span></div>
    <div><span class="key">🆔 AAGUID：</span><span class="value">${user.aaguid}</span></div>
    <div><span class="key">🔢 簽章次數：</span><span class="value">${user.signCount}</span></div>
    <div><span class="key">⏳ JWT 剩餘有效時間：</span><span class="value" id="jwt-remaining-time">計算中…</span></div>
`;



// ➤ 這裡是登出按鈕的點擊事件
async function logout() {
    // 清除 cookie
    const options = await fetch("/logout", {
        method: "POST",
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
        },
    });
    // 重整頁面
    location.reload();
}


for (let i = 1; i < 3; i++) {
    dashImages.push(`/static/images/dash${i}.png`);
}
// 通用 preload 函式
export function preloadImages(imageList) {
    imageList.forEach(src => {
        const img = new Image();
        img.src = src;
    });
}
// 預載完成後，隨機選擇一張圖片作為背景
async function toggleDash() {
    dash= !dash;
    switchBackground(dash ? dashImages[0] : dashImages[1]);
    // document.body.style.backgroundImage = `url("${dashImages[dash ? 0 : 1]}")`;
}


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



// JWT剩餘時間的計算函式
function getJwtRemainingTime(exp) {
    const expTime = exp * 1000;  // 轉成毫秒
    const nowTime = Date.now();
    return expTime - nowTime;
}
// 將毫秒轉換為可讀格式
function formatRemainingTime(ms) {
    const totalSec = Math.floor(ms / 1000);
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;

    return `${hours} 小時 ${minutes} 分鐘 ${seconds} 秒`;
}
// 顯示 JWT 倒數並更新畫面
function displayJwtRemainingTime(exp, elementId) {
    const updateRemainingTime = () => {
        const remainingMs = getJwtRemainingTime(exp);
        document.getElementById(elementId).textContent = remainingMs > 0
            ? formatRemainingTime(remainingMs)
            : 'JWT 已過期';
    };

    updateRemainingTime();
    setInterval(updateRemainingTime, 1000);
}

// 啟動倒數計時器，持續更新
displayJwtRemainingTime(user.exp, "jwt-remaining-time");