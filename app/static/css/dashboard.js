const ws = new WebSocket(`ws://${location.host}/ws/market`);

const nqPrices = [];
const nqTimes = [];

const chartDiv = document.getElementById('chart');

let chart = Plotly.newPlot(chartDiv, [{
  x: [], y: [],
  type: 'scatter',
  mode: 'lines',
  name: 'NQ',
  line: { color: '#3b82f6', width: 2 },
  fill: 'tozeroy',
  fillcolor: 'rgba(59,130,246,0.06)',
}], {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  margin: { t: 10, r: 10, b: 30, l: 70 },
  xaxis: { showgrid: false, color: '#7a7f94', tickfont: { size: 11 } },
  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', color: '#7a7f94', tickfont: { size: 11 } },
  showlegend: false,
}, { responsive: true, displayModeBar: false });

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const { nq, es, signals, performance, bot } = data;

  // Price
  const priceEl = document.getElementById('nq-price');
  const prev = parseFloat(priceEl.dataset.prev || nq.close);
  priceEl.textContent = nq.close.toFixed(2);
  priceEl.dataset.prev = nq.close;
  priceEl.style.color = nq.close > prev ? '#22c55e' : nq.close < prev ? '#ef4444' : '#e8eaf0';

  // ICT window
  const ictEl = document.getElementById('ict-status');
  const inWindow = signals.length > 0 && signals[0].active_ict_window;
  ictEl.textContent = inWindow ? '✓ ICT Window Active' : '× ICT Window Closed';
  ictEl.className = inWindow ? 'active' : '';

  // Performance stats
  const pnl = performance.total_pnl;
  const pnlEl = document.getElementById('total-pnl');
  pnlEl.textContent = (pnl >= 0 ? '+$' : '-$') + Math.abs(pnl).toLocaleString();
  pnlEl.className = pnl >= 0 ? 'up' : 'dn';
  document.getElementById('win-rate').textContent = performance.win_rate + '%';
  document.getElementById('total-trades').textContent = performance.total_trades;
  document.getElementById('best-setup').textContent = performance.best_setup || '--';

  // Bot
  document.getElementById('bot-mode').textContent = bot.mode || '--';
  const biasEl = document.getElementById('bot-bias');
  biasEl.textContent = bot.current_bias || '--';
  biasEl.className = bot.current_bias === 'long' ? 'up' : bot.current_bias === 'short' ? 'dn' : '';

  const botPnl = bot.total_pnl;
  const botPnlEl = document.getElementById('bot-pnl');
  botPnlEl.textContent = (botPnl >= 0 ? '+$' : '-$') + Math.abs(botPnl).toLocaleString();
  botPnlEl.className = botPnl >= 0 ? 'up' : 'dn';

  document.getElementById('bot-win-rate').textContent = bot.win_rate + '%';
  document.getElementById('bot-action').textContent = bot.last_action || 'Waiting...';

  const statusEl = document.getElementById('bot-status');
  statusEl.textContent = bot.status;
  statusEl.className = 'pill' + (bot.status === 'Running' ? '' : ' paused');

  // Chart
  nqPrices.push(nq.close);
  nqTimes.push(nq.time);
  if (nqPrices.length > 120) { nqPrices.shift(); nqTimes.shift(); }
  Plotly.update(chartDiv, { x: [nqTimes], y: [nqPrices] }, {}, [0]);

  // Signals
  const sigEl = document.getElementById('signals');
  if (!signals.length) {
    sigEl.innerHTML = '<p class="no-signal"><span class="pulse"></span>Scanning for setups...</p>';
  } else {
    sigEl.innerHTML = signals.map(s => {
      const isMaster = s.type === 'MASTER ICT SETUP';
      const cls = isMaster ? 'master' : (s.bias || '');
      return `<div class="signal ${cls}">
        <div>
          <div class="signal-type">${s.type}</div>
          <div class="signal-msg">${s.message}</div>
        </div>
        ${s.bias ? `<span class="signal-badge ${isMaster ? 'master' : s.bias}">${s.bias.toUpperCase()}</span>` : ''}
      </div>`;
    }).join('');
  }
};

ws.onerror = () => {
  document.getElementById('nq-price').textContent = 'WS Error';
};
ws.onclose = () => {
  document.getElementById('nq-price').textContent = 'Reconnecting...';
  setTimeout(() => location.reload(), 3000);
};
