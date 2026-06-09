"""
Unit tests for the core blockchain primitives defined in app.py.

These tests exercise the REAL implementation: the Transaction dataclass,
the MerkleTree, the Mempool, the Blockchain (PoW mining, genesis, validation,
dynamic difficulty) and the longest-chain node sync.

Wherever possible the tests build fresh objects rather than relying on the
module-level globals so they are deterministic and order-independent.
"""

import hashlib

import pytest

import app as A
from app import (
    Transaction,
    MerkleTree,
    Mempool,
    Blockchain,
    compute_block_hash,
    BLOCK_REWARD,
    DIFFICULTY_ADJUSTMENT_INTERVAL,
    TARGET_BLOCK_TIME,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reference_merkle_root(tx_hashes):
    """Independent re-implementation of the Merkle algorithm to verify app.py."""
    if not tx_hashes:
        return hashlib.sha256(b"empty").hexdigest()
    level = list(tx_hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        nxt = []
        for i in range(0, len(level), 2):
            nxt.append(hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest())
        level = nxt
    return level[0]


def fresh_node(node_id="test-node"):
    return Blockchain(node_id)


def mine_n(node, n):
    """Mine n blocks onto `node` with one transaction each."""
    for i in range(n):
        tx = Transaction(sender=f"s{i}", recipient=f"r{i}", amount=float(i + 1))
        node.mine_block([tx], miner=f"miner-{i}", emit_progress=False)


# ---------------------------------------------------------------------------
# Genesis block
# ---------------------------------------------------------------------------

def test_genesis_exists_and_index_zero():
    node = fresh_node()
    assert len(node.chain) == 1
    assert node.chain[0]["index"] == 0


def test_genesis_previous_hash_all_zeros():
    node = fresh_node()
    prev = node.chain[0]["previous_hash"]
    assert prev == "0" * 64
    assert set(prev) == {"0"}


def test_genesis_hash_meets_difficulty():
    node = fresh_node()
    g = node.chain[0]
    assert g["hash"].startswith("0" * g["difficulty"])


def test_genesis_has_single_coinbase_tx():
    node = fresh_node()
    txs = node.chain[0]["transactions"]
    assert len(txs) == 1
    assert txs[0]["sender"] == "COINBASE"
    assert txs[0]["amount"] == BLOCK_REWARD


def test_genesis_chain_is_valid():
    # A chain consisting of only the genesis block is trivially valid.
    node = fresh_node()
    assert node.is_valid() is True


# ---------------------------------------------------------------------------
# compute_block_hash determinism
# ---------------------------------------------------------------------------

BASE_ARGS = dict(
    index=1,
    transactions_root="aa" * 32,
    merkle_root="bb" * 32,
    timestamp=1234567890.0,
    previous_hash="cc" * 32,
    nonce=42,
    miner="node-x",
    difficulty=3,
)


def _hash(**overrides):
    args = dict(BASE_ARGS)
    args.update(overrides)
    return compute_block_hash(**args)


def test_compute_block_hash_deterministic():
    assert _hash() == _hash()
    # length / hex sanity
    h = _hash()
    assert len(h) == 64
    int(h, 16)  # raises if not hex


@pytest.mark.parametrize(
    "field,newval",
    [
        ("index", 2),
        ("transactions_root", "00" * 32),
        ("merkle_root", "11" * 32),
        ("timestamp", 1234567891.0),
        ("previous_hash", "ff" * 32),
        ("nonce", 43),
        ("miner", "node-y"),
        ("difficulty", 4),
    ],
)
def test_compute_block_hash_changes_on_any_field(field, newval):
    assert _hash() != _hash(**{field: newval})


# ---------------------------------------------------------------------------
# Transaction hashing / signing
# ---------------------------------------------------------------------------

def test_transaction_hash_is_deterministic():
    t1 = Transaction("alice", "bob", 5.0, timestamp=100.0)
    t2 = Transaction("alice", "bob", 5.0, timestamp=100.0)
    assert t1.tx_hash == t2.tx_hash
    # matches the documented preimage
    raw = "alicebob5.0100.0"
    assert t1.tx_hash == hashlib.sha256(raw.encode()).hexdigest()


def test_transaction_hash_changes_with_amount():
    t1 = Transaction("alice", "bob", 5.0, timestamp=100.0)
    t2 = Transaction("alice", "bob", 6.0, timestamp=100.0)
    assert t1.tx_hash != t2.tx_hash


def test_transaction_hash_changes_with_participants_and_time():
    base = Transaction("alice", "bob", 5.0, timestamp=100.0)
    assert base.tx_hash != Transaction("alicex", "bob", 5.0, timestamp=100.0).tx_hash
    assert base.tx_hash != Transaction("alice", "bobx", 5.0, timestamp=100.0).tx_hash
    assert base.tx_hash != Transaction("alice", "bob", 5.0, timestamp=101.0).tx_hash


def test_transaction_signature_present_and_derived():
    t = Transaction("alice", "bob", 5.0, timestamp=100.0)
    assert t.signature
    assert len(t.signature) == 64
    expected = hashlib.sha256(f"sig:{t.tx_hash}:alice".encode()).hexdigest()[:64]
    assert t.signature == expected


def test_transaction_to_dict_roundtrip_fields():
    t = Transaction("alice", "bob", 5.0, timestamp=100.0)
    d = t.to_dict()
    assert set(d) == {"sender", "recipient", "amount", "timestamp", "tx_hash", "signature"}
    assert d["sender"] == "alice" and d["amount"] == 5.0


# ---------------------------------------------------------------------------
# Proof-of-Work
# ---------------------------------------------------------------------------

def test_pow_mined_block_meets_difficulty():
    node = fresh_node()
    block = node.mine_block([], miner="m", emit_progress=False)
    assert block["hash"].startswith("0" * block["difficulty"])
    assert block["difficulty"] == node.difficulty


def test_pow_block_links_to_previous_hash():
    node = fresh_node()
    prev_hash = node.chain[-1]["hash"]
    block = node.mine_block([], miner="m", emit_progress=False)
    assert block["previous_hash"] == prev_hash
    assert block["index"] == 1


def test_pow_multiple_blocks_all_meet_difficulty():
    node = fresh_node()
    mine_n(node, 4)
    for b in node.chain:
        assert b["hash"].startswith("0" * b["difficulty"])


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------

def test_merkle_empty_is_known_constant():
    assert MerkleTree.compute_root([]) == hashlib.sha256(b"empty").hexdigest()


def test_merkle_single_tx_returns_the_hash():
    h = hashlib.sha256(b"only").hexdigest()
    assert MerkleTree.compute_root([h]) == h


def test_merkle_two_txs_known_value():
    root = MerkleTree.compute_root(["a", "b"])
    assert root == hashlib.sha256(b"ab").hexdigest()


def test_merkle_odd_count_duplicates_last():
    # 3 hashes -> last duplicated. Compare against the reference impl.
    hashes = ["a", "b", "c"]
    assert MerkleTree.compute_root(hashes) == reference_merkle_root(hashes)


def test_merkle_is_deterministic_and_stable():
    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(5)]
    r1 = MerkleTree.compute_root(hashes)
    r2 = MerkleTree.compute_root(list(hashes))
    assert r1 == r2


def test_merkle_changes_when_a_tx_changes():
    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(4)]
    before = MerkleTree.compute_root(hashes)
    mutated = list(hashes)
    mutated[2] = hashlib.sha256(b"tampered").hexdigest()
    assert MerkleTree.compute_root(mutated) != before


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 8, 9])
def test_merkle_matches_reference_for_even_and_odd(count):
    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(count)]
    assert MerkleTree.compute_root(hashes) == reference_merkle_root(hashes)


# ---------------------------------------------------------------------------
# Mining: coinbase + mempool inclusion
# ---------------------------------------------------------------------------

def test_mine_block_includes_coinbase_first():
    node = fresh_node()
    block = node.mine_block([], miner="miner-addr", emit_progress=False)
    coinbase = block["transactions"][0]
    assert coinbase["sender"] == "COINBASE"
    assert coinbase["recipient"] == "miner-addr"
    assert coinbase["amount"] == BLOCK_REWARD
    assert block["block_reward"] == BLOCK_REWARD


def test_mine_block_includes_supplied_transactions():
    node = fresh_node()
    txs = [Transaction("a", "b", 1.0), Transaction("c", "d", 2.0)]
    block = node.mine_block(txs, miner="m", emit_progress=False)
    # coinbase + 2 supplied
    assert len(block["transactions"]) == 3
    included = {t["tx_hash"] for t in block["transactions"]}
    for t in txs:
        assert t.tx_hash in included


def test_mine_block_merkle_root_matches_transactions():
    node = fresh_node()
    txs = [Transaction("a", "b", 1.0), Transaction("c", "d", 2.0)]
    block = node.mine_block(txs, miner="m", emit_progress=False)
    recomputed = MerkleTree.compute_root([t["tx_hash"] for t in block["transactions"]])
    assert block["merkle_root"] == recomputed


# ---------------------------------------------------------------------------
# Mempool
# ---------------------------------------------------------------------------

def test_mempool_add_increases_size():
    mp = Mempool()
    assert mp.size() == 0
    mp.add(Transaction("a", "b", 1.0))
    mp.add(Transaction("c", "d", 2.0))
    assert mp.size() == 2


def test_mempool_pop_for_block_respects_cap():
    mp = Mempool()
    txs = [Transaction("s", f"r{i}", float(i)) for i in range(15)]
    for t in txs:
        mp.add(t)
    selected = mp.pop_for_block()
    assert len(selected) == Mempool.MAX_PER_BLOCK == 10
    assert mp.size() == 5


def test_mempool_pop_is_fifo_and_clears():
    mp = Mempool()
    txs = [Transaction("s", f"r{i}", float(i)) for i in range(3)]
    for t in txs:
        mp.add(t)
    selected = mp.pop_for_block()
    # FIFO order preserved
    assert [t.tx_hash for t in selected] == [t.tx_hash for t in txs]
    assert mp.size() == 0


def test_mempool_peek_returns_independent_copy():
    mp = Mempool()
    mp.add(Transaction("a", "b", 1.0))
    snapshot = mp.peek()
    snapshot.clear()
    assert mp.size() == 1  # internal list untouched


def test_mempool_remove_by_hashes():
    mp = Mempool()
    t1 = Transaction("a", "b", 1.0)
    t2 = Transaction("c", "d", 2.0)
    mp.add(t1)
    mp.add(t2)
    mp.remove_by_hashes({t1.tx_hash})
    remaining = mp.peek()
    assert len(remaining) == 1
    assert remaining[0].tx_hash == t2.tx_hash


# ---------------------------------------------------------------------------
# Chain validation / tampering detection
# ---------------------------------------------------------------------------

def test_valid_chain_passes():
    node = fresh_node()
    mine_n(node, 3)
    assert node.is_valid() is True


def test_tampering_with_merkle_root_is_detected():
    node = fresh_node()
    mine_n(node, 2)
    assert node.is_valid() is True
    node.chain[1]["merkle_root"] = "deadbeef" * 8
    assert node.is_valid() is False


def test_tampering_with_a_transaction_is_detected():
    node = fresh_node()
    mine_n(node, 2)
    # Mutating a stored tx hash changes the recomputed merkle root.
    node.chain[1]["transactions"][0]["tx_hash"] = "f" * 64
    assert node.is_valid() is False


def test_breaking_previous_hash_linkage_is_detected():
    node = fresh_node()
    mine_n(node, 3)
    assert node.is_valid() is True
    node.chain[2]["previous_hash"] = "0" * 64
    assert node.is_valid() is False


# ---------------------------------------------------------------------------
# Dynamic difficulty
# ---------------------------------------------------------------------------

def _pad_chain_to(node, length):
    """Append filler block dicts so len(node.chain) == length."""
    while len(node.chain) < length:
        node.chain.append({"index": len(node.chain)})


def test_difficulty_increases_when_blocks_are_too_fast():
    node = fresh_node()
    node.difficulty = 3
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL)  # 10
    # All blocks much faster than half the target -> bump difficulty.
    node._block_times = [TARGET_BLOCK_TIME * 0.1] * DIFFICULTY_ADJUSTMENT_INTERVAL
    node._adjust_difficulty()
    assert node.difficulty == 4


def test_difficulty_decreases_when_blocks_are_too_slow():
    node = fresh_node()
    node.difficulty = 3
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL)
    node._block_times = [TARGET_BLOCK_TIME * 3] * DIFFICULTY_ADJUSTMENT_INTERVAL
    node._adjust_difficulty()
    assert node.difficulty == 2


def test_difficulty_unchanged_in_normal_range():
    node = fresh_node()
    node.difficulty = 3
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL)
    node._block_times = [float(TARGET_BLOCK_TIME)] * DIFFICULTY_ADJUSTMENT_INTERVAL
    node._adjust_difficulty()
    assert node.difficulty == 3


def test_difficulty_unchanged_off_adjustment_interval():
    node = fresh_node()
    node.difficulty = 3
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL // 2)  # not a multiple of 10
    node._block_times = [TARGET_BLOCK_TIME * 0.1] * 5
    node._adjust_difficulty()
    assert node.difficulty == 3


def test_difficulty_clamped_at_max():
    node = fresh_node()
    node.difficulty = 6  # max
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL)
    node._block_times = [TARGET_BLOCK_TIME * 0.1] * DIFFICULTY_ADJUSTMENT_INTERVAL
    node._adjust_difficulty()
    assert node.difficulty == 6


def test_difficulty_clamped_at_min():
    node = fresh_node()
    node.difficulty = 1  # min
    _pad_chain_to(node, DIFFICULTY_ADJUSTMENT_INTERVAL)
    node._block_times = [TARGET_BLOCK_TIME * 3] * DIFFICULTY_ADJUSTMENT_INTERVAL
    node._adjust_difficulty()
    assert node.difficulty == 1


# ---------------------------------------------------------------------------
# Node sync (longest-chain rule)
# ---------------------------------------------------------------------------

def test_replace_chain_adopts_longer_chain():
    short = fresh_node("short")
    long = fresh_node("long")
    mine_n(long, 3)
    assert len(long.chain) > len(short.chain)
    replaced = short.replace_chain(list(long.chain))
    assert replaced is True
    assert len(short.chain) == len(long.chain)
    assert short.chain[-1]["hash"] == long.chain[-1]["hash"]


def test_replace_chain_rejects_equal_or_shorter():
    a = fresh_node("a")
    b = fresh_node("b")
    mine_n(a, 2)
    mine_n(b, 2)
    # Equal length -> not replaced.
    assert b.replace_chain(list(a.chain)) is False
    # Shorter -> not replaced.
    short = fresh_node("short")
    assert a.replace_chain(list(short.chain)) is False


def test_sync_nodes_propagates_longest_chain(monkeypatch):
    # Exercise the REAL app.sync_nodes against a fresh, isolated node set.
    a = fresh_node("alpha")
    b = fresh_node("beta")
    c = fresh_node("gamma")
    mine_n(a, 4)  # alpha is the longest

    monkeypatch.setattr(A, "nodes", [a, b, c])
    A.sync_nodes()

    assert len(b.chain) == len(a.chain) == len(c.chain)
    assert b.chain[-1]["hash"] == a.chain[-1]["hash"]
    assert c.chain[-1]["hash"] == a.chain[-1]["hash"]


# ---------------------------------------------------------------------------
# Stats / summary
# ---------------------------------------------------------------------------

def test_stats_reports_expected_fields():
    node = fresh_node()
    mine_n(node, 2)
    stats = node.stats()
    assert set(stats) == {
        "total_blocks",
        "avg_block_time",
        "current_difficulty",
        "total_transactions",
        "network_hash_rate",
    }
    assert stats["total_blocks"] == len(node.chain) == 3
    # genesis(1) + 2 mined blocks each (coinbase + 1 supplied tx) = 1 + 2*2
    assert stats["total_transactions"] == 5
    assert stats["current_difficulty"] == node.difficulty


def test_summary_reports_expected_fields():
    node = fresh_node()
    mine_n(node, 1)
    s = node.summary()
    assert set(s) == {"node_id", "chain_length", "last_block_hash", "difficulty", "peer_count"}
    assert s["chain_length"] == 2
    assert s["last_block_hash"] == node.chain[-1]["hash"]
    assert s["peer_count"] == 2
