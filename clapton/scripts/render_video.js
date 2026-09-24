#!/usr/bin/env node
// Phase-4 entry point (name required by the production directive). The implementation lives in
// ../render.mjs (the name required by the acceptance spec); this forwards all arguments to it.
//   node scripts/render_video.js [--workers N] [--frames a:b --out file.mp4]
'use strict';
const path = require('node:path');
const { pathToFileURL } = require('node:url');
import(pathToFileURL(path.join(__dirname, '..', 'render.mjs')).href).catch(e => { console.error(e); process.exit(1); });
