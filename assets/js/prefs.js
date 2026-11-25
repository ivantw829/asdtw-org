/* 閱讀設定（字級、配色）。
 * 沒有 JavaScript 時，網站仍以預設樣式完整可讀；這支程式只負責「記住並套用使用者的偏好」。
 * 偏好只存在這個瀏覽器的 localStorage，不會傳到任何伺服器。
 */
(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "asdtw-prefs";

  var MSG = {
    zh: {
      text: { "1": "已切換為標準字級", "2": "已切換為大字級", "3": "已切換為特大字級", "4": "已切換為最大字級" },
      theme: { "default": "已切換為預設配色", "dark": "已切換為深色", "high": "已切換為高對比" },
      reset: "已還原為預設設定"
    },
    en: {
      text: { "1": "Switched to default text size", "2": "Switched to large text size", "3": "Switched to extra large text size", "4": "Switched to largest text size" },
      theme: { "default": "Switched to default theme", "dark": "Switched to dark theme", "high": "Switched to high contrast theme" },
      reset: "Reset to default settings"
    },
    ja: {
      text: { "1": "標準の文字サイズに切り替えました", "2": "大の文字サイズに切り替えました", "3": "特大の文字サイズに切り替えました", "4": "最大の文字サイズに切り替えました" },
      theme: { "default": "標準配色に切り替えました", "dark": "ダーク配色に切り替えました", "high": "ハイコントラスト配色に切り替えました" },
      reset: "初期設定に戻しました"
    }
  };

  function locale() {
    var lang = (root.getAttribute("lang") || "").toLowerCase();
    if (lang.indexOf("en") === 0) return "en";
    if (lang.indexOf("ja") === 0) return "ja";
    return "zh";
  }

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
    if (p.theme) root.setAttribute("data-theme", p.theme);
  }

  var prefs = load();
  apply(prefs); // 在 <head> 載入時立刻套用，避免畫面閃動

  document.addEventListener("DOMContentLoaded", function () {
    var panel = document.querySelector("[data-prefs]");
    if (!panel) return;
    panel.hidden = false;

    var status = panel.querySelector("[data-prefs-status]");
    var dict = MSG[locale()];

    function currentTheme() {
      if (prefs.theme) return prefs.theme;
      var mq = function (q) { return window.matchMedia && window.matchMedia(q).matches; };
      if (mq("(prefers-contrast: more)")) return "high";
      return mq("(prefers-color-scheme: dark)") ? "dark" : "default";
    }
    function sync() {
      var text = prefs.text || "1";
      var theme = currentTheme();
      panel.querySelectorAll("[data-pref-text]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-pref-text") === text));
      });
      panel.querySelectorAll("[data-pref-theme]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-pref-theme") === theme));
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
        announce(dict.text[prefs.text]);
      } else if (btn.hasAttribute("data-pref-theme")) {
        prefs.theme = btn.getAttribute("data-pref-theme");
        announce(dict.theme[prefs.theme]);
      } else if (btn.hasAttribute("data-pref-reset")) {
        prefs = {};
        root.removeAttribute("data-text");
        root.removeAttribute("data-theme");
        announce(dict.reset);
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
