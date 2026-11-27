// stand-in for node-cron: the harness fires the jobs on the simulated clock
export default {
  schedule(expr, fn) {
    const t = { expr, fn, active: true, stop() { this.active = false; }, start() { this.active = true; } };
    globalThis.CRON.push(t);
    return t;
  },
};
