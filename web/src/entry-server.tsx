import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
import App from './App.tsx'

// Rendered at build time into dist/index.html, so the first paint doesn't wait for the script.
export const render = () => renderToString(<StrictMode>
  <App />
</StrictMode>)
