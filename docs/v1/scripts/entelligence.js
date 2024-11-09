function initEntelligence() {
  const script = document.getElementById("entelligence-chat");

  if (!script) {
    const chatScript = document.createElement("script");
    chatScript.type = "module";
    chatScript.id = "entelligence-chat";
    chatScript.src =
      "https://d345f39z3arwqc.cloudfront.net/entelligence-chat.js";

    // Create initialization script
    const initScript = document.createElement("script");
    initScript.type = "module";
    initScript.textContent = `
    window.EntelligenceChat.init({
      analyticsData: {
        repoName: "agentops",
        organization: "AgentOps-AI", 
        apiKey: "1234567890",
        theme: 'dark'
      }
    });
  `;

    // Append initialization script after chat script loads
    chatScript.onload = () => {
      document.body.appendChild(initScript);
    };

    // Append chat script to the body
    document.body.appendChild(chatScript);
  }
}

window.addEventListener("load", function () {
  initEntelligence();
});
