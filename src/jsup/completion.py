"""Shell completions from the actual parser and local profile preferences only."""
import argparse
import shlex
from .commands import build_parser
from . import config


def candidates(words,prog='jira'):
    prefix=words[-1] if words else ''
    previous=words[:-1]
    parser=build_parser(prog)
    awaiting=None
    for word in previous:
        if awaiting:
            awaiting=None; continue
        action=next((a for a in parser._actions if word in a.option_strings),None)
        if action:
            if action.nargs!=0: awaiting=word
            continue
        sub=next((a for a in parser._actions if isinstance(a,argparse._SubParsersAction)),None)
        if sub and word in sub.choices: parser=sub.choices[word]
    if awaiting:
        if awaiting in ('--profile','--project','-p'):
            try: data=config._read_file()
            except (ValueError,OSError): return []
            profiles=data.get('profiles',{})
            values=profiles.keys() if awaiting=='--profile' else [p.get('project','') for p in profiles.values()]
            return sorted(set(v for v in values if v and v.startswith(prefix)))
        return []
    options=[flag for action in parser._actions for flag in action.option_strings]
    sub=next((a for a in parser._actions if isinstance(a,argparse._SubParsersAction)),None)
    values=options+(list(sub.choices) if sub else [])
    return sorted(v for v in values if v.startswith(prefix))


def script(shell,prog):
    command=shlex.quote(prog)
    if shell=='bash':
        return f'''_jira_cli_toolkit_complete() {{
  local line
  COMPREPLY=()
  while IFS= read -r line; do COMPREPLY+=("$line"); done < <({command} --_complete "${{COMP_WORDS[@]:1}}")
}}
complete -F _jira_cli_toolkit_complete {command}
'''
    if shell=='zsh':
        return f'''#compdef {prog}
_jira_cli_toolkit_complete() {{
  local -a candidates
  candidates=("${{(@f)$({command} --_complete "${{words[@]:1}}")}}")
  compadd -- "${{candidates[@]}}"
}}
compdef _jira_cli_toolkit_complete {command}
'''
    return f'''complete -c {command} -f -a '({command} --_complete (commandline -opc)[2..-1] (commandline -ct))'
'''
