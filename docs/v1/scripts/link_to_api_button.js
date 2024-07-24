// NOTE: The copy button is copying the old non-displayed API key, need to add a click listener and set
// the new textContent to be copied

function patternFindAndAddButton(apiKeyButtonHTML) {
  const targetClasses = document.querySelectorAll(".api-key-container");
  const codeElements = [];
  targetClasses.forEach(element => {
    codeElements.push(element.querySelector('code'));
  });

  const apiKeyPattern = /AGENTOPS_API_KEY/g;
  const tokenOperatorPattern1 = /<span class="token operator">&lt;<\/span>YOUR API KEY<span class="token operator">&gt;<\/span>/g;
  const tokenOperatorPattern2 = /<span class="token operator">&lt;<\/span>INSERT YOUR API KEY HERE<span class="token operator">&gt;<\/span>/g;

  // Process the collected elements
  codeElements.forEach(element => {
    console.log(element.textContent)
    const containsApiKeyPattern = element.textContent.includes("AGENTOPS_API_KEY");
    const containsTokenOperatorPattern1 = element.textContent.includes("<YOUR API KEY>");
    const containsTokenOperatorPattern2 = element.textContent.includes("<INSERT YOUR API KEY HERE>");

    if (containsTokenOperatorPattern1 || containsTokenOperatorPattern2 || containsApiKeyPattern) {
      const button = document.createElement('a');
      button.className = 'api-key-button';
      button.href = "https://app.agentops.ai/settings/projects";
      button.target = "_blank";
      button.textContent = 'Get API Key';
      element.parentNode.parentNode.parentNode.insertBefore(button, element.nextSibling);
      if (containsTokenOperatorPattern1) {
        button.classList.add('pattern1');
      } else if (containsTokenOperatorPattern2) {
        button.classList.add('pattern2');
      } else if (containsApiKeyPattern) {
        button.classList.add('pattern0');
      }
    }
  });
}

// Note that functions cannot be named the same thing across script files if copy-pasting this to add new scripts
function addAPIEventListeners() { // would change to button
  console.log("new listeners added")
  document.querySelectorAll('li, a').forEach(element => {
    // this can instead add a button before the "adjust-api-key" span that when clicked adjusts the API key
    element.addEventListener('click', () => {
      setTimeout(patternFindAndAddButton, 50);
    });
  });
}

window.addEventListener('load', function() {
  patternFindAndAddButton();
  const apiObserver = new MutationObserver(addAPIEventListeners);
  apiObserver.observe(document.body, { childList: true, subtree: true });
});