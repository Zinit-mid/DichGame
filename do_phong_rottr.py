"""Cong cu do phong chu (font) cua Rise of the Tomb Raider.

Quet tat ca goi .tiger cua game (ca phan nen CDRM), tim:
  * file Scaleform / Flash (GFX, CFX, FWS, CWS) va cac font ben trong (DefineFont2/3, DefineCompactedFont)
  * file font TrueType / OpenType nhung trong game
  * chuoi chu co nhac den "font" (ten file, ten font)
Ghi bao cao + mau file tim duoc ra mot thu muc (Desktop) de gui cho Claude phan tich.
"""
import bisect
import hashlib
import json
import mmap
import os
import re
import struct
import time
import zlib

MAGIC_CDRM = b"CDRM"
TEN_MOD = "viethoa_dichgame"

# chu tieng Viet can co (dung de kiem tra font co du dau khong)
CHU_VIET = "ăâđêôơưĂÂĐÊÔƠƯàảãáạằẳẵắặầẩẫấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ"
MA_VIET = sorted({ord(c) for c in CHU_VIET + CHU_VIET.upper()})

# dau hieu: GFX/CFX (Scaleform), FWS/CWS (Flash), TrueType/OpenType
MAU_FILE = re.compile(rb"(?:GFX|CFX|FWS|CWS)[\x06-\x14]|(?:\x00\x01\x00\x00|OTTO|true)\x00[\x04-\x28]")
MAU_CHU = re.compile(rb"[Ff]ont|FONT|\.ttf|\.otf|\.fnt|[Gg]lyph")
IN_DUOC = frozenset(range(0x20, 0x7F))

TEN_THE = {48: "DefineFont2", 75: "DefineFont3", 1005: "DefineCompactedFont", 88: "DefineFontName",
           56: "ExportAssets", 57: "ImportAssets", 71: "ImportAssets2", 13: "DefineFontInfo",
           62: "DefineFontInfo2", 73: "DefineFontAlignZones", 1000: "ExporterInfo", 1001: "DefineExternalImage",
           1003: "FontTextureInfo", 1009: "DefineExternalImage2"}


def _bao_viet(cac_ma):
    co = set(cac_ma)
    du = sum(1 for m in MA_VIET if m in co)
    return du, len(MA_VIET)


# ------------------------------------------------------------------ CDRM

def giai_cdrm(b, vt):
    """Giai nen 1 khoi CDRM bat dau o vt trong b (mmap/bytes). -> (du_lieu, vt_ket_thuc) hoac None."""
    if b[vt:vt + 4] != MAGIC_CDRM:
        return None
    so_khuc = struct.unpack_from("<i", b, vt + 8)[0]
    if not 0 < so_khuc < 200000:
        return None
    bang = vt + 16
    p = (bang + 8 * so_khuc + 0xF) & ~0xF
    ra = bytearray()
    n = len(b)
    for i in range(so_khuc):
        goc, nen = struct.unpack_from("<ii", b, bang + 8 * i)
        loai, goc = goc & 0xFF, goc >> 8
        if nen <= 0 or goc <= 0 or p + nen > n or goc > (64 << 20):
            return None
        k = b[p:p + nen]
        if nen == goc:
            ra += k
        else:
            try:
                ra += zlib.decompress(k)
            except zlib.error:
                return None
        p = (p + nen + 0xF) & ~0xF
    return bytes(ra), p


# ------------------------------------------------------------------ SWF / GFX

class _Bit:
    def __init__(self, b, p):
        self.b, self.p, self.bit = b, p, 0

    def doc(self, n):
        v = 0
        for _ in range(n):
            byte = self.b[self.p]
            v = (v << 1) | ((byte >> (7 - self.bit)) & 1)
            self.bit += 1
            if self.bit == 8:
                self.bit, self.p = 0, self.p + 1
        return v

    def het(self):
        return self.p + (1 if self.bit else 0)


def doc_gfx(b, vt=0):
    """Phan tich file GFX/SWF bat dau o vt. -> dict hoac None."""
    sig = b[vt:vt + 3]
    if len(b) < vt + 8:
        return None
    ban = b[vt + 3]
    dai = struct.unpack_from("<I", b, vt + 4)[0]
    if not 30 <= dai <= (200 << 20):
        return None
    if sig in (b"CFX", b"CWS"):
        try:
            d = zlib.decompressobj().decompress(bytes(b[vt + 8:vt + 8 + dai + 1024]), dai)
        except zlib.error:
            return None
        than = b"\0" * 8 + d
        goc = b"GFX" + bytes([ban]) + struct.pack("<I", len(than)) + d
    else:
        if vt + dai > len(b):
            return None
        than = bytes(b[vt:vt + dai])
        goc = than
    try:
        r = _Bit(than, 8)
        nb = r.doc(5)
        for _ in range(4):
            r.doc(nb)
        p = r.het() + 4
        the, phong, ten_xuat, nhap = {}, [], [], []
        while p + 2 <= len(than):
            ma_dai = struct.unpack_from("<H", than, p)[0]
            ma, n = ma_dai >> 6, ma_dai & 0x3F
            p += 2
            if n == 0x3F:
                n = struct.unpack_from("<I", than, p)[0]
                p += 4
            if p + n > len(than):
                break
            the[ma] = the.get(ma, 0) + 1
            d = than[p:p + n]
            if ma in (48, 75):
                phong.append(_doc_define_font(d, ma))
            elif ma == 1005:
                phong.append(_doc_compacted(d))
            elif ma == 56:
                c = struct.unpack_from("<H", d, 0)[0]
                q = 2
                for _ in range(c):
                    q += 2
                    e = d.index(b"\0", q)
                    ten_xuat.append(d[q:e].decode("latin-1"))
                    q = e + 1
            elif ma in (57, 71):
                e = d.index(b"\0")
                nhap.append(d[:e].decode("latin-1"))
            p += n
            if ma == 0:
                break
    except Exception as e:
        return {"loai": sig.decode(), "ban": ban, "dai": dai, "loi": str(e)[:80], "goc": goc}
    return {"loai": sig.decode(), "ban": ban, "dai": dai, "the": {TEN_THE.get(k, str(k)): v for k, v in the.items()},
            "phong": phong, "xuat": ten_xuat[:60], "nhap": nhap[:20], "goc": goc}


def _doc_define_font(d, ma):
    fid, co, lang, nl = struct.unpack_from("<HBBB", d, 0)
    ten = d[5:5 + nl].split(b"\0")[0].decode("latin-1", "replace")
    p = 5 + nl
    so = struct.unpack_from("<H", d, p)[0]
    p += 2
    rong = bool(co & 0x08)
    ma_rong = bool(co & 0x04)
    kq = {"the": TEN_THE[ma], "id": fid, "ten": ten, "so_glyph": so, "dam": bool(co & 1), "nghieng": bool(co & 2)}
    if so:
        if rong:
            bang = struct.unpack_from(f"<{so}I", d, p)
            ma_ofs = struct.unpack_from("<I", d, p + 4 * so)[0]
        else:
            bang = struct.unpack_from(f"<{so}H", d, p)
            ma_ofs = struct.unpack_from("<H", d, p + 2 * so)[0]
        q = p + ma_ofs
        cac = struct.unpack_from(f"<{so}H", d, q) if ma_rong else tuple(d[q:q + so])
        du, tong = _bao_viet(cac)
        kq["chu_viet"] = f"{du}/{tong}"
        kq["mau_chu"] = "".join(chr(c) for c in sorted(cac) if c >= 0x20)[:200]
    return kq


def _doc_compacted(d):
    # Scaleform DefineCompactedFont: id u16, roi du lieu font nen (ten font o dau)
    fid = struct.unpack_from("<H", d, 0)[0]
    chuoi = re.findall(rb"[\x20-\x7e]{3,}", d[2:200])
    return {"the": "DefineCompactedFont", "id": fid, "ten_doan": [c.decode() for c in chuoi[:3]], "co": len(d)}


# ------------------------------------------------------------------ TrueType

def doc_ttf(b, vt):
    try:
        so = struct.unpack_from(">H", b, vt + 4)[0]
        sr = struct.unpack_from(">H", b, vt + 6)[0]
        if sr != 16 * (1 << (so.bit_length() - 1)):
            return None
        bang = {}
        for i in range(so):
            tag, _, ofs, dai = struct.unpack_from(">4sIII", b, vt + 12 + 16 * i)
            if not re.fullmatch(rb"[\x20-\x7e]{4}", tag) or dai > (60 << 20):
                return None
            bang[tag.decode()] = (ofs, dai)
        if "cmap" not in bang or ("glyf" not in bang and "CFF " not in bang):
            return None
        het = max(o + d for o, d in bang.values())
        kq = {"loai": "TTF/OTF", "bang": sorted(bang), "dai": het, "ten": _ttf_ten(b, vt, bang)}
        cac = _ttf_cmap(b, vt, bang["cmap"][0])
        du, tong = _bao_viet(cac)
        kq["so_ky_tu"] = len(cac)
        kq["chu_viet"] = f"{du}/{tong}"
        return kq
    except Exception:
        return None


def _ttf_ten(b, vt, bang):
    if "name" not in bang:
        return ""
    o = vt + bang["name"][0]
    _, n, kho = struct.unpack_from(">HHH", b, o)
    ten = {}
    for i in range(n):
        pid, eid, lid, nid, dai, ofs = struct.unpack_from(">6H", b, o + 6 + 12 * i)
        if nid in (1, 4) and nid not in ten:
            s = bytes(b[o + kho + ofs:o + kho + ofs + dai])
            ten[nid] = s.decode("utf-16-be", "replace") if pid in (0, 3) else s.decode("latin-1")
    return ten.get(4) or ten.get(1, "")


def _ttf_cmap(b, vt, ofs):
    o = vt + ofs
    _, n = struct.unpack_from(">HH", b, o)
    cac = set()
    for i in range(n):
        pid, eid, so = struct.unpack_from(">HHI", b, o + 4 + 8 * i)
        t = o + so
        f = struct.unpack_from(">H", b, t)[0]
        if f == 4:
            seg = struct.unpack_from(">H", b, t + 6)[0] // 2
            cuoi = struct.unpack_from(f">{seg}H", b, t + 14)
            dau = struct.unpack_from(f">{seg}H", b, t + 16 + 2 * seg)
            for a, z in zip(dau, cuoi):
                if z != 0xFFFF:
                    cac.update(range(a, z + 1))
        elif f == 12:
            ng = struct.unpack_from(">I", b, t + 12)[0]
            for k in range(min(ng, 5000)):
                a, z, _ = struct.unpack_from(">III", b, t + 16 + 12 * k)
                cac.update(range(a, min(z, a + 70000) + 1))
    return cac


# ------------------------------------------------------------------ quet

class DoPhong:
    def __init__(self, thu_muc_game, thu_ra, bao=lambda s: None, dung=None):
        self.game = thu_muc_game
        self.ra = thu_ra
        self.bao = bao
        self.dung = dung
        self.ket_qua = []          # cac file GFX/TTF tim duoc
        self.chuoi = {}            # chuoi co chu "font" -> so lan
        self.da_luu = {}           # md5 -> ten file mau
        self.dung_luong_luu = 0
        self.so_cdrm = 0
        self.byte_giai = 0

    def _ghi_mau(self, du_lieu, ten, duoi):
        h = hashlib.md5(du_lieu).hexdigest()[:12]
        if h in self.da_luu:
            return self.da_luu[h]
        if self.dung_luong_luu + len(du_lieu) > (300 << 20) or len(self.da_luu) >= 200:
            return ""
        t = f"{ten}_{h}{duoi}"
        with open(os.path.join(self.ra, "mau", t), "wb") as f:
            f.write(du_lieu)
        self.da_luu[h] = t
        self.dung_luong_luu += len(du_lieu)
        return t

    def _mot(self, b, vt, nguon, cdrm_vt, la_giai):
        """Phan tich 1 dau hieu o vi tri vt cua b (bytes hoac mmap)."""
        sig = bytes(b[vt:vt + 4])
        kq = None
        if sig[:3] in (b"GFX", b"CFX", b"FWS", b"CWS"):
            g = doc_gfx(b, vt)
            if g and "the" in g and len(g["the"]) >= 2:
                goc = g.pop("goc")
                duoi = ".gfx" if sig[:3] in (b"GFX", b"CFX") else ".swf"
                co_phong = bool(g["phong"]) or any("Font" in k for k in g["the"])
                if co_phong or self.dung_luong_luu < (150 << 20):
                    g["mau"] = self._ghi_mau(goc, f"{len(self.ket_qua):04d}", duoi)
                kq = g
        else:
            t = doc_ttf(b, vt)
            if t:
                t["mau"] = self._ghi_mau(bytes(b[vt:vt + t["dai"]]), f"{len(self.ket_qua):04d}", ".ttf")
                kq = t
        if kq:
            kq.update({"file": nguon, "cdrm": cdrm_vt, "vi_tri": vt, "trong_nen": la_giai})
            kq["muc"] = self._muc(nguon, cdrm_vt if cdrm_vt >= 0 else vt)
            self.ket_qua.append(kq)

    def _tim(self, b, nguon, cdrm_vt, la_giai):
        """Tim dau hieu file trong vung b (bytes da giai nen)."""
        for m in MAU_FILE.finditer(b):
            self._mot(b, m.start(), nguon, cdrm_vt, la_giai)
        if la_giai:
            cuoi = -1
            for m in MAU_CHU.finditer(b):
                if m.start() < cuoi:
                    continue
                a, z = m.start(), m.end()
                while a > 0 and m.start() - a < 60 and b[a - 1] in IN_DUOC:
                    a -= 1
                while z < len(b) and z - m.end() < 60 and b[z] in IN_DUOC:
                    z += 1
                cuoi = z
                s = b[a:z].decode("latin-1").strip()
                if len(self.chuoi) < 3000 or s in self.chuoi:
                    self.chuoi[s] = self.chuoi.get(s, 0) + 1

    def quet_file(self, p, so_thu, tong, byte_xong, tong_byte):
        ten = os.path.basename(p)
        co = os.path.getsize(p)
        if co < 64:
            return
        with open(p, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as b:
            # 1. dau hieu file khong nen (quet tung khuc 64MB, chong lan 1MB)
            buoc = 64 << 20
            for dau in range(0, co, buoc):
                if self.dung is not None and self.dung.is_set():
                    return
                k = b[dau:min(co, dau + buoc + (1 << 20))]
                for m in MAU_FILE.finditer(k):
                    if m.start() >= buoc:
                        break
                    self._mot(b, dau + m.start(), ten, -1, False)
                pt = (byte_xong + dau) * 100 // max(1, tong_byte)
                self.bao(f"Đang dò font {pt}% – file {so_thu}/{tong}: {ten}")
            # 2. cac khoi nen CDRM (thang hang 16 byte)
            vt = b.find(MAGIC_CDRM)
            moc = time.time()
            while vt != -1:
                if self.dung is not None and self.dung.is_set():
                    return
                kq = giai_cdrm(b, vt) if vt % 16 == 0 else None
                if kq:
                    du_lieu, het = kq
                    self.so_cdrm += 1
                    self.byte_giai += len(du_lieu)
                    self._tim(du_lieu, ten, vt, True)
                    vt = b.find(MAGIC_CDRM, het)
                else:
                    vt = b.find(MAGIC_CDRM, vt + 4)
                if time.time() - moc > 1.5:
                    moc = time.time()
                    pt = (byte_xong + (vt if vt > 0 else co)) * 100 // max(1, tong_byte)
                    self.bao(f"Đang dò font {pt}% – file {so_thu}/{tong}: {ten} (giải nén {self.so_cdrm:,} khối)"
                             .replace(",", "."))

    def _nap_bang(self, cac):
        """Doc bang muc luc cua cac goi .000.tiger -> self.bang[ten_phan] = [(vt, bam, locale, co)] da sap xep."""
        self.bang = {}
        for p in cac:
            ten = os.path.basename(p)
            if not ten.endswith(".000.tiger"):
                continue
            try:
                with open(p, "rb") as f:
                    d = f.read(0x34)
                    magic, ban, so_phan, so_tep, ma = struct.unpack_from("<5i", d, 0)
                    if magic != 0x53464154 or ban != 4:
                        continue
                    bang = f.read(24 * so_tep)
                for i in range(so_tep):
                    bam, loc, co, _, phan, _, vt = struct.unpack_from("<IIIIhhI", bang, 24 * i)
                    tp = ten if not phan else ten[:-len(".000.tiger")] + f".{phan:03d}.tiger"
                    self.bang.setdefault(tp, []).append((vt, bam, loc, co))
            except Exception:
                pass
        for v in self.bang.values():
            v.sort()

    def _muc(self, ten, vt):
        ds = getattr(self, "bang", {}).get(ten)
        if not ds:
            return ""
        i = bisect.bisect_right(ds, (vt, 0xFFFFFFFF, 0xFFFFFFFF, 0)) - 1
        if i < 0:
            return ""
        v, bam, loc, co = ds[i]
        return f"bam={bam:08X} locale={loc:08X} vt_muc={v} co={co} lech={vt - v}"

    def chay(self):
        os.makedirs(os.path.join(self.ra, "mau"), exist_ok=True)
        cac = sorted(t for t in os.listdir(self.game)
                     if t.lower().endswith(".tiger") and TEN_MOD not in t)
        cac = [os.path.join(self.game, t) for t in cac]
        tong_byte = sum(os.path.getsize(p) for p in cac)
        self._nap_bang(cac)
        bat_dau = time.time()
        xong = 0
        for i, p in enumerate(cac, 1):
            if self.dung is not None and self.dung.is_set():
                break
            try:
                self.quet_file(p, i, len(cac), xong, tong_byte)
            except Exception as e:
                self.ket_qua.append({"loi_file": os.path.basename(p), "loi": str(e)[:120]})
            xong += os.path.getsize(p)
        return self.ghi_bao_cao(cac, time.time() - bat_dau)

    def ghi_bao_cao(self, cac, giay):
        dong = ["BÁO CÁO DÒ FONT – Rise of the Tomb Raider", f"Thư mục game: {self.game}",
                f"Số file .tiger: {len(cac)}  •  khối nén đã giải: {self.so_cdrm:,}  •  "
                f"dữ liệu giải nén: {self.byte_giai / 2**30:.1f} GB  •  thời gian: {giay / 60:.1f} phút", ""]
        gfx = [k for k in self.ket_qua if k.get("loai") in ("GFX", "CFX", "FWS", "CWS")]
        ttf = [k for k in self.ket_qua if k.get("loai") == "TTF/OTF"]
        dong.append(f"== FONT TRUETYPE / OPENTYPE: {len(ttf)} ==")
        for k in ttf:
            dong.append(f"- {k['ten']!r}  ký tự: {k['so_ky_tu']}  chữ Việt: {k['chu_viet']}  "
                        f"[{k['file']} @cdrm {k['cdrm']} +{k['vi_tri']} | {k.get('muc', '')}]  mẫu: {k.get('mau')}")
        dong.append("")
        co_font = [k for k in gfx if k.get("phong")]
        dong.append(f"== FILE SCALEFORM/FLASH: {len(gfx)} (có font bên trong: {len(co_font)}) ==")
        for k in sorted(gfx, key=lambda k: -len(k.get("phong", []))):
            dong.append(f"- {k['loai']} v{k['ban']} {k['dai']:,} byte [{k['file']} @cdrm {k['cdrm']} +{k['vi_tri']}] "
                        f"mẫu: {k.get('mau', '')}")
            for f in k.get("phong", []):
                dong.append(f"    font: {json.dumps(f, ensure_ascii=False)}")
            if k.get("nhap"):
                dong.append(f"    nhập từ: {k['nhap']}")
            if k.get("xuat"):
                dong.append(f"    xuất: {k['xuat'][:20]}")
            if k.get("the"):
                dong.append(f"    thẻ: {k['the']}")
            if k.get("loi"):
                dong.append(f"    lỗi đọc: {k['loi']}")
        dong.append("")
        dong.append(f"== CHUỖI CÓ CHỮ 'font' (nhiều nhất trước): {len(self.chuoi)} ==")
        for s, n in sorted(self.chuoi.items(), key=lambda x: -x[1])[:400]:
            dong.append(f"{n:6d}  {s}")
        loi = [k for k in self.ket_qua if "loi_file" in k]
        if loi:
            dong.append("")
            dong.append("== LỖI ==")
            dong += [f"- {k['loi_file']}: {k['loi']}" for k in loi]
        p = os.path.join(self.ra, "bao_cao_font.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(dong))
        with open(os.path.join(self.ra, "bao_cao_font.json"), "w", encoding="utf-8") as f:
            json.dump({"ket_qua": self.ket_qua, "chuoi": self.chuoi}, f, ensure_ascii=False, default=str)
        zp = os.path.join(self.ra, "GuiClaude_DoFont.zip")
        try:
            import zipfile
            with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(p, "bao_cao_font.txt")
                tong = 0
                for k in ttf + co_font:
                    m = k.get("mau")
                    mp = os.path.join(self.ra, "mau", m) if m else ""
                    if mp and os.path.isfile(mp) and m not in z.namelist() and tong + os.path.getsize(mp) < (20 << 20):
                        z.write(mp, m)
                        tong += os.path.getsize(mp)
        except Exception:
            zp = ""
        return {"bao_cao": p, "zip": zp, "ttf": len(ttf), "gfx": len(gfx), "co_font": len(co_font),
                "font": sum(len(k.get("phong", [])) for k in gfx)}
