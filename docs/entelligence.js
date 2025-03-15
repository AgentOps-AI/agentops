function injectShadowStyles(interval) {
  const container = document.getElementById("entelligence-chat-root");

  if (container && container.shadowRoot) {    
    const shadow = container.shadowRoot;

    // Create a div to hold the widget content
    const widgetContainer = document.createElement("div");
    shadow.appendChild(widgetContainer);
    // Create and insert style element at top of shadow root
    const style = document.createElement("style");
    shadow.prepend(style);   

    let css = ''

    // Load and inject CSS
   fetch("https://dujj2xy9pc7vi.cloudfront.net/entelligence-chat.css")
      .then(r => r.text())
      .then(styles => {
        const style = document.createElement("style");        
        style.textContent = styles;
        shadow.prepend(style);
        css = styles;
      })
      .finally(() => {        
        const headStyle = document.createElement('style');
        headStyle.textContent = css;
        document.head.prepend(headStyle);
      });
    clearInterval(interval);
  }
}

function initEntelligence() {
  const script = document.getElementById("entelligence-chat");

  if (!script) {
    const chatScript = document.createElement("script");
    chatScript.type = "module";
    chatScript.id = "entelligence-chat";
    chatScript.src =
      "https://dujj2xy9pc7vi.cloudfront.net/vanilla/entelligence-chat.es.js";
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

      const interval = setInterval(() => {
        injectShadowStyles(interval);
      }, 1000);
    };
  }
}

// Run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initEntelligence);
} else {
  initEntelligence();
}
