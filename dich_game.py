# -*- coding: utf-8 -*-
"""
DICH GAME - doc chu tieng Anh tren man hinh game va hien ban dich tieng Viet.
Windows 10/11.

  - Chup man hinh : Windows Graphics Capture -> DXGI -> GDI
  - Doc chu       : Windows OCR
  - Dich          : Claude (AI) - du phong Google Dich mien phi
  - Du lieu       : %APPDATA%\\DichGame (cau hinh, vung da chon, ma API, bo nho dich)
                    -> cap nhat / doi thu muc app khong mat cai dat

Phim tat mac dinh (doi duoc trong cau_hinh.json):
  F6 / F7   chon vung Hoi thoai / Nhiem vu
  F8        bat / tat tu dong dich
  F9        dich ngay (luu anh vung chup)
  F10       an / hien ban dich
  F11       chinh khung bang chuot
  F12       dich ca man hinh (lien tuc hoac 1 lan)
  Ctrl + mui ten / Ctrl+Shift + mui ten : dich khung Hoi thoai / Nhiem vu
  Ctrl+Shift+Q  thoat
"""

APP_VERSION = "6.0.0"
REPO_CAP_NHAT = "Zinit-mid/DichGame"  # kho GitHub chua ban phat hanh

import ctypes
import difflib
import http.client
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from ctypes import wintypes
from tkinter import messagebox

if sys.platform != "win32":
    print("App nay chi chay tren Windows.")
    sys.exit(1)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import keyboard
    import mss
    import numpy as np
    import winocr
    from PIL import Image, ImageTk
except ImportError as loi:
    _r = tk.Tk()
    _r.withdraw()
    messagebox.showerror(
        "Dịch Game",
        f"Thiếu thư viện: {loi.name}\n\nHãy bấm đúp file chay_thu.bat để tự cài rồi chạy lại.",
    )
    sys.exit(1)


# ================================================================ Thu muc & cau hinh

DONG_GOI = getattr(sys, "frozen", False)
THU_MUC_APP = os.path.dirname(sys.executable if DONG_GOI else os.path.abspath(__file__))
DU_LIEU = os.path.join(os.environ.get("APPDATA") or THU_MUC_APP, "DichGame")
os.makedirs(DU_LIEU, exist_ok=True)
# chuyen du lieu cua ban cu (nam canh app) sang thu muc du lieu chung
for _ten in ("cau_hinh.json", "ban_dich_da_luu.json", "tu_dien.json", "khoa_api.txt"):
    _cu, _moi = os.path.join(THU_MUC_APP, _ten), os.path.join(DU_LIEU, _ten)
    if os.path.exists(_cu) and not os.path.exists(_moi):
        try:
            shutil.copy2(_cu, _moi)
        except Exception:
            pass

FILE_CAU_HINH = os.path.join(DU_LIEU, "cau_hinh.json")
FILE_BO_NHO = os.path.join(DU_LIEU, "ban_dich_da_luu.json")
FILE_TU_DIEN = os.path.join(DU_LIEU, "tu_dien.json")
FILE_KHOA = os.path.join(DU_LIEU, "khoa_api.txt")

VUNG = {"hoi_thoai": "Hội thoại", "nhiem_vu": "Nhiệm vụ"}
PHIEN_BAN_CAU_HINH = 6
TY_GIA = 26000

TUY_VUNG = {
    # an_trong: an khung sau N vong khong thay chu | an_lech: an sau N vong chu khac han
    # bo_qua: giong cau dang hien tu muc nay -> khong dich lai | lech: duoi muc nay coi la doi chu
    # moi: xu ly vung moi N vong (nhiem vu it doi nen kiem tra thua hon)
    "hoi_thoai": {"an_trong": 2, "an_lech": 4, "bo_qua": 0.92, "lech": 0.8, "moi": 1},
    "nhiem_vu": {"an_trong": 12, "an_lech": 12, "bo_qua": 0.85, "lech": 0.7, "moi": 4},
}

CAU_HINH_MAC_DINH = {
    "phien_ban": PHIEN_BAN_CAU_HINH,
    "vung": {"hoi_thoai": None, "nhiem_vu": None},
    "khung_dich": {"hoi_thoai": None, "nhiem_vu": None},
    "co_chu": {"hoi_thoai": 18, "nhiem_vu": 15},
    "loc_chu_trang": {"hoi_thoai": True, "nhiem_vu": False},
    "nguong_chu_trang": 185,
    "kieu_hien": "phu_de",
    "vien_chu": 2,
    "do_dam_chu": 1.0,
    "do_mo": 0.85,
    "bo_dich": "claude",
    "mo_hinh": "claude-haiku-5-5",
    "gia_usd_moi_trieu_token": [0.10, 0.50],
    "da_dung_usd": 0.0,
    "hien_google_truoc": True,
    "chu_ky_giay": 0.25,
    "tu_dong_dich": True,
    "cach_chup": "tu_dong",
    "toan_man_lien_tuc": True,
    "chu_ky_toan_man_giay": 1.5,
    "github_repo": "",
    "url_cap_nhat": "",
    "tu_kiem_tra_cap_nhat": True,
    "phim_tat": {
        "chon_hoi_thoai": "f6",
        "chon_nhiem_vu": "f7",
        "bat_tat_tu_dong": "f8",
        "dich_ngay": "f9",
        "an_hien": "f10",
        "chinh_khung": "f11",
        "dich_man_hinh": "f12",
        "hoi_thoai_len": "ctrl+up",
        "hoi_thoai_xuong": "ctrl+down",
        "hoi_thoai_trai": "ctrl+left",
        "hoi_thoai_phai": "ctrl+right",
        "nhiem_vu_len": "ctrl+shift+up",
        "nhiem_vu_xuong": "ctrl+shift+down",
        "nhiem_vu_trai": "ctrl+shift+left",
        "nhiem_vu_phai": "ctrl+shift+right",
        "thoat": "ctrl+shift+q",
    },
}

TU_DIEN_MAU = {
    "_huong_dan": (
        "ten_rieng: tên riêng giữ nguyên tiếng Anh khi dịch (thêm tùy ý). "
        "sua_ban_dich: bên trái là chữ dịch sai, bên phải là chữ bạn muốn. Lưu file rồi mở lại app."
    ),
    "ten_rieng": ["Kliff", "Greymane", "Greymanes", "Pywel", "Hernand", "Hernandian"],
    "sua_ban_dich": {},
}

# ---- mau giao dien
MAU_TRONG = "#010101"
MAU_NEN = "#101014"
MAU_CHU = "#FFFFFF"
MAU_VIEN = "#000000"
UI_NEN = "#15161b"
UI_THE = "#1e2027"
UI_O = "#2a2d36"
UI_O_HOVER = "#363a46"
UI_CHU = "#e9e9ec"
UI_PHU = "#9299a6"
UI_DO = "#c8413a"
UI_DO_HOVER = "#dc5248"
UI_VANG = "#f0b54a"
UI_XANH = "#3ecf8e"
UI_LOI = "#ff6b6b"
FONT = ("Segoe UI", 10)
FONT_DAM = ("Segoe UI", 10, "bold")


def doc_json(duong_dan, mac_dinh):
    try:
        with open(duong_dan, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return mac_dinh


def ghi_json(duong_dan, du_lieu):
    tam = duong_dan + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)
    os.replace(tam, duong_dan)


def tron(mac_dinh, nguoi_dung):
    kq = dict(mac_dinh)
    if isinstance(nguoi_dung, dict):
        for k, v in nguoi_dung.items():
            if isinstance(v, dict) and isinstance(kq.get(k), dict):
                kq[k] = tron(kq[k], v)
            else:
                kq[k] = v
    return kq


def nang_cap_cau_hinh(cfg):
    if isinstance(cfg.get("co_chu"), (int, float)):
        cfg["co_chu"] = {k: int(cfg["co_chu"]) + (2 if k == "hoi_thoai" else 0) for k in VUNG}
    if cfg.get("phien_ban", 1) < 4:
        cfg["chu_ky_giay"] = 0.25
        cfg["do_mo"] = 0.85
        lech = cfg.get("lech_doc", {}) or {}
        for k in VUNG:
            v = cfg["vung"].get(k)
            if v and not cfg["khung_dich"].get(k):
                cfg["khung_dich"][k] = [v[0], v[1] + int(lech.get(k, 0)), v[2]]
    for cu in ("lech_doc", "vi_tri_ban_dich", "so_lan_on_dinh"):
        cfg.pop(cu, None)
    cfg["phien_ban"] = PHIEN_BAN_CAU_HINH
    return cfg


def so_phien_ban(s):
    return tuple(int(x) for x in re.findall(r"\d+", str(s))[:4]) or (0,)


# ================================================================ Ham Windows

user32 = ctypes.windll.user32
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
user32.SetWindowDisplayAffinity.restype = wintypes.BOOL

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x11


def hwnd_cua(win):
    win.update_idletasks()
    return user32.GetParent(win.winfo_id()) or win.winfo_id()


def dat_xuyen_chuot(win, xuyen):
    h = hwnd_cua(win)
    kieu = user32.GetWindowLongW(h, GWL_EXSTYLE) | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    kieu = kieu | WS_EX_TRANSPARENT if xuyen else kieu & ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(h, GWL_EXSTYLE, kieu)


def an_khoi_anh_chup(win):
    try:
        return bool(user32.SetWindowDisplayAffinity(hwnd_cua(win), WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def ve_chu_vien(cv, x, y, chu, font, rong, neo, can, day):
    if day > 0:
        for dx in range(-day, day + 1):
            for dy in range(-day, day + 1):
                if (dx or dy) and dx * dx + dy * dy <= day * day + 1:
                    cv.create_text(x + dx, y + dy, text=chu, font=font, fill=MAU_VIEN,
                                   width=rong, anchor=neo, justify=can)
    return cv.create_text(x, y, text=chu, font=font, fill=MAU_CHU, width=rong, anchor=neo, justify=can)


# ================================================================ Chup man hinh

def man_hinh_chinh():
    with mss.mss() as s:
        m = s.monitors[1] if len(s.monitors) > 1 else s.monitors[0]
        return dict(m)


class ChupWGC:
    """Windows Graphics Capture (thu vien windows-capture)."""

    def __init__(self):
        from windows_capture import WindowsCapture
        self.khoa = threading.Lock()
        self.can = threading.Event()
        self.co = threading.Event()
        self.khung = None
        self.dung = False
        cap = None
        self.co_vien = True
        for kw in (
            dict(cursor_capture=False, draw_border=False),
            dict(capture_cursor=False, draw_border=False),
            dict(draw_border=False),
            dict(cursor_capture=False, draw_border=False, monitor_index=None, window_name=None),
            dict(capture_cursor=False, draw_border=False, monitor_index=None, window_name=None),
            dict(cursor_capture=None, draw_border=None, monitor_index=None, window_name=None),
            dict(),
        ):
            try:
                cap = WindowsCapture(**kw)
                self.co_vien = kw.get("draw_border") is not False
                break
            except Exception:
                continue
        if cap is None:
            raise RuntimeError("không khởi tạo được windows-capture")

        @cap.event
        def on_frame_arrived(frame, capture_control):
            if self.dung:
                capture_control.stop()
                return
            if self.khung is not None and not self.can.is_set():
                return
            buf = getattr(frame, "frame_buffer", None)
            if buf is None:
                return
            with self.khoa:
                self.khung = np.array(buf, copy=True)
            self.can.clear()
            self.co.set()

        @cap.event
        def on_closed():
            pass

        self.ten = "Windows Graphics Capture" + (" – có viền vàng" if self.co_vien else "")
        if hasattr(cap, "start_free_threaded"):
            self.dieu_khien = cap.start_free_threaded()
        else:
            threading.Thread(target=cap.start, daemon=True).start()
        if not self.co.wait(4):
            self.dung = True
            raise RuntimeError("không nhận được hình từ Windows Graphics Capture")

    def lam_moi(self):
        self.co.clear()
        self.can.set()
        self.co.wait(0.3)

    def cat(self, x, y, w, h):
        with self.khoa:
            f = self.khung
        if f is None or x < 0 or y < 0 or y + h > f.shape[0] or x + w > f.shape[1]:
            return None
        return Image.fromarray(np.ascontiguousarray(f[y:y + h, x:x + w, 2::-1]))

    def dong(self):
        self.dung = True


class ChupDXGI:
    def __init__(self, man):
        mod = None
        for ten in ("bettercam", "dxcam"):
            try:
                mod = __import__(ten)
                self.ten = f"DXGI ({ten})"
                break
            except Exception:
                continue
        if mod is None:
            raise RuntimeError("chưa cài bettercam/dxcam")
        self.cam = None
        for d in range(3):
            for o in range(4):
                try:
                    cam = mod.create(device_idx=d, output_idx=o, output_color="RGB")
                except Exception:
                    continue
                if (getattr(cam, "width", 0), getattr(cam, "height", 0)) == (man["width"], man["height"]):
                    self.cam = cam
                    break
            if self.cam:
                break
        if self.cam is None:
            raise RuntimeError("không tìm thấy màn hình khớp độ phân giải")
        self.khung = None

    def lam_moi(self):
        for _ in range(3):
            try:
                f = self.cam.grab()
            except Exception:
                f = None
            if f is not None:
                self.khung = f
                return
            if self.khung is not None:
                return
            time.sleep(0.05)

    def cat(self, x, y, w, h):
        f = self.khung
        if f is None or x < 0 or y < 0 or y + h > f.shape[0] or x + w > f.shape[1]:
            return None
        return Image.fromarray(np.ascontiguousarray(f[y:y + h, x:x + w]))

    def dong(self):
        pass


class BoChup:
    def __init__(self, cach="tu_dong"):
        self.man = man_hinh_chinh()
        self.mss = mss.mss()
        self.nguon = None
        self.ten = "GDI (cách cũ)"
        self.ghi_chu = []
        cac_cach = {"tu_dong": (ChupWGC, lambda: ChupDXGI(self.man)),
                    "wgc": (ChupWGC,),
                    "dxgi": (lambda: ChupDXGI(self.man),),
                    "gdi": ()}.get(cach, (ChupWGC, lambda: ChupDXGI(self.man)))
        for tao in cac_cach:
            try:
                self.nguon = tao()
                self.ten = self.nguon.ten
                break
            except Exception as e:
                self.ghi_chu.append(str(e))

    def lam_moi(self):
        if self.nguon:
            self.nguon.lam_moi()

    def cat(self, vung):
        x, y, w, h = [int(v) for v in vung]
        if self.nguon:
            anh = self.nguon.cat(x - self.man["left"], y - self.man["top"], w, h)
            if anh is not None:
                return anh
        chup = self.mss.grab({"left": x, "top": y, "width": w, "height": h})
        return Image.frombytes("RGB", chup.size, chup.bgra, "raw", "BGRX")

    def toan_man(self):
        m = self.man
        return self.cat([m["left"], m["top"], m["width"], m["height"]])

    def dong(self):
        if self.nguon:
            self.nguon.dong()


# ================================================================ Doc chu (OCR)

CANH_TOI_DA = 2500


def _lay(o, k):
    return o.get(k) if isinstance(o, dict) else getattr(o, k, None)


def ocr_tho(anh):
    anh = anh.convert("RGB")
    w, h = anh.size
    he_so = min(2.0, CANH_TOI_DA / max(w, h))
    if abs(he_so - 1) > 0.05:
        anh = anh.resize((max(1, int(w * he_so)), max(1, int(h * he_so))), Image.LANCZOS)
    else:
        he_so = 1.0
    kq = winocr.recognize_pil_sync(anh, "en")
    dong = _lay(kq, "lines") or []
    ra = []
    for d in dong:
        chu = str(_lay(d, "text") or "")
        hop = None
        cac_o = [_lay(t, "bounding_rect") for t in (_lay(d, "words") or [])]
        cac_o = [o for o in cac_o if o is not None]
        if cac_o:
            x0 = min(_lay(o, "x") for o in cac_o)
            y0 = min(_lay(o, "y") for o in cac_o)
            x1 = max(_lay(o, "x") + _lay(o, "width") for o in cac_o)
            y1 = max(_lay(o, "y") + _lay(o, "height") for o in cac_o)
            hop = (x0 / he_so, y0 / he_so, (x1 - x0) / he_so, (y1 - y0) / he_so)
        ra.append((chu, hop))
    if not dong:
        ra = [(t, None) for t in str(_lay(kq, "text") or "").splitlines()]
    return ra


def doc_chu(anh):
    return [t for t, _ in ocr_tho(anh)]


def loc_chu_trang(anh, nguong):
    return anh.convert("L").point(lambda p: 0 if p >= nguong else 255)


def dong_hop_le(d):
    tu = re.findall(r"[A-Za-z']+", d)
    so_chu_cai = sum(len(t) for t in tu)
    if so_chu_cai < 3 or not any(len(t) >= 3 for t in tu):
        return False
    return so_chu_cai / max(1, len(d.replace(" ", ""))) >= 0.6


def lam_sach(cac_dong):
    kq = []
    for d in cac_dong:
        d = re.sub(r"\s+", " ", d).strip()
        if not dong_hop_le(d):
            continue
        if kq and d[:1].islower() and not re.search(r"[.!?:;\"”’)\]…]$", kq[-1]):
            kq[-1] += " " + d
        else:
            kq.append(d)
    return "\n".join(kq)


def dau_van_tay(anh):
    return anh.convert("L").resize((96, 24)).tobytes()


def anh_giong(a, b, nguong=3.0):
    if a is None or b is None or len(a) != len(b):
        return False
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) < nguong


def chu_giong(a, b, ty_le):
    if a == b:
        return True
    if not a or not b:
        return False
    sm = difflib.SequenceMatcher(None, a, b)
    return sm.real_quick_ratio() >= ty_le and sm.quick_ratio() >= ty_le and sm.ratio() >= ty_le


def bo_dau(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


CHU_VIET = set("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ")


def la_tieng_viet(s):
    s = s.lower()
    n = sum(c in CHU_VIET for c in s)
    so_chu = sum(c.isalpha() for c in s)
    return n >= 2 or (so_chu > 0 and n / so_chu > 0.05)


def so_hoa(s):
    return re.sub(r"\d+", "#", s)


def thay_so(ban_dich, so_cu, so_moi):
    if so_cu == so_moi:
        return ban_dich
    if len(so_cu) != len(so_moi) or re.findall(r"\d+", ban_dich) != so_cu:
        return None
    lap = iter(so_moi)
    return re.sub(r"\d+", lambda m: next(lap), ban_dich)


def het_cau(s):
    return bool(re.search(r"[.!?…\"”’]\s*$", s.strip()))


def ocr_toan_man(anh):
    W, H = anh.size
    o, o_rong = 200, 2400
    bat_dau = [0]
    while bat_dau[-1] + o_rong < W:
        bat_dau.append(bat_dau[-1] + o_rong - o)
    ket_qua = []
    for s in bat_dau:
        e = min(W, s + o_rong)
        lo = s + (o / 2 if s > 0 else 0)
        hi = e - (o / 2 if e < W else 0)
        for chu, hop in ocr_tho(anh.crop((s, 0, e, H))):
            if not hop:
                continue
            x, y, w, h = hop
            if lo <= s + x + w / 2 <= hi:
                ket_qua.append((chu, (s + x, y, w, h)))
    return ket_qua


def gom_doan(cac_dong):
    cac_dong = [(t, b) for t, b in cac_dong if dong_hop_le(t)]
    cac_dong.sort(key=lambda d: (d[1][1], d[1][0]))
    doan = []
    for chu, (x, y, w, h) in cac_dong:
        for d in reversed(doan):
            khoang = y - d["y1"]
            if (-0.3 * h <= khoang <= 0.8 * d["h"] and abs(h - d["h"]) <= 0.45 * d["h"]
                    and x < d["x1"] and x + w > d["x0"] and abs(x - d["x0"]) < 6 * d["h"]):
                d["dong"].append(chu)
                d["x0"], d["x1"] = min(d["x0"], x), max(d["x1"], x + w)
                d["y1"] = y + h
                break
        else:
            doan.append({"dong": [chu], "x0": x, "y0": y, "x1": x + w, "y1": y + h, "h": h})
    ra = []
    for d in doan:
        chu = lam_sach(d["dong"])
        if chu:
            ra.append((chu, (int(d["x0"]), int(d["y0"]), int(d["x1"] - d["x0"]), int(d["y1"] - d["y0"])), d["h"]))
    return ra[:80]


def giao_nhau(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


# ================================================================ Dich

def google_dich(van_ban):
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "vi", "dt": "t", "q": van_ban[:1800]}
    )
    yeu_cau = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(yeu_cau, timeout=8) as r:
        du_lieu = json.loads(r.read().decode("utf-8"))
    return "".join(doan[0] for doan in du_lieu[0] if doan and doan[0])


HUONG_DAN_AI = """Bạn là dịch giả chuyên Việt hóa game. Game đang chơi: Crimson Desert (nhập vai thế giới mở, \
bối cảnh trung cổ kỳ ảo; nhân vật chính là Kliff, thủ lĩnh nhóm lính đánh thuê Greymane).
Bạn nhận văn bản tiếng Anh do máy đọc chữ (OCR) chụp từ màn hình game và dịch sang tiếng Việt.

Quy tắc:
- CHỈ trả về bản dịch tiếng Việt. Không giải thích, không ghi chú, không thêm ngoặc kép.
- Văn phong tự nhiên như phụ đề phim kỳ ảo/cổ trang. Chọn xưng hô hợp ngữ cảnh \
(ta – ngươi, ta – các ngươi, tôi – ngài, anh – em...), giữ nhất quán với các câu trước.
- Giữ nguyên tiếng Anh cho tên riêng: tên người, địa danh, phe phái, tên vật phẩm đặc biệt.
- Văn bản có thể bị OCR đọc sai (sai chữ, thiếu dấu câu, ký tự rác): tự sửa theo ngữ cảnh rồi dịch, bỏ ký tự rác.
- Giữ cách xuống dòng. Dòng dạng "Tên: lời thoại" thì giữ tên, dịch lời thoại.
- Với chữ nhiệm vụ / menu / nút bấm: dịch ngắn gọn, rõ nghĩa như trong game Việt hóa.
- Giữ nguyên các con số.
- Nếu không có gì để dịch, trả về đúng chuỗi rỗng."""


class LoiClaude(Exception):
    pass


class ClaudeDich:
    """Goi Claude; giu ket noi HTTPS mo san (moi luong 1 ket noi) de do mat thoi gian bat tay."""
    MAY_CHU = "api.anthropic.com"

    def __init__(self):
        self.kieu_xac_thuc = None
        self._rieng = threading.local()

    def _ket_noi(self, moi=False):
        c = getattr(self._rieng, "c", None)
        if moi and c is not None:
            try:
                c.close()
            except Exception:
                pass
            c = None
        if c is None:
            c = http.client.HTTPSConnection(self.MAY_CHU, timeout=20)
            self._rieng.c = c
        return c

    def lam_nong(self):
        try:
            self._ket_noi().connect()
        except Exception:
            pass

    def _gui(self, khoa, body, kieu):
        dau = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
        if kieu == "bearer":
            dau["authorization"] = "Bearer " + khoa
        else:
            dau["x-api-key"] = khoa
        du_lieu = json.dumps(body).encode("utf-8")
        for lan in range(2):
            c = self._ket_noi(moi=lan > 0)
            try:
                c.request("POST", "/v1/messages", body=du_lieu, headers=dau)
                return c.getresponse()
            except (http.client.HTTPException, OSError):
                if lan:
                    raise

    def goi(self, khoa, mo_hinh, noi_dung, max_tokens=800, goi_lai=None):
        body = {"model": mo_hinh, "max_tokens": max_tokens, "stream": True,
                "system": HUONG_DAN_AI, "messages": [{"role": "user", "content": noi_dung}]}
        cac_kieu = [self.kieu_xac_thuc] if self.kieu_xac_thuc else ["x-api-key", "bearer"]
        loi, r = None, None
        for kieu in cac_kieu:
            r = self._gui(khoa, body, kieu)
            if r.status < 400:
                self.kieu_xac_thuc = kieu
                break
            noi = r.read().decode("utf-8", "ignore")
            try:
                tb = json.loads(noi)["error"]["message"]
            except Exception:
                tb = noi[:150]
            loi = LoiClaude(f"HTTP {r.status}: {tb}")
            r = None
            if loi and ("HTTP 401" not in str(loi) and "HTTP 403" not in str(loi)):
                raise loi
        if r is None:
            raise loi or LoiClaude("Không kết nối được Claude")

        doan, vao, ra = [], 0, 0
        while True:
            dong = r.readline()
            if not dong:
                break
            dong = dong.decode("utf-8", "ignore").strip()
            if not dong.startswith("data:"):
                continue
            try:
                sk = json.loads(dong[5:].strip())
            except Exception:
                continue
            loai = sk.get("type")
            if loai == "message_start":
                vao = sk.get("message", {}).get("usage", {}).get("input_tokens", 0)
            elif loai == "content_block_delta":
                chu = sk.get("delta", {}).get("text", "")
                if chu:
                    doan.append(chu)
                    if goi_lai:
                        goi_lai("".join(doan))
            elif loai == "message_delta":
                ra = sk.get("usage", {}).get("output_tokens", ra)
            elif loai == "error":
                raise LoiClaude(sk.get("error", {}).get("message", "lỗi không rõ"))
        return "".join(doan).strip(), vao, ra

    def dich(self, khoa, mo_hinh, van_ban, loai, lich_su, ten_rieng, goi_lai=None):
        phan = [f"Loại chữ: {'lời thoại / phụ đề' if loai == 'hoi_thoai' else 'nhiệm vụ / mục tiêu'}"]
        if ten_rieng:
            phan.append("Tên riêng giữ nguyên: " + ", ".join(ten_rieng))
        if lich_su:
            phan.append("Các câu ngay trước (để hiểu ngữ cảnh, KHÔNG dịch lại):\n" +
                        "\n".join(f"- {en} => {vi}" for en, vi in lich_su))
        phan.append("Dịch đoạn sau:\n<<<\n" + van_ban + "\n>>>")
        return self.goi(khoa, mo_hinh, "\n\n".join(phan), 800, goi_lai)

    def dich_nhieu(self, khoa, mo_hinh, cac_doan, ten_rieng):
        phan = ["Đây là các đoạn chữ rời rạc chụp từ màn hình game (menu, bảng thông tin, mô tả, nút bấm, "
                "tên nhân vật...). Dịch TỪNG đoạn. Mỗi bản dịch bắt đầu bằng đúng số thứ tự dạng [số] như "
                "đầu vào. Không gộp, không bỏ đoạn nào. Tên riêng đứng một mình thì giữ nguyên."]
        if ten_rieng:
            phan.append("Tên riêng giữ nguyên: " + ", ".join(ten_rieng))
        phan.append("\n".join(f"[{i + 1}] {d}" for i, d in enumerate(cac_doan)))
        chu, vao, ra = self.goi(khoa, mo_hinh, "\n\n".join(phan), 4000)
        ket_qua = {}
        manh = re.split(r"^\s*\[(\d+)\]\s?", chu, flags=re.M)
        for i in range(1, len(manh) - 1, 2):
            ket_qua[int(manh[i]) - 1] = manh[i + 1].strip()
        return ket_qua, vao, ra


class BoDich:
    def __init__(self, cfg):
        self.cfg = cfg
        self.claude = ClaudeDich()
        self.bo_nho = doc_json(FILE_BO_NHO, {})
        if not isinstance(self.bo_nho, dict):
            self.bo_nho = {}
        self.gan_day = [k for k in self.bo_nho if "#|" in k][-400:]
        tu_dien = doc_json(FILE_TU_DIEN, None)
        if not isinstance(tu_dien, dict):
            tu_dien = dict(TU_DIEN_MAU)
        if "ten_rieng" not in tu_dien:
            tu_dien["ten_rieng"] = TU_DIEN_MAU["ten_rieng"]
            tu_dien["_huong_dan"] = TU_DIEN_MAU["_huong_dan"]
        try:
            ghi_json(FILE_TU_DIEN, tu_dien)
        except Exception:
            pass
        self.ten_rieng = [str(t) for t in tu_dien.get("ten_rieng", [])]
        self.sua = tu_dien.get("sua_ban_dich", {}) or {}
        self.lich_su = {k: [] for k in VUNG}
        self.khoa_api = self._doc_khoa()
        self.khoa_hong = False
        self.khoa = threading.Lock()
        self.co_moi = False

    def _doc_khoa(self):
        try:
            with open(FILE_KHOA, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return os.environ.get("ANTHROPIC_API_KEY", "").strip()

    def luu_khoa(self, khoa):
        khoa = khoa.strip()
        with open(FILE_KHOA, "w", encoding="utf-8") as f:
            f.write(khoa)
        self.khoa_api = khoa
        self.khoa_hong = False
        self.claude.kieu_xac_thuc = None

    def dung_claude(self):
        return self.cfg["bo_dich"] == "claude" and bool(self.khoa_api) and not self.khoa_hong

    def _sua(self, s):
        for sai, dung in self.sua.items():
            s = s.replace(sai, dung)
        return s

    def _tim(self, may, van_ban):
        so_moi = re.findall(r"\d+", van_ban)
        mau = so_hoa(van_ban)
        with self.khoa:
            cu = self.bo_nho.get(f"{may}|{van_ban}")
            if isinstance(cu, str):
                return cu
            ung_vien = [f"{may}#|{mau}"] + [k for k in reversed(self.gan_day) if k.startswith(may + "#|")]
            for i, k in enumerate(ung_vien):
                e = self.bo_nho.get(k)
                if not isinstance(e, dict):
                    continue
                if i > 0 and not chu_giong(k[len(may) + 2:], mau, 0.93):
                    continue
                kq = thay_so(e["vi"], re.findall(r"\d+", e["src"]), so_moi)
                if kq is not None:
                    return kq
        return None

    def tim(self, van_ban):
        kq = self._tim("claude" if self.dung_claude() else "google", van_ban)
        return None if kq is None else self._sua(kq)

    def _luu(self, may, van_ban, vi):
        k = f"{may}#|{so_hoa(van_ban)}"
        with self.khoa:
            self.bo_nho[k] = {"src": van_ban, "vi": vi}
            self.gan_day = (self.gan_day + [k])[-400:]
            self.co_moi = True

    def tien(self, vao, ra):
        gia_vao, gia_ra = self.cfg["gia_usd_moi_trieu_token"]
        return vao * gia_vao / 1e6 + ra * gia_ra / 1e6

    def _loi_claude(self, e):
        if "HTTP 401" in str(e) or "HTTP 403" in str(e):
            self.khoa_hong = True
        return f"Claude lỗi ({e}) – tạm dùng Google"

    def dich(self, van_ban, loai, goi_lai=None):
        """Tra ve (ban_dich, nguon, tien_usd, loi)."""
        may = "claude" if self.dung_claude() else "google"
        cu = self._tim(may, van_ban)
        if cu is not None:
            return self._sua(cu), "đã lưu", 0.0, None
        tien, loi = 0.0, None
        if may == "claude":
            try:
                kq, vao, ra = self.claude.dich(self.khoa_api, self.cfg["mo_hinh"], van_ban, loai,
                                               self.lich_su[loai][-4:], self.ten_rieng, goi_lai)
                tien = self.tien(vao, ra)
            except Exception as e:
                loi = self._loi_claude(e)
                may, kq = "google", google_dich(van_ban)
        else:
            kq = google_dich(van_ban)
        self._luu(may, van_ban, kq)
        with self.khoa:
            self.lich_su[loai] = (self.lich_su[loai] + [(van_ban, kq)])[-4:]
        return self._sua(kq), ("Claude" if may == "claude" else "Google"), tien, loi

    def dich_nhieu(self, cac_doan):
        may = "claude" if self.dung_claude() else "google"
        ket_qua = [self._tim(may, d) for d in cac_doan]
        thieu = [i for i, r in enumerate(ket_qua) if r is None]
        tien, loi = 0.0, None
        if thieu and may == "claude":
            try:
                kq, vao, ra = self.claude.dich_nhieu(self.khoa_api, self.cfg["mo_hinh"],
                                                     [cac_doan[i] for i in thieu], self.ten_rieng)
                tien = self.tien(vao, ra)
                for j, i in enumerate(thieu):
                    if kq.get(j):
                        ket_qua[i] = kq[j]
                        self._luu("claude", cac_doan[i], kq[j])
            except Exception as e:
                loi = self._loi_claude(e)
        for i, r in enumerate(ket_qua):
            if r is None:
                try:
                    ket_qua[i] = google_dich(cac_doan[i])
                    self._luu("google", cac_doan[i], ket_qua[i])
                except Exception:
                    ket_qua[i] = cac_doan[i]
        return [self._sua(r) for r in ket_qua], tien, loi

    def luu(self):
        with self.khoa:
            if not self.co_moi:
                return
            self.bo_nho = dict(list(self.bo_nho.items())[-30000:])
            ban_sao = dict(self.bo_nho)
            self.co_moi = False
        try:
            ghi_json(FILE_BO_NHO, ban_sao)
        except Exception:
            pass


# ================================================================ Cap nhat

def _tai_json(url):
    yc = urllib.request.Request(url, headers={"User-Agent": "DichGame-capnhat",
                                              "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(yc, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def lay_thong_tin_ban_moi(cfg):
    repo = (cfg.get("github_repo") or REPO_CAP_NHAT).strip().strip("/")
    url = (cfg.get("url_cap_nhat") or "").strip()
    if repo:
        d = _tai_json(f"https://api.github.com/repos/{repo}/releases/latest")
        tep = {a.get("name"): a.get("browser_download_url") for a in d.get("assets", [])}
        return {"phien_ban": str(d.get("tag_name", "")).lstrip("vV"), "ghi_chu": d.get("body") or "",
                "exe": tep.get("DichGame.exe"), "zip": tep.get("DichGame.zip")}
    if url:
        return _tai_json(url)
    raise RuntimeError("chưa cài nguồn cập nhật (github_repo trong cau_hinh.json)")


def tai_tep(url, duong_dan, bao=None):
    yc = urllib.request.Request(url, headers={"User-Agent": "DichGame-capnhat"})
    with urllib.request.urlopen(yc, timeout=30) as r, open(duong_dan, "wb") as f:
        tong = int(r.headers.get("Content-Length") or 0)
        da = 0
        while True:
            khuc = r.read(256 * 1024)
            if not khuc:
                break
            f.write(khuc)
            da += len(khuc)
            if bao and tong:
                bao(f"Đang tải bản mới... {da * 100 // tong}%")


def ap_dung_cap_nhat(thong_tin, bao):
    """Tai va thay ban moi. Tra ve True neu app can tat de hoan tat."""
    if DONG_GOI:
        url = thong_tin.get("exe")
        if not url:
            raise RuntimeError("bản phát hành không có file DichGame.exe")
        moi = os.path.join(DU_LIEU, "DichGame_moi.exe")
        tai_tep(url, moi, bao)
        hien = sys.executable
        bat = os.path.join(DU_LIEU, "cap_nhat.bat")
        with open(bat, "w", encoding="utf-8") as f:
            f.write("@echo off\r\nchcp 65001 >nul\r\nping 127.0.0.1 -n 3 >nul\r\n:lap\r\n"
                    f'move /y "{moi}" "{hien}" >nul 2>nul\r\n'
                    "if errorlevel 1 (ping 127.0.0.1 -n 2 >nul & goto lap)\r\n"
                    f'start "" "{hien}"\r\ndel "%~f0"\r\n')
        subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000, close_fds=True)
        return True
    url = thong_tin.get("zip")
    if not url:
        raise RuntimeError("bản phát hành không có file DichGame.zip")
    tam = os.path.join(tempfile.gettempdir(), "DichGame_moi.zip")
    tai_tep(url, tam, bao)
    with zipfile.ZipFile(tam) as z:
        for ten in z.namelist():
            goc = os.path.basename(ten)
            if goc and goc.lower().endswith((".py", ".bat", ".txt", ".ico")):
                with z.open(ten) as nguon, open(os.path.join(THU_MUC_APP, goc), "wb") as dich:
                    shutil.copyfileobj(nguon, dich)
    subprocess.Popen([sys.executable, os.path.join(THU_MUC_APP, "dich_game.py")], cwd=THU_MUC_APP)
    return True


# ================================================================ Khung hien ban dich

class KhungBanDich:
    LE = 10

    def __init__(self, root, khoa, khi_doi):
        self.khoa = khoa
        self.khi_doi = khi_doi
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=MAU_TRONG)
        self.cv = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=MAU_TRONG)
        self.cv.pack(fill="both", expand=True)
        self.da_cai_dat = False
        self.khong_bi_chup = False
        self.dang_hien = False
        self.dang_chinh = False
        self.x, self.y, self.w, self.h = 100, 100, 600, 60
        self.co_chu = 18
        self.van_ban = ""
        self.kieu = "phu_de"
        self.vien = 2
        self._keo = None
        self._ve_cuoi = None
        self.cv.bind("<ButtonPress-1>", self._nhan)
        self.cv.bind("<B1-Motion>", self._di)
        self.cv.bind("<ButtonRelease-1>", self._tha)
        self.cv.bind("<MouseWheel>", self._lan)

    def _ve(self):
        cv, le = self.cv, self.LE
        cv.delete("all")
        giua = self.khoa == "hoi_thoai"
        font = ("Segoe UI", self.co_chu, "bold")
        rong_chu = max(60, self.w - 2 * le)
        x0, neo, can = (self.w // 2, "n", "center") if giua else (le, "nw", "left")
        chu = self.van_ban
        if self.dang_chinh and not chu:
            chu = f"[{VUNG[self.khoa]}] Kéo để di chuyển • kéo góc ◢ đổi độ rộng • lăn chuột đổi cỡ chữ"
        if self.dang_chinh:
            nen = "#2b2b33"
        elif self.kieu == "phu_de":
            nen = MAU_TRONG
        else:
            nen = MAU_NEN
        cv.configure(bg=nen)
        day = self.vien + (1 if self.co_chu >= 26 and self.vien else 0) if nen == MAU_TRONG else 0
        ve_chu_vien(cv, x0, le, chu, font, rong_chu, neo, can, day)
        hop = cv.bbox("all") or (0, 0, 0, 30)
        self.h = max(30, hop[3] + le)
        if self.dang_chinh:
            cv.create_rectangle(1, 1, self.w - 2, self.h - 2, outline="#ffcc33", width=2, dash=(6, 4))
            cv.create_polygon(self.w - 2, self.h - 22, self.w - 2, self.h - 2, self.w - 22, self.h - 2,
                              fill="#ffcc33", outline="")
        self.win.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")

    def _cai_dat_lan_dau(self):
        self.win.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.win.deiconify()
        self.win.update_idletasks()
        self.win.attributes("-transparentcolor", MAU_TRONG)
        dat_xuyen_chuot(self.win, not self.dang_chinh)
        self.khong_bi_chup = an_khoi_anh_chup(self.win)
        self.da_cai_dat = True

    def hien(self, van_ban, x, y, w, co_chu, kieu, do_dam, vien):
        trang_thai = (van_ban, int(x), int(y), int(w), int(co_chu), kieu, do_dam, int(vien), self.dang_chinh)
        if trang_thai == self._ve_cuoi and self.dang_hien:
            return  # khong doi gi -> khoi ve lai
        self._ve_cuoi = trang_thai
        self.van_ban, self.x, self.y, self.w = van_ban, int(x), int(y), int(w)
        self.co_chu, self.kieu, self.vien = int(co_chu), kieu, int(vien)
        if not self.da_cai_dat:
            self._cai_dat_lan_dau()
        self.win.attributes("-alpha", 0.95 if self.dang_chinh else do_dam)
        self._ve()
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.dang_hien = True

    def an(self):
        if self.dang_hien:
            self.win.withdraw()
        self.dang_hien = False
        self._ve_cuoi = None

    def che_do_chinh(self, bat):
        self.dang_chinh = bat
        self._ve_cuoi = None
        if self.da_cai_dat:
            dat_xuyen_chuot(self.win, not bat)

    def giu_tren_cung(self):
        if self.dang_hien:
            self.win.attributes("-topmost", True)
            self.win.lift()

    def _nhan(self, e):
        if not self.dang_chinh:
            return
        doi_rong = e.x >= self.w - 30 and e.y >= self.h - 30
        self._keo = (e.x_root, e.y_root, self.x, self.y, self.w, doi_rong)

    def _di(self, e):
        if not self._keo:
            return
        xr, yr, x0, y0, w0, doi_rong = self._keo
        dx, dy = e.x_root - xr, e.y_root - yr
        if doi_rong:
            self.w = max(150, w0 + dx)
        else:
            self.x, self.y = x0 + dx, y0 + dy
        self._ve()

    def _tha(self, e):
        if self._keo:
            self._keo = None
            self._ve_cuoi = None
            self.khi_doi(self)

    def _lan(self, e):
        if not self.dang_chinh:
            return
        self.co_chu = max(10, min(48, self.co_chu + (1 if e.delta > 0 else -1)))
        self._ve()
        self._ve_cuoi = None
        self.khi_doi(self)


class LopToanManHinh:
    def __init__(self, root, man):
        self.man = man
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=MAU_TRONG)
        self.cv = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=MAU_TRONG)
        self.cv.pack(fill="both", expand=True)
        self.da_cai_dat = False
        self.dang_hien = False
        self._chu_ky = None

    def _mo(self):
        m = self.man
        if not self.dang_hien:
            self.win.geometry(f"{m['width']}x{m['height']}+{m['left']}+{m['top']}")
            self.win.deiconify()
        if not self.da_cai_dat:
            self.win.update_idletasks()
            self.win.attributes("-transparentcolor", MAU_TRONG)
            dat_xuyen_chuot(self.win, True)
            an_khoi_anh_chup(self.win)
            self.da_cai_dat = True
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.dang_hien = True

    def _tieu_de(self, chu):
        ve_chu_vien(self.cv, self.man["width"] - 20, 10, chu, ("Segoe UI", 11, "bold"),
                    self.man["width"] // 2, "ne", "right", 2)

    def cho(self, chu):
        self.cv.delete("all")
        self._chu_ky = None
        self._tieu_de(chu)
        self._mo()

    def hien(self, cac_doan, ghi_chu):
        chu_ky = (tuple((vi, hop[0] // 8, hop[1] // 8) for vi, hop, _ in cac_doan), ghi_chu)
        if chu_ky == self._chu_ky and self.dang_hien:
            return
        self._chu_ky = chu_ky
        cv = self.cv
        cv.delete("all")
        for vi, (x, y, w, h), cao_dong in cac_doan:
            font = ("Segoe UI", -max(12, int(cao_dong * 0.8)))
            t = cv.create_text(x, y, text=vi, font=font, fill=MAU_CHU, width=max(w, 160), anchor="nw")
            b = cv.bbox(t) or (x, y, x + w, y + h)
            r = cv.create_rectangle(min(b[0], x) - 5, min(b[1], y) - 3, max(b[2], x + w) + 5,
                                    max(b[3], y + h) + 3, fill="#17171d", outline="")
            cv.tag_lower(r, t)
        self._tieu_de(ghi_chu)
        self._mo()

    def an(self):
        self.win.withdraw()
        self.cv.delete("all")
        self.dang_hien = False
        self._chu_ky = None


class ViecNen:
    """Luong nen chi lam viec MOI NHAT (viec cu chua kip lam thi bo)."""

    def __init__(self, ham, khi_loi):
        self.ham, self.khi_loi = ham, khi_loi
        self.dk = threading.Condition()
        self.viec = None
        self.ban = False
        threading.Thread(target=self._chay, daemon=True).start()

    def gui(self, *tham_so):
        with self.dk:
            self.viec = tham_so
            self.dk.notify()

    def _chay(self):
        while True:
            with self.dk:
                while self.viec is None:
                    self.dk.wait()
                tham_so, self.viec = self.viec, None
                self.ban = True
            try:
                self.ham(*tham_so)
            except Exception as e:
                self.khi_loi(e)
            finally:
                self.ban = False


class TrangThai:
    def __init__(self):
        self.van_tay = None
        self.chu_ocr = None
        self.chu_cho = None
        self.so_lan_giong = 0
        self.chu_da_hien = ""
        self.lan_trong = 0
        self.lan_lech = 0
        self.lan_xem = 0.0


# ================================================================ App chinh

class App:
    def __init__(self):
        self.cfg = nang_cap_cau_hinh(tron(CAU_HINH_MAC_DINH, doc_json(FILE_CAU_HINH, {})))
        self.root = tk.Tk()
        self.root.title(f"Dịch Game v{APP_VERSION}")
        self.root.configure(bg=UI_NEN)
        self.root.resizable(False, False)
        bieu_tuong = os.path.join(THU_MUC_APP, "icon.ico")
        if DONG_GOI:
            bieu_tuong = os.path.join(getattr(sys, "_MEIPASS", THU_MUC_APP), "icon.ico")
        try:
            self.root.iconbitmap(bieu_tuong)
        except Exception:
            pass
        self.q = queue.Queue()
        self.bo_dich = BoDich(self.cfg)
        self.man = man_hinh_chinh()
        self.khung = {k: KhungBanDich(self.root, k, self._khung_doi_bang_chuot) for k in VUNG}
        self.toan_man = LopToanManHinh(self.root, self.man)
        self.trang_thai = {k: TrangThai() for k in VUNG}
        self.van_ban = {k: "" for k in VUNG}
        self.anh_xem = {}
        self.hien_ban_dich = True
        self.dang_chon = False
        self.dang_chinh_khung = False
        self.xem_vung = False
        self.toan_man_bat = False
        self.dang_dich_toan_man = False
        self.lan_toan_man = 0.0
        self.doan_truoc = []
        self.ban_moi = None
        self.xem_thu_den = 0.0
        self.tam_dung = threading.Event()
        self.ep_dich = threading.Event()
        self.can_toan_man = threading.Event()
        self.dung = threading.Event()
        self.viec_dich = {k: ViecNen(lambda chu, k=k: self._thuc_hien_dich(k, chu), self._loi_nen) for k in VUNG}
        self.viec_toan_man = ViecNen(self._xu_ly_toan_man, self._loi_nen)

        self._giao_dien()
        self._dang_ky_phim()
        self.root.after(300, lambda: an_khoi_anh_chup(self.root))
        threading.Thread(target=self._vong_lap, daemon=True).start()
        for k in VUNG:
            self.viec_dich[k].gui("")  # mo san ket noi toi Claude
        self.root.after(50, self._xu_ly_hang_doi)
        self.root.after(2000, self._giu_tren_cung)
        self.root.after(30000, self._luu_dinh_ky)
        if self.cfg.get("tu_kiem_tra_cap_nhat"):
            self.root.after(4000, lambda: self._kiem_tra_cap_nhat(im_lang=True))
        self.root.protocol("WM_DELETE_WINDOW", self.thoat)

    # ------------------------------------------------------------ cac phan tu giao dien
    def _nut(self, cha, chu, lenh=None, kieu="thuong", rong=None, cmd=None, nho=False):
        mau = {"thuong": (UI_O, UI_CHU, UI_O_HOVER), "chinh": (UI_DO, "#ffffff", UI_DO_HOVER)}[kieu]
        b = tk.Button(cha, text=chu, command=cmd or (lambda: self.lenh(lenh)), bg=mau[0], fg=mau[1],
                      activebackground=mau[2], activeforeground=mau[1], relief="flat", bd=0,
                      highlightthickness=0, padx=8 if nho else 12, pady=3 if nho else 6, cursor="hand2",
                      font=("Segoe UI", 9) if nho else FONT)
        if rong:
            b.config(width=rong)
        b.mau_nen, b.mau_hover = mau[0], mau[2]
        b.bind("<Enter>", lambda e: b.config(bg=b.mau_hover))
        b.bind("<Leave>", lambda e: b.config(bg=b.mau_nen))
        return b

    def _dat_mau_nut(self, b, bat):
        b.mau_nen = UI_DO if bat else UI_O
        b.mau_hover = UI_DO_HOVER if bat else UI_O_HOVER
        b.config(bg=b.mau_nen, fg="#ffffff" if bat else UI_CHU)

    def _the(self, cha, tieu_de):
        ngoai = tk.Frame(cha, bg=UI_THE, padx=14, pady=10)
        ngoai.pack(fill="x", pady=(0, 10))
        tk.Label(ngoai, text=tieu_de.upper(), bg=UI_THE, fg=UI_VANG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        return ngoai

    def _hang(self, cha, pady=3):
        h = tk.Frame(cha, bg=UI_THE)
        h.pack(fill="x", pady=pady)
        return h

    def _nhan(self, cha, chu="", mau=UI_CHU, font=FONT, **kw):
        return tk.Label(cha, text=chu, bg=cha["bg"], fg=mau, font=font, **kw)

    def _o_chon(self, cha, chu, bien, lenh):
        return tk.Checkbutton(cha, text=chu, variable=bien, command=lenh, bg=cha["bg"], fg=UI_CHU,
                              selectcolor=UI_O, activebackground=cha["bg"], activeforeground=UI_CHU,
                              font=("Segoe UI", 9), bd=0, highlightthickness=0, cursor="hand2")

    def _cap(self, cha, lua_chon, lenh_cua):
        """Nhom nut chon 1 trong nhieu (segmented)."""
        h = tk.Frame(cha, bg=cha["bg"])
        nut = {}
        for gia_tri, chu in lua_chon:
            b = self._nut(h, chu, cmd=lambda g=gia_tri: lenh_cua(g), nho=True)
            b.pack(side="left", padx=(0, 2))
            nut[gia_tri] = b
        return h, nut

    # ------------------------------------------------------------ giao dien
    def _giao_dien(self):
        p = self.cfg["phim_tat"]
        goc = tk.Frame(self.root, bg=UI_NEN, padx=16, pady=14)
        goc.pack()

        dau = tk.Frame(goc, bg=UI_NEN)
        dau.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 10))
        tk.Label(dau, text="DỊCH GAME", bg=UI_NEN, fg=UI_CHU, font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(dau, text=f"  Anh → Việt  •  v{APP_VERSION}", bg=UI_NEN, fg=UI_PHU,
                 font=("Segoe UI", 10)).pack(side="left", pady=(8, 0))
        self.lbl_tt = tk.Label(goc, text="Đang khởi động...", bg=UI_THE, fg=UI_PHU, font=("Segoe UI", 9),
                               wraplength=760, justify="left", anchor="w", padx=12, pady=6)
        self.lbl_tt.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))

        trai = tk.Frame(goc, bg=UI_NEN)
        trai.grid(row=2, column=0, sticky="n", padx=(0, 10))
        phai = tk.Frame(goc, bg=UI_NEN)
        phai.grid(row=2, column=1, sticky="n")

        # ---------- Dich AI
        t = self._the(trai, "Dịch bằng AI")
        self.lbl_khoa = self._nhan(t, font=("Segoe UI", 9))
        self.lbl_khoa.pack(anchor="w")
        h = self._hang(t)
        self.o_khoa = tk.Entry(h, show="•", width=26, bg=UI_O, fg=UI_CHU, insertbackground=UI_CHU,
                               relief="flat", font=FONT)
        self.o_khoa.pack(side="left", ipady=4, padx=(0, 6))
        self._nut(h, "Lưu mã", cmd=self._luu_khoa, nho=True).pack(side="left", padx=(0, 2))
        self._nut(h, "Thử", cmd=self._thu_claude, nho=True).pack(side="left")
        h = self._hang(t)
        self._nhan(h, "Bộ dịch:", UI_PHU, ("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        khung, self.nut_bo_dich = self._cap(h, [("claude", "Claude AI"), ("google", "Google (miễn phí)")],
                                            lambda g: self.lenh("bo_dich_" + g))
        khung.pack(side="left")
        self.lbl_tien = self._nhan(t, mau=UI_PHU, font=("Segoe UI", 9))
        self.lbl_tien.pack(anchor="w", pady=(4, 0))
        self.bien_google = tk.BooleanVar(value=bool(self.cfg["hien_google_truoc"]))
        self._o_chon(t, "Hiện bản Google trước trong lúc chờ Claude (nhanh hơn)", self.bien_google,
                     self._doi_google_truoc).pack(anchor="w", pady=(4, 0))

        # ---------- Vung dich
        t = self._the(trai, "Vùng dịch (app tự nhớ)")
        self.lbl_vung = {}
        for khoa, phim in (("hoi_thoai", p["chon_hoi_thoai"]), ("nhiem_vu", p["chon_nhiem_vu"])):
            h = self._hang(t)
            self._nhan(h, VUNG[khoa], font=FONT_DAM, width=9, anchor="w").pack(side="left")
            self.lbl_vung[khoa] = self._nhan(h, "", UI_PHU, ("Segoe UI", 9), width=22, anchor="w")
            self.lbl_vung[khoa].pack(side="left")
            self._nut(h, f"Chọn ({phim.upper()})", "chon_" + khoa, nho=True).pack(side="right")
        self.bien_loc = tk.BooleanVar(value=bool(self.cfg["loc_chu_trang"].get("hoi_thoai")))
        self._o_chon(t, "Lọc chữ trắng cho phụ đề Hội thoại (nên bật)", self.bien_loc,
                     self._doi_loc).pack(anchor="w", pady=(4, 0))

        # ---------- Dieu khien
        t = self._the(trai, "Điều khiển")
        self.nut_tu_dong = self._nut(t, "", "bat_tat_tu_dong")
        self.nut_tu_dong.pack(fill="x", pady=2)
        h = self._hang(t)
        self._nut(h, f"Dịch ngay ({p['dich_ngay'].upper()})", "dich_ngay").pack(side="left", expand=True,
                                                                                fill="x", padx=(0, 4))
        self._nut(h, f"Ẩn / Hiện ({p['an_hien'].upper()})", "an_hien").pack(side="left", expand=True, fill="x")
        self.nut_toan_man = self._nut(t, "", "dich_man_hinh")
        self.nut_toan_man.pack(fill="x", pady=(6, 2))
        h = self._hang(t)
        self._nhan(h, "Kiểu dịch cả màn hình:", UI_PHU, ("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        khung, self.nut_kieu_toan_man = self._cap(h, [("lien_tuc", "Liên tục"), ("mot_lan", "1 lần")],
                                                  lambda g: self.lenh("toan_man_" + g))
        khung.pack(side="left")

        # ---------- Hien thi
        t = self._the(phai, "Khung dịch")
        h = self._hang(t)
        self._nhan(h, "Kiểu:", UI_PHU, ("Segoe UI", 9), width=8, anchor="w").pack(side="left")
        khung, self.nut_kieu = self._cap(h, [("phu_de", "Phụ đề (chỉ chữ)"), ("khung", "Khung nền tối")],
                                         lambda g: self.lenh("kieu_" + g))
        khung.pack(side="left")
        self.nut_chinh = self._nut(t, "", "chinh_khung")
        self.nut_chinh.pack(fill="x", pady=(6, 4))

        def cong_tru(ten, tru, cong):
            h = self._hang(t, 2)
            nhan = self._nhan(h, ten, UI_PHU, ("Segoe UI", 9), width=14, anchor="w")
            nhan.pack(side="left")
            self._nut(h, "−", tru, nho=True, rong=2).pack(side="left")
            gt = self._nhan(h, "", UI_CHU, FONT_DAM, width=6)
            gt.pack(side="left")
            self._nut(h, "+", cong, nho=True, rong=2).pack(side="left")
            return nhan, gt

        self.lbl_dam_ten, self.lbl_dam = cong_tru("", "giam_do_dam", "tang_do_dam")
        _, self.lbl_vien = cong_tru("Viền chữ:", "giam_vien", "tang_vien")
        for khoa in VUNG:
            h = self._hang(t, 2)
            self._nhan(h, VUNG[khoa] + ":", UI_PHU, ("Segoe UI", 9), width=14, anchor="w").pack(side="left")
            for chu, hanh in (("◀", "trai"), ("▲", "len"), ("▼", "xuong"), ("▶", "phai")):
                self._nut(h, chu, f"{khoa}_{hanh}", nho=True, rong=2).pack(side="left", padx=1)
            self._nut(h, "A+", f"{khoa}_to", nho=True).pack(side="left", padx=(8, 1))
            self._nut(h, "A−", f"{khoa}_nho", nho=True).pack(side="left", padx=1)
        self._nhan(t, f"Ctrl+mũi tên: dời khung Hội thoại • Ctrl+Shift+mũi tên: dời khung Nhiệm vụ",
                   UI_PHU, ("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        # ---------- Xem vung chup
        t = self._the(phai, "App đang nhìn thấy gì")
        self.nut_xem = self._nut(t, "", "xem_vung")
        self.nut_xem.pack(fill="x", pady=(0, 4))
        self.lbl_xem = {}
        for khoa in VUNG:
            self._nhan(t, VUNG[khoa], UI_PHU, ("Segoe UI", 8)).pack(anchor="w")
            self.lbl_xem[khoa] = tk.Label(t, text="(tắt)", fg=UI_PHU, bg="#0d0e12", width=48, height=3)
            self.lbl_xem[khoa].pack(pady=(0, 4), anchor="w")

        # ---------- He thong
        t = self._the(phai, "Hệ thống")
        h = self._hang(t)
        self.nut_cach_chup = self._nut(h, "", "doi_cach_chup", nho=True)
        self.nut_cach_chup.pack(side="left", padx=(0, 4))
        self._nut(h, "Thư mục dữ liệu", cmd=lambda: os.startfile(DU_LIEU), nho=True).pack(side="left")
        h = self._hang(t)
        self.nut_cap_nhat = self._nut(h, "Kiểm tra cập nhật", cmd=self._kiem_tra_cap_nhat, nho=True)
        self.nut_cap_nhat.pack(side="left", padx=(0, 4))
        self._nut(h, "Thoát", kieu="chinh", cmd=self.thoat, nho=True).pack(side="right")

        self._cap_nhat_nut()

    def _bao(self, chu, loai="ok"):
        mau = {"ok": UI_XANH, "loi": UI_LOI, "canh_bao": UI_VANG, "phu": UI_PHU}.get(loai, UI_PHU)
        self.lbl_tt.config(text=chu, fg=mau)

    def _cap_nhat_nut(self):
        c, p = self.cfg, self.cfg["phim_tat"]
        self.nut_tu_dong.config(text=f"Tự động dịch: {'BẬT' if c['tu_dong_dich'] else 'TẮT'}  "
                                     f"({p['bat_tat_tu_dong'].upper()})")
        self._dat_mau_nut(self.nut_tu_dong, c["tu_dong_dich"])
        khoa = self.bo_dich.khoa_api
        if khoa and self.bo_dich.khoa_hong:
            self.lbl_khoa.config(text=f"Mã API (…{khoa[-4:]}) bị từ chối – dán mã mới", fg=UI_LOI)
        elif khoa:
            self.lbl_khoa.config(text=f"Mã API đã lưu (…{khoa[-4:]}) ✓", fg=UI_XANH)
        else:
            self.lbl_khoa.config(text="Chưa có mã API – dán mã vào ô dưới", fg=UI_VANG)
        for g, b in self.nut_bo_dich.items():
            self._dat_mau_nut(b, c["bo_dich"] == g)
        usd = c["da_dung_usd"]
        self.lbl_tien.config(text=f"Đã dùng khoảng {usd:.4f} USD (≈ {usd * TY_GIA:,.0f}đ)".replace(",", "."))
        for khoa in VUNG:
            v = c["vung"].get(khoa)
            self.lbl_vung[khoa].config(text=f"đã nhớ ✓  {v[2]}×{v[3]}" if v else "chưa chọn",
                                       fg=UI_XANH if v else UI_VANG)
        self.nut_toan_man.config(text=(f"Dịch cả màn hình: {'BẬT' if self.toan_man_bat else 'TẮT'}  "
                                       f"({p['dich_man_hinh'].upper()})") if c["toan_man_lien_tuc"]
                                 else f"Dịch cả màn hình 1 lần  ({p['dich_man_hinh'].upper()})")
        self._dat_mau_nut(self.nut_toan_man, self.toan_man_bat or self.toan_man.dang_hien)
        for g, b in self.nut_kieu_toan_man.items():
            self._dat_mau_nut(b, (g == "lien_tuc") == bool(c["toan_man_lien_tuc"]))
        for g, b in self.nut_kieu.items():
            self._dat_mau_nut(b, c["kieu_hien"] == g)
        phu_de = c["kieu_hien"] == "phu_de"
        self.lbl_dam_ten.config(text="Độ đậm chữ:" if phu_de else "Độ đậm khung:")
        self.lbl_dam.config(text=f"{round((c['do_dam_chu'] if phu_de else c['do_mo']) * 100)}%")
        self.lbl_vien.config(text=str(c["vien_chu"]) if c["vien_chu"] else "tắt")
        self.nut_chinh.config(text=("✔ ĐANG CHỈNH KHUNG – bấm để khóa" if self.dang_chinh_khung
                                    else f"Chỉnh khung bằng chuột  ({p['chinh_khung'].upper()})"))
        self._dat_mau_nut(self.nut_chinh, self.dang_chinh_khung)
        ten_cach = {"tu_dong": "Tự động", "wgc": "WGC", "dxgi": "DXGI", "gdi": "GDI"}
        self.nut_cach_chup.config(text=f"Cách chụp: {ten_cach.get(c.get('cach_chup'), '?')}")
        self.nut_xem.config(text="Tắt xem vùng chụp" if self.xem_vung else "Bật xem vùng chụp (mỗi giây)")
        self._dat_mau_nut(self.nut_xem, self.xem_vung)
        if self.ban_moi:
            self.nut_cap_nhat.config(text=f"Cập nhật lên v{self.ban_moi['phien_ban']}")
            self._dat_mau_nut(self.nut_cap_nhat, True)

    def _dang_ky_phim(self):
        for lenh, phim in self.cfg["phim_tat"].items():
            try:
                keyboard.add_hotkey(phim, lambda l=lenh: self.q.put(("lenh", l)))
            except Exception as e:
                self._bao(f"Phím tắt '{phim}' không dùng được: {e}", "loi")

    def _doi_loc(self):
        self.cfg["loc_chu_trang"]["hoi_thoai"] = bool(self.bien_loc.get())
        self.trang_thai["hoi_thoai"] = TrangThai()
        self._luu_cau_hinh()

    def _doi_google_truoc(self):
        self.cfg["hien_google_truoc"] = bool(self.bien_google.get())
        self._luu_cau_hinh()

    def _loi_nen(self, e):
        self.q.put(("trang_thai", f"Lỗi: {type(e).__name__}: {e}"))

    # ------------------------------------------------------------ ma API
    def _luu_khoa(self):
        khoa = self.o_khoa.get().strip()
        if not khoa.startswith("sk-ant-"):
            self._bao("Mã không đúng dạng (phải bắt đầu bằng sk-ant-).", "loi")
            return
        try:
            self.bo_dich.luu_khoa(khoa)
        except Exception as e:
            self._bao(f"Không lưu được mã: {e}", "loi")
            return
        self.o_khoa.delete(0, "end")
        self.cfg["bo_dich"] = "claude"
        self._luu_cau_hinh()
        self._cap_nhat_nut()
        self._thu_claude()

    def _thu_claude(self):
        if not self.bo_dich.khoa_api:
            self._bao("Chưa có mã API.", "loi")
            return
        self._bao("Đang thử kết nối Claude...", "phu")

        def chay():
            try:
                t0 = time.time()
                kq, vao, ra = self.bo_dich.claude.dich(
                    self.bo_dich.khoa_api, self.cfg["mo_hinh"],
                    "Greetings, traveler. The road to Hernand is dangerous at night.", "hoi_thoai", [], [])
                self.bo_dich.khoa_hong = False
                self.q.put(("tien", self.bo_dich.tien(vao, ra)))
                self.q.put(("trang_thai", f"Đang chạy • Claude OK ({time.time() - t0:.1f}s): {kq}"))
            except Exception as e:
                self.q.put(("trang_thai", f"Claude chưa dùng được: {e}"))

        threading.Thread(target=chay, daemon=True).start()

    # ------------------------------------------------------------ cap nhat
    def _kiem_tra_cap_nhat(self, im_lang=False):
        if not im_lang:
            self._bao("Đang kiểm tra bản mới...", "phu")

        def chay():
            try:
                tt = lay_thong_tin_ban_moi(self.cfg)
                if so_phien_ban(tt.get("phien_ban")) > so_phien_ban(APP_VERSION):
                    self.q.put(("ban_moi", tt, im_lang))
                elif not im_lang:
                    self.q.put(("trang_thai", f"Đang chạy • Bạn đang dùng bản mới nhất (v{APP_VERSION})"))
            except Exception as e:
                if not im_lang:
                    self.q.put(("trang_thai", f"Không kiểm tra được cập nhật: {e}"))

        threading.Thread(target=chay, daemon=True).start()

    def _hoi_cap_nhat(self, tt):
        ghi_chu = (tt.get("ghi_chu") or "").strip()[:800]
        if not messagebox.askyesno("Có bản mới",
                                   f"Có bản mới v{tt['phien_ban']} (bạn đang dùng v{APP_VERSION}).\n\n"
                                   f"{ghi_chu}\n\nCập nhật ngay? App sẽ tự tắt và mở lại.", parent=self.root):
            return
        self._bao("Đang tải bản mới...", "phu")

        def chay():
            try:
                if ap_dung_cap_nhat(tt, lambda chu: self.q.put(("trang_thai_phu", chu))):
                    self.q.put(("thoat_cap_nhat",))
            except Exception as e:
                self.q.put(("trang_thai", f"Cập nhật lỗi: {e}"))

        threading.Thread(target=chay, daemon=True).start()

    # ------------------------------------------------------------ lenh
    def _khung_cua(self, khoa):
        kd = self.cfg["khung_dich"].get(khoa)
        if kd:
            return list(kd)
        v = self.cfg["vung"].get(khoa)
        return [v[0], v[1], v[2]] if v else None

    def lenh(self, ten):
        c = self.cfg
        if ten == "chon_hoi_thoai":
            self.chon_vung("hoi_thoai")
        elif ten == "chon_nhiem_vu":
            self.chon_vung("nhiem_vu")
        elif ten == "bat_tat_tu_dong":
            c["tu_dong_dich"] = not c["tu_dong_dich"]
        elif ten == "dich_ngay":
            self.ep_dich.set()
        elif ten == "an_hien":
            self.hien_ban_dich = not self.hien_ban_dich
            self._ve_lai()
        elif ten == "dich_man_hinh":
            if c["toan_man_lien_tuc"]:
                self.toan_man_bat = not self.toan_man_bat
                self.doan_truoc = []
                if self.toan_man_bat:
                    self.lan_toan_man = 0.0
                    self.toan_man.cho("⏳ Đang bật dịch cả màn hình...")
                else:
                    self.toan_man.an()
            elif self.toan_man.dang_hien:
                self.toan_man.an()
            elif not self.dang_dich_toan_man:
                self.dang_dich_toan_man = True
                self.toan_man.cho("⏳ Đang đọc và dịch cả màn hình...")
                self.can_toan_man.set()
                self.ep_dich.set()
        elif ten in ("toan_man_lien_tuc", "toan_man_mot_lan"):
            c["toan_man_lien_tuc"] = ten == "toan_man_lien_tuc"
            self.toan_man_bat = False
            self.toan_man.an()
        elif ten == "xem_vung":
            self.xem_vung = not self.xem_vung
            if not self.xem_vung:
                for k in VUNG:
                    self.lbl_xem[k].config(image="", text="(tắt)", width=48, height=3)
                self.anh_xem.clear()
        elif ten in ("bo_dich_claude", "bo_dich_google"):
            c["bo_dich"] = ten.split("_")[-1]
            if c["bo_dich"] == "claude" and not self.bo_dich.khoa_api:
                self._bao("Chưa có mã API – dán mã vào ô rồi bấm Lưu mã.", "canh_bao")
        elif ten in ("kieu_phu_de", "kieu_khung"):
            c["kieu_hien"] = "phu_de" if ten == "kieu_phu_de" else "khung"
            self._xem_thu()
        elif ten == "chinh_khung":
            self.dang_chinh_khung = not self.dang_chinh_khung
            for khung in self.khung.values():
                khung.che_do_chinh(self.dang_chinh_khung)
            self._ve_lai()
        elif ten in ("tang_do_dam", "giam_do_dam"):
            ten_gt = "do_dam_chu" if c["kieu_hien"] == "phu_de" else "do_mo"
            c[ten_gt] = round(max(0.2, min(1.0, c[ten_gt] + (0.05 if ten == "tang_do_dam" else -0.05))), 2)
            self._xem_thu()
        elif ten in ("tang_vien", "giam_vien"):
            c["vien_chu"] = max(0, min(5, c["vien_chu"] + (1 if ten == "tang_vien" else -1)))
            self._xem_thu()
        elif ten == "doi_cach_chup":
            thu_tu = ["tu_dong", "dxgi", "gdi"]
            hien_tai = c.get("cach_chup", "tu_dong")
            c["cach_chup"] = thu_tu[(thu_tu.index(hien_tai) + 1) % 3] if hien_tai in thu_tu else "tu_dong"
            self._bao("Đã đổi cách chụp – TẮT app rồi MỞ LẠI để áp dụng.", "canh_bao")
        elif "_" in ten and ten.rsplit("_", 1)[0] in VUNG:
            khoa, hanh = ten.rsplit("_", 1)
            kd = self._khung_cua(khoa)
            if not kd:
                self._bao(f"Chưa chọn vùng {VUNG[khoa]}.", "canh_bao")
                return
            if hanh == "len":
                kd[1] -= 20
            elif hanh == "xuong":
                kd[1] += 20
            elif hanh == "trai":
                kd[0] -= 20
            elif hanh == "phai":
                kd[0] += 20
            elif hanh == "to":
                kd[2] = int(kd[2] * 1.1)
                c["co_chu"][khoa] = min(48, c["co_chu"][khoa] + 1)
            elif hanh == "nho":
                kd[2] = max(150, int(kd[2] / 1.1))
                c["co_chu"][khoa] = max(10, c["co_chu"][khoa] - 1)
            else:
                return
            c["khung_dich"][khoa] = kd
            self._xem_thu()
        elif ten == "thoat":
            self.thoat()
            return
        else:
            return
        self._cap_nhat_nut()
        self._luu_cau_hinh()

    def _khung_doi_bang_chuot(self, khung):
        self.cfg["khung_dich"][khung.khoa] = [khung.x, khung.y, khung.w]
        self.cfg["co_chu"][khung.khoa] = khung.co_chu
        self._luu_cau_hinh()

    def _xem_thu(self):
        self.xem_thu_den = time.time() + 2
        self._ve_lai()
        self.root.after(2100, self._ve_lai)

    def _ve_lai(self):
        c = self.cfg
        for k, khung in self.khung.items():
            kd = self._khung_cua(k)
            chu = self.van_ban[k]
            if not chu and time.time() < self.xem_thu_den:
                chu = f"(Khung dịch {VUNG[k].lower()} – xem thử)"
            hien = kd and not self.dang_chon and (self.dang_chinh_khung or (self.hien_ban_dich and chu))
            if hien:
                do_dam = c["do_dam_chu"] if c["kieu_hien"] == "phu_de" else c["do_mo"]
                khung.hien(chu, kd[0], kd[1], kd[2], c["co_chu"][k], c["kieu_hien"], do_dam, c["vien_chu"])
            else:
                khung.an()

    # ------------------------------------------------------------ chon vung
    def chon_vung(self, khoa):
        if self.dang_chon:
            return
        self.dang_chon = True
        self.tam_dung.set()
        for khung in self.khung.values():
            khung.an()
        with mss.mss() as s:
            tat_ca, chinh = s.monitors[0], s.monitors[1]

        sel = tk.Toplevel(self.root)
        sel.overrideredirect(True)
        sel.attributes("-topmost", True)
        sel.attributes("-alpha", 0.35)
        sel.geometry(f"{tat_ca['width']}x{tat_ca['height']}+{tat_ca['left']}+{tat_ca['top']}")
        cv = tk.Canvas(sel, bg="black", highlightthickness=0, cursor="crosshair")
        cv.pack(fill="both", expand=True)
        cx = chinh["left"] - tat_ca["left"] + chinh["width"] // 2
        cy = chinh["top"] - tat_ca["top"] + 70
        cv.create_text(cx, cy, fill="white", font=("Segoe UI", 22, "bold"),
                       text=f"Kéo chuột khoanh vùng chữ {VUNG[khoa].upper()}   •   Esc để hủy")
        cu = self.cfg["vung"].get(khoa)
        if cu:
            x, y, w, h = cu
            cv.create_rectangle(x - tat_ca["left"], y - tat_ca["top"], x - tat_ca["left"] + w,
                                y - tat_ca["top"] + h, outline="#f0b54a", width=2, dash=(6, 4))
        dau = {}

        def dong():
            sel.destroy()
            self.dang_chon = False
            self.trang_thai[khoa] = TrangThai()
            self.tam_dung.clear()
            self._ve_lai()
            self._cap_nhat_nut()
            self.ep_dich.set()

        def nhan(e):
            dau["x"], dau["y"] = e.x, e.y
            dau["hcn"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#ff4040", width=3)

        def keo(e):
            if "hcn" in dau:
                cv.coords(dau["hcn"], dau["x"], dau["y"], e.x, e.y)

        def tha(e):
            if "x" not in dau:
                return
            x1, x2 = sorted((dau["x"], e.x))
            y1, y2 = sorted((dau["y"], e.y))
            if x2 - x1 >= 20 and y2 - y1 >= 10:
                v = [x1 + tat_ca["left"], y1 + tat_ca["top"], x2 - x1, y2 - y1]
                self.cfg["vung"][khoa] = v
                if not self.cfg["khung_dich"].get(khoa):
                    self.cfg["khung_dich"][khoa] = [v[0], v[1], v[2]]
                self.van_ban[khoa] = ""
                self._luu_cau_hinh()
                self._bao(f"Đã lưu vùng {VUNG[khoa]} – lần sau mở app không cần chọn lại.")
            dong()

        cv.bind("<ButtonPress-1>", nhan)
        cv.bind("<B1-Motion>", keo)
        cv.bind("<ButtonRelease-1>", tha)
        sel.bind("<Escape>", lambda e: dong())
        sel.after(80, sel.focus_force)

    # ------------------------------------------------------------ luong doc man hinh
    def _vong_lap(self):
        try:
            sct = BoChup(self.cfg.get("cach_chup", "tu_dong"))
        except Exception as e:
            self.q.put(("trang_thai", f"Không chụp được màn hình: {e}"))
            return
        if sct.nguon is None:
            self.q.put(("trang_thai", "CẢNH BÁO: đang dùng cách chụp cũ (GDI), có thể chụp nhầm Desktop. "
                                      "Lỗi: " + " | ".join(sct.ghi_chu)))
        else:
            self.q.put(("trang_thai", f"Đang chạy (chụp: {sct.ten})"))
        dem = 0
        while not self.dung.is_set():
            ep = self.ep_dich.wait(self.cfg["chu_ky_giay"])
            self.ep_dich.clear()
            if self.dung.is_set():
                break
            dem += 1
            da_lam_moi = False

            # --- dich ca man hinh
            mot_lan = self.can_toan_man.is_set()
            lien_tuc = (self.toan_man_bat and not self.viec_toan_man.ban
                        and time.time() - self.lan_toan_man >= self.cfg["chu_ky_toan_man_giay"])
            if mot_lan or lien_tuc:
                self.can_toan_man.clear()
                self.lan_toan_man = time.time()
                sct.lam_moi()
                da_lam_moi = True
                try:
                    self.viec_toan_man.gui(sct.toan_man(), mot_lan)
                except Exception as e:
                    self.q.put(("toan_man", None, f"Không chụp được màn hình: {e}", mot_lan))

            if self.tam_dung.is_set() or self.dang_chinh_khung:
                continue
            tu_dong = ep or self.cfg["tu_dong_dich"]
            can_lam = [k for k in VUNG if self.cfg["vung"].get(k)
                       and (ep or dem % TUY_VUNG[k]["moi"] == 0)]
            if not tu_dong and not self.xem_vung:
                continue
            if not can_lam:
                continue
            if not da_lam_moi:
                sct.lam_moi()
            for khoa in can_lam:
                try:
                    if tu_dong:
                        self._xu_ly_vung(sct, khoa, ep)
                    else:
                        self._gui_xem(sct.cat(self.cfg["vung"][khoa]), khoa)
                except Exception as e:
                    self.q.put(("trang_thai", f"Lỗi ở vùng {VUNG[khoa]}: {e}"))
        sct.dong()

    def _gui_xem(self, anh, khoa):
        st = self.trang_thai[khoa]
        if not self.xem_vung or time.time() - st.lan_xem < 1.0:
            return
        st.lan_xem = time.time()
        anh = anh.copy()
        anh.thumbnail((360, 90))
        self.q.put(("xem", khoa, anh))

    def _xu_ly_vung(self, sct, khoa, ep):
        st = self.trang_thai[khoa]
        tuy = TUY_VUNG[khoa]
        anh = sct.cat(self.cfg["vung"][khoa])
        self._gui_xem(anh, khoa)
        loc = self.cfg["loc_chu_trang"].get(khoa)
        anh_doc = loc_chu_trang(anh, self.cfg["nguong_chu_trang"]) if loc else anh
        if ep:
            try:
                anh.save(os.path.join(DU_LIEU, f"anh_chup_{khoa}.png"))
                if loc:
                    anh_doc.save(os.path.join(DU_LIEU, f"anh_chup_{khoa}_da_loc.png"))
            except Exception:
                pass

        van_tay = dau_van_tay(anh_doc)
        if not ep and st.chu_ocr is not None and anh_giong(van_tay, st.van_tay):
            chu = st.chu_ocr
        else:
            try:
                chu = lam_sach(doc_chu(anh_doc))
            except Exception as e:
                self.q.put(("trang_thai", "Không đọc được chữ. Có thể Windows chưa cài gói đọc chữ "
                                          f"tiếng Anh (xem HUONG_DAN.txt). Lỗi: {e}"))
                return
            hien_tai = self.van_ban.get(khoa) or ""
            if chu and hien_tai and chu_giong(bo_dau(chu), bo_dau(hien_tai), 0.55):
                self.q.put(("bi_chup", khoa))
                st.van_tay = van_tay
                return
            st.chu_ocr = chu
        st.van_tay = van_tay

        st.lan_trong = st.lan_trong + 1 if not chu else 0
        if st.chu_da_hien and chu and not chu_giong(so_hoa(chu), so_hoa(st.chu_da_hien), tuy["lech"]):
            st.lan_lech += 1
        else:
            st.lan_lech = 0
        if st.chu_da_hien and (st.lan_trong >= tuy["an_trong"] or st.lan_lech >= tuy["an_lech"]):
            st.chu_da_hien = ""
            st.lan_lech = 0
            self.q.put(("an", khoa))

        if st.chu_cho is not None and chu_giong(so_hoa(chu), so_hoa(st.chu_cho), 0.9):
            st.so_lan_giong += 1
        else:
            st.so_lan_giong = 0
        st.chu_cho = chu
        # hoi thoai: cau da co dau ket thuc thi dich ngay, khong cho doc lan 2
        on_dinh = ep or st.so_lan_giong >= 1 or (khoa == "hoi_thoai" and het_cau(chu))
        if not on_dinh or not chu:
            return
        if not ep and st.chu_da_hien:
            if chu == st.chu_da_hien:
                return
            chi_doi_so = so_hoa(chu) == so_hoa(st.chu_da_hien)
            if not chi_doi_so and chu_giong(so_hoa(chu), so_hoa(st.chu_da_hien), tuy["bo_qua"]):
                return

        st.chu_da_hien = chu
        self.viec_dich[khoa].gui(chu)  # dich o luong rieng -> vong doc man hinh khong bi cho

    def _thuc_hien_dich(self, khoa, chu):
        if not chu:  # lenh "lam nong" ket noi luc mo app
            if self.bo_dich.dung_claude():
                self.bo_dich.claude.lam_nong()
            return
        st = self.trang_thai[khoa]

        def con_dung():
            return self.trang_thai[khoa] is st and st.chu_da_hien == chu

        cu = self.bo_dich.tim(chu)
        if cu is not None:
            if con_dung():
                self.q.put(("hien", khoa, cu))
            return

        trang = {"google": False, "xong": False, "do_dai": 0, "lan_cuoi": 0.0}
        if self.bo_dich.dung_claude() and self.cfg.get("hien_google_truoc") and khoa == "hoi_thoai":
            def google_truoc():
                try:
                    vi = google_dich(chu)
                except Exception:
                    return
                if not trang["xong"] and trang["do_dai"] < 15 and con_dung():
                    trang["google"] = True
                    self.q.put(("hien", khoa, vi))
            threading.Thread(target=google_truoc, daemon=True).start()

        def dang_ra(doan):
            trang["do_dai"] = len(doan)
            if trang["google"]:
                return  # dang hien ban Google -> doi Claude xong roi thay
            bay_gio = time.time()
            if bay_gio - trang["lan_cuoi"] > 0.12 and con_dung():
                trang["lan_cuoi"] = bay_gio
                self.q.put(("hien", khoa, doan))

        try:
            ban_dich, nguon, tien, loi = self.bo_dich.dich(chu, khoa, dang_ra)
            trang["xong"] = True
            if tien:
                self.q.put(("tien", tien))
            self.q.put(("trang_thai", loi or f"Đang chạy • {VUNG[khoa]}: {nguon}"))
        except Exception as e:
            trang["xong"] = True
            ban_dich = f"[Không dịch được: {type(e).__name__} {str(e)[:80]}]\n" + chu
            if con_dung():
                st.chu_da_hien = ""
        if ban_dich.strip() and con_dung():
            self.q.put(("hien", khoa, ban_dich))

    def _xu_ly_toan_man(self, anh, mot_lan):
        try:
            self._xu_ly_toan_man_that(anh, mot_lan)
        except Exception as e:
            self.q.put(("toan_man", None, f"Lỗi dịch cả màn hình: {e}", mot_lan))

    def _xu_ly_toan_man_that(self, anh, mot_lan):
        if not mot_lan and not self.toan_man_bat:
            return
        cac_vung = [v for v in self.cfg["vung"].values() if v]
        cac_doan = [d for d in gom_doan(ocr_toan_man(anh))
                    if not la_tieng_viet(d[0]) and not any(giao_nhau(d[1], v) for v in cac_vung)]
        ket_qua, can_dich = [], []
        for chu, hop, cao in cac_doan:
            vi = self.bo_dich.tim(chu)
            if vi is not None:
                ket_qua.append((vi, hop, cao, chu))
            elif mot_lan or any(chu_giong(so_hoa(chu), t, 0.9) for t in self.doan_truoc):
                can_dich.append((chu, hop, cao))  # chi dich chu da xuat hien 2 lan lien tiep
        self.doan_truoc = [so_hoa(d[0]) for d in cac_doan]
        if can_dich:
            vis, tien, loi = self.bo_dich.dich_nhieu([d[0] for d in can_dich])
            if tien:
                self.q.put(("tien", tien))
            if loi:
                self.q.put(("trang_thai", loi))
            ket_qua += [(vi, hop, cao, en) for vi, (en, hop, cao) in zip(vis, can_dich)]
        ket_qua = [(vi, hop, cao) for vi, hop, cao, en in ket_qua
                   if vi.strip() and vi.strip().lower() != en.strip().lower()]
        phim = self.cfg["phim_tat"]["dich_man_hinh"].upper()
        if mot_lan:
            ghi_chu = f"Bản dịch màn hình ({len(ket_qua)} đoạn) – {phim} để tắt" if ket_qua \
                else "Không thấy chữ tiếng Anh nào trên màn hình"
        else:
            ghi_chu = f"● Dịch cả màn hình: BẬT – {phim} để tắt"
        self.q.put(("toan_man", ket_qua, ghi_chu, mot_lan))

    # ------------------------------------------------------------ nhan ket qua
    def _xu_ly_hang_doi(self):
        try:
            while True:
                tin = self.q.get_nowait()
                loai = tin[0]
                if loai == "hien":
                    self.van_ban[tin[1]] = tin[2]
                    self._ve_lai()
                elif loai == "an":
                    self.van_ban[tin[1]] = ""
                    self._ve_lai()
                elif loai == "bi_chup":
                    self._doi_khung_ra_ngoai(tin[1])
                elif loai == "tien":
                    self.cfg["da_dung_usd"] = round(self.cfg["da_dung_usd"] + tin[1], 6)
                    self._cap_nhat_nut()
                elif loai == "xem":
                    if self.xem_vung:
                        self.anh_xem[tin[1]] = ImageTk.PhotoImage(tin[2])
                        self.lbl_xem[tin[1]].config(image=self.anh_xem[tin[1]], text="", width=0, height=0)
                elif loai == "toan_man":
                    _, ket_qua, ghi_chu, mot_lan = tin
                    if mot_lan:
                        self.dang_dich_toan_man = False
                        if ket_qua:
                            self.toan_man.hien(ket_qua, ghi_chu)
                        else:
                            self.toan_man.cho(ghi_chu)
                            self.root.after(2500, self.toan_man.an)
                    elif self.toan_man_bat and ket_qua is not None:
                        self.toan_man.hien(ket_qua, ghi_chu)
                    self._cap_nhat_nut()
                elif loai == "ban_moi":
                    self.ban_moi = tin[1]
                    self._cap_nhat_nut()
                    self._bao(f"Có bản mới v{tin[1]['phien_ban']} – bấm nút cập nhật (mục Hệ thống).",
                              "canh_bao")
                    if not tin[2]:
                        self._hoi_cap_nhat(tin[1])
                elif loai == "thoat_cap_nhat":
                    self.thoat()
                    return
                elif loai == "trang_thai_phu":
                    self._bao(tin[1], "phu")
                elif loai == "trang_thai":
                    self._bao(tin[1], "ok" if tin[1].startswith("Đang chạy") else "loi")
                    if "Claude lỗi" in tin[1]:
                        self._cap_nhat_nut()
                elif loai == "lenh":
                    self.lenh(tin[1])
        except queue.Empty:
            pass
        if not self.dung.is_set():
            self.root.after(30, self._xu_ly_hang_doi)

    def _doi_khung_ra_ngoai(self, khoa):
        v = self.cfg["vung"].get(khoa)
        kd = self._khung_cua(khoa)
        if not v or not kd:
            return
        cao = self.khung[khoa].h or 60
        y = v[1] - cao - 6
        if y < 0:
            y = v[1] + v[3] + 6
        self.cfg["khung_dich"][khoa] = [kd[0], y, kd[2]]
        self._luu_cau_hinh()
        self._ve_lai()
        self._bao(f"Khung dịch {VUNG[khoa]} đang che vùng đọc chữ nên đã dời ra ngoài.", "canh_bao")

    def _giu_tren_cung(self):
        if not self.dang_chon:
            for khung in self.khung.values():
                khung.giu_tren_cung()
        if not self.dung.is_set():
            self.root.after(2000, self._giu_tren_cung)

    def _luu_dinh_ky(self):
        threading.Thread(target=self.bo_dich.luu, daemon=True).start()
        self._luu_cau_hinh()
        if not self.dung.is_set():
            self.root.after(30000, self._luu_dinh_ky)

    def _luu_cau_hinh(self):
        try:
            ghi_json(FILE_CAU_HINH, self.cfg)
        except Exception as e:
            self._bao(f"Không lưu được cài đặt: {e}", "loi")

    def thoat(self):
        if self.dung.is_set():
            return
        self.dung.set()
        self.ep_dich.set()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.bo_dich.luu()
        self._luu_cau_hinh()
        self.root.destroy()

    def chay(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().chay()
