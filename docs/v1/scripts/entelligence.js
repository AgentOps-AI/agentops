function initEntelligence() {
  const script = document.getElementById("entelligence-chat");

  if (!script) {
    const chatScript = document.createElement("script");
    chatScript.type = "module";
    chatScript.id = "entelligence-chat";
    chatScript.src =
      "https://dujj2xy9pc7vi.cloudfront.net/vanilla/entelligence-chat.umd.js";
    chatScript.defer = true; // Add defer to load after HTML parsing

    // Create initialization script
    const initScript = document.createElement("script");
    initScript.type = "module";
    initScript.textContent = `
    window.EntelligenceChat.init({
      analyticsData: {
        repoName: "agentops",
        organization: "AgentOps-AI",
        apiKey: "YrodtbYbdqWNKOraqTFuVWPQ5k6yqWHTevojAI_w0Zg",
        theme: 'dark',
        companyName: "AgentOps"
      }
    });
  `;

    // Add to head instead of body for better performance
    const head = document.getElementsByTagName("head")[0];
    head.appendChild(chatScript);

    // Initialize after script loads
    chatScript.onload = () => {
      document.head.appendChild(initScript);
    };
  }
}

// Run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initEntelligence);
} else {
  initEntelligence();
}
