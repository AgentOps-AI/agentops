// Function to load content from another HTML file
async function loadContent(div_element) {
    console.log('Loading content for:', div_element);
    try {
        const fileName = div_element.getAttribute('data-content-file');
        console.log('Fetching file:', fileName);
        const response = await fetch(fileName);
        
        if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);
        const content = await response.text();
        console.log('Content loaded, length:', content.length);
        
        // Use a timeout to ensure this runs after the current call stack is clear
        setTimeout(() => {
            div_element.innerHTML = content;
            console.log('Content set to innerHTML');
        }, 0);
    } catch (error) {
        console.error('Failed to load content:', error);
        div_element.innerHTML = `<p>Error loading content: ${error.message}</p>`;
    }
}

// Load content when the page is fully loaded
function loadAllContent() {
    console.log('loadAllContent called');
    const divs = document.querySelectorAll('div[data-content-file]');
    console.log('Found divs:', divs.length);
    
    // Use Promise.all to wait for all content to load
    Promise.all(Array.from(divs).map(div => loadContent(div)))
        .then(() => console.log('All content loaded'))
        .catch(error => console.error('Error loading some content:', error));
}

// Use both DOMContentLoaded and window.onload
document.addEventListener('DOMContentLoaded', loadAllContent);
window.onload = loadAllContent;

// Add a mutation observer to handle dynamically added elements
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE && node.matches('div[data-content-file]')) {
                    loadContent(node);
                }
            });
        }
    });
});

observer.observe(document.body, { childList: true, subtree: true });

// Add a debugging function
window.debugContentLoading = function() {
    console.log('Debugging content loading');
    const divs = document.querySelectorAll('div[data-content-file]');
    divs.forEach((div, index) => {
        console.log(`Div ${index}:`, {
            'data-content-file': div.getAttribute('data-content-file'),
            'innerHTML length': div.innerHTML.length,
            'isVisible': div.offsetParent !== null
        });
    });
};

// Call debugContentLoading after a short delay
setTimeout(debugContentLoading, 1000);