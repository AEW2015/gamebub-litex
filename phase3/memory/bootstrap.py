#!/usr/bin/env python3
"""Install extra pinned memory IP into a private target; never change phase2 venv."""
import hashlib,json,pathlib,subprocess,sys,urllib.request
lock=json.loads(pathlib.Path(__file__).with_name('dependencies.json').read_text())
prefix=pathlib.Path(lock['prefix'])
if prefix.exists():
    raise SystemExit('Refusing to replace existing '+str(prefix))
downloads=prefix.with_name('phase3-memory-downloads')
downloads.mkdir(exist_ok=True)
files=[]
for entry in lock['packages']:
    path=downloads/entry['file']
    if not path.exists():
        with urllib.request.urlopen(entry['url']) as src,path.open('xb') as dest:
            while block:=src.read(1024*1024):dest.write(block)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise SystemExit('Hash mismatch: '+str(path))
    files.append(str(path))
subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--target',str(prefix),*files],check=True)
