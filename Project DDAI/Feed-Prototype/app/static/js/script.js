document.addEventListener("DOMContentLoaded", () => {
    loadFeed();
  
    const uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
      uploadForm.addEventListener("submit", function (e) {
        e.preventDefault();
  
        const formData = new FormData(uploadForm);
  
        fetch("/upload", {
          method: "POST",
          body: formData
        })
          .then(res => {
            if (!res.ok) throw new Error("Upload failed");
            return res.json();
          })
          .then(data => {
            console.log("Uploaded:", data);
            // Go back to the feed and refresh it
            window.location.href = "/";
          })
          .catch(err => {
            console.error("Error uploading post:", err);
            alert("Could not upload post. Please try again.");
          });
      });
    }
  });
  
  function loadFeed() {
    fetch("/get_posts")
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
  
        // attach handlers after DOM insertion
        document.querySelectorAll('.like-btn').forEach(btn =>
          btn.addEventListener('click', () => {
            fetch(`/posts/${btn.dataset.id}/like`, { method: 'POST' })
              .then(res => res.json())
              .then(data => { btn.textContent = `👍 ${data.likes}`; });
          })
        );
        document.querySelectorAll('.dislike-btn').forEach(btn =>
          btn.addEventListener('click', () => {
            fetch(`/posts/${btn.dataset.id}/dislike`, { method: 'POST' })
              .then(res => res.json())
              .then(data => { btn.textContent = `👎 ${data.dislikes}`; });
          })
        );
      })
      .catch(err => console.error("Error loading feed:", err));
  }
  