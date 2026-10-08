// Renders the page into dist/index.html after `vite build --ssr`, then removes the server bundle.
import { readFile, rm, writeFile } from 'node:fs/promises'

const server = new URL('../dist-ssr/', import.meta.url)
const page = new URL('../dist/index.html', import.meta.url)
const { render } = await import(new URL('entry-server.js', server).href)
const html = await readFile(page, 'utf8')
const empty = '<div id="root"></div>'
if (!html.includes(empty)) throw new Error('dist/index.html has no empty #root to prerender into')
await writeFile(page, html.replace(empty, `<div id="root">${render()}</div>`))
await rm(server, { recursive: true, force: true })
