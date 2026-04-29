(function(){
  function loadAds(){
    if(window.adsbygoogle && window.adsbygoogle.loaded) return;
    var s = document.createElement('script');
    s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-9156049827002127';
    s.async = true;
    s.crossOrigin = 'anonymous';
    document.body.appendChild(s);
  }
  if(document.readyState === 'complete' || document.readyState === 'interactive'){
    setTimeout(loadAds, 0);
  } else {
    document.addEventListener('DOMContentLoaded', loadAds);
  }
})();
