// Way A: OpenTrader's own strategy templates, strategy runner and backtest simulator (unchanged) on the price server.
// Copies the loop of packages/backtesting/src/backtesting.ts (nextCandle -> fulfillOrders -> start/process ->
// placeOrders), but candles arrive one at a time from price_server.py, and every fill its simulator makes is sent
// to the server, which keeps the real $1,000 account and charges 0.7% per side. Settings: see NOTES.md.
//   node_modules/.bin/tsx run_opentrader.ts grid|rsi <port>
import { spawn } from "node:child_process";
import { readFileSync, appendFileSync } from "node:fs";
import { createStrategyRunner } from "./downloads/opentrader/packages/bot-processor/src/index.ts";
import * as templates from "./downloads/opentrader/packages/bot-templates/src/templates/index.ts";
import { MarketSimulator } from "./downloads/opentrader/packages/backtesting/src/market-simulator.ts";
import { MemoryStore } from "./downloads/opentrader/packages/backtesting/src/store/memory-store.ts";
import { MemoryExchange } from "./downloads/opentrader/packages/backtesting/src/exchange/memory-exchange.ts";

const ROOT = "/home/user/Machine-";
const [, , which, portArg] = process.argv;
const port = Number(portArg);

const SETTINGS: Record<string, { settings: any; minutes: number }> = {
  grid: { settings: { highPrice: 1.762, lowPrice: 0.2864, gridLevels: 20, quantityPerGrid: 40.93 }, minutes: 1 },
  rsi: { settings: { high: 70, low: 30, periods: 14, persistence: 1, quantity: 818 }, minutes: 60 },
};
const cfg = SETTINGS[which];
const template: any = (templates as any)[which];

type Candle = { open: number; high: number; low: number; close: number; volume: number; timestamp: number };

function history(minutes: number, keep: number): Candle[] {
  // pre-Oct minutes only (data/PEARL-USDT_min1_before_oct.csv), grouped into `minutes`-long candles
  const rows = readFileSync(`${ROOT}/data/PEARL-USDT_min1_before_oct.csv`, "utf8").trim().split("\n").slice(1);
  const out: Candle[] = [];
  for (const r of rows) {
    const [t, o, h, l, c, v] = r.split(",");
    const ts = Date.parse(t);
    const start = ts - (ts % (minutes * 60000));
    const last = out[out.length - 1];
    if (last && last.timestamp === start) {
      last.high = Math.max(last.high, +h); last.low = Math.min(last.low, +l); last.close = +c; last.volume += +v;
    } else out.push({ open: +o, high: +h, low: +l, close: +c, volume: +v, timestamp: start });
  }
  return out.slice(-keep);
}

async function main() {
  const server = spawn("python3", ["price_server.py", "--port", String(port)], { cwd: ROOT, stdio: "ignore" });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 100; i++) {
    try { await fetch(`${base}/ping`); break; } catch { await new Promise((r) => setTimeout(r, 200)); }
  }
  const sim = new MarketSimulator();
  const store = new MemoryStore(sim);
  const exchange = new MemoryExchange(sim);
  const botConfig = { id: 0, symbol: "PEARL/USDT", exchangeCode: "OKX", settings: cfg.settings,
                      timeframe: cfg.minutes === 60 ? "1h" : "1m" };
  const runner = createStrategyRunner({ store, exchange, additionalExchanges: [], botConfig: botConfig as any,
                                        botTemplate: template });
  const botState: any = {};
  const candles: Candle[] = which === "rsi" ? history(60, 200) : [];
  const queue: Array<[string, number]> = [];
  const snap = () => sim.smartTrades.map((t: any) => [t.entryOrder?.status, t.tpOrder?.status]);
  const orders = (t: any) => [t.entryOrder, t.tpOrder];

  let account: any = null, prevClose: number | null = null, started = false, building: Candle | null = null;
  let sent = 0, skipped = 0;
  while (true) {
    let q = "/next?order=NONE";
    if (queue.length) { const [side, qty] = queue.shift()!; q = `/next?order=${side}&qty=${qty}`; sent++; }
    const m: any = await (await fetch(base + q)).json();
    if (m.done) { account = m.account; break; }
    const minuteMs = m.ts * 60000;
    const open = prevClose ?? m.close;
    prevClose = m.close;
    const start = minuteMs - (minuteMs % (cfg.minutes * 60000));
    if (!building || building.timestamp !== start) building = { open, high: m.high, low: m.low, close: m.close, volume: m.volume, timestamp: start };
    else { building.high = Math.max(building.high, m.high); building.low = Math.min(building.low, m.low); building.close = m.close; building.volume += m.volume; }
    if ((m.ts + 1) % cfg.minutes !== 0) continue;           // candle not closed yet
    const candle = { ...building };
    candles.push(candle);

    sim.nextCandle(candle as any);
    let before = snap();
    sim.fulfillOrders();
    sim.smartTrades.forEach((t: any, i: number) => orders(t).forEach((o: any, k: number) => {
      if (o && o.type === "Limit" && before[i]?.[k] === "Placed" && o.status === "Filled")
        queue.push([o.side === "Buy" ? "BUY" : "SELL", t.entryOrder.quantity]);
    }));
    if (!started) { await runner.start(botState); started = true; }
    else await runner.process(botState, undefined, { candle, candles } as any);
    before = snap();
    sim.placeOrders();
    sim.smartTrades.forEach((t: any, i: number) => orders(t).forEach((o: any, k: number) => {
      if (o && o.type === "Market" && before[i]?.[k] !== "Placed" && o.status === "Placed")
        queue.push([o.side === "Buy" ? "BUY" : "SELL", t.entryOrder.quantity]);
    }));
  }
  server.kill();
  const filled = account.trades.length;
  skipped = sent - filled;
  const line = { which, settings: cfg.settings, sent, filled, skipped, value: account.value, cash: account.cash,
                 coins: account.coins, holding: account.holding, first: account.trades.slice(0, 6), last: account.trades.slice(-4) };
  console.log(JSON.stringify(line, null, 1));
  appendFileSync(`${ROOT}/contest/grid_dca/work/ot/result_${which}.json`, JSON.stringify(line) + "\n");
}

main();
