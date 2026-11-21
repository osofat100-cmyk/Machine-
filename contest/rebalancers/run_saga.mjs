// Saga-Labs/rebalancer rebalance-bot.js, unchanged: RebalanceBot.calculateWeights + RebalanceBot.rebalance decide.
// Its constructor needs a wallet key and a Base RPC, so the object is built from its prototype with the same field
// values the constructor sets (deviation 0.05 and min trade $5 defaults, slippage 0.005, check every 4 h hard-coded,
// baseToken 'WETH'), and the loop body of start() runs every 4 h: getBalances, getPrices, calculateWeights, rebalance.
// Stand-ins (its chain/price connections): getBalances, getPrices, swap - backed by the price server.
// The hub token is WETH in the code; here WETH stands for USDT (price 1). CUSTOM_WEIGHTS = {"PEARL":0.2,"WETH":0.8}.
// Swaps are market-like (CoW); they fill at the next minute's close. Orders under 2 USDT are refused.
//     node run_saga.mjs 8840
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const PORT = parseInt(process.argv[2] || '8840');
const { RebalanceBot } = await import(path.join(HERE, 'downloads', 'Saga-Labs_rebalancer', 'rebalance-bot.js'));

const server = spawn('python3', [path.join(ROOT, 'price_server.py'), '--port', String(PORT)], { cwd: ROOT, stdio: 'ignore' });
process.on('exit', () => server.kill());
const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
function next(order = 'NONE', qty = null) {
  const q = `/next?order=${order}` + (qty !== null ? `&qty=${qty}` : '');
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port: PORT, path: q, agent }, res => {
      let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b)));
    }).on('error', reject);
  });
}
let m = null;
for (let i = 0; i < 200 && m === null; i++) {
  try { m = await next(); } catch { await new Promise(r => setTimeout(r, 200)); }
}
const queue = [], decisions = [];
const bot = Object.create(RebalanceBot.prototype);
Object.assign(bot, {
  weights: JSON.parse('{"PEARL": 0.2, "WETH": 0.8}'), deviationThreshold: 0.05, minTradeUSD: 5.0,
  slippagePercent: 0.005, checkInterval: 4 * 60 * 60 * 1000, baseToken: 'WETH',
  logFile: path.join(HERE, 'log_saga_bot.txt'), bot: null, chatIds: [], lastKnownPrices: {},
  initialBalances: { PEARL: 0, WETH: 1000 }, startDate: m.time, dataFile: path.join(HERE, 'saga-data.json'),
  tokens: { PEARL: 'stand-in', WETH: 'stand-in' },
  priceCache: { prices: {}, timestamp: 0, maxAge: 5 * 60 * 1000 },
});
fs.writeFileSync(bot.logFile, '');
bot.getBalances = async () => ({ PEARL: m.coins, WETH: m.cash });
bot.getPrices = async () => ({ PEARL: m.close, WETH: 1 });
bot.swap = async (fromToken, toToken, amount) => {
  if (fromToken === toToken) return false;   // its own first check in swap()
  const side = fromToken === 'WETH' ? 'BUY' : 'SELL';
  let qty = side === 'BUY' ? amount / m.close : amount;
  qty = Math.floor(qty / 0.0001 + 1e-9) * 0.0001;
  if (qty * m.close < 2.0) return false;
  queue.push([side, qty]); decisions.push([m.time, side, qty, m.close]);
  return true;
};
const realSetTimeout = global.setTimeout;
global.setTimeout = (fn, ms, ...a) => realSetTimeout(fn, Math.min(ms, 1), ...a);   // its 2 s pauses between swaps

const start = m.ts;
let runs = 0, done = null;
while (true) {
  if ((m.ts - start) % 240 === 0 && queue.length === 0) {
    runs++;
    const balances = await bot.getBalances();
    const prices = await bot.getPrices();
    const w = await bot.calculateWeights(balances, prices);
    await bot.rebalance(w, balances, prices);
  }
  const o = queue.shift();
  const r = o ? await next(o[0], o[1]) : await next();
  if (r.done) { done = r.account; break; }
  m = r;
}
server.kill();
const acct = done;
console.error(`Saga-Labs/rebalancer: $1,000 -> $${acct.value.toFixed(2)} after ${acct.trades.length} fills, ${runs} checks (holding $${acct.holding.toFixed(2)})`);
fs.writeFileSync(path.join(HERE, 'log_saga.json'), JSON.stringify({ decisions, account: acct }, null, 1));
process.exit(0);
