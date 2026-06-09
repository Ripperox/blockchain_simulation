/* =========================================================
   BlockChain Terminal – Frontend
   ========================================================= */

const socket = io({ transports: ['websocket', 'polling'] });

let isMining = false;
let chainData = [];

// =========================================================
// Socket.IO Events
// =========================================================

socket.on('connect', () => {
  log('Connected to node-alpha', 'sync');
});

socket.on('disconnect', () => {
  log('Disconnected', 'error');
});

socket.on('init', (data) => {
  chainData = data.chain || [];
  renderChain(chainData);
  renderMempool(data.mempool || []);
  renderNodes(data.nodes || []);
  updateStats(data.stats || {});
});

socket.on('mining_progress', (data) => {
  if (!isMining) return;
  updateMiningProgress(data);
});

socket.on('block_mined', (data) => {
  stopMiningUI();
  chainData = chainData.concat([data.block]);
  renderChain(chainData);
  updateBadge('chain-length-badge', `${data.chain_length} blocks`);
  updateBadge('mempool-badge', `${data.mempool_size} tx pending`);
  updateBadge('mempool-count', `${data.mempool_size} pending`);
  log(`Block #${data.block.index} mined — nonce ${data.block.nonce}, ${data.block.transactions.length} txs`, 'mine');
  fetchAndUpdateStats();
});

socket.on('mempool_updated', (data) => {
  renderMempool(data.transactions || []);
});

socket.on('nodes_updated', (data) => {
  renderNodes(data.nodes || []);
});

// =========================================================
// Mine Button
// =========================================================

const btnMine = document.getElementById('btn-mine');
const btnText = document.getElementById('mine-btn-text');
const miningProgress = document.getElementById('mining-progress');

btnMine.addEventListener('click', async () => {
  if (isMining) return;
  isMining = true;
  startMiningUI();
  log('Mining started…', 'mine');

  try {
    const res = await fetch('/mine', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    const data = await res.json();
    if (!res.ok) {
      log('Mining failed: ' + (data.error || 'unknown'), 'error');
      stopMiningUI();
    }
  } catch (e) {
    log('Network error: ' + e.message, 'error');
    stopMiningUI();
  }
});

function startMiningUI() {
  btnMine.disabled = true;
  btnText.textContent = 'MINING…';
  miningProgress.classList.remove('hidden');
  document.getElementById('progress-bar').style.width = '0%';
  setHashStream('Initializing proof-of-work…');
}

function stopMiningUI() {
  isMining = false;
  btnMine.disabled = false;
  btnText.textContent = 'START MINING';
  document.getElementById('progress-bar').style.width = '100%';
  setTimeout(() => {
    document.getElementById('progress-bar').style.width = '0%';
    miningProgress.classList.add('hidden');
  }, 1200);
}

function updateMiningProgress(data) {
  document.getElementById('prog-nonce').textContent = data.current_nonce.toLocaleString();
  document.getElementById('prog-speed').textContent = formatHashRate(data.attempts_per_second);
  document.getElementById('prog-diff').textContent = data.difficulty;

  // Animate progress bar based on leading zeros found
  const hash = data.current_hash || '';
  const target = '0'.repeat(data.difficulty);
  let matchLen = 0;
  for (let i = 0; i < Math.min(hash.length, target.length + 4); i++) {
    if (hash[i] === '0') matchLen++;
    else break;
  }
  const pct = Math.min(95, (matchLen / (data.difficulty + 2)) * 100);
  document.getElementById('progress-bar').style.width = pct + '%';

  setHashStream(data.current_hash || '');
}

function setHashStream(hash) {
  const el = document.getElementById('hash-stream');
  // Color leading zeros in bright accent
  const zeros = hash.match(/^0*/)?.[0] || '';
  const rest = hash.slice(zeros.length);
  el.innerHTML = `<span style="color:#00ff88;font-weight:700">${zeros}</span><span style="color:#5a5a7a">${rest}</span> <span class="hash-cursor">▌</span>`;
}

// =========================================================
// Add Transaction
// =========================================================

document.getElementById('btn-add-tx').addEventListener('click', async () => {
  const sender = document.getElementById('tx-sender').value.trim();
  const recipient = document.getElementById('tx-recipient').value.trim();
  const amount = parseFloat(document.getElementById('tx-amount').value);
  const feedback = document.getElementById('tx-feedback');

  if (!sender || !recipient || isNaN(amount) || amount <= 0) {
    showFeedback(feedback, 'Invalid inputs — fill all fields', 'error');
    return;
  }

  try {
    const res = await fetch('/add_transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender, recipient, amount })
    });
    const data = await res.json();
    if (res.ok) {
      showFeedback(feedback, `TX broadcast: ${data.tx_hash.slice(0, 16)}…`, 'success');
      log(`TX added: ${amount} → ${recipient.slice(0, 10)}…`, 'tx');
      document.getElementById('tx-sender').value = '';
      document.getElementById('tx-recipient').value = '';
      document.getElementById('tx-amount').value = '';
    } else {
      showFeedback(feedback, data.error || 'Error', 'error');
    }
  } catch (e) {
    showFeedback(feedback, 'Network error', 'error');
  }
});

function showFeedback(el, msg, type) {
  el.textContent = msg;
  el.className = `tx-feedback ${type}`;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 3500);
}

// =========================================================
// Render: Chain
// =========================================================

function renderChain(chain) {
  const container = document.getElementById('chain-container');
  container.innerHTML = '';
  updateBadge('chain-length-badge', `${chain.length} blocks`);

  // Render newest block first
  const reversed = [...chain].reverse();

  reversed.forEach((block, idx) => {
    const isGenesis = block.index === 0;
    const isValid = idx === reversed.length - 1 || true; // simplified; server validates
    const card = document.createElement('div');
    card.className = 'block-card';
    card.id = `block-${block.index}`;

    const txCount = (block.transactions || []).length;
    const merkle = block.merkle_root || '—';
    const prevHash = block.previous_hash || '—';
    const blockHash = block.hash || '—';
    const nonce = block.nonce ?? '—';
    const diff = block.difficulty ?? '—';
    const reward = block.block_reward ?? '—';
    const blockTime = block.block_time != null ? block.block_time + 's' : '—';
    const miner = block.miner || '—';
    const ts = block.timestamp ? new Date(block.timestamp * 1000).toLocaleTimeString() : '—';

    card.innerHTML = `
      <div class="block-header">
        <span class="block-index">#${block.index}</span>
        <span class="block-miner">${miner.slice(0, 22)}…</span>
        ${isGenesis ? '<span class="genesis-badge">GENESIS</span>' : `<span class="block-time-badge">${blockTime}</span>`}
      </div>
      <div class="block-fields">
        <div class="block-field full">
          <div class="field-label">Hash</div>
          <div class="field-value green" title="${blockHash}">${blockHash.slice(0, 32)}…</div>
        </div>
        <div class="block-field full">
          <div class="field-label">Prev Hash</div>
          <div class="field-value" title="${prevHash}">${prevHash.slice(0, 32)}…</div>
        </div>
        <div class="block-field full">
          <div class="field-label">Merkle Root</div>
          <div class="field-value" title="${merkle}">${merkle.slice(0, 32)}…</div>
        </div>
        <div class="block-field">
          <div class="field-label">Nonce</div>
          <div class="field-value">${nonce.toLocaleString()}</div>
        </div>
        <div class="block-field">
          <div class="field-label">Difficulty</div>
          <div class="field-value">${diff}</div>
        </div>
        <div class="block-field">
          <div class="field-label">Reward</div>
          <div class="field-value">${reward} BTC</div>
        </div>
        <div class="block-field">
          <div class="field-label">Timestamp</div>
          <div class="field-value">${ts}</div>
        </div>
      </div>
      <div class="block-txs">
        <div class="block-txs-label">${txCount} Transaction${txCount !== 1 ? 's' : ''}</div>
        ${renderTxRows(block.transactions || [])}
      </div>
    `;

    container.appendChild(card);
  });
}

function renderTxRows(txs) {
  if (!txs.length) return '<div style="color:var(--text-dim);font-size:0.65rem;">No transactions</div>';
  return txs.slice(0, 5).map(tx => `
    <div class="block-tx-row">
      <span class="block-tx-hash">${(tx.tx_hash || '').slice(0, 12)}…</span>
      <span style="color:var(--text-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:80px;">${shortenAddr(tx.sender)} → ${shortenAddr(tx.recipient)}</span>
      <span class="block-tx-amount">${Number(tx.amount).toFixed(4)}</span>
    </div>
  `).join('') + (txs.length > 5 ? `<div style="color:var(--text-dim);font-size:0.62rem;text-align:center;margin-top:2px;">+${txs.length - 5} more</div>` : '');
}

function shortenAddr(addr) {
  if (!addr) return '—';
  if (addr === 'COINBASE') return 'COINBASE';
  return addr.slice(0, 6) + '…';
}

// =========================================================
// Render: Mempool
// =========================================================

function renderMempool(txs) {
  const list = document.getElementById('mempool-list');
  const count = txs.length;

  updateBadge('mempool-count', `${count} pending`);
  updateBadge('mempool-badge', `${count} tx pending`);

  if (!count) {
    list.innerHTML = '<div class="mempool-empty">No pending transactions</div>';
    return;
  }

  list.innerHTML = txs.map(tx => `
    <div class="mempool-item" id="mp-${tx.tx_hash}">
      <div class="mempool-item-hash">${tx.tx_hash.slice(0, 28)}…</div>
      <div class="mempool-item-detail">
        <span>${shortenAddr(tx.sender)} → ${shortenAddr(tx.recipient)}</span>
        <span class="mempool-amount">${Number(tx.amount).toFixed(4)}</span>
      </div>
    </div>
  `).join('');
}

// =========================================================
// Render: Nodes
// =========================================================

function renderNodes(nodes) {
  const list = document.getElementById('nodes-list');
  list.innerHTML = nodes.map(n => `
    <div class="node-card">
      <div class="node-header">
        <div class="node-dot"></div>
        <span class="node-name">${n.node_id}</span>
        <span class="node-peers">${n.peer_count} peers</span>
      </div>
      <div class="node-info">
        <div class="node-kv">
          <span class="node-kv-label">Chain Length</span>
          <span class="node-kv-value">${n.chain_length}</span>
        </div>
        <div class="node-kv">
          <span class="node-kv-label">Difficulty</span>
          <span class="node-kv-value">${n.difficulty}</span>
        </div>
        <div class="node-kv" style="grid-column:1/-1">
          <span class="node-kv-label">Last Block Hash</span>
          <span class="node-kv-value">${(n.last_block_hash || '').slice(0, 20)}…</span>
        </div>
      </div>
    </div>
  `).join('');
}

// =========================================================
// Stats
// =========================================================

async function fetchAndUpdateStats() {
  try {
    const res = await fetch('/get_stats');
    const data = await res.json();
    updateStats(data);
  } catch (_) {}
}

function updateStats(stats) {
  setText('stat-blocks-val', stats.total_blocks ?? '—');
  setText('stat-txs-val', stats.total_transactions ?? '—');
  setText('stat-hashrate-val', formatHashRate(stats.network_hash_rate ?? 0));
  setText('stat-diff-val', stats.current_difficulty ?? '—');
}

// =========================================================
// Log
// =========================================================

const MAX_LOG = 50;

function log(msg, type = 'info') {
  const list = document.getElementById('log-list');
  const now = new Date().toLocaleTimeString('en-US', { hour12: false });
  const entry = document.createElement('div');
  entry.className = `log-entry log-${type}`;
  entry.innerHTML = `<span class="log-time">${now}</span>${escapeHtml(msg)}`;
  list.insertBefore(entry, list.firstChild);
  // Trim old entries
  while (list.children.length > MAX_LOG) {
    list.removeChild(list.lastChild);
  }
}

// =========================================================
// Utilities
// =========================================================

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function updateBadge(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function formatHashRate(n) {
  if (!n || n === 0) return '0 H/s';
  if (n >= 1e9) return (n / 1e9).toFixed(2) + ' GH/s';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + ' MH/s';
  if (n >= 1e3) return (n / 1e3).toFixed(2) + ' KH/s';
  return n + ' H/s';
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// =========================================================
// Initial load
// =========================================================

(async () => {
  try {
    const [chainRes, mempoolRes, nodesRes, statsRes] = await Promise.all([
      fetch('/get_chain'),
      fetch('/get_mempool'),
      fetch('/get_nodes'),
      fetch('/get_stats'),
    ]);
    chainData = await chainRes.json();
    const mempool = await mempoolRes.json();
    const nodes = await nodesRes.json();
    const stats = await statsRes.json();

    renderChain(chainData);
    renderMempool(mempool);
    renderNodes(nodes);
    updateStats(stats);
    log('Blockchain loaded', 'sync');
  } catch (e) {
    log('Failed to load chain: ' + e.message, 'error');
  }
})();
