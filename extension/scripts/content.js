// Amazon Intelligence Pro — In-SERP Content Script
// Author: Tarik Islam (tarikislam.in)

(() => {
  console.log("🛰️ Amazon Intelligence Pro active on SERP.");

  function injectRankBadges() {
    const items = document.querySelectorAll('div[data-component-type="s-search-result"]');
    if (!items.length) return;

    let organicCounter = 0;

    items.forEach((item, index) => {
      if (item.querySelector(".intel-rank-badge")) return; // already injected

      const asin = item.getAttribute("data-asin");
      const isSponsored = !!item.querySelector('.puis-label-popover-default, .s-sponsored-label-info-icon, [data-component-type="sp-sponsored-result"]');

      if (!isSponsored) {
        organicCounter++;
      }

      const badge = document.createElement("div");
      badge.className = "intel-rank-badge " + (isSponsored ? "sponsored" : "organic");
      badge.innerHTML = `
        <span class="badge-tag">${isSponsored ? "📢 AD" : "🌿 #" + organicCounter}</span>
        <span class="badge-asin" title="Click to copy ASIN">${asin || "NO-ASIN"}</span>
      `;

      badge.querySelector(".badge-asin").addEventListener("click", (e) => {
        e.stopPropagation();
        if (asin) {
          navigator.clipboard.writeText(asin);
          alert(`Copied ASIN: ${asin}`);
        }
      });

      const targetContainer = item.querySelector(".s-product-image-container, .a-section") || item;
      targetContainer.style.position = "relative";
      targetContainer.appendChild(badge);
    });

    injectFloatingHUD(organicCounter, items.length - organicCounter);
  }

  function injectFloatingHUD(organicTotal, sponsoredTotal) {
    if (document.getElementById("intel-floating-hud")) return;

    const hud = document.createElement("div");
    hud.id = "intel-floating-hud";
    hud.innerHTML = `
      <div class="hud-header">
        <span>🛰️ Amazon Intel Pro</span>
        <button id="hud-close-btn">✕</button>
      </div>
      <div class="hud-body">
        <div class="hud-stat"><span>Organic Products:</span> <b>${organicTotal}</b></div>
        <div class="hud-stat"><span>Sponsored Ads:</span> <b>${sponsoredTotal}</b></div>
      </div>
    `;

    document.body.appendChild(hud);
    document.getElementById("hud-close-btn").addEventListener("click", () => {
      hud.style.display = "none";
    });
  }

  // Initial run & observe dynamic loads
  window.addEventListener("load", () => {
    setTimeout(injectRankBadges, 1000);
  });

  const observer = new MutationObserver(() => {
    injectRankBadges();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
