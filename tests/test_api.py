"""
HTTP integration tests for the Flask routes in app.py, driven through the
Flask test client.

Mining is asynchronous (a background thread started by POST /mine that emits
Socket.IO progress), so those tests poll GET /get_chain until the chain grows,
with a bounded timeout.

These tests operate against the module-level singletons (primary node / shared
mempool), which is the real wiring the browser talks to.
"""

import time

import pytest

import app as A


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    A.app.config["TESTING"] = True
    return A.app.test_client()


def _chain_len(client):
    return len(client.get("/get_chain").get_json())


def _wait_for_lock_free(timeout=10.0):
    start = time.time()
    while A.mining_lock.locked() and time.time() - start < timeout:
        time.sleep(0.02)


def _mine_and_wait(client, timeout=20.0):
    """POST /mine and block until the chain grows. Returns the new length."""
    _wait_for_lock_free()
    before = _chain_len(client)
    resp = client.post("/mine", json={})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "mining_started"

    start = time.time()
    while time.time() - start < timeout:
        if _chain_len(client) > before:
            _wait_for_lock_free()  # let the background thread fully release
            return before + 1
        time.sleep(0.05)
    pytest.fail("Mining did not produce a new block within the timeout")


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def test_index_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "<html" in body.lower()
    assert "BlockChain" in body


# ---------------------------------------------------------------------------
# GET /get_chain
# ---------------------------------------------------------------------------

def test_get_chain_returns_list_with_genesis(client):
    chain = client.get("/get_chain").get_json()
    assert isinstance(chain, list)
    assert len(chain) >= 1
    assert chain[0]["index"] == 0
    assert chain[0]["previous_hash"] == "0" * 64


def test_chain_blocks_expose_expected_fields(client):
    block = client.get("/get_chain").get_json()[0]
    for field in (
        "index",
        "transactions",
        "merkle_root",
        "timestamp",
        "previous_hash",
        "nonce",
        "hash",
        "miner",
        "difficulty",
        "block_reward",
    ):
        assert field in block, f"missing block field: {field}"


# ---------------------------------------------------------------------------
# POST /add_transaction + GET /get_mempool
# ---------------------------------------------------------------------------

def test_add_transaction_returns_tx_and_appears_in_mempool(client):
    before = len(client.get("/get_mempool").get_json())
    payload = {"sender": "0xSenderTest", "recipient": "0xRecipientTest", "amount": 3.5}
    resp = client.post("/add_transaction", json=payload)
    assert resp.status_code == 200
    tx = resp.get_json()
    assert tx["sender"] == payload["sender"]
    assert tx["recipient"] == payload["recipient"]
    assert tx["amount"] == 3.5
    assert tx["tx_hash"] and len(tx["tx_hash"]) == 64
    assert tx["signature"]

    mempool = client.get("/get_mempool").get_json()
    assert len(mempool) == before + 1
    assert any(t["tx_hash"] == tx["tx_hash"] for t in mempool)


def test_add_transaction_casts_string_amount(client):
    resp = client.post(
        "/add_transaction",
        json={"sender": "a", "recipient": "b", "amount": "7.25"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["amount"] == 7.25


def test_add_transaction_missing_fields_returns_400(client):
    resp = client.post("/add_transaction", json={"sender": "a", "recipient": "b"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_add_transaction_empty_payload_returns_400(client):
    resp = client.post("/add_transaction", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_add_transaction_invalid_amount_returns_400(client):
    resp = client.post(
        "/add_transaction",
        json={"sender": "a", "recipient": "b", "amount": "not-a-number"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# POST /mine (async)
# ---------------------------------------------------------------------------

def test_mine_when_locked_returns_409(client):
    # Hold the mining lock to deterministically trigger the busy path.
    _wait_for_lock_free()
    acquired = A.mining_lock.acquire(blocking=False)
    assert acquired
    try:
        resp = client.post("/mine", json={})
        assert resp.status_code == 409
        assert "error" in resp.get_json()
    finally:
        A.mining_lock.release()


def test_mine_starts_and_chain_grows(client):
    before = _chain_len(client)
    after = _mine_and_wait(client)
    assert after == before + 1
    # The newly mined block satisfies its own proof-of-work target.
    new_block = client.get("/get_chain").get_json()[-1]
    assert new_block["hash"].startswith("0" * new_block["difficulty"])
    # Coinbase reward tx present.
    assert new_block["transactions"][0]["sender"] == "COINBASE"


def test_mine_clears_mined_transactions_from_mempool(client):
    # Seed a known transaction, mine, then confirm it is no longer pending.
    payload = {"sender": "0xClearMe", "recipient": "0xDest", "amount": 1.0}
    tx = client.post("/add_transaction", json=payload).get_json()
    pending_hashes = {t["tx_hash"] for t in client.get("/get_mempool").get_json()}
    assert tx["tx_hash"] in pending_hashes

    _mine_and_wait(client)

    still_pending = {t["tx_hash"] for t in client.get("/get_mempool").get_json()}
    assert tx["tx_hash"] not in still_pending


# ---------------------------------------------------------------------------
# GET /get_stats
# ---------------------------------------------------------------------------

def test_get_stats_returns_expected_fields(client):
    stats = client.get("/get_stats").get_json()
    for field in (
        "total_blocks",
        "avg_block_time",
        "current_difficulty",
        "total_transactions",
        "network_hash_rate",
    ):
        assert field in stats, f"missing stat field: {field}"
    assert stats["total_blocks"] == _chain_len(client)
    assert isinstance(stats["current_difficulty"], int)


# ---------------------------------------------------------------------------
# GET /get_nodes
# ---------------------------------------------------------------------------

def test_get_nodes_returns_three_nodes_with_fields(client):
    nodes = client.get("/get_nodes").get_json()
    assert isinstance(nodes, list)
    assert len(nodes) == 3
    for node in nodes:
        for field in ("node_id", "chain_length", "last_block_hash", "difficulty", "peer_count"):
            assert field in node, f"missing node field: {field}"
        assert isinstance(node["chain_length"], int)
        assert node["peer_count"] == 2


def test_nodes_converge_after_mining(client):
    _mine_and_wait(client)
    nodes = client.get("/get_nodes").get_json()
    lengths = {n["chain_length"] for n in nodes}
    last_hashes = {n["last_block_hash"] for n in nodes}
    # Longest-chain sync runs after each mine -> all nodes agree.
    assert len(lengths) == 1
    assert len(last_hashes) == 1
