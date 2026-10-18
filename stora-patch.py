#!/usr/bin/env python3
"""
stora-patch.py - adds the extra pages to an OpenWrt firmware for the Netgear Stora

Adds to the firmware file, before you flash it:
  - Services > Disks & RAID   (prepare disks, RAID 0/1, SMART, share users)
  - System > Shut down        (and a working power button: the Stora really
                               switches off instead of only halting)

Works on Windows, macOS and Linux with Python 3.8 or newer; nothing else
has to be installed.

Usage:
  Windows:        py stora-patch.py <firmware-sysupgrade.bin>
  macOS / Linux:  python3 stora-patch.py <firmware-sysupgrade.bin>

The result is written next to the input as <name>-patched.bin (or give a
second file name). Flash that file in the web interface under
System > Backup / Flash Firmware > Flash image.

The input must be an OpenWrt "sysupgrade" image for the Netgear Stora,
for example one built with https://firmware-selector.openwrt.org .
"""

VERSION = '1.0'

PAYLOAD = '''
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
'''

"""
Minimal SquashFS 4.0 reader/rewriter (Python standard library only).

Reads an existing image, lets you add/replace files, directories and symlinks,
and writes a new image. All existing file data (data blocks and fragments) is
copied byte-for-byte; only the metadata (inode table, directory table,
fragment/id tables) is rebuilt. New file data and the rebuilt metadata are
stored uncompressed, which every SquashFS reader supports, so no compressor
is needed for writing.
"""
import lzma
import struct
import zlib

MAGIC = 0x73717368
INVALID = 0xFFFFFFFFFFFFFFFF
NOFRAG = 0xFFFFFFFF
META_SIZE = 8192
BLK_UNCOMP = 1 << 24
META_UNCOMP = 1 << 15

DIR, FILE, SYMLINK, BLKDEV, CHRDEV, FIFO, SOCKET = 1, 2, 3, 4, 5, 6, 7
F_EXPORTABLE = 0x0080

SB_FMT = '<IIIIIHHHHHHQQQQQQQQ'
SB_SIZE = struct.calcsize(SB_FMT)  # 96


class SquashError(Exception):
    pass


class Node:
    __slots__ = ('kind', 'mode', 'uid', 'gid', 'mtime', 'children', 'target',
                 'rdev', 'nlink', 'blocks_start', 'frag', 'frag_off', 'size',
                 'blocks', 'sparse', 'newdata', 'ino', 'ref', 'parent')

    def __init__(self, kind, mode, uid, gid, mtime):
        self.kind, self.mode, self.uid, self.gid, self.mtime = kind, mode, uid, gid, mtime
        self.children = {} if kind == DIR else None
        self.target = None
        self.rdev = 0
        self.nlink = 1
        self.blocks_start = 0
        self.frag = NOFRAG
        self.frag_off = 0
        self.size = 0
        self.blocks = []
        self.sparse = 0
        self.newdata = None   # bytes for files added by us
        self.ino = None
        self.ref = None
        self.parent = None


class Image:
    def __init__(self, data):
        self.data = data
        if len(data) < SB_SIZE:
            raise SquashError('image too small')
        sb = struct.unpack_from(SB_FMT, data, 0)
        (self.magic, self.inode_count, self.mod_time, self.block_size, self.frag_count,
         self.comp, self.block_log, self.flags, self.id_count, vmaj, vmin,
         self.root_ref, self.bytes_used, self.id_start, self.xattr_start,
         self.inode_start, self.dir_start, self.frag_start, self.export_start) = sb
        if self.magic != MAGIC:
            raise SquashError('not a SquashFS image')
        if (vmaj, vmin) != (4, 0):
            raise SquashError('unsupported SquashFS version %d.%d' % (vmaj, vmin))
        if self.xattr_start != INVALID:
            raise SquashError('images with extended attributes are not supported')
        if self.comp not in (1, 4):
            raise SquashError('unsupported compression id %d (only gzip and xz)' % self.comp)

        self.ids = self._read_table(self.id_start, self.id_count, 4, '<I')
        self.frags = self._read_table(self.frag_start, self.frag_count, 16, '<QII') if self.frag_count else []

        dir_end = self._dir_table_end()
        self.inode_bytes, self.inode_map = self._read_meta_region(self.inode_start, self.dir_start)
        self.dir_bytes, self.dir_map = self._read_meta_region(self.dir_start, dir_end)

        self._cache = {}
        self.root = self._read_inode(self.root_ref, None)

    # ---------- low level ----------
    def _decompress(self, raw):
        if self.comp == 4:
            return lzma.decompress(raw, format=lzma.FORMAT_XZ)
        return zlib.decompress(raw)

    def _read_meta_block(self, pos):
        hdr, = struct.unpack_from('<H', self.data, pos)
        size = hdr & 0x7FFF
        raw = self.data[pos + 2:pos + 2 + size]
        out = raw if hdr & META_UNCOMP else self._decompress(raw)
        return out, pos + 2 + size

    def _read_meta_region(self, start, end):
        buf, offsets, pos = bytearray(), {}, start
        while pos < end:
            offsets[pos - start] = len(buf)
            block, pos = self._read_meta_block(pos)
            buf += block
        return bytes(buf), offsets

    def _index_positions(self, start, count, entry_size):
        n = (count * entry_size + META_SIZE - 1) // META_SIZE
        return list(struct.unpack_from('<%dQ' % n, self.data, start)) if n else []

    def _read_table(self, start, count, entry_size, fmt):
        out = bytearray()
        for pos in self._index_positions(start, count, entry_size):
            block, _ = self._read_meta_block(pos)
            out += block
        return [struct.unpack_from(fmt, out, i * entry_size) for i in range(count)] if fmt != '<I' \
            else [struct.unpack_from('<I', out, i * 4)[0] for i in range(count)]

    def _dir_table_end(self):
        cands = [self.id_start]
        cands += self._index_positions(self.id_start, self.id_count, 4)
        if self.frag_count:
            cands.append(self.frag_start)
            cands += self._index_positions(self.frag_start, self.frag_count, 16)
        if self.export_start != INVALID:
            cands.append(self.export_start)
            cands += self._index_positions(self.export_start, self.inode_count, 8)
        return min(c for c in cands if c > self.dir_start)

    def _meta_pos(self, offsets, ref, what):
        block, off = ref >> 16, ref & 0xFFFF
        if block not in offsets:
            raise SquashError('bad %s reference %#x' % (what, ref))
        return offsets[block] + off

    # ---------- inodes ----------
    def _read_inode(self, ref, parent):
        if ref in self._cache:
            node = self._cache[ref]
            return node
        b = self.inode_bytes
        p = self._meta_pos(self.inode_map, ref, 'inode')
        itype, mode, uid, gid, mtime, ino = struct.unpack_from('<HHHHII', b, p)
        p += 16
        kind = itype if itype <= 7 else itype - 7
        node = Node(kind, mode, self.ids[uid], self.ids[gid], mtime)
        self._cache[ref] = node

        if itype == 1:
            start, nlink, fsize, off, _parent = struct.unpack_from('<IIHHI', b, p)
            self._read_dir(node, start, off, fsize)
        elif itype == 8:
            nlink, fsize, start, _parent, _icount, off, _x = struct.unpack_from('<IIIIHHI', b, p)
            self._read_dir(node, start, off, fsize)
        elif itype in (2, 9):
            if itype == 2:
                bstart, frag, foff, fsize = struct.unpack_from('<IIII', b, p)
                p += 16
                sparse, nlink = 0, 1
            else:
                bstart, fsize, sparse, nlink, frag, foff, _x = struct.unpack_from('<QQQIIII', b, p)
                p += 40
            if frag == NOFRAG:
                nblocks = (fsize + self.block_size - 1) // self.block_size
            else:
                nblocks = fsize // self.block_size
            node.blocks = list(struct.unpack_from('<%dI' % nblocks, b, p))
            node.blocks_start, node.frag, node.frag_off, node.size = bstart, frag, foff, fsize
            node.sparse, node.nlink = sparse, nlink
        elif itype in (3, 10):
            nlink, tsize = struct.unpack_from('<II', b, p)
            node.target = b[p + 8:p + 8 + tsize]
            node.nlink = nlink
        elif itype in (4, 5, 11, 12):
            node.nlink, node.rdev = struct.unpack_from('<II', b, p)
        elif itype in (6, 7, 13, 14):
            node.nlink, = struct.unpack_from('<I', b, p)
        else:
            raise SquashError('unknown inode type %d' % itype)
        return node

    def _read_dir(self, node, start, off, fsize):
        size = fsize - 3
        if size <= 0:
            return
        b = self.dir_bytes
        p = self._meta_pos(self.dir_map, (start << 16) | off, 'directory')
        end = p + size
        while p < end:
            count, iblock, base = struct.unpack_from('<III', b, p)
            p += 12
            for _ in range(count + 1):
                eoff, _delta, _etype, nsize = struct.unpack_from('<HhHH', b, p)
                p += 8
                name = b[p:p + nsize + 1]
                p += nsize + 1
                child = self._read_inode((iblock << 16) | eoff, node)
                if child.kind == DIR:
                    child.parent = node
                node.children[name] = child

    # ---------- data access (for verification) ----------
    def read_file(self, node):
        if node.newdata is not None:
            return node.newdata
        out = bytearray()
        pos = node.blocks_start
        for bs in node.blocks:
            size = bs & ~BLK_UNCOMP
            if size == 0:   # sparse block
                out += bytes(min(self.block_size, node.size - len(out)))
                continue
            raw = self.data[pos:pos + size]
            out += raw if bs & BLK_UNCOMP else self._decompress(raw)
            pos += size
        if node.frag != NOFRAG:
            fstart, fsize, _ = self.frags[node.frag]
            size = fsize & ~BLK_UNCOMP
            raw = self.data[fstart:fstart + size]
            block = raw if fsize & BLK_UNCOMP else self._decompress(raw)
            out += block[node.frag_off:node.frag_off + node.size - len(out)]
        return bytes(out[:node.size])

    # ---------- editing ----------
    def lookup(self, path):
        node = self.root
        for part in [p for p in path.strip('/').split('/') if p]:
            if node.kind != DIR or part.encode() not in node.children:
                return None
            node = node.children[part.encode()]
        return node

    def _parent_dir(self, path, mtime):
        parts = [p for p in path.strip('/').split('/') if p]
        node = self.root
        for part in parts[:-1]:
            key = part.encode()
            child = node.children.get(key)
            if child is None:
                child = Node(DIR, 0o755, 0, 0, mtime)
                child.parent = node
                node.children[key] = child
            elif child.kind != DIR:
                raise SquashError('%s is not a directory' % part)
            node = child
        return node, parts[-1].encode()

    def add_file(self, path, data, mode=0o644, mtime=None):
        mtime = self.mod_time if mtime is None else mtime
        parent, name = self._parent_dir(path, mtime)
        n = Node(FILE, mode, 0, 0, mtime)
        n.newdata, n.size = bytes(data), len(data)
        parent.children[name] = n

    def add_symlink(self, path, target, mtime=None):
        mtime = self.mod_time if mtime is None else mtime
        parent, name = self._parent_dir(path, mtime)
        n = Node(SYMLINK, 0o777, 0, 0, mtime)
        n.target = target.encode()
        parent.children[name] = n

    # ---------- writing ----------
    def build(self):
        out = bytearray(self.data[:self.inode_start])  # superblock + all existing data, verbatim

        # ids
        ids = list(self.ids)

        def id_index(v):
            if v not in ids:
                ids.append(v)
            return ids.index(v)

        # append data of new files (uncompressed blocks)
        def walk(node, seen):
            if id(node) in seen:
                return
            seen.add(id(node))
            if node.kind == DIR:
                for c in node.children.values():
                    walk(c, seen)
            elif node.kind == FILE and node.newdata is not None:
                node.blocks_start = len(out) if node.newdata else 0
                node.blocks, node.frag, node.frag_off = [], NOFRAG, 0
                for i in range(0, len(node.newdata), self.block_size):
                    chunk = node.newdata[i:i + self.block_size]
                    out.extend(chunk)
                    node.blocks.append(len(chunk) | BLK_UNCOMP)
        walk(self.root, set())

        # inode numbers: unique nodes, depth first
        order, seen = [], set()

        def number(node):
            if id(node) in seen:
                return
            seen.add(id(node))
            order.append(node)
            if node.kind == DIR:
                for k in sorted(node.children):
                    number(node.children[k])
        number(self.root)
        for i, n in enumerate(order, 1):
            n.ino, n.ref = i, None
        inode_count = len(order)

        # link counts
        links = {}
        def count_links(node):
            for c in node.children.values():
                links[id(c)] = links.get(id(c), 0) + 1
                if c.kind == DIR:
                    count_links(c)
        count_links(self.root)

        itab, dtab = MetaWriter(), MetaWriter()

        def write_inode(node, parent_ino):
            if node.ref is not None:
                return node.ref
            uid, gid = id_index(node.uid), id_index(node.gid)
            common = lambda t: struct.pack('<HHHHII', t, node.mode & 0xFFFF, uid, gid, node.mtime, node.ino)
            if node.kind == DIR:
                for k in sorted(node.children):
                    c = node.children[k]
                    if c.kind == DIR:
                        write_inode(c, node.ino)
                    else:
                        write_inode(c, node.ino)
                listing = build_listing(node)
                dref = dtab.write(listing)
                dstart, doff = dref >> 16, dref & 0xFFFF
                nlink = 2 + sum(1 for c in node.children.values() if c.kind == DIR)
                fsize = len(listing) + 3
                if fsize <= 0xFFFF:
                    body = common(1) + struct.pack('<IIHHI', dstart, nlink, fsize, doff, parent_ino)
                else:
                    body = common(8) + struct.pack('<IIIIHHI', nlink, fsize, dstart, parent_ino, 0, doff, 0xFFFFFFFF)
            elif node.kind == FILE:
                nlink = max(links.get(id(node), 1), 1)
                blist = struct.pack('<%dI' % len(node.blocks), *node.blocks)
                if nlink == 1 and node.sparse == 0 and node.blocks_start < 2**32 and node.size < 2**32:
                    body = common(2) + struct.pack('<IIII', node.blocks_start, node.frag, node.frag_off, node.size) + blist
                else:
                    body = common(9) + struct.pack('<QQQIIII', node.blocks_start, node.size, node.sparse, nlink,
                                                    node.frag, node.frag_off, 0xFFFFFFFF) + blist
            elif node.kind == SYMLINK:
                body = common(3) + struct.pack('<II', max(links.get(id(node), 1), 1), len(node.target)) + node.target
            elif node.kind in (BLKDEV, CHRDEV):
                body = common(node.kind) + struct.pack('<II', max(links.get(id(node), 1), 1), node.rdev)
            else:
                body = common(node.kind) + struct.pack('<I', max(links.get(id(node), 1), 1))
            node.ref = itab.write(body)
            return node.ref

        def build_listing(node):
            out_l = bytearray()
            entries = [(k, node.children[k]) for k in sorted(node.children)]
            i = 0
            while i < len(entries):
                block = entries[i][1].ref >> 16
                base = entries[i][1].ino
                group = []
                while i < len(entries) and len(group) < 256:
                    c = entries[i][1]
                    if c.ref >> 16 != block or not -32768 <= c.ino - base <= 32767:
                        break
                    group.append(entries[i])
                    i += 1
                out_l += struct.pack('<III', len(group) - 1, block, base)
                for name, c in group:
                    if not 1 <= len(name) <= 256:
                        raise SquashError('bad file name length')
                    out_l += struct.pack('<HhHH', c.ref & 0xFFFF, c.ino - base, c.kind, len(name) - 1) + name
            return bytes(out_l)

        root_ref = write_inode(self.root, inode_count + 1)

        inode_start = len(out)
        out += itab.finish()
        dir_start = len(out)
        out += dtab.finish()

        frag_start = INVALID
        if self.frags:
            fdata = b''.join(struct.pack('<QII', *f) for f in self.frags)
            positions = []
            for i in range(0, len(fdata), META_SIZE):
                positions.append(len(out))
                chunk = fdata[i:i + META_SIZE]
                out += struct.pack('<H', len(chunk) | META_UNCOMP) + chunk
            frag_start = len(out)
            out += struct.pack('<%dQ' % len(positions), *positions)

        idata = struct.pack('<%dI' % len(ids), *ids)
        positions = []
        for i in range(0, len(idata), META_SIZE):
            positions.append(len(out))
            chunk = idata[i:i + META_SIZE]
            out += struct.pack('<H', len(chunk) | META_UNCOMP) + chunk
        id_start = len(out)
        out += struct.pack('<%dQ' % len(positions), *positions)

        bytes_used = len(out)
        flags = self.flags & ~F_EXPORTABLE
        sb = struct.pack(SB_FMT, MAGIC, inode_count, self.mod_time, self.block_size, len(self.frags),
                         self.comp, self.block_log, flags, len(ids), 4, 0, root_ref, bytes_used,
                         id_start, INVALID, inode_start, dir_start, frag_start, INVALID)
        out[0:SB_SIZE] = sb
        pad = (-len(out)) % 4096
        out += b'\0' * pad
        return bytes(out)


class MetaWriter:
    """Writes uncompressed metadata blocks; returns (block_pos << 16 | offset) refs."""

    def __init__(self):
        self.blocks = bytearray()
        self.cur = bytearray()

    def write(self, data):
        ref = (len(self.blocks) << 16) | len(self.cur)
        self.cur += data
        while len(self.cur) >= META_SIZE:
            chunk, self.cur = self.cur[:META_SIZE], self.cur[META_SIZE:]
            self.blocks += struct.pack('<H', META_SIZE | META_UNCOMP) + chunk
        return ref

    def finish(self):
        if self.cur:
            self.blocks += struct.pack('<H', len(self.cur) | META_UNCOMP) + self.cur
            self.cur = bytearray()
        return bytes(self.blocks)


def walk_files(node, prefix=b''):
    """Yield (path, node) for every entry below node."""
    for name in sorted(node.children):
        child = node.children[name]
        path = prefix + b'/' + name
        yield path, child
        if child.kind == DIR:
            yield from walk_files(child, path)


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
