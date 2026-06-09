// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * End-to-end verification of the blockchain simulator in a real headless
 * browser. This drives the live Socket.IO mining round-trip: the page POSTs to
 * /mine, the Flask background thread mines a block and emits `block_mined` over
 * the WebSocket, and the front end renders a new block card. We assert the new
 * card actually appears and the stats update — proving the realtime path works
 * end to end, not just the HTTP API.
 */

test.describe('Blockchain simulator', () => {
  test('renders the terminal, genesis block, and the header brand', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/BlockChain Terminal/i);
    await expect(page.locator('.brand-name')).toContainText('BlockChain');

    // Genesis block card is rendered (id block-0) with a GENESIS badge.
    const genesis = page.locator('#block-0');
    await expect(genesis).toBeVisible();
    await expect(genesis.locator('.genesis-badge')).toHaveText('GENESIS');

    // Stats dashboard is populated (not the placeholder dash).
    await expect(page.locator('#stat-blocks-val')).not.toHaveText('—');
  });

  test('mining a block over the live WebSocket adds a block and updates stats', async ({ page }) => {
    await page.goto('/');

    // Wait for the chain to render (genesis at minimum).
    await expect(page.locator('#block-0')).toBeVisible();

    const blockCards = page.locator('.block-card');
    const initialCount = await blockCards.count();

    const blocksStat = page.locator('#stat-blocks-val');
    const initialBlocks = parseInt((await blocksStat.textContent()) || '0', 10);

    // Broadcast a transaction so the next block carries it (exercises the
    // /add_transaction + mempool path through the UI).
    await page.fill('#tx-sender', '0xPlaywrightSender0000000000000000000001');
    await page.fill('#tx-recipient', '0xPlaywrightRecipient00000000000000000002');
    await page.fill('#tx-amount', '4.2');
    await page.click('#btn-add-tx');
    await expect(page.locator('#tx-feedback')).toContainText(/TX broadcast/i);

    // Kick off mining. The new block only appears via the Socket.IO
    // `block_mined` event, so a growing card count proves the WS round-trip.
    await page.click('#btn-mine');

    await expect(blockCards).toHaveCount(initialCount + 1, { timeout: 30000 });

    // The newest block card (rendered first) should not be the genesis block.
    const newest = blockCards.first();
    await expect(newest).not.toHaveClass(/genesis/);
    await expect(newest.locator('.block-index')).not.toHaveText('#0');

    // Stats update through the live socket flow.
    await expect
      .poll(async () => parseInt((await blocksStat.textContent()) || '0', 10), {
        timeout: 30000,
      })
      .toBeGreaterThan(initialBlocks);

    // Chain length badge reflects the new height.
    await expect(page.locator('#chain-length-badge')).toContainText(
      `${initialCount + 1} blocks`
    );
  });
});
