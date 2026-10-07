// Typed view of commands.json, which scripts/command_tree.py generates from the real parser.
import data from '../data/commands.json' with { type: 'json' }

export type Nargs = string | number | null
export type Opt = {
  flag: string; names: string[]; takesValue: boolean; nargs: Nargs; metavar: string
  required: boolean; choices: string[]; repeat: boolean; type: string | null; help: string
}
export type Pos = { positional: string; metavar: string | null; nargs: Nargs; choices: string[]; type: string | null; help: string }
export type Arg = Opt | Pos
export type Node = {
  name: string; help: string; description: string | null; shared: boolean
  dest?: string; title?: string | null; commands?: Node[]; options?: Arg[]
}
type Root = Node & { version: string; epilog: string; legacy: { name: string; help: string }[]; globals: Opt[]; exclusive: string[][] }

export const root = data as unknown as Root
export const isOpt = (arg: Arg): arg is Opt => 'flag' in arg

// Root-only --version; argparse lists it after the shared options.
export const versionOpt: Opt = {
  flag: '--version', names: ['--version'], takesValue: false, nargs: 0, metavar: 'VERSION',
  required: false, choices: [], repeat: false, type: null, help: "show program's version number and exit",
}

export function child(node: Node, name: string) {
  return node.commands?.find(c => c.name === name)
}

/** Every action argparse knows about at this level, in declaration order. */
export function actions(node: Node, isRoot: boolean): Arg[] {
  const shared = node.shared ? root.globals : root.globals.filter(g => g.flag === '--help')
  return [...shared, ...(isRoot ? [versionOpt] : []), ...(node.options ?? [])]
}

export function leaves(node: Node = root, path: string[] = []): { path: string[]; node: Node }[] {
  return (node.commands ?? []).flatMap(c => c.commands ? leaves(c, [...path, c.name]) : [{ path: [...path, c.name], node: c }])
}
