document.addEventListener("DOMContentLoaded", () => {
    fetchChain();
    const blockDataInput = document.getElementById("blockData");
    blockDataInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter") mineBlock();
    });
});

async function fetchChain() {
    try {
        const response = await fetch("/get_chain");
        const chain = await response.json();
        console.log("Chain data:", chain);
        displayBlocks(chain);
    } catch (error) {
        console.error("Error fetching chain:", error);
    }
}

function displayBlocks(chain) {
    const container = document.getElementById("blockchainContainer");
    container.innerHTML = "";

    chain.forEach((block) => {
        const blockDiv = document.createElement("div");
        blockDiv.classList.add("block");
        blockDiv.dataset.index = block.index;
        blockDiv.dataset.hash = block.hash;
        blockDiv.dataset.previousHash = block.previous_hash;
        blockDiv.dataset.nonce = block.nonce;
        blockDiv.dataset.timestamp = block.timestamp;

        blockDiv.innerHTML = `
            <h3>Block #${block.index}</h3>
            <p><strong>Prev:</strong> ${block.previous_hash.slice(0, 8)}...</p>
            <input type="text" class="data" value="${block.data}">
            <p><strong>Nonce:</strong> ${block.nonce}</p>
            <p><strong>Hash:</strong> <span class="hash" data-full-hash="${block.hash}">${block.hash.slice(0, 8)}...</span></p>
        `;

        const dataInput = blockDiv.querySelector(".data");
        const hashSpan = blockDiv.querySelector(".hash");

        // Option 1: Client-side hash recalculation (default behavior)
        dataInput.addEventListener("input", async () => {
            const newData = dataInput.value;
            const newHash = await computeHash(
                blockDiv.dataset.index,
                blockDiv.dataset.timestamp,
                newData,
                blockDiv.dataset.previousHash,
                blockDiv.dataset.nonce
            );
            blockDiv.dataset.hash = newHash;
            hashSpan.dataset.fullHash = newHash;
            hashSpan.textContent = `${newHash.slice(0, 8)}...`;
            validateBlockchain();
        });

        // Option 2: Persist changes to server (uncomment to use)
        /*
        dataInput.addEventListener("input", async () => {
            const newData = dataInput.value;
            try {
                const response = await fetch("/update_block", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ index: parseInt(blockDiv.dataset.index), data: newData }),
                });
                if (response.ok) {
                    fetchChain(); // Refresh entire chain from server
                } else {
                    console.error("Failed to update block:", await response.json());
                }
            } catch (error) {
                console.error("Error updating block:", error);
            }
        });
        */

        container.appendChild(blockDiv);
    });

    validateBlockchain();
}

async function mineBlock() {
    const blockData = document.getElementById("blockData").value.trim();
    if (!blockData) return alert("Please enter block data!");

    try {
        const response = await fetch("/mine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data: blockData }),
        });
        if (response.ok) {
            document.getElementById("blockData").value = ""; // Clear input
            fetchChain();
        } else {
            console.error("Mining failed:", await response.json());
        }
    } catch (error) {
        console.error("Error mining block:", error);
    }
}

async function validateBlockchain() {
    const blocks = document.querySelectorAll(".block");
    let isChainValid = true;

    for (let i = 1; i < blocks.length; i++) {
        const prevBlock = blocks[i - 1];
        const currBlock = blocks[i];

        const expectedPrevHash = prevBlock.dataset.hash;
        const actualPrevHash = currBlock.dataset.previousHash;

        const recalculatedHash = await computeHash(
            currBlock.dataset.index,
            currBlock.dataset.timestamp,
            currBlock.querySelector(".data").value,
            actualPrevHash,
            currBlock.dataset.nonce
        );

        if (actualPrevHash !== expectedPrevHash || recalculatedHash !== currBlock.dataset.hash) {
            currBlock.classList.add("invalid");
            currBlock.classList.remove("valid");
            isChainValid = false;
            for (let j = i + 1; j < blocks.length; j++) {
                blocks[j].classList.add("invalid");
                blocks[j].classList.remove("valid");
            }
            break;
        } else {
            currBlock.classList.remove("invalid");
            currBlock.classList.add("valid");
        }
    }
}

async function computeHash(index, timestamp, data, previousHash, nonce) {
    try {
        const response = await fetch("/compute_hash", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ index, timestamp, data, previous_hash: previousHash, nonce }),
        });
        const result = await response.json();
        return result.hash;
    } catch (error) {
        console.error("Error computing hash:", error);
        return "";
    }
}

async function fixBlockchain() {
    try {
        const response = await fetch("/fix_chain", { method: "POST" });
        if (response.ok) {
            fetchChain();
        } else {
            console.error("Failed to fix chain:", await response.json());
        }
    } catch (error) {
        console.error("Error fixing chain:", error);
    }
}