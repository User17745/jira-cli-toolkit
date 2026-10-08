import path from "node:path"
import { defineConfig, type Plugin } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

// Preload the Latin Geist faces so text renders in them first time. With `optional` display, a face that
// misses the first paint isn't swapped in later, so it can never shift the layout; the next visit has it cached.
function preloadFonts(): Plugin {
  let base = "/"
  return {
    name: "preload-fonts",
    apply: "build",
    configResolved(config) { base = config.base },
    generateBundle(_options, bundle) {
      for (const file of Object.values(bundle))
        if (file.type === "asset" && file.fileName.endsWith(".css")) file.source = String(file.source).replaceAll("font-display:swap", "font-display:optional")
    },
    transformIndexHtml: {
      order: "post",
      // The page is prerendered, so its script only adds interactivity; fetch it after the styles and fonts.
      handler: (html, { bundle }) => ({ html: html.replace('<script type="module" crossorigin', '<script type="module" fetchpriority="low" crossorigin'), tags: Object.keys(bundle ?? {})
        .filter(file => /\/geist(-mono)?-latin-wght-normal-[\w-]+\.woff2$/.test(file))
        .map(file => ({ tag: "link", injectTo: "head", attrs: { rel: "preload", href: base + file, as: "font", type: "font/woff2", crossorigin: "" } })) }),
    },
  }
}

export default defineConfig({
  // Vercel serves the site at the domain root; the GitHub Pages copy sets BASE_PATH=/jira-cli-toolkit/.
  base: process.env.BASE_PATH || "/",
  plugins: [react(), tailwindcss(), preloadFonts()],  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
})
