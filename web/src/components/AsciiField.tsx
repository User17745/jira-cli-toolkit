import { useEffect, useRef } from 'react'

const RAMP = '  ..::--==++**#'
const FONT_SIZE = 12
const LINE = 16

/**
 * A faint field of ASCII characters behind the page. Interfering waves drift slowly and
 * shift with scroll; the field itself scrolls at a third of the page speed. Each row is
 * one fillText call, so a frame costs about as many draw calls as there are rows.
 * Under reduced motion it draws once and ignores scroll.
 */
export function AsciiField() {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    let cols = 0
    let rows = 0
    let cell = 0
    let dirty = true
    let last = 0
    let raf = 0

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas!.width = Math.round(window.innerWidth * dpr)
      canvas!.height = Math.round(window.innerHeight * dpr)
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx!.font = `${FONT_SIZE}px 'Geist Mono Variable', ui-monospace, monospace`
      ctx!.textBaseline = 'top'
      cell = ctx!.measureText('M').width || 7.2
      cols = Math.ceil(window.innerWidth / cell) + 1
      rows = Math.ceil(window.innerHeight / LINE) + 2
      dirty = true
    }

    function draw(now: number) {
      const still = reduce.matches
      const scroll = still ? 0 : window.scrollY
      const t = still ? 0 : now / 9000
      // Rows scroll with the page at a third of its speed.
      const shift = (scroll / 3) % LINE
      const first = Math.floor(scroll / 3 / LINE)
      ctx!.clearRect(0, 0, window.innerWidth, window.innerHeight)
      ctx!.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--ascii') || 'rgb(0 0 0 / 7%)'
      for (let r = 0; r < rows; r++) {
        const y = first + r
        let line = ''
        for (let c = 0; c < cols; c++) {
          // Cells are about twice as tall as wide, so distances double the row index.
          const dx = c - cols * (0.3 + 0.1 * Math.sin(t))
          const dy = (y - first - rows * 0.35) * 2.1
          const v = Math.sin(c * 0.06 + t * 2.1 + scroll * 0.0011)
            + Math.sin(Math.hypot(dx, dy) * 0.075 - t * 2.6 - scroll * 0.004)
            + Math.sin(c * 0.035 - y * 0.11 + t + scroll * 0.0018)
          const n = Math.max(0, (v + 1.2) / 4.2)
          line += RAMP[Math.min(RAMP.length - 1, Math.floor(n * n * RAMP.length))]
        }
        ctx!.fillText(line, 0, r * LINE - shift)
      }
    }

    function frame(now: number) {
      raf = requestAnimationFrame(frame)
      if (document.hidden) return
      // About 15 frames a second for the drift; scroll redraws right away.
      if (!dirty && (reduce.matches || now - last < 66)) return
      draw(now)
      last = now
      dirty = false
    }

    const markDirty = () => { dirty = true }
    const theme = new MutationObserver(markDirty)
    theme.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    resize()
    window.addEventListener('resize', resize)
    window.addEventListener('scroll', markDirty, { passive: true })
    reduce.addEventListener('change', markDirty)
    document.fonts?.ready.then(resize)
    raf = requestAnimationFrame(frame)
    return () => {
      cancelAnimationFrame(raf)
      theme.disconnect()
      window.removeEventListener('resize', resize)
      window.removeEventListener('scroll', markDirty)
      reduce.removeEventListener('change', markDirty)
    }
  }, [])

  return <canvas ref={ref} className="ascii-field" aria-hidden="true" />
}
