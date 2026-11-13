# -*- coding: utf-8 -*-
"""Cong cu chu cua Crimson Desert (ban 2.04+): doc / ghi file .paloc.

  python crimson_desert.py xuat  <thu_muc_nhom_0020> <ra.json>
      -> giai ma toan bo .paloc trong nhom, xuat {ten_file: [[khoa, chu], ...]}
  python crimson_desert.py dong_goi <thu_muc_nhom_0020> <ban_dich.json> <thu_muc_ra>
      -> ghi lai cac .paloc da dich (dang giai ma, boc LZ4 nhu game) de trinh nap mod dua vao game

ban_dich.json: {ten_file: {khoa: "chu tieng Viet", ...}, ...} – chi can cac cau da dich.

Dinh dang (xem Project: crimson_desert_dinh_dang.md):
  .paloc trong .paz: ChaCha20 (khoa tu hashlittle(ten_file, 0xC5EDE)) -> header 0x200 "paloc"
  -> 1 khoi LZ4 -> lap [8 byte][u32 len][khoa][u32 len][chu UTF-8] -> 4 byte duoi.
Chi DOC file game, khong sua file nao trong thu muc game.
"""
import json
import os
import struct
import sys

# ------------------------------------------------------------------ hashlittle + ChaCha20

def _rot(v, k):
    return ((v << k) | (v >> (32 - k))) & 0xFFFFFFFF


def hashlittle(data, initval=0):
    M = 0xFFFFFFFF
    n = len(data)
    a = b = c = (0xDEADBEEF + n + initval) & M
    o = 0
    while n > 12:
        a = (a + struct.unpack_from("<I", data, o)[0]) & M
        b = (b + struct.unpack_from("<I", data, o + 4)[0]) & M
        c = (c + struct.unpack_from("<I", data, o + 8)[0]) & M
        a = (a - c) & M; a ^= _rot(c, 4); c = (c + b) & M
        b = (b - a) & M; b ^= _rot(a, 6); a = (a + c) & M
        c = (c - b) & M; c ^= _rot(b, 8); b = (b + a) & M
        a = (a - c) & M; a ^= _rot(c, 16); c = (c + b) & M
        b = (b - a) & M; b ^= _rot(a, 19); a = (a + c) & M
        c = (c - b) & M; c ^= _rot(b, 4); b = (b + a) & M
        o += 12
        n -= 12
    if n == 0:
        return c
    duoi = data[o:] + b"\x00" * 12
    w0, w1, w2 = struct.unpack_from("<III", duoi, 0)
    if n >= 9:
        c = (c + (w2 & (M >> (8 * (12 - n))))) & M
    if n >= 8:
        b = (b + w1) & M
    elif n >= 5:
        b = (b + (w1 & (M >> (8 * (8 - n))))) & M
    if n >= 4:
        a = (a + w0) & M
    else:
        a = (a + (w0 & (M >> (8 * (4 - n))))) & M
    c ^= b; c = (c - _rot(b, 14)) & M
    a ^= c; a = (a - _rot(c, 11)) & M
    b ^= a; b = (b - _rot(a, 25)) & M
    c ^= b; c = (c - _rot(b, 16)) & M
    a ^= c; a = (a - _rot(c, 4)) & M
    b ^= a; b = (b - _rot(a, 14)) & M
    c ^= b; c = (c - _rot(b, 24)) & M
    return c


def khoa_iv(ten_file):
    seed = hashlittle(os.path.basename(ten_file).lower().encode("utf-8"), 0x000C5EDE)
    iv = struct.pack("<I", seed) * 4
    goc = seed ^ 0x60616263
    khoa = b"".join(struct.pack("<I", goc ^ d) for d in (
        0, 0x0A0A0A0A, 0x0C0C0C0C, 0x06060606, 0x0E0E0E0E, 0x0A0A0A0A, 0x06060606, 0x02020202))
    return khoa, iv


def chacha20(du_lieu, ten_file):
    khoa, iv = khoa_iv(ten_file)
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
        return Cipher(algorithms.ChaCha20(khoa, iv), mode=None).encryptor().update(du_lieu)
    except ImportError:
        return _chacha20_python(du_lieu, khoa, iv)


def _chacha20_python(du_lieu, khoa, iv):
    M = 0xFFFFFFFF
    k = list(struct.unpack("<8I", khoa))
    dem, *nonce = struct.unpack("<4I", iv)
    ra = bytearray(len(du_lieu))
    for khoi in range(0, len(du_lieu), 64):
        s = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574] + k + [(dem + khoi // 64) & M] + nonce
        x = s[:]
        for _ in range(10):
            for a, b, c, d in ((0, 4, 8, 12), (1, 5, 9, 13), (2, 6, 10, 14), (3, 7, 11, 15),
                               (0, 5, 10, 15), (1, 6, 11, 12), (2, 7, 8, 13), (3, 4, 9, 14)):
                x[a] = (x[a] + x[b]) & M; x[d] = _rot(x[d] ^ x[a], 16)
                x[c] = (x[c] + x[d]) & M; x[b] = _rot(x[b] ^ x[c], 12)
                x[a] = (x[a] + x[b]) & M; x[d] = _rot(x[d] ^ x[a], 8)
                x[c] = (x[c] + x[d]) & M; x[b] = _rot(x[b] ^ x[c], 7)
        dong = struct.pack("<16I", *((x[i] + s[i]) & M for i in range(16)))
        doan = du_lieu[khoi:khoi + 64]
        ra[khoi:khoi + len(doan)] = bytes(p ^ q for p, q in zip(doan, dong))
    return bytes(ra)

# ------------------------------------------------------------------ LZ4 khoi

def lz4_giai_nen(src, co_goc):
    dst = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok = src[i]; i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]; i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += 4
        bd = len(dst) - off
        if off >= ml:
            dst += dst[bd:bd + ml]
        else:
            for t in range(ml):
                dst.append(dst[bd + t])
    if len(dst) != co_goc:
        raise ValueError("LZ4: sai kích thước sau giải nén")
    return bytes(dst)


def lz4_nen(du_lieu):
    """LZ4 hop le, nhanh, ti le nen vua phai (bang bam 4 byte)."""
    try:
        import lz4.block
        return lz4.block.compress(du_lieu, store_size=False)
    except ImportError:
        pass
    n = len(du_lieu)
    ra = bytearray()
    bang = {}
    i = anchor = 0
    gioi_han = n - 12

    def ghi(lit_tu, lit_den, off, ml):
        lit = lit_den - lit_tu
        tok_l = 15 if lit >= 15 else lit
        tok_m = 0 if ml is None else (15 if ml - 4 >= 15 else ml - 4)
        ra.append((tok_l << 4) | tok_m)
        if lit >= 15:
            r = lit - 15
            while r >= 255:
                ra.append(255); r -= 255
            ra.append(r)
        ra.extend(du_lieu[lit_tu:lit_den])
        if ml is not None:
            ra.extend(struct.pack("<H", off))
            if ml - 4 >= 15:
                r = ml - 4 - 15
                while r >= 255:
                    ra.append(255); r -= 255
                ra.append(r)

    while i < gioi_han:
        k = du_lieu[i:i + 4]
        j = bang.get(k)
        bang[k] = i
        if j is not None and i - j < 65535:
            ml = 4
            while i + ml < n - 5 and du_lieu[j + ml] == du_lieu[i + ml]:
                ml += 1
            ghi(anchor, i, i - j, ml)
            i += ml
            anchor = i
        else:
            i += 1
    ghi(anchor, n, 0, None)
    return bytes(ra)

# ------------------------------------------------------------------ PAMT (2.04+)

def _varint(d, o):
    v = s = 0
    while True:
        b = d[o]; o += 1
        v |= (b & 0x7F) << s; s += 7
        if b < 0x80:
            return v, o


def _cay(d, o, co):
    dau, nut = o, {}
    while o < dau + co:
        vt = o - dau
        lui, o2 = _varint(d, o)
        dl = d[o2]
        nut[vt] = (vt - lui if lui else None, d[o2 + 1:o2 + 1 + dl].decode("utf-8", "replace"))
        o = o2 + 1 + dl

    def duong(r):
        ds = []
        while r is not None:
            p, t = nut[r]
            ds.append(t)
            r = p
        return "".join(reversed(ds))
    return nut, duong, o


def doc_pamt(duong_dan):
    d = open(duong_dan, "rb").read()
    o = 4
    so_paz = struct.unpack_from("<I", d, o)[0]; o += 12
    for i in range(so_paz):
        o += 8 + (4 if i < so_paz - 1 else 0)
    co = struct.unpack_from("<I", d, o)[0]; o += 4
    _, _, o = _cay(d, o, co)
    co = struct.unpack_from("<I", d, o)[0]; o += 4
    nut, duong, o = _cay(d, o, co)
    so_tm = struct.unpack_from("<I", d, o)[0]; o += 8 + so_tm * 16
    ds = []
    while o + 20 <= len(d):
        ten, vt, nen, goc, co_bit = struct.unpack_from("<IIIII", d, o)
        if ten not in nut:
            break
        ds.append({"ten": duong(ten), "vt": vt, "nen": nen, "goc": goc, "co": co_bit, "paz": co_bit & 0xFF})
        o += 20
    return ds

def doc_pamt_day_du(duong_dan):
    """Moi file kem thu muc, duoi file, kieu nen/ma hoa (nhom nhieu thu muc, VD 0006 am thanh)."""
    d = open(duong_dan, "rb").read()
    o = 4
    so_paz = struct.unpack_from("<I", d, o)[0]; o += 12
    for i in range(so_paz):
        o += 8 + (4 if i < so_paz - 1 else 0)
    co = struct.unpack_from("<I", d, o)[0]; o += 4
    nut_tm, duong_tm, o = _cay(d, o, co)
    co = struct.unpack_from("<I", d, o)[0]; o += 4
    nut, duong, o = _cay(d, o, co)
    so_tm = struct.unpack_from("<I", d, o)[0]; o += 8
    cac_tm = [struct.unpack_from("<IIII", d, o + 16 * i) for i in range(so_tm)]
    o += so_tm * 16
    ds = []
    while o + 20 <= len(d):
        ten, vt, nen, goc, co_bit = struct.unpack_from("<IIIII", d, o)
        if ten not in nut:
            break
        ds.append({"ten": duong(ten), "vt": vt, "nen": nen, "goc": goc, "paz": co_bit & 0xFFFF,
                   "kieu_nen": (co_bit >> 16) & 0x0F, "ma_hoa": (co_bit >> 20) & 0x0F, "duoi_so": co_bit >> 24})
        o += 20
    duoi = [""]
    if o + 4 <= len(d):
        duoi = d[o + 4:].split(b"\x00")
        duoi = [x.decode("ascii", "replace") for x in duoi]
    for nut_tm_vt, dau, so, _ in cac_tm:
        if so and nut_tm_vt in nut_tm:
            tm = duong_tm(nut_tm_vt)
            for f in ds[dau:dau + so]:
                f["thu_muc"] = tm
    for f in ds:
        f.setdefault("thu_muc", "")
        f["duoi"] = duoi[f["duoi_so"]] if f["duoi_so"] < len(duoi) else ""
    return ds


def doc_tep(thu_muc_nhom, f):
    """Doc noi dung 1 file trong nhom (giai nen LZ4 neu can; file ma hoa thi giai ma theo ten)."""
    with open(os.path.join(thu_muc_nhom, f"{f['paz']}.paz"), "rb") as fh:
        fh.seek(f["vt"])
        b = fh.read(f["nen"])
    if f["ma_hoa"]:
        b = chacha20(b, f["ten"] + f.get("duoi", ""))
    if f["kieu_nen"] == 2:
        b = lz4_giai_nen(b, f["goc"])
    return b


def thong_tin_wem(b):
    """RIFF Wwise: -> dict(ma_codec, kenh, tan_so, giay)"""
    kq = {}
    if b[:4] not in (b"RIFF", b"RIFX"):
        return kq
    o = 12
    while o + 8 <= len(b):
        ten, co = b[o:o + 4], struct.unpack_from("<I", b, o + 4)[0]
        if ten == b"fmt ":
            ma, kenh, tan_so, bps = struct.unpack_from("<HHII", b, o + 8)
            kq.update(ma_codec=ma, kenh=kenh, tan_so=tan_so, bps=bps)
            if ma == 0xFFFF and co >= 0x18 + 4:
                try:
                    kq["mau"] = struct.unpack_from("<I", b, o + 8 + 0x18)[0]
                except struct.error:
                    pass
        o += 8 + co + (co & 1)
    if kq.get("mau") and kq.get("tan_so"):
        kq["giay"] = kq["mau"] / kq["tan_so"]
    elif kq.get("bps"):
        kq["giay"] = (len(b) - 44) / kq["bps"]
    kq["ten_codec"] = {0xFFFF: "Wwise Vorbis", 0xFFFE: "PCM", 0x0002: "ADPCM", 0x3041: "Opus"}.get(
        kq.get("ma_codec"), hex(kq.get("ma_codec", 0)))
    return kq


# ------------------------------------------------------------------ PALOC

def mo_boc(ban_giai_ma):
    """header 0x200 'paloc' + khoi LZ4 -> (header, noi_dung)"""
    if ban_giai_ma[:5] != b"paloc":
        raise ValueError("không phải file paloc (sai khóa giải mã?)")
    dai_khoi, dai_goc = struct.unpack_from("<II", ban_giai_ma, 9)
    return ban_giai_ma[:0x200], lz4_giai_nen(ban_giai_ma[0x200:0x200 + dai_khoi], dai_goc)


def boc(header, noi_dung):
    khoi = lz4_nen(noi_dung)
    h = bytearray(header[:0x200])
    struct.pack_into("<II", h, 9, len(khoi), len(noi_dung))
    return bytes(h) + khoi


def tach(noi_dung):
    """-> (danh sach [dau8, khoa, chu], duoi)"""
    o, ds = 0, []
    while o + 16 <= len(noi_dung):
        if struct.unpack_from("<I", noi_dung, o + 8)[0] > len(noi_dung):
            break
        dau = noi_dung[o:o + 8]; o += 8
        dk = struct.unpack_from("<I", noi_dung, o)[0]; o += 4
        k = noi_dung[o:o + dk].decode("utf-8"); o += dk
        dv = struct.unpack_from("<I", noi_dung, o)[0]; o += 4
        v = noi_dung[o:o + dv].decode("utf-8"); o += dv
        ds.append([dau, k, v])
    return ds, noi_dung[o:]


def ghep(ds, duoi):
    ra = bytearray()
    for dau, k, v in ds:
        kb, vb = k.encode("utf-8"), v.encode("utf-8")
        ra += dau + struct.pack("<I", len(kb)) + kb + struct.pack("<I", len(vb)) + vb
    return bytes(ra) + duoi


def doc_nhom(thu_muc):
    """-> {ten: {"header", "ds", "duoi", "duong_dan"}} cho moi .paloc trong nhom (VD 0020)."""
    kq = {}
    cac_paz = {}
    for f in doc_pamt(os.path.join(thu_muc, "0.pamt")):
        p = os.path.join(thu_muc, f"{f['paz']}.paz")
        if p not in cac_paz:
            cac_paz[p] = open(p, "rb")
        cac_paz[p].seek(f["vt"])
        ten = f["ten"] + ".paloc"
        header, noi_dung = mo_boc(chacha20(cac_paz[p].read(f["nen"]), ten))
        ds, duoi = tach(noi_dung)
        kq[f["ten"]] = {"header": header, "ds": ds, "duoi": duoi}
    for fh in cac_paz.values():
        fh.close()
    return kq


def ma_ngon_ngu(thu_muc):
    with open(os.path.join(thu_muc, "0.pamt"), "rb") as f:
        d = f.read(400)
    i = d.find(b"/binary__")
    j = d.find(b"/", i + 1)
    return d[j + 1:j + 1 + d[j - 1] - 1].decode("ascii", "replace") if i > 0 and j > 0 else "eng"


def dong_goi(nhom, ban_dich, thu_muc_ra, ngon_ngu="eng"):
    """Ghi .paloc da dich (giai ma, boc LZ4) vao thu_muc_ra/gamedata/stringtable/binary__/<ngon_ngu>/"""
    dich = os.path.join(thu_muc_ra, "gamedata", "stringtable", "binary__", ngon_ngu)
    os.makedirs(dich, exist_ok=True)
    thong_ke = {}
    for ten, cau in ban_dich.items():
        if ten not in nhom or not cau:
            continue
        g = nhom[ten]
        so = 0
        ds_moi = []
        for dau, k, v in g["ds"]:
            if k in cau and cau[k] != v:
                v = cau[k]
                so += 1
            ds_moi.append([dau, k, v])
        with open(os.path.join(dich, ten + ".paloc"), "wb") as f:
            f.write(boc(g["header"], ghep(ds_moi, g["duoi"])))
        thong_ke[ten] = so
    return thong_ke


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "xuat":
        nhom = doc_nhom(sys.argv[2])
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            json.dump({t: [[k, v] for _, k, v in g["ds"]] for t, g in nhom.items()}, f, ensure_ascii=False)
        print(f"Đã xuất {sum(len(g['ds']) for g in nhom.values())} câu từ {len(nhom)} file")
    elif len(sys.argv) >= 5 and sys.argv[1] == "dong_goi":
        nhom = doc_nhom(sys.argv[2])
        with open(sys.argv[3], encoding="utf-8") as f:
            ban_dich = json.load(f)
        print(dong_goi(nhom, ban_dich, sys.argv[4], ma_ngon_ngu(sys.argv[2])))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
