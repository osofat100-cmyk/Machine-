// stand-in for swap.js (1inch on Base): a market order on the price server, filled at the next minute's close
export async function executeSwap(fromAddr, toAddr, amountInUnits, fromSymbol, toSymbol, amountUSD, ethPrice) {
  const F = globalThis.FEED, p = F.m.close;
  const dec = fromSymbol === 'PEARL' ? 8 : 6;
  const amountToken = Number(amountInUnits) / 10 ** dec;
  const side = fromSymbol === 'PEARL' ? 'SELL' : 'BUY';
  let qty = side === 'SELL' ? amountToken : amountToken / p;
  qty = Math.floor(qty / 0.0001 + 1e-9) * 0.0001;
  if (qty * p < 2.0) throw new Error('below the 2 USDT minimum order');
  F.queue.push([side, qty]);
  F.decisions.push([F.m.time, side, qty, p, `${fromSymbol}->${toSymbol} $${amountUSD.toFixed(2)}`]);
  return { hash: 'stand-in', gasCost: 0, dryRun: false };
}
export async function estimateSwapCost() { return { gasCostUSD: 0 }; }
