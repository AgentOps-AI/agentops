window.addEventListener('load', function() {
    const iframe = document.getElementById('iframe');
    const body = iframe.contentDocument.body;
    iframe.style.height = body.scrollHeight + 100 + 'px';
    iframe.style.width = '100%'
});