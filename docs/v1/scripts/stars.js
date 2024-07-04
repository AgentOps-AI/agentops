function updateStars() {
  fetch("https://api.github.com/repos/AgentOps-AI/agentops")
    .then((response) => response.json())
    .then((data) => {
      const stars = Math.ceil(data.stargazers_count / 100) * 100 + 100;
      const dataContainer = document.getElementById("stars-text");
      dataContainer.innerHTML = `${stars.toLocaleString()}th`;
    })
    .catch((error) => {
      // console.error("Github Stars pull error:", error);
    });
}


// Note that functions cannot be named the same thing across script files if copy-pasting this to add new scripts
function addStarsEventListeners() {
  setTimeout(() => {
    document.querySelectorAll('li, a').forEach(element => {
      element.addEventListener('click', () => {
        setTimeout(updateStars, 50);
      });
    });
  }, 50);
}

window.addEventListener('load', function() {
  updateStars();
  const starsObserver = new MutationObserver(addStarsEventListeners);
  starsObserver.observe(document.body, { childList: true, subtree: true });
});