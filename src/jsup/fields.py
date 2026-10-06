"""Metadata-aware field input; arbitrary validators remain Jira's responsibility."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import os
import sys
import tempfile
import time

from . import config, ui
from .client import adf, JiraError

TTL=300


def cached(cfg,project,kind,fetch,refresh=False):
    identity=[cfg['site'],cfg.get('email'),cfg.get('profile'),project,kind]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    path=config.CONFIG_PATH.parent/'cache'/(key+'.json')
    if not refresh:
        try:
            entry=json.loads(path.read_text())
            if 0<=time.time()-entry['saved_at']<TTL:
                return entry['data']
        except (OSError,ValueError,KeyError,TypeError): pass
    data=fetch()
    try: config.atomic_json(path,{'saved_at':time.time(),'data':data})
    except OSError: pass  # Cache availability must not block Jira operations.
    return data


def invalidate(cfg):
    # Invalidate this CLI's metadata cache after a validation failure.
    for path in (config.CONFIG_PATH.parent/'cache').glob('*.json'):
        try: path.unlink()
        except OSError: pass


def choose(items,value,label):
    if not isinstance(items,list) or any(not isinstance(i,dict) or 'id' not in i for i in items):
        raise ValueError('Jira returned invalid value metadata.')
    if value is None: raise ValueError(f'Pass {label}; available values: '+', '.join(f"{i['name']} [id:{i['id']}]" for i in items))
    raw=str(value).removeprefix('id:')
    exact=[i for i in items if str(i.get('id'))==raw]
    matches=exact or [i for i in items if str(i.get('name',i.get('value',''))).casefold()==raw.casefold()]
    if len(matches)!=1:
        raise ValueError(f'{label} {value!r} is unavailable or ambiguous; use an explicit ID. Available: '+', '.join(f"{i.get('name',i.get('value',''))} [id:{i.get('id')}]" for i in items))
    return matches[0]


def normalize(meta):
    if isinstance(meta,dict): return meta
    return {item.get('fieldId') or item['key']:item for item in meta}


def field_key(meta,key):
    if key in meta: return key
    matches=[fid for fid,f in meta.items() if f.get('name','').casefold()==key.casefold()]
    if len(matches)!=1: raise ValueError(f'Unknown or ambiguous field {key!r}; use its field ID (project fields).')
    return matches[0]


def typed(field,value):
    schema=field.get('schema',{}); kind=schema.get('type')
    if value is None: return None
    if isinstance(value,(dict,list,int,float,bool)):
        return value  # Explicit structured values are passed intact for Jira validation.
    if kind=='array':
        values=value.split(',')
        element={**field,'schema':{**schema,'type':schema.get('items')}}
        return [typed(element,v.strip()) for v in values if v.strip()]
    allowed=field.get('allowedValues',[])
    if allowed:
        if isinstance(allowed[0],str):
            matches=[option for option in allowed if option.casefold()==value.casefold()]
            if len(matches)!=1: raise ValueError(f"{field.get('name')}: value is not allowed.")
            return matches[0]
        item=choose(allowed,value,field.get('name','field'))
        if isinstance(item,dict):
            return {'id':str(item['id'])} if 'id' in item else {'value':item.get('value',item.get('name'))}
        return item
    if kind in ('number','integer'):
        try: return int(value) if kind=='integer' else float(value)
        except ValueError: raise ValueError(f"{field.get('name')}: expected a number.") from None
    if kind=='date':
        try: return date.fromisoformat(value).isoformat()
        except ValueError: raise ValueError(f"{field.get('name')}: use YYYY-MM-DD.") from None
    if kind=='user': return {'accountId':value.removeprefix('id:')}
    if kind in ('priority','component','option','issuetype','resolution','version'):
        if not value.startswith('id:'): raise ValueError(f"{field.get('name')}: pass id:<ID> or structured JSON; no allowed-value names were returned.")
        return {'id':value[3:]}
    if field.get('key')=='description' or schema.get('system')=='description' or schema.get('custom','').endswith(':textarea'):
        return adf(value)
    if kind in ('string',None): return value
    if kind=='issuelink': return {'key':value}
    raise ValueError(f"{field.get('name')}: unsupported field format ({kind}); supply a structured JSON value using --field FIELD:=JSON or --fields-file.")


def supplied(args,meta):
    values={}
    if getattr(args,'fields_file',None):
        values=json.loads(Path(args.fields_file).read_text())
        if not isinstance(values,dict): raise ValueError('--fields-file must contain a JSON object of field values.')
    for entry in getattr(args,'field',[]):
        separator=':=' if ':=' in entry else '='
        key,found,value=entry.partition(separator)
        if not found or not key: raise ValueError('Use --field FIELD=VALUE or FIELD:=JSON.')
        values[key]=json.loads(value) if separator==':=' else value
    result={}
    for key,value in values.items():
        fid=field_key(meta,key)
        if fid in result: raise ValueError(f'Duplicate values refer to field {fid}; use one ID/name.')
        result[fid]=typed(meta[fid],value)
    return result


def description(args):
    if getattr(args,'desc_file',None): return Path(args.desc_file).read_text()
    if getattr(args,'editor',False):
        if args.no_input or args.json or not sys.stdin.isatty(): raise ValueError('--editor requires interactive input without --json.')
        editor=os.getenv('VISUAL') or os.getenv('EDITOR')
        if not editor: raise ValueError('Set VISUAL or EDITOR before using --editor.')
        with tempfile.TemporaryDirectory(prefix='jira-editor-') as temp:
            path=Path(temp)/'description.txt'; path.write_text(getattr(args,'desc',None) or '')
            try: subprocess.run([*shlex.split(editor),str(path)],check=True)
            except subprocess.SubprocessError: raise ValueError('Editor failed; no Jira operation was submitted.') from None
            return path.read_text()
    return getattr(args,'desc',None)


def require_fields(args,meta,fields):
    missing=[key for key,f in meta.items() if f.get('required') and not f.get('hasDefaultValue') and fields.get(key) in (None,'',[])]
    if missing and (args.no_input or args.json or not sys.stdin.isatty()):
        raise ValueError('Required fields missing: '+', '.join(f"{meta[k].get('name',k)} ({k})" for k in missing)+'. Supply --field FIELD=VALUE or --fields-file.')
    for key in missing:
        field=meta[key]; allowed=field.get('allowedValues',[])
        if allowed:
            index=ui.pick(field.get('name',key),[f"{v.get('name',v.get('value'))} [id:{v.get('id')}]" for v in allowed])
            fields[key]=typed(field,'id:'+str(allowed[index]['id']))
        else:
            fields[key]=typed(field,input(f"{field.get('name',key)} ({key}): ").strip())
            if fields[key] in (None,'',[]): raise ValueError(f'Required field {key} cannot be empty.')


def prepare_create(j,args,cfg):
    project=cfg['project']
    if not project: raise ValueError('Select a project with --project or context use.')
    types=cached(cfg,project,'types',lambda:j.issue_types(project),args.refresh)
    issue_type=args.type
    if not issue_type and not args.no_input and not args.json and sys.stdin.isatty():
        issue_type=types[ui.pick('Issue type',[f"{i['name']} [{i['id']}]" for i in types])]['id']
    selected=choose(types,issue_type,'--type')
    meta=normalize(cached(cfg,project,'create:'+selected['id'],lambda:j.create_fields(project,selected['id']),args.refresh))
    provided=supplied(args,meta)
    explicit={'summary':args.summary,'description':description(args),'priority':args.priority,
              'assignee':args.assignee,'labels':args.label or None,'components':args.component or None,'parent':args.parent}
    fields={}
    for key,value in getattr(args,'template_fields',{}).items():
        fid=field_key(meta,key)
        if fid in provided or explicit.get(fid) is not None:
            continue
        if isinstance(value,list) and all(isinstance(v,str) for v in value): value=','.join(value)
        fields[fid]=typed(meta[fid],value)
    fields.update(provided)
    if 'project' in fields or 'issuetype' in fields: raise ValueError('Select project/type with --project and --type, not --field.')
    fields.update(project={'key':project},issuetype={'id':selected['id']})
    for key,value in explicit.items():
        if value is not None:
            if key not in meta: raise ValueError(f'Field {key} is not available for creation in this project/type.')
            if key in ('parent',): fields[key]={'key':value}
            else: fields[key]=typed(meta[key],','.join(value) if isinstance(value,list) else value)
    require_fields(args,meta,fields)
    return fields


def create(j,args,cfg):
    if getattr(args,'template',None):
        from .templates import apply
        apply(args)
    fields=prepare_create(j,args,cfg)
    try: return j.create_with_fields(fields)
    except JiraError as error:
        if error.status in (400,422): invalidate(cfg)
        raise


def transition(j,args,cfg):
    transitions=j.transition_fields(args.key).get('transitions',[])
    selected=choose(transitions,args.to,'--to')
    meta=normalize(selected.get('fields',{}))
    fields=supplied(args,meta)
    require_fields(args,meta,fields)
    result=j.transition_with_fields(args.key,selected['id'],fields)
    return {**result, 'moved':args.key, 'to':selected['name']}
