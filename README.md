# Blockchain Simulator

[![CI](https://github.com/Ripperox/blockchain_simulation/actions/workflows/ci.yml/badge.svg)](https://github.com/Ripperox/blockchain_simulation/actions/workflows/ci.yml)

A real-time blockchain simulator built with Flask and Socket.IO. Mine blocks, watch live PoW progress, manage a mempool, and observe a 3-node peer network — all in the browser.

![image](https://github.com/user-attachments/assets/7738df2a-f807-470a-a2d4-7c4cc345b7be)

## Features

- **Real-time mining** via WebSocket — watch the nonce counter, hash attempts/sec, and current hash animate as the block is mined
- **Mempool** — submit transactions (sender/recipient/amount), which get batched into the next mined block
- **Merkle tree** — each block computes a Merkle root from its transaction hashes
- **Dynamic difficulty** — adjusts every 10 blocks to target a 10-second block time
- **3-node network simulation** — alpha/beta/gamma nodes sync via longest-chain rule after each mine
- **Stats dashboard** — total blocks, avg block time, hash rate, current difficulty

## Stack

- **Backend:** Python, Flask, Flask-SocketIO, eventlet
- **Frontend:** Vanilla JS with Socket.IO client, JetBrains Mono terminal aesthetic

## Installation

### Option 1: Docker

```sh
git clone https://github.com/Ripperox/blockchain_simulation.git
cd blockchain_simulation
docker build -t blockchain-simulation .
docker run -p 5000:5000 blockchain-simulation
```

Open [http://localhost:5000](http://localhost:5000)

### Option 2: Local

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

## API Endpoints

| Method | Endpoint            | Description                        |
|--------|--------------------|------------------------------------|
| GET    | `/get_chain`        | Full blockchain with transactions  |
| POST   | `/mine`             | Start async mining (WebSocket)     |
| POST   | `/add_transaction`  | Add tx to mempool                  |
| GET    | `/get_mempool`      | Pending transactions               |
| GET    | `/get_stats`        | Network stats                      |
| GET    | `/get_nodes`        | 3-node network status              |

## Testing

The project ships with three layers of automated tests that back the behavior end to end:

| Layer | Location | What it covers |
|-------|----------|----------------|
| **Pytest unit tests** | `tests/test_blockchain.py` | Genesis block, deterministic hashing, proof-of-work leading-zero target, Merkle root (single/even/odd/tamper), mempool cap & FIFO, chain validation & tamper detection, dynamic difficulty adjustment, and longest-chain node sync |
| **Pytest API tests** | `tests/test_api.py` | Every HTTP route (`/get_chain`, `/add_transaction`, `/get_mempool`, `/mine`, `/get_stats`, `/get_nodes`) via the Flask test client, including the **async mining** path (polled with a timeout) and error cases |
| **Playwright E2E** | `e2e/sim.spec.js` | Boots the real Flask + Socket.IO server and drives a **headless Chromium** browser through the full live WebSocket mining round-trip: broadcast a tx, click *Mine*, and assert a new block card renders and the stats update |

### Run the Python tests

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Run the Playwright E2E tests

The E2E suite uses [Bun](https://bun.sh) and a Playwright `webServer` that launches
the Flask app on port `5055`, so it exercises the genuine Socket.IO mining flow in
a real browser — not a mock.

```sh
bun add -d @playwright/test
bunx playwright install chromium
bunx playwright test
```

Both suites run automatically on every push and pull request via
[GitHub Actions](.github/workflows/ci.yml) (see the CI badge above).

## File Structure

```
blockchain_simulation/
├── app.py                  # Flask backend + SocketIO + blockchain logic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt    # pytest + pytest-timeout
├── playwright.config.js    # Playwright config (boots Flask on :5055)
├── package.json
├── conftest.py
├── .github/
│   └── workflows/
│       └── ci.yml          # Pytest + Playwright CI
├── tests/                  # Pytest unit + API integration tests
│   ├── test_blockchain.py
│   └── test_api.py
├── e2e/                    # Playwright browser E2E
│   └── sim.spec.js
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```
