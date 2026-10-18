
# ---------------------------------------------------------------------------
# Firmware patcher
# ---------------------------------------------------------------------------
import base64
import hashlib
import io
import json
import os
import sys
import tarfile

FW_MAGIC = 0x46577830  # "FWx0"
FW_SIGNATURE, FW_INFO = 0, 1
MARKER = '/usr/share/stora-patch/version'


def fw_crc(data):
    """CRC as computed by OpenWrt's fwtool (CRC-32 without final inversion)."""
    return (~zlib.crc32(data)) & 0xFFFFFFFF


def split_fwtool(data):
    """Return (payload, metadata_json_bytes or None, had_signature)."""
    metadata, signature = None, False
    end = len(data)
    while end >= 16:
        magic, crc, typ, size = struct.unpack('>IIB3xI', data[end - 16:end])
        if magic != FW_MAGIC or size < 16 or size > end:
            break
        start = end - size
        if fw_crc(data[:end - 16]) != crc:
            raise SystemExit('ERROR: the firmware file is damaged (metadata checksum mismatch).')
        if typ == FW_SIGNATURE:
            signature = True
        elif typ == FW_INFO:
            metadata = data[start + 8:end - 16]  # skip 8 byte header (version, flags)
        end = start
    return data[:end], metadata, signature


def append_metadata(payload, metadata):
    hdr = struct.pack('<II', 0, 0)
    size = len(hdr) + len(metadata) + 16
    crc = fw_crc(payload + hdr + metadata)
    return payload + hdr + metadata + struct.pack('>IIB3xI', FW_MAGIC, crc, FW_INFO, size)


def load_payload():
    files = []
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)), mode='r:gz') as t:
        for m in t.getmembers():
            if m.isfile():
                files.append(('file', '/' + m.name.lstrip('./'), m.mode & 0o7777, t.extractfile(m).read()))
            elif m.issym():
                files.append(('symlink', '/' + m.name.lstrip('./'), m.linkname, None))
    return files


def say(msg=''):
    print(msg, flush=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not args or len(args) > 2:
        say(__doc__)
        return 1
    src = args[0]
    if len(args) == 2:
        dst = args[1]
    else:
        base, ext = os.path.splitext(src)
        dst = base + '-patched' + (ext or '.bin')
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit('ERROR: input and output must be different files.')

    say('Stora firmware patcher %s' % VERSION)
    say('Reading %s' % src)
    with open(src, 'rb') as f:
        data = f.read()

    payload, metadata, signed = split_fwtool(data)
    if metadata is None:
        raise SystemExit('ERROR: this is not an OpenWrt sysupgrade image (no image metadata found).\n'
                         'Use the file with "sysupgrade" in its name.')
    meta = json.loads(metadata.decode('utf-8', 'replace'))
    devices = meta.get('supported_devices', []) + meta.get('new_supported_devices', [])
    version = meta.get('version', {}).get('version', '?')
    say('  OpenWrt %s for %s' % (version, ', '.join(devices) or '?'))
    if not any('stora' in d for d in devices):
        raise SystemExit('ERROR: this firmware is not for the Netgear Stora.')

    try:
        tar = tarfile.open(fileobj=io.BytesIO(payload), mode='r:')
        members = tar.getmembers()
    except tarfile.TarError:
        raise SystemExit('ERROR: unexpected firmware layout (not a sysupgrade tar).')
    root_member = next((m for m in members if m.name.endswith('/root')), None)
    if root_member is None:
        raise SystemExit('ERROR: no root file system found in the firmware.')

    say('Opening the root file system')
    rootfs = tar.extractfile(root_member).read()
    img = Image(rootfs)

    already = img.lookup(MARKER)
    if already is not None:
        say('  This firmware was patched before (%s); the files are replaced.'
            % img.read_file(already).decode(errors='replace').strip())

    say('Adding: Services > Disks & RAID, System > Shut down, Stora power-off')
    for kind, path, a, b in load_payload():
        if kind == 'file':
            img.add_file(path, b, a)
        else:
            img.add_symlink(path, a)
    img.add_file(MARKER, ('stora-patch %s\n' % VERSION).encode(), 0o644)

    missing = [name for name, path in (('ksmbd-server (network shares)', '/usr/sbin/ksmbd.adduser'),
                                       ('fdisk', '/usr/sbin/fdisk'),
                                       ('e2fsprogs', '/usr/sbin/mkfs.ext4'),
                                       ('block-mount', '/sbin/block'),
                                       ('mdadm (RAID)', '/sbin/mdadm'),
                                       ('smartmontools (SMART)', '/usr/sbin/smartctl'))
               if img.lookup(path) is None]

    say('Building the new root file system')
    newroot = img.build()

    say('Checking the result')
    check = Image(newroot)
    for kind, path, a, b in load_payload():
        node = check.lookup(path)
        if node is None:
            raise SystemExit('ERROR: self-check failed for %s' % path)
        if kind == 'file' and check.read_file(node) != b:
            raise SystemExit('ERROR: self-check failed for %s' % path)
    nfiles = 0
    for _path, node in walk_files(check.root):
        if node.kind == FILE:
            check.read_file(node)
            nfiles += 1
    say('  %d files readable, OK' % nfiles)

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w', format=tarfile.GNU_FORMAT) as nt:
        for m in members:
            if m is root_member:
                nm = tarfile.TarInfo(m.name)
                nm.size, nm.mode, nm.mtime = len(newroot), m.mode, m.mtime
                nm.uid, nm.gid, nm.uname, nm.gname = 0, 0, m.uname, m.gname
                nt.addfile(nm, io.BytesIO(newroot))
            elif m.isfile():
                nt.addfile(m, tar.extractfile(m))
            else:
                nt.addfile(m)
    result = append_metadata(out.getvalue(), metadata)

    with open(dst, 'wb') as f:
        f.write(result)

    say()
    say('Done: %s' % dst)
    say('  size   %d bytes' % len(result))
    say('  sha256 %s' % hashlib.sha256(result).hexdigest())
    if signed:
        say('  Note: the original OpenWrt signature was removed (the content changed).')
    if missing:
        say()
        say('WARNING: these packages are not in this firmware, so parts of the')
        say('Disks & RAID page will not work until they are added:')
        for name in missing:
            say('  - ' + name)
        say('Build the firmware with the Firmware Selector and add them to the package list.')
    say()
    say('Flash it in the web interface: System > Backup / Flash Firmware > Flash image.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SquashError as e:
        sys.exit('ERROR: %s' % e)
