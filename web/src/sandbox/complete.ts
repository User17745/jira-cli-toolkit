// Tab completion from the generated command tree, plus sample values for common arguments.
import { boards, projects, statuses } from './sample.ts'
import { actions, child, isOpt, root, type Node, type Opt, type Pos } from './tree.ts'

const quote = (value: string) => (/\s/.test(value) ? `'${value}'` : value)

function values(opt: Opt): string[] {
  if (opt.choices.length) return opt.choices
  switch (opt.flag) {
    case '--to': case '--status': return statuses.map(s => quote(s.name))
    case '--user': case '--assignee': return ['me']
    case '--board': return boards.map(b => String(b.id))
    case '--project': return projects.map(p => p.key)
    case '--profile': return ['work']
    default: return []
  }
}

function commonPrefix(items: string[]) {
  return items.reduce((prefix, item) => {
    let i = 0
    while (i < prefix.length && prefix[i] === item[i]) i++
    return prefix.slice(0, i)
  })
}

export function complete(line: string, keys: string[]): { line: string; options: string[] } {
  // Completion inside an open quote is left to the user.
  if ((line.match(/['"]/g) ?? []).length % 2) return { line, options: [] }
  const words = line.split(/\s+/)
  const partial = words.pop() ?? ''
  const done = words.filter(Boolean)

  let candidates: string[] = []
  if (!done.length) candidates = ['jira']
  else if (done[0] === 'jira') {
    let node: Node = root
    let pending: Opt | undefined
    let filled = 0
    const used = new Set<string>()
    for (const word of done.slice(1)) {
      const level = actions(node, node === root)
      if (pending) { pending = undefined; continue }
      if (word.startsWith('-')) {
        const opt = level.filter(isOpt).find(o => o.names.includes(word.split('=')[0]))
        if (opt) { used.add(opt.flag); if (opt.takesValue && !word.includes('=')) pending = opt }
        continue
      }
      const next = node.commands && child(node, word)
      if (next) node = next
      else filled++
    }
    const level = actions(node, node === root)
    if (pending) candidates = values(pending)
    else if (partial.startsWith('-')) {
      candidates = level.filter(isOpt).filter(o => o.repeat || !used.has(o.flag)).flatMap(o => o.names.filter(n => n.startsWith('--')))
    } else if (node.commands) candidates = node.commands.map(c => c.name)
    else {
      const slot = level.filter((a): a is Pos => !isOpt(a))[filled]
      if (slot?.choices.length) candidates = slot.choices
      else if (slot && /^keys?$/.test(slot.positional)) candidates = keys
    }
  }

  const matches = candidates.filter(c => c.startsWith(partial))
  const base = line.slice(0, line.length - partial.length)
  if (matches.length === 1) return { line: `${base}${matches[0]} `, options: [] }
  if (!matches.length) return { line, options: [] }
  return { line: base + commonPrefix(matches), options: matches }
}
