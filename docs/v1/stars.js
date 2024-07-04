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

window.addEventListener('load', function() {
  updateStars();
  document.querySelectorAll('li, a').forEach(item => {
    item.addEventListener('click', updateStars);
  });
});