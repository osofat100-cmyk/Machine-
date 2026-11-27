// Way B: Bitfox (GitHub benjamin-keil-crypto-worx/bitfox) strategies in Bitfox's own BackTest engine.
// The strategies are built around that engine (strategy.run(index) on precomputed causal indicators), so way A is
// not possible. Settings = examples/StrategyBenchmark.js (1h, profitPct 1.03, stopLossPct 0.98, amount 1000), except:
// sidePreference "long" (spot, no shorting), makerFee = takerFee = 0.007 and slippage 0 (the test's 0.7% per side
// already includes the spread). Candles: 1h from the history before 1 Oct + the sealed minutes walked from the price
// server; each strategy gets exactly its own warm-up candles before 1 Oct, so trading starts on 1 Oct.
const fs = require("fs");
const path = require("path");
const BF = path.join(__dirname, "downloads", "gh_bitfox");
const {BackTestEngine} = require(path.join(BF, "engine", "BackTest"));

const names = process.argv.slice(2).length ? process.argv.slice(2) :
    ["Phoenix", "SuperTrend", "RSITrend", "EmaTrend", "Bollinger", "MfiMacd", "SmartAccumulate", "ZemaCrossOver",
     "ThorsHammer", "DonchianTrend", "DynamicGrid", "MarketMaker", "MultiDivergence", "Regime", "SuperTrendFull"];

const rows = fs.readFileSync(path.join(__dirname, "data", "PEARL_USDT_1h.csv"), "utf8").trim().split("\n").slice(1);
const all = rows.map(r => { const [d, o, h, l, c, v] = r.split(","); return [Date.parse(d), +o, +h, +l, +c, +v]; });
const oct1 = Date.parse("2026-10-01T00:00:00Z");
const iOct = all.findIndex(c => c[0] >= oct1);
const lastClose = all[all.length - 1][4];
const FEE = 0.007;

function args() {
    return {symbol: "PEARLUSDT", timeframe: "1h", amount: 1000, profitPct: 1.03, stopLossPct: 0.98,
            sidePreference: "long", public: true, exchangeName: "bybit", makerFee: FEE, takerFee: FEE,
            slippage: 0, verbose: false};
}

(async () => {
    const out = [];
    for (const name of names) {
        try {
            const Cls = require(path.join(BF, "strategies", name))[name];
            // warm-up length = candles the strategy's indicators need (what adjustForDelay drops)
            const probe = Cls.init(args());
            const ind = (await probe.setup(all.map(c => [...c]))).getIndicator();
            const warm = Math.abs(all.length - ind.length);
            if (iOct - warm < 0) { out.push({name, error: `needs ${warm} warm-up hours, history has ${iOct}`}); continue; }
            const candles = all.slice(iOct - warm).map(c => [...c]);
            const a = args();
            const strat = Cls.init(a);
            const bt = BackTestEngine.getBackTester(strat, a);
            await bt.backTest(candles);
            const th = bt.tradeHistory || [];
            const done = th.filter(t => t.exitTimeStamp != null);
            const firstEntry = th.length ? th[0].entryTimestamp : null;
            let value = 1000;
            if (bt.metrics) value = 1000 * (1 + bt.metrics.totalReturnPct / 100);
            const open = th.filter(t => t.exitTimeStamp == null);
            if (open.length) {        // a position still open at the end: value it at the last close minus exit cost
                const t = open[open.length - 1];
                const cashBefore = done.length ? done[done.length - 1].funds : 1000;
                const cost = t.entryOrder.amount * t.entryOrder.price * (1 + FEE);
                value = cashBefore - cost + t.entryOrder.amount * lastClose * (1 - FEE);
            }
            // spot-realistic: same trades, each with the whole account, after fees (engine keeps a fixed coin amount)
            let spot = 1000;
            for (const t of done) {
                const r = (t.exitOrder.price * (1 - FEE)) / (t.entryOrder.price * (1 + FEE));
                spot *= r;
            }
            if (open.length) spot *= (lastClose * (1 - FEE)) / (open[open.length - 1].entryOrder.price * (1 + FEE));
            out.push({name, trades: th.length, completed: done.length, open: open.length, value, spot, warm, firstEntry,
                      returnPct: bt.metrics ? bt.metrics.totalReturnPct : 0});
        } catch (e) {
            out.push({name, error: `${e.name}: ${e.message}`.slice(0, 160)});
        }
    }
    fs.writeFileSync(path.join(__dirname, "bitfox_results.json"), JSON.stringify(out, null, 1));
    for (const r of out) console.log(JSON.stringify(r));
})();
