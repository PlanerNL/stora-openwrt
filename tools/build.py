#!/usr/bin/env python3
"""Rebuilds ../stora-patch.py from tools/*.py and the files in ../src."""
import base64, io, os, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'src')
VERSION = open(os.path.join(HERE, 'VERSION')).read().strip()

buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz', format=tarfile.GNU_FORMAT) as t:
    for top in sorted(os.listdir(SRC)):
        for dp, dn, fn in os.walk(os.path.join(SRC, top)):
            dn.sort()
            for f in sorted(fn):
                p = os.path.join(dp, f)
                ti = t.gettarinfo(p, arcname=os.path.relpath(p, SRC).replace(os.sep, '/'))
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = 'root'
                if ti.isfile():
                    # executables: scripts in sbin, etc/init.d and usr/libexec
                    if ti.name.startswith(('sbin/', 'etc/init.d/', 'usr/libexec/')):
                        ti.mode = 0o755
                    else:
                        ti.mode = 0o644
                    with open(p, 'rb') as fh:
                        t.addfile(ti, fh)
                else:
                    t.addfile(ti)
    # enable the power-off service (symlinks are made here, so the repository
    # contains no symlinks and also checks out cleanly on Windows)
    for link in ('etc/rc.d/S99stora-power', 'etc/rc.d/K89stora-power'):
        ti = tarfile.TarInfo(link)
        ti.type, ti.linkname, ti.mode = tarfile.SYMTYPE, '../init.d/stora-power', 0o777
        ti.uname = ti.gname = 'root'
        t.addfile(ti)
b64 = base64.b64encode(buf.getvalue()).decode()
payload = '\n'.join(b64[i:i + 76] for i in range(0, len(b64), 76))
rd = lambda n: open(os.path.join(HERE, n), encoding='utf-8').read()
out = ('#!/usr/bin/env python3\n' + rd('header.txt') + "\nVERSION = '%s'\n\nPAYLOAD = '''\n%s\n'''\n\n" % (VERSION, payload)
       + rd('sqfs.py') + '\n' + rd('main.py'))
with open(os.path.join(ROOT, 'stora-patch.py'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(out)
print('stora-patch.py %s written (%d bytes)' % (VERSION, len(out)))
