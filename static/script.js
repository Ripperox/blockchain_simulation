document.addEventListener("DOMContentLoaded", () => {
    fetchChain();
    const blockDataInput = document.getElementById("blockData");
    if (blockDataInput) {
        blockDataInput.addEventListener("keypress", (event) => {
            if (event.key === "Enter") mineBlock();
        });
    }

    // Add event listener for the mine button if it exists
    const mineButton = document.getElementById("mineButton");
    if (mineButton) {
        mineButton.addEventListener("click", mineBlock);
    }

    // Add event listener for the fix button if it exists
    const fixButton = document.getElementById("fixButton");
    if (fixButton) {
        fixButton.addEventListener("click", fixBlockchain);
    }
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
    // Find the container - try both potential IDs/classes
    const container = document.getElementById("blockchainContainer") || document.querySelector(".blockchain-grid");
    if (!container) {
        console.error("Could not find blockchain container");
        return;
    }
    
    container.innerHTML = "";

    chain.forEach((block) => {
        const blockDiv = document.createElement("div");
        blockDiv.classList.add("block");
        // Store original data for validation
        blockDiv.dataset.index = block.index;
        blockDiv.dataset.hash = block.hash;
        blockDiv.dataset.previousHash = block.previous_hash;
        blockDiv.dataset.nonce = block.nonce;
        blockDiv.dataset.timestamp = block.timestamp;
        blockDiv.dataset.originalData = block.data;

        blockDiv.innerHTML = `
            <h3>Block #${block.index}</h3>
            <p><strong>Prev Hash:</strong> <span class="previous-hash">${block.previous_hash.slice(0, 8)}...</span></p>
            <input type="text" class="data" value="${block.data}">
            <p><strong>Nonce:</strong> ${block.nonce}</p>
            <p><strong>Hash:</strong> <span class="hash" data-full-hash="${block.hash}">${block.hash.slice(0, 8)}...</span></p>
        `;

        const dataInput = blockDiv.querySelector(".data");
        
        // Make sure input changes trigger validation
        dataInput.addEventListener("input", () => {
            validateBlockchain();
        });

        container.appendChild(blockDiv);
    });

    // Initial validation
    validateBlockchain();
}

async function mineBlock() {
    const blockDataInput = document.getElementById("blockData");
    if (!blockDataInput) {
        console.error("Block data input not found");
        return;
    }
    
    const blockData = blockDataInput.value.trim();
    if (!blockData) {
        alert("Please enter block data!");
        return;
    }

    try {
        const response = await fetch("/mine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data: blockData }),
        });
        
        if (response.ok) {
            blockDataInput.value = ""; // Clear input
            fetchChain(); // Refresh the chain
        } else {
            const errorData = await response.json();
            console.error("Mining failed:", errorData);
            alert("Mining failed: " + (errorData.error || "Unknown error"));
        }
    } catch (error) {
        console.error("Error mining block:", error);
        alert("Error mining block: " + error.message);
    }
}

async function validateBlockchain() {
    const blocks = document.querySelectorAll(".block");
    if (blocks.length === 0) return;
    
    // Always mark genesis block as valid
    blocks[0].classList.remove("invalid");
    blocks[0].classList.add("valid");
    
    let chainBroken = false;
    
    // For blocks beyond genesis, validate each one
    for (let i = 1; i < blocks.length; i++) {
        const currentBlock = blocks[i];
        const previousBlock = blocks[i-1];
        
        // If the chain is already broken, mark all subsequent blocks as invalid
        if (chainBroken) {
            currentBlock.classList.remove("valid");
            currentBlock.classList.add("invalid");
            continue;
        }
        
        // Get current values
        const currentData = currentBlock.querySelector(".data").value;
        const storedPrevHash = currentBlock.dataset.previousHash;
        const previousBlockHash = previousBlock.dataset.hash;
        
        // First check: Does this block point to the correct previous hash?
        // This should always be true unless the blockchain structure itself is broken
        const prevHashValid = storedPrevHash === previousBlockHash;
        
        // Second check: Has the data been tampered with?
        const dataChanged = currentData !== currentBlock.dataset.originalData;
        
        if (!prevHashValid || dataChanged) {
            // Mark as invalid
            currentBlock.classList.remove("valid");
            currentBlock.classList.add("invalid");
            chainBroken = true; // Break the chain for all subsequent blocks
        } else {
            // Mark as valid
            currentBlock.classList.remove("invalid");
            currentBlock.classList.add("valid");
        }
    }
}

async function fixBlockchain() {
    try {
        const response = await fetch("/fix_chain", { 
            method: "POST" 
        });
        
        if (response.ok) {
            console.log("Chain fixed successfully");
            fetchChain(); // Refresh the chain
        } else {
            const errorData = await response.json();
            console.error("Failed to fix chain:", errorData);
            alert("Failed to fix chain: " + (errorData.error || "Unknown error"));
        }
    } catch (error) {
        console.error("Error fixing chain:", error);
        alert("Error fixing chain: " + error.message);
    }
}

async function computeHash(index, timestamp, data, previousHash, nonce) {
    try {
        const response = await fetch("/compute_hash", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                index, 
                timestamp, 
                data, 
                previous_hash: previousHash, 
                nonce 
            }),
        });
        
        const result = await response.json();
        return result.hash;
    } catch (error) {
        console.error("Error computing hash:", error);
        return "";
    }
}