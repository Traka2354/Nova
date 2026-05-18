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
    width:            220,
    margin:           2,
    color: { dark: '#000000', light: '#ffffff' },
    errorCorrectionLevel: 'H',
  }, (err) => { if (err) console.error('QR error:', err); });
}

function initQRCodes() {
  generateQR('qrCanvas1', PARTNER_URL);
  generateQR('qrCanvas2', PARTNER_URL);
  // Wire up buttons to the real URL
  document.querySelectorAll('.js-register-link').forEach(el => {
    el.setAttribute('href', PARTNER_URL);
  });
}

if (typeof QRCode !== 'undefined') {
  initQRCodes();
} else {
  document.addEventListener('qrlib-ready', initQRCodes);
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
