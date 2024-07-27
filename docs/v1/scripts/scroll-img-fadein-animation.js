function typeInTerminalText() {
  const pythonTerminal = document.getElementById("python-terminal");
  const terminalCommand = document.getElementById("terminal-command");
  const textsAndElementTargets = [
    {
      text: "python",
      target: pythonTerminal,
      nextTarget: {
        text: "openai_job_post_agent.py",
        target: terminalCommand
      }
    },
    {
      text: "python",
      target: pythonTerminal,
      nextTarget: {
        text: "crew_subreddit_finder_agent.py",
        target: terminalCommand
      }
    },
    {
      text: "python",
      target: pythonTerminal,
      nextTarget: {
        text: "claude_email_reply_agent.py",
        target: terminalCommand
      }
    }
  ]
  const toggleEmptySpace = document.getElementById("toggle-empty-space");
  const inlineCodeImg = document.getElementById("inline-code-img");
  const barelySpace = document.getElementById("barely-space");
  const cursor = document.getElementById("cursor");
  const terminalContentDiv = document.getElementById("terminal-content");
  const terminalContentTexts = [
    [
      "<p style='color: green;'>Successfully posted 32 jobs ✅</p>",
      "<p style='color: red;'>Failed to post 36 jobs ❌</p>",
      "<p>0 errors logged 📝</p>",
    ],
    [
      "<p style='color: green;'>Found 18 relevant subreddits 🎯</p>",
      "<p style='color: red;'>But 47 irrelevant ones 💩</p>",
      "<p>0 hallucinations logged 😵‍💫</p>",
    ],
    [
      "<p style='color: green'>10 perfectly polite emails 🧑‍💼</p>",
      "<p style='color: red;'>3 uses of [$%&# - redacted] 🤬</p>",
      "<p>0 additional insight 🤔</p>"
    ]
  ]
  const imagesSrcs = [
    "https://github.com/AgentOps-AI/agentops/blob/3c03341f5129f9f494ca64ed4e8d03b9a0575db4/docs/images/docs-icons/chat.png?raw=true",
    "https://github.com/AgentOps-AI/agentops/blob/388a8a94603393cd2aa15e1adcd56e7f435839f9/docs/images/docs-icons/crew.png?raw=true",
    "https://github.com/AgentOps-AI/agentops/blob/3c03341f5129f9f494ca64ed4e8d03b9a0575db4/docs/images/docs-icons/claude.png?raw=true"
  ]
  let increment = 0;
  let contentIncrement = 0;

  function addToTerminal(terminalContentDiv, texts) {
    let increment = 0;
    const interval = setInterval(() => {
      if (!terminalContentDiv) return
      terminalContentDiv.innerHTML += texts[increment];
      increment++;
      if (increment === texts.length) {
        clearInterval(interval);
        cursor.classList.remove("off");
        setTimeout(() => {
          terminalContentDiv.innerHTML = null;
          if (pythonTerminal) pythonTerminal.textContent = "";
          terminalCommand.textContent = "";
          inlineCodeImg.classList.remove("on");
          barelySpace.classList.add("off");
          contentIncrement = (contentIncrement + 1) % 3;
        }, 4000);
      }
    }, 1200);
  }

  function typewriterEffect(text, target, nextTarget = null) {
    let i = 0;
    const interval = setInterval(() => {
      if (!target) return
      if (i < text.length) {
        target.textContent += text[i];
        i++;
      } else {
        toggleEmptySpace.classList.remove("off");
        inlineCodeImg.classList.add("on");
        barelySpace.classList.remove("off");
        clearInterval(interval);
        if (nextTarget) {
          setTimeout(() => {
            typewriterEffect(nextTarget.text, nextTarget.target);
          }, 20);
        } else {
          cursor.classList.add("off");
        }
      }
    }, 20);
  }

  typewriterEffect(textsAndElementTargets[contentIncrement].text, textsAndElementTargets[contentIncrement].target, textsAndElementTargets[contentIncrement].nextTarget);
  addToTerminal(terminalContentDiv, terminalContentTexts[contentIncrement]);

  setInterval(() => {
    // this is to catch timeout bugginess with Mint
    if (terminalContentDiv) terminalContentDiv.innerHTML = null;
    if (pythonTerminal) pythonTerminal.textContent = "";
    if (terminalCommand) terminalCommand.textContent = "";
    if (inlineCodeImg) inlineCodeImg.classList.remove("on");
    if (barelySpace) barelySpace.classList.add("off");

    inlineCodeImg.src = imagesSrcs[contentIncrement];
    typewriterEffect(textsAndElementTargets[contentIncrement].text, textsAndElementTargets[contentIncrement].target, textsAndElementTargets[contentIncrement].nextTarget);
    addToTerminal(terminalContentDiv, terminalContentTexts[contentIncrement]);
  }, 10000);
}

function typeInPipText(target) {
  const codeTextFirstPart = "pip install agentops\n\n";
  const codeTextSecondPartComplete = "[▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇] 100% <span style='color: green;'>√</span>";
  const LLMCostCodeText = "\n<span style='font-weight: bold;'>AgentOps:</span> This LLM run cost <span style='color: red;'>$0.26270</span> <span style='color: green;'>√</span>";
  const dashboardText = "\nSee dashboard for full replay: <a href='usage/dashboard-info' style='color: #0088D4; text-decoration: underline;'>https://app.agentops.ai/drilldown?session=SESSION_ID</a> <span style='color: green;'>√</span>";
  let codeSecondIndex = 0;
  target.textContent += "[                                 ]   0%";
  const progressBar = "[                                 ]   0%";
  const progressBarArray = progressBar.split('');
  const progressBarLength = progressBar.length;
  
  const codeTypewriterIntervalSecondPart = setInterval(() => {
    if (target.textContent.includes("99%")) {
      clearInterval(codeTypewriterIntervalSecondPart);
      target.innerHTML = codeTextFirstPart + codeTextSecondPartComplete;
      return;
    }
    if (codeSecondIndex < progressBarLength) {
      if (progressBarArray[codeSecondIndex] === ' ' && codeSecondIndex % 2 === 1) {
        progressBarArray[codeSecondIndex] = '▇';
      }

      let percentageIndexEnd = progressBarArray.indexOf('%');
      let percentage = parseInt(progressBarArray.slice(percentageIndexEnd - 2, percentageIndexEnd).join('')) + 3;
      let percentageString = percentage.toString().padStart(3, ' ');

      target.textContent = codeTextFirstPart + progressBarArray.join('');
      codeSecondIndex++;
      
      for (let i = 0; i < percentageString.length; i++) {
        progressBarArray[percentageIndexEnd - 3 + i] = percentageString[i];
      }
    } else {
      clearInterval(codeTypewriterIntervalSecondPart);
    }
  }, 20);

  const animateTokenCost = setTimeout(() => {
    target.innerHTML += "\n\nObserving";
    let dotCount = 0;
    const dotInterval = setInterval(() => {
      if (dotCount < 6) {
        target.innerHTML += " .";
        dotCount++;
      } else {
        target.innerHTML += "          <span style='color: green;'>√</span>"
        clearInterval(dotInterval);
        setTimeout(() => {
          target.innerHTML += LLMCostCodeText;
          setTimeout(() => {
            target.innerHTML += dashboardText;
          }, 800);
        }, 800);
      }
    }, 200);

  }, 1200);
}

function typeInGithubPushText(target) {
  const codeTextSecondPart = "<span id='text-to-replace'>\nPushing to prod...</span>";
  const codeTextReplaceSecondPart = "\nPushed to prod <span style='color: green;'>√</span>";
  const codeTextThirdPart = "\n<span style='color: green;'>+2 ■</span><span style='color: #343941'>■■■■</span>";
  const monitoringOnText = "<span class='text-to-alternate'>\n\nEvents logged to dashboard <span style='color: #13C75D;'>⬤</span></span>";
  const monitoringBlinkText = "<span class='text-to-alternate'>\n\nEvents logged to dashboard <span style='color: #0C883F;'>⬤</span></span>";

  const animateGithubPushText = setTimeout(() => {
    target.innerHTML += codeTextSecondPart;
    setTimeout(() => {
      const textToReplaceElement = document.getElementById('text-to-replace');
      if (textToReplaceElement) {
        textToReplaceElement.remove();
      }
      target.innerHTML += codeTextReplaceSecondPart;
      setTimeout(() => {
        target.innerHTML += codeTextThirdPart;
        setTimeout(() => {
          target.innerHTML += monitoringBlinkText;
          const monitoringOnInterval = setInterval(() => {
            const monitoringOnTextElement = document.querySelector('.text-to-alternate');
            if (monitoringOnTextElement) {
              monitoringOnTextElement.remove();
            }
            target.innerHTML += monitoringOnText;
            setTimeout(() => {
              const monitoringBlinkTextElement = document.querySelector('.text-to-alternate');
              if (monitoringBlinkTextElement) {
                monitoringBlinkTextElement.remove();
              }
              target.innerHTML += monitoringBlinkText;
            }, 800);
          }, 1600);
        }, 800);
      }, 800);
    }, 1200);
  }, 300);
}

function fadeInIntroRowTexts(preloaded=false) {
  function fadeInText(i) {
    trailingTextElements[i].classList.add('loaded');
    trailingImgElements[i].classList.add('loaded');
  }

  const trailingTextElements = document.getElementsByClassName('trailing');
  const trailingImgElements = document.getElementsByClassName('trailing-img');

  if (preloaded) {
    for (let i = 0; i < trailingTextElements.length; i++) {
      trailingTextElements[i].classList.add('preloaded');
      trailingImgElements[i].classList.add('preloaded');
    }
  } else {
    for (let i = 0; i < trailingTextElements.length; i++) {
      const increment = i*500;
      setTimeout(() => {
        fadeInText(i);
      }, increment);
    }
  }
}

function addIntroEventListeners() {
  setTimeout(() => {
    document.querySelectorAll('li, a').forEach(element => {
      element.addEventListener('click', () => {
        // Clear all intervals on click
        const highestIntervalId = setInterval(() => {}, 1000);
        for (let i = 0; i < highestIntervalId; i++) {
          clearInterval(i);
        }
        setTimeout(() => {
          loadTerminalText();
          loadIntro(true);
          fadeInIntroRowTexts(true);
        }, 50);
      });
    });
  }, 100);
}

function loadTerminalText() {
  setInterval(() => {
    const cursor = document.getElementById("cursor");
    if (!cursor) return
    if (cursor.style.opacity === "0") {
      cursor.style.opacity = "1";
    } else {
      cursor.style.opacity = "0";
    }
  }, 800);
  setTimeout(() => {
    typeInTerminalText();
  }, 1000);
}

function loadIntro(preloaded = false) {
  const targetSpans = document.querySelectorAll('.animated-code');
  const targetSpansArray = Array.from(targetSpans);

  if (!targetSpans) {
    return;
  }
  
  const codeElementsArray = [];
  targetSpansArray.forEach(targetSpan => {
    const codeElement = targetSpan.querySelector('code');
    console.log(codeElement);
    codeElementsArray.push(codeElement);
  });
  
  if (preloaded) {
    codeElementsArray[0].innerHTML = "pip install agentops\n\n[▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇] 100% <span style='color: green;'>√</span>\n\nObserving . . . . .          <span style='color: green;'>√</span>\n<span style='font-weight: bold;'>AgentOps:</span> This LLM run cost <span style='color: red;'>$0.26270</span> <span style='color: green;'>√</span>\nSee dashboard for full replay: <a href='usage/dashboard-info' style='color: #0088D4; text-decoration: underline;'>https://app.agentops.ai/drilldown?session=SESSION_ID</a> <span style='color: green;'>√</span>";
    codeElementsArray[1].innerHTML = "import agentops\nagentops.init(<INSERT YOUR API KEY HERE>)\n\nPushed to prod <span style='color: green;'>√</span>\n\n<span style='color: green;'>+2 ■</span><span style='color: #343941'>■■■■</span>\n<span class='text-to-alternate'>Events logged to dashboard <span style='color: #13C75D;'>⬤</span></span>";
    const monitoringOnInterval = setInterval(() => {
      const monitoringOnTextElement = document.querySelector('.text-to-alternate');
      if (monitoringOnTextElement) {
        monitoringOnTextElement.remove();
      }
      codeElementsArray[1].innerHTML += "<span class='text-to-alternate'>Events logged to dashboard <span style='color: #13C75D;'>⬤</span></span>";
      setTimeout(() => {
        const monitoringBlinkTextElement = document.querySelector('.text-to-alternate');
        if (monitoringBlinkTextElement) {
          monitoringBlinkTextElement.remove();
        }
        codeElementsArray[1].innerHTML += "<span class='text-to-alternate'>Events logged to dashboard <span style='color: #0C883F;'>⬤</span></span>";
      }, 800);
    }, 1600);
  }

  let pipAnimationTriggered = preloaded; // Flag to track if the animation has been triggered
  let githubPushAnimationTriggered = preloaded; // Flag to track if the animation has been triggered

  function handlePipIntersection(entries, observer) {
    entries.forEach(entry => {
      if (entry.isIntersecting && !pipAnimationTriggered) {
        pipAnimationTriggered = true; // Set the flag to true to prevent re-triggering
        setTimeout(() => {
          typeInPipText(codeElementsArray[0]);
        }, 500);
        observer.unobserve(entry.target); // Stop observing the element
      }
    });
  }

  function handleGithubPushIntersection(entries, observer) {
    entries.forEach(entry => {
      if (entry.isIntersecting && !githubPushAnimationTriggered) {
        githubPushAnimationTriggered = true; // Set the flag to true to prevent re-triggering
        typeInGithubPushText(codeElementsArray[1]);
        observer.unobserve(entry.target); // Stop observing the element
      }
    });
  }

  const pipObserver = new IntersectionObserver(handlePipIntersection, {
    root: document, // Use the document start as the root
    threshold: 0.8 // Trigger when 10% of the element is visible
  });
  const githubPushObserver = new IntersectionObserver(handleGithubPushIntersection, {
    root: document, // Use the document start as the root
    threshold: 0.6 // Trigger when 10% of the element is visible
  });

  pipObserver.observe(codeElementsArray[0]);
  githubPushObserver.observe(codeElementsArray[1]);
}

window.addEventListener('load', function() {
  loadTerminalText();
  loadIntro();
  fadeInIntroRowTexts();
  const observer = new MutationObserver(addIntroEventListeners);
  observer.observe(document.body, { childList: true, subtree: true });
});