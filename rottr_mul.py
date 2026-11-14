# -*- coding: utf-8 -*-
"""Rise of the Tomb Raider (Foundation) – doc / ghi file .mul (luong da kenh: am thanh + phu de + chuyen dong phim).

Dinh dang theo TR Reboot Mod Tools (arcusmaximus, MIT) – Shared/Cdc/MultiplexStream.cs, MultiplexStreamBuilder.cs:
  header co dinh (Hertz, ..., so kenh am thanh, co phim, co phu de, ...) -> can 0x1000/0x2000
  -> chuoi goi [kieu i32][co i32][8 byte] (+noi dung, can 0x10):
       0 = am thanh: moi kenh [co i32][kenh i32][8 byte][du lieu] – du lieu cac goi noi lai = 1 file FSB4 (MP3) / kenh
       1 = phim (cine): goi dau co header "CINE", roi [co khung][so khung][gia tri kenh][phu de]
     phu de: [co i32] roi lap "ngon_ngu\\r" "chu\\r" (UTF-8).
Am thanh: FSB4, 1 mau, ma MP3 44.1 kHz (header FSB 0x30 + mau 0x50, so mau tai 0x50).
"""
import struct

try:
    import numpy as np
except Exception:          # chay cham hon nhung van dung
    np = None

HDR = struct.Struct("<iiiiiiiiiiiiiif12f12f12ii1024i1024h1024s12s")   # 7388 byte
CINE = 0x43494E45
GOI_AM, GOI_PHIM = 0, 1


class LoiMul(Exception):
    pass


def _can(n, a):
    return (n + a - 1) // a * a


class GoiPhim:
    __slots__ = ("header", "khung", "kenh", "phu_de", "tho", "duoi")

    def __init__(self):
        self.header = None
        self.khung = 0
        self.kenh = b""
        self.phu_de = None      # dict ngon_ngu -> chu (giu thu tu)
        self.tho = None         # goi chi co khung < 0
        self.duoi = b""         # byte thua cuoi khung (game de 1 byte 0 sau phu de)


class GoiAm:
    __slots__ = ("du_lieu", "dem")

    def __init__(self, du_lieu, dem=None):
        self.du_lieu = du_lieu   # list bytes theo kenh
        self.dem = dem           # 8 byte du tru moi kenh (game de rac 0xCD) – chi de ghi lai y nguyen


class Mul:
    def __init__(self, b=None):
        self.hdr = None
        self.goi = []           # list (kieu, doi_tuong | (kieu_la, bytes))
        if b is not None:
            self.doc(b)

    # ------------------------------------------------------------- doc
    @property
    def so_kenh(self):
        return self.hdr[3]

    @property
    def co_phim(self):
        return self.hdr[8] != 0

    @property
    def co_phu_de(self):
        return self.hdr[9] != 0

    def doc(self, b):
        if len(b) < HDR.size:
            raise LoiMul("file .mul quá ngắn")
        self.hdr = list(HDR.unpack_from(b, 0))
        if not 0 <= self.so_kenh <= 12:
            raise LoiMul("số kênh âm thanh sai")
        self._dau = b[:0x2000]
        vt = 0x2000
        st = {"kenh": None, "ver": 0, "i32": None, "b": b}
        while vt + 16 <= len(b):
            kieu, co = struct.unpack_from("<ii", b, vt)
            nd = vt + 16
            if kieu == GOI_AM:
                ds, dem = [], []
                p = nd
                for i in range(self.so_kenh):
                    n, k = struct.unpack_from("<ii", b, p)
                    if k != i:
                        raise LoiMul("kênh âm thanh sai thứ tự")
                    ds.append(b[p + 16:p + 16 + n])
                    dem.append(b[p + 8:p + 16])
                    p += 16 + n
                self.goi.append((GOI_AM, GoiAm(ds, dem)))
            elif kieu == GOI_PHIM:
                self.goi.append((GOI_PHIM, self._doc_phim(b, nd, st)))
            else:
                self.goi.append((kieu, b[nd:nd + co]))
            vt = _can(nd + co, 0x10)

    def _doc_phim(self, b, p, st):
        g = GoiPhim()
        if st["kenh"] is None:
            p0 = p
            if struct.unpack_from("<i", b, p)[0] != CINE:
                raise LoiMul("goi phim sai")
            ver, _co, _so = struct.unpack_from("<iii", b, p + 4)
            st["ver"] = ver
            p += 16 + 0x40 + 4
            n = 0
            na = struct.unpack_from("<i", b, p)[0]; p += 4 + 0xC * na; n += 9 * na
            ns = struct.unpack_from("<i", b, p)[0]; p += 4
            for _ in range(ns):
                p += 4
                if ver == 13:
                    p += 4
                nb = struct.unpack_from("<i", b, p)[0]; p += 8 + 0x40 * nb; n += 3 + 14 * nb
                nl = struct.unpack_from("<i", b, p)[0]; p += 8 + 0x18 * nl; n += 10 * nl
                nc = struct.unpack_from("<i", b, p)[0]; p += 8; n += nc
                if ver == 14:
                    nbs = struct.unpack_from("<i", b, p)[0]; p += 8; n += nbs
            ncam = struct.unpack_from("<i", b, p)[0]; p += 4 + 4 * ncam; n += 16 * ncam
            p += 4
            nt = struct.unpack_from("<i", b, p)[0]; p += 4 + 8 * nt; n += nt
            p += 4                       # so phu de
            p += 0x1C * ns
            if ver == 14:
                p += 0x1C * ncam
                if ncam > 0:
                    ncc = struct.unpack_from("<i", b, p)[0]; p += 4 + 4 * ncc
            g.header = b[p0:p]
            if np is not None:
                st["kenh"] = (np.zeros(n, np.int64), np.zeros(n, bool))
                st["i32"] = np.frombuffer(b, "<i4", count=len(b) // 4)
            else:
                st["kenh"] = [[0, False] for _ in range(n)]
        co_khung, g.khung = struct.unpack_from("<ii", b, p)
        het_khung = p + 4 + co_khung
        p += 8
        if g.khung < 0:
            return g
        p0 = p
        if st["i32"] is not None and p % 4 == 0:
            con, moi_khung = st["kenh"]
            if len(con):
                het = con == 0
                co = np.where(het, 8, np.where(moi_khung, 4, 0))
                vt = np.cumsum(co) - co
                chi = np.nonzero(het)[0]
                if len(chi):
                    run = st["i32"][(p + vt[chi]) // 4].astype(np.int64)
                    con[chi] = run & 0xFFFFFF
                    moi_khung[chi] = ((run >> 24) & 0xFF) != 0
                con -= 1
                p += int(co.sum())
        else:
            if not isinstance(st["kenh"], list):
                con, moi_khung = st["kenh"]
                st["kenh"] = [[int(a), bool(c)] for a, c in zip(con, moi_khung)]
                st["i32"] = None
            for c in st["kenh"]:
                if c[0] == 0:
                    run = struct.unpack_from("<i", b, p)[0]; p += 4
                    c[0] = run & 0xFFFFFF
                    c[1] = ((run >> 24) & 0xFF) != 0
                    p += 4
                elif c[1]:
                    p += 4
                c[0] -= 1
        g.kenh = b[p0:p]
        n = struct.unpack_from("<i", b, p)[0]
        p += 4
        g.duoi = b[p + n:het_khung]
        if n:
            ds = b[p:p + n].split(b"\r")
            g.phu_de = {}
            for i in range(0, len(ds) - 1, 2):
                g.phu_de[ds[i].decode("utf-8", "replace")] = ds[i + 1].decode("utf-8", "replace")
        return g

    # ------------------------------------------------------------- ghi
    def ghi(self):
        ra = bytearray(self._dau_moi())
        for kieu, g in self.goi:
            ra += struct.pack("<ii", kieu, 0) + b"\0" * 8
            nd = len(ra)
            if kieu == GOI_AM:
                for i, d in enumerate(g.du_lieu):
                    ra += struct.pack("<ii", len(d), i) + (g.dem[i] if g.dem else b"\0" * 8) + d
            elif kieu == GOI_PHIM:
                if g.header:
                    ra += g.header
                pk = len(ra)
                ra += struct.pack("<ii", 0, g.khung)
                if g.khung >= 0:
                    ra += g.kenh
                    pd = len(ra)
                    ra += b"\0\0\0\0"
                    if g.phu_de:
                        for k, v in g.phu_de.items():
                            ra += k.encode("utf-8") + b"\r" + v.encode("utf-8") + b"\r"
                    struct.pack_into("<i", ra, pd, len(ra) - pd - 4)
                    ra += g.duoi
                struct.pack_into("<i", ra, pk, len(ra) - pk - 4)
                ra += b"\0" * (_can(len(ra), 0x10) - len(ra))
            else:
                ra += g
            struct.pack_into("<i", ra, nd - 12, len(ra) - nd)
            ra += b"\0" * (_can(len(ra), 0x10) - len(ra))
        return bytes(ra)

    def _dau_moi(self):
        """Header: giu nguyen file goc; neu da thay am thanh thi cap nhat so mau, so goi am, co du lieu kenh."""
        if not getattr(self, "_da_thay", False):
            return self._dau
        h = list(self.hdr)
        fsb = self.fsb_kenh()
        so_mau = min((struct.unpack_from("<i", f, 0x50)[0] for f in fsb if len(f) >= 0x54), default=h[2])
        if 0 < h[2] < 0x7FFFFFFF:
            h[2] = min(h[2], so_mau)
        vt_mk = 1 + 14 + 36 + 1          # sau 15 so dau, 3 mang 12 phan tu, SpliceMarkersCount
        for i, f in enumerate(fsb):
            h[vt_mk + 1023 - i] = len(f)
        return HDR.pack(*h) + self._dau[HDR.size:0x2000]

    # ------------------------------------------------------------- am thanh
    def fsb_kenh(self):
        """Noi cac goi am thanh -> list bytes FSB (moi kenh 1 file)."""
        ra = [bytearray() for _ in range(self.so_kenh)]
        for k, g in self.goi:
            if k == GOI_AM:
                for i, d in enumerate(g.du_lieu):
                    if d != b"\xff\xfb":
                        ra[i] += d
        return [bytes(x) for x in ra]

    def thay_am_thanh(self, fsb_moi):
        """Thay am thanh, GIU NGUYEN bo cuc goi cua game (so goi, thu tu xen voi goi phim).
        fsb_moi: list bytes FSB4-MP3 (moi kenh). Ranh gioi goi moi = ranh gioi goc nhan ti le, bat vao dau khung MP3."""
        if len(fsb_moi) != self.so_kenh:
            raise LoiMul("số kênh không khớp")
        vi_tri = [i for i, (k, _) in enumerate(self.goi) if k == GOI_AM]
        if not vi_tri:
            raise LoiMul("file .mul không có âm thanh")
        for kenh in range(self.so_kenh):
            goc = [self.goi[i][1].du_lieu[kenh] for i in vi_tri]
            goc = [d if d != b"\xff\xfb" else b"" for d in goc]
            tong_goc = sum(len(d) for d in goc) or 1
            moi = fsb_moi[kenh]
            ti_le = len(moi) / tong_goc
            ranh, cong = [], 0
            for d in goc[:-1]:
                cong += len(d)
                ranh.append(cong)
            cat, truoc = [], 0
            for r in ranh:
                vt = min(max(int(round(r * ti_le)), truoc), len(moi))
                cat.append((truoc, vt))
                truoc = vt
            cat.append((truoc, len(moi)))
            for i, (a, b) in zip(vi_tri, cat):
                g = self.goi[i][1]
                g.du_lieu = list(g.du_lieu)
                g.du_lieu[kenh] = moi[a:b] if b > a else b"\xff\xfb"
        self._da_thay = True

    # ------------------------------------------------------------- phu de
    def phu_de(self):
        """-> list (chi_so_goi, dict ngon_ngu->chu)."""
        return [(i, g.phu_de) for i, (k, g) in enumerate(self.goi) if k == GOI_PHIM and g.phu_de]


# ------------------------------------------------------------- FSB4 (MP3)

def mp3_khung(mp3):
    """Tach cac khung MP3 (bo ID3, khung Xing/Info, byte 0 dem giua cac khung).
    -> list bytes moi khung. Chi nhan MPEG-1 Layer III 44.1 kHz, toc do bit co dinh hoac thay doi deu duoc."""
    d = mp3
    if d[:3] == b"ID3":
        n = (d[6] << 21) | (d[7] << 14) | (d[8] << 7) | d[9]
        d = d[10 + n:]
    if d[-128:-125] == b"TAG":
        d = d[:-128]
    BR = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    ra, vt, dau = [], 0, True
    while vt + 4 <= len(d):
        h = d[vt:vt + 4]
        br = BR[h[2] >> 4] if h[0] == 0xFF and (h[1] & 0xFE) == 0xFA else 0
        if br == 0 or (h[2] >> 2) & 3 != 0:
            j = d.find(b"\xff\xfb", vt + 1)
            if j < 0:
                break
            vt = j
            continue
        dai = 144000 * br // 44100 + ((h[2] >> 1) & 1)
        if vt + dai > len(d):
            break
        khung = d[vt:vt + dai]
        vt += dai
        if dau:
            dau = False
            if b"Xing" in khung[:64] or b"Info" in khung[:64]:
                continue
        ra.append(khung)
    if not ra:
        raise LoiMul("file MP3 không đúng định dạng MPEG-1 Layer III 44.1 kHz")
    return ra


def tao_fsb4(mp3, ten, mau_goc=None):
    """Boc du lieu MP3 thanh FSB4 giong file game (1 mau, MP3 mono 44.1 kHz). mau_goc: FSB goc de chep header/hash."""
    ds = mp3_khung(mp3)
    so_mau = len(ds) * 1152
    khung = b"".join(k + b"\0" * (-len(k) % 4) for k in ds)   # FMOD can moi khung theo 4 byte
    du_lieu = khung + b"\0" * (-len(khung) % 32)                # vung du lieu can 32 byte
    if mau_goc and len(mau_goc) >= 0x80:
        dau = bytearray(mau_goc[:0x80])
    else:
        dau = bytearray(0x80)
        dau[0:4] = b"FSB4"
        struct.pack_into("<IIIII", dau, 4, 1, 0x50, 0, 0x40000, 0x40)
        struct.pack_into("<H", dau, 0x30, 0x50)
        struct.pack_into("<IIIIIiHhHH", dau, 0x50, 0, 0, 0, 0, 0x10000200, 44100, 255, 128, 128, 1)
        struct.pack_into("<ffiHh", dau, 0x70, 1.0, 10000.0, 0, 0, 0)
    struct.pack_into("<I", dau, 0x0C, len(du_lieu))
    ten_b = ten.encode("ascii", "replace")[:29]
    dau[0x32:0x50] = ten_b + b"\0" * (30 - len(ten_b))
    struct.pack_into("<IIII", dau, 0x50, so_mau, len(khung), 0, so_mau - 1)
    return bytes(dau) + du_lieu


def fsb_thong_tin(fsb):
    """-> (ten_mau, so_mau, du_lieu_mp3)."""
    if fsb[:4] != b"FSB4":
        raise LoiMul("không phải FSB4")
    sh = struct.unpack_from("<I", fsb, 8)[0]
    ten = fsb[0x32:0x50].split(b"\0")[0].decode("ascii", "replace")
    so_mau = struct.unpack_from("<I", fsb, 0x50)[0]
    return ten, so_mau, fsb[0x30 + sh:]
