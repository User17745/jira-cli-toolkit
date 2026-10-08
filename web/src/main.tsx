import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const root = document.getElementById('root')!
const app = <StrictMode>
  <App />
</StrictMode>

// Builds prerender the page into #root (see scripts/prerender.mjs); the dev server starts empty.
// Hydrate after the next frame, so the prerendered page paints first even when the script is cached.
if (root.firstElementChild) requestAnimationFrame(() => setTimeout(() => hydrateRoot(root, app)))
else createRoot(root).render(app)
