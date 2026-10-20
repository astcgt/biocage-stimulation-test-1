"""Minimal reader for FEBio .xplt plot files (format 3.x as written by FEBio 4): dictionary, surface names and
per-state surface (face) data. Chunk ids from FEBioPlot/FEBioPlotFile.h. Only what the validation needs.
"""
import struct, zlib
import numpy as np

ROOT, HEADER, HDR_COMPRESSION = 0x01000000, 0x01010000, 0x01010004
DICTIONARY, DIC_ITEM, DIC_TYPE, DIC_FMT, DIC_NAME = 0x01020000, 0x01020001, 0x01020002, 0x01020003, 0x01020004
DIC_GLOBAL, DIC_NODAL, DIC_DOMAIN, DIC_SURFACE = 0x01021000, 0x01023000, 0x01024000, 0x01025000
MESH, SURFACE_SECTION, SURFACE, SURFACE_HDR, SURFACE_ID, SURFACE_NAME = (0x01040000, 0x01043000, 0x01043100,
                                                                        0x01043101, 0x01043102, 0x01043104)
STATE, STATE_HEADER, STATE_TIME, STATE_DATA = 0x02000000, 0x02010000, 0x02010002, 0x02020000
DOMAIN_SECTION, DOMAIN, DOMAIN_HDR, DOM_ELEM_TYPE, DOM_PART_ID, DOM_ELEMS, DOM_NAME = (0x01042000, 0x01042100, 0x01042101,
                                                                                     0x01042102, 0x01042103, 0x01032104, 0x01032105)
DOM_ELEM_LIST, ELEMENT = 0x01042200, 0x01042201
ELEMENT_DATA = 0x02020400
VAR, VAR_ID, VAR_DATA, FACE_DATA = 0x02020001, 0x02020002, 0x02020003, 0x02020500
NCOMP = {0: 1, 1: 3, 2: 6, 3: 3, 4: 9, 5: 9}        # float, vec3f, mat3fs, mat3fd, tens4fs, mat3f


def _name(b):
    """FEBio 4 writes names as uint32 length + chars (older: fixed 64-byte, NUL padded)."""
    n = struct.unpack_from('<I', b, 0)[0]
    return b[4:4 + n].decode() if 0 < n <= len(b) - 4 else b.split(b'\0')[0].decode()


def chunks(buf, off=0, end=None):
    end = len(buf) if end is None else end
    while off + 8 <= end:
        cid, size = struct.unpack_from('<II', buf, off)
        if off + 8 + size > end:
            return                                   # truncated (file still being written)
        yield cid, buf[off + 8: off + 8 + size]
        off += 8 + size


def find(buf, cid):
    return [d for c, d in chunks(buf) if c == cid]


def read(path):
    raw = open(path, 'rb').read()
    assert struct.unpack_from('<I', raw, 0)[0] == 0x00464542, 'not an xplt file'
    body = raw[4:]
    out = dict(dict={}, surfaces={}, domains=[], states=[])
    compressed = False
    for cid, d in chunks(body):
        if cid == ROOT:
            for c2, d2 in chunks(d):
                if c2 == HEADER:
                    for c3, d3 in chunks(d2):
                        if c3 == HDR_COMPRESSION:
                            compressed = struct.unpack('<I', d3)[0] != 0
                elif c2 == DICTIONARY:
                    for sec_id, sec in chunks(d2):
                        items = []
                        for c3, item in chunks(sec):
                            if c3 != DIC_ITEM: continue
                            f = {c4: d4 for c4, d4 in chunks(item)}
                            items.append(dict(type=struct.unpack('<I', f[DIC_TYPE])[0], fmt=struct.unpack('<I', f[DIC_FMT])[0],
                                              name=f[DIC_NAME].split(b'\0')[0].decode()))
                        out['dict'][sec_id] = items
        elif cid == MESH:                                 # top-level sibling of ROOT in FEBio 4 files
            for c3, d3 in chunks(d):
                if c3 == DOMAIN_SECTION:
                    for c4, dom in chunks(d3):
                        if c4 != DOMAIN: continue
                        hdr = {c5: d5 for c5, d5 in chunks(find(dom, DOMAIN_HDR)[0])}
                        el = find(dom, DOM_ELEM_LIST)
                        ids = [struct.unpack_from('<I', e, 0)[0] for c6, e in chunks(el[0]) if c6 == ELEMENT] if el else []
                        out['domains'].append(dict(part=struct.unpack('<I', hdr[DOM_PART_ID])[0] if DOM_PART_ID in hdr else None,
                                                   name=_name(hdr[DOM_NAME]) if DOM_NAME in hdr else '',
                                                   n=struct.unpack('<I', hdr[DOM_ELEMS])[0] if DOM_ELEMS in hdr else len(ids),
                                                   elem_ids=np.array(ids)))
                if c3 != SURFACE_SECTION: continue
                for c4, s in chunks(d3):
                    if c4 != SURFACE: continue
                    hdr = {c5: d5 for c5, d5 in chunks(find(s, SURFACE_HDR)[0])}
                    sid = struct.unpack('<I', hdr[SURFACE_ID])[0]
                    out['surfaces'][sid] = _name(hdr[SURFACE_NAME]) if SURFACE_NAME in hdr else str(sid)
        elif cid == STATE:
            d = zlib.decompress(d) if compressed else d
            st = dict(time=None, face={}, elem={})
            for c2, d2 in chunks(d):
                if c2 == STATE_HEADER:
                    for c3, d3 in chunks(d2):
                        if c3 == STATE_TIME: st['time'] = struct.unpack('<f', d3)[0]
                elif c2 == STATE_DATA:
                    for c3, d3 in chunks(d2):
                        if c3 not in (FACE_DATA, ELEMENT_DATA): continue
                        sec = DIC_SURFACE if c3 == FACE_DATA else DIC_DOMAIN
                        target = st['face'] if c3 == FACE_DATA else st['elem']
                        for c4, v in chunks(d3):
                            if c4 != VAR: continue
                            f = {c5: d5 for c5, d5 in chunks(v)}
                            vid = struct.unpack('<I', f[VAR_ID])[0]
                            item = out['dict'][sec][vid - 1]
                            data, o, regs = f[VAR_DATA], 0, {}
                            while o + 8 <= len(data):
                                rid, sz = struct.unpack_from('<II', data, o)
                                regs[rid] = np.frombuffer(data, '<f4', sz // 4, o + 8).reshape(-1, NCOMP[item['type']])
                                o += 8 + sz
                            target[item['name']] = regs
            out['states'].append(st)
    return out
