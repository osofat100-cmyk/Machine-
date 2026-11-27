// Module-loader hook: inside 0xRozier's folder, its connection modules (and config.js) resolve to stand-ins here.
const MAP = {
  './balances.js': 'balances.mjs', './swap.js': 'swap.mjs', './notifier.js': 'notifier.mjs', './yield.js': 'yield.mjs',
  './telegram.js': 'telegram.mjs', './rpc_manager.js': 'rpc_manager.mjs', './config.js': 'config.mjs',
  './prices.js': 'prices.mjs', 'node-cron': 'cron.mjs',
};
export async function resolve(spec, ctx, next) {
  if (ctx.parentURL && ctx.parentURL.includes('0xRozier_rebalancing-bot') && MAP[spec]) {
    return { url: new URL(MAP[spec], import.meta.url).href, shortCircuit: true };
  }
  return next(spec, ctx);
}
