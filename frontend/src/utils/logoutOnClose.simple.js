/**
 * logoutOnClose.simple.js
 *
 * Beginner-friendly version.
 * - No tokens, no cookies.
 * - Uses sendBeacon (best during unload) and falls back to fetch keepalive.
 * - Optionally only logs out when the *last tab* of your app closes.
 *
 * Usage (ES modules):
 *   import { registerLogoutOnClose } from "./logoutOnClose.simple.js";
 *   const unregister = registerLogoutOnClose({
 *     apiBaseUrl: "https://api.example.com",
 *     username: "alice",
 *     onlyLastTab: true,  // default true
 *     appKey: "my-app"    // optional: unique key for your app
 *   });
 *
 * Usage (script tag):
 *   <script src="/path/logoutOnClose.simple.js"></script>
 *   <script>
 *     window.LogoutOnClose.registerLogoutOnClose({
 *       apiBaseUrl: "https://api.example.com",
 *       username: "alice"
 *     });
 *   </script>
 */

/**
 * @param {Object} opts
 * @param {string} opts.apiBaseUrl - e.g. "https://api.example.com"
 * @param {string} opts.username   - the username used by your logout endpoint
 * @param {boolean} [opts.onlyLastTab=true] - only logout when the last tab closes
 * @param {string} [opts.appKey="app"] - a name used for localStorage coordination
 * @returns {() => void} unregister function
 */
export function registerLogoutOnClose(opts) {
  const {
    apiBaseUrl,
    username,
    onlyLastTab = true,
    appKey = "app",
  } = opts || {};

  if (!apiBaseUrl || !username) {
    console.warn("[logoutOnClose] Missing apiBaseUrl or username; not registering.");
    return () => {};
  }

  const endpoint = `${String(apiBaseUrl).replace(/\/+$/, "")}/users/${encodeURIComponent(username)}/logout`;
  const openTabsKey = `${appKey}:openTabs`;
  const tabId = (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;

  // --- localStorage helpers (simple & safe) ---
  function readOpenTabs() {
    try {
      const raw = localStorage.getItem(openTabsKey);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch {
      return [];
    }
  }
  function writeOpenTabs(arr) {
    try {
      localStorage.setItem(openTabsKey, JSON.stringify(arr));
    } catch {}
  }
  function addThisTab() {
    const arr = readOpenTabs().filter(id => id !== tabId);
    arr.push(tabId);
    writeOpenTabs(arr);
  }
  function removeThisTab() {
    const arr = readOpenTabs().filter(id => id !== tabId);
    writeOpenTabs(arr);
    return arr; // remaining after removal
  }

  // --- how we send the logout ---
  const payloadJson = JSON.stringify({
    reason: "page-closed",
    at: new Date().toISOString(),
  });

  function sendLogout() {
    // Prefer sendBeacon (works best during unload)
    if ("sendBeacon" in navigator) {
      try {
        const blob = new Blob([payloadJson], { type: "application/json" });
        navigator.sendBeacon(endpoint, blob);
        return;
      } catch {}
    }
    // Fallback: keepalive fetch (no headers, no cookies)
    try {
      fetch(endpoint, {
        method: "POST",
        body: payloadJson,
        headers: { "Content-Type": "application/json" },
        keepalive: true,
      }).catch(() => {});
    } catch {}
  }

  let sent = false;
  function logoutOnce() {
    if (sent) return;
    sent = true;
    sendLogout();
  }

  function onPageHide() {
    const remaining = removeThisTab();
    if (!onlyLastTab) {
      logoutOnce();
      return;
    }
    // Tiny delay so simultaneous closing tabs can update storage first
    setTimeout(() => {
      const after = readOpenTabs();
      if (after.length === 0) {
        logoutOnce();
      }
    }, 0);
  }

  function onBeforeUnload() {
    // Keep the list in sync even if pagehide doesn't fire
    removeThisTab();
  }

  // Register
  addThisTab();
  window.addEventListener("pagehide", onPageHide);
  window.addEventListener("beforeunload", onBeforeUnload);

  // Return an unregister function
  return function unregister() {
    window.removeEventListener("pagehide", onPageHide);
    window.removeEventListener("beforeunload", onBeforeunload);
    removeThisTab();
  };
}

// Browser global for <script> usage
if (typeof window !== "undefined") {
  window.LogoutOnClose = window.LogoutOnClose || {};
  window.LogoutOnClose.registerLogoutOnClose = registerLogoutOnClose;
}