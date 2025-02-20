document.addEventListener("DOMContentLoaded", function () {
    loadFeed();

    document.getElementById("uploadForm")?.addEventListener("submit", function (e) {
        e.preventDefault();
        let formData = new FormData(this);

        fetch("/upload", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                console.log("Post saved:", data);
                window.location.href = "/"; // Redirect to home after posting
            }
        })
        .catch(error => console.error("Error:", error));
    });
});

function loadFeed() {
    fetch("/get_posts")
        .then(response => response.json())
        .then(posts => {
            console.log("Loaded posts:", posts);
            const feed = document.getElementById("feed");
            feed.innerHTML = "";
            posts.forEach(post => {
                let postElement = document.createElement("div");
                postElement.className = "post";
                if (post.text) postElement.innerHTML += `<p>${post.text}</p>`;
                if (post.image) postElement.innerHTML += `<img src="${post.image}" alt="Post Image">`;
                feed.appendChild(postElement);
            });
        })
        .catch(error => console.error("Error:", error));
}
