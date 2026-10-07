// A port of the parts of Python's argparse.HelpFormatter that `jira` uses, at COLUMNS=80.
import { actions, isOpt, root, type Arg, type Node, type Opt, type Pos } from './tree.ts'

const WIDTH = 78
const MAX_HELP_POSITION = 24
const exclusive = new Set(root.exclusive.flat())

function metavarFor(arg: Arg) {
  if (arg.choices.length) return `{${arg.choices.join(',')}}`
  return isOpt(arg) ? arg.metavar : arg.metavar ?? arg.positional
}

function formatArgs(arg: Arg) {
  const m = metavarFor(arg)
  if (arg.nargs === '?') return `[${m}]`
  if (arg.nargs === '*') return `[${m} ...]`
  if (arg.nargs === '+') return `${m} [${m} ...]`
  return m
}

function subcommandChoices(node: Node, isRoot: boolean) {
  const names = (node.commands ?? []).map(c => c.name)
  return `{${[...names, ...(isRoot ? root.legacy.map(l => l.name) : [])].join(',')}}`
}

function usageParts(node: Node, isRoot: boolean) {
  const opts: string[] = []
  const pos: string[] = []
  const list = actions(node, isRoot)
  list.forEach((arg, i) => {
    if (!isOpt(arg)) { pos.push(formatArgs(arg)); return }
    const body = arg.takesValue ? `${arg.names[0]} ${formatArgs(arg)}` : arg.names[0]
    if (exclusive.has(arg.flag)) {
      const prev = list[i - 1]
      const first = !(prev && isOpt(prev) && exclusive.has(prev.flag))
      opts.push(...(first ? [`[${body}`, '|'] : [`${body}]`]))
    } else opts.push(arg.required ? body : `[${body}]`)
  })
  if (node.commands) pos.push(`${subcommandChoices(node, isRoot)} ...`)
  return { opts, pos }
}

function getLines(parts: string[], indent: string, prefix?: string) {
  const lines: string[] = []
  let line: string[] = []
  let len = prefix !== undefined ? prefix.length - 1 : indent.length - 1
  for (const part of parts) {
    if (len + 1 + part.length > WIDTH && line.length) {
      lines.push(indent + line.join(' '))
      line = []
      len = indent.length - 1
    }
    line.push(part)
    len += part.length + 1
  }
  if (line.length) lines.push(indent + line.join(' '))
  if (prefix !== undefined) lines[0] = lines[0].slice(indent.length)
  return lines
}

export function usage(prog: string, node: Node) {
  const isRoot = node === root
  const { opts, pos } = usageParts(node, isRoot)
  const prefix = 'usage: '
  const flat = [prog, ...opts, ...pos].join(' ')
  if (prefix.length + flat.length <= WIDTH) return prefix + flat
  const indent = ' '.repeat(prefix.length + prog.length + 1)
  const lines = getLines([prog, ...opts], indent, prefix)
  lines.push(...getLines(pos, indent))
  return prefix + lines.join('\n')
}

/** textwrap.wrap: break at whitespace, and after hyphens inside words. */
export function wrap(text: string, width: number) {
  const chunks = text.trim().split(/\s+/).flatMap(word =>
    word.split(/(?<=[A-Za-z]-)(?=[A-Za-z])/).map((part, i) => ({ part, glued: i > 0 })))
  const lines: string[] = []
  let line = ''
  for (const { part, glued } of chunks) {
    const joined = line ? line + (glued ? '' : ' ') + part : part
    if (joined.length > width && line) {
      lines.push(line)
      line = part
    } else line = joined
  }
  if (line) lines.push(line)
  return lines
}

function invocation(arg: Arg) {
  if (!isOpt(arg)) return metavarFor(arg as Pos)
  const names = arg.names.join(', ')
  return arg.takesValue ? `${names} ${formatArgs(arg)}` : names
}

function item(inv: string, help: string, indent: number, position: number) {
  const width = position - indent - 2
  const pad = ' '.repeat(indent)
  if (!help) return [pad + inv]
  const helpLines = wrap(help, WIDTH - position)
  const out = inv.length <= width
    ? [pad + inv.padEnd(width) + '  ' + helpLines[0], ...helpLines.slice(1).map(l => ' '.repeat(position) + l)]
    : [pad + inv, ...helpLines.map(l => ' '.repeat(position) + l)]
  return out
}

export function help(prog: string, node: Node) {
  const isRoot = node === root
  const list = actions(node, isRoot)
  const sections: string[] = [usage(prog, node)]
  if (node.description) sections.push(wrap(node.description, WIDTH).join('\n'))

  const rows: [string, string, number][] = [
    ...list.map(a => [invocation(a), a.help, 2] as [string, string, number]),
    ...(node.commands ? [
      [subcommandChoices(node, isRoot), '', 2] as [string, string, number],
      ...node.commands.map(c => [c.name, c.help, 4] as [string, string, number]),
      ...(isRoot ? root.legacy.map(l => [l.name, l.help, 4] as [string, string, number]) : []),
    ] : []),
  ]
  // argparse narrows the help column when every invocation is short.
  const position = Math.min(Math.max(...rows.map(([inv, , indent]) => inv.length + indent)) + 2, MAX_HELP_POSITION)
  const subcommands = rows.slice(list.length).flatMap(([inv, h, indent]) => item(inv, h, indent, position))
  const positionals = list.filter(a => !isOpt(a)).flatMap(a => item(invocation(a), a.help, 2, position))
  const options = list.filter(isOpt).flatMap((a: Opt) => item(invocation(a), a.help, 2, position))

  // Untitled subparsers join "positional arguments"; titled ones get their own group after options.
  const ownGroup = node.title !== 'positional arguments'
  if (node.commands && !ownGroup) positionals.push(...subcommands)
  if (positionals.length) sections.push(['positional arguments:', ...positionals].join('\n'))
  sections.push(['options:', ...options].join('\n'))
  if (node.commands && ownGroup) sections.push([`${node.title}:`, ...subcommands].join('\n'))
  if (isRoot) sections.push(wrap(root.epilog, WIDTH).join('\n'))
  return sections.join('\n\n')
}
