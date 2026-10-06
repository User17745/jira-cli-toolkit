"""Guided personal API-token setup and profile operations."""
from __future__ import annotations

import getpass
import os
import re
import sys
import uuid
from types import SimpleNamespace

import requests
from rich.panel import Panel

from . import config, credentials, ui
from .client import Jira, JiraError

TOKEN_URL = 'https://id.atlassian.com/manage-profile/security/api-tokens'


def interactive(args):
    return not args.no_input and sys.stdin.isatty() and not args.json


def profile_name(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', name):
        raise ValueError('Profile names use 1–64 letters, digits, underscores or hyphens.')
    return name


def document():
    current = config._read_file()
    if current.get('schema_version') == 2:
        return current
    if current:
        raise ValueError('Legacy configuration exists. Run config migrate before saving profiles; your old credentials are unchanged.')
    return {'schema_version':2, 'active_profile':None, 'profiles':{}}


def explain():
    ui.err_console.print(Panel(
        '[bold cyan]Connect your Jira account[/bold cyan]\n\n'
        f'1. Open [link={TOKEN_URL}]{TOKEN_URL}[/link]\n'
        '2. Create a token for Jira and choose an expiration date.\n'
        '3. Paste it below; input is hidden.\n\n'
        '[bold]Permissions[/bold]: tokens inherit your account’s project permissions. '
        'Scoped tokens also need scopes for each operation. Browse, create, edit, '
        'transition, attachments, and Jira Software operations can require different access.\n'
        'A token does not grant administrator access.\n\n'
        '[dim]Store: native OS credential store by default. Headless use: environment '
        'variables. Plaintext file storage requires --storage file (POSIX only).[/dim]',
        title='Jira CLI Toolkit', border_style='cyan'))


def api_site(site, scoped=False, cloud_id=None):
    if not scoped and not cloud_id:
        return site, None
    if not cloud_id:
        try:
            r=requests.get(site+'/_edge/tenant_info', timeout=(10,30))
            r.raise_for_status()
            cloud_id=r.json().get('cloudId')
        except (requests.RequestException, ValueError):
            raise ValueError('Could not discover the cloud ID. Pass --cloud-id for a scoped token.') from None
    if not cloud_id or not re.fullmatch(r'[a-zA-Z0-9-]+', cloud_id):
        raise ValueError('Invalid cloud ID.')
    return 'https://api.atlassian.com/ex/jira/'+cloud_id, cloud_id


def validate(site, email, token):
    client=Jira(site,email,token)
    try:
        identity=client.me()
        if not isinstance(identity,dict) or not identity.get('accountId'):
            raise ValueError('Jira returned an invalid account identity; no credentials were saved.')
        return identity
    finally:
        client.close()


def persist(doc, name, settings, token):
    # New credential ID preserves the old credential on a failed config write.
    old=doc['profiles'].get(name)
    settings={**settings,'credential_id':str(uuid.uuid4())}
    credentials.put(settings,token,config.CONFIG_PATH)
    doc['profiles'][name]=settings
    doc['active_profile']=name
    try:
        config.atomic_json(config.CONFIG_PATH,doc)
    except OSError:
        credentials.delete(settings,config.CONFIG_PATH)
        raise
    if old:
        try:
            credentials.delete(old,config.CONFIG_PATH)
        except credentials.CredentialError:
            ui.err_console.print('The replaced credential could not be removed from its old store. Local config uses the new credential.')


def login(args, *, replace=False):
    doc=document()
    name=profile_name(args.profile or os.getenv('JIRA_PROFILE') or doc.get('active_profile') or 'default')
    old=doc['profiles'].get(name,{})
    can_prompt=interactive(args)
    if can_prompt:
        explain()
    site=(getattr(args,'site',None) or (None if replace else os.getenv('JIRA_SITE')) or old.get('site',''))
    email=(getattr(args,'email',None) or (None if replace else os.getenv('JIRA_EMAIL')) or old.get('email',''))
    if can_prompt and not replace:
        site=input(f'Jira site [{site}]: ').strip() or site
        email=input(f'Account email [{email}]: ').strip() or email
    site=config.validate_site(site)
    token=getattr(args,'token',None) or (None if replace else os.getenv('JIRA_API_TOKEN'))
    if getattr(args,'token_stdin',False):
        token=sys.stdin.readline().strip()
    if not token and can_prompt:
        token=getpass.getpass('Paste API token (hidden): ').strip()
    if not email or not token:
        raise ValueError('Login needs a site, email and token. Use interactive auth login or JIRA_SITE/JIRA_EMAIL/JIRA_API_TOKEN with --no-input.')
    if replace and (site!=old.get('site') or email!=old.get('email')):
        raise ValueError('Token recovery cannot change the selected site/account. Use an explicit new profile.')
    scoped=getattr(args,'scoped',False) or bool(old.get('cloud_id'))
    endpoint,cloud_id=api_site(site,scoped,getattr(args,'cloud_id',None) or old.get('cloud_id'))
    identity=validate(endpoint,email,token)
    selected_project=args.project or old.get('project','')
    if selected_project or can_prompt:
        j=Jira(endpoint,email,token)
        try:
            if selected_project:
                selected_project=j.project_get(selected_project)['key']
            elif can_prompt:
                projects=j.projects(all_results=True)
                if projects:
                    index=ui.pick('Default project', ['Skip for now']+[f"{p['key']} — {p['name']}" for p in projects])
                    selected_project=projects[index-1]['key'] if index else ''
        finally:
            j.close()
    settings=dict(site=site,email=email,account_id=identity['accountId'],
                  project=selected_project,board=old.get('board'),
                  storage=getattr(args,'storage',None) or old.get('storage','keyring'))
    if replace and old.get('account_id') and identity['accountId']!=old['account_id']:
        raise ValueError('Replacement token belongs to a different account; create another profile explicitly.')
    if cloud_id:
        settings['cloud_id']=cloud_id
    persist(doc,name,settings,token)
    return dict(authenticated=True,profile=name,site=site,account_id=identity['accountId'],
                storage=settings['storage'],project=settings['project'],
                expiry='unknown; API tokens cannot be refreshed')


def migrate(args):
    old=config._read_file()
    if old.get('schema_version')==2:
        return {'migrated':False,'schema_version':2}
    site=config.validate_site(old.get('JIRA_SITE',''))
    email,token=old.get('JIRA_EMAIL'),old.get('JIRA_API_TOKEN')
    if not email or not token:
        raise ValueError('Legacy configuration has no complete identity to migrate. Use auth login for a new installation.')
    identity=validate(site,email,token)
    name=profile_name(args.profile or 'default')
    doc={'schema_version':2,'active_profile':name,'profiles':{}}
    settings=dict(site=site,email=email,account_id=identity['accountId'],project=old.get('JIRA_PROJECT',''),storage=args.storage)
    # Original plaintext remains intact until both secure storage and atomic config write succeed.
    persist(doc,name,settings,token)
    return {'migrated':True,'profile':name,'schema_version':2,'storage':args.storage}


def status(args, doctor=False):
    cfg=config.resolve_config(args)
    result={k:cfg.get(k) for k in ('site','email','profile','source','project','board')}
    result.update(authenticated=False, token_configured=bool(cfg['token']), expiry='unknown', refresh_supported=False)
    if not all(cfg.get(k) for k in ('site','email','token')):
        raise ValueError('No complete credentials. Run auth login or config migrate.')
    identity=validate(cfg.get('api_site',cfg['site']),cfg['email'],cfg['token'])
    result.update(authenticated=True,account_id=identity['accountId'],display_name=identity.get('displayName'))
    if doctor and cfg.get('project'):
        j=Jira(cfg.get('api_site',cfg['site']),cfg['email'],cfg['token'])
        try:
            result['project_access']=j.project_get(cfg['project']).get('key')
        finally:
            j.close()
    return result


def local(args):
    doc=document()
    profiles=doc['profiles']
    name=args.profile or os.getenv('JIRA_PROFILE') or doc.get('active_profile')
    if args.cmd=='profile-list':
        return {'active_profile':doc.get('active_profile'), 'profiles':[
            {'name':n,**{k:v for k,v in p.items() if k!='credential_id'}} for n,p in profiles.items()]}
    if args.cmd in ('profile-use','profile-remove'):
        name=args.name
    if name not in profiles:
        raise ValueError('Select an existing profile; use profile list.')
    if args.cmd=='profile-use':
        doc['active_profile']=name
    elif args.cmd in ('profile-remove','auth-logout'):
        credentials.delete(profiles[name],config.CONFIG_PATH)
        if args.cmd=='profile-remove':
            del profiles[name]
            if doc.get('active_profile')==name:
                doc['active_profile']=None  # Never silently switch identities.
        config.atomic_json(config.CONFIG_PATH,doc)
        return {'profile':name,'local_credential_removed':True,'upstream_revoked':False,
                'external_credentials_unchanged':True}
    elif args.cmd=='config-get':
        return {'profile':name,args.key:profiles[name].get(args.key)}
    elif args.cmd=='config-set':
        # Validate contextual preferences through context use rather than arbitrary edits.
        args.project=args.value if args.key=='project' else None
        args.board=int(args.value) if args.key=='board' else None
        args.cmd='context-use'
    if args.cmd=='context-use':
        cfg=config.resolve_config(SimpleNamespace(profile=name,site=None,email=None,token=None,project=None))
        j=Jira(cfg.get('api_site',cfg['site']),cfg['email'],cfg['token'])
        try:
            if getattr(args,'select',False):
                if not interactive(args): raise ValueError('--select requires interactive input without --json.')
                projects=j.projects(all_results=True)
                if not projects: raise ValueError('No accessible projects.')
                selected=projects[ui.pick('Project',[f"{p['key']} — {p['name']}" for p in projects])]
                args.project=selected['key']
                if selected.get('projectTypeKey')=='software':
                    boards=j.boards(project=args.project,all_results=True).get('values',[])
                    index=ui.pick('Default board',['No default board']+[f"{b['name']} [{b['id']}]" for b in boards])
                    args.board=boards[index-1]['id'] if index else None
            if args.project:
                p=j.project_get(args.project)
                if profiles[name].get('project') != p['key']:
                    profiles[name]['board']=None
                profiles[name]['project']=p['key']
            if args.board:
                if args.board<1: raise ValueError('Board IDs must be positive.')
                j.board_get(args.board)
                profiles[name]['board']=args.board
            doc['active_profile']=name
        finally:
            j.close()
    config.atomic_json(config.CONFIG_PATH,doc)
    return {'profile':name,'project':profiles[name].get('project'),'board':profiles[name].get('board')}


def handle(args):
    if args.cmd=='auth-login': return login(args)
    if args.cmd=='config-migrate': return migrate(args)
    if args.cmd in ('auth-status','doctor'): return status(args, args.cmd=='doctor')
    return local(args)
