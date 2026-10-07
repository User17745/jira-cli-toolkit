"""Issue maintenance with metadata validation and explicit destructive actions."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from . import fields
from .client import JiraError, project_jql


def edit(j,args,cfg):
    meta=fields.normalize(j.edit_fields(args.key))
    values=fields.supplied(args,meta)
    explicit={'summary':args.summary,'description':fields.description(args),'priority':args.priority,
              'duedate':args.due_date,'parent':args.parent}
    for key,value in explicit.items():
        if value is not None:
            if key not in meta: raise ValueError(f'Field {key} is not editable on this issue.')
            values[key]={'key':value} if key=='parent' else fields.typed(meta[key],value)
    updates={}
    for singular,plural in [('label','labels'),('component','components')]:
        replace=getattr(args,singular); add=getattr(args,'add_'+singular); remove=getattr(args,'remove_'+singular)
        if replace and (add or remove): raise ValueError(f'Use either --{singular} replacement or add/remove operations.')
        if (replace or add or remove) and plural not in meta: raise ValueError(f'Field {plural} is not editable.')
        if replace: values[plural]=fields.typed(meta[plural],','.join(replace))
        if add or remove:
            if plural in values: raise ValueError(f'Field {plural} cannot be both replaced and incrementally updated.')
            permitted=meta[plural].get('operations',[])
            for operation,items in [('add',add),('remove',remove)]:
                if items and operation not in permitted: raise ValueError(f'Jira does not allow {operation} on {plural} for this issue.')
                element={**meta[plural],'schema':{**meta[plural].get('schema',{}),'type':meta[plural].get('schema',{}).get('items')}}
                updates.setdefault(plural,[]).extend({operation:fields.typed(element,item)} for item in items)
    if not values and not updates: raise ValueError('No changes supplied. Use issue edit --help.')
    for key,value in values.items():
        if meta[key].get('required') and value in (None,'',[]): raise ValueError(f'Required field {key} cannot be cleared.')
        if 'set' not in meta[key].get('operations',['set']): raise ValueError(f'Jira does not allow setting {key}.')
    try: return j.edit_issue(args.key,values,updates or None)
    except JiraError as error:
        if error.status in (400,422): fields.invalidate(cfg)
        raise


def body(args):
    if args.message is not None: return args.message
    if getattr(args,'message_file',None): return Path(args.message_file).read_text(encoding="utf-8")
    if getattr(args,'editor',False):
        proxy=SimpleNamespace(desc=None,desc_file=None,editor=True,json=args.json,no_input=args.no_input)
        return fields.description(proxy)
    raise ValueError('Supply --message, --message-file, or interactive --editor.')


def issue_list(j,args,cfg):
    filters=bool(args.open or args.project or args.assignee or args.status or args.type or args.label or args.board)
    if args.jql:
        if filters or args.order_by!='updated' or args.order!='desc': raise ValueError('--jql is a complete query; omit generated filters and ordering flags.')
        jql=args.jql
    else:
        clauses=[]
        project=args.project or (None if args.board else cfg['project'])
        if not project and not args.board: raise ValueError('Select --project or --board, or supply complete --jql.')
        if project: clauses.append(project_jql(project))
        if args.open: clauses.append('statusCategory != Done')
        if args.assignee: clauses.append('assignee = '+('currentUser()' if args.assignee=='me' else json.dumps(args.assignee.removeprefix('id:'))))
        if args.status: clauses.append('status IN ('+', '.join(json.dumps(s) for s in args.status)+')')
        if args.type: clauses.append('issuetype = '+json.dumps(args.type))
        for label in args.label: clauses.append('labels = '+json.dumps(label))
        jql=' AND '.join(clauses)+f' ORDER BY {args.order_by} {args.order.upper()}'
        jql=jql.strip()
    options={}
    if getattr(args,'all',False): options['all_results']=True
    if args.fields: options['fields']=args.fields
    if args.board: return j.board_issues(args.board,jql,args.max,**options)
    return j.search(jql,args.max,**options)


def handle(j,args,cfg):
    cmd=args.cmd
    if cmd=='issue-edit': return edit(j,args,cfg)
    if cmd=='issue-unassign': return j.assign(args.key,None)
    if cmd=='issue-assign':
        if args.user=='me': account=j.me()['accountId']
        elif args.user.startswith('id:'): account=args.user[3:]
        else:
            candidates=j.assignable_users(args.key,args.user)
            matches=[u for u in candidates if args.user.casefold() in (u.get('displayName','').casefold(),u.get('emailAddress','').casefold())]
            if len(matches)!=1: raise ValueError('User is unavailable or ambiguous; use --user id:<account ID>.')
            account=matches[0]['accountId']
        if not account: raise ValueError('A nonempty account ID is required.')
        return j.assign(args.key,account)
    if cmd=='issue-link':
        kind=fields.choose(j.link_types(),args.type,'--type')
        inward,outward=(args.other,args.key) if args.direction=='outward' else (args.key,args.other)
        return j.link(inward,outward,kind['id'])
    if cmd=='issue-unlink': return j.unlink(args.id)
    if cmd in ('comment-add','comment-edit'):
        text=body(args)
        if not text.strip(): raise ValueError('Comment body cannot be empty.')
        return j.comment_add(args.key,text) if cmd=='comment-add' else j.comment_edit(args.key,args.comment_id,text)
    if cmd=='comment-delete': return j.comment_delete(args.key,args.comment_id)
    if cmd=='attachment-list': return j.issue_get(args.key).get('fields',{}).get('attachment',[])
    if cmd=='attachment-upload': return j.attachment_upload(args.key,args.files)
    if cmd=='attachment-download': return j.attachment_download(args.id,args.output)
    if cmd=='attachment-delete': return j.attachment_delete(args.id)
    raise ValueError('Unsupported maintenance operation.')
