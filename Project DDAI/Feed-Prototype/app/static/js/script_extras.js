// app/static/js/script_extras.js

(() => {
  let draggingEl = null;

  // ——— Helper: show a toast message ———
  function showToast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    toastZone.appendChild(t);
    t.addEventListener("animationend", e => {
      if (e.animationName === "fadeout") t.remove();
    });
  }

  // ——— Helper: persist current order to server ———
  function persistOrder() {
    const feed = document.getElementById("feed");
    const order = Array.from(feed.children).map(el => +el.dataset.id);
    const active = document.querySelector(".cat-pill.active");
    const cat = active?.dataset.name || null;

    fetch("/posts/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order, category: cat })
    }).catch(console.error);
  }

  // ——— On initial load, inject top bar + toast container ———
  document.addEventListener("DOMContentLoaded", () => {
    // 1) Top-bar goes just beneath the category pills
    const catBar = document.getElementById("categoryButtons");
    window.topBar = document.createElement("div");
    topBar.id = "drag-top-bar";
    topBar.innerHTML = `
      <div class="top-drop unknown-zone">
        <span class="icon">❓</span>
        <span class="label">Don't know</span>
      </div>
      <div class="top-drop love-zone">
        <span class="icon">⭐️</span>
        <span class="label">Love this</span>
      </div>
      <div class="top-drop hate-zone">
        <span class="icon">🗑️</span>
        <span class="label">Hate this</span>
      </div>
    `;
    catBar.after(topBar);

    // 2) Toast container at bottom center
    window.toastZone = document.createElement("div");
    toastZone.id = "toast-container";
    document.body.appendChild(toastZone);
  });

  // ——— Monkey-patch loadFeed to wire up Hammer.js interactions ———
  if (typeof window.loadFeed === "function") {
    const originalLoad = window.loadFeed;
    window.loadFeed = (query = "") => {
      originalLoad(query);

      // Wait until posts are rendered
      setTimeout(() => {
        const feed = document.getElementById("feed");
        feed.querySelectorAll(".post").forEach(el => {
          // Clean up old Hammer instance
          if (el._hammer) el._hammer.destroy();

          const hammer = new Hammer(el);
          el._hammer = hammer;
          hammer.get("pan").set({ direction: Hammer.DIRECTION_ALL, threshold: 5 });

          hammer.on("panstart", () => {
            draggingEl = el;
            topBar.style.display = "flex";
          });

          hammer.on("panmove", ev => {
            el.style.transform = `translate(${ev.deltaX}px, ${ev.deltaY}px)`;
          });

          hammer.on("panend", ev => {
            // Determine if released over one of the three zones
            const cx = ev.center.x, cy = ev.center.y;
            const inUnknown = hitTest(".unknown-zone", cx, cy);
            const inLove    = hitTest(".love-zone",    cx, cy);
            const inHate    = hitTest(".hate-zone",    cx, cy);

            if (inUnknown || inLove || inHate) {
              // Map zones → rating
              const val = inLove  ? 5
                        : inHate  ? 1
                        : /*unknown*/ 3;
              fetch(`/posts/${el.dataset.id}/rate`, {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({ value: val })
              })
              .then(() => {
                el.remove();
                showToast(
                  inLove  ? "⭐️ You loved it!"
                  : inHate ? "🗑️ You hated it!"
                  : "❓ You marked unknown!"
                );
                persistOrder();
              })
              .catch(console.error);

            } else {
              // Otherwise treat as manual reorder → persist new order
              persistOrder();
            }

            // Reset transform and hide bar
            el.style.transition = "transform 0.2s ease-out";
            el.style.transform  = "";
            setTimeout(() => el.style.transition = "", 200);

            topBar.style.display = "none";
            draggingEl = null;
          });
        });
      }, 50);
    };
  }

  // ——— Hit-test a drop cell by selector and point ———
  function hitTest(selector, x, y) {
    const zone = document.querySelector(selector);
    if (!zone) return false;
    const rect = zone.getBoundingClientRect();
    return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
  }
})();
