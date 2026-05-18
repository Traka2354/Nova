/* ─── RISK BANNER CLOSE ─── */
const closeBanner = document.getElementById('closeBanner');
if (closeBanner) {
  closeBanner.addEventListener('click', () => {
    const banner = closeBanner.closest('.risk-banner');
    if (banner) banner.style.display = 'none';
  });
}

/* ─── NAV SCROLL ─── */
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

/* ─── MOBILE BURGER ─── */
const burger    = document.getElementById('burger');
const navLinks  = document.getElementById('navLinks');
burger.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  burger.setAttribute('aria-expanded', open);
});
navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => navLinks.classList.remove('open'));
});

/* ─── SCROLL REVEAL ─── */
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('visible'), i * 80);
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

/* ─── HERO PARTICLES ─── */
(function spawnParticles() {
  const container = document.getElementById('particles');
  if (!container) return;
  const count = 28;
  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    const size = Math.random() * 3 + 1;
    const gold = Math.random() > 0.5;
    Object.assign(p.style, {
      position:        'absolute',
      width:           size + 'px',
      height:          size + 'px',
      borderRadius:    '50%',
      background:      gold ? 'rgba(245,200,66,.55)' : 'rgba(255,255,255,.18)',
      left:            Math.random() * 100 + '%',
      top:             Math.random() * 100 + '%',
      animation:       `float ${6 + Math.random() * 10}s ease-in-out ${Math.random() * 6}s infinite`,
      willChange:      'transform',
    });
    container.appendChild(p);
  }
  if (!document.getElementById('particle-style')) {
    const s = document.createElement('style');
    s.id = 'particle-style';
    s.textContent = `
      @keyframes float {
        0%,100% { transform: translateY(0) translateX(0) scale(1); opacity:.6; }
        33%      { transform: translateY(-22px) translateX(8px) scale(1.1); opacity:1; }
        66%      { transform: translateY(-10px) translateX(-6px) scale(.9); opacity:.7; }
      }`;
    document.head.appendChild(s);
  }
})();

/* ─── QR CODE GENERATION ─── */
const PARTNER_URL = 'https://aitech.ibportal.io/auth/register?e=uxHzQEHidtHpyg4rd8YcgfCM0lROvpn4lGFvQU8bvEI&a=1';

function generateQR(canvasId, url) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof QRCode === 'undefined') return;
  QRCode.toCanvas(canvas, url, {
    width: 220,
    margin: 2,
    color: { dark: '#000000', light: '#ffffff' },
    errorCorrectionLevel: 'H',
  }, (err) => { if (err) console.error('QR error:', err); });
}

function initQRCodes() {
  generateQR('qrCanvas1', PARTNER_URL);
  document.querySelectorAll('.js-register-link').forEach(el => {
    el.setAttribute('href', PARTNER_URL);
  });
}

/* Try immediately, on custom event, and on window load — covers all timing cases */
if (typeof QRCode !== 'undefined') {
  initQRCodes();
} else {
  document.addEventListener('qrlib-ready', initQRCodes);
  window.addEventListener('load', () => {
    if (typeof QRCode !== 'undefined') initQRCodes();
  });
}

/* ─── FAQ ─── */
document.querySelectorAll('.faq-item summary').forEach(summary => {
  summary.addEventListener('click', (e) => {
    const item = summary.parentElement;
    const isOpen = item.hasAttribute('open');
    document.querySelectorAll('.faq-item[open]').forEach(d => {
      if (d !== item) d.removeAttribute('open');
    });
    if (isOpen) { e.preventDefault(); item.removeAttribute('open'); }
  });
});

/* ─── COUNTDOWN TIMER — next Friday 21:00 UTC ─── */
(function initCountdown() {
  function getNextFriday2100() {
    const now = new Date();
    const target = new Date(now);
    // Set to Friday (5) at 21:00 UTC
    target.setUTCHours(21, 0, 0, 0);
    const day = target.getUTCDay(); // 0=Sun, 5=Fri
    let daysUntilFriday = (5 - day + 7) % 7;
    if (daysUntilFriday === 0 && now >= target) {
      daysUntilFriday = 7;
    }
    target.setUTCDate(target.getUTCDate() + daysUntilFriday);
    return target;
  }

  const bar     = document.getElementById('countdownBar');
  const elDays  = document.getElementById('cdDays');
  const elHours = document.getElementById('cdHours');
  const elMins  = document.getElementById('cdMins');
  const elSecs  = document.getElementById('cdSecs');

  if (!bar || !elDays) return;

  function pad(n) { return String(n).padStart(2, '0'); }

  function tick() {
    const now    = new Date();
    const target = getNextFriday2100();
    const diff   = target - now;

    if (diff <= 0) {
      if (bar) bar.style.display = 'none';
      return;
    }

    const totalSecs = Math.floor(diff / 1000);
    const d = Math.floor(totalSecs / 86400);
    const h = Math.floor((totalSecs % 86400) / 3600);
    const m = Math.floor((totalSecs % 3600) / 60);
    const s = totalSecs % 60;

    elDays.textContent  = pad(d);
    elHours.textContent = pad(h);
    elMins.textContent  = pad(m);
    elSecs.textContent  = pad(s);
  }

  tick();
  setInterval(tick, 1000);
})();

/* ─── ANIMATED COUNTERS ─── */
(function initCounters() {
  const counterEls = document.querySelectorAll('.stat__value[data-target]');
  if (!counterEls.length) return;

  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

  function animateCounter(el) {
    const target   = parseFloat(el.getAttribute('data-target'));
    const prefix   = el.getAttribute('data-prefix') || '';
    const suffix   = el.getAttribute('data-suffix') || '';
    const duration = 1500;
    const start    = performance.now();

    function update(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const value    = Math.round(easeOut(progress) * target);
      el.textContent = prefix + value + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counterEls.forEach(el => counterObserver.observe(el));
})();

/* ─── LANGUAGE SWITCHER ─── */
(function initLangSwitcher() {
  const btn  = document.getElementById('langToggle');
  const body = document.body;
  if (!btn) return;

  const saved = localStorage.getItem('siteLang');
  if (saved === 'hr') {
    body.classList.add('lang-hr');
    btn.textContent = 'EN';
  } else {
    btn.textContent = 'HR';
  }

  btn.addEventListener('click', () => {
    const isHr = body.classList.toggle('lang-hr');
    btn.textContent = isHr ? 'EN' : 'HR';
    localStorage.setItem('siteLang', isHr ? 'hr' : 'en');
  });
})();

/* ─── PROFIT CALCULATOR ─── */
(function initCalculator() {
  const amountInput = document.getElementById('calcAmount');
  const typeSelect  = document.getElementById('calcType');
  const weeksSlider = document.getElementById('calcWeeks');
  const weeksLabel  = document.getElementById('calcWeeksLabel');
  const finalBal    = document.getElementById('calcFinalBalance');
  const totalProfit = document.getElementById('calcTotalProfit');
  const totalGrowth = document.getElementById('calcTotalGrowth');
  const tableBody   = document.getElementById('calcTableBody');

  if (!amountInput || !typeSelect || !weeksSlider) return;

  function fmt(n) {
    return '$' + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function calculate() {
    const start   = parseFloat(amountInput.value) || 100;
    const rate    = parseFloat(typeSelect.value) || 0.05;
    const weeks   = parseInt(weeksSlider.value, 10) || 12;

    weeksLabel.textContent = weeks;

    // Build week-by-week data
    const rows = [];
    let balance = start;
    for (let w = 1; w <= weeks; w++) {
      const gain  = balance * rate;
      balance     = balance + gain;
      rows.push({ week: w, balance, gain });
    }

    const final  = balance;
    const profit = final - start;
    const growth = ((profit / start) * 100);

    finalBal.textContent    = fmt(final);
    totalProfit.textContent = '+' + fmt(profit);
    totalGrowth.textContent = '+' + growth.toFixed(1) + '%';

    // Build mini table — show every 4 weeks + first + last
    tableBody.innerHTML = '';

    // Start row
    const startRow = document.createElement('tr');
    startRow.innerHTML = `<td>Start</td><td>${fmt(start)}</td><td>—</td>`;
    tableBody.appendChild(startRow);

    const shown = new Set();
    rows.forEach(({ week, balance, gain }) => {
      const show = week === 1 || week % 4 === 0 || week === weeks;
      if (show && !shown.has(week)) {
        shown.add(week);
        const tr = document.createElement('tr');
        if (week === weeks) tr.classList.add('calc-table__highlight');
        tr.innerHTML = `<td>Week ${week}</td><td>${fmt(balance)}</td><td class="green">+${fmt(gain)}</td>`;
        tableBody.appendChild(tr);
      }
    });
  }

  weeksSlider.addEventListener('input', calculate);
  amountInput.addEventListener('input', calculate);
  typeSelect.addEventListener('change', calculate);

  calculate(); // initial render
})();

/* ─── STICKY CTA BAR ─── */
(function initStickyCta() {
  const stickyCta = document.getElementById('stickyCta');
  const hero      = document.getElementById('hero');
  if (!stickyCta || !hero) return;

  const heroObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) {
        stickyCta.classList.add('visible');
      } else {
        stickyCta.classList.remove('visible');
      }
    });
  }, { threshold: 0.2 });

  heroObserver.observe(hero);
})();

/* ─── COOKIE CONSENT ─── */
(function initCookieConsent() {
  const banner  = document.getElementById('cookieBanner');
  const accept  = document.getElementById('cookieAccept');
  const decline = document.getElementById('cookieDecline');
  if (!banner) return;

  const consent = localStorage.getItem('cookieConsent');
  if (!consent) {
    setTimeout(() => banner.classList.add('show'), 2000);
  }

  function hideBanner() {
    banner.classList.remove('show');
  }

  if (accept) {
    accept.addEventListener('click', () => {
      localStorage.setItem('cookieConsent', 'accepted');
      hideBanner();
      // Fire GA4 consent update if gtag is available
      if (typeof gtag === 'function') {
        gtag('consent', 'update', {
          analytics_storage: 'granted',
        });
      }
    });
  }

  if (decline) {
    decline.addEventListener('click', () => {
      localStorage.setItem('cookieConsent', 'declined');
      hideBanner();
    });
  }
})();
