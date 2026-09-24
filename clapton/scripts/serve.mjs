// Minimal local static server for FILAMENT (no network access required).
// - Serves the clapton/ folder read-only.
// - Accepts POST /__upload?name=<file> (used only by the offline render CLI to
//   hand rendered float PCM from headless Chromium back to disk).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(__dirname, '..');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.css': 'text/css; charset=utf-8'
};

export function startServer({ port = 0, uploadDir = null, log = false } = {}) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'POST' && url.pathname === '/__upload') {
      if (!uploadDir) { res.writeHead(403); res.end('uploads disabled'); return; }
      const name = path.basename(url.searchParams.get('name') || 'upload.bin');
      const out = fs.createWriteStream(path.join(uploadDir, name));
      req.pipe(out);
      out.on('finish', () => { res.writeHead(200); res.end('ok'); });
      out.on('error', e => { res.writeHead(500); res.end(String(e)); });
      return;
    }
    if (url.pathname === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    let rel = decodeURIComponent(url.pathname);
    if (rel.endsWith('/')) rel += 'index.html';
    const file = path.resolve(ROOT, '.' + rel);
    if (!file.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); res.end('not found'); if (log) console.log('404', rel); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      res.end(data);
      if (log) console.log('200', rel);
    });
  });
  return new Promise(resolve => server.listen(port, '127.0.0.1', () => resolve({ server, port: server.address().port })));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.argv[2] || 8765);
  startServer({ port, log: true }).then(({ port }) => {
    console.log(`FILAMENT served at http://127.0.0.1:${port}/  (Ctrl+C to stop)`);
  });
}
