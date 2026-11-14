# -*- coding: utf-8 -*-
"""
Viet hoa Tomb Raider (2013) va Shadow of the Tomb Raider – cung engine Foundation voi Rise of the Tomb Raider.

  Tomb Raider 2013 (goi .tiger phien ban 3, bam 32 bit, khong co .nfo):
    game khong doc goi mod rieng -> app dung lai goi "patch2.000.tiger" (cach cua TR Reboot Mod Tools):
    giu ban goc thanh bigfile._orig.patch2.000.tiger, tao patch2 moi = toan bo file cu + locals.bin tieng Viet.
    Go = tra lai patch2 goc.
  Shadow of the Tomb Raider (goi .tiger phien ban 5, bam 64 bit, .nfo + .specmasks.toc):
    tao goi mod rieng bigfile._mod.viethoa_dichgame.* (khong sua file goc). Go = xoa goi do.
Dinh dang tham khao tu TR Reboot Mod Tools (arcusmaximus, giay phep MIT).
"""

import json
import os
import shutil
import struct
import zlib

import viet_hoa_cd as vcd
from viet_hoa_cd import LoiDung
import viet_hoa_rottr as vrt

MAGIC_TIGER = 0x53464154
MAGIC_CDRM = 0x4D524443
TEN_MOD = "viethoa_dichgame"
TEN_MARKER_TR13 = "viethoa_dichgame_tr2013.txt"
PATCH2 = "patch2.000.tiger"
PATCH2_GOC = "bigfile._orig.patch2.000.tiger"
ID_PATCH2 = 67

LOAI = {
    "tr2013": {"ten": "Tomb Raider (2013)", "ban": 3, "nen": "pc-w", "thu_muc": "tr2013",
               "locals": ["pc-w\\local\\locals.bin", "pc-w\\locals.bin", "local\\locals.bin"]},
    "shadow": {"ten": "Shadow of the Tomb Raider", "ban": 5, "nen": "pcx64-w", "thu_muc": "shadow",
               "locals": ["pcx64-w\\local\\locals.bin", "pc-w\\local\\locals.bin", "local\\locals.bin"]},
}

NGON_NGU_SHADOW = ["english", "french", "german", "italian", "latamspanish", "iberspanish", "japanese", "portuguese",
                   "polish", "russian", "dutch", "korean", "chinese", "simplechinese", None, "arabic"]


def bam32(s):
    return vrt.bam_cdc(s)


def bam64(s):
    h = 0xCBF29CE484222325
    for c in s:
        h = ((h ^ ord(c)) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def nhan_dien(thu_muc):
    """'tr2013' | 'shadow' | None"""
    if os.path.isfile(os.path.join(thu_muc, "SOTTR.exe")):
        return "shadow"
    if os.path.isfile(os.path.join(thu_muc, "TombRaider.exe")):
        return "tr2013"
    return None


# ================================================================ goi .tiger (v3 / v5)

def doc_tiger(p):
    """-> (dau, ds_muc). dau: ban, id, sub, so_phan, so_tep, co_dau. muc: bam, locale, co, phan, id, sub, vt."""
    with open(p, "rb") as f:
        d = f.read(0x38)
        if len(d) < 0x34:
            raise ValueError("file .tiger quá ngắn")
        magic, ban, so_phan, so_tep, ma = struct.unpack_from("<5i", d, 0)
        if magic != MAGIC_TIGER:
            raise ValueError("không phải file .tiger")
        if ban == 3:
            co_dau, kich = 0x34, 16
        elif ban == 4:
            co_dau, kich = 0x34, 24
        elif ban == 5:
            co_dau, kich = 0x38, 32
        else:
            raise ValueError(f"file .tiger phiên bản {ban} chưa hỗ trợ")
        sub = struct.unpack_from("<i", d, 0x14)[0] if ban == 5 else 0
        f.seek(co_dau)
        bang = f.read(kich * so_tep)
    ds = []
    for i in range(so_tep):
        o = kich * i
        if ban == 3:
            bam, loc, co, goi = struct.unpack_from("<IIII", bang, o)
            ds.append({"bam": bam, "locale": loc, "co": co, "phan": goi & 0xF, "id": (goi >> 4) & 0x7F, "sub": 0,
                       "vt": goi & 0xFFFFF800})
        elif ban == 4:
            bam, loc, co, _, phan, ma_g, vt = struct.unpack_from("<IIIIhhI", bang, o)
            ds.append({"bam": bam, "locale": loc, "co": co, "phan": phan, "id": ma_g, "sub": 0, "vt": vt})
        else:
            bam, loc, co, _, phan, ma_g, sub_g, vt = struct.unpack_from("<QQIIhBBI", bang, o)
            ds.append({"bam": bam, "locale": loc, "co": co, "phan": phan, "id": ma_g, "sub": sub_g, "vt": vt})
    return {"ban": ban, "id": ma, "sub": sub, "so_phan": so_phan, "so_tep": so_tep, "co_dau": co_dau}, ds


def doc_du_lieu(p, muc, tho=False):
    """Noi dung 1 file trong goi. tho=True: lay nguyen byte trong goi (ke ca khoi nen CDRM)."""
    with open(vrt.duong_dan_phan(p, muc["phan"]), "rb") as f:
        f.seek(muc["vt"])
        dau = f.read(16)
        if len(dau) >= 16 and struct.unpack_from("<I", dau, 0)[0] == MAGIC_CDRM:
            so_khuc = struct.unpack_from("<i", dau, 8)[0]
            bang = f.read(8 * so_khuc)
            vt = (muc["vt"] + 16 + 8 * so_khuc + 0xF) & ~0xF
            ra = bytearray()
            for i in range(so_khuc):
                goc, nen = struct.unpack_from("<ii", bang, 8 * i)
                goc >>= 8
                f.seek(vt)
                b = f.read(nen)
                ra += b if nen == goc else zlib.decompress(b)
                vt = (vt + nen + 0xF) & ~0xF
            if tho:
                f.seek(muc["vt"])
                return f.read(vt - muc["vt"])
            return bytes(ra)
        f.seek(muc["vt"])
        return f.read(muc["co"])


# ================================================================ locals.bin

def doc_locals_32(b):
    """Tomb Raider 2013: con tro 4 byte. -> (lang, khoa, chuoi{i: str}, so)"""
    lang, so_khoa, so = struct.unpack_from("<iii", b, 0)
    o = 12
    khoa = list(struct.unpack_from(f"<{so_khoa}i", b, o)) if so_khoa else []
    o += 4 * so_khoa
    chuoi = {}
    for i in range(so):
        p = struct.unpack_from("<i", b, o + 4 * i)[0]
        if p <= 0 or p >= len(b):
            continue
        j = b.index(b"\0", p)
        chuoi[i] = b[p:j].decode("utf-8", "replace")
    return lang, khoa, chuoi, so


def ghi_locals_32(lang, khoa, chuoi, so=None):
    n = max(so or 0, (max(chuoi) + 1) if chuoi else 0)
    dau = struct.pack("<iii", lang, len(khoa), n) + (struct.pack(f"<{len(khoa)}i", *khoa) if khoa else b"")
    bat_dau = len(dau) + 4 * n
    con_tro = bytearray(4 * n)
    than = bytearray()
    for i in range(n):
        s = chuoi.get(i)
        if s is None:
            continue
        struct.pack_into("<i", con_tro, 4 * i, bat_dau + len(than))
        than += s.encode("utf-8") + b"\0"
    return dau + bytes(con_tro) + bytes(than)


def doc_locals_shadow(b):
    """Shadow: moi muc 'khoa gia_tri'. -> (lang, [khoa theo thu tu], chuoi{khoa: str})"""
    lang, so = struct.unpack_from("<ii", b, 0)
    thu_tu, chuoi = [], {}
    for i in range(so):
        p = struct.unpack_from("<q", b, 8 + 8 * i)[0]
        if p <= 0 or p >= len(b):
            continue
        j = b.index(b"\0", p)
        s = b[p:j]
        k = s.find(b" ")
        if k < 0:
            continue
        khoa = s[:k].decode("utf-8", "replace")
        thu_tu.append(khoa)
        chuoi[khoa] = s[k + 1:].decode("utf-8", "replace")
    return lang, thu_tu, chuoi


def ghi_locals_shadow(lang, thu_tu, chuoi):
    n = len(thu_tu)
    dau = struct.pack("<ii", lang, n)
    bat_dau = len(dau) + 8 * n
    con_tro = bytearray(8 * n)
    than = bytearray()
    for i, k in enumerate(thu_tu):
        struct.pack_into("<q", con_tro, 8 * i, bat_dau + len(than))
        than += k.encode("utf-8") + b" " + chuoi[k].encode("utf-8") + b"\0"
    return dau + bytes(con_tro) + bytes(than)


def _hop_ly(chuoi):
    """Kiem tra du lieu doc ra co phai bang chu cua game (nhieu chuoi tieng Anh) khong."""
    v = [s for s in chuoi.values() if s]
    if len(v) < 200:
        return False
    anh = sum(1 for s in v[:3000] if any(c.isalpha() for c in s) and all(ord(c) < 0x250 for c in s[:40]))
    return anh >= 0.8 * min(len(v), 3000)


# ================================================================ quet game

def _la_anh(loai, loc):
    """locale co phai chu tieng Anh (hoac chung moi ngon ngu) khong. -> 2 = rieng tieng Anh, 1 = chung, 0 = khong."""
    if loai == "shadow":
        if loc == 0xFFFFFFFFFFFFFFFF:
            return 1
        txt = loc & 0xFFFFFFF
        if txt == 0xFFFFFFF:
            return 1
        return 2 if txt & 1 else 0
    if loc == 0xFFFFFFFF:
        return 1
    return 2 if loc & 1 else 0


def _cac_goi(thu_muc):
    for t in sorted(os.listdir(thu_muc)):
        if t.lower().endswith(".000.tiger") and TEN_MOD not in t:
            yield t


def quet(thu_muc, loai, bao=lambda s: None):
    """Tim locals.bin tieng Anh dang duoc game dung. -> dict(nguon=(duong_dan, muc), ...)"""
    cau = LOAI[loai]
    bam = {(bam64 if loai == "shadow" else bam32)(n) for n in cau["locals"]}
    meta = {}
    if loai == "shadow":
        for t in os.listdir(thu_muc):
            if t.endswith(".nfo") and not t.startswith("bigfile._mod."):
                try:
                    m = vrt.doc_nfo(os.path.join(thu_muc, t))
                    meta[m.get("dlcindex", -1)] = m
                except Exception:
                    pass
    ung_vien, du_phong, id_max = [], [], 0
    goc_patch2 = os.path.isfile(os.path.join(thu_muc, PATCH2_GOC))
    for t in _cac_goi(thu_muc):
        if loai == "tr2013":
            if t == PATCH2 and goc_patch2:
                continue                          # patch2 hien tai la ban app / mod tao -> dung ban goc
            if t.startswith("bigfile._orig.") and t != PATCH2_GOC:
                continue
        elif t.startswith("bigfile._orig."):
            continue
        p = os.path.join(thu_muc, t)
        try:
            dau, ds = doc_tiger(p)
        except Exception:
            continue
        if t.startswith("bigfile._mod."):
            if loai == "shadow":
                id_max = max(id_max, dau["id"])
            continue
        id_max = max(id_max, dau["id"])
        if loai == "tr2013":
            if dau["id"] > ID_PATCH2:
                continue
            uu = (dau["id"],)
        else:
            m = meta.get(dau["id"])
            if m is None:
                continue
            uu = (m.get("version", 0), -m.get("required", 1), m.get("package", 0), m.get("chunk", 0), dau["sub"])
        for muc in ds:
            la = _la_anh(loai, muc["locale"])
            if not la:
                continue
            if muc["bam"] in bam:
                ung_vien.append((uu + (la,), p, muc))
            elif la == 2 and 20000 < muc["co"] < 40 << 20 and muc["id"] == dau["id"]:
                du_phong.append((uu + (la,), p, muc))
    if not ung_vien:
        # khong biet ten file -> do tung file tieng Anh xem file nao la bang chu
        bao("Đang tìm file chữ tiếng Anh (lần đầu hơi lâu)...")
        for uu, p, muc in sorted(du_phong, key=lambda x: x[0], reverse=True)[:4000]:
            try:
                b = doc_du_lieu(p, muc)
                ch = doc_locals_shadow(b)[2] if loai == "shadow" else doc_locals_32(b)[2]
                if _hop_ly(ch):
                    ung_vien.append((uu, p, muc))
                    break
            except Exception:
                continue
    if not ung_vien:
        raise LoiDung("không tìm thấy file chữ tiếng Anh (locals.bin) trong các gói .tiger của game")
    ung_vien.sort(key=lambda x: x[0])
    _, p, muc = ung_vien[-1]
    kq = {"nguon": (p, muc), "id_max": id_max}
    if meta:
        kq["bap"] = next((m["bap"] for m in meta.values() if m.get("bap")), 0)
        kq["steam"] = next((c for m in meta.values() for c in m["custom"] if c.startswith("steamID:")), None)
        kq["phien_ban_max"] = max(m.get("version", 0) for m in meta.values())
    return kq


# ================================================================ tao goi

def duoi_shadow(loc):
    """Hau to ten goi theo locale (giong TR Reboot Mod Tools)."""
    if loc == 0xFFFFFFFFFFFFFFFF:
        return ""

    def ten(co, tat_ca):
        if co == 0xFFFFFFF or (co & 0xFFF0000) != 0xFFF0000:
            return tat_ca
        v = co & 0xFFFF
        for i, n in enumerate(NGON_NGU_SHADOW):
            if n and v == (0x400 | (1 << i)):
                return n
        return tat_ca
    txt = ten(loc & 0xFFFFFFF, "alltxt")
    vo = ten((loc >> 28) & 0xFFFFFFF, "allvo")
    pl = loc >> 56
    plt = "allplt" if pl == 0xFF else ("neutral" if pl == 0x20 else f"{pl:02X}")
    return f"_{txt}_{vo}_{plt}"


def tao_tiger_v5(duong_dan, ma, sub, cac_tep):
    cac_tep = sorted(cac_tep, key=lambda x: (x[0], x[1]))
    dau = struct.pack("<5ii", MAGIC_TIGER, 5, 1, len(cac_tep), ma, sub) + b"pcx64-w".ljust(0x20, b"\0")
    vt = len(dau) + 32 * len(cac_tep)
    bang, than = bytearray(), bytearray()
    for bam, loc, du_lieu in cac_tep:
        than += b"\0" * ((-(vt + len(than))) % 0x10)
        bang += struct.pack("<QQIIhBBI", bam, loc, len(du_lieu), 0, 0, ma, sub, vt + len(than))
        than += du_lieu
    tam = duong_dan + ".tam"
    with open(tam, "wb") as f:
        f.write(dau + bang + than)
    os.replace(tam, duong_dan)


def tao_patch2(thu_muc, them, bao=lambda s: None):
    """Tomb Raider 2013: patch2 moi = file cua patch2 goc + file them (cung bam/locale thi thay). them: {(bam, loc): bytes}"""
    goc = os.path.join(thu_muc, PATCH2_GOC)
    hien = os.path.join(thu_muc, PATCH2)
    if not os.path.isfile(goc) and os.path.isfile(hien):
        shutil.copy2(hien, goc)                      # giu ban goc (1 lan)
    cu = []
    if os.path.isfile(goc):
        _, ds = doc_tiger(goc)
        cu = [m for m in ds if (m["bam"], m["locale"]) not in them]
    tong = len(cu) + len(them)
    dau = struct.pack("<5i", MAGIC_TIGER, 3, 1, tong, ID_PATCH2) + b"pc-w".ljust(0x20, b"\0")
    hang = []                                        # (bam, loc, co, goi_hoac_None, ham_lay)
    for m in cu:
        if m["id"] != ID_PATCH2:
            hang.append((m["bam"], m["locale"], m["co"], (m["vt"] | (m["id"] << 4) | m["phan"]), None))
        else:
            hang.append((m["bam"], m["locale"], m["co"], None, lambda m=m: doc_du_lieu(goc, m, tho=True)))
    for (bam, loc), b in them.items():
        hang.append((bam, loc, len(b), None, lambda b=b: b))
    hang.sort(key=lambda x: (x[0], x[1]))
    bang = bytearray(16 * tong)
    tam = hien + ".viethoa_tam"
    with open(tam, "wb") as f:
        f.write(dau + bytes(bang))
        vt = len(dau) + len(bang)
        for i, (bam, loc, co, goi, ham) in enumerate(hang):
            if goi is None:
                dem = (-vt) % 0x800
                f.write(b"\0" * dem)
                vt += dem
                du = ham()
                if vt + len(du) > 0xFFFFF800:
                    raise LoiDung("gói patch2 vượt 4 GB")
                goi = vt | (ID_PATCH2 << 4)
                f.write(du)
                vt += len(du)
                co = len(du) if co == 0 else co
            struct.pack_into("<IIII", bang, 16 * i, bam, loc, co, goi)
            if i % 300 == 0:
                bao(f"Đang ghi gói Việt hóa: {i:,}/{tong:,} file".replace(",", "."))
        f.write(b"\0" * ((-vt) % 0x800))
        f.seek(len(dau))
        f.write(bytes(bang))
    os.replace(tam, hien)
    with open(os.path.join(thu_muc, TEN_MARKER_TR13), "w", encoding="utf-8") as f:
        f.write("Dich Game: patch2.000.tiger da duoc thay bang ban Viet hoa. Ban goc: " + PATCH2_GOC + "\n")


def tep_mod_shadow(thu_muc):
    return [t for t in os.listdir(thu_muc) if t.startswith(f"bigfile._mod.{TEN_MOD}.")
            or t.startswith(f"_mod.{TEN_MOD}.")]


def da_cai_nhanh(thu_muc, loai):
    if loai == "tr2013":
        return os.path.isfile(os.path.join(thu_muc, TEN_MARKER_TR13))
    try:
        return any(t.endswith(".tiger") for t in tep_mod_shadow(thu_muc))
    except OSError:
        return False


# ================================================================ cong viec Viet hoa

HUONG_DAN = {
    "tr2013": "Game: Tomb Raider (2013) (phiêu lưu sinh tồn; Lara Croft trẻ tuổi mắc kẹt trên đảo Yamatai; "
              "giáo phái Solarii; Nữ hoàng Mặt Trời Himiko; con tàu Endurance).",
    "shadow": "Game: Shadow of the Tomb Raider (phiêu lưu hành động; Lara Croft ở rừng rậm Mỹ Latinh, "
              "thành phố ẩn Paititi; tổ chức Trinity; Dr. Dominguez; ngày tận thế của người Maya).",
}
TEN_RIENG = {
    "tr2013": ["Lara", "Croft", "Lara Croft", "Roth", "Conrad Roth", "Sam", "Samantha", "Jonah", "Reyes", "Alex",
               "Grim", "Whitman", "Mathias", "Himiko", "Yamatai", "Solarii", "Stormguard", "Oni", "Endurance",
               "Sun Queen", "Shipwreck Beach", "Shantytown", "Mountain Village", "Chasm Monastery"],
    "shadow": ["Lara", "Croft", "Lara Croft", "Jonah", "Dominguez", "Pedro Dominguez", "Unuratu", "Etzli", "Abby",
               "Uchu", "Trinity", "Paititi", "Kuwaq Yaku", "Cozumel", "Peru", "Mexico", "Yaaxil", "Cult of Kukulkan",
               "Kukulkan", "Ix Chel", "Mission", "Porvenir", "San Juan", "Silver Box", "Chak Chel", "Hidden City"],
}


class ViecTr(vrt.ViecRottr):
    """Dung lai toan bo cach dich / loc chu cua Rise; chi khac cach doc va ghi file game."""

    def __init__(self, thu_muc_game, loai):
        super().__init__(thu_muc_game)
        self.loai = loai
        self.tm = os.path.join(vcd.DU_LIEU, LOAI[loai]["thu_muc"])
        self.file_bo_nho = os.path.join(self.tm, "bo_nho_dich.json")
        self.HUONG_DAN = vrt.HUONG_DAN_ROTTR.replace(
            vrt.HUONG_DAN_ROTTR.split("\n")[0], "Bạn là dịch giả chuyên Việt hóa game. " + HUONG_DAN[loai])

    def nap(self, bao=lambda s: None):
        bao("Đang tìm file chữ tiếng Anh của game (locals.bin)...")
        self.tt = quet(self.thu_muc_game, self.loai, bao)
        p, muc = self.tt["nguon"]
        bao(f"Đang đọc chữ từ {os.path.basename(p)}...")
        b = doc_du_lieu(p, muc)
        if self.loai == "shadow":
            lang, thu_tu, chuoi = doc_locals_shadow(b)
            self.locals = (lang, thu_tu, chuoi)
        else:
            self.locals = doc_locals_32(b)
            chuoi = self.locals[2]
        self.goc = chuoi
        self.bang_ten = vcd.BangTen(set(TEN_RIENG[self.loai]))
        self.mul = {}
        try:
            with open(self.file_bo_nho, encoding="utf-8") as f:
                self.bo_nho = json.load(f)
        except Exception:
            self.bo_nho = {}
        return self

    def luu(self):
        os.makedirs(self.tm, exist_ok=True)
        with self.khoa:
            du_lieu = json.dumps(self.bo_nho, ensure_ascii=False)
        tam = self.file_bo_nho + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            f.write(du_lieu)
        os.replace(tam, self.file_bo_nho)

    def quet_mul(self, bao=lambda s: None):
        self.mul = {}

    def thong_ke_mul(self):
        return {"cau": 0, "da_dich": 0, "giong": 0, "da_long": 0}

    def da_cai(self):
        return da_cai_nhanh(self.thu_muc_game, self.loai)

    def cai(self, khong_dau=False, chi_thu=False, bao=lambda s: None):
        moi = dict(self.goc)
        doi = 0
        for k, en in self.goc.items():
            if chi_thu:
                vi = vrt.CHU_THU.get(en.strip().lower())
                if vi:
                    vi = vrt.bo_dau(vi) if khong_dau else vrt.dau_ghep(vi)
            else:
                vi = self.chuoi_viet(en, khong_dau)
            if vi:
                moi[k] = vi
                doi += 1
        if not doi:
            raise LoiDung("chưa có câu nào được dịch – bấm Dịch trước")
        self.so_cai = {"phu_de": 0, "giong": 0}
        p, muc = self.tt["nguon"]
        tm = self.thu_muc_game
        if self.loai == "tr2013":
            lang, khoa, _, n = self.locals
            du_lieu = ghi_locals_32(lang, khoa, moi, n)
            tao_patch2(tm, {(muc["bam"], muc["locale"]): du_lieu}, bao)
            return doi
        lang, thu_tu, _ = self.locals
        du_lieu = ghi_locals_shadow(lang, thu_tu, moi)
        self.go()
        tt = self.tt
        ma = tt["id_max"] + 1
        loc = muc["locale"]
        goc_ten = f"bigfile._mod.{TEN_MOD}.000.000.tiger"
        en_ten = f"bigfile._mod.{TEN_MOD}.000{duoi_shadow(loc)}.000.tiger"
        if en_ten == goc_ten:
            tao_tiger_v5(os.path.join(tm, goc_ten), ma, 0, [(muc["bam"], loc, du_lieu)])
        else:
            tao_tiger_v5(os.path.join(tm, goc_ten), ma, 0, [])
            tao_tiger_v5(os.path.join(tm, en_ten), ma, 1, [(muc["bam"], loc, du_lieu)])
            with open(os.path.join(tm, f"_mod.{TEN_MOD}.specmasks.toc"), "w", encoding="utf-8", newline="\r\n") as f:
                f.write("c7fff1c00fff0400\n")
                f.write(f"{0xFFFFFFFFFFFFFFFF:016x} {goc_ten}\n")
                f.write(f"{loc:016x} {en_ten}\n")
        vrt.ghi_nfo(os.path.join(tm, f"bigfile._mod.{TEN_MOD}.000.000.nfo"), tt.get("bap", 0),
                    tt.get("phien_ban_max", 0) + 1, ma, tt.get("steam"))
        return doi

    def go(self):
        tm = self.thu_muc_game
        if self.loai == "tr2013":
            mk = os.path.join(tm, TEN_MARKER_TR13)
            if not os.path.isfile(mk):
                return
            goc = os.path.join(tm, PATCH2_GOC)
            if os.path.isfile(goc):
                shutil.copy2(goc, os.path.join(tm, PATCH2))
            else:
                os.remove(os.path.join(tm, PATCH2))
            os.remove(mk)
            return
        for t in tep_mod_shadow(tm):
            os.remove(os.path.join(tm, t))
