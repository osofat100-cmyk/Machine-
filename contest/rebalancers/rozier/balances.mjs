// stand-in for balances.js (on-chain ERC20 balances): the price server's account
export async function getBalances(useCache = true) { const m = globalThis.FEED.m; return { PEARL: m.coins, USDC: m.cash }; }
export async function getTokenBalanceReal(symbol) { return (await getBalances())[symbol]; }
export async function hasEnoughBalance(symbol, amount) { return (await getBalances())[symbol] >= amount; }
export async function getGasBalance() { return 1; }
export async function hasEnoughGas() { return true; }
export function clearBalanceCache() {}
export function getWalletAddress() { return '0xstand-in'; }
