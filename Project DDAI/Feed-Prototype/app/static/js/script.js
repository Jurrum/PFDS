// app/static/js/script.js

document.addEventListener("DOMContentLoaded", () => {
  createFeedbackContainer();
  reloadCategories();
  hookUploadForm();
});

function hookUploadForm() {
  const uploadForm = document.getElementById("uploadForm");
  if (!uploadForm) return;
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
    .then(() => {
      showFeedback("Your post was created!", "success");
      setTimeout(() => window.location.href = "/", 800);
    })
    .catch(err => {
      console.error(err);
      showFeedback("Could not upload post.", "error");
    });
  });
}

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
          const q = btn.dataset.id === "" 
                    ? "" 
                    : `?category=${encodeURIComponent(name)}`;
          loadFeed(q);
          showFeedback(`Filtered to "${btn.textContent}"`, "info");
        });
      });

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
    if (!name) return showFeedback("Please enter a category name.", "error");

    fetch("/categories", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ name })
    })
    .then(r => r.json())
    .then(json => {
      if (json.error) throw new Error(json.error);
      showFeedback(`Category "${name}" added`, "success");
      reloadCategories();
    })
    .catch(err => {
      console.error(err);
      showFeedback("Failed to add category: " + err.message, "error");
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
        const el = createPostElement(post);
        feed.appendChild(el);
      });
      showFeedback("Feed updated", "info");
    })
    .catch(err => {
      console.error("Error loading feed:", err);
      showFeedback("Error loading feed", "error");
    });
}

function createPostElement(post) {
  const feed = document.getElementById("feed");
  const postEl = document.createElement("div");
  postEl.className = "post";
  postEl.dataset.id = post.id;
  postEl.draggable = true;

  // text + image
  if (post.text)  postEl.innerHTML += `<p>${post.text}</p>`;
  if (post.image) postEl.innerHTML += `<img src="${post.image}" alt="Post Image">`;

  // actions container
  const actions = document.createElement("div");
  actions.className = "actions";

  // like/dislike buttons
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
    const b = document.createElement("button");
    b.className = "rating-btn";
    b.textContent = n;
    b.dataset.id = post.id;
    b.dataset.value = n;
    scaleRow.appendChild(b);
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

  // open scale on click
  likeBtn.addEventListener("click", () => openScale("like"));
  dislikeBtn.addEventListener("click", () => openScale("dislike"));

  function openScale(type) {
    question.textContent = type === "like"
      ? "How much do you like this content?"
      : "How much do you dislike this content?";
    actions.style.display     = "none";
    ratingScale.style.display = "flex";
    ratingScale.dataset.type  = type;
  }

  // handle 1–5 rating clicks
  scaleRow.querySelectorAll(".rating-btn").forEach(b => {
    b.addEventListener("click", () => {
      const id   = b.dataset.id;
      const val  = parseInt(b.dataset.value, 10);
      const type = ratingScale.dataset.type;

      fetch(`/posts/${id}/rate`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ value: val })
      })
      .then(() => {
        const sym = type === "like" ? "👍" : "👎";
        actions.innerHTML = `<button class="${type}-btn">${sym} ${val}</button>`;
        ratingScale.style.display = "none";
        actions.style.display     = "flex";
        showFeedback(`You rated this ${type} ${val}/5`, "success");
      })
      .then(() => maybeGenerate())
      .catch(console.error);
    });
  });

  // swipe to rate = 3
  const hammer = new Hammer(postEl);
  hammer.get("pan").set({ direction: Hammer.DIRECTION_HORIZONTAL });
  hammer.on("pan", ev => {
    postEl.style.transform = `translateX(${ev.deltaX}px)`;
    likeOv.style.opacity    = ev.deltaX>0 ? Math.min(ev.deltaX/100,1) : 0;
    dislikeOv.style.opacity = ev.deltaX<0 ? Math.min(-ev.deltaX/100,1) : 0;
  });
  hammer.on("panend", ev => {
    const thr = 100;
    if (Math.abs(ev.deltaX)>thr) {
      postEl.style.transition = "transform .2s ease-out, opacity .2s";
      postEl.style.transform  = ev.deltaX>0 ? "translateX(100%)" : "translateX(-100%)";
      postEl.style.opacity    = "0";
      setTimeout(() => {
        fetch(`/posts/${post.id}/rate`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ value: 3 })
        })
        .catch(console.error)
        .finally(() => {
          postEl.remove();
          showFeedback("You swiped—rated 3/5!", "info");
          maybeGenerate();
        });
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

  // drag & drop for reranking
  postEl.addEventListener("dragstart", () => {
    postEl.classList.add("dragging");
  });
  postEl.addEventListener("dragend", () => {
    postEl.classList.remove("dragging");
  });

  // allow drop on feed
  postEl.addEventListener("dragover", e => {
    e.preventDefault();
    const dragging = document.querySelector(".dragging");
    if (!dragging) return;
    const boxes = [...feed.querySelectorAll(".post:not(.dragging)")];
    const afterEl = boxes.reduce((closest, child) => {
      const boxRect = child.getBoundingClientRect();
      const offset = e.clientY - boxRect.top - boxRect.height / 2;
      return offset < 0 && offset > closest.offset
        ? { offset, element: child }
        : closest;
    }, { offset: -Infinity }).element;
    if (afterEl) feed.insertBefore(dragging, afterEl);
    else feed.appendChild(dragging);
  });

  postEl.addEventListener("drop", () => {
    sendReorder();
    showFeedback("Algorithm: noted your preferred order!", "info");
  });

  return postEl;
}

function maybeGenerate() {
  let count = parseInt(localStorage.getItem("ratingCount") || "0", 10) + 1;
  localStorage.setItem("ratingCount", count);
  if (count % 3 !== 0) return;

  const active = document.querySelector(".cat-pill.active");
  const cat    = active?.dataset.name || null;

  fetch("/generate", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ category: cat, count: 3 })
  })
  .then(res => {
    if (!res.ok) throw new Error("Generation failed");
    return res.json();
  })
  .then(newPosts => {
    newPosts.forEach(p => document.getElementById("feed")
      .appendChild(createPostElement(p)));
    showFeedback(`3 new ${cat||'general'} posts generated`, "success");
  })
  .catch(err => console.error(err));
}

function sendReorder() {
  const feed = document.getElementById("feed");
  const order = Array.from(feed.children)
    .map(el => parseInt(el.dataset.id, 10));
  const active = document.querySelector(".cat-pill.active");
  const category = active?.dataset.name || null;

  fetch("/posts/reorder", {
    method: "POST",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify({ order, category })
  })
  .catch(console.error);
}

// ——— Feedback “toaster” ———

function createFeedbackContainer() {
  const c = document.createElement("div");
  c.id = "feedbackContainer";
  document.body.appendChild(c);
}

function showFeedback(message, type="info", duration=3000) {
  const container = document.getElementById("feedbackContainer");
  const msg = document.createElement("div");
  msg.className = `feedback-message ${type}`;
  msg.textContent = message;
  container.appendChild(msg);
  setTimeout(() => {
    msg.classList.add("hide");
    msg.addEventListener("transitionend", () => msg.remove());
  }, duration);
}
