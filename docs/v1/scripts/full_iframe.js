window.addEventListener('load', function() {
    let iframes = document.getElementsByTagName('iframe');
    for (let i = 0; i < iframes.length; ++i) {
        let iframe = iframes[i];
        let body = iframe.contentDocument.body;

        iframe.style.height = body.scrollHeight + 100 + 'px';
        iframe.style.width = '95%';
        iframe.style.borderRadius = '15px';
        iframe.style.boxShadow = '0px 2px 15px rgba(0, 0, 0, 0.1)';
        iframe.style.marginLeft = '15px';
        iframe.style.padding = '5px';
        iframe.style.marginBottom = '25px'
    }
});