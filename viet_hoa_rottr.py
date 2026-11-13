# -*- coding: utf-8 -*-
"""
Viet hoa Rise of the Tomb Raider (engine Foundation / Crystal Dynamics).

  - Chu cua game nam trong file pcx64-w\\local\\locals.bin ben trong cac goi bigfile*.tiger
  - Doc locals.bin tieng Anh dang duoc game dung -> dich -> ghi locals.bin tieng Viet vao MOT GOI MOI
    bigfile._mod.viethoa_dichgame.000_ENGLISH.000.tiger (+ file .nfo) – khong sua file goc nao.
  - Go Viet hoa = xoa 2 file do.
Dinh dang tham khao tu TR Reboot Mod Tools (arcusmaximus, giay phep MIT).
"""

import json
import os
import re
import struct
import time
import unicodedata
import zlib

import viet_hoa_cd as vcd
from viet_hoa_cd import LoiDung

THU_MUC_RT = os.path.join(vcd.DU_LIEU, "rottr")
FILE_BO_NHO = os.path.join(THU_MUC_RT, "bo_nho_dich.json")

TEN_LOCALS = "pcx64-w\\local\\locals.bin"
LOCALE_EN = 0xFFFF0001
TEN_MOD = "viethoa_dichgame"
TEP_NFO = f"bigfile._mod.{TEN_MOD}.000.000.nfo"
TEP_TIGER = f"bigfile._mod.{TEN_MOD}.000_ENGLISH.000.tiger"
TEP_TIGER_GOC = f"bigfile._mod.{TEN_MOD}.000.000.tiger"   # goi chung (rong) - game bat buoc phai co
MAGIC_TIGER = 0x53464154
MAGIC_CDRM = 0x4D524443
NGON_NGU = ["ENGLISH", "FRENCH", "GERMAN", "ITALIAN", "LATAMSPANISH", "IBERSPANISH", "JAPANESE", "PORTUGUESE",
            "POLISH", "RUSSIAN", "DUTCH", "KOREAN", "CHINESE", "SIMPLECHINESE", "ARABIC"]


def bam_cdc(s):
    """CRC32 kieu Crystal Dynamics (MSB truoc, da thuc 0x04C11DB7)."""
    h = 0xFFFFFFFF
    for c in s:
        h ^= ord(c) << 24
        for _ in range(8):
            h = ((h << 1) ^ 0x04C11DB7) if h & 0x80000000 else (h << 1)
            h &= 0xFFFFFFFF
    return (~h) & 0xFFFFFFFF


BAM_LOCALS = bam_cdc(TEN_LOCALS)


# ================================================================ goi .tiger

def doc_tiger(duong_dan):
    """-> (dau, ds_muc). dau: id, so_phan, so_tep. muc: dict(bam, locale, co, phan, id, vt)."""
    with open(duong_dan, "rb") as f:
        d = f.read(0x34)
        if len(d) < 0x34:
            raise ValueError("file .tiger quá ngắn")
        magic, ban, so_phan, so_tep, ma = struct.unpack_from("<5i", d, 0)
        if magic != MAGIC_TIGER:
            raise ValueError("không phải file .tiger")
        if ban != 4:
            raise ValueError(f"file .tiger phiên bản {ban} (cần 4 – Rise of the Tomb Raider)")
        bang = f.read(24 * so_tep)
    ds = []
    for i in range(so_tep):
        bam, loc, co, co_nen, phan, ma_g, vt = struct.unpack_from("<IIIIhhI", bang, 24 * i)
        ds.append({"bam": bam, "locale": loc, "co": co, "phan": phan, "id": ma_g, "vt": vt})
    return {"id": ma, "so_phan": so_phan, "so_tep": so_tep}, ds


def duong_dan_phan(duong_dan, phan):
    return duong_dan.replace(".000.tiger", f".{phan:03d}.tiger") if phan else duong_dan


def doc_tep_tiger(duong_dan, muc):
    """Noi dung 1 file trong goi (giai nen CDRM neu can)."""
    with open(duong_dan_phan(duong_dan, muc["phan"]), "rb") as f:
        f.seek(muc["vt"])
        dau = f.read(16)
        if len(dau) >= 16 and struct.unpack_from("<I", dau, 0)[0] == MAGIC_CDRM:
            so_khuc = struct.unpack_from("<i", dau, 8)[0]
            bang = f.read(8 * so_khuc)
            vt = muc["vt"] + 16 + 8 * so_khuc
            vt = (vt + 0xF) & ~0xF
            ra = bytearray()
            for i in range(so_khuc):
                goc, nen = struct.unpack_from("<ii", bang, 8 * i)
                goc >>= 8
                f.seek(vt)
                b = f.read(nen)
                ra += b if nen == goc else zlib.decompress(b)
                vt = (vt + nen + 0xF) & ~0xF
            return bytes(ra)
        f.seek(muc["vt"])
        return f.read(muc["co"])


def tao_tiger(duong_dan, ma, cac_tep):
    """Goi .tiger moi (1 phan). cac_tep: [(bam, locale, du_lieu)]."""
    dau = struct.pack("<5i", MAGIC_TIGER, 4, 1, len(cac_tep), ma) + b"pcx64-w".ljust(0x20, b"\0")
    vt = len(dau) + 24 * len(cac_tep)
    bang, than = b"", b""
    for bam, loc, du_lieu in cac_tep:
        dem = (-(vt + len(than))) % 0x10
        than += b"\0" * dem
        bang += struct.pack("<IIIIhhI", bam, loc, len(du_lieu), 0, 0, ma, vt + len(than))
        than += du_lieu
    tam = duong_dan + ".tam"
    with open(tam, "wb") as f:
        f.write(dau + bang + than)
    os.replace(tam, duong_dan)


# ================================================================ .nfo

def doc_nfo(duong_dan):
    with open(duong_dan, encoding="utf-8", errors="replace") as f:
        dong = [x.strip() for x in f.read().splitlines()]
    dau = dong[0].split(" ") if dong else [""]
    tt = {"ten": dau[0], "custom": []}
    for i in range(1, len(dau) - 1, 2):
        try:
            tt[dau[i]] = int(dau[i + 1])
        except ValueError:
            pass
    for x in dong[1:]:
        if x.startswith("custom "):
            tt["custom"].append(x[7:])
    return tt


def ghi_nfo(duong_dan, bap, phien_ban, ma, steam=None):
    ten = os.path.basename(duong_dan).replace("bigfile.", "", 1)
    ten = ten[:-len(".nfo")].replace(".000", "")
    dong = [f"{ten} bap {bap} package {ma} chunk 0 version {phien_ban} required 1 bigfile 1 dlcindex {ma} "
            f"mount 0 unmount 1"]
    if steam:
        dong.append(f"custom {steam}")
    dong.append("custom mod:Viet hoa (Dich Game)")
    with open(duong_dan, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(dong) + "\r\n")


# ================================================================ locals.bin

def doc_locals(b):
    """-> (ma_ngon_ngu, khoa_dac_biet[list int], chuoi{so: str}, so_vi_tri)"""
    lang, so_khoa, so_chuoi = struct.unpack_from("<iii", b, 0)
    o = 12
    khoa = list(struct.unpack_from(f"<{so_khoa}i", b, o)) if so_khoa else []
    o += 4 * so_khoa
    chuoi = {}
    for i in range(so_chuoi):
        p = struct.unpack_from("<q", b, o + 8 * i)[0]
        if p <= 0 or p >= len(b):
            continue
        j = b.index(b"\0", p)
        chuoi[i] = b[p:j].decode("utf-8", "replace")
    return lang, khoa, chuoi, so_chuoi


def ghi_locals(lang, khoa, chuoi, so_chuoi=None):
    n = max(so_chuoi or 0, (max(chuoi) + 1) if chuoi else 0)
    dau = struct.pack("<iii", lang, len(khoa), n) + (struct.pack(f"<{len(khoa)}i", *khoa) if khoa else b"")
    bat_dau = len(dau) + 8 * n
    con_tro = bytearray(8 * n)
    than = bytearray()
    for i in range(n):
        s = chuoi.get(i)
        if s is None:
            continue
        struct.pack_into("<q", con_tro, 8 * i, bat_dau + len(than))
        than += s.encode("utf-8") + b"\0"
    return dau + bytes(con_tro) + bytes(than)


def bo_dau(s):
    """Tieng Viet khong dau (du phong khi font game khong co dau tieng Viet)."""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# ================================================================ quet thu muc game

def la_rottr(thu_muc):
    return os.path.isfile(os.path.join(thu_muc, "ROTTR.exe")) or os.path.isfile(
        os.path.join(thu_muc, "bigfile_ENGLISH.000.tiger"))


def _thu_tu_ngon_ngu(ten_tep):
    goc = ten_tep.replace(".000.tiger", "")
    for i, ng in enumerate(NGON_NGU):
        if goc.upper().endswith(ng):
            return i + 1
    return 0


def quet(thu_muc):
    """Tim locals.bin tieng Anh dang duoc game dung (bo qua cac goi mod) + thong tin de tao goi mod.
    -> dict(nguon=(duong_dan, muc), bap, steam, phien_ban_max, id_max)"""
    meta = {}
    for t in os.listdir(thu_muc):
        if t.endswith(".nfo") and not t.startswith("bigfile._mod."):
            try:
                m = doc_nfo(os.path.join(thu_muc, t))
                meta[m.get("dlcindex", -1)] = m
            except Exception:
                pass
    ung_vien, id_max = [], 0
    for t in os.listdir(thu_muc):
        if not t.endswith(".000.tiger") or not t.startswith("bigfile"):
            continue
        if TEN_MOD in t:   # goi cua chinh app: cai lai se thay the
            continue
        p = os.path.join(thu_muc, t)
        try:
            dau, ds = doc_tiger(p)
        except Exception:
            continue
        id_max = max(id_max, dau["id"])
        if t.startswith("bigfile._mod."):
            continue
        m = meta.get(dau["id"])
        if m is None:
            continue
        for muc in ds:
            if muc["bam"] == BAM_LOCALS and (muc["locale"] == 0xFFFFFFFF or muc["locale"] & 1):
                khoa = (m.get("version", 0), -m.get("required", 1), m.get("package", 0), m.get("chunk", 0),
                        _thu_tu_ngon_ngu(t))
                ung_vien.append((khoa, p, muc))
    for t in os.listdir(thu_muc):   # id cua goi mod khac cung tinh vao
        if t.startswith("bigfile._mod.") and t.endswith(".nfo") and TEN_MOD not in t:
            try:
                id_max = max(id_max, doc_nfo(os.path.join(thu_muc, t)).get("dlcindex", 0))
            except Exception:
                pass
    if not ung_vien:
        raise LoiDung("không tìm thấy file chữ tiếng Anh (locals.bin) trong các gói .tiger của game")
    ung_vien.sort(key=lambda x: x[0])
    _, p, muc = ung_vien[-1]
    bap = next((m["bap"] for m in meta.values() if m.get("bap")), 0)
    steam = next((c for m in meta.values() for c in m["custom"] if c.startswith("steamID:")), None)
    return {"nguon": (p, muc), "bap": bap, "steam": steam,
            "phien_ban_max": max(m.get("version", 0) for m in meta.values()), "id_max": id_max}


# ================================================================ cong viec Viet hoa

HUONG_DAN_ROTTR = """Bạn là dịch giả chuyên Việt hóa game. Game: Rise of the Tomb Raider (phiêu lưu hành động; \
nhân vật chính Lara Croft đi tìm thành phố cổ Kitezh ở Siberia; tổ chức Trinity; người Remnant; Deathless Ones).
Bạn nhận một mảng JSON các chuỗi tiếng Anh lấy từ file chữ của game và trả về mảng JSON các bản dịch tiếng Việt.

Quy tắc bắt buộc:
- CHỈ trả về một mảng JSON hợp lệ, CÙNG SỐ PHẦN TỬ, CÙNG THỨ TỰ. Không giải thích, không ```.
- GIỮ NGUYÊN tiếng Anh: tên người, địa danh, tổ chức, phe phái, tên vũ khí / trang bị / kỹ năng riêng, \
và mọi từ trong danh sách "Giữ nguyên" nếu có.
- Giữ NGUYÊN từng ký tự mọi thẻ và mã: <...>, {...}, [...], %s, %d, \\n, $..., kể cả khoảng trắng quanh chúng. \
Không dịch, không thêm, không bớt thẻ.
- Giữ nguyên số, ký hiệu, khoảng trắng đầu/cuối và cách xuống dòng.
- Văn phong tự nhiên như phụ đề phim phiêu lưu hiện đại. Lara xưng "tôi"; xưng hô hợp ngữ cảnh.
- Menu, nút bấm, tiêu đề: ngắn gọn, rõ nghĩa như game Việt hóa chính thức.
- Chuỗi chỉ gồm tên riêng hoặc không có gì để dịch: trả lại y nguyên."""

TEN_RIENG = ["Lara", "Croft", "Lara Croft", "Lord Croft", "Richard Croft", "Jonah", "Jacob", "Ana", "Konstantin",
             "Sofia", "Nadia", "Trinity", "Remnant", "Kitezh", "Siberia", "Syria", "Baba Yaga", "Deathless Ones",
             "Divine Source", "Prophet", "Atlas", "Croft Manor", "Soviet", "Geothermal Valley", "Lost City",
             "Ice Cave", "Acropolis", "Copper Mill", "Gulag", "Flooded Archives", "Kitezh"]

# chu menu de lam GOI THU font (co du dau tieng Viet)
CHU_THU = {
    "continue": "Tiếp tục", "options": "Tùy chọn", "new game": "Trò chơi mới", "load game": "Tải màn chơi",
    "quit": "Thoát", "quit game": "Thoát trò chơi", "exit": "Thoát", "extras": "Phần thêm",
    "credits": "Danh sách – ắằẳẵặ ếềểễệ ốồổỗộ ớờởỡợ ứừửữự ỳỷỹỵ đĐ", "resume": "Chơi tiếp",
    "display": "Hiển thị", "audio": "Âm thanh", "controls": "Điều khiển", "graphics": "Đồ họa",
    "language": "Ngôn ngữ", "subtitles": "Phụ đề", "yes": "Đồng ý", "no": "Không", "back": "Quay lại",
    "select": "Chọn", "settings": "Cài đặt", "game": "Trò chơi", "expeditions": "Thám hiểm",
    "story": "Cốt truyện", "main menu": "Về menu chính", "quit to main menu": "Về menu chính",
}


class ViecRottr(vcd.ViecDich):
    """Dung lai bo may dich (Claude theo lo / Offline) cua Viet hoa Crimson Desert."""
    HUONG_DAN = HUONG_DAN_ROTTR
    THE = re.compile(r"<[^<>]*>|\{[^{}]*\}|\[[^\[\]]*\]|%[0-9]*[sdif]|\\n|\$[A-Za-z_][A-Za-z0-9_]*")

    def __init__(self, thu_muc_game):
        super().__init__(thu_muc_game, 1)
        self.tt = None
        self.goc = {}
        self.locals = None

    def nap(self, bao=lambda s: None):
        bao("Đang tìm file chữ tiếng Anh của game (locals.bin)...")
        self.tt = quet(self.thu_muc_game)
        p, muc = self.tt["nguon"]
        bao(f"Đang đọc chữ từ {os.path.basename(p)}...")
        self.locals = doc_locals(doc_tep_tiger(p, muc))
        self.goc = self.locals[2]
        self.bang_ten = vcd.BangTen(set(TEN_RIENG))
        try:
            with open(FILE_BO_NHO, encoding="utf-8") as f:
                self.bo_nho = json.load(f)
        except Exception:
            self.bo_nho = {}
        return self

    def luu(self):
        os.makedirs(THU_MUC_RT, exist_ok=True)
        with self.khoa:
            du_lieu = json.dumps(self.bo_nho, ensure_ascii=False)
        tam = FILE_BO_NHO + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            f.write(du_lieu)
        os.replace(tam, FILE_BO_NHO)

    def nen_dich(self, f, v, dot=None):
        t = self.THE.sub("", v).strip()
        if not t or not re.search(r"[A-Za-z]{2,}", t):
            return False
        if re.fullmatch(r"[A-Za-z0-9_./\\-]+", t) and ("_" in t or "/" in t or "\\" in t):
            return False   # ma noi bo (IDS_..., duong dan)
        return not self.bang_ten.la_ten(v)

    def _chuoi_cua_dot(self):
        for v in self.goc.values():
            if self.nen_dich(None, v):
                yield v

    def cau_can_dich(self):
        ds, da = [], set()
        for v in self._chuoi_cua_dot():
            if v in da:
                continue
            vi = self.bo_nho.get(v)
            if vi is not None and (vi == v or self._the(vi) == self._the(v)):
                continue
            da.add(v)
            ds.append(v)
        return ds

    def thong_ke(self):
        tat_ca = set(self._chuoi_cua_dot())
        con = self.cau_can_dich()
        return {"tong": len(tat_ca), "da_dich": len(tat_ca) - len(con), "con": len(con),
                "ky_tu_con": sum(len(v) for v in con)}

    def _the(self, s):
        return sorted(self.THE.findall(s))

    def chuoi_viet(self, en, khong_dau=False):
        vi = self.bo_nho.get(en)
        if not vi or vi == en or self._the(vi) != self._the(en):
            return None
        return bo_dau(vi) if khong_dau else vi

    # ---------------------------------------------------------- cai / go
    def da_cai(self):
        return os.path.isfile(os.path.join(self.thu_muc_game, TEP_TIGER))

    def cai(self, khong_dau=False, chi_thu=False):
        """Ghi goi mod vao thu muc game. chi_thu: chi doi chu menu (kiem tra font). -> so chuoi da doi."""
        lang, khoa, goc, n = self.locals
        moi = dict(goc)
        doi = 0
        for i, en in goc.items():
            if chi_thu:
                vi = CHU_THU.get(en.strip().lower())
                if vi and khong_dau:
                    vi = bo_dau(vi)
            else:
                vi = self.chuoi_viet(en, khong_dau)
            if vi:
                moi[i] = vi
                doi += 1
        if not doi:
            raise LoiDung("chưa có câu nào được dịch – bấm Dịch trước")
        self.go()
        tt = self.tt
        ma = tt["id_max"] + 1
        du_lieu = ghi_locals(lang, khoa, moi, n)
        tao_tiger(os.path.join(self.thu_muc_game, TEP_TIGER_GOC), ma, [])
        tao_tiger(os.path.join(self.thu_muc_game, TEP_TIGER), ma, [(BAM_LOCALS, LOCALE_EN, du_lieu)])
        ghi_nfo(os.path.join(self.thu_muc_game, TEP_NFO), tt["bap"], tt["phien_ban_max"] + 1, ma, tt["steam"])
        return doi

    def go(self):
        for t in (TEP_TIGER, TEP_TIGER_GOC, TEP_NFO, TEP_NFO + ".disabled"):
            p = os.path.join(self.thu_muc_game, t)
            if os.path.isfile(p):
                os.remove(p)
