// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tgt = document.querySelector(link.getAttribute('href'));
    if (tgt) tgt.scrollIntoView({ behavior: 'smooth' });
  });
});

// Initialize empty Chart.js
const ctx = document.getElementById('progressChart')?.getContext('2d');
if (ctx) {
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],      // à remplir dynamiquement
      datasets: [{
        label: 'Progression %',
        data: [],
        borderColor: '#D4AF37',
        backgroundColor: 'rgba(212,175,55,0.3)',
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100 } }
    }
  });
}
