"""Zenbot 4.1.0 (docker image deviavir/zenbot:unstable; its lib/engine.js, sim exchange, commands/sim.js and
poloniex products.json are byte-identical to repo commit 52872fb), way B: Zenbot's own `sim` command.

Data: load_zenbot_trades.py (minutes from history + sealed export -> 4 trades a minute) in MongoDB.
Every shipped strategy runs with its own defaults and Zenbot's default conf (maker orders, buy/sell 99%).
Config: selector poloniex.PEARL-USDT, 1 Oct 00:00 - 21 Nov 00:00, 1,000 USDT and 0 PEARL,
cost 0.7% per side = the shipped poloniex maker fee 0.15% + --avg_slippage_pct 0.55 (sim option; in maker mode it
moves every fill price against us by 0.55%). Warm-up: sim itself loads min_periods of history before the start.
End value: USDT + PEARL left at the last close x (1 - 0.007), like the price server.

    venv_jesse/bin/python run_zenbot.py [strategy ...]
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sealed  # noqa: E402

IMAGE = "deviavir/zenbot:unstable"
LAST = 1.8278


def strategies():
    out = subprocess.run(["docker", "run", "--rm", "--entrypoint", "ls", IMAGE, "extensions/strategies"],
                         capture_output=True, text=True, check=True).stdout.split()
    return out


def run(name):
    cmd = ["docker", "run", "--rm", "--network", "zbnet", "-e", "ZENBOT_MONGODB_HOST=zbmongo", IMAGE, "sim",
           "poloniex.PEARL-USDT", "--strategy", name, "--start", "202610010000", "--end", "202611210000",
           "--currency_capital", "1000", "--asset_capital", "0", "--avg_slippage_pct", "0.55",
           "--filename", "none", "--silent"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired:
        return name, None, "cannot run here", "sim did not finish within 20 minutes"
    text = p.stdout
    start = text.rfind('{\n  "')
    try:
        while start >= 0:
            try:
                res = json.loads(text[start:text.rindex("}") + 1])
                break
            except json.JSONDecodeError:
                start = text.rfind('{\n  "', 0, start)
        sr = res["simresults"]
    except Exception:
        lines = (p.stderr + "\n" + p.stdout).strip().splitlines()
        hits = [l.strip() for l in lines if "rror" in l and "/app/" not in l]
        err = (hits[0] if hits else (lines[-1] if lines else "no output"))[:250]
        return name, None, "does not run as shipped", err
    # sim.js: simresults.currency = net_currency + close x asset (the whole account at the last close);
    # top-level net_currency = the USDT part. No trades -> nothing was spent.
    if int(sr["total_trades"]) == 0:
        cash, coins_value, end = 1000.0, 0.0, 1000.0
    else:
        total, cash = float(sr["currency"]), float(res["net_currency"])
        coins_value = total - cash
        end = cash + coins_value * (1 - 0.007)
    note = (f"Zenbot sim; {sr['total_trades']} trades ({sr['total_sells']} sells, {sr['total_losses']} losing); "
            f"end {cash:.2f} USDT + {coins_value:.2f} USDT of PEARL (less 0.7% exit cost); "
            f"Zenbot's own buy&hold {float(sr['buy_hold']):.2f}")
    return name, (int(sr["total_trades"]), end), "ran", note


def main():
    names = sys.argv[1:] or strategies()
    with ThreadPoolExecutor(1) as pool:
        for name, res, status, note in pool.map(run, names):
            trades, end = res if res else ("", None)
            print(f"{name:<20} {status:<24} trades {trades!s:>5}  end {'' if end is None else f'${end:,.2f}'}  "
                  f"{note}", flush=True)
            sealed.record("Zenbot 4.1.0", f"{name} (defaults)", "B", trades, end, status, note)


if __name__ == "__main__":
    main()
