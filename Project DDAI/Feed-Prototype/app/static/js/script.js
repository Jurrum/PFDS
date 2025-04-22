// app/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
    // Build category bar + initial feed
    reloadCategories();
  
    // Hook the upload form (AJAX + redirect)
    const uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
  
        fetch("/upload", {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          body: formData
        })
        .then(res => {
          if (!res.ok) throw new Error("Upload failed");
          return res.json();
        })
        .then(() => { window.location.href = "/"; })
        .catch(err => {
          console.error("Upload error:", err);
          alert("Could not upload post. Please try again.");
        });
      });
    }
  });
  
  /**
   * Rebuilds the category‑pill bar (including the “+” icon),
   * then does the initial loadFeed() once it’s ready.
   */
  function reloadCategories() {
    const container = document.getElementById("categoryButtons");
    container.innerHTML = "";  // clear out old pills
  
    fetch("/categories")
      .then(res => res.json())
      .then(cats => {
        // “All” pill
        container.appendChild(makePill("", "All"));
  
        // existing categories
        cats.forEach(c => container.appendChild(makePill(c.id, c.name)));
  
        // “+” button for adding a new category
        const plus = document.createElement("button");
        plus.className = "category-button add-cat-icon";
        plus.textContent = "+";
        plus.title = "Add category";
        plus.addEventListener("click", showAddCategoryInput);
        container.appendChild(plus);
  
        // pill click = filter feed
        container.querySelectorAll(".cat-pill").forEach(btn => {
          btn.addEventListener("click", () => {
            container.querySelectorAll(".cat-pill").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
  
            const name = btn.dataset.name;
            const query = btn.dataset.id === ""
              ? ""
              : `?category=${encodeURIComponent(name)}`;
            loadFeed(query);
          });
        });
  
        // initial feed load
        const active = container.querySelector(".cat-pill.active");
        const qs = active.dataset.id === ""
          ? ""
          : `?category=${encodeURIComponent(active.dataset.name)}`;
        loadFeed(qs);
      })
      .catch(err => {
        console.error("Could not load categories:", err);
        loadFeed();
      });
  }
  
  /** Injects the “new category” input + confirm button inline. */
  function showAddCategoryInput(e) {
    const plusBtn = e.currentTarget;
    const container = plusBtn.parentNode;
  
    // if already showing, bail
    if (container.querySelector("#newCategory")) return;
  
    // create the text input
    const input = document.createElement("input");
    input.id = "newCategory";
    input.placeholder = "New category…";
    input.style.cssText = "padding:4px;border-radius:4px;border:1px solid #ccc;margin-left:6px;";
  
    // create the confirm button
    const confirm = document.createElement("button");
    confirm.textContent = "Add";
    confirm.style.cssText = "margin-left:6px;padding:4px 8px;border-radius:4px;";
    confirm.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) return alert("Please enter a category name.");
  
      fetch("/categories", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ name })
      })
      .then(r => r.json())
      .then(json => {
        if (json.error) throw new Error(json.error);
        reloadCategories();
      })
      .catch(err => {
        console.error("Add category failed:", err);
        alert("Failed to add category: " + err.message);
      });
    });
  
    plusBtn.after(input, confirm);
    input.focus();
  }
  
  /** Builds a single category‑pill button. */
  function makePill(id, label) {
    const btn = document.createElement("button");
    btn.className = `category-button cat-pill${id === "" ? " active" : ""}`;
    btn.dataset.id   = id + "";
    btn.dataset.name = id === "" ? "" : label;
    btn.textContent  = label;
    return btn;
  }
  
  /**
   * Fetches posts (optionally filtered) and renders them,
   * wiring up both button‐based and swipe‐based like/dislike.
   */
  function loadFeed(query = "") {
    fetch("/get_posts" + query)
      .then(res => res.json())
      .then(posts => {
        console.log("Feed data:", posts);
        const feed = document.getElementById("feed");
        feed.innerHTML = "";
  
        posts.forEach(post => {
          // build the card
          const postEl = document.createElement("div");
          postEl.className = "post";
  
          if (post.text)  postEl.innerHTML += `<p>${post.text}</p>`;
          if (post.image) postEl.innerHTML += `<img src="${post.image}" alt="Post Image">`;
  
          // like/dislike buttons fallback
          postEl.innerHTML += `
            <div class="actions">
              <button class="like-btn"    data-id="${post.id}">👍 ${post.likes || 0}</button>
              <button class="dislike-btn" data-id="${post.id}">👎 ${post.dislikes || 0}</button>
            </div>
          `;
  
          // create swipe overlays
          const likeOverlay    = document.createElement("div");
          likeOverlay.className    = "overlay like-overlay";
          likeOverlay.textContent  = "👍 Like";
          postEl.appendChild(likeOverlay);
  
          const dislikeOverlay = document.createElement("div");
          dislikeOverlay.className = "overlay dislike-overlay";
          dislikeOverlay.textContent = "💔 Dislike";
          postEl.appendChild(dislikeOverlay);
  
          // attach swipe behavior via Hammer.js
          const hammer = new Hammer(postEl);
          hammer.get("pan").set({ direction: Hammer.DIRECTION_HORIZONTAL });
          hammer.on("pan", ev => {
            // move card
            postEl.style.transform = `translateX(${ev.deltaX}px)`;
            // show appropriate overlay
            if (ev.deltaX > 0) {
              likeOverlay.style.opacity    = Math.min(ev.deltaX / 100, 1);
              dislikeOverlay.style.opacity = 0;
            } else {
              dislikeOverlay.style.opacity = Math.min(-ev.deltaX / 100, 1);
              likeOverlay.style.opacity    = 0;
            }
          });
  
          hammer.on("panend", ev => {
            const threshold = 100;
            // Like
            if (ev.deltaX > threshold) {
              // animate out
              postEl.style.transition = "transform 0.2s ease-out, opacity 0.2s";
              postEl.style.transform  = "translateX(100%)";
              postEl.style.opacity    = "0";
              setTimeout(() => {
                fetch(`/posts/${post.id}/like`, { method: "POST" })
                  .catch(console.error);
                postEl.remove();
              }, 200);
  
            // Dislike
            } else if (ev.deltaX < -threshold) {
              postEl.style.transition = "transform 0.2s ease-out, opacity 0.2s";
              postEl.style.transform  = "translateX(-100%)";
              postEl.style.opacity    = "0";
              setTimeout(() => {
                fetch(`/posts/${post.id}/dislike`, { method: "POST" })
                  .catch(console.error);
                postEl.remove();
              }, 200);
  
            // Revert
            } else {
              postEl.style.transition = "transform 0.2s ease-out";
              postEl.style.transform  = "";
              likeOverlay.style.opacity    = 0;
              dislikeOverlay.style.opacity = 0;
              postEl.addEventListener("transitionend", () => {
                postEl.style.transition = "";
              }, { once: true });
            }
          });
  
          // append to feed
          feed.appendChild(postEl);
        });
  
        // also bind click handlers as fallback
        document.querySelectorAll(".like-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            const id = btn.dataset.id;
            fetch(`/posts/${id}/like`, { method: "POST" })
              .then(r => r.json())
              .then(d => btn.textContent = `👍 ${d.likes}`)
              .catch(console.error);
          })
        );
        document.querySelectorAll(".dislike-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            const id = btn.dataset.id;
            fetch(`/posts/${id}/dislike`, { method: "POST" })
              .then(r => r.json())
              .then(d => btn.textContent = `👎 ${d.dislikes}`)
              .catch(console.error);
          })
        );
      })
      .catch(err => console.error("Error loading feed:", err));
  }
  