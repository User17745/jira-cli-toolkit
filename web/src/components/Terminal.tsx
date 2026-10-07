import { useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent, type Ref } from 'react'
import { ChevronDown, RotateCcw, SquareTerminal } from 'lucide-react'
import { complete } from '@/sandbox/complete'
import { Session, type Block, type Result } from '@/sandbox/session'
import './Terminal.css'

export type TerminalHandle = { run: (command: string) => void }
type Entry = { id: number; command: string; result: Result; interrupted?: boolean; options?: string[] }

const FIRST = 'jira issue list --open'
const HINT = 'jira --help'
const TYPE_DELAY = 14

function Output({ block }: { block: Block }) {
  switch (block.kind) {
    case 'text':
      return block.stream === 'stderr'
        ? <pre className="t-err"><span className="sr-only">Standard error: </span>{block.text}</pre>
        : <pre className="t-out">{block.text}</pre>
    case 'table':
      return <div className="t-scroll" tabIndex={0} role="group" aria-label={block.title}>
        <table className="t-table">
          <caption>{block.title}</caption>
          <thead><tr>{block.columns.map(c => <th key={c} scope="col">{c}</th>)}</tr></thead>
          <tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} data-tone={cell.tone}>{cell.text}</td>)}</tr>)}</tbody>
        </table>
      </div>
    case 'panel':
      return <div className="t-panel">
        <span className="t-panel-title">{block.title}</span>
        <pre><strong>{block.heading[0]}</strong>: {block.heading[1]}{'\n'}{block.lines.join('\n')}</pre>
        <span className="t-panel-subtitle">{block.subtitle}</span>
      </div>
    case 'note':
      return <p className="t-note"># {block.text}</p>
  }
}

function Prompt({ failed }: { failed?: boolean }) {
  return <span className="t-prompt" aria-hidden="true"><span className="t-path">~</span> <span data-failed={failed}>$</span> </span>
}

export function Terminal({ ref, open, onOpenChange }: { ref?: Ref<TerminalHandle>; open: boolean; onOpenChange: (open: boolean) => void }) {
  const session = useRef(new Session())
  const nextId = useRef(1)
  const [entries, setEntries] = useState<Entry[]>(() => [{ id: 0, command: FIRST, result: session.current.run(FIRST) }])
  const [input, setInput] = useState('')
  const [caret, setCaret] = useState(0)
  const [focused, setFocused] = useState(false)
  const [history, setHistory] = useState<string[]>([FIRST])
  const [cursor, setCursor] = useState<number | null>(null)
  // After Escape, Tab moves focus out of the terminal instead of completing.
  const [released, setReleased] = useState(false)
  const [typing, setTyping] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const screenRef = useRef<HTMLDivElement>(null)
  const typingTimer = useRef<number | undefined>(undefined)

  const last = [...entries].reverse().find(e => e.result.exit !== null && !e.options)
  const failed = last ? last.result.exit !== 0 : false
  // Fish-style autosuggestion from history, accepted with → at the end of the line.
  const suggestion = input
    ? [...history].reverse().find(h => h.startsWith(input) && h !== input)?.slice(input.length) ?? ''
    : entries.length <= 1 ? HINT : ''

  function push(entry: Omit<Entry, 'id'>) {
    setEntries(list => [...list.slice(-39), { ...entry, id: nextId.current++ }])
  }

  function setLine(value: string) {
    setInput(value)
    setCaret(value.length)
  }

  function run(command: string) {
    const line = command.trim()
    setLine('')
    setCursor(null)
    if (line === 'clear') { setEntries([]); return }
    if (line) setHistory(list => [...list.filter(h => h !== line), line].slice(-50))
    push({ command: line, result: session.current.run(line) })
  }

  useImperativeHandle(ref, () => ({
    run(command) {
      onOpenChange(true)
      window.clearInterval(typingTimer.current)
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { run(command); return }
      // Type the command out so the click visibly becomes input, then press Enter.
      let i = 0
      setTyping(true)
      setLine('')
      typingTimer.current = window.setInterval(() => {
        i += 2
        setLine(command.slice(0, i))
        if (i >= command.length) {
          window.clearInterval(typingTimer.current)
          setTyping(false)
          run(command)
        }
      }, TYPE_DELAY)
    },
  }))

  useEffect(() => () => window.clearInterval(typingTimer.current), [])

  // Follow new output, but open at the top so the first command stays visible.
  const mounted = useRef(false)
  useEffect(() => {
    const screen = screenRef.current
    if (screen && mounted.current) screen.scrollTop = screen.scrollHeight
    mounted.current = true
  }, [entries, input])

  function syncCaret() {
    setCaret(inputRef.current?.selectionStart ?? input.length)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (typing) { event.preventDefault(); return }
    if (event.key === 'Enter') { event.preventDefault(); run(input); return }
    if (event.key === 'Escape') { setReleased(true); return }
    if (event.key === 'ArrowRight' && suggestion && caret === input.length) { event.preventDefault(); setLine(input + suggestion); return }
    if (event.key === 'Tab' && !event.shiftKey && !released && input.trim()) {
      event.preventDefault()
      const result = complete(input, session.current.issues.map(i => i.key))
      setLine(result.line)
      if (result.options.length) push({ command: result.line, result: { blocks: [], exit: null }, options: result.options })
      return
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      if (!history.length) return
      event.preventDefault()
      const up = event.key === 'ArrowUp'
      const index = cursor === null ? (up ? history.length - 1 : null) : Math.min(Math.max(cursor + (up ? -1 : 1), 0), history.length)
      if (index === null || index === history.length) { setCursor(null); setLine(''); return }
      setCursor(index)
      setLine(history[index])
      return
    }
    if (event.ctrlKey && event.key === 'c') {
      event.preventDefault()
      push({ command: input, result: { blocks: [], exit: 130 }, interrupted: true })
      setLine('')
      return
    }
    if (event.ctrlKey && event.key === 'l') { event.preventDefault(); setEntries([]) }
  }

  function reset() {
    window.clearInterval(typingTimer.current)
    setTyping(false)
    session.current.reset()
    setEntries([])
    setHistory([])
    setLine('')
    inputRef.current?.focus()
  }

  const before = input.slice(0, caret)
  const under = input.slice(caret, caret + 1)
  const after = input.slice(caret + 1)
  return <section className="terminal" data-open={open} aria-labelledby="terminal-title">
    <div className="t-bar">
      <span className="t-dots" aria-hidden="true"><i /><i /><i /></span>
      <h2 id="terminal-title" className="t-title">
        <button type="button" className="t-dock-toggle" onClick={() => onOpenChange(!open)} aria-expanded={open} aria-controls="terminal-body">
          <SquareTerminal aria-hidden="true" />
          <span>Sandbox terminal</span>
          <ChevronDown className="t-dock-chevron" aria-hidden="true" />
        </button>
        <span className="t-title-desktop">sandbox <span>— zsh — sample data</span></span>
      </h2>
      <button type="button" className="t-icon" onClick={reset} aria-label="Reset sandbox" title="Reset sandbox"><RotateCcw aria-hidden="true" /></button>
    </div>
    <div className="t-body" id="terminal-body">
      <div className="t-screen" ref={screenRef} onMouseUp={() => { if (!window.getSelection()?.toString()) inputRef.current?.focus() }}>
        <div role="log" aria-live="polite" aria-label="Sandbox output">{entries.map((entry, i) => {
          const previous = entries.slice(0, i).reverse().find(e => e.result.exit !== null && !e.options)
          return <div className="t-entry" key={entry.id}>
            <p className="t-cmd">
              {!!entry.result.exit && <span className="t-rprompt">exit {entry.result.exit}</span>}
              <Prompt failed={previous ? previous.result.exit !== 0 : false} />{entry.command}{entry.interrupted && <span className="t-dim">^C</span>}
            </p>
            {entry.options && <p className="t-options">{entry.options.join('   ')}</p>}
            {entry.result.blocks.map((block, j) => <Output key={j} block={block} />)}
          </div>
        })}</div>
        <div className="t-line" data-focused={focused}>
          <Prompt failed={failed} />
          <span className="t-input-wrap">
            <span className="t-mirror" aria-hidden="true">{before}<span className="t-caret">{under || (suggestion ? suggestion[0] : ' ')}</span>{under ? after : ''}{!under && suggestion && <span className="t-ghost">{suggestion.slice(1)}</span>}</span>
            <input id="terminal-input" ref={inputRef} value={input} aria-label="Sandbox command" aria-describedby="terminal-keys"
              autoComplete="off" autoCapitalize="off" autoCorrect="off" spellCheck={false} enterKeyHint="go"
              onChange={e => { setInput(e.target.value); setCaret(e.target.selectionStart ?? e.target.value.length); setReleased(false) }}
              onKeyDown={onKeyDown} onKeyUp={syncCaret} onSelect={syncCaret}
              onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} />
          </span>
        </div>
      </div>
      <div className="t-status">
        <p id="terminal-keys"><span>tab</span> complete <span>↑</span> history <span>→</span> accept <span>^C</span> interrupt <span>esc</span> release</p>
        {last && <p className="t-exit" data-failed={failed}>exit {last.result.exit}</p>}
      </div>
    </div>
  </section>
}
