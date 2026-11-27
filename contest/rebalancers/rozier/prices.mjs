// stand-in for prices.js (CoinGecko): the minute's close. getDynamicThreshold is only logged by rebalance.js.
export async function getPrices() { return { PEARL: globalThis.FEED.m.close, USDC: 1 }; }
export function getPriceHistory() { return []; }
export function calculateVolatility() { return 0; }
export function getDynamicThreshold(baseThreshold = 0.02) { return baseThreshold; }
export function clearPriceCache() {}
