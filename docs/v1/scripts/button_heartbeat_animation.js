// Placeholder for anime.js animation

function addHeartbeatListeners() {
  setTimeout(() => {
    document.querySelectorAll('li, a').forEach(element => {
      element.addEventListener('click', function() {
        drawHeartbeat();
      });
    });
  }, 50);
}

window.addEventListener('load', function() {
  drawHeartbeat();
  const observer = new MutationObserver(addHeartbeatListeners);
  observer.observe(document.body, { childList: true, subtree: true });
});