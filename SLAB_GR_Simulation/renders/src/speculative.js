// STUB — to be implemented (see docs/viewer_architecture.md).
export class SpeculativeView {
  constructor(container, data, opts = {}) { this.container = container; this.data = data; this.opts = opts;
    this.el = document.createElement('div'); this.el.className = 'overlay'; this.el.textContent = 'speculative view: not implemented yet'; container.appendChild(this.el); }
  update(sample, state) {}
  resize() {}
  setMode(mode) {}
  dispose() {}
}
