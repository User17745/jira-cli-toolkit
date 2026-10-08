import { useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent, type Ref } from 'react'
import { ChevronDown, RotateCcw, SquareTerminal } from 'lucide-react'
import { complete } from '@/sandbox/complete'
import { Session, type Block, type Result } from '@/sandbox/session'
import { intro, scenarios, type Scenario, type ScenarioId, type Step } from '@/sandbox/scenarios'
import './Terminal.css'

export type TerminalHandle = { run: (command: string) => void; play: (id: ScenarioId) => void }
// Entries without a command are parts of an agent session in a replay.
type Entry = { id: number; command?: string; result: Result; interrupted?: boolean; options?: string[]; running?: boolean }
type Replay = { skip: boolean; cancelled: boolean }
// A clicked command that is still typing, waiting for Enter, or running.
type Pending = { command: string; stage: 'typing' | 'typed' | 'running' }

const HINT = 'jira --help'
const TYPE_DELAY = 14
// Replay pacing: the request types fast, but each step pauses long enough to read what just happened.
const READ_PROMPT = 1200
const BEFORE_STEP = { message: 1600, tool: 1100 }
const RUNNING = { Bash: 1500, other: 1000 }
const BEFORE_ENTER = 600
const PREVIEW_LINES = 4
const PREVIEW_WIDTH = 120
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const wait = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))

const agent = (block: Block): Omit<Entry, 'id'> => ({ result: { blocks: [block], exit: null } })

/** The finished block for a step: `jira` runs in the sandbox unless the step fixes its output. */
function execute(session: Session, step: Step): Block {
  if ('say' in step) return { kind: 'say', text: step.say }
  if ('reply' in step) return { kind: 'reply', text: step.reply }
  if ('tool' in step) return { kind: 'tool', name: step.tool, input: step.file, output: [{ kind: 'text', stream: 'stdout', text: step.result }], exit: 0 }
  if (step.output !== undefined || !step.run.startsWith('jira '))
    return { kind: 'tool', name: 'Bash', input: step.run, output: step.output ? [{ kind: 'text', stream: (step.exit ?? 0) ? 'stderr' : 'stdout', text: step.output }] : [], exit: step.exit ?? 0 }
  const result = session.run(step.run)
  return { kind: 'tool', name: 'Bash', input: step.run, output: result.blocks, exit: result.exit ?? 0 }
}

function session(scenario: Scenario, run: Session): Omit<Entry, 'id'>[] {
  return [agent({ kind: 'session' }), agent({ kind: 'ask', text: scenario.prompt }), ...scenario.steps.map(step => agent(execute(run, step)))]
}

/** Long tool output shows its first lines, like an agent's transcript, and expands on request. */
function ToolOutput({ blocks }: { blocks: Block[] }) {
  return <>{blocks.map((block, i) => {
    if (block.kind !== 'text') return <Output key={i} block={block} />
    const tone = block.stream === 'stderr' ? 't-err' : 't-out'
    const lines = block.text.split('\n')
    const preview = lines.slice(0, PREVIEW_LINES).map(line => line.length > PREVIEW_WIDTH ? `${line.slice(0, PREVIEW_WIDTH)}…` : line)
    const hidden = lines.length - preview.length
    if (preview.join('\n') === block.text) return <pre key={i} className={tone}>{block.text}</pre>
    return <details key={i} className="t-more">
      <summary><pre className={`${tone} t-preview`}>{preview.join('\n')}</pre><span className="t-more-label">{hidden ? `… +${hidden} lines` : 'show all'}</span><span className="t-less-label">show less</span></summary>
      <pre className={tone}>{block.text}</pre>
    </details>
  })}</>
}

function Output({ block }: { block: Block }) {
  switch (block.kind) {
    case 'text':
      return block.stream === 'stderr'
        ? <pre className="t-err"><span className="sr-only">Standard error: </span>{block.text}</pre>
        : <pre className="t-out">{block.text}</pre>
    case 'table':
      return <div className="t-scroll" tabIndex={0} role="group" aria-label={block.title}>
        <table className="t-table" data-title={block.title}>
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
    case 'session':
      return <p className="t-session"><span className="t-session-name">✻ coding agent</span><span>replay · sample data · any agent that runs shell commands</span></p>
    case 'ask':
      return <p className="t-ask"><span className="t-ask-mark" aria-hidden="true">&gt;</span><span className="sr-only">You ask the agent: </span><span>{block.text}</span></p>
    case 'say':
    case 'reply':
      return <pre className={block.kind === 'say' ? 't-say' : 't-reply'}><span className="t-dot" aria-hidden="true">● </span><span className="sr-only">Agent: </span>{block.text}</pre>
    case 'tool':
      return <div className="t-tool" data-state={block.output === null ? 'running' : block.exit ? 'failed' : 'done'}>
        <p className="t-tool-call"><span className="t-dot" aria-hidden="true">● </span><span className="sr-only">Agent runs </span><strong>{block.name}</strong>({block.input}){block.exit ? <span className="t-tool-exit"> exit {block.exit}</span> : null}</p>
        <div className="t-tool-out"><span className="t-elbow" aria-hidden="true">⎿</span>
          <div className="min-w-0">{block.output === null ? <p className="t-dim t-running">Running…</p> : block.output.length ? <ToolOutput blocks={block.output} /> : <p className="t-dim">(no output)</p>}</div>
        </div>
      </div>
  }
}

function Prompt({ failed }: { failed?: boolean }) {
  return <span className="t-prompt" aria-hidden="true"><span className="t-path">~</span> <span data-failed={failed}>$</span> </span>
}

type Props = { ref?: Ref<TerminalHandle>; open: boolean; onOpenChange: (open: boolean) => void; onReplayChange?: (id: ScenarioId | undefined) => void }

export function Terminal({ ref, open, onOpenChange, onReplayChange }: Props) {
  const sandbox = useRef(new Session())
  const nextId = useRef(1)
  const [entries, setEntries] = useState<Entry[]>(() => [...session(intro, sandbox.current), agent({ kind: 'note', text: intro.after })].map((e, i) => ({ ...e, id: -1 - i })))
  const [input, setInput] = useState('')
  const [caret, setCaret] = useState(0)
  const [focused, setFocused] = useState(false)
  const [history, setHistory] = useState<string[]>(['jira issue list --open'])
  const [cursor, setCursor] = useState<number | null>(null)
  // After Escape, Tab moves focus out of the terminal instead of completing.
  const [released, setReleased] = useState(false)
  const [typing, setTyping] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const screenRef = useRef<HTMLDivElement>(null)
  const typingTimer = useRef<number | undefined>(undefined)
  const replay = useRef<Replay | null>(null)
  const pending = useRef<Pending | null>(null)
  const pendingTimer = useRef<number | undefined>(undefined)
  const [playing, setPlaying] = useState<ScenarioId>()

  const last = [...entries].reverse().find(e => e.result.exit !== null && !e.options)
  const failed = last ? last.result.exit !== 0 : false
  // Fish-style autosuggestion from history, accepted with → at the end of the line.
  const suggestion = input
    ? [...history].reverse().find(h => h.startsWith(input) && h !== input)?.slice(input.length) ?? ''
    : entries.length <= intro.steps.length + 3 && !playing ? HINT : ''

  function push(entry: Omit<Entry, 'id'>) {
    setEntries(list => [...list.slice(-39), { ...entry, id: nextId.current++ }])
  }

  function updateLast(block: Block) {
    setEntries(list => [...list.slice(0, -1), { ...list[list.length - 1], result: { blocks: [block], exit: null } }])
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
    if (line) remember(line)
    push({ command: line, result: sandbox.current.run(line) })
  }

  // A clicked command types out, waits a beat before Enter, then shows it running, at the replay's pace.
  function typeOut(command: string) {
    let i = 0
    pending.current = { command, stage: 'typing' }
    setTyping(true)
    setLine('')
    typingTimer.current = window.setInterval(() => {
      i += 2
      setLine(command.slice(0, i))
      if (i < command.length) return
      window.clearInterval(typingTimer.current)
      pending.current = { command, stage: 'typed' }
      pendingTimer.current = window.setTimeout(() => enter(command), BEFORE_ENTER)
    }, TYPE_DELAY)
  }

  function enter(command: string) {
    const line = command.trim()
    if (line === 'clear') { endPending(); run(line); return }
    setLine('')
    setCursor(null)
    remember(line)
    push({ command: line, result: { blocks: [], exit: null }, running: true })
    pending.current = { command, stage: 'running' }
    pendingTimer.current = window.setTimeout(() => finish(line), RUNNING.Bash)
  }

  function finish(line: string) {
    const result = sandbox.current.run(line)
    replaceLast({ result, running: false })
    endPending()
  }

  function replaceLast(entry: Partial<Entry>) {
    setEntries(list => [...list.slice(0, -1), { ...list[list.length - 1], ...entry }])
  }

  function endPending() {
    window.clearInterval(typingTimer.current)
    window.clearTimeout(pendingTimer.current)
    pending.current = null
    setTyping(false)
  }

  /** Jumps a clicked command straight to its output. */
  function skipPending() {
    const current = pending.current
    if (!current) return
    if (current.stage === 'running') { window.clearTimeout(pendingTimer.current); finish(current.command.trim()); return }
    endPending()
    run(current.command)
  }

  function remember(line: string) {
    setHistory(list => [...list.filter(h => h !== line), line].slice(-50))
  }

  function stopReplay() {
    if (replay.current) replay.current.cancelled = true
    replay.current = null
    setPlaying(undefined)
    onReplayChange?.(undefined)
  }

  // Types the request, then shows each tool call running before its result, unless the visitor skips ahead.
  // Each replay starts from fresh sample data, so its keys and IDs always match the script.
  async function play(id: ScenarioId) {
    skipPending()
    stopReplay()
    window.clearInterval(typingTimer.current)
    const scenario = scenarios[id]
    const state: Replay = { skip: reducedMotion(), cancelled: false }
    replay.current = state
    setPlaying(id)
    onReplayChange?.(id)
    setTyping(true)
    setLine('')
    sandbox.current.reset()
    push(agent({ kind: 'session' }))
    push(agent({ kind: 'ask', text: '' }))
    for (let i = 3; i < scenario.prompt.length && !state.skip; i += 3) {
      updateLast({ kind: 'ask', text: scenario.prompt.slice(0, i) })
      await wait(TYPE_DELAY)
      if (state.cancelled) return
    }
    updateLast({ kind: 'ask', text: scenario.prompt })
    if (!state.skip) await wait(READ_PROMPT)
    for (const step of scenario.steps) {
      if (!state.skip) await wait('say' in step || 'reply' in step ? BEFORE_STEP.message : BEFORE_STEP.tool)
      if (state.cancelled) return
      const block = execute(sandbox.current, step)
      if (block.kind === 'tool' && !state.skip) {
        push(agent({ ...block, output: null }))
        await wait(block.name === 'Bash' ? RUNNING.Bash : RUNNING.other)
        if (state.cancelled) return
        updateLast(block)
      } else push(agent(block))
    }
    push(agent({ kind: 'note', text: scenario.after }))
    if (replay.current !== state) return
    setTyping(false)
    stopReplay()
  }

  useImperativeHandle(ref, () => ({
    play(id) {
      onOpenChange(true)
      void play(id)
    },
    run(command) {
      onOpenChange(true)
      if (replay.current) { stopReplay(); setTyping(false) }
      skipPending()
      if (reducedMotion()) { run(command); return }
      typeOut(command)
    },
  }))

  useEffect(() => () => { window.clearInterval(typingTimer.current); window.clearTimeout(pendingTimer.current) }, [])

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
    if (replay.current) {
      // During a replay Ctrl+C stops it where it is; any other key skips to the end.
      // Modifiers alone don't count, or the Ctrl of Ctrl+C would skip before C arrives.
      if (event.key === 'Tab' || ['Control', 'Shift', 'Alt', 'Meta'].includes(event.key)) return
      event.preventDefault()
      if (event.ctrlKey && event.key === 'c') {
        stopReplay()
        setTyping(false)
        push({ command: input, result: { blocks: [], exit: 130 }, interrupted: true })
        setLine('')
      } else replay.current.skip = true
      return
    }
    if (pending.current) {
      // Like a replay: Ctrl+C stops the clicked command, any other key skips to its output.
      if (event.key === 'Tab' || ['Control', 'Shift', 'Alt', 'Meta'].includes(event.key)) return
      event.preventDefault()
      if (event.ctrlKey && event.key === 'c') {
        const running = pending.current.stage === 'running'
        endPending()
        if (running) replaceLast({ result: { blocks: [], exit: 130 }, interrupted: true, running: false })
        else push({ command: input, result: { blocks: [], exit: 130 }, interrupted: true })
        setLine('')
      } else skipPending()
      return
    }
    if (typing) { event.preventDefault(); return }
    if (event.key === 'Enter') { event.preventDefault(); run(input); return }
    if (event.key === 'Escape') { setReleased(true); return }
    if (event.key === 'ArrowRight' && suggestion && caret === input.length) { event.preventDefault(); setLine(input + suggestion); return }
    if (event.key === 'Tab' && !event.shiftKey && !released && input.trim()) {
      event.preventDefault()
      const result = complete(input, sandbox.current.issues.map(i => i.key))
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
    stopReplay()
    endPending()
    sandbox.current.reset()
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
            {entry.command !== undefined && <p className="t-cmd">
              {!!entry.result.exit && <span className="t-rprompt">exit {entry.result.exit}</span>}
              <Prompt failed={previous ? previous.result.exit !== 0 : false} />{entry.command}{entry.interrupted && <span className="t-dim">^C</span>}
            </p>}
            {entry.options && <p className="t-options">{entry.options.join('   ')}</p>}
            {entry.running && <p className="t-dim t-running">Running…</p>}
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
        {playing
          ? <p id="terminal-keys">agent replay <span>any key</span> skip <span>^C</span> stop</p>
          : typing
          ? <p id="terminal-keys">running <span>any key</span> skip <span>^C</span> stop</p>
          : <p id="terminal-keys"><span>tab</span> complete <span>↑</span> history <span>→</span> accept <span>^C</span> interrupt <span>esc</span> release</p>}
        {last && <p className="t-exit" data-failed={failed}>exit {last.result.exit}</p>}
      </div>
    </div>
  </section>
}
