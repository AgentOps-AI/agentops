window.addEventListener('load', function() {
    const iframe = document.getElementById('iframe');
    const body = iframe.contentDocument.body;
    iframe.style.height = body.scrollHeight + 100 + 'px';
    iframe.style.width = '95%'
    iframe.style.borderRadius = '15px';
    iframe.style.boxShadow = '0px 2px 15px rgba(0, 0, 0, 0.1)';
    iframe.style.marginLeft = '15px';
    iframe.style.padding = '5px';
});