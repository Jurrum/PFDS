// app/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
    // Build categories + initial feed
    reloadCategories();
  
    // AJAX upload form (if present)
    const uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", e => {
        e.preventDefault();
        const fd = new FormData(uploadForm);
        fetch("/upload", {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          body: fd
        })
        .then(r => {
          if (!r.ok) throw new Error("Upload failed");
          return r.json();
        })
        .then(() => window.location.href = "/")
        .catch(err => {
          console.error(err);
          alert("Could not upload post.");
        });
      });
    }
  });
  
  function reloadCategories() {
    const container = document.getElementById("categoryButtons");
    container.innerHTML = "";
  
    fetch("/categories")
      .then(r => r.json())
      .then(cats => {
        container.appendChild(makePill("", "All"));
        cats.forEach(c => container.appendChild(makePill(c.id, c.name)));
  
        const plus = document.createElement("button");
        plus.className = "category-button add-cat-icon";
        plus.textContent = "+";
        plus.title = "Add category";
        plus.addEventListener("click", showAddCategoryInput);
        container.appendChild(plus);
  
        container.querySelectorAll(".cat-pill").forEach(btn => {
          btn.addEventListener("click", () => {
            container.querySelectorAll(".cat-pill").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const name = btn.dataset.name;
            const q = btn.dataset.id === "" ? "" : `?category=${encodeURIComponent(name)}`;
            loadFeed(q);
          });
        });
  
        // initial load
        const active = container.querySelector(".cat-pill.active");
        const q = active.dataset.id === "" 
          ? "" 
          : `?category=${encodeURIComponent(active.dataset.name)}`;
        loadFeed(q);
      })
      .catch(err => {
        console.error(err);
        loadFeed();
      });
  }
  
  function showAddCategoryInput(e) {
    const plusBtn = e.currentTarget;
    const container = plusBtn.parentNode;
    if (container.querySelector("#newCategory")) return;
  
    const input = document.createElement("input");
    input.id = "newCategory";
    input.placeholder = "New category…";
    input.style.cssText = "padding:4px;border:1px solid #ccc;border-radius:4px;margin-left:6px;";
  
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
        console.error(err);
        alert("Failed to add category: " + err.message);
      });
    });
  
    plusBtn.after(input, confirm);
    input.focus();
  }
  
  function makePill(id, label) {
    const btn = document.createElement("button");
    btn.className = `category-button cat-pill${id === "" ? " active" : ""}`;
    btn.dataset.id   = id + "";
    btn.dataset.name = id === "" ? "" : label;
    btn.textContent  = label;
    return btn;
  }
  
  function loadFeed(query = "") {
    fetch("/get_posts" + query)
      .then(r => r.json())
      .then(posts => {
        const feed = document.getElementById("feed");
        feed.innerHTML = "";
  
        posts.forEach(post => {
          // create post card
          const postEl = document.createElement("div");
          postEl.className = "post";
  
          if (post.text)  postEl.innerHTML += `<p>${post.text}</p>`;
          if (post.image) postEl.innerHTML += `<img src="${post.image}" alt="Post Image">`;
  
          // actions: like + dislike buttons
          const actions = document.createElement("div");
          actions.className = "actions";
          const likeBtn    = document.createElement("button");
          likeBtn.className    = "like-btn";
          likeBtn.textContent  = "👍";
          const dislikeBtn = document.createElement("button");
          dislikeBtn.className = "dislike-btn";
          dislikeBtn.textContent = "👎";
          actions.append(likeBtn, dislikeBtn);
          postEl.appendChild(actions);
  
          // rating scale (hidden)
          const ratingScale = document.createElement("div");
          ratingScale.className = "rating-scale";
          ratingScale.style.display = "none";
  
          const question = document.createElement("p");
          question.className = "rating-question";
          question.style.margin = "0 0 8px";
          ratingScale.appendChild(question);
  
          const scaleRow = document.createElement("div");
          [1,2,3,4,5].forEach(n => {
            const btn = document.createElement("button");
            btn.className = "rating-btn";
            btn.textContent = n;
            btn.dataset.id    = post.id;
            btn.dataset.value = n;
            scaleRow.appendChild(btn);
          });
          ratingScale.appendChild(scaleRow);
          postEl.appendChild(ratingScale);
  
          // swipe overlays
          const likeOv    = document.createElement("div");
          likeOv.className    = "overlay like-overlay";
          likeOv.textContent  = "❤️ Like";
          const dislikeOv = document.createElement("div");
          dislikeOv.className = "overlay dislike-overlay";
          dislikeOv.textContent = "💔 Dislike";
          postEl.append(likeOv, dislikeOv);
  
          // open rating on click
          likeBtn.addEventListener("click", () => {
            question.textContent = "How much do you like this content?";
            actions.style.display      = "none";
            ratingScale.style.display  = "flex";
            ratingScale.dataset.type   = "like";
          });
          dislikeBtn.addEventListener("click", () => {
            question.textContent = "How much do you dislike this content?";
            actions.style.display      = "none";
            ratingScale.style.display  = "flex";
            ratingScale.dataset.type   = "dislike";
          });
  
          // handle rating selection
          scaleRow.querySelectorAll(".rating-btn").forEach(btn => {
            btn.addEventListener("click", () => {
              const id   = btn.dataset.id;
              const val  = parseInt(btn.dataset.value, 10);
              const type = ratingScale.dataset.type;  // "like" or "dislike"
  
              fetch(`/posts/${id}/rate`, {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({ value: val })
              })
              .then(() => {
                // show chosen rating on a single button
                const symbol   = type === "like" ? "👍" : "👎";
                const btnClass = type === "like" ? "like-btn" : "dislike-btn";
                actions.innerHTML = `<button class="${btnClass}">${symbol} ${val}</button>`;
  
                // hide scale, show actions again
                ratingScale.style.display = "none";
                actions.style.display     = "flex";
              })
              .catch(console.error);
            });
          });
  
          // swipe to rate = 3
          const hammer = new Hammer(postEl);
          hammer.get("pan").set({ direction: Hammer.DIRECTION_HORIZONTAL });
          hammer.on("pan", ev => {
            postEl.style.transform = `translateX(${ev.deltaX}px)`;
            likeOv.style.opacity    = ev.deltaX > 0 ? Math.min(ev.deltaX/100,1) : 0;
            dislikeOv.style.opacity = ev.deltaX < 0 ? Math.min(-ev.deltaX/100,1) : 0;
          });
          hammer.on("panend", ev => {
            const thr = 100;
            if (Math.abs(ev.deltaX) > thr) {
              postEl.style.transition = "transform .2s ease-out, opacity .2s";
              postEl.style.transform  = ev.deltaX>0 ? "translateX(100%)" : "translateX(-100%)";
              postEl.style.opacity    = "0";
              setTimeout(() => {
                fetch(`/posts/${post.id}/rate`, {
                  method: "POST",
                  headers: {"Content-Type":"application/json"},
                  body: JSON.stringify({ value: 3 })
                }).catch(console.error);
                postEl.remove();
              }, 200);
            } else {
              postEl.style.transition = "transform .2s ease-out";
              postEl.style.transform  = "";
              likeOv.style.opacity = dislikeOv.style.opacity = 0;
              postEl.addEventListener("transitionend", () => {
                postEl.style.transition = "";
              }, { once: true });
            }
          });
  
          feed.appendChild(postEl);
        });
      })
      .catch(err => console.error("Error loading feed:", err));
  }
  