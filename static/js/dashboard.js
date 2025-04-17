// 將 html 轉換為可讀的文字
function htmlUnescape(str) {
    const div = document.createElement("div");
    div.innerHTML = str;
    return div.textContent;
}

// 顯示使用者資訊
document.getElementById("user-title").innerText = `歡迎回來，${htmlUnescape(user.sub)}`;

// ➤ 改為漂亮的條列式資訊展示
const userInfoDiv = document.getElementById("user-info");
userInfoDiv.innerHTML = `
            <div><span class="key">🙋 使用者名稱：</span><span class="value">${htmlUnescape(user.sub)}</span></div>
            <div><span class="key">🧑‍💼 角色：</span><span class="value">${user.role}</span></div>
            <div><span class="key">🆔 AAGUID：</span><span class="value">${user.aaguid}</span></div>
    <div><span class="key">🔢 簽章次數：</span><span class="value">${user.signCount}</span></div>
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


export let dash = true;  // 預設是 1 狀態
export const dashImages = [];

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
// 執行預載
preloadImages([ ...dashImages]);
document.body.style.backgroundImage = `url("${dashImages[1]}")`;
// 預載完成後，隨機選擇一張圖片作為背景
async function toggleDash() {
    dash= !dash;
    document.body.style.backgroundImage = `url("${dashImages[dash ? 0 : 1]}")`;
}

window.toggleDash = toggleDash; // 將函式綁定到 window 物件上，便於在 HTML 中使用
window.logout = logout; // 將函式綁定到 window 物件上，便於在 HTML 中使用   

export { toggleDash, logout }; // 將函式導出，便於在其他模組中使用