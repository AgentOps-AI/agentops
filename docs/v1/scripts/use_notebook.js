// Function to load content from another HTML file
async function loadContent(div_element) {
    try {
        const fileName = div_element.getAttribute('data-content-file');
        const response = await fetch(fileName);
        if (!response.ok) throw new Error('Network response was not ok');
        div_element.innerHTML = await response.text();
    } catch (error) {
        console.error('Failed to load content:', error);
    }
}

// Load content when the page is fully loaded
window.onload = function() {
    const divs = document.querySelectorAll('div[data-content-file]');
    divs.forEach(div => {
        loadContent(div);
    });
};