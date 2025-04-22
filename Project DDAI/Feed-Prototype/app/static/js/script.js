// app/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
    // Build the categories bar (pills + add‑icon) and then load the feed
    reloadCategories();
  
    // Upload form handler
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
        .then(() => {
          window.location.href = "/";
        })
        .catch(err => {
          console.error("Error uploading post:", err);
          alert("Could not upload post. Please try again.");
        });
      });
    }
  });
  
  /**
   * Fetches categories, renders the pill bar + the “+” icon,
   * hooks up all handlers, then triggers the initial feed load.
   */
  function reloadCategories() {
    const container = document.getElementById("categoryButtons");
    container.innerHTML = "";  // clear everything
  
    fetch("/categories")
      .then(res => res.json())
      .then(cats => {
        // 1) The “All” pill
        container.appendChild(makePill("", "All"));
  
        // 2) One pill per category
        cats.forEach(c => {
          container.appendChild(makePill(c.id, c.name));
        });
  
        // 3) The “+” icon to add new categories
        const plusBtn = document.createElement("button");
        plusBtn.className = "category-button add-cat-icon";
        plusBtn.textContent = "+"; 
        plusBtn.title = "Add category";
        plusBtn.addEventListener("click", showAddCategoryInput);
        container.appendChild(plusBtn);
  
        // 4) Hook up pill clicks (filter feed)
        container.querySelectorAll(".cat-pill").forEach(btn => {
          btn.addEventListener("click", () => {
            // deactivate others, activate this one
            container.querySelectorAll(".cat-pill").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
  
            // build query string
            const name = btn.dataset.name;
            const query = btn.dataset.id === "" 
              ? "" 
              : `?category=${encodeURIComponent(name)}`;
            loadFeed(query);
          });
        });
  
        // 5) Initial feed load with whichever pill is active (defaults to “All”)
        const active = container.querySelector(".cat-pill.active");
        const qs = active.dataset.id === "" 
          ? "" 
          : `?category=${encodeURIComponent(active.dataset.name)}`;
        loadFeed(qs);
      })
      .catch(err => {
        console.error("Could not load categories:", err);
        loadFeed();  // fallback
      });
  }
  
  /** Show the input + confirm button to add a new category. */
  function showAddCategoryInput(event) {
    const plusBtn = event.currentTarget;
    const container = plusBtn.parentNode;
  
    // if the input is already shown, do nothing
    if (container.querySelector("#newCategory")) return;
  
    // create input
    const input = document.createElement("input");
    input.type = "text";
    input.id = "newCategory";
    input.placeholder = "New category…";
    input.style.cssText = "padding:4px;border-radius:4px;border:1px solid #ccc;margin-left:6px;";
  
    // create confirm button
    const confirmBtn = document.createElement("button");
    confirmBtn.id = "confirmAddCategoryBtn";
    confirmBtn.textContent = "Add";
    confirmBtn.style.cssText = "margin-left:6px;padding:4px 8px;border-radius:4px;";
    confirmBtn.addEventListener("click", () => {
      const name = input.value.trim();
      if (!name) return alert("Please enter a category name.");
  
      fetch("/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      })
      .then(res => res.json())
      .then(json => {
        if (json.error) throw new Error(json.error);
        reloadCategories();  // rebuild the pill bar (hides input)
      })
      .catch(err => {
        console.error("Add category failed:", err);
        alert("Failed to add category: " + err.message);
      });
    });
  
    // insert the input + confirm button right after the plus icon
    plusBtn.after(input, confirmBtn);
    input.focus();
  }
  
  /** Create a category‑pill button. */
  function makePill(id, label) {
    const btn = document.createElement("button");
    btn.className = `category-button cat-pill${id === "" ? " active" : ""}`;
    btn.dataset.id   = id + "";              // empty string for “All”
    btn.dataset.name = id === "" ? "" : label;
    btn.textContent  = label;
    return btn;
  }
  
  /**
   * Fetch and display posts.
   * @param {string} query — optional query string (e.g. "?category=Sports")
   */
  function loadFeed(query = "") {
    fetch("/get_posts" + query)
      .then(res => res.json())
      .then(posts => {
        console.log("Feed data:", posts);
        const feed = document.getElementById("feed");
        feed.innerHTML = "";
  
        posts.forEach(post => {
          const postEl = document.createElement("div");
          postEl.className = "post";
  
          if (post.text)  postEl.innerHTML += `<p>${post.text}</p>`;
          if (post.image) postEl.innerHTML += `<img src="${post.image}" alt="Post Image">`;
  
          postEl.innerHTML += `
            <div class="actions">
              <button class="like-btn"    data-id="${post.id}">👍 ${post.likes || 0}</button>
              <button class="dislike-btn" data-id="${post.id}">👎 ${post.dislikes || 0}</button>
            </div>
          `;
          feed.appendChild(postEl);
        });
  
        // bind like/dislike
        document.querySelectorAll(".like-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            fetch(`/posts/${btn.dataset.id}/like`, { method: "POST" })
              .then(r => r.json()).then(d => btn.textContent = `👍 ${d.likes}`);
          })
        );
        document.querySelectorAll(".dislike-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            fetch(`/posts/${btn.dataset.id}/dislike`, { method: "POST" })
              .then(r => r.json()).then(d => btn.textContent = `👎 ${d.dislikes}`);
          })
        );
      })
      .catch(err => console.error("Error loading feed:", err));
  }
  