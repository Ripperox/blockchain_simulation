from flask import Flask, jsonify, render_template, request # type: ignore
import hashlib
import time

app = Flask(__name__)

# Blockchain Class
class Blockchain:
    def __init__(self):
        self.chain = []
        self.difficulty = 4  # Number of leading zeros required in hash
        self.create_block("Genesis Block", "0")

    def create_block(self, data, previous_hash):
        index = len(self.chain)
        timestamp = time.time()
        block = {
            "index": index,
            "timestamp": timestamp,
            "data": data,
            "previous_hash": previous_hash,
            "nonce": 0  # Initial value, will be updated by mine_block
        }
        self.mine_block(block)
        self.chain.append(block)
        return block

    def compute_hash(self, index, timestamp, data, previous_hash, nonce):
        block_string = f"{index}{timestamp}{data}{previous_hash}{nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, block):
        target = "0" * self.difficulty
        while True:
            block["hash"] = self.compute_hash(
                block["index"],
                block["timestamp"],
                block["data"],
                block["previous_hash"],
                block["nonce"]
            )
            if block["hash"].startswith(target):
                break
            block["nonce"] += 1

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current["previous_hash"] != previous["hash"]:
                return False
            if self.compute_hash(
                current["index"],
                current["timestamp"],
                current["data"],
                current["previous_hash"],
                current["nonce"]
            ) != current["hash"]:
                return False
        return True

blockchain = Blockchain()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain.chain)

@app.route("/mine", methods=["POST"])
def mine():
    data = request.json.get("data", "")
    if not data:
        return jsonify({"error": "Data is required"}), 400
    previous_hash = blockchain.chain[-1]["hash"] if blockchain.chain else "0"
    new_block = blockchain.create_block(data, previous_hash)
    return jsonify(new_block)

@app.route("/fix_chain", methods=["POST"])
def fix_chain():
    for i in range(1, len(blockchain.chain)):
        blockchain.chain[i]["previous_hash"] = blockchain.chain[i - 1]["hash"]
        # Re-mine the block to ensure it meets difficulty
        blockchain.mine_block(blockchain.chain[i])
    return jsonify({"message": "Blockchain fixed!", "chain": blockchain.chain})

@app.route("/compute_hash", methods=["POST"])
def compute_hash():
    data = request.json
    try:
        index = data["index"]
        timestamp = data["timestamp"]
        block_data = data["data"]
        previous_hash = data["previous_hash"]
        nonce = data["nonce"]
        computed_hash = blockchain.compute_hash(index, timestamp, block_data, previous_hash, nonce)
        return jsonify({"hash": computed_hash})
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400

# Optional: Endpoint to update block data from frontend
@app.route("/update_block", methods=["POST"])
def update_block():
    data = request.json
    try:
        index = data["index"]
        new_data = data["data"]
        if index < 0 or index >= len(blockchain.chain):
            return jsonify({"error": "Invalid block index"}), 400
        block = blockchain.chain[index]
        block["data"] = new_data
        blockchain.mine_block(block)  # Re-mine to update hash and nonce
        # Update subsequent blocks
        for i in range(index + 1, len(blockchain.chain)):
            blockchain.chain[i]["previous_hash"] = blockchain.chain[i - 1]["hash"]
            blockchain.mine_block(blockchain.chain[i])
        return jsonify({"message": "Block updated!", "chain": blockchain.chain})
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400

if __name__ == "__main__":
    app.run(debug=True)