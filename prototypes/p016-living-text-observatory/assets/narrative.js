/* P016 Living Text Observatory — minimal, deterministic, dependency-free.
   Progressive enhancement only: without this file the page is fully readable. */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("p016-js");

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* Configurable workbench destination (local/staging/production). */
  var meta = document.querySelector('meta[name="delta-workbench-url"]');
  var target = meta && meta.content ? meta.content : null;
  if (target) {
    var links = document.querySelectorAll("a[data-workbench]");
    for (var i = 0; i < links.length; i += 1) links[i].setAttribute("href", target);
  }

  /* Reading progress + header scrolled-state (passive; native scroll untouched). */
  var progress = document.querySelector(".p016-progress span");
  var header = document.querySelector(".p016-header");
  var allReveals = document.querySelectorAll(".p016-reveal");
  var ticking = false;
  function paintScrollState() {
    ticking = false;
    var de = document.documentElement;
    var top = window.pageYOffset || de.scrollTop || 0;
    var max = de.scrollHeight - de.clientHeight;
    if (progress && max > 0) {
      progress.style.width = ((top / max) * 100).toFixed(2) + "%";
    }
    if (header) header.classList.toggle("is-scrolled", top > 8);
    /* Rect-based reveal fallback: guarantees the narrative under scrolling
       models where IntersectionObserver never fires (embedded webviews). */
    var vh = window.innerHeight || de.clientHeight;
    for (var ri = 0; ri < allReveals.length; ri += 1) {
      var el = allReveals[ri];
      if (el.classList.contains("is-in")) continue;
      var rect = el.getBoundingClientRect();
      if (rect.top < vh * 0.92 && rect.bottom > 0) el.classList.add("is-in");
    }
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(paintScrollState); }
  }, { passive: true });
  paintScrollState();

  /* Wrapper-scroll environments (some in-app browsers/embeds) never deliver
     window scroll events or scrollTop changes. A light self-terminating watcher
     keeps the one-way reveals working there too. */
  var watcher = window.setInterval(function () {
    paintScrollState();
    var pending = 0;
    for (var wi = 0; wi < allReveals.length; wi += 1) {
      if (!allReveals[wi].classList.contains("is-in")) { pending = 1; break; }
    }
    if (!pending) window.clearInterval(watcher);
  }, 400);

  /* Stagger indices for the run ledger rows. */
  var ledgerRows = document.querySelectorAll(".p016-run-ledger li");
  for (var li = 0; li < ledgerRows.length; li += 1) {
    ledgerRows[li].style.setProperty("--i", String(li));
  }

  /* Hero settle: one-shot Gather -> ordered field. */
  /* Mobile: start the nav disclosure collapsed (no-JS mobile keeps it open, which
     remains accessible). Desktop always shows the inline list. */
  var navDetails = document.querySelector(".p016-nav-details");
  if (navDetails && window.matchMedia("(max-width: 860px)").matches) {
    navDetails.removeAttribute("open");
  }

  var hero = document.querySelector(".p016-hero-field");
  if (hero) {
    if (reduced.matches) {
      hero.classList.add("is-settled");
    } else {
      window.setTimeout(function () { hero.classList.add("is-settled"); }, 240);
    }
  }

  /* Section reveals: one-way, persist once shown (valid under fast/reverse scroll). */
  var reveals = document.querySelectorAll(".p016-reveal");
  if (reduced.matches || !("IntersectionObserver" in window)) {
    for (var r = 0; r < reveals.length; r += 1) reveals[r].classList.add("is-in");
    return;
  }
  var observer = new IntersectionObserver(
    function (entries) {
      for (var e = 0; e < entries.length; e += 1) {
        if (entries[e].isIntersecting) {
          entries[e].target.classList.add("is-in");
          observer.unobserve(entries[e].target);
        }
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
  );
  for (var k = 0; k < reveals.length; k += 1) observer.observe(reveals[k]);

  /* If the user loads mid-page (refresh at scroll position), reveal everything
     above and around the viewport immediately so no content is stuck hidden. */
  window.addEventListener("load", function () {
    var vh = window.innerHeight;
    for (var j = 0; j < reveals.length; j += 1) {
      var rect = reveals[j].getBoundingClientRect();
      if (rect.top < vh * 0.95) reveals[j].classList.add("is-in");
    }
  });
})();
