# -*- coding: utf-8 -*-
"""Phien am ten rieng nuoc ngoai (Kliff, Oongka, Pywel, Konstantin...) thanh cach doc tieng Viet
de VieNeu doc duoc khi long tieng. Chi dung cho CHU DUA VAO MAY DOC – phu de van giu ten goc.

Thu tu uu tien: tu dien co dinh -> tu dien Claude phien am (luu dem) -> quy tac tu dong.
"""
import json
import os
import re
import threading

DU_LIEU = os.path.join(os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(__file__)), "VietHoaGame")
FILE_TU_DIEN = os.path.join(DU_LIEU, "phien_am.json")

# ten hay gap (Crimson Desert + Rise of the Tomb Raider) – doc theo kieu nguoi Viet
CO_DINH = {
    # Crimson Desert
    "kliff": "Cờ-líp", "oongka": "Un-ca", "yann": "Dan", "damian": "Đây-mi-ần", "nairah": "Nai-ra",
    "naira": "Nai-ra", "greymane": "Grây-mên", "greymanes": "Grây-mên", "pywel": "Pai-oeo",
    "hernand": "Hơ-nan", "demeniss": "Đê-mơ-nít", "pailune": "Pai-lun", "delesyia": "Đê-lê-xi-a",
    "kweiden": "Quây-đần", "calphade": "Can-phết", "witch": "Phù thủy", "marius": "Ma-ri-út",
    "dwayne": "Đuây-n", "andrew": "An-đru", "tolstein": "Tôn-xtai", "shay": "Sây", "russo": "Ru-xô",
    "valgash": "Van-gát", "alustin": "A-lu-xtin", "shakatu": "Sa-ca-tu", "diederik": "Đi-đơ-ríc",
    "azureian": "A-du-rê-an", "drake": "Đrây-c", "myurdin": "Mi-ua-đin", "kamu": "Ca-mu",
    "matthias": "Ma-thi-át", "crimson": "Crim-xơn", "abyss": "A-bít", "silver": "Xin-vơ", "desert": "Đe-dợt",
    # Rise of the Tomb Raider
    "lara": "La-ra", "croft": "Cờ-róp", "jonah": "Giô-na", "jacob": "Gia-cốp", "nadia": "Na-đi-a",
    "sofia": "Xô-phi-a", "ana": "A-na", "konstantin": "Côn-xtan-tin", "trinity": "Tri-ni-ti",
    "remnant": "Rem-nần", "kitezh": "Ki-tét", "siberia": "Xi-bê-ri-a", "syria": "Xi-ri-a",
    "baba": "Ba-ba", "yaga": "Gia-ga", "atlas": "Át-lát", "richard": "Ri-chát", "lord": "Lo",
    "prophet": "Pro-phít", "divine": "Đi-vai", "source": "Xót", "soviet": "Xô-viết", "gulag": "Gu-lát",
    "constantinople": "Côn-xtan-ti-nốp", "byzantine": "By-dăng", "ivan": "I-van", "jonathan": "Giô-na-than",
}

_AM_TIET = re.compile(
    r"(ngh|ng|gh|gi|kh|nh|ph|qu|th|tr|ch|b|c|d|g|h|k|l|m|n|p|r|s|t|v|x)?"
    r"(uye|uya|uyu|uy|ieu|yeu|uoi|uou|oai|oay|oeo|uay|uao|ai|ao|au|ay|eo|eu|ia|ie|iu|oa|oe|oi|oo|ua|ue|ui|uo|uu|ye|"
    r"a|e|i|o|u|y)(ch|ng|nh|c|m|n|p|t|i|o|u|y)?")
TU = re.compile(r"[A-Za-zÀ-ỹĐđ][A-Za-zÀ-ỹĐđ'’]*")


def la_ngoai(w):
    """Tu thuan chu Latin khong dau va khong phai am tiet tieng Viet -> tu nuoc ngoai."""
    w = w.replace("’", "'")
    return w.isascii() and not la_am_tiet_viet(w.replace("'", ""))


def la_am_tiet_viet(tu):
    """Tu khong dau co the la 1 am tiet tieng Viet (ban, con, toi...) -> khong phien am."""
    return bool(_AM_TIET.fullmatch(tu.lower()))


# ---------------------------------------------------------------- quy tac tu dong
_NGUYEN_AM = "aeiouy"
_VAN = [("ee", "i"), ("ea", "i"), ("oo", "u"), ("ou", "ao"), ("ow", "ao"), ("au", "o"), ("aw", "o"),
        ("ai", "ây"), ("ay", "ây"), ("ei", "ây"), ("ey", "ây"), ("oi", "oi"), ("oy", "oi"), ("ie", "i"),
        ("ue", "u"), ("ui", "ui"), ("ia", "ia"), ("io", "iô"), ("eu", "iu"),
        ("a", "a"), ("e", "e"), ("i", "i"), ("o", "ô"), ("u", "u"), ("y", "i")]
_DAU = [("sch", "s"), ("tch", "ch"), ("ch", "ch"), ("sh", "s"), ("th", "th"), ("ph", "ph"), ("kh", "kh"),
        ("gh", "g"), ("wh", "u"), ("qu", "qu"), ("ck", "c"), ("b", "b"), ("c", "c"), ("d", "đ"), ("f", "ph"),
        ("g", "g"), ("h", "h"), ("j", "gi"), ("k", "c"), ("l", "l"), ("m", "m"), ("n", "n"), ("p", "p"),
        ("q", "c"), ("r", "r"), ("s", "x"), ("t", "t"), ("v", "v"), ("w", "u"), ("x", "x"), ("z", "d")]
_CUOI = {"c": "c", "k": "c", "ck": "c", "g": "c", "q": "c", "d": "t", "t": "t", "th": "t", "b": "p", "p": "p",
         "f": "p", "ff": "p", "ph": "p", "v": "p", "n": "n", "nn": "n", "m": "m", "mm": "m", "ng": "ng",
         "nk": "ng", "l": "n", "ll": "n", "r": "", "rr": "", "s": "", "ss": "t", "z": "", "x": "c", "ch": "ch",
         "sh": "", "tch": "ch", "h": "", "gh": "", "w": "", "y": ""}


def _phu_am(s):
    ra, i = [], 0
    while i < len(s):
        for a, b in _DAU:
            if s.startswith(a, i):
                ra.append(b)
                i += len(a)
                break
        else:
            i += 1
    return ra


def _van(s):
    for a, b in _VAN:
        if s.startswith(a):
            return b, len(a)
    return "", 1


def _gan_cuoi(am, cuoi):
    """Them phu am cuoi; van ket thuc bang ban nguyen am (ây, ao, oi...) thi bo ban nguyen am."""
    if len(am) >= 2 and am[-1] in "yiuo" and am[-2] in "âaôoeu":
        am = am[:-1]
    return am + cuoi


def quy_tac(tu):
    """Phien am thô bang quy tac: 'Hernand' -> 'Hơ-nan', 'Brollam' -> 'Bơ-rô-lam'."""
    s = re.sub(r"[^a-z]", "", tu.lower())
    if not s:
        return tu
    s = re.sub(r"([b-df-hj-np-tv-z])\1", r"\1", s)          # phu am doi: ff, ll, tt -> 1
    if len(s) > 3 and re.search(r"[^aeiouy]e$", s) and not s.endswith(("ee", "le")):
        s = s[:-1]                                             # e cam cuoi tu: Pailune -> Pailun
    # cat thanh [phu am dau][nguyen am][phu am giua]...
    khuc = re.findall(r"[^aeiouy]*[aeiouy]+|[^aeiouy]+$", s)
    am = []
    for k, cum in enumerate(khuc):
        m = re.match(r"([^aeiouy]*)([aeiouy]*)", cum)
        dau, nguyen = m.group(1), m.group(2)
        if not nguyen:                         # phu am o cuoi tu
            cuoi = _CUOI.get(dau)
            if cuoi is None and dau:
                cuoi = _CUOI.get(dau[0], "") or _CUOI.get(dau[-1], "")
            if am and cuoi:
                am[-1] = _gan_cuoi(am[-1], cuoi)
            continue
        pa = _phu_am(dau)
        # cum phu am (kl, str...) -> them am "ơ" cho cac phu am dau
        for p in pa[:-1]:
            am.append(p + "ơ")
        van, _ = _van(nguyen)
        am.append((pa[-1] if pa else "") + van)
        # phu am dung giua 2 nguyen am: cuoi am truoc lay 1 phu am neu cum >= 2
        if k + 1 < len(khuc):
            sau = re.match(r"[^aeiouy]*", khuc[k + 1]).group(0)
            if len(sau) >= 2 and sau[0] in "mnlr" and khuc[k + 1][len(sau):]:
                cuoi = _CUOI.get(sau[0], "")
                if sau[0] == "r" and am[-1].endswith("e"):
                    am[-1] = am[-1][:-1] + "ơ"                  # "er" -> ơ: Hernand -> Hơ-nan
                if cuoi:
                    am[-1] = _gan_cuoi(am[-1], cuoi)
                khuc[k + 1] = khuc[k + 1][1:]
    am = [a.replace("cy", "ki").replace("ci", "ki").replace("ce", "ke").replace("ge", "ghe").replace("gi", "ghi")
          .replace("đi", "đi") for a in am if a]
    if not am:
        return tu
    kq = "-".join(am)
    return kq[0].upper() + kq[1:]


# ---------------------------------------------------------------- tu dien
class TuDien:
    def __init__(self):
        self.khoa_luong = threading.Lock()
        try:
            with open(FILE_TU_DIEN, encoding="utf-8") as f:
                self.tu = json.load(f)
        except Exception:
            self.tu = {}

    def luu(self):
        os.makedirs(DU_LIEU, exist_ok=True)
        with open(FILE_TU_DIEN + ".tam", "w", encoding="utf-8") as f:
            json.dump(self.tu, f, ensure_ascii=False, indent=0)
        os.replace(FILE_TU_DIEN + ".tam", FILE_TU_DIEN)

    @staticmethod
    def tu_ngoai(van_ban):
        """Cac tu nuoc ngoai (khong phai am tiet tieng Viet) trong cau tieng Viet."""
        return {w.replace("’", "'") for w in TU.findall(van_ban or "") if la_ngoai(w)}

    def cach_doc(self, tu):
        k = tu.lower().replace("'s", "").replace("'", "")
        return CO_DINH.get(k) or self.tu.get(k) or quy_tac(k)

    def doc_duoc(self, van_ban):
        """Thay ten nuoc ngoai bang cach doc tieng Viet (chi cho may doc)."""
        def thay(m):
            w = m.group(0)
            if not la_ngoai(w):
                return w
            return self.cach_doc(w).replace("-", " ")      # may doc: am tiet cach nhau bang khoang trang
        return TU.sub(thay, van_ban or "")

    def hoc_bang_claude(self, cac_cau, khoa, bao=lambda s: None):
        """Gom tu nuoc ngoai chua co trong tu dien, nho Claude phien am (theo lo), luu lai."""
        if not khoa:
            return 0
        import viet_hoa_cd as vcd
        can = set()
        for c in cac_cau:
            for w in self.tu_ngoai(c):
                k = w.lower().replace("'s", "").replace("'", "")
                if len(k) >= 2 and k not in CO_DINH and k not in self.tu:
                    can.add(k)
        can = sorted(can)
        if not can:
            return 0
        cl = vcd.Claude(khoa, huong_dan=(
            "Bạn phiên âm tên riêng / từ tiếng nước ngoài trong game sang cách đọc tiếng Việt để máy đọc tiếng Việt "
            "đọc lên nghe giống tiếng gốc. Mỗi âm tiết là một âm tiết tiếng Việt HỢP LỆ có dấu thanh, nối bằng "
            "gạch nối. Phụ âm ghép không có trong tiếng Việt thì tách thành âm tiết riêng (Kliff -> Cờ-líp, "
            "Konstantin -> Côn-xtan-tin, Hernand -> Hơ-nan, Pywel -> Pai-oeo). Từ tiếng Anh thông dụng thì đọc "
            "theo cách người Việt hay đọc (OK -> Ô-kê). CHỈ trả về một đối tượng JSON {từ: cách đọc}, không giải "
            "thích, không ```."))
        xong = 0
        for i in range(0, len(can), 150):
            lo = can[i:i + 150]
            bao(f"Đang nhờ Claude phiên âm tên riêng {min(i + 150, len(can))}/{len(can)}...")
            try:
                chu, _, _ = cl.goi(json.dumps(lo, ensure_ascii=False), 6000)
                chu = chu.strip().strip("`")
                chu = chu[chu.find("{"):chu.rfind("}") + 1]
                kq = json.loads(chu)
            except Exception:
                continue
            for k, v in kq.items():
                k = str(k).lower().replace("'s", "").replace("'", "")
                if isinstance(v, str) and v.strip() and len(v) < 80:
                    self.tu[k] = v.strip()
                    xong += 1
            self.luu()
        return xong
