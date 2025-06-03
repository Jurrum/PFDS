// app/static/js/script.js

// Track post view times
let viewStartTime = null;
let currentPostId = null;
let viewTimeInterval = null;

// Track view time at regular intervals
function startViewTimeTracking(postId) {
    // Stop any existing tracking
    stopViewTimeTracking();
    
    // Start new tracking
    currentPostId = postId;
    viewStartTime = Date.now();
    
    // Send updates every 5 seconds while the post is being viewed
    viewTimeInterval = setInterval(() => {
        if (viewStartTime && currentPostId) {
            const viewTime = (Date.now() - viewStartTime) / 1000; // Convert to seconds
            sendViewTime(currentPostId, viewTime);
        }
    }, 5000);
}

function stopViewTimeTracking() {
    if (viewTimeInterval) {
        clearInterval(viewTimeInterval);
        viewTimeInterval = null;
    }
    
    // Send final view time when user stops viewing
    if (viewStartTime && currentPostId) {
        const viewTime = (Date.now() - viewStartTime) / 1000; // Convert to seconds
        sendViewTime(currentPostId, viewTime);
    }
    
    viewStartTime = null;
    currentPostId = null;
}

function sendViewTime(postId, viewTime) {
    fetch(`/posts/${postId}/view_time`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ view_time: viewTime })
    })
    .then(response => {
        if (!response.ok) {
            console.error('Failed to track view time');
        }
    })
    .catch(error => {
        console.error('Error tracking view time:', error);
    });
}

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

  // Define the 5 main categories we want to show
  const mainCategories = ["Technology", "Science", "Health", "Entertainment", "Lifestyle"];
  
  // Always add the 'All' button first
  container.appendChild(makePill("", "All"));
  
  // Add the 5 main categories
  mainCategories.forEach(category => {
    container.appendChild(makePill(category, category));
  });

  // Set up event listeners for the category buttons
  container.querySelectorAll(".cat-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      container.querySelectorAll(".cat-pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const category = btn.dataset.id === "" ? "" : btn.dataset.id;
      const q = category ? `?category=${encodeURIComponent(category)}` : "";
      loadFeed(q);
      showFeedback(`Filtered to "${btn.textContent}"`, "info");
    });
  });

  // Load the feed with the active category (default to "All")
  const active = container.querySelector(".cat-pill.active") || container.querySelector(".cat-pill");
  const category = active && active.dataset.id !== "" ? active.dataset.id : "";
  const q = category ? `?category=${encodeURIComponent(category)}` : "";
  loadFeed(q);
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

/**
 * Load posts into the feed, with proper view time tracking
 * @param {string} query - Optional query string for filtering posts
 */
function loadFeed(query = "") {
  // Stop any active view time tracking before refreshing the feed
  stopViewTimeTracking();
  
  // Show a loading indicator
  const feed = document.getElementById("feed");
  if (!feed) {
    console.error("Feed container not found");
    return Promise.reject("Feed container not found");
  }
  
  // Add loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'loading-indicator';
  loadingIndicator.textContent = 'Loading posts...';
  
  // Clear existing content and show loading indicator
  feed.innerHTML = '';
  feed.appendChild(loadingIndicator);
  
  return fetch("/get_posts" + query)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      // Remove loading indicator
      if (loadingIndicator.parentNode) {
        loadingIndicator.remove();
      }
      
      // Parse the response - data should be an object with a 'posts' array
      const responseData = data || {};
      const posts = Array.isArray(responseData) ? responseData : (responseData.posts || []);
      
      // Clear the feed
      feed.innerHTML = '';
      
      if (posts.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'empty-feed-message';
        emptyMessage.textContent = 'No posts found. Try a different category or generate new content.';
        feed.appendChild(emptyMessage);
        return [];
      }
      
      // Add posts to the feed
      posts.forEach(post => {
        try {
          const postEl = createPostElement(post);
          if (postEl) {
            feed.appendChild(postEl);
          }
        } catch (error) {
          console.error('Error creating post element:', error);
        }
      });
      
      // Check if we need to generate more posts
      if (posts.length < 5) {
        maybeGenerate();
      }
      
      showFeedback(`Loaded ${posts.length} posts`, "success");
      return posts;
    })
    .catch(error => {
      console.error("Error loading feed:", error);
      
      // Remove loading indicator on error
      if (loadingIndicator.parentNode) {
        loadingIndicator.remove();
      }
      
      // Show error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'error-message';
      errorMessage.textContent = 'Failed to load posts. Please try again.';
      feed.appendChild(errorMessage);
      
      showFeedback("Error loading feed", "error");
      return [];
    });
}

function createPostElement(post) {
  const postEl = document.createElement("div");
  postEl.className = "post";
  postEl.dataset.id = post.id;
  postEl.dataset.category = post.category;
  
  // Track when the post becomes visible in the viewport
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        // Post is visible, start tracking view time
        startViewTimeTracking(post.id);
      } else {
        // Post is no longer visible, stop tracking
        stopViewTimeTracking();
      }
    });
  }, {
    threshold: 0.5 // Consider post visible when 50% is in viewport
  });
  
  // Start observing the post element
  observer.observe(postEl);
  
  // Clean up observer when post is removed
  postEl._observer = observer;

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
      const isPositive = type === "like";

      fetch(`/posts/${id}/rate`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ value: val })
      })
      .then(() => {
        // Update user preferences for this category
        fetch(`/user/preferences/${post.category}`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({ rating: val, is_positive: isPositive })
        }).catch(console.error);

        const sym = type === "like" ? "👍" : "👎";
        actions.innerHTML = `<button class="${type}-btn">${sym} ${val}</button>`;
        ratingScale.style.display = "none";
        actions.style.display     = "flex";
        showFeedback(`You rated this ${type} ${val}/5`, "success");
        
        // Remove the post from the DOM before refreshing
        postEl.remove();
        
        // Refresh the feed to show the updated order
        const activeCat = document.querySelector(".cat-pill.active");
        if (activeCat) {
          const query = activeCat.dataset.name;
          loadFeed(query);
        } else {
          loadFeed();
        }
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
      // Remove the post immediately
      postEl.remove();
      
      // Get current category
      const activeCat = document.querySelector(".cat-pill.active");
      const query = activeCat ? activeCat.dataset.name : '';
      
      // Rate the post
      const rating = ev.deltaX > 0 ? 5 : 1; // 5 for like (right), 1 for dislike (left)
      fetch(`/posts/${post.id}/rate`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ value: rating })
      })
      .then(() => {
        // Refresh the feed with the new order
        loadFeed(query);
      })
      .catch(console.error)
      .finally(() => {
        showFeedback(`You swiped—rated ${rating}/5!`, "info");
        maybeGenerate();
      });
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

/**
 * Generate new posts when needed based on user interaction patterns.
 * This function is called after a user rates a post or when the feed is low on content.
 */
function maybeGenerate() {
  // Stop any active view time tracking during generation
  stopViewTimeTracking();
  
  // Get the active category and feed element
  const active = document.querySelector(".cat-pill.active");
  const feed = document.getElementById("feed");
  
  // Validate we have the required elements
  if (!feed) {
    console.error("Feed container not found");
    return;
  }
  
  // Get current post count in the feed
  const currentPostCount = feed.querySelectorAll(".post").length;
  const minPosts = 5; // Minimum number of posts we want to maintain
  
  // If we have enough posts, no need to generate more
  if (currentPostCount >= minPosts) {
    return;
  }
  
  // Calculate how many posts we need to generate
  const postsToGenerate = minPosts - currentPostCount;
  const category = active?.dataset.name || null;
  
  // Show loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'loading-indicator';
  loadingIndicator.textContent = 'Loading more posts...';
  feed.appendChild(loadingIndicator);
  
  // Make the generation request
  fetch("/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ 
      category: category, 
      count: postsToGenerate 
    })
  })
  .then(res => {
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res.json();
  })
  .then(data => {
    // Remove loading indicator
    if (loadingIndicator.parentNode) {
      loadingIndicator.remove();
    }
    
    // Check if we got valid posts
    if (!data || !data.success || !Array.isArray(data.posts) || data.posts.length === 0) {
      console.warn("No new posts generated or invalid response format");
      return;
    }
    
    // Add new posts to the feed
    data.posts.forEach(post => {
      try {
        const postEl = createPostElement(post);
        if (postEl) {
          feed.appendChild(postEl);
          console.log(`Added new post: ${post.id} in category: ${post.category}`);
        }
      } catch (error) {
        console.error('Error creating post element:', error);
      }
    });
    
    // Show success message if we added any posts
    if (data.posts.length > 0) {
      const categoryName = category || 'general';
      showFeedback(`Added ${data.posts.length} new ${categoryName} posts`, "success");
    }
    
    // If we still don't have enough posts, try again
    if (feed.querySelectorAll(".post").length < minPosts) {
      maybeGenerate();
    }
  })
  .catch(error => {
    console.error("Error generating posts:", error);
    
    // Remove loading indicator on error
    if (loadingIndicator.parentNode) {
      loadingIndicator.remove();
    }
    
    // Only show error if we have no posts at all
    if (currentPostCount === 0) {
      showFeedback("Failed to load posts. Please try again.", "error");
    }
    
    // Retry after a delay if we still need more posts
    if (feed.querySelectorAll(".post").length < minPosts) {
      setTimeout(maybeGenerate, 5000); // Retry after 5 seconds
    }
  });
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
  .then(res => {
    if (!res.ok) {
      throw new Error("Failed to reorder posts");
    }
    return res.json();
  })
  .then(() => {
    // Refresh the feed after successful reorder
    const activeCat = document.querySelector(".cat-pill.active");
    if (activeCat) {
      const query = activeCat.dataset.name;
      loadFeed(query);
    } else {
      loadFeed();
    }
    showFeedback("Feed reordered", "success");
  })
  .catch(err => {
    console.error("Error reordering posts:", err);
    showFeedback("Failed to reorder posts", "error");
  });
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
