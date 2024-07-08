window.addEventListener('load', function() {
  const targetImg = document.querySelector('.resolved-stamp');

  window.addEventListener('scroll', () => {
    const scrollPosition = window.scrollY || document.documentElement.scrollTop;
    if (scrollPosition > 1) { // Adjust the scroll position threshold as needed
      targetImg.classList.add('scrolled');
    }
  });
});