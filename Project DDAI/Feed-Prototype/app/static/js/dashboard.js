document.addEventListener('DOMContentLoaded', () => {
  renderEventLog();
  renderTrendChart();
  hookSliders();
});

// 1) Event log
function renderEventLog() {
  const ul = document.getElementById('event-log');
  EVENTS.forEach(e => {
    const li = document.createElement('li');
    li.textContent = `[${e.category}] #${e.id}: ${e.text} → avg ${e.avg.toFixed(2)} over ${e.count}`;
    ul.appendChild(li);
  });
}

// 2) Trend chart
function renderTrendChart() {
  const ctx = document.getElementById('trendChart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: TRENDS.map(t => t.category),
      datasets: [{
        label: 'Avg Rating',
        data: TRENDS.map(t => t.avg),
      }]
    },
    options: {
      scales: { y: { beginAtZero: true, max: 5 } }
    }
  });
}

// 3) Sliders foreach weight
function hookSliders() {
  const keys = ['likes','shares','comments','dislikes'];
  keys.forEach(k => {
    const s = document.getElementById(`${k}-slider`);
    const v = document.getElementById(`${k}-val`);
    s.addEventListener('input', () => v.textContent = s.value);
  });
  document.getElementById('save-settings')
    .addEventListener('click', saveSettings);
}

function saveSettings() {
  const payload = {};
  ['likes','shares','comments','dislikes'].forEach(k => {
    payload[k] = document.getElementById(`${k}-slider`).value;
  });
  fetch('/dashboard/settings', {
    method:'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  })
  .then(r=>r.json())
  .then(resp => {
    const msg = document.getElementById('settings-msg');
    msg.textContent = 'Settings saved!';
    msg.classList.remove('hide');
    setTimeout(()=> msg.classList.add('hide'), 2000);
  })
  .catch(console.error);
}
