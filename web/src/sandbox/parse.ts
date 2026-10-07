// Mirrors how argparse resolves `jira` arguments, including its error messages and exit code 2.
import { help, usage } from './help.ts'
import { actions, child, isOpt, root, type Node, type Opt, type Pos } from './tree.ts'

export type Values = Record<string, string | string[] | boolean | undefined>
export type Parsed =
  | { kind: 'run'; path: string[]; node: Node; opts: Values; args: Values; legacy?: string }
  | { kind: 'group'; path: string[]; node: Node }
  | { kind: 'help'; text: string }
  | { kind: 'version' }
  | { kind: 'error'; text: string }

export function tokenize(line: string): string[] | { error: string } {
  const tokens: string[] = []
  let current = ''
  let quote = ''
  let started = false
  for (const ch of line) {
    if (quote) {
      if (ch === quote) quote = ''
      else current += ch
    } else if (ch === '"' || ch === "'") { quote = ch; started = true }
    else if (/\s/.test(ch)) {
      if (started) tokens.push(current)
      current = ''
      started = false
    } else { current += ch; started = true }
  }
  if (quote) return { error: `unmatched ${quote}` }
  if (started) tokens.push(current)
  return tokens
}

const looksLikeOption = (token: string) => token.startsWith('-') && token !== '-' && !/^-\d/.test(token)
const display = (arg: Opt | Pos) => isOpt(arg) ? arg.names.join('/') : arg.metavar ?? arg.positional
const quoteList = (items: string[]) => items.map(i => `'${i}'`).join(', ')

class ArgError extends Error {
  prog: string
  node: Node
  constructor(prog: string, node: Node, message: string) {
    super(message)
    this.prog = prog
    this.node = node
  }
}

function convert(prog: string, node: Node, arg: Opt | Pos, value: string) {
  if (arg.choices.length && !arg.choices.includes(value))
    throw new ArgError(prog, node, `argument ${display(arg)}: invalid choice: '${value}' (choose from ${quoteList(arg.choices)})`)
  if (arg.type === 'positive_int' || arg.type === 'int') {
    if (!/^\s*[+-]?\d+\s*$/.test(value)) throw new ArgError(prog, node, `argument ${display(arg)}: invalid ${arg.type} value: '${value}'`)
    if (arg.type === 'positive_int' && Number(value) <= 0) throw new ArgError(prog, node, `argument ${display(arg)}: must be greater than zero`)
  }
  return value
}

function resolveOption(prog: string, node: Node, opts: Opt[], token: string): [Opt | undefined, string | undefined] {
  const [name, inline] = token.startsWith('--') && token.includes('=') ? [token.slice(0, token.indexOf('=')), token.slice(token.indexOf('=') + 1)] : [token, undefined]
  const exact = opts.find(o => o.names.includes(name))
  if (exact) return [exact, inline]
  if (!name.startsWith('--')) {
    // Short options accept attached values, such as -pENG.
    const short = opts.find(o => o.takesValue && o.names.includes(name.slice(0, 2)))
    return short ? [short, name.slice(2)] : [undefined, undefined]
  }
  const matches = opts.flatMap(o => o.names.filter(n => n.startsWith('--') && n.startsWith(name)).map(n => [o, n] as const))
  if (matches.length > 1) throw new ArgError(prog, node, `ambiguous option: ${name} could match ${matches.map(m => m[1]).join(', ')}`)
  return [matches[0]?.[0], inline]
}

function errorText(error: ArgError) {
  return `${usage(error.prog, error.node)}\n${error.prog}: error: ${error.message}`
}

export function parse(argv: string[]): Parsed {
  const path: string[] = []
  const opts: Values = {}
  const args: Values = {}
  const extras: string[] = []
  let node: Node = root
  let legacy: string | undefined
  let seen = new Set<string>()
  let filled = 0
  const prog = () => ['jira', ...path].join(' ')
  try {
    for (let i = 0; i < argv.length; i++) {
      const token = argv[i]
      const level = actions(node, node === root)
      const options = level.filter(isOpt)
      if (token === '--') { extras.push(...argv.slice(i + 1)); break }
      if (looksLikeOption(token)) {
        const [opt, inline] = resolveOption(prog(), node, options, token)
        if (!opt) { extras.push(token); continue }
        if (opt.flag === '--help') return { kind: 'help', text: help(prog(), node) }
        if (opt.flag === '--version') return { kind: 'version' }
        const rival = root.exclusive.find(group => group.includes(opt.flag))?.find(f => f !== opt.flag && seen.has(f))
        if (rival) throw new ArgError(prog(), node, `argument ${opt.names.join('/')}: not allowed with argument ${rival}`)
        seen.add(opt.flag)
        const key = opt.flag.replace(/^-+/, '')
        if (!opt.takesValue) { opts[key] = true; continue }
        const values: string[] = []
        if (inline !== undefined) values.push(inline)
        else {
          const many = opt.nargs === '+' || opt.nargs === '*'
          while (i + 1 < argv.length && !looksLikeOption(argv[i + 1]) && (many || !values.length)) values.push(argv[++i])
        }
        if (!values.length && opt.nargs !== '*') throw new ArgError(prog(), node, `argument ${opt.names.join('/')}: expected ${opt.nargs === '+' ? 'at least one argument' : 'one argument'}`)
        values.forEach(v => convert(prog(), node, opt, v))
        opts[key] = opt.repeat ? [...((opts[key] as string[]) ?? []), ...values] : opt.nargs === '+' || opt.nargs === '*' ? values : values[0]
        continue
      }
      if (node.commands && path.length === 0 && root.legacy.some(l => l.name === token)) { legacy = token; path.push(token); node = { name: token, help: '', description: null, shared: true }; continue }
      if (node.commands) {
        const next = child(node, token)
        if (!next) {
          const names = [...node.commands.map(c => c.name), ...(node === root ? root.legacy.map(l => l.name) : [])]
          throw new ArgError(prog(), node, `argument ${node.dest}: invalid choice: '${token}' (choose from ${quoteList(names)})`)
        }
        path.push(token)
        node = next
        // Each subparser starts with fresh mutually exclusive bookkeeping.
        seen = new Set()
        continue
      }
      const positionals = level.filter((a): a is Pos => !isOpt(a))
      // A '+' or '*' positional absorbs every remaining positional token.
      const slot = positionals[filled]
      if (!slot) { extras.push(token); continue }
      convert(prog(), node, slot, token)
      if (slot.nargs === '+' || slot.nargs === '*') args[slot.positional] = [...((args[slot.positional] as string[]) ?? []), token]
      else { args[slot.positional] = token; filled++ }
    }
    if (legacy) return { kind: 'run', path, node, opts, args, legacy }
    if (node.commands) return { kind: 'group', path, node }
    const missing = actions(node, false).filter(a =>
      isOpt(a) ? a.required && opts[a.flag.replace(/^-+/, '')] === undefined
        : (a.nargs === null || a.nargs === '+') && args[a.positional] === undefined)
    if (missing.length) throw new ArgError(prog(), node, `the following arguments are required: ${missing.map(display).join(', ')}`)
    if (extras.length) throw new ArgError('jira', root, `unrecognized arguments: ${extras.join(' ')}`)
    return { kind: 'run', path, node, opts, args }
  } catch (error) {
    if (error instanceof ArgError) return { kind: 'error', text: errorText(error) }
    throw error
  }
}
