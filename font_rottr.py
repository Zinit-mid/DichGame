# -*- coding: utf-8 -*-
"""
Font tieng Viet cho Rise of the Tomb Raider.

Chu trong game (menu, phu de...) ve bang Scaleform, dung thu vien font "gfxfontlib" (font DIN-Bold, chi co chu
Latin-1). App:
  1. Doc cac "bo suu tap" (.drm, phien ban 22) trong goi .tiger cua game -> tim tai nguyen GFX chua font Latin
     (DefineFont3 >= 150 chu, co a/à, khong phai font Nga / A Rap / CJK) va moi bo suu tap tham chieu toi no.
  2. Them chu Viet vao font (font_viet.them_tieng_viet).
  3. Ghi vao goi mod cua app: tai nguyen moi (khoi nen CDRM + dau "NEXT") trong goi chung, cac bo suu tap
     tro sang tai nguyen moi (giong cach TR Reboot Mod Tools cai mod).
Ket qua do lan dau duoc luu (%APPDATA%/VietHoaGame/rottr/font_rottr.json) – lan sau khong phai do lai.
"""
import hashlib
import json
import os
import struct
import time
import zlib

import viet_hoa_cd as vcd
import viet_hoa_rottr as vrt
import font_viet as fv

PHIEN_BAN_DO = 2
FILE_DO = os.path.join(vcd.DU_LIEU, "rottr", "font_rottr.json")
LOAI_BO = {1, 2, 5, 6, 9, 10, 12, 13, 15}          # rong, hoat anh, texture, am thanh, shader, vat lieu, mo hinh...


class LoiFont(Exception):
    pass


# ================================================================ doc goi / khoi nen

class _Doc:
    """Doc du lieu trong cac goi .tiger, giu file mo de doc nhanh."""

    def __init__(s):
        s.f = {}
        s.nho = None                             # trang thai khoi dang giai nen do (xem doan)

    def _mo(s, p):
        f = s.f.get(p)
        if f is None:
            if len(s.f) > 40:
                for x in s.f.values():
                    x.close()
                s.f.clear()
            f = s.f[p] = open(p, "rb")
        return f

    def doan(s, p, vt, tu, dai):
        """Doc dai byte tu vi tri 'tu' (sau giai nen) cua khoi o vt. Giai nen DAN DAN va nho trang thai,
        nen doc nhieu tai nguyen trong cung 1 khoi lon chi giai nen 1 lan (truoc day giai lai tu dau -> rat cham)."""
        can = tu + dai
        tt = s.nho if isinstance(s.nho, dict) and s.nho.get("k") == (p, vt) else None
        if tt is None:
            f = s._mo(p)
            f.seek(vt)
            dau = f.read(16)
            if len(dau) < 16 or struct.unpack_from("<I", dau, 0)[0] != vrt.MAGIC_CDRM:
                f.seek(vt + tu)
                return f.read(dai)
            so = struct.unpack_from("<i", dau, 8)[0]
            if not 0 < so < 100000:
                raise LoiFont("khối nén hỏng")
            bang = f.read(8 * so)
            tt = {"k": (p, vt), "du": bytearray(), "khuc": [struct.unpack_from("<ii", bang, 8 * i) for i in range(so)],
                  "i": 0, "q": (vt + 16 + 8 * so + 0xF) & ~0xF}
            s.nho = tt
        f = s._mo(p)
        while len(tt["du"]) < can and tt["i"] < len(tt["khuc"]):
            goc, nen = tt["khuc"][tt["i"]]
            goc >>= 8
            f.seek(tt["q"])
            b = f.read(nen)
            tt["du"] += b if nen == goc else zlib.decompress(b)
            tt["q"] = (tt["q"] + nen + 0xF) & ~0xF
            tt["i"] += 1
        return bytes(tt["du"][tu:can])

    def dong(s):
        for x in s.f.values():
            x.close()
        s.f.clear()

    def khoi(s, p, vt, can=None, toi_da=None):
        """Giai nen khoi bat dau o vt (CDRM hoac du lieu tho). can: so byte can (dung som). toi_da: co tho."""
        f = s._mo(p)
        f.seek(vt)
        dau = f.read(16)
        if len(dau) < 16 or struct.unpack_from("<I", dau, 0)[0] != vrt.MAGIC_CDRM:
            f.seek(vt)
            return f.read(toi_da if toi_da is not None else (can or 0))   # du lieu khong nen
        so = struct.unpack_from("<i", dau, 8)[0]
        if not 0 < so < 100000:
            raise LoiFont("khối nén hỏng")
        bang = f.read(8 * so)
        q = (vt + 16 + 8 * so + 0xF) & ~0xF
        ra = bytearray()
        for i in range(so):
            goc, nen = struct.unpack_from("<ii", bang, 8 * i)
            goc >>= 8
            f.seek(q)
            b = f.read(nen)
            ra += b if nen == goc else zlib.decompress(b)
            q = (q + nen + 0xF) & ~0xF
            if can is not None and len(ra) >= can:
                break
        return bytes(ra)


def doc_drm(b):
    """Bo suu tap Rise (.drm v22) -> dict hoac None."""
    if len(b) < 32:
        return None
    ver, inc, dep, pad, kich, co, n, chinh = struct.unpack_from("<8i", b, 0)
    if ver != 22 or not 0 <= n < 200000 or inc < 0 or dep < 0:
        return None
    vt_id = 32
    vt_loc = vt_id + 20 * n + dep + inc
    if vt_loc + 24 * n > len(b):
        return None
    ids, locs = [], []
    for i in range(n):
        than, loai, _, _, sub_ref, ma, loc = struct.unpack_from("<IBBhIiI", b, vt_id + 20 * i)
        ids.append({"than": than, "loai": loai, "ref": sub_ref >> 8, "ma": ma, "locale": loc})
        _, _, phan, goi, vt, co_goi, giai = struct.unpack_from("<iihhIII", b, vt_loc + 24 * i)
        locs.append((goi, phan, vt, co_goi, giai))
    return {"ids": ids, "locs": locs, "vt_id": vt_id, "vt_loc": vt_loc}


# ================================================================ do

def _cac_goi(thu_muc):
    meta = {}
    for t in os.listdir(thu_muc):
        if t.endswith(".nfo") and not t.startswith("bigfile._mod."):
            try:
                m = vrt.doc_nfo(os.path.join(thu_muc, t))
                meta[m.get("dlcindex", -1)] = m
            except Exception:
                pass
    goi = []
    for t in sorted(os.listdir(thu_muc)):
        if not t.endswith(".000.tiger") or not t.startswith("bigfile") or t.startswith("bigfile._mod."):
            continue
        p = os.path.join(thu_muc, t)
        try:
            dau, ds = vrt.doc_tiger(p)
        except Exception:
            continue
        m = meta.get(dau["id"], {})
        uu = (m.get("version", 0), -m.get("required", 1), m.get("package", 0), m.get("chunk", 0),
              vrt._thu_tu_ngon_ngu(t))
        goi.append({"p": p, "ten": t, "id": dau["id"], "uu": uu, "ds": ds})
    return goi


def _chu_ky(goi):
    h = hashlib.md5()
    for g in goi:
        st = os.stat(g["p"])
        h.update(f"{g['ten']}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()


def la_font_latin(f):
    if len(f.ma) < 150 or ord("a") not in f.ma or ord("à") not in f.ma:
        return False
    la = sum(1 for c in f.ma if 0x400 <= c < 0x700 or 0x3000 <= c < 0xE000)   # Nga, A Rap, CJK, Han
    return la <= 10


def _tim_gfx(du):
    for k in range(0, min(len(du) - 3, 96)):
        if du[k:k + 3] in (b"GFX", b"CFX", b"FWS", b"CWS") and 6 <= du[k + 3] <= 20:
            return k
    return -1


def do_font(thu_muc, bao=lambda s: None, dung=None):
    """-> dict ket qua do (luu lai). Nem LoiFont neu khong tim thay."""
    goi = _cac_goi(thu_muc)
    if not goi:
        raise LoiFont("không đọc được gói .tiger nào của game")
    ck = _chu_ky(goi)
    try:
        with open(FILE_DO, encoding="utf-8") as f:
            cu = json.load(f)
        if cu.get("chu_ky") == ck and cu.get("phien_ban") == PHIEN_BAN_DO and cu.get("font"):
            return cu
    except Exception:
        pass
    # file co hieu luc: (bam, locale) -> goi uu tien cao nhat
    hl = {}
    for g in sorted(goi, key=lambda g: g["uu"]):
        for m in g["ds"]:
            hl[(m["bam"], m["locale"])] = (g, m)
    theo_id = {}
    for g in goi:
        theo_id.setdefault(g["id"], []).append(g)
    for v in theo_id.values():
        v.sort(key=lambda g: g["ten"].count("_"))   # goi chung truoc goi ngon ngu
    doc = _Doc()
    bst = []                     # (g, muc, drm)
    tong = len(hl)
    try:
        for i, ((bam, loc), (g, m)) in enumerate(hl.items()):
            if dung is not None and dung.is_set():
                raise LoiFont("đã dừng")
            if i % 2000 == 0:
                bao(f"Đang dò font chữ (lần đầu): đọc danh mục {i * 100 // max(tong, 1)}%...")
            if m["co"] < 32 or m["co"] > (32 << 20):
                continue
            p = vrt.duong_dan_phan(g["p"], m["phan"])
            try:
                dau = doc.khoi(p, m["vt"], can=32, toi_da=32)
                if len(dau) < 32 or struct.unpack_from("<i", dau, 0)[0] != 22:
                    continue
                du = doc.khoi(p, m["vt"], toi_da=m["co"])
                d = doc_drm(du)
            except Exception:
                continue
            if d:
                bst.append((g, m, d))
        # tai nguyen ung vien
        ung = {}
        for g, m, d in bst:
            for idn, loc in zip(d["ids"], d["locs"]):
                kich = idn["than"] + idn["ref"]
                if idn["loai"] in LOAI_BO or not 2000 < kich < (6 << 20):
                    continue
                ung.setdefault(loc, kich)
        bao(f"Đang dò font chữ: kiểm tra {len(ung):,} tài nguyên...".replace(",", "."))
        font = []
        moc = 0
        for j, (loc, kich) in enumerate(sorted(ung.items())):
            if dung is not None and dung.is_set():
                raise LoiFont("đã dừng")
            if time.time() - moc > 1.5:
                moc = time.time()
                bao(f"Đang dò font chữ: tài nguyên {j:,}/{len(ung):,} ({j * 100 // max(len(ung), 1)}%)...".replace(",", "."))
            goi_id, phan, vt, _, giai = loc
            for g in theo_id.get(goi_id, []):
                p = vrt.duong_dan_phan(g["p"], phan)
                if not os.path.isfile(p):
                    continue
                try:
                    du = doc.doan(p, vt, giai, 120)
                except Exception:
                    continue
                k = _tim_gfx(du)
                if k < 0:
                    continue
                try:
                    toan = doc.doan(p, vt, giai, kich)
                    gfx = fv.giai_gfx(toan[k:])
                    _, the = fv.tach_the(gfx)
                    ok = any(c == 75 and la_font_latin(fv.Font3(dl)) for c, dl in the)
                except Exception:
                    ok = False
                if ok:
                    font.append({"loc": list(loc), "p": g["ten"], "kich": kich,
                                 "md5": hashlib.md5(toan).hexdigest()})
                break
        if not font:
            raise LoiFont("không tìm thấy thư viện font chữ Latin của game")
        locs_font = {tuple(x["loc"]) for x in font}
        dung_bst = []
        for g, m, d in bst:
            idx = [i for i, loc in enumerate(d["locs"]) if tuple(loc) in locs_font]
            if idx:
                dung_bst.append({"p": g["ten"], "bam": m["bam"], "locale": m["locale"], "phan": m["phan"],
                                 "vt": m["vt"], "co": m["co"], "idx": idx})
    finally:
        doc.dong()
    kq = {"phien_ban": PHIEN_BAN_DO, "chu_ky": ck, "font": font, "bst": dung_bst}
    os.makedirs(os.path.dirname(FILE_DO), exist_ok=True)
    with open(FILE_DO, "w", encoding="utf-8") as f:
        json.dump(kq, f)
    return kq


# ================================================================ tao goi

def khoi_cdrm(du):
    """Nen du lieu thanh khoi CDRM (moi khuc <= 256 KB) giong game."""
    khuc = [du[i:i + 0x40000] for i in range(0, len(du), 0x40000)] or [b""]
    dau = struct.pack("<IiiI", vrt.MAGIC_CDRM, 0, len(khuc), 0)
    bang = bytearray(8 * len(khuc))
    than = bytearray()
    vt0 = (len(dau) + len(bang) + 0xF) & ~0xF
    for i, k in enumerate(khuc):
        z = zlib.compress(k, 9)
        loai = 2
        if len(z) >= len(k):
            z, loai = k, 1
        struct.pack_into("<II", bang, 8 * i, (len(k) << 8) | loai, len(z))
        than += z
        than += b"\0" * ((-(vt0 + len(than))) % 0x10)
    ra = dau + bytes(bang)
    ra += b"\0" * (vt0 - len(ra))
    return bytes(ra + than)


def chuan_bi(thu_muc, ttf, bao=lambda s: None, dung=None):
    """Tao du lieu font Viet de dua vao goi mod.
    -> {"tai_nguyen": [bytes khoi CDRM], "bst": [(bam, locale, ham(goi_id, vt_tai_nguyen) -> bytes drm moi)]}"""
    kq = do_font(thu_muc, bao, dung)
    goi = {g["ten"]: g for g in _cac_goi(thu_muc)}
    doc = _Doc()
    try:
        moi = {}                                  # loc goc -> (du_lieu_moi, ref)
        for x in kq["font"]:
            g = goi.get(x["p"])
            if g is None:
                raise LoiFont("game đã thay đổi – xóa kết quả dò và thử lại")
            goi_id, phan, vt, _, giai = x["loc"]
            p = vrt.duong_dan_phan(g["p"], phan)
            toan = doc.doan(p, vt, giai, x["kich"])
            k = _tim_gfx(toan)
            gfx_goc = toan[k:]
            L = struct.unpack_from("<I", gfx_goc, 4)[0]
            if gfx_goc[:1] in (b"G", b"F"):
                duoi = gfx_goc[L:]
                gfx_goc = gfx_goc[:L]
            else:
                duoi = b""
            bao("Đang thêm chữ tiếng Việt vào font của game...")
            gfx_moi, so = fv.them_tieng_viet(gfx_goc, ttf)
            if not so:
                continue
            truoc = bytearray(toan[:k])
            if k >= 4 and struct.unpack_from("<I", truoc, k - 4)[0] == L:
                struct.pack_into("<I", truoc, k - 4, len(gfx_moi))
            moi[tuple(x["loc"])] = bytes(truoc) + gfx_moi + duoi
        if not moi:
            raise LoiFont("font của game đã có đủ chữ tiếng Việt")
        cac_loc = list(moi)
        tai_nguyen = [khoi_cdrm(moi[l]) for l in cac_loc]
        bst = []
        for b in kq["bst"]:
            g = goi.get(b["p"])
            if g is None:
                continue
            du = doc.khoi(vrt.duong_dan_phan(g["p"], b["phan"]), b["vt"], toi_da=b["co"])
            d = doc_drm(du)
            if not d:
                continue
            bst.append((b["bam"], b["locale"], _ham_drm(du, d, cac_loc, moi, tai_nguyen)))
    finally:
        doc.dong()
    return {"tai_nguyen": tai_nguyen, "bst": bst, "so_chu": len(fv.CHU_VIET)}


def _ham_drm(du, d, cac_loc, moi, tai_nguyen):
    def tao(goi_id, cac_vt):
        b = bytearray(du)
        for i, loc in enumerate(d["locs"]):
            if tuple(loc) not in moi:
                continue
            j = cac_loc.index(tuple(loc))
            idn = d["ids"][i]
            ref = idn["ref"]
            # BodySize = kich moi - RefDefinitionsSize
            struct.pack_into("<I", b, d["vt_id"] + 20 * i, len(moi[tuple(loc)]) - ref)
            o = d["vt_loc"] + 24 * i
            struct.pack_into("<hhIII", b, o + 8, 0, goi_id, cac_vt[j], len(tai_nguyen[j]), 0)
        return bytes(b)
    return tao


def tao_goi_chung(duong_dan, ma, tai_nguyen, cac_tep):
    """Goi chung cua mod (locale tat ca): cac khoi tai nguyen (moi khoi + dau "NEXT") roi cac file.
    tai_nguyen: [bytes]; cac_tep: [(bam, locale, ham(cac_vt_tai_nguyen) -> bytes)]. -> vi tri cac tai nguyen."""
    cac_tep = sorted(cac_tep, key=lambda x: (x[0], x[1]))
    dau = struct.pack("<5i", vrt.MAGIC_TIGER, 4, 1, len(cac_tep), ma) + b"pcx64-w".ljust(0x20, b"\0")
    vt = len(dau) + 24 * len(cac_tep)
    than = bytearray()
    cac_vt, dau_next = [], []
    for tn in tai_nguyen:
        o = (vt + len(than) + 0xF) & ~0xF
        than += b"\0" * (o - vt - len(than))
        if dau_next:                                    # dau NEXT truoc: khoang cach toi tai nguyen nay
            struct.pack_into("<I", than, dau_next[-1] - vt + 4, o - dau_next[-1])
        cac_vt.append(o)
        than += tn
        than += b"\0" * ((-(vt + len(than))) % 0x10)
        dau_next.append(vt + len(than))
        than += struct.pack("<II", 0x5458454E, 0)       # "NEXT", 0 = tai nguyen cuoi
        than += b"\0" * ((-(vt + len(than))) % 0x10)
    bang = bytearray()
    for bam, loc, ham in cac_tep:
        du = ham(cac_vt)
        o = (vt + len(than) + 0xF) & ~0xF
        than += b"\0" * (o - vt - len(than))
        bang += struct.pack("<IIIIhhI", bam, loc, len(du), 0, 0, ma, o)
        than += du
    tam = duong_dan + ".tam"
    with open(tam, "wb") as f:
        f.write(dau + bytes(bang) + bytes(than))
    os.replace(tam, duong_dan)
    return cac_vt
