# -*- coding: utf-8 -*-
"""
Do file chu cua MOI game (chi do game nguoi dung chon).

  - Quet thu muc game, tim file co nhieu chu tieng Anh, cho biet file nao, loai gi, bao nhieu cau, cau mau.
  - Doc / ghi duoc cac dang file chu pho bien: JSON (ca RPG Maker), CSV/TSV, XML/RESX, INI/LANG/PROPERTIES/STRINGS,
    PO, YAML, TXT, Ren'Py .rpy, Unreal .locres (de roi).
  - Goi nen rieng cua hang (Unreal .pak, Unity .assets, Ren'Py .rpa, .tiger, .paz...) chi bao "chua ho tro".
  - Dich bang bo may dich chung (Claude theo lo / Offline), hoac tu dich bang file CSV (Excel).
  - Ghi vao game: luon sao luu ban goc truoc, co nut tra lai ban goc.
"""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import struct
import time
import unicodedata

import viet_hoa_cd as vcd

THU_MUC_DO = os.path.join(vcd.DU_LIEU, "do_file")
PHIEN_BAN_QUET = 1

DUOI_CHU = {
    ".json": "json", ".csv": "csv", ".tsv": "csv", ".xml": "xml", ".resx": "xml", ".xliff": "xml", ".xlf": "xml",
    ".ini": "ini", ".lang": "ini", ".properties": "ini", ".cfg": "ini", ".strings": "ini", ".loc": "ini",
    ".po": "po", ".pot": "po", ".yml": "yaml", ".yaml": "yaml", ".txt": "txt", ".rpy": "rpy", ".locres": "locres",
}
TEN_LOAI = {"json": "JSON", "csv": "Bảng CSV", "xml": "XML", "ini": "Danh sách khóa=chữ", "po": "Gettext PO",
            "yaml": "YAML", "txt": "Văn bản", "rpy": "Kịch bản Ren'Py", "locres": "Unreal .locres"}
GOI_NEN = {
    ".pak": "gói Unreal Engine (.pak)", ".utoc": "gói Unreal Engine (.utoc/.ucas)", ".ucas": "gói Unreal Engine (.utoc/.ucas)",
    ".assets": "gói Unity (.assets)", ".bundle": "gói Unity (.bundle)", ".resource": "gói Unity (.resource)",
    ".rpa": "gói Ren'Py (.rpa)", ".pck": "gói Godot (.pck)", ".tiger": "gói Crystal Dynamics (.tiger)",
    ".paz": "gói Pearl Abyss (.paz)", ".forge": "gói Ubisoft (.forge)", ".cpk": "gói CRI (.cpk)",
    ".vpk": "gói Valve (.vpk)", ".big": "gói .big", ".wad": "gói .wad", ".arc": "gói .arc", ".rgssad": "gói RPG Maker XP/VX",
    ".rgss2a": "gói RPG Maker VX", ".rgss3a": "gói RPG Maker VX Ace", ".bnk": None, ".pck_": None,
}
BO_THU_MUC = {"__pycache__", ".git", "_commonredist", "directx", "redist", "redistributables", "vcredist",
              "dotnetfx", "physx", "easyanticheat", "battleye", "steam_settings", "__installer", "_redist",
              "binaries", "plugins", "crashreportclient", "mono", "monobleedingedge", "il2cpp_data"}
BO_TEN = re.compile(r"(readme|license|licence|eula|credits|changelog|third.?party|copying|notice|patch.?notes|"
                    r"steam_appid|unins|version)", re.I)
TU_ANH = {"the", "and", "you", "to", "of", "is", "a", "in", "it", "your", "for", "that", "this", "with", "on",
          "are", "be", "have", "not", "we", "can", "will", "my", "what", "i", "me", "do", "an", "at", "if", "from"}
KHOA_BO = {"id", "key", "type", "icon", "iconindex", "image", "file", "filename", "path", "sound", "se", "bgm",
           "bgs", "me", "script", "class", "tag", "tags", "url", "font", "animation", "charactername", "facename",
           "battlername", "picture", "texture", "sprite", "model", "prefab", "material", "shader", "guid", "uuid",
           "hash", "version", "color", "colour", "format", "locale", "lang", "language", "code", "ref", "asset",
           "assetpath", "event", "trigger", "command", "anim", "audio", "music", "voice", "tileset", "parallaxname",
           "title1name", "title2name", "battleback1name", "battleback2name", "note", "plugin", "parameters_raw"}
MA_RPG_BO = {355, 655, 356, 357, 108, 408, 111, 122, 231, 241, 245, 249, 250, 132, 133, 139, 283, 284}

# the / ma can giu nguyen (dung de kiem tra ban dich)
THE = re.compile(r"<[^<>]*>|\{[^{}]*\}|\[[^\[\]]*\]|%[-+ 0#]*\d*(?:\.\d+)?[sdifxXuc@]|%\d+\$?[sd]?|\\[nrt]|"
                 r"\$[A-Za-z_][A-Za-z0-9_]*|\\[A-Za-z]+\[[^\]]*\]|\\[A-Za-z{}\\|.!<>^$]")


def the_cua(s):
    return sorted(THE.findall(s))


def bo_dau(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def la_chu_anh(s):
    """Chuoi co ve la chu tieng Anh hien len man hinh (khong phai ma, duong dan, ten file...)."""
    if not isinstance(s, str) or len(s) < 2 or len(s) > 5000:
        return False
    t = THE.sub(" ", s).strip()
    if len(t) < 2 or not re.search(r"[A-Za-z]{2,}", t):
        return False
    if "://" in t or re.fullmatch(r"[\w\-./\\]+\.[A-Za-z0-9]{2,4}", t) or re.fullmatch(r"[\w\-]+[/\\][\w\-./\\]*", t):
        return False
    chu = re.findall(r"[^\W\d_]", t)
    if chu and sum(1 for c in chu if c.isascii()) / len(chu) < 0.9:
        return False                                 # ngon ngu khac (Trung, Nga, Viet...)
    if " " not in t:
        if "_" in t or re.search(r"[a-z][A-Z]", t) or re.search(r"[A-Za-z]\d|\d[A-Za-z]", t):
            return False                             # ma noi bo: ten_bien, TenBien, abc123
        if t.islower() or t.isupper() and len(t) > 12:
            return False                             # true, normal, CONSTANT_NAME
    ma = sum(1 for c in t if c in "{}();=<>|&*^~`\\")
    if ma > max(2, len(t) * 0.12):
        return False
    return True


def la_cau(s):
    return len(THE.sub(" ", s).split()) >= 3


def ty_le_anh(cac):
    tu = [w.lower() for s in cac[:3000] for w in re.findall(r"[A-Za-z']+", s)]
    if not tu:
        return 0.0
    return sum(1 for w in tu if w in TU_ANH) / len(tu)


# ================================================================ doc / ghi chu (ma hoa)

def giai_ma(b):
    """bytes -> (chu, ma_hoa, bom)"""
    for bom, mh in ((b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if b.startswith(bom):
            return b[len(bom):].decode(mh, "replace"), mh, bom
    if len(b) >= 4 and b[1:2] == b"\0" and b[3:4] == b"\0":
        return b.decode("utf-16-le", "replace"), "utf-16-le", b""
    try:
        return b.decode("utf-8"), "utf-8", b""
    except UnicodeDecodeError:
        return b.decode("cp1252", "replace"), "cp1252", b""


def ma_hoa(chu, mh, bom):
    try:
        return bom + chu.encode(mh)
    except UnicodeEncodeError:
        if mh == "cp1252":       # file cu khong chua duoc tieng Viet -> ghi UTF-8 co BOM
            return b"\xef\xbb\xbf" + chu.encode("utf-8")
        raise


# ================================================================ cac dinh dang
# Moi dinh dang: doc(b) -> [(khoa, chu_anh)] ; ghi(b, dich) -> bytes. dich(chu_anh) -> chu_viet hoac None.

class DangRegex:
    """Dinh dang doc bang 1 bieu thuc chinh quy: nhom 'v' la chu. Ghi = thay dung cac nhom do."""
    MAU = None

    def _tach(self, m):
        return m.group("v")

    def _mo(self, v):
        return v

    def _dong(self, v, m):
        return v

    def doc(self, b):
        chu, _, _ = giai_ma(b)
        kq = []
        for i, m in enumerate(self.MAU.finditer(chu)):
            v = self._mo(self._tach(m))
            if v is not None and self.loc(v, m):
                kq.append((f"{m.start('v')}", v))
        return kq

    def loc(self, v, m):
        return la_chu_anh(v)

    def ghi(self, b, dich):
        chu, mh, bom = giai_ma(b)

        def thay(m):
            v = self._mo(self._tach(m))
            if v is None or not self.loc(v, m):
                return m.group(0)
            vi = dich(v)
            if vi is None:
                return m.group(0)
            a, z = m.start("v") - m.start(0), m.end("v") - m.start(0)
            g = m.group(0)
            return g[:a] + self._dong(vi, m) + g[z:]
        return ma_hoa(self.MAU.sub(thay, chu), mh, bom)


def _xml_mo(v):
    return (v.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
            .replace("&#10;", "\n").replace("&amp;", "&"))


def _xml_dong(v):
    return v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class DangXml(DangRegex):
    MAU = re.compile(r"<!\[CDATA\[(?P<c>.*?)\]\]>|(?<=>)(?P<t>[^<>]+)(?=<)|"
                     r"\b(?i:text|value|string|label|title|caption|desc|description|tooltip|content|message|"
                     r"displayname|display_name|hint|header|body)\s*=\s*\"(?P<a>[^\"]*)\"", re.S)

    def _tach(self, m):
        return m.group("c") if m.group("c") is not None else (m.group("t") if m.group("t") is not None else m.group("a"))

    def doc(self, b):
        chu, _, _ = giai_ma(b)
        kq = []
        for m in self.MAU.finditer(chu):
            v = self._v(m)
            if v.strip() and la_chu_anh(v.strip()):
                kq.append((str(m.start()), v.strip()))
        return kq

    def _v(self, m):
        if m.group("c") is not None:
            return m.group("c")
        return _xml_mo(m.group("t") if m.group("t") is not None else m.group("a"))

    def ghi(self, b, dich):
        chu, mh, bom = giai_ma(b)

        def thay(m):
            v = self._v(m)
            s = v.strip()
            if not s or not la_chu_anh(s):
                return m.group(0)
            vi = dich(s)
            if vi is None:
                return m.group(0)
            moi = v.replace(s, vi, 1)
            ten = "c" if m.group("c") is not None else ("t" if m.group("t") is not None else "a")
            if ten != "c":
                moi = _xml_dong(moi) if ten == "a" else _xml_dong(moi).replace("&quot;", '"')
            a, z = m.start(ten) - m.start(0), m.end(ten) - m.start(0)
            return m.group(0)[:a] + moi + m.group(0)[z:]
        return ma_hoa(self.MAU.sub(thay, chu), mh, bom)


def _thoat(vi, q='"'):
    """Them dau \\ truoc dau nhay chua duoc thoat (chu doc ra van giu nguyen cac ma thoat goc)."""
    return re.sub(r'(?<!\\)' + re.escape(q), lambda m: "\\" + q, vi.replace("\r\n", "\\n").replace("\n", "\\n"))


def _nhay_mo(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


class DangIni(DangRegex):
    # key = value | "key" = "value"; (Apple .strings) | key: value (properties)
    MAU = re.compile(r'(?m)^(?P<k>[ \t]*(?:"(?:[^"\\]|\\.)*"|[^\s=#;\[/][^=\r\n]*?)[ \t]*=[ \t]*)'
                     r'(?P<v>"(?:[^"\\]|\\.)*"|[^\r\n]*?)[ \t]*;?[ \t]*$')

    def _mo(self, v):
        return _nhay_mo(v)

    def _dong(self, vi, m):
        g = m.group("v").strip()
        if len(g) >= 2 and g[0] == g[-1] and g[0] in "\"'":
            q = g[0]
            return q + _thoat(vi, q) + q
        return vi.replace("\n", "\\n")

    def ghi(self, b, dich):
        chu, mh, bom = giai_ma(b)

        def thay(m):
            v = self._mo(m.group("v"))
            if not self.loc(v, m):
                return m.group(0)
            vi = dich(v)
            if vi is None:
                return m.group(0)
            a, z = m.start("v") - m.start(0), m.end("v") - m.start(0)
            return m.group(0)[:a] + self._dong(vi, m) + m.group(0)[z:]
        return ma_hoa(self.MAU.sub(thay, chu), mh, bom)


class DangYaml(DangIni):
    MAU = re.compile(r'(?m)^(?P<k>[ \t]*(?:- )?[\w.\-"\' ]+:[ \t]+)(?P<v>(?!["\']?\s*$)[^|>&*!{\[\r\n#][^\r\n]*?)[ \t]*$')

    def _mo(self, v):
        v = v.strip()
        if v in ("true", "false", "null", "~") or re.fullmatch(r"-?[\d.]+", v):
            return None
        if len(v) >= 2 and v[0] == v[-1] == "'":
            return v[1:-1].replace("''", "'")
        if len(v) >= 2 and v[0] == v[-1] == '"':
            return v[1:-1]
        return v

    def _dong(self, vi, m):
        g = m.group("v").strip()
        if g.startswith("'"):
            return "'" + vi.replace("'", "''") + "'"
        return '"' + _thoat(vi) + '"'

    def ghi(self, b, dich):
        chu, mh, bom = giai_ma(b)

        def thay(m):
            v = self._mo(m.group("v"))
            if v is None or not self.loc(v, m):
                return m.group(0)
            vi = dich(v)
            if vi is None:
                return m.group(0)
            a, z = m.start("v") - m.start(0), m.end("v") - m.start(0)
            return m.group(0)[:a] + self._dong(vi, m) + m.group(0)[z:]
        return ma_hoa(self.MAU.sub(thay, chu), mh, bom)


class DangTxt(DangRegex):
    MAU = re.compile(r"(?m)^(?P<l>[ \t]*)(?P<v>\S[^\r\n]*?)[ \t]*$")

    def loc(self, v, m):
        return la_chu_anh(v) and len(v.split()) >= 2


class DangRpy(DangRegex):
    MAU = re.compile(r'(?m)^(?P<l>[ \t]*)(?:(?P<n>[A-Za-z_][\w.]*)[ \t]+)?"(?P<v>(?:[^"\\\r\n]|\\.)*)"'
                     r'(?P<s>[ \t]*(?:with[ \t]+\w+)?[ \t]*:?)[ \t]*$')
    BO = {"old", "new", "voice", "play", "queue", "image", "show", "call", "jump", "style", "define", "default",
          "scene", "hide", "font", "translate", "label", "screen", "action", "text_font", "renpy"}

    def _dong(self, vi, m):
        return _thoat(vi)

    def loc(self, v, m):
        return (m.group("n") or "") not in self.BO and la_chu_anh(v)


class DangPo:
    def _muc(self, chu):
        dong = chu.splitlines(keepends=True)
        i, kq = 0, []
        while i < len(dong):
            if dong[i].startswith("msgid "):
                a = i
                id_ = [re.match(r'msgid\s+"(.*)"\s*$', dong[i]).group(1)] if re.match(r'msgid\s+"(.*)"\s*$', dong[i]) else [""]
                i += 1
                while i < len(dong) and dong[i].lstrip().startswith('"'):
                    id_.append(dong[i].strip()[1:-1])
                    i += 1
                if i < len(dong) and dong[i].startswith("msgstr"):
                    s = i
                    i += 1
                    while i < len(dong) and dong[i].lstrip().startswith('"'):
                        i += 1
                    kq.append((a, s, i, "".join(id_)))
                continue
            i += 1
        return dong, kq

    def doc(self, b):
        chu, _, _ = giai_ma(b)
        _, ds = self._muc(chu)
        return [(str(a), v) for a, s, e, v in ds if v and la_chu_anh(v)]

    def ghi(self, b, dich):
        chu, mh, bom = giai_ma(b)
        dong, ds = self._muc(chu)
        for a, s, e, v in reversed(ds):
            if not v or not la_chu_anh(v):
                continue
            vi = dich(v)
            if vi is None:
                continue
            xd = "\r\n" if dong[s].endswith("\r\n") else "\n"
            dong[s:e] = ['msgstr "' + _thoat(vi) + '"' + xd]
        return ma_hoa("".join(dong), mh, bom)


class DangCsv:
    COT_ANH = {"en", "eng", "english", "en-us", "en_us", "en-gb", "en_gb", "text", "source", "value", "string",
               "english(en)", "english (en)", "en_text", "text_en", "englishtext"}

    def _doc(self, b):
        chu, mh, bom = giai_ma(b)
        mau = chu[:20000]
        try:
            dl = csv.Sniffer().sniff(mau, delimiters=",;\t|").delimiter
        except csv.Error:
            dl = "\t" if mau.count("\t") > mau.count(",") else ","
        hang = list(csv.reader(io.StringIO(chu, newline=""), delimiter=dl))
        xd = "\r\n" if "\r\n" in chu[:5000] else "\n"
        cot = None
        if hang:
            dau = [c.strip().lower() for c in hang[0]]
            for i, c in enumerate(dau):
                if c in self.COT_ANH or "english" in c:
                    cot = i
                    break
        return chu, mh, bom, dl, hang, xd, cot

    def _o(self, hang, cot):
        for r, h in enumerate(hang):
            if cot is not None:
                if r == 0 or cot >= len(h):
                    continue
                yield r, cot, h[cot]
            else:
                for c, v in enumerate(h):
                    yield r, c, v

    def doc(self, b):
        chu, mh, bom, dl, hang, xd, cot = self._doc(b)
        return [(f"{r}:{c}", v) for r, c, v in self._o(hang, cot) if la_chu_anh(v) and (cot is not None or la_cau(v))]

    def ghi(self, b, dich):
        chu, mh, bom, dl, hang, xd, cot = self._doc(b)
        for r, c, v in list(self._o(hang, cot)):
            if la_chu_anh(v) and (cot is not None or la_cau(v)):
                vi = dich(v)
                if vi is not None:
                    hang[r][c] = vi
        ra = io.StringIO(newline="")
        w = csv.writer(ra, delimiter=dl, lineterminator=xd)
        w.writerows(hang)
        moi = ra.getvalue()
        if not chu.endswith(("\n", "\r")):
            moi = moi.rstrip("\r\n")
        return ma_hoa(moi, mh, bom)


class DangJson:
    def _duyet(self, o, duong, ra, cha_ma=None):
        if isinstance(o, dict):
            am = {"volume", "pitch", "pan"} <= set(o)
            ma = o.get("code") if isinstance(o.get("code"), int) else None
            for k, v in o.items():
                kl = str(k).lower()
                if kl in KHOA_BO or (am and kl == "name"):
                    continue
                if ma in MA_RPG_BO and kl == "parameters":
                    continue
                self._duyet(v, duong + (k,), ra, ma)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                self._duyet(v, duong + (i,), ra, cha_ma)
        elif isinstance(o, str) and la_chu_anh(o):
            ra.append((duong, o))

    def _nap(self, b):
        chu, mh, bom = giai_ma(b)
        return chu, mh, bom, json.loads(chu)

    def doc(self, b):
        _, _, _, o = self._nap(b)
        ra = []
        self._duyet(o, (), ra)
        return [(json.dumps(d), v) for d, v in ra]

    def ghi(self, b, dich):
        chu, mh, bom, o = self._nap(b)
        ra = []
        self._duyet(o, (), ra)
        doi = 0
        for d, v in ra:
            vi = dich(v)
            if vi is None:
                continue
            x = o
            for k in d[:-1]:
                x = x[k]
            x[d[-1]] = vi
            doi += 1
        if not doi:
            return b
        m = re.search(r'\n([ \t]+)["{\[]', chu)
        if m:
            thut = m.group(1) if m.group(1).startswith("\t") else len(m.group(1))
            moi = json.dumps(o, ensure_ascii=False, indent=thut)
            if "\r\n" in chu[:2000]:
                moi = moi.replace("\n", "\r\n")
        else:
            moi = json.dumps(o, ensure_ascii=False, separators=(",", ":") if chu.count('":') > chu.count('": ') else (", ", ": "))
        if chu.endswith("\n"):
            moi += "\r\n" if chu.endswith("\r\n") else "\n"
        return ma_hoa(moi, mh, bom)


# ---------------------------------------------------------------- Unreal .locres

MAGIC_LOCRES = bytes.fromhex("0E14747567 4A03FC4A15909DC3377F1B".replace(" ", ""))


class _Doc:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def i64(self):
        v = struct.unpack_from("<q", self.b, self.p)[0]
        self.p += 8
        return v

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            s = self.b[self.p:self.p - 2 * n].decode("utf-16-le", "replace")
            self.p += -2 * n
        else:
            s = self.b[self.p:self.p + n].decode("cp1252", "replace")
            self.p += n
        return s[:-1] if s.endswith("\0") else s


def ghi_fstr(s):
    if not s:
        return struct.pack("<i", 0)
    if all(ord(c) < 128 for c in s):
        d = s.encode("ascii") + b"\0"
        return struct.pack("<i", len(d)) + d
    d = s.encode("utf-16-le") + b"\0\0"
    return struct.pack("<i", -(len(d) // 2)) + d


class DangLocres:
    def _nap(self, b):
        r = _Doc(b)
        ban = 0
        if b[:16] == MAGIC_LOCRES:
            r.p = 16
            ban = b[16]
            r.p = 17
        if ban == 0:
            # ban cu: gia tri nam ngay trong bang
            kq = []
            so_ns = r.u32()
            for _ in range(so_ns):
                r.fstr()
                so = r.u32()
                for _ in range(so):
                    r.fstr()
                    r.u32()
                    vt = r.p
                    v = r.fstr()
                    kq.append((vt, r.p, v))
            return {"ban": 0, "o": kq}
        vt_mang = r.i64()
        r2 = _Doc(b, vt_mang)
        so = r2.i32()
        mang = []
        for _ in range(so):
            v = r2.fstr()
            dem = r2.i32() if ban >= 2 else None
            mang.append((v, dem))
        return {"ban": ban, "vt_mang": vt_mang, "mang": mang, "het": r2.p}

    def doc(self, b):
        d = self._nap(b)
        if d["ban"] == 0:
            return [(str(i), v) for i, (_, _, v) in enumerate(d["o"]) if la_chu_anh(v)]
        return [(str(i), v) for i, (v, _) in enumerate(d["mang"]) if la_chu_anh(v)]

    def ghi(self, b, dich):
        d = self._nap(b)

        def doi(v):
            if not la_chu_anh(v):
                return v
            vi = dich(v)
            return v if vi is None else vi
        if d["ban"] == 0:
            ra, cu = bytearray(), 0
            for a, z, v in d["o"]:
                ra += b[cu:a] + ghi_fstr(doi(v))
                cu = z
            ra += b[cu:]
            return bytes(ra)
        mang = bytearray(struct.pack("<i", len(d["mang"])))
        for v, dem in d["mang"]:
            mang += ghi_fstr(doi(v))
            if dem is not None:
                mang += struct.pack("<i", dem)
        return b[:d["vt_mang"]] + bytes(mang) + b[d["het"]:]


DANG = {"json": DangJson(), "csv": DangCsv(), "xml": DangXml(), "ini": DangIni(), "po": DangPo(),
        "yaml": DangYaml(), "txt": DangTxt(), "rpy": DangRpy(), "locres": DangLocres()}


# ================================================================ quet thu muc game

def nhan_dien_engine(thu_muc):
    try:
        ten = {t.lower() for t in os.listdir(thu_muc)}
    except OSError:
        return ""
    if any(t.endswith("_data") for t in ten) or "unityplayer.dll" in ten:
        return "Unity"
    if "engine" in ten or any(t.endswith(".uproject") for t in ten):
        return "Unreal Engine"
    if "renpy" in ten or ("game" in ten and "lib" in ten):
        return "Ren'Py"
    if "www" in ten or ("data" in ten and "js" in ten) or any(t.endswith((".rgss3a", ".rgss2a", ".rgssad")) for t in ten):
        return "RPG Maker"
    if any(t.endswith(".pck") for t in ten):
        return "Godot"
    return ""


def thu_muc_viec(thu_muc_game):
    ten = re.sub(r"[^\w\-]+", "_", os.path.basename(os.path.normpath(thu_muc_game)))[:40]
    return os.path.join(THU_MUC_DO, f"{ten}_{hashlib.md5(os.path.normcase(thu_muc_game).encode('utf-8')).hexdigest()[:8]}")


def quet(thu_muc_game, bao=lambda s: None, dung=None, gioi_han_tep=200000):
    """-> dict(engine, file=[{tuong_doi, loai, co, so, so_cau, anh, mau}], goi=[{loai, so, co, vi_du}])"""
    ds, goi = [], {}
    dem = 0
    moc = time.time()
    for goc, thu, tep in os.walk(thu_muc_game):
        thu[:] = [t for t in thu if t.lower() not in BO_THU_MUC]
        for t in tep:
            dem += 1
            if dem > gioi_han_tep or (dung is not None and dung.is_set()):
                break
            p = os.path.join(goc, t)
            duoi = os.path.splitext(t)[1].lower()
            if time.time() - moc > 0.5:
                moc = time.time()
                bao(f"Đang dò: {dem:,} file – {os.path.relpath(p, thu_muc_game)}".replace(",", "."))
            if duoi in GOI_NEN and GOI_NEN[duoi]:
                try:
                    co = os.path.getsize(p)
                except OSError:
                    continue
                g = goi.setdefault(GOI_NEN[duoi], {"loai": GOI_NEN[duoi], "so": 0, "co": 0, "vi_du": []})
                g["so"] += 1
                g["co"] += co
                if len(g["vi_du"]) < 3:
                    g["vi_du"].append(os.path.relpath(p, thu_muc_game))
                continue
            loai = DUOI_CHU.get(duoi)
            if not loai or BO_TEN.search(t):
                continue
            try:
                co = os.path.getsize(p)
                if co < 8 or co > (60 << 20):
                    continue
                with open(p, "rb") as f:
                    b = f.read()
                cac = DANG[loai].doc(b)
            except Exception:
                continue
            if not cac:
                continue
            chu = [v for _, v in cac]
            so_cau = sum(1 for v in chu if la_cau(v))
            anh = ty_le_anh(chu)
            if loai == "txt" and (len(cac) < 5 or anh < 0.04):
                continue
            mau = sorted({v.replace("\n", " ")[:120] for v in chu if la_cau(v)} or {v[:120] for v in chu},
                         key=lambda v: -len(v))[:3]
            ds.append({"tuong_doi": os.path.relpath(p, thu_muc_game), "loai": loai, "co": co, "so": len(cac),
                       "so_cau": so_cau, "anh": round(anh, 3), "mau": mau, "mtime": os.path.getmtime(p)})
    for f in ds:
        ten = f["tuong_doi"].lower()
        diem = f["so"] + 3 * f["so_cau"]
        if re.search(r"(^|[\\/_.\-])(en|eng|english|en[-_]us)([\\/_.\-]|$)", ten):
            diem *= 2
        if f["anh"] < 0.03:
            diem *= 0.2
        f["diem"] = diem
    ds.sort(key=lambda f: -f["diem"])
    return {"phien_ban": PHIEN_BAN_QUET, "thu_muc": thu_muc_game, "engine": nhan_dien_engine(thu_muc_game),
            "luc": time.strftime("%d/%m/%Y %H:%M"), "file": ds, "goi": sorted(goi.values(), key=lambda g: -g["co"]),
            "so_tep": dem}


# ================================================================ cong viec dich + ghi

HUONG_DAN_CHUNG = """Bạn là dịch giả chuyên Việt hóa game. Game: {ten}.
Bạn nhận một mảng JSON các chuỗi tiếng Anh lấy từ file chữ của game và trả về mảng JSON các bản dịch tiếng Việt.

Quy tắc bắt buộc:
- CHỈ trả về một mảng JSON hợp lệ, CÙNG SỐ PHẦN TỬ, CÙNG THỨ TỰ. Không giải thích, không ```.
- GIỮ NGUYÊN tiếng Anh: tên người, địa danh, tổ chức, phe phái, tên riêng của vật phẩm / kỹ năng, \
và mọi từ trong danh sách "Giữ nguyên" nếu có.
- Giữ NGUYÊN từng ký tự mọi thẻ và mã: <...>, {{...}}, [...], %s, %d, %1, \\n, \\c[1], $..., kể cả khoảng trắng quanh chúng. \
Không dịch, không thêm, không bớt thẻ.
- Giữ nguyên số, ký hiệu, khoảng trắng đầu/cuối và cách xuống dòng.
- Nếu một chuỗi là mã kỹ thuật, tên file hay từ khóa lập trình thì trả về NGUYÊN VĂN.
- Văn phong tự nhiên như game Việt hóa chính thức; menu / nút bấm ngắn gọn; xưng hô hợp ngữ cảnh.
"""


class ViecFile(vcd.ViecDich):
    """Dich cac file chu nguoi dung chon trong mot game bat ky."""

    def __init__(self, thu_muc_game, ten_game=""):
        super().__init__(thu_muc_game, 1)
        self.ten_game = ten_game or os.path.basename(os.path.normpath(thu_muc_game))
        self.HUONG_DAN = HUONG_DAN_CHUNG.format(ten=self.ten_game)
        self.tm = thu_muc_viec(thu_muc_game)
        self.file_bo_nho = os.path.join(self.tm, "bo_nho_dich.json")
        self.file_quet = os.path.join(self.tm, "ket_qua_do.json")
        self.file_ghi = os.path.join(self.tm, "da_ghi.json")
        self.sao_luu = os.path.join(self.tm, "sao_luu")
        self.bang_ten = vcd.BangTen(set())
        self.kq_quet = None
        self.chon = []               # danh sach duong dan tuong doi da chon
        self.chu = {}                # tuong_doi -> [(khoa, chu_anh)]

    # ---------------------------------------------------------- luu / nap
    def nap(self, bao=lambda s: None):
        self.bo_nho = _doc_json(self.file_bo_nho, {})
        self.kq_quet = _doc_json(self.file_quet, None)
        if self.kq_quet and self.kq_quet.get("phien_ban") != PHIEN_BAN_QUET:
            self.kq_quet = None
        if self.kq_quet:
            self.chon = list(self.kq_quet.get("chon", []))
        return self

    def luu(self):
        with self.khoa:
            d = dict(self.bo_nho)
        _ghi_json(self.file_bo_nho, d)

    def quet(self, bao=lambda s: None):
        self.kq_quet = quet(self.thu_muc_game, bao, self.dung)
        # tu chon san cac file tot nhat (tieng Anh ro rang)
        self.chon = [f["tuong_doi"] for f in self.kq_quet["file"][:40] if f["anh"] >= 0.03 and f["diem"] >= 10][:5]
        self.luu_quet()
        return self.kq_quet

    def luu_quet(self):
        if self.kq_quet is not None:
            self.kq_quet["chon"] = self.chon
            _ghi_json(self.file_quet, self.kq_quet)

    def file_goc(self, td):
        """Ban goc cua file (ban sao luu neu da tung ghi Viet hoa)."""
        sl = os.path.join(self.sao_luu, td)
        p = os.path.join(self.thu_muc_game, td)
        rec = _doc_json(self.file_ghi, {}).get(td)
        if os.path.isfile(sl) and rec:
            try:
                if _md5(p) == rec.get("md5_viet"):   # file trong game van la ban app da ghi
                    return sl
                if _md5(p) != rec.get("md5_goc"):    # game da cap nhat -> file moi la ban goc
                    return p
            except OSError:
                pass
            return sl
        return p

    def doc_chon(self):
        self.chu = {}
        for td in self.chon:
            loai = DUOI_CHU.get(os.path.splitext(td)[1].lower())
            try:
                with open(self.file_goc(td), "rb") as f:
                    self.chu[td] = DANG[loai].doc(f.read())
            except Exception as e:
                self.chu[td] = []
                self.loi_doc = f"{td}: {e}"
        return self.chu

    # ---------------------------------------------------------- may dich dung chung
    def nen_dich(self, f, v, dot=None):
        return la_chu_anh(v)

    def _chuoi_cua_dot(self):
        for ds in self.chu.values():
            for _, v in ds:
                yield v

    def dich_cua(self, khong_dau):
        def dich(en):
            vi = self.bo_nho.get(en)
            if not vi or vi == en:
                return None
            if the_cua(en) != the_cua(vi):
                return None
            return bo_dau(vi) if khong_dau else vi
        return dich

    # ---------------------------------------------------------- ghi vao game / tra lai
    def ghi_vao_game(self, khong_dau=False, bao=lambda s: None):
        rec_all = _doc_json(self.file_ghi, {})
        dich = self.dich_cua(khong_dau)
        tong = 0
        for td in self.chon:
            p = os.path.join(self.thu_muc_game, td)
            loai = DUOI_CHU.get(os.path.splitext(td)[1].lower())
            nguon = self.file_goc(td)
            with open(nguon, "rb") as f:
                goc = f.read()
            sl = os.path.join(self.sao_luu, td)
            if nguon == p or not os.path.isfile(sl):
                os.makedirs(os.path.dirname(sl), exist_ok=True)
                shutil.copy2(p, sl)
            dem = [0]

            def dich_dem(en):
                vi = dich(en)
                if vi is not None:
                    dem[0] += 1
                return vi
            moi = DANG[loai].ghi(goc, dich_dem)
            DANG[loai].doc(moi)                    # kiem tra file moi doc lai duoc
            bao(f"Đang ghi {td} ({dem[0]} câu)...")
            tam = p + ".viethoa_tmp"
            with open(tam, "wb") as f:
                f.write(moi)
            os.replace(tam, p)
            rec_all[td] = {"md5_goc": hashlib.md5(goc).hexdigest(), "md5_viet": hashlib.md5(moi).hexdigest(),
                           "cau": dem[0], "luc": time.strftime("%d/%m/%Y %H:%M"), "khong_dau": khong_dau}
            tong += dem[0]
        _ghi_json(self.file_ghi, rec_all)
        return tong

    def da_ghi(self):
        return _doc_json(self.file_ghi, {})

    def tra_lai(self, bao=lambda s: None):
        rec_all = _doc_json(self.file_ghi, {})
        so = 0
        for td in list(rec_all):
            sl = os.path.join(self.sao_luu, td)
            p = os.path.join(self.thu_muc_game, td)
            if os.path.isfile(sl):
                shutil.copy2(sl, p)
                so += 1
            rec_all.pop(td)
        _ghi_json(self.file_ghi, rec_all)
        return so

    # ---------------------------------------------------------- tu dich bang Excel (CSV)
    def xuat_csv(self, duong_dan):
        with open(duong_dan, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["File", "Khóa", "Tiếng Anh", "Tiếng Việt"])
            da = set()
            n = 0
            for td, ds in self.chu.items():
                for k, v in ds:
                    if v in da:
                        continue
                    da.add(v)
                    w.writerow([td, k, v, self.bo_nho.get(v, "")])
                    n += 1
        return n

    def nap_csv(self, duong_dan):
        with open(duong_dan, "rb") as f:
            chu, _, _ = giai_ma(f.read())
        mau = chu[:5000]
        dl = "\t" if mau.count("\t") > max(mau.count(","), mau.count(";")) else (
            ";" if mau.count(";") > mau.count(",") else ",")
        hang = list(csv.reader(io.StringIO(chu, newline=""), delimiter=dl))
        if not hang:
            return 0
        dau = [c.strip().lower() for c in hang[0]]
        ca = next((i for i, c in enumerate(dau) if "anh" in c or "english" in c), 2)
        cv = next((i for i, c in enumerate(dau) if "việt" in c or "viet" in c or "vietnam" in c), 3)
        so = 0
        with self.khoa:
            for h in hang[1:]:
                if len(h) > max(ca, cv) and h[ca] and h[cv].strip():
                    self.bo_nho[h[ca]] = h[cv]
                    so += 1
        self.luu()
        return so


def _md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for k in iter(lambda: f.read(1 << 20), b""):
            h.update(k)
    return h.hexdigest()


def _doc_json(p, mac_dinh):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return mac_dinh


def _ghi_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tam, p)
