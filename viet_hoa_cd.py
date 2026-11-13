# -*- coding: utf-8 -*-
"""Viet hoa Crimson Desert bang Claude: doc chu tieng Anh (nhom 0020) ngay trong thu muc game,
dich theo lo, luu bo nho dich (chay tiep duoc), xuat goi zip cho DMM.

- Giu nguyen tieng Anh: ten nhan vat, ten rieng (dia danh, phe phai), ten vat pham.
- Giu nguyen the: <br/>, {…}, [EMPTY]; kiem tra lai sau khi dich, sai thi dich lai / giu tieng Anh.
- Khoa Claude lay tu app Dich Game tren cung may (%APPDATA%\\DichGame\\khoa_api.txt).
"""
import concurrent.futures
import http.client
import json
import os
import re
import threading
import time
import zipfile

import crimson_desert as cd

DU_LIEU = os.path.join(os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(__file__)), "VietHoaGame")
THU_MUC_CD = os.path.join(DU_LIEU, "crimson_desert")
FILE_BO_NHO = os.path.join(THU_MUC_CD, "bo_nho_dich.json")
FILE_DO_LUONG = os.path.join(THU_MUC_CD, "do_luong_chi_phi.json")
DICH_GAME = os.path.join(os.environ.get("APPDATA") or "", "DichGame")
STEAM_APPID = "3321460"

DOT = {
    1: {"ten": "Đợt 1 – menu, nhiệm vụ, hội thoại cốt truyện, cắt cảnh",
        "file": ["ui", "localstringinfo", "quest", "questdialog", "sequencer", "narrationdialog", "talktree",
                 "stageclosedialog", "failmessage", "gameadvice", "interaction", "inventory", "equiptype",
                 "symboltext", "minigame", "platformservice", "uisocialaction", "lookat", "board", "bank"]},
    2: {"ten": "Đợt 2 – lời thoại chiến đấu / đi đường, mô tả vật phẩm, phe phái, kỹ năng, sự kiện",
        "file": ["aidialog", "item", "multichange", "gimmick", "character", "npc", "faction", "patterndescription",
                 "managementbuff", "managementneedssynergy", "globalgameevent", "entitlement", "housingobject",
                 "sublevel", "house", "housingroom", "housingobjectgroup", "socket"],
        # cac file nay lan ten va mo ta: chi dich CAU (mo ta), giu nguyen ten / nhan
        "chi_cau": ["item", "multichange", "gimmick", "character", "npc", "faction", "housingobject"]},
    3: {"ten": "Đợt 3 – bách khoa (knowledge): giới thiệu nhân vật, vùng đất, sinh vật, lịch sử",
        "file": ["knowledge"],
        "chi_cau": ["knowledge"]},
}
# file chi chua ten -> lam bang ten rieng (giu nguyen, khong dich)
FILE_TEN = ["npcname", "character", "region", "faction", "factionoperationgroup", "item", "itemgroup",
            "housingobject", "dyecolorgroup", "personality"]

MO_HINH = "claude-haiku-5-5"
GIA_MAC_DINH = [0.10, 0.50]   # USD / 1 trieu token (vao, ra) – lay theo cau hinh Dich Game neu co
KY_TU_MOI_LO = 6000
CAU_MOI_LO = 40
SO_LUONG = 4

HUONG_DAN = """Bạn là dịch giả chuyên Việt hóa game. Game: Crimson Desert (nhập vai thế giới mở, trung cổ kỳ ảo; \
nhân vật chính Kliff, thủ lĩnh nhóm lính đánh thuê Greymanes; lục địa Pywel).
Bạn nhận một mảng JSON các chuỗi tiếng Anh lấy từ file chữ của game và trả về mảng JSON các bản dịch tiếng Việt.

Quy tắc bắt buộc:
- CHỈ trả về một mảng JSON hợp lệ, CÙNG SỐ PHẦN TỬ, CÙNG THỨ TỰ. Không giải thích, không ```.
- GIỮ NGUYÊN tiếng Anh: tên nhân vật, tên người, địa danh, phe phái, tổ chức, tên vật phẩm, tên trang bị, \
tên kỹ năng riêng, và mọi từ trong danh sách "Giữ nguyên" nếu có.
- Giữ NGUYÊN từng ký tự các thẻ: <br/>, <...>, {...} (VD {Key:Key_Jump}, {Param1}), [EMPTY]. Không dịch, không thêm, không bớt thẻ.
- Giữ nguyên số, ký hiệu, khoảng trắng đầu/cuối và cách xuống dòng.
- Văn phong tự nhiên như phụ đề phim kỳ ảo/cổ trang. Xưng hô hợp ngữ cảnh \
(ta – ngươi, tôi – ngài, anh – em, ta – các ngươi...).
- Menu, nút bấm, tiêu đề nhiệm vụ: ngắn gọn, rõ nghĩa như game Việt hóa chính thức.
- Chuỗi chỉ gồm tên riêng hoặc không có gì để dịch: trả lại y nguyên."""

THE = re.compile(r"<[^<>]*>|\{[^{}]*\}|\[EMPTY\]")


def khong_can_dich(s):
    t = THE.sub("", s).strip()
    return not t or not re.search(r"[A-Za-z]{2,}", t)


def la_cau(s):
    """Chuoi la cau / doan van (mo ta) chu khong phai ten hay nhan ngan."""
    t = THE.sub(" ", s).strip()
    if "<br/>" in s or len(t) >= 70:
        return True
    return len(t.split()) >= 4 and (t.endswith((".", "!", "?", "…", '"')) or ". " in t)


def the_cua(s):
    return sorted(THE.findall(s))


# ================================================================ bang ten rieng

class BangTen:
    def __init__(self, ten):
        self.ten = {t for t in ten if 2 <= len(t) <= 40}
        self.dai = max((len(t.split()) for t in self.ten), default=1)

    @staticmethod
    def tao(nhom):
        ten = set()
        for f in FILE_TEN:
            for _, _, v in nhom.get(f, {}).get("ds", []):
                v = THE.sub("", v).strip()
                if (v and len(v) <= 40 and "\n" not in v and not v.endswith((".", "!", "?", ":"))
                        and v[0].isupper() and len(v.split()) <= 5):
                    ten.add(v)
        # bo cac tu thong dung de khong chan dich nham
        thuong = {"Talk", "Map", "Quest", "Quests", "Inventory", "Continue", "Settings", "Options", "Yes", "No",
                  "Gold", "Silver", "Food", "Water", "Wood", "Stone", "Iron", "Horse", "Sword", "Shield", "Bow",
                  "Help", "Back", "Close", "Cancel", "Confirm", "Accept", "Reward", "Rewards", "Level", "None"}
        return BangTen(ten - thuong)

    def trong(self, van_ban):
        """Cac ten rieng xuat hien trong van ban (cum chu viet hoa)."""
        kq = set()
        tu = re.findall(r"[A-Za-z][A-Za-z'’-]*", van_ban)
        for i in range(len(tu)):
            if not tu[i][0].isupper():
                continue
            for n in range(min(self.dai, len(tu) - i), 0, -1):
                cum = " ".join(tu[i:i + n])
                if cum in self.ten:
                    kq.add(cum)
                    break
        return kq

    def la_ten(self, s):
        return s.strip() in self.ten


# ================================================================ Claude

class LoiDung(Exception):
    """Loi khong the tiep tuc (sai khoa, het tien...)."""


class Claude:
    MAY_CHU = "api.anthropic.com"

    def __init__(self, khoa, mo_hinh=MO_HINH):
        self.khoa = khoa
        self.mo_hinh = mo_hinh
        self.kieu = None
        self.rieng = threading.local()

    def _ket_noi(self, moi=False):
        c = getattr(self.rieng, "c", None)
        if moi or c is None:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
            c = http.client.HTTPSConnection(self.MAY_CHU, timeout=180)
            self.rieng.c = c
        return c

    def goi(self, noi_dung, max_tokens):
        body = json.dumps({"model": self.mo_hinh, "max_tokens": max_tokens, "system": HUONG_DAN,
                           "messages": [{"role": "user", "content": noi_dung}]}).encode("utf-8")
        for lan in range(6):
            for kieu in ([self.kieu] if self.kieu else ["x-api-key", "bearer"]):
                dau = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
                if kieu == "bearer":
                    dau["authorization"] = "Bearer " + self.khoa
                else:
                    dau["x-api-key"] = self.khoa
                try:
                    c = self._ket_noi(moi=lan > 0)
                    c.request("POST", "/v1/messages", body=body, headers=dau)
                    r = c.getresponse()
                    du_lieu = r.read().decode("utf-8", "ignore")
                except (http.client.HTTPException, OSError):
                    time.sleep(2 + lan * 3)
                    break
                if r.status in (401, 403):
                    continue
                if r.status in (429, 500, 502, 503, 529):
                    time.sleep(5 + lan * 10)
                    break
                if r.status >= 400:
                    try:
                        tb = json.loads(du_lieu)["error"]["message"]
                    except Exception:
                        tb = du_lieu[:200]
                    if "credit" in tb.lower() or "billing" in tb.lower():
                        raise LoiDung("tài khoản Claude hết tiền: " + tb)
                    raise RuntimeError(f"HTTP {r.status}: {tb}")
                self.kieu = kieu
                d = json.loads(du_lieu)
                chu = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
                u = d.get("usage", {})
                return chu, u.get("input_tokens", 0), u.get("output_tokens", 0)
            else:
                raise LoiDung("mã Claude không hợp lệ (HTTP 401/403) – kiểm tra lại mã trong app Dịch Game")
        raise RuntimeError("Claude bận hoặc mất mạng, đã thử lại nhiều lần")


# ================================================================ dich offline (mo hinh cua app Dich Game)

THU_MUC_OFFLINE = os.path.join(DICH_GAME, "mo_hinh", "quickmt-en-vi")
TEP_OFFLINE = ["config.json", "source_vocabulary.json", "target_vocabulary.json", "src.spm.model",
               "tgt.spm.model", "model.bin"]


def co_offline():
    """-> (co_the_dung, ly_do)"""
    try:
        import ctranslate2  # noqa: F401
        import sentencepiece  # noqa: F401
    except Exception:
        return False, "bản launcher này thiếu thư viện dịch offline"
    if not all(os.path.isfile(os.path.join(THU_MUC_OFFLINE, t)) for t in TEP_OFFLINE):
        return False, ("chưa có mô hình offline – mở app Dịch Game, chọn chế độ dịch Offline một lần "
                       "để app tải mô hình (~400 MB)")
    return True, ""


class Offline:
    """quickmt-en-vi qua CTranslate2 tren CPU. Giu the bang cach chi dich phan chu giua cac the."""
    TACH_CAU = re.compile(r"(?<=[.!?…])\s+(?=[\"'“A-Z0-9(])")

    def __init__(self):
        import ctranslate2
        import sentencepiece as spm
        so = max(2, min(8, (os.cpu_count() or 8) - 2))
        self.tr = ctranslate2.Translator(THU_MUC_OFFLINE, device="cpu", compute_type="int8",
                                         inter_threads=1, intra_threads=so)
        self.sp_vao = spm.SentencePieceProcessor(model_file=os.path.join(THU_MUC_OFFLINE, "src.spm.model"))
        self.sp_ra = spm.SentencePieceProcessor(model_file=os.path.join(THU_MUC_OFFLINE, "tgt.spm.model"))

    def _dich_cau(self, cac_cau):
        kq = []
        for i in range(0, len(cac_cau), 32):
            phan = cac_cau[i:i + 32]
            ra = self.tr.translate_batch([self.sp_vao.encode(c, out_type=str) for c in phan],
                                         beam_size=2, max_decoding_length=256, max_batch_size=32)
            for r in ra:
                manh = r.hypotheses[0]
                try:
                    kq.append(self.sp_ra.decode(manh).strip())
                except Exception:
                    kq.append(self.sp_ra.decode_pieces(manh).strip())
        return kq

    def _dich_doan(self, cac_doan):
        """Dich cac doan chu (khong co <..>, xuong dong). Ma {..} giua cau thay bang ZQn roi tra lai;
        neu mo hinh lam mat ma thi dich tung manh giua cac ma."""
        cau, khuon = [], []
        for doan in cac_doan:
            ma = re.findall(r"\{[^{}]*\}", doan)
            tam = doan
            for n, m in enumerate(ma):
                tam = tam.replace(m, f"ZQ{n}", 1)
            ds = [c for c in self.TACH_CAU.split(tam.strip()) if c]
            khuon.append((doan, ma, len(cau), len(ds)))
            cau.extend(ds)
        ban = self._dich_cau(cau) if cau else []
        kq, lai = [], []
        for k, (doan, ma, dau, so) in enumerate(khuon):
            vi = " ".join(ban[dau:dau + so])
            if ma:
                if all(vi.count(f"ZQ{n}") == 1 for n in range(len(ma))) and not re.search(rf"ZQ{len(ma)}", vi):
                    for n, m in enumerate(ma):
                        vi = vi.replace(f"ZQ{n}", m)
                else:
                    vi = None
                    lai.append(k)
            kq.append(vi)
        for k in lai:   # du phong: dich tung manh giua cac ma
            doan = khuon[k][0]
            manh = re.split(r"(\{[^{}]*\})", doan)
            chu = [m for m in manh if m and not m.startswith("{") and re.search(r"[A-Za-z]{2,}", m)]
            dich = dict(zip(chu, self._dich_cau([m.strip() for m in chu]))) if chu else {}
            kq[k] = "".join((m[:len(m) - len(m.lstrip())] + dich[m] + m[len(m.rstrip()):]) if m in dich else m
                            for m in manh)
        return kq

    def dich_lo(self, lo):
        """lo: [chuoi] -> [ban dich | None]"""
        khuon, doan_can = [], []
        for s in lo:
            phan = []
            for doan in re.split(r"(<[^<>]*>|\[EMPTY\]|\n)", s):
                if not doan:
                    continue
                if THE.fullmatch(doan) or doan == "\n" or not re.search(r"[A-Za-z]{2,}", THE.sub("", doan)):
                    phan.append(("giu", doan))
                    continue
                trai = doan[:len(doan) - len(doan.lstrip())]
                phai = doan[len(doan.rstrip()):]
                phan.append(("dich", trai, len(doan_can), phai))
                doan_can.append(doan.strip())
            khuon.append(phan)
        ban = self._dich_doan(doan_can) if doan_can else []
        kq = []
        for phan in khuon:
            vi = "".join(p[1] if p[0] == "giu" else p[1] + ban[p[2]] + p[3] for p in phan)
            kq.append(vi if vi.strip() else None)
        return kq


def doc_khoa_claude():
    p = os.path.join(DICH_GAME, "khoa_api.txt")
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def doc_gia():
    try:
        with open(os.path.join(DICH_GAME, "cau_hinh.json"), encoding="utf-8") as f:
            c = json.load(f)
        g = c.get("gia_usd_moi_trieu_token")
        if isinstance(g, list) and len(g) == 2:
            return [float(g[0]), float(g[1])], c.get("mo_hinh") or MO_HINH
    except Exception:
        pass
    return list(GIA_MAC_DINH), MO_HINH


def tach_json(chu, so):
    chu = chu.strip()
    if chu.startswith("```"):
        chu = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", chu)
    i, j = chu.find("["), chu.rfind("]")
    if i < 0 or j < i:
        raise ValueError("không thấy mảng JSON")
    ds = json.loads(chu[i:j + 1])
    if not isinstance(ds, list) or len(ds) != so or not all(isinstance(x, str) for x in ds):
        raise ValueError("sai số phần tử")
    return ds


# ================================================================ cong viec

class ViecDich:
    """Mot lan Viet hoa: doc game -> lap danh sach cau can dich -> dich -> xuat goi."""

    def __init__(self, thu_muc_game, dot=1):
        self.thu_muc_game = thu_muc_game
        self.dot = dot
        self.nhom = None
        self.bang_ten = None
        self.bo_nho = {}
        self.khoa = threading.Lock()
        self.dung = threading.Event()
        self.da_doi = 0
        self.tien = 0.0
        self.loi = 0

    # ---------------------------------------------------------- chuan bi
    def nap(self, bao=lambda s: None):
        thu_muc = os.path.join(self.thu_muc_game, "0020")
        if not os.path.isfile(os.path.join(thu_muc, "0.pamt")):
            raise LoiDung("không thấy thư mục chữ tiếng Anh (0020) trong thư mục game")
        bao("Đang đọc chữ tiếng Anh của game...")
        self.nhom = cd.doc_nhom(thu_muc)
        self.bang_ten = BangTen.tao(self.nhom)
        try:
            with open(FILE_BO_NHO, encoding="utf-8") as f:
                self.bo_nho = json.load(f)
        except Exception:
            self.bo_nho = {}
        return self

    def luu(self):
        os.makedirs(THU_MUC_CD, exist_ok=True)
        with self.khoa:
            du_lieu = json.dumps(self.bo_nho, ensure_ascii=False)
        tam = FILE_BO_NHO + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            f.write(du_lieu)
        os.replace(tam, FILE_BO_NHO)

    def nen_dich(self, f, v, dot=None):
        """Chuoi v trong file f co thuoc dien dich khong (dung luat cua dot chua file f)."""
        if khong_can_dich(v) or self.bang_ten.la_ten(v):
            return False
        d = dot or next((k for k, x in DOT.items() if f in x["file"]), None)
        if d is None:
            return False
        if f in DOT[d].get("chi_cau", []) and not la_cau(v):
            return False
        return True

    def _chuoi_cua_dot(self):
        for f in DOT[self.dot]["file"]:
            for _, _, v in self.nhom.get(f, {}).get("ds", []):
                if self.nen_dich(f, v, self.dot):
                    yield v

    def cau_can_dich(self):
        """Cac chuoi tieng Anh (khong trung) cua dot nay chua co trong bo nho."""
        ds, da = [], set()
        for v in self._chuoi_cua_dot():
            if v in da or v in self.bo_nho:
                continue
            da.add(v)
            ds.append(v)
        return ds

    def thong_ke(self):
        tat_ca = set(self._chuoi_cua_dot())
        con = self.cau_can_dich()
        return {"tong": len(tat_ca), "da_dich": sum(1 for v in tat_ca if v in self.bo_nho),
                "con": len(con), "ky_tu_con": sum(len(v) for v in con)}

    @staticmethod
    def uoc_tinh_usd(ky_tu, gia):
        """Theo so do thuc te (USD / ky tu) cua cac lan dich truoc; chua co thi dung he so da hieu chinh
        (lan dau do duoc: ~1 USD cho 720k ky tu ~ 4,2 lan cong thuc cu)."""
        try:
            with open(FILE_DO_LUONG, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("ky_tu", 0) > 50000:
                return ky_tu * d["usd"] / d["ky_tu"]
        except Exception:
            pass
        vao = ky_tu / 3.6 * 1.35 + 900 * (ky_tu / KY_TU_MOI_LO + 1)
        ra = ky_tu / 3.6 * 1.9
        return (vao * gia[0] / 1e6 + ra * gia[1] / 1e6) * 4.2

    def _ghi_do_luong(self, ky_tu, usd):
        if ky_tu <= 0 or usd <= 0:
            return
        try:
            with open(FILE_DO_LUONG, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {"ky_tu": 0, "usd": 0.0}
        d["ky_tu"] += ky_tu
        d["usd"] += usd
        os.makedirs(THU_MUC_CD, exist_ok=True)
        with open(FILE_DO_LUONG, "w", encoding="utf-8") as f:
            json.dump(d, f)

    # ---------------------------------------------------------- dich
    def _chia_lo(self, ds):
        lo, ky = [], 0
        for v in ds:
            if lo and (len(lo) >= CAU_MOI_LO or ky + len(v) > KY_TU_MOI_LO):
                yield lo
                lo, ky = [], 0
            lo.append(v)
            ky += len(v)
        if lo:
            yield lo

    def _dich_lo(self, claude, lo, gia):
        ten = set()
        for v in lo:
            ten |= self.bang_ten.trong(v)
        phan = []
        if ten:
            phan.append("Giữ nguyên (không dịch): " + ", ".join(sorted(ten)[:150]))
        phan.append(json.dumps(lo, ensure_ascii=False))
        noi_dung = "\n\n".join(phan)
        max_tok = min(16000, int(sum(len(v) for v in lo) / 1.2) + 800)
        tien = 0.0
        for lan in range(2):
            chu, vao, ra = claude.goi(noi_dung, max_tok)
            tien += vao * gia[0] / 1e6 + ra * gia[1] / 1e6
            try:
                kq = tach_json(chu, len(lo))
                break
            except ValueError:
                kq = None
        if kq is None:
            if len(lo) > 1:   # chia doi roi thu lai
                giua = len(lo) // 2
                a, ta = self._dich_lo(claude, lo[:giua], gia)
                b, tb = self._dich_lo(claude, lo[giua:], gia)
                return a + b, tien + ta + tb
            return [None], tien
        ra_ds = []
        for en, vi in zip(lo, kq):
            ok = vi.strip() and the_cua(en) == the_cua(vi)
            ra_ds.append(vi if ok else None)
        return ra_ds, tien

    def chay_offline(self, bao, tien_do):
        ok, ly_do = co_offline()
        if not ok:
            raise LoiDung(ly_do)
        ds = self.cau_can_dich()
        tong = len(ds)
        if not tong:
            bao("Đợt này đã dịch xong hết.")
            return True
        self.dung.clear()
        self.tien = 0.0
        bao("Đang nạp mô hình dịch offline...")
        may = Offline()
        bao(f"Bắt đầu dịch offline {tong} câu...")
        xong, lan_luu = 0, time.time()
        for i in range(0, tong, 24):
            if self.dung.is_set():
                break
            lo = ds[i:i + 24]
            try:
                kq = may.dich_lo(lo)
            except Exception as e:
                self.loi += len(lo)
                bao(f"Lỗi dịch offline ({e}) – bỏ qua lô này")
                kq = [None] * len(lo)
            with self.khoa:
                for en, vi in zip(lo, kq):
                    if vi is not None and the_cua(en) == the_cua(vi):
                        self.bo_nho[en] = vi
                        self.da_doi += 1
            xong += len(lo)
            tien_do(xong, tong, 0.0)
            if time.time() - lan_luu > 30:
                self.luu()
                lan_luu = time.time()
        self.luu()
        return not self.dung.is_set() and not self.cau_can_dich()

    def chay(self, khoa_claude, gioi_han_usd, bao, tien_do):
        gia, mo_hinh = doc_gia()
        claude = Claude(khoa_claude, mo_hinh)
        ds = self.cau_can_dich()
        tong = len(ds)
        if not tong:
            bao("Đợt này đã dịch xong hết.")
            return True
        self.dung.clear()
        self.tien = 0.0
        lo_list = list(self._chia_lo(ds))
        xong = 0
        lan_luu = time.time()
        bao(f"Bắt đầu dịch {tong} câu ({len(lo_list)} lô)...")
        with concurrent.futures.ThreadPoolExecutor(SO_LUONG) as ex:
            dang = {}
            it = iter(lo_list)

            def nop():
                if self.dung.is_set() or self.tien >= gioi_han_usd:
                    return False
                lo = next(it, None)
                if lo is None:
                    return False
                dang[ex.submit(self._dich_lo, claude, lo, gia)] = lo
                return True

            for _ in range(SO_LUONG):
                nop()
            while dang:
                xong_f, _ = concurrent.futures.wait(dang, return_when=concurrent.futures.FIRST_COMPLETED)
                for f in xong_f:
                    lo = dang.pop(f)
                    try:
                        kq, tien = f.result()
                    except LoiDung as e:
                        self.dung.set()
                        bao(f"Dừng: {e}")
                        continue
                    except Exception as e:
                        self.loi += 1
                        bao(f"Lỗi một lô ({e}) – bỏ qua, lần sau chạy tiếp sẽ dịch lại")
                        continue
                    with self.khoa:
                        self.tien += tien
                        for en, vi in zip(lo, kq):
                            if vi is not None:
                                self.bo_nho[en] = vi
                                self.da_doi += 1
                            else:
                                self.loi += 1
                    xong += len(lo)
                    ky_tu_xong = sum(len(v) for v in lo)
                    self._ghi_do_luong(ky_tu_xong, tien)
                    tien_do(xong, tong, self.tien)
                    if time.time() - lan_luu > 20:
                        self.luu()
                        lan_luu = time.time()
                    nop()
        self.luu()
        if self.tien >= gioi_han_usd:
            bao(f"Đã chạm giới hạn {gioi_han_usd:.2f} USD – bấm Dịch lần nữa để chạy tiếp.")
            return False
        if self.dung.is_set():
            return False
        return not self.cau_can_dich()

    # ---------------------------------------------------------- long tieng Kliff (thu nghiem)
    def trich_giong_kliff(self, thu_muc_ra, bao=lambda s: None):
        """Lay toan bo cau thoai Kliff (tieng Anh) ra thu_muc_ra/goc/*.wem + danh_sach.csv
        (ten file, cau tieng Anh, ban Viet hoa neu co). Chi DOC file game."""
        import csv
        nhom_am = os.path.join(self.thu_muc_game, "0006")
        if not os.path.isfile(os.path.join(nhom_am, "0.pamt")):
            raise LoiDung("không thấy thư mục âm thanh tiếng Anh (0006) trong thư mục game")
        bao("Đang đọc danh sách file âm thanh...")
        ds = [f for f in cd.doc_pamt_day_du(os.path.join(nhom_am, "0.pamt"))
              if f["duoi"] == ".wem" and f["ten"].startswith("unique_kliff_")]
        cau = {}
        for g in self.nhom.values():
            for _, k, v in g["ds"]:
                cau[k.lower()] = v
        os.makedirs(os.path.join(thu_muc_ra, "goc"), exist_ok=True)
        os.makedirs(os.path.join(thu_muc_ra, "wav_tieng_viet"), exist_ok=True)
        dong, mau, loi = [], None, 0
        for i, f in enumerate(ds):
            try:
                b = cd.doc_tep(nhom_am, f)
            except Exception:
                loi += 1
                continue
            with open(os.path.join(thu_muc_ra, "goc", f["ten"] + ".wem"), "wb") as fh:
                fh.write(b)
            tt = cd.thong_tin_wem(b)
            if mau is None and tt:
                mau = tt
            en = cau.get(f["ten"][len("unique_kliff_"):], "")
            dong.append([f["ten"], f["thu_muc"], f"{tt.get('giay', 0):.2f}", en,
                         self.bo_nho.get(en, "") if en else ""])
            if i % 200 == 0:
                bao(f"Đang lấy giọng Kliff... {i}/{len(ds)}")
        dong.sort(key=lambda x: x[0])
        with open(os.path.join(thu_muc_ra, "danh_sach.csv"), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ten_file", "thu_muc_trong_game", "giay", "tieng_anh", "tieng_viet"])
            w.writerows(dong)
        with open(os.path.join(thu_muc_ra, "DOC_TRUOC.txt"), "w", encoding="utf-8") as fh:
            fh.write("Thư mục goc: giọng Kliff gốc (Wwise .wem) lấy từ game – chỉ để thử, không chia sẻ.\n"
                     "danh_sach.csv: tên file, độ dài (giây), câu tiếng Anh, bản Việt hóa.\n"
                     "wav_tieng_viet: đặt file WAV tiếng Việt cùng tên (VD unique_kliff_xxx.wav) để đóng gói.\n")
        return {"so": len(dong), "co_viet": sum(1 for x in dong if x[4]), "loi": loi, "mau": mau or {}}

    # ---------------------------------------------------------- dong goi giong Viet (Wwise)
    @staticmethod
    def tim_wwise_console():
        """Tim WwiseConsole.exe: bien WWISEROOT, cac thu muc cai mac dinh tren moi o dia."""
        import glob
        ung_vien = []
        goc = os.environ.get("WWISEROOT")
        if goc:
            ung_vien.append(os.path.join(goc, "Authoring", "x64", "Release", "bin", "WwiseConsole.exe"))
        for o in "CDEFGH":
            for mau in (rf"{o}:\Program Files (x86)\Audiokinetic\*\Authoring\x64\Release\bin\WwiseConsole.exe",
                        rf"{o}:\Program Files\Audiokinetic\*\Authoring\x64\Release\bin\WwiseConsole.exe",
                        rf"{o}:\Audiokinetic\*\Authoring\x64\Release\bin\WwiseConsole.exe",
                        rf"{o}:\*\Audiokinetic\*\Authoring\x64\Release\bin\WwiseConsole.exe"):
                ung_vien += sorted(glob.glob(mau), reverse=True)
        for p in ung_vien:
            if os.path.isfile(p):
                return p
        return None

    @staticmethod
    def chuan_wav(nguon, dich, tan_so=48000):
        """WAV bat ky (PCM 16/24/32 bit, float, stereo) -> PCM 16 bit mono 48 kHz. -> so giay."""
        import wave
        import numpy as np
        with open(nguon, "rb") as f:
            b = f.read()
        if b[:4] != b"RIFF" or b[8:12] != b"WAVE":
            raise ValueError(f"{os.path.basename(nguon)} không phải file WAV")
        o, fmt, data = 12, None, None
        while o + 8 <= len(b):
            ten, co = b[o:o + 4], int.from_bytes(b[o + 4:o + 8], "little")
            if ten == b"fmt ":
                fmt = b[o + 8:o + 8 + co]
            elif ten == b"data":
                data = b[o + 8:o + 8 + co]
            o += 8 + co + (co & 1)
        if not fmt or data is None:
            raise ValueError(f"{os.path.basename(nguon)}: WAV hỏng")
        ma, kenh, ts = int.from_bytes(fmt[0:2], "little"), int.from_bytes(fmt[2:4], "little"), \
            int.from_bytes(fmt[4:8], "little")
        bit = int.from_bytes(fmt[14:16], "little")
        if ma == 0xFFFE and len(fmt) >= 26:
            ma = int.from_bytes(fmt[24:26], "little")
        if ma == 3:
            x = np.frombuffer(data[:len(data) // 4 * 4], dtype="<f4").astype(np.float64)
        elif bit == 16:
            x = np.frombuffer(data[:len(data) // 2 * 2], dtype="<i2") / 32768.0
        elif bit == 24:
            a = np.frombuffer(data[:len(data) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
            v = a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16)
            x = np.where(v >= 1 << 23, v - (1 << 24), v) / float(1 << 23)
        elif bit == 32:
            x = np.frombuffer(data[:len(data) // 4 * 4], dtype="<i4") / float(1 << 31)
        else:
            raise ValueError(f"{os.path.basename(nguon)}: WAV {bit} bit chưa hỗ trợ")
        if kenh > 1:
            x = x[:len(x) // kenh * kenh].reshape(-1, kenh).mean(axis=1)
        if ts != tan_so and len(x):
            n = int(round(len(x) * tan_so / ts))
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
        x = np.clip(x, -1, 1)
        with wave.open(dich, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(tan_so)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        return len(x) / tan_so

    def dong_goi_giong(self, thu_muc, duong_dan_zip, wwise=None, bao=lambda s: None):
        """thu_muc/wav_tieng_viet/<ten>.wav -> WwiseConsole (Vorbis) -> .wem -> zip DMM."""
        import csv
        import shutil
        import subprocess
        import xml.sax.saxutils as xs
        wwise = wwise or self.tim_wwise_console()
        if not wwise:
            raise LoiDung("không tìm thấy Wwise (WwiseConsole.exe) – cài Wwise bằng Audiokinetic Launcher")
        thu_wav = os.path.join(thu_muc, "wav_tieng_viet")
        wavs = sorted(f for f in os.listdir(thu_wav) if f.lower().endswith(".wav")) if os.path.isdir(thu_wav) else []
        if not wavs:
            raise LoiDung("chưa có file WAV nào trong LongTieng_Kliff\\wav_tieng_viet")
        do_dai = {}
        try:
            with open(os.path.join(thu_muc, "danh_sach.csv"), encoding="utf-8-sig") as f:
                for d in csv.DictReader(f):
                    do_dai[d["ten_file"]] = float(d.get("giay") or 0)
        except Exception:
            pass
        tam = os.path.join(THU_MUC_CD, "wwise_tam")
        shutil.rmtree(tam, ignore_errors=True)
        nguon = os.path.join(tam, "nguon")
        os.makedirs(nguon)
        bao_cao = []
        bo_qua = []
        for w in wavs:
            ten = os.path.splitext(w)[0].strip()
            if do_dai and ten not in do_dai:
                bo_qua.append(f"✗ {w}: tên file không khớp câu nào của Kliff – đổi tên giống file trong thư mục goc")
                continue
            giay = self.chuan_wav(os.path.join(thu_wav, w), os.path.join(nguon, ten + ".wav"))
            goc = do_dai.get(ten)
            bao_cao.append((ten, giay, goc))
        if not bao_cao:
            raise LoiDung("không có file WAV nào đặt đúng tên: " + "; ".join(bo_qua[:3]))
        bao("Đang tạo project Wwise tạm...")
        an = 0x08000000 if os.name == "nt" else 0
        du_an = os.path.join(tam, "VH", "VH.wproj")
        nhat_ky = open(os.path.join(thu_muc, "wwise_nhat_ky.txt"), "w", encoding="utf-8", errors="replace")
        try:
            r = subprocess.run([wwise, "create-new-project", du_an, "--platform", "Windows", "--quiet"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=an, timeout=600)
            nhat_ky.write(r.stdout.decode("utf-8", "replace"))
            if not os.path.isfile(du_an):
                raise LoiDung("Wwise không tạo được project tạm – xem LongTieng_Kliff\\wwise_nhat_ky.txt")
            ra_wem = os.path.join(tam, "ra")
            for chuyen_doi in ("Vorbis Quality High", None):
                ds = "\n".join(
                    f'  <Source Path="{xs.escape(t)}.wav"'
                    + (f' Conversion="{chuyen_doi}"' if chuyen_doi else "")
                    + f' Destination="{xs.escape(t)}.wem"/>' for t, _, _ in bao_cao)
                with open(os.path.join(tam, "ds.wsources"), "w", encoding="utf-8") as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                            f'<ExternalSourcesList SchemaVersion="1" Root="{xs.escape(nguon)}">\n{ds}\n'
                            '</ExternalSourcesList>\n')
                bao(f"Wwise đang mã hóa {len(bao_cao)} câu ({chuyen_doi or 'cài đặt mặc định'})...")
                shutil.rmtree(ra_wem, ignore_errors=True)
                r = subprocess.run([wwise, "convert-external-source", du_an, "--platform", "Windows",
                                    "--source-file", os.path.join(tam, "ds.wsources"), "--output", ra_wem],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=an, timeout=1800)
                nhat_ky.write(f"\n===== {chuyen_doi} =====\n" + r.stdout.decode("utf-8", "replace"))
                co = {}
                for g, _, ts in os.walk(ra_wem):
                    for t in ts:
                        if t.lower().endswith(".wem"):
                            co[os.path.splitext(t)[0]] = os.path.join(g, t)
                if co and all(cd.thong_tin_wem(open(p, "rb").read()).get("ma_codec") == 0xFFFF
                              for p in co.values()):
                    break
            if not co:
                raise LoiDung("Wwise không tạo ra file .wem – xem LongTieng_Kliff\\wwise_nhat_ky.txt")
        finally:
            nhat_ky.close()
        dong = []
        with zipfile.ZipFile(duong_dan_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for ten, giay, goc in bao_cao:
                p = co.get(ten)
                if not p:
                    dong.append(f"✗ {ten}: Wwise không mã hóa được")
                    continue
                tt = cd.thong_tin_wem(open(p, "rb").read())
                z.write(p, f"LongTieng_Kliff/0006/sound/windows/english(us)/{ten}.wem")
                lech = f" (gốc {goc:.1f}s)" if goc else " (không thấy tên này trong danh sách!)"
                dong.append(f"✓ {ten}: {giay:.1f}s{lech} • {tt.get('ten_codec')} {tt.get('tan_so')} Hz")
        shutil.rmtree(tam, ignore_errors=True)
        return dong + bo_qua

    # ---------------------------------------------------------- xuat goi DMM
    def xuat_goi(self, duong_dan_zip):
        tam = os.path.join(THU_MUC_CD, "goi_tam")
        import shutil
        shutil.rmtree(tam, ignore_errors=True)
        ban_dich = {}
        for f in sorted({x for d in DOT.values() for x in d["file"]}):
            g = self.nhom.get(f)
            if not g:
                continue
            m = {k: self.bo_nho[v] for _, k, v in g["ds"]
                 if v in self.bo_nho and self.bo_nho[v] != v and self.nen_dich(f, v)}
            if m:
                ban_dich[f] = m
        thong_ke = cd.dong_goi(self.nhom, ban_dich, tam, "eng")
        ten_mod = "VietHoa_CrimsonDesert"
        os.makedirs(os.path.dirname(os.path.abspath(duong_dan_zip)), exist_ok=True)
        with zipfile.ZipFile(duong_dan_zip, "w", zipfile.ZIP_DEFLATED) as z:
            goc = os.path.join(tam, "gamedata")
            for thu_muc, _, tep in os.walk(goc):
                for t in tep:
                    p = os.path.join(thu_muc, t)
                    z.write(p, f"{ten_mod}/0020/" + os.path.relpath(p, tam).replace(os.sep, "/"))
        shutil.rmtree(tam, ignore_errors=True)
        return thong_ke
