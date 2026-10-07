import { useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent, type Ref } from 'react'
import { complete } from '@/sandbox/complete'
import { Session, type Block, type Result } from '@/sandbox/session'

export type SandboxHandle = { run: (command: string) => void }
type Entry = { id: number; command: string; result: Result; interrupted?: boolean; options?: string[] }

const FIRST = 'jira issue list --open'
export const suggestions = [
  'jira issue view ENG-43',
  "jira issue transition ENG-43 --to 'In Progress'",
  'jira issue list --open --json --limit 1',
  'jira issue list --open --csv --columns key,status',
  'jira sprint list',
  'jira issue list --json --csv',
]

function Output({ block }: { block: Block }) {
  switch (block.kind) {
    case 'text':
      return block.stream === 'stderr'
        ? <pre className="term-err"><span className="sr-only">Standard error: </span>{block.text}</pre>
        : <pre className="term-out">{block.text}</pre>
    case 'table':
      return <div className="rich-scroll" tabIndex={0} role="group" aria-label={block.title}>
        <table className="rich-table">
          <caption>{block.title}</caption>
          <thead><tr>{block.columns.map(c => <th key={c} scope="col">{c}</th>)}</tr></thead>
          <tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} data-tone={cell.tone}>{cell.text}</td>)}</tr>)}</tbody>
        </table>
      </div>
    case 'panel':
      return <div className="rich-panel">
        <span className="rich-panel-title">{block.title}</span>
        <pre><strong>{block.heading[0]}</strong>: {block.heading[1]}{'\n'}{block.lines.join('\n')}</pre>
        <span className="rich-panel-subtitle">{block.subtitle}</span>
      </div>
    case 'note':
      return <p className="term-note"><strong>Sandbox:</strong> {block.text}</p>
  }
}

export function Sandbox({ ref }: { ref?: Ref<SandboxHandle> }) {
  const session = useRef(new Session())
  const nextId = useRef(1)
  const [entries, setEntries] = useState<Entry[]>(() => [{ id: 0, command: FIRST, result: session.current.run(FIRST) }])
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<string[]>([FIRST])
  const [cursor, setCursor] = useState<number | null>(null)
  // After Escape, Tab moves focus out of the terminal instead of completing.
  const [released, setReleased] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const logRef = useRef<HTMLDivElement>(null)

  function push(entry: Omit<Entry, 'id'>) {
    setEntries(list => [...list.slice(-39), { ...entry, id: nextId.current++ }])
  }

  function run(command: string) {
    const line = command.trim()
    setInput('')
    setCursor(null)
    if (line === 'clear') { setEntries([]); return }
    if (line) setHistory(list => [...list.filter(h => h !== line), line].slice(-50))
    push({ command: line, result: session.current.run(line) })
  }

  useImperativeHandle(ref, () => ({
    run(command) {
      run(command)
      inputRef.current?.focus({ preventScroll: true })
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      inputRef.current?.closest('.sandbox')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' })
    },
  }))

  // Follow new output, but open at the top so the first command stays visible.
  const mounted = useRef(false)
  useEffect(() => {
    const log = logRef.current
    if (log && mounted.current) log.scrollTop = log.scrollHeight
    mounted.current = true
  }, [entries])

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') { event.preventDefault(); run(input); return }
    if (event.key === 'Escape') { setReleased(true); return }
    if (event.key === 'Tab' && !event.shiftKey && !released && input.trim()) {
      event.preventDefault()
      const result = complete(input, session.current.issues.map(i => i.key))
      setInput(result.line)
      if (result.options.length) push({ command: result.line, result: { blocks: [], exit: null }, options: result.options })
      return
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      if (!history.length) return
      event.preventDefault()
      const up = event.key === 'ArrowUp'
      const index = cursor === null ? (up ? history.length - 1 : null) : Math.min(Math.max(cursor + (up ? -1 : 1), 0), history.length)
      if (index === null || index === history.length) { setCursor(null); setInput(''); return }
      setCursor(index)
      setInput(history[index])
      return
    }
    if (event.ctrlKey && event.key === 'c') {
      event.preventDefault()
      push({ command: input, result: { blocks: [], exit: 130 }, interrupted: true })
      setInput('')
      return
    }
    if (event.ctrlKey && event.key === 'l') { event.preventDefault(); setEntries([]) }
  }

  function reset() {
    session.current.reset()
    setEntries([])
    setHistory([])
    setInput('')
    inputRef.current?.focus()
  }

  return <section className="sandbox" id="sandbox" aria-labelledby="sandbox-title">
    <div className="sandbox-bar">
      <h2 id="sandbox-title">Sandbox</h2>
      <p className="example-label">Sample data on an example site. Nothing here reaches Jira.</p>
      <button type="button" className="sandbox-reset" onClick={reset}>Reset</button>
    </div>
    <div className="sandbox-screen" ref={logRef} onClick={e => { if (!window.getSelection()?.toString() && e.target === e.currentTarget) inputRef.current?.focus() }}>
      <div role="log" aria-live="polite" aria-label="Sandbox output">{entries.map(entry => <div className="term-entry" key={entry.id}>
        <p className="term-cmd"><span aria-hidden="true">$ </span>{entry.command}{entry.interrupted && <span className="term-ctrl">^C</span>}</p>
        {entry.options && <p className="term-options">{entry.options.join('   ')}</p>}
        {entry.result.blocks.map((block, i) => <Output key={i} block={block} />)}
        {entry.result.exit !== null && entry.command && <p className="term-exit" data-ok={entry.result.exit === 0}>exit {entry.result.exit}</p>}
      </div>)}</div>
      <div className="term-prompt">
        <label htmlFor="sandbox-input"><span aria-hidden="true">$</span><span className="sr-only">Sandbox command</span></label>
        <input id="sandbox-input" ref={inputRef} value={input} autoComplete="off" autoCapitalize="off" autoCorrect="off" spellCheck={false}
          aria-describedby="sandbox-keys" placeholder={entries.length > 1 ? '' : 'Type a command, such as jira --help'}
          onChange={e => { setInput(e.target.value); setReleased(false) }} onKeyDown={onKeyDown} />
      </div>
    </div>
    <div className="sandbox-foot">
      <p id="sandbox-keys">
        <kbd>Tab</kbd> completes, <kbd>↑</kbd> recalls, <kbd>Ctrl</kbd>+<kbd>C</kbd> interrupts, <kbd>Esc</kbd> then <kbd>Tab</kbd> leaves.
      </p>
    </div>
  </section>
}
