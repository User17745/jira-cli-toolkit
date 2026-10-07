"""Versioned, non-executable team templates."""
from __future__ import annotations

import copy
from importlib.resources import files
import json
from pathlib import Path
import re
import string
import sys

from . import config

ALLOWED={'schema_version','name','type','summary','description','fields','variables'}


def load(name):
    if name=='callback':
        data=json.loads(files('jsup').joinpath('data/callback.json').read_text(encoding="utf-8"))
    else:
        path=Path(name)
        if path.suffix!='.json' and len(path.parts)==1:
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',name): raise ValueError('Invalid template name.')
            path=config.CONFIG_PATH.parent/'templates'/(name+'.json')
        data=json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data):
    if not isinstance(data,dict) or data.get('schema_version')!=1 or set(data)-ALLOWED:
        raise ValueError('Unsupported template schema/keys. Templates cannot contain hooks or credentials.')
    if not isinstance(data.get('fields',{}),dict) or not isinstance(data.get('variables',[]),list):
        raise ValueError('Template fields must be an object and variables a list.')
    names=set()
    for variable in data.get('variables',[]):
        if not isinstance(variable,dict) or set(variable)-{'name','prompt','required','default'}:
            raise ValueError('Invalid template variable.')
        name=variable.get('name','')
        if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*',name) or name in names:
            raise ValueError('Invalid or duplicate template variable name.')
        names.add(name)
    for key in ('summary','description'):
        if key in data:
            if not isinstance(data[key],str): raise ValueError('Template summary/description must be strings.')
            try:
                for literal,name,spec,conversion in string.Formatter().parse(data[key]):
                    if name is not None and (name not in names or spec or conversion):
                        raise ValueError('Template placeholders must be declared simple variable names; expressions are unsupported.')
            except ValueError:
                raise ValueError('Invalid template pattern or placeholder.') from None
    return data


def render(data,variables):
    validate(data)
    declared={v['name']:v for v in data.get('variables',[])}
    if set(variables)-set(declared): raise ValueError('Unknown template variables: '+', '.join(sorted(set(variables)-set(declared))))
    resolved={name:variables.get(name,entry.get('default','')) for name,entry in declared.items()}
    missing=[name for name,entry in declared.items() if entry.get('required') and not resolved[name]]
    if missing: raise ValueError('Missing template variables: '+', '.join(missing))
    fields=copy.deepcopy(data.get('fields',{}))
    if 'summary' in data: fields['summary']=data['summary'].format_map(resolved)
    if 'description' in data: fields['description']=data['description'].format_map(resolved)
    return fields


def apply(args, *, validating=False):
    data=load(args.template)
    values={}
    for item in args.var:
        key,sep,value=item.partition('=')
        if not sep: raise ValueError('Use --var NAME=VALUE.')
        values[key]=value
    for variable in data.get('variables',[]):
        name=variable['name']
        if name not in values and variable.get('required'):
            if validating:
                values[name]='example'
            elif not args.no_input and not args.json and sys.stdin.isatty():
                values[name]=input(variable.get('prompt',name)+': ').strip()
    args.template_fields=render(data,values)
    if not args.type: args.type=data.get('type')
    return args


def list_templates():
    local=config.CONFIG_PATH.parent/'templates'
    return {'templates':['callback']+sorted(p.stem for p in local.glob('*.json') if p.stem!='callback')}
