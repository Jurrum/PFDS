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
            
            // Apply sophisticated recommendation algorithm
            posts = recommendPosts(posts);
            
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

function recommendPosts(posts) {
    // More sophisticated recommendation logic
    return posts.sort((a, b) => {
        let aScore = (a.likes || 0) * 2 + (a.shares || 0) * 3 + (a.comments || 0) * 1.5;
        let bScore = (b.likes || 0) * 2 + (b.shares || 0) * 3 + (b.comments || 0) * 1.5;
        return bScore - aScore;
    });
}
