/* 閱讀設定（字級、對比）。
 * 沒有 JavaScript 時，網站仍以預設樣式完整可讀；這支程式只負責「記住並套用使用者的偏好」。
 * 偏好只存在這個瀏覽器的 localStorage，不會傳到任何伺服器。
 */
(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "asdtw-prefs";

  function load() {
    try {
      var v = JSON.parse(localStorage.getItem(KEY) || "{}");
      return v && typeof v === "object" ? v : {};
    } catch (e) {
      return {};
    }
  }
  function save(p) {
    try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* 私密模式等情況：忽略 */ }
  }
  function apply(p) {
    if (p.text) root.setAttribute("data-text", p.text);
    if (p.contrast) root.setAttribute("data-contrast", p.contrast);
  }

  var prefs = load();
  apply(prefs); // 在 <head> 載入時立刻套用，避免畫面閃動

  document.addEventListener("DOMContentLoaded", function () {
    var panel = document.querySelector("[data-prefs]");
    if (!panel) return;
    panel.hidden = false;

    var status = panel.querySelector("[data-prefs-status]");
    var labels = {
      text: { "1": "標準字級", "2": "大字級", "3": "特大字級", "4": "最大字級" },
      contrast: { "default": "預設配色", "high": "高對比" }
    };

    function currentContrast() {
      if (prefs.contrast) return prefs.contrast;
      return window.matchMedia && window.matchMedia("(prefers-contrast: more)").matches ? "high" : "default";
    }
    function sync() {
      var text = prefs.text || "1";
      var contrast = currentContrast();
      panel.querySelectorAll("[data-pref-text]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-pref-text") === text));
      });
      panel.querySelectorAll("[data-pref-contrast]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-pref-contrast") === contrast));
      });
    }
    function announce(msg) {
      if (!status) return;
      status.textContent = "";
      window.setTimeout(function () { status.textContent = msg; }, 50);
    }

    panel.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      if (btn.hasAttribute("data-pref-text")) {
        prefs.text = btn.getAttribute("data-pref-text");
        announce("已切換為" + labels.text[prefs.text]);
      } else if (btn.hasAttribute("data-pref-contrast")) {
        prefs.contrast = btn.getAttribute("data-pref-contrast");
        announce("已切換為" + labels.contrast[prefs.contrast]);
      } else if (btn.hasAttribute("data-pref-reset")) {
        prefs = {};
        root.removeAttribute("data-text");
        root.removeAttribute("data-contrast");
        announce("已還原為預設設定");
        save(prefs);
        sync();
        return;
      } else {
        return;
      }
      apply(prefs);
      save(prefs);
      sync();
    });

    sync();
  });
})();
