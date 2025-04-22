// app/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
    const categoryButtonsContainer = document.getElementById("categoryButtons");
    let currentCategory = "";
  
    // 1) Fetch categories and build buttons
    fetch("/categories")
      .then(res => res.json())
      .then(cats => {
        // Always include an "All" button
        categoryButtonsContainer.appendChild(
          createCategoryButton("", "All")
        );
  
        cats.forEach(cat => {
          categoryButtonsContainer.appendChild(
            createCategoryButton(cat, cat)
          );
        });
  
        // Default to "All"
        setActiveCategoryButton("");
        loadFeed("");
      })
      .catch(err => console.error("Could not load categories:", err));
  
    // 2) Delegate click events on buttons
    categoryButtonsContainer.addEventListener("click", (e) => {
      if (!e.target.classList.contains("category-button")) return;
      const selected = e.target.dataset.category;
      currentCategory = selected;
      setActiveCategoryButton(selected);
      loadFeed(selected);
    });
  
    // 3) Upload form handler (if on upload page)
    const uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", e => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        fetch("/upload", { method: "POST", body: formData })
          .then(res => {
            if (!res.ok) throw new Error("Upload failed");
            return res.json();
          })
          .then(() => window.location.href = "/")
          .catch(err => {
            console.error("Upload error:", err);
            alert("Could not upload. Try again.");
          });
      });
    }
  });
  
  /**
   * Creates a category button element.
   * @param {string} category — the category value ("" = All)
   * @param {string} label — text to display
   */
  function createCategoryButton(category, label) {
    const btn = document.createElement("button");
    btn.className = "category-button";
    btn.dataset.category = category;
    btn.textContent = label;
    return btn;
  }
  
  /**
   * Highlights the active category button.
   * @param {string} category — the selected category value
   */
  function setActiveCategoryButton(category) {
    document.querySelectorAll(".category-button").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.category === category);
    });
  }
  
  /**
   * Fetches and displays posts, optionally filtered by category.
   * @param {string} category
   */
  function loadFeed(category = "") {
    let url = "/get_posts";
    if (category) url += `?category=${encodeURIComponent(category)}`;
  
    fetch(url)
      .then(res => res.json())
      .then(posts => {
        const feed = document.getElementById("feed");
        feed.innerHTML = "";
  
        posts.forEach(post => {
          const postEl = document.createElement("div");
          postEl.className = "post";
  
          if (post.text) postEl.innerHTML += `<p>${post.text}</p>`;
          if (post.image) postEl.innerHTML += `<img src="${post.image}" alt="Post Image">`;
  
          postEl.innerHTML += `
            <div class="actions">
              <button class="like-btn" data-id="${post.id}">👍 ${post.likes || 0}</button>
              <button class="dislike-btn" data-id="${post.id}">👎 ${post.dislikes || 0}</button>
            </div>
          `;
  
          feed.appendChild(postEl);
        });
  
        // Attach like/dislike handlers
        document.querySelectorAll(".like-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            fetch(`/posts/${btn.dataset.id}/like`, { method: "POST" })
              .then(res => res.json())
              .then(data => { btn.textContent = `👍 ${data.likes}`; })
              .catch(err => console.error("Error liking post:", err));
          })
        );
        document.querySelectorAll(".dislike-btn").forEach(btn =>
          btn.addEventListener("click", () => {
            fetch(`/posts/${btn.dataset.id}/dislike`, { method: "POST" })
              .then(res => res.json())
              .then(data => { btn.textContent = `👎 ${data.dislikes}`; })
              .catch(err => console.error("Error disliking post:", err));
          })
        );
      })
      .catch(err => console.error("Error loading feed:", err));
  }
  