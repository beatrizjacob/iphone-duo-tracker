"""Durable state on a dedicated git branch; no cache eviction or source commits."""
import json
import subprocess
import sys
from pathlib import Path

BRANCH = 'refs/heads/stock-state'

def git(*args, data=None, check=True):
    return subprocess.run(['git', *args], input=data, text=True, capture_output=True, check=check)

def remote_head():
    result = git('ls-remote', '--exit-code', 'origin', BRANCH, check=False)
    if result.returncode == 2: return None
    if result.returncode != 0: raise RuntimeError('Cannot read state branch; refusing to reset state')
    return result.stdout.split()[0]

def main():
    mode = sys.argv[1]
    if mode == 'load':
        old = remote_head()
        Path('.state-parent').write_text(old or '')
        if old:
            git('fetch', '--no-tags', 'origin', BRANCH)
            content = git('show', f'{old}:state.json').stdout
            json.loads(content)  # Corruption must fail, never silently reset.
            Path('state.json').write_text(content)
        else:
            Path('state.json').write_text(json.dumps({'version': 1, 'sources': {}, 'items': {}}))
    elif mode == 'save':
        if not Path('state.json').exists(): return
        old = Path('.state-parent').read_text().strip()
        content = Path('state.json').read_text(); json.loads(content)
        if old and git('show', f'{old}:state.json').stdout == content: return
        blob = git('hash-object', '-w', '--stdin', data=content).stdout.strip()
        tree = git('mktree', data=f'100644 blob {blob}\tstate.json\n').stdout.strip()
        git('config', 'user.name', 'StockWatch')
        git('config', 'user.email', 'stockwatch@users.noreply.github.com')
        parent = ['-p', old] if old else []
        commit = git('commit-tree', tree, *parent, data='Update stock monitor state\n').stdout.strip()
        git('push', 'origin', f'{commit}:{BRANCH}')  # Never force-push.
    else: raise RuntimeError('Expected load or save')

if __name__ == '__main__':
    try: main()
    except Exception: raise SystemExit('State persistence failed. Check repository write permissions; alerts may repeat.') from None
