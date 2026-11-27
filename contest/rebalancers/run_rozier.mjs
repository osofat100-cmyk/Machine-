// 0xRozier/rebalancing-bot: index.js runs unchanged (initialize, first runRebalancing, cron jobs every 2 h and
// emergency check every 20 min, its error handling and 3-errors-then-exit rule), with rebalance.js, breaker.js,
// pnl.js, utils.js unchanged. Its connection modules and config.js resolve to stand-ins (rozier/hooks.mjs).
// Clock: Date.now is the test's minute; its setTimeout pauses (5 min RPC retry, 3-5 s waits) are shortened.
// Swaps fill at the next minute's close. Start: 'cash' = 0 PEARL / 1000 USDC; 'split' = 20% bought by hand first.
//     node run_rozier.mjs cash 8841
import { register } from 'node:module';
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const START = process.argv[2] || 'cash';
const PORT = parseInt(process.argv[3] || '8841');
register('./rozier/hooks.mjs', import.meta.url);

process.env.PRIVATE_KEY = '0x' + '1'.repeat(64);   // dummy: only validateEnv reads it; no wallet is used
process.env.RPC_URL = 'http://stand-in';
process.env.ONEINCH_API_KEY = 'stand-in';

const server = spawn('python3', [path.join(ROOT, 'price_server.py'), '--port', String(PORT)], { cwd: ROOT, stdio: 'ignore' });
const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
function next(order = 'NONE', qty = null) {
  const q = `/next?order=${order}` + (qty !== null ? `&qty=${qty}` : '');
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port: PORT, path: q, agent }, res => {
      let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b)));
    }).on('error', reject);
  });
}
const realSetTimeout = global.setTimeout;
let m = null;
for (let i = 0; i < 200 && m === null; i++) {
  try { m = await next(); } catch { await new Promise(r => realSetTimeout(r, 200)); }
}
const FEED = { m, queue: [], decisions: [] };
globalThis.FEED = FEED; globalThis.CRON = [];
if (START === 'split') {
  const q = Math.floor(200 / (m.close * 1.007) / 0.0001) * 0.0001;
  FEED.decisions.push([m.time, 'BUY', q, m.close, "user's own first 20% buy, not the program"]);
  FEED.m = m = await next('BUY', q);
}
Date.now = () => FEED.m.ts * 60000;
global.setTimeout = (fn, ms, ...a) => realSetTimeout(fn, Math.min(ms, 1), ...a);
let stopped = null;
process.exit = (code) => { stopped = stopped || `process.exit(${code}) at ${FEED.m.time}`; };
const box = path.join(HERE, `home_rozier_${START}`);
fs.mkdirSync(box, { recursive: true });
process.chdir(box);
const logs = [];
console.log = (...a) => { logs.push(a.join(' ')); };
console.error = (...a) => { logs.push('ERR ' + a.join(' ')); };
console.warn = (...a) => { logs.push('WARN ' + a.join(' ')); };

await import(pathToFileURL(path.join(HERE, 'downloads', '0xRozier_rebalancing-bot', 'index.js')).href);
for (let i = 0; i < 2000 && globalThis.CRON.length < 2 && !stopped; i++) await new Promise(r => realSetTimeout(r, 5));

let runs = 0;
while (true) {
  const o = FEED.queue.shift();
  const r = o ? await next(o[0], o[1]) : await next();
  if (r.done) { FEED.account = r.account; break; }
  FEED.m = r;
  if (stopped) continue;
  const minute = r.ts % 60, hour = Math.floor(r.ts / 60) % 24;
  const due = globalThis.CRON.filter(t => t.active && (
    (t.expr === '0 */2 * * *' && minute === 0 && hour % 2 === 0) || (t.expr === '*/20 * * * *' && minute % 20 === 0)));
  if (due.length) { runs++; await Promise.all(due.map(t => t.fn())); }
}
server.kill();
const a = FEED.account;
fs.writeFileSync(path.join(HERE, `log_rozier_${START}.json`), JSON.stringify({ stopped, decisions: FEED.decisions, account: a, lastLogs: logs.slice(-60) }, null, 1));
fs.writeSync(2, `0xRozier [${START}]: $1,000 -> $${a.value.toFixed(2)} after ${a.trades.length} fills, ${runs} cron ticks, stopped=${stopped}\n`);
realSetTimeout(() => process.reallyExit(0), 10);
