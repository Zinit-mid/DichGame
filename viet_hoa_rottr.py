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
import rottr_mul as rm

THU_MUC_RT = os.path.join(vcd.DU_LIEU, "rottr")
FILE_BO_NHO = os.path.join(THU_MUC_RT, "bo_nho_dich.json")
FILE_MUL = os.path.join(THU_MUC_RT, "muc_luc_mul.json")      # muc luc file .mul (phu de + giong) da quet
PHIEN_BAN_MUL = 2

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
    """Goi .tiger moi (1 phan). cac_tep: [(bam, locale, du_lieu)] – tu xep theo (bam, locale)."""
    cac_tep = sorted(cac_tep, key=lambda x: (x[0], x[1]))
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


def tao_tiger_lon(duong_dan, ma, cac_tep, bao=lambda s: None):
    """Nhu tao_tiger nhung ghi dan ra dia (goi lon). cac_tep: [(bam, locale, ham_lay_bytes)].
    BANG FILE PHAI XEP THEO (bam, locale) – game tim file kieu nhi phan, sai thu tu = mat ca goi."""
    cac_tep = sorted(cac_tep, key=lambda x: (x[0], x[1]))
    dau = struct.pack("<5i", MAGIC_TIGER, 4, 1, len(cac_tep), ma) + b"pcx64-w".ljust(0x20, b"\0")
    bang = bytearray(24 * len(cac_tep))
    tam = duong_dan + ".tam"
    with open(tam, "wb") as f:
        f.write(dau + bytes(bang))
        vt = len(dau) + len(bang)
        for i, (bam, loc, ham) in enumerate(cac_tep):
            dem = (-vt) % 0x10
            f.write(b"\0" * dem)
            vt += dem
            du_lieu = ham()
            struct.pack_into("<IIIIhhI", bang, 24 * i, bam, loc, len(du_lieu), 0, 0, ma, vt)
            f.write(du_lieu)
            vt += len(du_lieu)
            if vt > 0x7FFFFFF0:
                raise LoiDung("gói Việt hóa vượt 2 GB")
            if i % 200 == 0:
                bao(f"Đang ghi gói Việt hóa: {i:,}/{len(cac_tep):,} file".replace(",", "."))
        f.seek(len(dau))
        f.write(bytes(bang))
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


_LATIN1 = set(chr(c) for c in range(0xC0, 0x100))


def dau_ghep(s):
    """Font game chi co chu co dau Latin-1 (À Á Â Ã È É Ê Ì Í Ò Ó Ô Õ Ù Ú Ý...), thieu Ế Ụ Ọ Ớ Ử Đ...
    -> giu chu font co, chu thieu thi ghep chu cai + dau roi (U+0300..U+0323); Đ -> D."""
    ra = []
    for ch in unicodedata.normalize("NFC", s):
        if ord(ch) < 0x80 or ch in _LATIN1:
            ra.append(ch)
            continue
        if ch in "đĐ":
            ra.append("d" if ch == "đ" else "D")
            continue
        d = unicodedata.normalize("NFD", ch)
        goc, dau = d[0], d[1:]
        if not dau:
            ra.append(ch)
            continue
        tot = goc + dau
        for i in range(len(dau)):
            c = unicodedata.normalize("NFC", goc + dau[i])
            if c in _LATIN1:
                tot = c + dau[:i] + dau[i + 1:]
                break
        ra.append(tot)
    return "".join(ra)


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


def goi_tieng_anh(thu_muc):
    """Cac goi .tiger chua file tieng Anh, xep theo uu tien tang dan (goi sau de len goi truoc)."""
    meta = {}
    for t in os.listdir(thu_muc):
        if t.endswith(".nfo") and not t.startswith("bigfile._mod."):
            try:
                m = doc_nfo(os.path.join(thu_muc, t))
                meta[m.get("dlcindex", -1)] = m
            except Exception:
                pass
    ds = []
    for t in os.listdir(thu_muc):
        if not t.endswith(".000.tiger") or not t.startswith("bigfile") or t.startswith("bigfile._mod."):
            continue
        if "_ENGLISH" not in t.upper() or "KSA_" in t.upper():
            continue
        p = os.path.join(thu_muc, t)
        try:
            dau, muc = doc_tiger(p)
        except Exception:
            continue
        m = meta.get(dau["id"])
        if m is None:
            continue
        khoa = (m.get("version", 0), -m.get("required", 1), m.get("package", 0), m.get("chunk", 0),
                _thu_tu_ngon_ngu(t))
        ds.append((khoa, p, muc))
    ds.sort(key=lambda x: x[0])
    return ds


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
        self.mul = {}

    def nap(self, bao=lambda s: None):
        bao("Đang tìm file chữ tiếng Anh của game (locals.bin)...")
        self.tt = quet(self.thu_muc_game)
        p, muc = self.tt["nguon"]
        bao(f"Đang đọc chữ từ {os.path.basename(p)}...")
        self.locals = doc_locals(doc_tep_tiger(p, muc))
        self.goc = self.locals[2]
        self.bang_ten = vcd.BangTen(set(TEN_RIENG))
        try:
            self.quet_mul(bao)
        except Exception as e:
            self.loi_mul = str(e)
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
        chi = getattr(self, "chi_cau", None)
        if chi is not None:          # chi dich mot nhom cau (goi thu long tieng)
            yield from chi
            return
        for v in self.goc.values():
            if self.nen_dich(None, v):
                yield v
        for v in self.cau_phu_de():
            if self.nen_dich(None, v):
                yield v

    # ---------------------------------------------------------- phu de phim / giong noi (.mul)
    def cau_phu_de(self):
        for tt in (self.mul or {}).values():
            for _, en in tt["pd"]:
                if en:
                    yield en

    def quet_mul(self, bao=lambda s: None):
        """Muc luc moi file .mul tieng Anh dang duoc game dung (goi uu tien cao nhat) co phu de.
        Luu dem vao FILE_MUL, chi quet lai khi goi game thay doi."""
        goi = goi_tieng_anh(self.thu_muc_game)
        dau_van = [[os.path.basename(p), os.path.getsize(p), int(os.path.getmtime(p))] for _, p, _ in goi]
        try:
            with open(FILE_MUL, encoding="utf-8") as f:
                cu = json.load(f)
            if cu.get("ban") == PHIEN_BAN_MUL and cu.get("goi") == dau_van and \
                    os.path.normcase(cu.get("game", "")) == os.path.normcase(self.thu_muc_game):
                self.mul = cu["mul"]
                return self.mul
        except Exception:
            pass
        chon = {}
        for _, p, ds in goi:
            for muc in ds:
                if muc["locale"] & 1:
                    chon[muc["bam"]] = (p, muc)
        kq, n = {}, 0
        for bam, (p, muc) in chon.items():
            n += 1
            if n % 300 == 0:
                bao(f"Đang quét phụ đề phim và giọng nói: {n:,}/{len(chon):,} file".replace(",", "."))
            if self.dung.is_set():
                raise LoiDung("đã dừng")
            try:
                if muc["co"] < 0x2010:
                    continue
                with open(duong_dan_phan(p, muc["phan"]), "rb") as f:
                    f.seek(muc["vt"])
                    dau = f.read(rm.HDR.size)
                if struct.unpack_from("<I", dau, 0)[0] == MAGIC_CDRM:
                    dau = doc_tep_tiger(p, muc)
                if struct.unpack_from("<i", dau, 0)[0] != 44100 or not rm.HDR.unpack_from(dau, 0)[9]:
                    continue          # khong phai .mul / khong co phu de
                x = rm.Mul(doc_tep_tiger(p, muc))
            except Exception:
                continue
            pd = [[x.goi[i][1].khung, d.get("0", "")] for i, d in x.phu_de()]
            if not any(en for _, en in pd):
                continue
            tt = {"goi": os.path.basename(p), "muc": muc, "k": x.so_kenh, "phim": x.co_phim, "pd": pd,
                  "ten": "", "mau": 0}
            try:
                loai = list(x.hdr[-1][:x.so_kenh])
                kenh = []
                for c, f in enumerate(x.fsb_kenh()):
                    ten, so, _ = rm.fsb_thong_tin(f)
                    kenh.append([loai[c], ten, so])
                tt["kenh"] = kenh
                tt["ten"], tt["mau"] = kenh[0][1], kenh[0][2]
                giong = [k for k in kenh if self.la_kenh_giong(k, x.so_kenh)]
                if giong:
                    tt["ten"], tt["mau"] = giong[0][1], max(k[2] for k in giong)
            except Exception:
                pass
            kq[f"{bam:08x}"] = tt
        os.makedirs(THU_MUC_RT, exist_ok=True)
        with open(FILE_MUL + ".tam", "w", encoding="utf-8") as f:
            json.dump({"ban": PHIEN_BAN_MUL, "game": self.thu_muc_game, "goi": dau_van, "mul": kq}, f,
                      ensure_ascii=False)
        os.replace(FILE_MUL + ".tam", FILE_MUL)
        self.mul = kq
        return kq

    def doc_mul(self, ma):
        tt = self.mul[ma]
        return rm.Mul(doc_tep_tiger(os.path.join(self.thu_muc_game, tt["goi"]), tt["muc"]))

    def phu_de_viet(self, en, khong_dau=False):
        vi = self.chuoi_viet(en, khong_dau) if en else None
        return vi

    @staticmethod
    def nguoi_noi(ten_fsb):
        """'610_by_050_230_nadia.str_0' -> 'nadia'; 'looter_a' -> 'looter'."""
        goc = ten_fsb.split(".")[0].split("#")[0]
        t = [x for x in goc.split("_") if x]
        j = max([i for i, v in enumerate(t) if v.isdigit()], default=-1)
        t = t[j + 1:]
        if len(t) > 1 and len(t[-1]) == 1:
            t = t[:-1]
        return "_".join(t).lower() or "khac"

    @staticmethod
    def chu_de_doc(vi):
        """Bo the [..] / <..> / *tieng cuoi* de VieNeu doc."""
        t = re.sub(r"\[[^\[\]]*\]|<[^<>]*>|\{[^{}]*\}|\*[^*]*\*", " ", vi)
        t = re.sub(r"^\s*[A-ZÀ-Ỹ][\wÀ-ỹ.'\- ]{0,24}:\s+", "", t)          # "Lara:  ..." -> bo ten nguoi noi
        t = re.sub(r"\s+", " ", t).strip(" -–")
        return t if re.search(r"[A-Za-zÀ-ỹ]{2,}", t) else ""

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

    def chuoi_viet(self, en, khong_dau=False, goc=False):
        vi = self.bo_nho.get(en)
        if not vi or vi == en or self._the(vi) != self._the(en):
            return None
        if goc:
            return vi
        return bo_dau(vi) if khong_dau else dau_ghep(vi)

    # ---------------------------------------------------------- cai / go
    def da_cai(self):
        return os.path.isfile(os.path.join(self.thu_muc_game, TEP_TIGER))

    def cai(self, khong_dau=False, chi_thu=False, bao=lambda s: None):
        """Ghi goi mod vao thu muc game. chi_thu: chi doi chu menu (kiem tra font). -> so chuoi da doi."""
        lang, khoa, goc, n = self.locals
        moi = dict(goc)
        doi = 0
        for i, en in goc.items():
            if chi_thu:
                vi = CHU_THU.get(en.strip().lower())
                if vi:
                    vi = bo_dau(vi) if khong_dau else dau_ghep(vi)
            else:
                vi = self.chuoi_viet(en, khong_dau)
            if vi:
                moi[i] = vi
                doi += 1
        tt = self.tt
        ma = tt["id_max"] + 1
        du_lieu = ghi_locals(lang, khoa, moi, n)
        cac = [(BAM_LOCALS, LOCALE_EN, lambda: du_lieu)]
        self.so_cai = {"phu_de": 0, "giong": 0}
        if not chi_thu:
            for m, t in sorted(self.mul.items()):
                giong = self.file_giong(m)
                if giong or any(self.chuoi_viet(en, khong_dau) for _, en in t["pd"] if en):
                    cac.append((int(m, 16), t["muc"]["locale"],
                                lambda m=m, giong=giong: self._mul_moi(m, khong_dau, giong)))
        if not doi and len(cac) == 1:
            raise LoiDung("chưa có câu nào được dịch – bấm Dịch trước")
        tam = os.path.join(self.thu_muc_game, TEP_TIGER + ".moi")
        tao_tiger_lon(tam, ma, cac, bao)
        self.go()
        os.replace(tam, os.path.join(self.thu_muc_game, TEP_TIGER))
        tao_tiger(os.path.join(self.thu_muc_game, TEP_TIGER_GOC), ma, [])
        ghi_nfo(os.path.join(self.thu_muc_game, TEP_NFO), tt["bap"], tt["phien_ban_max"] + 1, ma, tt["steam"])
        return doi

    def _mul_moi(self, ma, khong_dau, giong):
        x = self.doc_mul(ma)
        try:
            for _, d in x.phu_de():
                en = d.get("0")
                vi = self.chuoi_viet(en, khong_dau) if en else None
                if vi:
                    d["0"] = vi
                    if d.get("14") == en:
                        d["14"] = vi
                    self.so_cai["phu_de"] += 1
            if giong:
                fsb = list(x.fsb_kenh())
                for c, p in giong.items():
                    with open(p, "rb") as f:
                        mp3 = f.read()
                    for cc in (c, self.kenh_phai(self.mul[ma], c)):
                        if cc is not None and cc < len(fsb):
                            fsb[cc] = rm.tao_fsb4(mp3, rm.fsb_thong_tin(fsb[cc])[0], fsb[cc])
                x.thay_am_thanh(fsb)
                self.so_cai["giong"] += 1
            return x.ghi()
        except Exception:
            return self.doc_mul(ma).ghi()

    def go(self):
        for t in (TEP_TIGER, TEP_TIGER_GOC, TEP_NFO, TEP_NFO + ".disabled", TEP_TIGER + ".moi.tam"):
            p = os.path.join(self.thu_muc_game, t)
            if os.path.isfile(p):
                os.remove(p)

    # ---------------------------------------------------------- long tieng (VieNeu)
    @staticmethod
    def la_kenh_giong(k, so_kenh):
        """k = [loai, ten_fsb, so_mau]. File 1 kenh = loi thoai. Nhieu kenh: kenh '#group..' / '_vo_' = giong
        nhan vat (mono, hoac kenh TRAI cua cap trai/phai – kenh phai lay cung giong); nhac / tieng dong thi khong."""
        if so_kenh == 1:
            return True
        ten = (k[1] or "").lower()
        if any(x in ten for x in ("music", "_mus", "musi", "sfx", "_amb", "ambien")):
            return False
        # ten FSB bi cat con 29 ky tu: "...#grou", "...#gr" -> chi can co "#"
        return k[0] in (0, 1) and ("#" in ten or "_vo_" in ten or "_vo." in ten)

    @staticmethod
    def kenh_phai(t, c):
        """Kenh phai di cap voi kenh trai c (cung ten) -> chi so, hoac None."""
        kenh = t.get("kenh") or []
        if c + 1 < len(kenh) and kenh[c][0] == 1 and kenh[c + 1][0] == 2 and kenh[c + 1][1] == kenh[c][1]:
            return c + 1
        return None

    def thu_muc_giong(self):
        return os.path.join(vcd.ViecDich.thu_muc_lam_viec(self.thu_muc_game), "RotTR")

    BAN_MAU = "v2"           # doi khi doi cach chon giong mau -> tao lai giong mau + doc lai

    def _mau(self, g):
        return os.path.join(self.thu_muc_giong(), "mau", f"{g}.{self.BAN_MAU}.wav")

    def _thu_wav(self, g):
        return os.path.join(self.thu_muc_giong(), "wav", f"{g}.{self.BAN_MAU}")

    def _ten_mp3(self, ma, c):
        t = self.mul.get(ma, {})
        return os.path.join(self.thu_muc_giong(), "mp3", ma + (".mp3" if t.get("k", 1) == 1 else f"_{c}.mp3"))

    def file_giong(self, ma):
        """-> {kenh: duong_dan_mp3} cac kenh da long tieng cua 1 file .mul ({} neu chua)."""
        t = self.mul.get(ma)
        if not t:
            return {}
        ra = {}
        for c in range(t.get("k", 1)):
            p = self._ten_mp3(ma, c)
            if os.path.isfile(p):
                ra[c] = p
        return ra

    def mul_long_tieng_duoc(self):
        ra = {}
        for m, t in self.mul.items():
            if t.get("phim") or not t.get("kenh"):
                continue
            kg = [c for c, k in enumerate(t["kenh"]) if self.la_kenh_giong(k, t["k"])]
            if kg:
                ra[m] = dict(t, kg=kg)
        return ra

    def thong_ke_mul(self):
        cau = [en for t in self.mul.values() for _, en in t["pd"] if en]
        long = self.mul_long_tieng_duoc()
        return {"file": len(self.mul), "cau": len(cau), "da_dich": sum(1 for en in cau if self.chuoi_viet(en)),
                "phim": sum(1 for t in self.mul.values() if t["k"] > 1),
                "giong": len(long), "da_long": sum(1 for m in long if self.file_giong(m))}

    TEN_NOI = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*([A-Z][A-Za-z.'\- ]{1,24}):\s")

    def _cau_doc(self, t):
        """-> [(khung, chu_viet_de_doc | '', ten_nguoi_noi_tieng_anh | None)] (bo khung xoa phu de)."""
        ra = []
        for khung, en in t["pd"]:
            if not en:
                continue
            vi = self.chuoi_viet(en, goc=True)
            m = self.TEN_NOI.match(en)
            ra.append((khung, self.chu_de_doc(vi) if vi else "", m.group(1).strip().lower().replace(" ", "_") if m else None))
        return ra

    def _xuat_mp3_goc(self, ma, c, thu):
        p = os.path.join(thu, f"{ma}_{c}.mp3")
        if not os.path.isfile(p):
            x = self.doc_mul(ma)
            _, _, d = rm.fsb_thong_tin(x.fsb_kenh()[c])
            with open(p + ".tam", "wb") as f:
                f.write(b"".join(rm.mp3_khung(d)))
            os.replace(p + ".tam", p)
        return p

    def _chay_kich_ban(self, ten, noi_dung, viec, py, hf, bao, nhan):
        import subprocess
        tam = os.path.join(THU_MUC_RT, "vieneu_tam")
        os.makedirs(tam, exist_ok=True)
        kb = os.path.join(tam, ten + ".py")
        with open(kb, "w", encoding="utf-8") as f:
            f.write(noi_dung)
        vj = os.path.join(tam, ten + ".json")
        with open(vj, "w", encoding="utf-8") as f:
            json.dump(viec, f, ensure_ascii=False)
        env = dict(os.environ, HF_HOME=hf, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        an = 0x08000000 if os.name == "nt" else 0
        cuoi = []
        p = subprocess.Popen([py, "-I", kb, vj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                             cwd=tam, creationflags=an)
        for dong in iter(p.stdout.readline, b""):
            d = dong.decode("utf-8", "replace").rstrip()
            if self.dung.is_set():
                p.kill()
                break
            if d.startswith("XONG "):
                a, b = d.split()[1:3]
                bao(f"{nhan} {a}/{b}")
            elif d.strip():
                cuoi = (cuoi + [d])[-4:]
        p.wait()
        if self.dung.is_set():
            return False
        if p.returncode != 0:
            raise LoiDung(f"{nhan} bị lỗi:\n" + "\n".join(cuoi[-3:]))
        return True

    @staticmethod
    def thu_tu_game(ten_fsb):
        """'100_bp_115_090_lara.str_0' -> khoa xep theo tien trinh game (so dau ten = khu vuc / man)."""
        t = (ten_fsb or "").split(".")[0].split("#")[0].split("_")
        return tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in t)

    def dich_truoc(self, cac_cau, may="claude", khoa=None, gioi_han=0.5, bao=lambda s: None):
        """Dich ngay mot nhom cau (goi thu) bang may da chon."""
        can = [c for c in dict.fromkeys(cac_cau) if not self.chuoi_viet(c, goc=True)]
        if not can:
            return
        self.chi_cau = can
        try:
            bao(f"Đang dịch {len(can)} câu thoại cho gói thử...")
            if may == "offline":
                self.chay_offline(bao, lambda a, b, t: None)
            else:
                if not khoa:
                    raise LoiDung("chưa có mã Claude – lưu mã trong Cài đặt, hoặc chọn máy dịch Offline")
                self.chay(khoa, gioi_han, bao, lambda a, b, t: None)
        finally:
            self.chi_cau = None

    def long_tieng(self, thu=False, bao=lambda s: None, tien_do=lambda a, b, s: None, may="claude", khoa=None,
                   tang_db=4.0):
        """thu=True: 10 doan thoai DAU GAME (tu dich truoc) de nghe thu. Chay lai = lam tiep.
        -> dict thong ke, None neu bi dung."""
        vn = vcd.ViecDich.tim_vieneu()
        if not vn:
            raise LoiDung("không tìm thấy app VieNeu (bản tăng tốc GPU) – mở VieNeu, cài 'GPU' rồi thử lại")
        py, hf, gpu = vn
        lv = self.thu_muc_giong()
        for t in ("goc", "mau", "wav", "mp3", "tam"):
            os.makedirs(os.path.join(lv, t), exist_ok=True)
        tat_ca = self.mul_long_tieng_duoc()
        if not tat_ca:
            raise LoiDung("không tìm thấy lời thoại nào trong game (bấm Quét lại)")
        thu_tu = sorted(tat_ca, key=lambda m: (self.thu_tu_game(tat_ca[m]["ten"]), m))
        if thu:
            co_chu = [m for m in thu_tu if any(re.search(r"[A-Za-z]{2,}", self.THE.sub("", en))
                                               for _, en in tat_ca[m]["pd"] if en)]
            mo_dau = ("iceclimb", "ice_climb", "lara_ledge_catch")      # doan leo nui tuyet dau game
            dau = [m for m in co_chu if any(x in (tat_ca[m]["ten"] or "").lower() for x in mo_dau)]
            dau = (dau + [m for m in co_chu if m not in dau])[:max(10, len(dau))][:16]
            self.dich_truoc([en for m in dau for _, en in tat_ca[m]["pd"] if en], may, khoa, 0.5, bao)
            if self.dung.is_set():
                return None
            self.luu()
            thu_tu = dau
        chon = {}
        for m in thu_tu:
            cau = self._cau_doc(tat_ca[m])
            if not any(x[1] for x in cau):
                continue
            if not thu and self.file_giong(m):
                continue
            chon[m] = cau
        if not chon:
            if thu:
                raise LoiDung("không dịch được câu thoại đầu game – kiểm tra mã Claude / máy dịch")
            return {"file": 0, "da_co": sum(1 for m in tat_ca if self.file_giong(m)), "tong": len(tat_ca)}
        goc_dir = os.path.join(lv, "goc")

        # 1. cua so thoi gian tung cau + xac dinh cau nao nam o kenh giong nao
        cua_so = {}
        for m, cau in chon.items():
            het = tat_ca[m]["mau"]
            ds = []
            for i, (khung, _, _) in enumerate(cau):
                a = int(khung / 30 * 44100)
                b = int(cau[i + 1][0] / 30 * 44100) if i + 1 < len(cau) else het
                ds.append([a, max(b, a + 4410)])
            cua_so[m] = ds
        bao("Bước 1/4: xuất giọng gốc...")
        phan_tich = []
        for m in chon:
            kg = tat_ca[m]["kg"]
            if len(kg) > 1:
                phan_tich.append({"id": m, "kenh": [self._xuat_mp3_goc(m, c, goc_dir) for c in kg], "cau": cua_so[m]})
            else:
                self._xuat_mp3_goc(m, kg[0], goc_dir)
            if self.dung.is_set():
                return None
        gan = {}
        if phan_tich:
            ra_pt = os.path.join(lv, "tam", "phan_tich.json")
            if not self._chay_kich_ban("rt_phan_tich", KICH_BAN_RT, {"che_do": "phan_tich", "ds": phan_tich,
                                                                     "ra": ra_pt}, py, hf, bao,
                                       "Bước 1/4: tìm kênh giọng từng nhân vật"):
                return None
            with open(ra_pt, encoding="utf-8") as f:
                kq = json.load(f)
            for v in phan_tich:
                kg = tat_ca[v["id"]]["kg"]
                gan[v["id"]] = [kg[j] if j is not None and j >= 0 else None for j in kq.get(v["id"], [])]
        for m in chon:
            if m not in gan:
                gan[m] = [tat_ca[m]["kg"][0]] * len(chon[m])

        # 2. nguoi noi tung cau -> giong mau
        nguoi_cau = {}           # (m, i) -> khoa giong
        mau_nguon = {}           # khoa giong -> [(m, c)]
        for m, cau in chon.items():
            t = tat_ca[m]
            ten_kenh = {}
            for i, (_, _, ten) in enumerate(cau):
                c = gan[m][i] if i < len(gan[m]) else None
                if c is None:
                    continue
                if t["k"] == 1:
                    g = self.nguoi_noi(t["ten"])
                else:
                    if ten:
                        ten_kenh[c] = ten
                    g = ten_kenh.get(c) or f"kenh_{m}_{c}"
                nguoi_cau[(m, i)] = g
                mau_nguon.setdefault(g, []).append((m, c))
        # giong mau: uu tien cau NOI TO, DUT KHOAT (cau co dau "!", khong phai tieng tho / tieng dong)
        don = {}
        for m2, t2 in self.mul_long_tieng_duoc().items():
            if t2["k"] == 1 and 1.5 < t2["mau"] / 44100 < 9:
                en = " ".join(e for _, e in t2["pd"] if e)
                chu = self.THE.sub("", en)
                if "<" in chu or "*" in chu or len(re.findall(r"[A-Za-z]+", chu)) < 3:
                    continue
                diem = chu.count("!") * 2 + (1 if 2.5 < t2["mau"] / 44100 < 7 else 0)
                don.setdefault(self.nguoi_noi(t2["ten"]), []).append((-diem, m2))
        viec_mau = []
        for g, ds in mau_nguon.items():
            ra = self._mau(g)
            if os.path.isfile(ra):
                continue
            if g in don:
                ung = [m2 for _, m2 in sorted(don[g])[:24]]
                bao(f"Bước 2/4: chọn câu {g} nói mạnh nhất làm giọng mẫu ({len(ung)} câu)...")
                nguon = [self._xuat_mp3_goc(m2, 0, goc_dir) for m2 in ung]
                viec_mau.append({"ra": ra, "nguon": nguon, "chon": 3})
            else:
                nguon = [self._xuat_mp3_goc(m2, c2, goc_dir) for m2, c2 in list(dict.fromkeys(ds))[:3]]
                viec_mau.append({"ra": ra, "nguon": nguon})
            if self.dung.is_set():
                return None
        if viec_mau and not self._chay_kich_ban("rt_mau", KICH_BAN_RT, {"che_do": "mau", "ds": viec_mau}, py, hf,
                                                bao, "Bước 2/4: tạo giọng mẫu"):
            return None

        # 3. VieNeu doc tung cau
        nhom = {}
        for (m, i), g in nguoi_cau.items():
            chu = chon[m][i][1]
            if not chu or not os.path.isfile(self._mau(g)):
                continue
            a, b = cua_so[m][i]
            nhom.setdefault(g, []).append([f"{m}_{i}", chu, round(max((b - a) / 44100, 0.5), 3)])
        viec_doc = [{"ten": g, "mau": self._mau(g), "ra": self._thu_wav(g),
                     "rms": 0.08, "ds": ds} for g, ds in sorted(nhom.items(), key=lambda x: -len(x[1]))]
        vj = os.path.join(lv, "tam", "rt_doc.json")
        with open(vj, "w", encoding="utf-8") as f:
            json.dump({"nhom": viec_doc, "toi_da": 1.35, "gpu": gpu}, f, ensure_ascii=False)
        if viec_doc and not self.chay_vieneu(vj, py, hf, gpu, os.path.join(lv, "vieneu_nhat_ky.txt"),
                                             lambda a, b, ct: tien_do(a, b, "Bước 3/4: VieNeu đã đọc" + ct)):
            return None

        # 4. ghep vao dung kenh, dung thoi diem phu de -> MP3 44.1 kHz
        bao("Bước 4/4: ghép giọng vào đúng thời điểm phụ đề...")
        viec = []
        for m, cau in chon.items():
            t = tat_ca[m]
            theo_kenh = {}
            for i in range(len(cau)):
                g = nguoi_cau.get((m, i))
                c = gan[m][i] if i < len(gan[m]) else None
                w = os.path.join(self._thu_wav(g or "_"), f"{m}_{i}.wav")
                if g is None or c is None or not cau[i][1] or not os.path.isfile(w):
                    continue
                theo_kenh.setdefault(c, []).append(cua_so[m][i] + [w])
            for c, ds in theo_kenh.items():
                viec.append({"goc": self._xuat_mp3_goc(m, c, goc_dir), "so_mau": t["kenh"][c][2],
                             "ra": self._ten_mp3(m, c), "cau": ds})
        if viec and not self._chay_kich_ban("rt_ghep", KICH_BAN_RT, {"che_do": "ghep", "ds": viec, "tang_db": tang_db}, py, hf, bao,
                                            "Bước 4/4: đã ghép"):
            return None
        xong = len({os.path.basename(v["ra"]).split("_")[0].split(".")[0] for v in viec if os.path.isfile(v["ra"])})
        return {"file": xong, "da_co": sum(1 for m in tat_ca if self.file_giong(m)), "tong": len(tat_ca)}

    def xoa_giong(self):
        import shutil
        shutil.rmtree(os.path.join(self.thu_muc_giong(), "mp3"), ignore_errors=True)


KICH_BAN_RT = r"""
import json, os, sys
import numpy as np
import soundfile as sf
viec = json.load(open(sys.argv[1], encoding="utf-8"))
SR = 44100

def doc(p):
    y, sr = sf.read(p, dtype="float32", always_2d=True)
    y = y.mean(axis=1)
    if sr != SR:
        try:
            import soxr
            y = soxr.resample(y, sr, SR)
        except Exception:
            import librosa
            y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    return np.nan_to_num(y.astype(np.float32))

def rms(y):
    return float(np.sqrt(np.mean(y ** 2))) if len(y) else 0.0

def chi_giong(y):
    # bo doan im lang (giu cac khung 50 ms co tieng)
    n = int(0.05 * SR)
    k = len(y) // n
    if k == 0:
        return y
    kh = y[:k * n].reshape(k, n)
    e = np.sqrt((kh ** 2).mean(axis=1))
    giu = kh[e > max(0.01, e.max() * 0.08)]
    return giu.reshape(-1) if len(giu) else y

ds = viec["ds"]
print("TONG", len(ds), flush=True)
if viec["che_do"] == "phan_tich":
    kq = {}
    for i, v in enumerate(ds, 1):
        am = []
        for p in v["kenh"]:
            try:
                am.append(doc(p))
            except Exception as e:
                print("LOI", p, e, flush=True)
                am.append(np.zeros(1, np.float32))
        gan = []
        for a, b in v["cau"]:
            e = [rms(y[a:b]) for y in am]
            j = int(np.argmax(e)) if e else -1
            gan.append(j if e and e[j] > 0.004 else -1)
        kq[v["id"]] = gan
        print("XONG", i, len(ds), flush=True)
    json.dump(kq, open(viec["ra"], "w", encoding="utf-8"))
elif viec["che_do"] == "mau":
    for i, v in enumerate(ds, 1):
        phan = []
        nguon = v["nguon"]
        if v.get("chon"):
            # chon cac cau noi TO va CHAC nhat (RMS phan co tieng cao, it khoang lang)
            diem = []
            for p in nguon:
                try:
                    y = doc(p)
                    gy = chi_giong(y)
                    diem.append((rms(gy) * min(1.0, len(gy) / max(len(y), 1) * 1.4), p))
                except Exception as e:
                    print("LOI", p, e, flush=True)
            diem.sort(reverse=True)
            nguon = [p for _, p in diem[: v["chon"]]]
            print("CHON", [os.path.basename(p) for p in nguon], flush=True)
        for p in nguon:
            try:
                phan.append(chi_giong(doc(p)))
                phan.append(np.zeros(int(0.3 * SR), np.float32))
            except Exception as e:
                print("LOI", p, e, flush=True)
        if phan:
            y = np.concatenate(phan)[: 15 * SR]
            sf.write(v["ra"] + ".tam.wav", y, SR, subtype="PCM_16")
            os.replace(v["ra"] + ".tam.wav", v["ra"])
        print("XONG", i, len(ds), flush=True)
else:
    try:
        import librosa
    except Exception:
        librosa = None
    tang = 10 ** (float(viec.get("tang_db", 0)) / 20)

    def dam(y):
        # giong chac hon: bo am tram duoi 100 Hz, tang nhe dai 2-6 kHz (ro chu), nen dinh mem
        try:
            from scipy.signal import butter, sosfilt
            y = sosfilt(butter(2, 100, "highpass", fs=SR, output="sos"), y).astype(np.float32)
            y = (y + 0.35 * sosfilt(butter(2, 2000, "highpass", fs=SR, output="sos"), y)).astype(np.float32)
        except Exception:
            pass
        return y

    for i, v in enumerate(ds, 1):
        try:
            goc = doc(v["goc"])
        except Exception as e:
            print("LOI doc goc", v["goc"], e, flush=True)
            continue
        n = int(v["so_mau"])
        goc = np.pad(goc, (0, max(0, n - len(goc))))[:n]
        ra = goc.copy()                       # giu nguyen am thanh goc ngoai cac cau da long tieng
        for a, b, w in v["cau"]:
            a, b = max(0, min(a, n)), max(0, min(b, n))
            if b <= a or not w:
                continue
            y = doc(w)
            cho = b - a
            if len(y) > cho and librosa is not None:
                try:
                    y = librosa.effects.time_stretch(y, rate=min(len(y) / cho, 1.35))
                except Exception:
                    pass
            if len(y) > cho:
                y = y[:cho]
                m = min(len(y), int(0.03 * SR))
                y[-m:] *= np.linspace(1, 0, m, dtype=np.float32)
            y = dam(y)
            g = goc[a:b]
            r0, r1 = rms(g[np.abs(g) > 0.01]), rms(y[np.abs(y) > 0.01])
            if r0 > 1e-3 and r1 > 1e-3:
                y = y * min(r0 / r1, 4.0)
            y = y * tang
            y = (np.tanh(1.5 * y) / 1.5).astype(np.float32)      # nen dinh: to ma khong vo tieng
            ra[a:b] = 0
            ra[a:a + len(y)] = y
        dinh = float(np.max(np.abs(ra))) if n else 0
        if dinh > 0.98:
            ra *= 0.98 / dinh
        sf.write(v["ra"] + ".tam", ra, SR, format="MP3", subtype="MPEG_LAYER_III",
                 bitrate_mode="CONSTANT", compression_level=0.7)
        os.replace(v["ra"] + ".tam", v["ra"])
        print("XONG", i, len(ds), flush=True)
print("HET", flush=True)
"""
