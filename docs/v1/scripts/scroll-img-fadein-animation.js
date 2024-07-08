function typeInPipText(target) {
  const codeTextFirstPart = "pip install agentops\n\n";
  let codeFirstIndex = 0;
  let codeSecondIndex = 0;
  target.textContent += "[                                 ]   0%";
  const progressBar = "[                                 ]   0%";
  const progressBarArray = progressBar.split('');
  const progressBarLength = progressBar.length;
  
  const codeTypewriterIntervalSecondPart = setInterval(() => {
    if (target.textContent.includes("99%")) {
      clearInterval(codeTypewriterIntervalSecondPart);
      target.innerHTML = codeTextFirstPart + "[▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇] 100% <span style='color: green;'>√</span>";
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
          target.innerHTML += "\n<span style='font-weight: bold;'>AgentOps:</span> This LLM run cost <span style='color: red;'>$0.26270</span> <span style='color: green;'>√</span>"
          setTimeout(() => {
            target.innerHTML += "\nSee dashboard for full replay: <a href='#dashboard' style='color: #0088D4; text-decoration: underline;'>https://app.agentops.ai/drilldown?session=SESSION_ID</a> <span style='color: green;'>√</span>"
          }, 800);
        }, 800);
      }
    }, 200);

  }, 1200);
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
        setTimeout(() => {
          loadIntro(true);
          fadeInIntroRowTexts(true);
        }, 50);
      });
    });
  }, 100);
}

function loadIntro(preloaded = false) {
  const targetSpan = document.querySelector('.animated-code');

  if (!targetSpan) {
    return;
  }
  
  const codeElement = targetSpan.querySelector('code');
  
  if (preloaded) {
    codeElement.innerHTML = "pip install agentops\n\n[▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇ ▇] 100% <span style='color: green;'>√</span>\n\nObserving . . . . .          <span style='color: green;'>√</span>\n<span style='font-weight: bold;'>AgentOps:</span> This LLM run cost <span style='color: red;'>$0.26270</span> <span style='color: green;'>√</span>\nSee dashboard for full replay: <a href='#dashboard' style='color: #0088D4; text-decoration: underline;'>https://app.agentops.ai/drilldown?session=SESSION_ID</a> <span style='color: green;'>√</span>";
  }

  let animationTriggered = preloaded; // Flag to track if the animation has been triggered

  window.addEventListener('scroll', () => {
    if (animationTriggered) return; // Exit if the animation has already been triggered

    if (window.scrollY > 110 || document.documentElement.scrollTop > 110 || document.documentElement.scrollBottom < 12000) { // Adjust the scroll position threshold as needed
      animationTriggered = true; // Set the flag to true to prevent re-triggering
      setTimeout(() => {
        if (!preloaded) {
          typeInPipText(codeElement);
        }
      }, 500);
    }
  });
}

window.addEventListener('load', function() {
  loadIntro();
  fadeInIntroRowTexts();
  const observer = new MutationObserver(addIntroEventListeners);
  observer.observe(document.body, { childList: true, subtree: true });
});