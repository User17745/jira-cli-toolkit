import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

// index.html applies the stored or system theme before first paint; this keeps it in sync afterwards.
export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const follow = () => { if (!localStorage.getItem('theme')) apply(media.matches) }
    media.addEventListener('change', follow)
    return () => media.removeEventListener('change', follow)
  }, [])

  function apply(next: boolean) {
    document.documentElement.classList.toggle('dark', next)
    setDark(next)
  }

  function toggle() {
    apply(!dark)
    try { localStorage.setItem('theme', dark ? 'light' : 'dark') } catch { /* private mode: keep the choice for this visit */ }
  }

  return <button type="button" onClick={toggle} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'} title={dark ? 'Light theme' : 'Dark theme'}
    className="grid size-8 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
    {dark ? <Sun className="size-4" aria-hidden="true" /> : <Moon className="size-4" aria-hidden="true" />}
  </button>
}
