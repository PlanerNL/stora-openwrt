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
