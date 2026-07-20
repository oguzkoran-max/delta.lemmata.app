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
