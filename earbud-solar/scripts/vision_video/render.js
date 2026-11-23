// Render the vision video: serves index.html + meshes + three.js locally, steps the timeline in headless
// Chromium (WebGL via SwiftShader) and pipes the frames to ffmpeg (H.264, yuv420p).
// Usage: node render.js <assets dir> <three.js package dir> <out.mp4> [fps=30]
//        node render.js <assets dir> <three dir> <out dir> --stills 0,3,6,9,11.5   (CLEAN=1: no captions)
const http = require("http"), fs = require("fs"), path = require("path"), { spawn } = require("child_process");
const { chromium } = require("playwright");

const [assets, three, out, a4, a5] = process.argv.slice(2);
const stills = a4 === "--stills" ? a5.split(",").map(Number) : null;
const fps = stills ? 0 : Number(a4 || 30);
const types = { ".html": "text/html", ".js": "text/javascript", ".glb": "model/gltf-binary", ".json": "application/json" };

const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  const f = u.startsWith("/assets/") ? path.join(assets, u.slice(8))
    : u.startsWith("/three/") ? path.join(three, u.slice(7))
    : path.join(__dirname, u === "/" ? "index.html" : u);
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" }); res.end(d);
  });
});

(async () => {
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("console", m => console.log("[page]", m.text()));
  page.on("pageerror", e => console.log("[page error]", e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(() => window.ready !== undefined);
  await page.evaluate(() => window.ready);
  await page.evaluate(() => document.fonts.ready);
  const T = await page.evaluate(() => window.T_END);

  if (stills) {
    fs.mkdirSync(out, { recursive: true });
    for (const t of stills) {
      await page.evaluate(t => window.renderAt(t), t);
      if (process.env.CLEAN) await page.evaluate(() => document.querySelectorAll(".cap").forEach(e => (e.style.display = "none")));
      await page.screenshot({ path: path.join(out, `still_${t.toFixed(1)}.png`) });
      console.log("still", t);
    }
  } else {
    const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
      "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
    const n = Math.round(T * fps), t0 = Date.now();
    for (let i = 0; i <= n; i++) {
      await page.evaluate(t => window.renderAt(t), i / fps);
      const buf = await page.screenshot({ type: "png" });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
      if (i % 30 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on("close", r));
    console.log("saved", out);
  }
  await browser.close(); server.close();
})();
