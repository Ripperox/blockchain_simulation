from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import hashlib
import time
import random
import string
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Optional

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blockchain-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    timestamp: float = field(default_factory=time.time)
    tx_hash: str = ""
    signature: str = ""

    def __post_init__(self):
        if not self.tx_hash:
            raw = f"{self.sender}{self.recipient}{self.amount}{self.timestamp}"
            self.tx_hash = hashlib.sha256(raw.encode()).hexdigest()
        if not self.signature:
            # Simulated ECDSA signature
            self.signature = hashlib.sha256(f"sig:{self.tx_hash}:{self.sender}".encode()).hexdigest()[:64]

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Merkle Tree
# ---------------------------------------------------------------------------

class MerkleTree:
    @staticmethod
    def compute_root(tx_hashes: List[str]) -> str:
        if not tx_hashes:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = list(tx_hashes)
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = next_level
        return hashes[0]


# ---------------------------------------------------------------------------
# Mempool
# ---------------------------------------------------------------------------

class Mempool:
    MAX_PER_BLOCK = 10

    def __init__(self):
        self._txs: List[Transaction] = []
        self._lock = threading.Lock()

    def add(self, tx: Transaction):
        with self._lock:
            self._txs.append(tx)

    def pop_for_block(self) -> List[Transaction]:
        with self._lock:
            selected = self._txs[:self.MAX_PER_BLOCK]
            self._txs = self._txs[self.MAX_PER_BLOCK:]
            return selected

    def peek(self) -> List[Transaction]:
        with self._lock:
            return list(self._txs)

    def remove_by_hashes(self, hashes: set):
        with self._lock:
            self._txs = [t for t in self._txs if t.tx_hash not in hashes]

    def size(self) -> int:
        with self._lock:
            return len(self._txs)


# ---------------------------------------------------------------------------
# Block / Blockchain
# ---------------------------------------------------------------------------

DIFFICULTY_ADJUSTMENT_INTERVAL = 10
TARGET_BLOCK_TIME = 10  # seconds
BLOCK_REWARD = 50.0

def compute_block_hash(index, transactions_root, merkle_root, timestamp, previous_hash, nonce, miner, difficulty):
    raw = f"{index}{transactions_root}{merkle_root}{timestamp}{previous_hash}{nonce}{miner}{difficulty}"
    return hashlib.sha256(raw.encode()).hexdigest()


class Blockchain:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.chain = []
        self.difficulty = 3
        self._block_times = []
        self._lock = threading.Lock()
        self._create_genesis()

    def _create_genesis(self):
        genesis_tx = Transaction(
            sender="COINBASE",
            recipient="genesis",
            amount=BLOCK_REWARD,
            timestamp=time.time()
        )
        block = {
            "index": 0,
            "transactions": [genesis_tx.to_dict()],
            "merkle_root": MerkleTree.compute_root([genesis_tx.tx_hash]),
            "timestamp": time.time(),
            "previous_hash": "0" * 64,
            "nonce": 0,
            "hash": "",
            "miner": self.node_id,
            "difficulty": self.difficulty,
            "block_reward": BLOCK_REWARD,
            "block_time": 0,
        }
        target = "0" * self.difficulty
        while True:
            block["hash"] = compute_block_hash(
                block["index"], block["merkle_root"], block["merkle_root"],
                block["timestamp"], block["previous_hash"], block["nonce"],
                block["miner"], block["difficulty"]
            )
            if block["hash"].startswith(target):
                break
            block["nonce"] += 1
        self.chain.append(block)

    def _adjust_difficulty(self):
        n = len(self.chain)
        if n < DIFFICULTY_ADJUSTMENT_INTERVAL or n % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return
        recent = self._block_times[-DIFFICULTY_ADJUSTMENT_INTERVAL:]
        if not recent:
            return
        avg = sum(recent) / len(recent)
        if avg < TARGET_BLOCK_TIME * 0.5:
            self.difficulty = min(self.difficulty + 1, 6)
        elif avg > TARGET_BLOCK_TIME * 2:
            self.difficulty = max(self.difficulty - 1, 1)

    def mine_block(self, transactions: List[Transaction], miner: str, emit_progress=False):
        with self._lock:
            prev = self.chain[-1]
            prev_hash = prev["hash"]
            index = len(self.chain)
            ts = time.time()

            # Coinbase reward tx
            coinbase = Transaction(sender="COINBASE", recipient=miner, amount=BLOCK_REWARD, timestamp=ts)
            all_txs = [coinbase] + transactions

            tx_hashes = [t.tx_hash for t in all_txs]
            merkle_root = MerkleTree.compute_root(tx_hashes)
            transactions_root = hashlib.sha256("".join(tx_hashes).encode()).hexdigest()

            block = {
                "index": index,
                "transactions": [t.to_dict() for t in all_txs],
                "merkle_root": merkle_root,
                "timestamp": ts,
                "previous_hash": prev_hash,
                "nonce": 0,
                "hash": "",
                "miner": miner,
                "difficulty": self.difficulty,
                "block_reward": BLOCK_REWARD,
                "block_time": 0,
            }

            target = "0" * self.difficulty
            start = time.time()
            last_emit = time.time()
            attempts_window_start = time.time()
            attempts_in_window = 0

            while True:
                block["hash"] = compute_block_hash(
                    block["index"], transactions_root, merkle_root,
                    block["timestamp"], block["previous_hash"], block["nonce"],
                    block["miner"], block["difficulty"]
                )
                attempts_in_window += 1

                if block["hash"].startswith(target):
                    break

                if emit_progress and block["nonce"] % 500 == 0:
                    now = time.time()
                    elapsed = now - attempts_window_start
                    aps = int(attempts_in_window / elapsed) if elapsed > 0 else 0
                    if now - last_emit >= 0.1:
                        socketio.emit('mining_progress', {
                            'node': self.node_id,
                            'current_nonce': block["nonce"],
                            'current_hash': block["hash"],
                            'attempts_per_second': aps,
                            'difficulty': self.difficulty,
                        })
                        last_emit = now

                block["nonce"] += 1

            elapsed = time.time() - start
            block["block_time"] = round(elapsed, 3)
            self._block_times.append(elapsed)

            self.chain.append(block)
            self._adjust_difficulty()
            return block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            cur = self.chain[i]
            prev = self.chain[i - 1]
            if cur["previous_hash"] != prev["hash"]:
                return False
            tx_hashes = [t["tx_hash"] for t in cur["transactions"]]
            merkle_root = MerkleTree.compute_root(tx_hashes)
            if merkle_root != cur["merkle_root"]:
                return False
        return True

    def replace_chain(self, new_chain: list) -> bool:
        with self._lock:
            if len(new_chain) > len(self.chain):
                self.chain = new_chain
                return True
        return False

    def summary(self) -> dict:
        last = self.chain[-1]
        return {
            "node_id": self.node_id,
            "chain_length": len(self.chain),
            "last_block_hash": last["hash"],
            "difficulty": self.difficulty,
            "peer_count": 2,
        }

    def stats(self) -> dict:
        total_txs = sum(len(b["transactions"]) for b in self.chain)
        times = self._block_times
        avg_time = round(sum(times) / len(times), 2) if times else 0
        # Simulated network hash rate based on difficulty and avg block time
        network_hash_rate = int((16 ** self.difficulty) / avg_time) if avg_time > 0 else 0
        return {
            "total_blocks": len(self.chain),
            "avg_block_time": avg_time,
            "current_difficulty": self.difficulty,
            "total_transactions": total_txs,
            "network_hash_rate": network_hash_rate,
        }


# ---------------------------------------------------------------------------
# Multi-node simulation
# ---------------------------------------------------------------------------

mempool = Mempool()
nodes: List[Blockchain] = [
    Blockchain("node-alpha"),
    Blockchain("node-beta"),
    Blockchain("node-gamma"),
]
# Primary node (node-alpha) is the one users mine on
primary = nodes[0]
mining_lock = threading.Lock()


def sync_nodes():
    """Propagate longest chain to all nodes."""
    longest = max(nodes, key=lambda n: len(n.chain))
    for node in nodes:
        if node is not longest:
            node.replace_chain(list(longest.chain))


def _random_addr():
    return "0x" + ''.join(random.choices(string.hexdigits[:16], k=40))


def seed_mempool():
    """Pre-populate mempool with some transactions."""
    addrs = [_random_addr() for _ in range(6)]
    for i in range(5):
        tx = Transaction(
            sender=addrs[i % 6],
            recipient=addrs[(i + 1) % 6],
            amount=round(random.uniform(0.1, 10.0), 4)
        )
        mempool.add(tx)


seed_mempool()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_chain", methods=["GET"])
def get_chain():
    return jsonify(primary.chain)


@app.route("/mine", methods=["POST"])
def mine():
    if not mining_lock.acquire(blocking=False):
        return jsonify({"error": "Mining already in progress"}), 409

    def do_mine():
        try:
            txs = mempool.pop_for_block()
            miner_addr = _random_addr()
            block = primary.mine_block(txs, miner_addr, emit_progress=True)
            mined_hashes = {t["tx_hash"] for t in block["transactions"]}
            mempool.remove_by_hashes(mined_hashes)
            sync_nodes()
            socketio.emit('block_mined', {
                'block': block,
                'chain_length': len(primary.chain),
                'mempool_size': mempool.size(),
            })
            # Add a couple of new random txs to mempool after mining
            for _ in range(random.randint(1, 3)):
                tx = Transaction(
                    sender=_random_addr(),
                    recipient=_random_addr(),
                    amount=round(random.uniform(0.01, 20.0), 4)
                )
                mempool.add(tx)
            socketio.emit('mempool_updated', {
                'transactions': [t.to_dict() for t in mempool.peek()],
            })
            socketio.emit('nodes_updated', {'nodes': [n.summary() for n in nodes]})
        finally:
            mining_lock.release()

    t = threading.Thread(target=do_mine, daemon=True)
    t.start()
    return jsonify({"status": "mining_started"})


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    data = request.json or {}
    try:
        tx = Transaction(
            sender=data["sender"],
            recipient=data["recipient"],
            amount=float(data["amount"])
        )
        mempool.add(tx)
        socketio.emit('mempool_updated', {
            'transactions': [t.to_dict() for t in mempool.peek()],
        })
        return jsonify(tx.to_dict())
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/get_mempool", methods=["GET"])
def get_mempool():
    return jsonify([t.to_dict() for t in mempool.peek()])


@app.route("/get_stats", methods=["GET"])
def get_stats():
    return jsonify(primary.stats())


@app.route("/get_nodes", methods=["GET"])
def get_nodes():
    return jsonify([n.summary() for n in nodes])


# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------

@socketio.on('connect')
def on_connect():
    emit('init', {
        'chain': primary.chain,
        'mempool': [t.to_dict() for t in mempool.peek()],
        'stats': primary.stats(),
        'nodes': [n.summary() for n in nodes],
    })


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
