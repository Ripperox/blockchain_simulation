# Blockchain Simulator

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

## File Structure

```
blockchain_simulation/
├── app.py              # Flask backend + SocketIO + blockchain logic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```
