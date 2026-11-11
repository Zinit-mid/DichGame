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
  F6 / F7   chon lai vung 1 / vung 2 (cac vung khac chon tren bang dieu khien)
  F8        bat / tat tu dong dich
  F9        dich ngay (luu anh vung chup)
  F10       an / hien ban dich
  F11       chinh khung bang chuot
  F12       dich ca man hinh (lien tuc hoac 1 lan)
  Ctrl + mui ten / Ctrl+Shift + mui ten : dich khung dich cua vung 1 / vung 2
  Ctrl+Shift+Q  thoat
"""

APP_VERSION = "6.2.1"
REPO_CAP_NHAT = "Zinit-mid/DichGame"  # kho GitHub chua ban phat hanh

import concurrent.futures
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
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from ctypes import wintypes
from tkinter import messagebox, simpledialog

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

PHIEN_BAN_CAU_HINH = 10
SO_VUNG_TOI_DA = 6
TY_GIA = 26000

# Tinh chinh theo loai vung. Vong doc: phu_de moi 0.15s, co_dinh moi ~1s.
TUY_LOAI = {
    # an_trong: an khung sau N lan doc khong thay chu | an_lech: an sau N lan chu khac han
    # bo_qua: giong cau dang hien tu muc nay -> khong dich lai | lech: duoi muc nay coi la doi chu
    "phu_de": {"an_trong": 3, "an_lech": 5, "bo_qua": 0.92, "lech": 0.8},
    "co_dinh": {"an_trong": 30, "an_lech": 10 ** 9, "bo_qua": 0.85, "lech": 0.7},
}
TEN_LOAI = {"phu_de": "phụ đề / hội thoại", "co_dinh": "chữ cố định (nhiệm vụ, menu...)"}
VONG_CO_DINH = 2  # vung co_dinh: doc lai moi 2 vong (~0.25 giay); hinh khong doi thi khong doc chu lai


def vung_moi(ma, ten, loai):
    return {"id": ma, "ten": ten, "loai": loai, "vung": None, "khung": None,
            "co_chu": 18 if loai == "phu_de" else 15, "loc_trang": loai == "phu_de"}


CAU_HINH_MAC_DINH = {
    "phien_ban": PHIEN_BAN_CAU_HINH,
    "cac_vung": [vung_moi("hoi_thoai", "Hội thoại", "phu_de"),
                 vung_moi("nhiem_vu", "Nhiệm vụ", "co_dinh")],
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
    "chu_ky_giay": 0.12,
    "che_do_hoi_thoai": "offline_claude",  # offline | offline_claude | claude | google
    "thay_bang_claude": False,      # dang hien ban offline -> doi sang ban Claude khi co
    "giong_doc": True,
    "giong": "vi-VN-NamMinhNeural",
    "toc_do_giong": 25,             # %
    "toc_tu_dong": True,            # cau dai -> tu doc nhanh hon de theo kip game
    "co_dinh_thay_claude": True,    # vung co dinh (tui do, tai lieu): doi sang ban Claude khi co
    "am_luong_giong": 1.0,
    "giam_tieng_game": 1.0,         # 1.0 giu nguyen | 0.5 | 0.25 | 0.0 tat tieng game khi doc
    "co_giao_dien": 0.85,           # co chu / nut cua bang dieu khien (0.7 / 0.85 / 1.0)
    "thu_gon": False,
    "the_dang_mo": "chinh",
    "vi_tri_bang": None,
    "tu_dong_dich": True,
    "cach_chup": "tu_dong",
    "toan_man_lien_tuc": True,
    "chu_ky_toan_man_giay": 1.0,
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
        "bat_tat_giong": "ctrl+shift+v",
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
    """Chuyen cau hinh ban cu (2 vung co dinh) sang danh sach vung tuy y, giu vung da chon."""
    if cfg.get("phien_ban", 1) < 7 and isinstance(cfg.get("vung"), dict):
        co_chu = cfg.get("co_chu")
        loc = cfg.get("loc_chu_trang") or {}
        lech = cfg.get("lech_doc") or {}
        ds = []
        for ma, ten, loai in (("hoi_thoai", "Hội thoại", "phu_de"), ("nhiem_vu", "Nhiệm vụ", "co_dinh")):
            v = vung_moi(ma, ten, loai)
            v["vung"] = cfg["vung"].get(ma)
            kd = (cfg.get("khung_dich") or {}).get(ma)
            if not kd and v["vung"]:
                x, y, w, _ = v["vung"]
                kd = [x, y + int(lech.get(ma, 0)), w]
            v["khung"] = kd
            if isinstance(co_chu, dict) and ma in co_chu:
                v["co_chu"] = int(co_chu[ma])
            elif isinstance(co_chu, (int, float)):
                v["co_chu"] = int(co_chu) + (2 if ma == "hoi_thoai" else 0)
            if ma in loc:
                v["loc_trang"] = bool(loc[ma])
            ds.append(v)
        cfg["cac_vung"] = ds
        cfg["chu_ky_giay"] = 0.12
        if cfg.get("chu_ky_toan_man_giay", 1.5) >= 1.5:
            cfg["chu_ky_toan_man_giay"] = 1.0
    if cfg.get("phien_ban", 1) < 10 and int(cfg.get("toc_do_giong", 25)) == 10:
        cfg["toc_do_giong"] = 25
    if cfg.get("phien_ban", 1) < 9 and cfg.pop("hoi_thoai_chi_google", False):
        cfg["che_do_hoi_thoai"] = "google"
    cfg.pop("hoi_thoai_chi_google", None)
    if cfg.get("phien_ban", 1) < 8 and cfg.get("chu_ky_giay", 0.12) > 0.12:
        cfg["chu_ky_giay"] = 0.12
    for cu in ("vung", "khung_dich", "co_chu", "loc_chu_trang", "lech_doc", "vi_tri_ban_dich", "so_lan_on_dinh"):
        cfg.pop(cu, None)
    if not cfg.get("cac_vung"):
        cfg["cac_vung"] = [vung_moi("hoi_thoai", "Hội thoại", "phu_de")]
    for v in cfg["cac_vung"]:
        for k, gt in vung_moi(v.get("id", "x"), v.get("ten", "Vùng"), v.get("loai", "co_dinh")).items():
            v.setdefault(k, gt)
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
        self.khung = None      # ca man hinh (chi khi can, vd F12)
        self.manh = {}         # (x, y, w, h) -> mang BGRA cua tung vung
        self.yeu_cau = []      # danh sach vung can sao chep; None = ca man hinh
        self.da_co = False
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
            if self.da_co and not self.can.is_set():
                return
            buf = getattr(frame, "frame_buffer", None)
            if buf is None:
                return
            yc = self.yeu_cau
            with self.khoa:
                if yc is None:
                    self.khung = np.array(buf, copy=True)
                    self.manh = {}
                else:  # chi sao chep dung cac vung can doc (nhe hon ca man hinh rat nhieu)
                    H, W = buf.shape[:2]
                    self.manh = {r: np.array(buf[r[1]:r[1] + r[3], r[0]:r[0] + r[2]], copy=True)
                                 for r in yc if r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= W and r[1] + r[3] <= H}
            self.da_co = True
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

    def lam_moi(self, vung=None):
        self.yeu_cau = None if vung is None else [tuple(int(a) for a in r) for r in vung]
        self.co.clear()
        self.can.set()
        self.co.wait(0.1)

    def cat(self, x, y, w, h):
        with self.khoa:
            m = self.manh.get((x, y, w, h))
            f = self.khung
        if m is not None:
            return Image.fromarray(np.ascontiguousarray(m[:, :, 2::-1]))
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

    def lam_moi(self, vung=None):
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

    def lam_moi(self, cac_vung=None):
        """cac_vung: danh sach [x, y, w, h] se doc trong vong nay; None = ca man hinh."""
        if self.nguon:
            tuong_doi = None if cac_vung is None else [
                (int(v[0]) - self.man["left"], int(v[1]) - self.man["top"], int(v[2]), int(v[3])) for v in cac_vung]
            self.nguon.lam_moi(tuong_doi)

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
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(bat_dau)) as ex:
        cac_kq = list(ex.map(lambda s: ocr_tho(anh.crop((s, 0, min(W, s + o_rong), H))), bat_dau))
    for s, kq_phan in zip(bat_dau, cac_kq):
        e = min(W, s + o_rong)
        lo = s + (o / 2 if s > 0 else 0)
        hi = e - (o / 2 if e < W else 0)
        for chu, hop in kq_phan:
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


def hop_le_toan_man(chu):
    """Loai doan rac khi doc ca man hinh (canh vat bi doc nham thanh chu)."""
    tu = re.findall(r"[A-Za-z']+", chu)
    so_chu_cai = sum(len(t) for t in tu)
    return (so_chu_cai >= 4 and any(len(t) >= 3 for t in tu)
            and so_chu_cai / max(1, len(re.sub(r"\s", "", chu))) >= 0.65)


def trung_vi_tri(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    rong = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    cao = max(0, min(ay + ah, by + bh) - max(ay, by))
    giao = rong * cao
    hop = aw * ah + bw * bh - giao
    if hop > 0 and giao / hop >= 0.3:
        return True
    tam_a = (ax + aw / 2, ay + ah / 2)
    tam_b = (bx + bw / 2, by + bh / 2)
    nguong = max(30, 1.5 * min(ah, bh))
    return abs(tam_a[0] - tam_b[0]) <= nguong * 2 and abs(tam_a[1] - tam_b[1]) <= nguong


def goi_y_doan(chu, cao_dong):
    if "\n" in chu or len(chu.split()) > 8:
        return "mô tả"
    if cao_dong >= 30:
        return "tiêu đề"
    if len(chu.split()) <= 3:
        return "nhãn/nút"
    return "dòng chữ"


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

    def dich(self, khoa, mo_hinh, van_ban, mo_ta, lich_su, ten_rieng, goi_lai=None):
        phan = [f"Loại chữ: {mo_ta}"]
        if ten_rieng:
            phan.append("Tên riêng giữ nguyên: " + ", ".join(ten_rieng))
        if lich_su:
            phan.append("Các câu ngay trước (để hiểu ngữ cảnh, KHÔNG dịch lại):\n" +
                        "\n".join(f"- {en} => {vi}" for en, vi in lich_su))
        phan.append("Dịch đoạn sau:\n<<<\n" + van_ban + "\n>>>")
        return self.goi(khoa, mo_hinh, "\n\n".join(phan), 800, goi_lai)

    def dich_nhieu(self, khoa, mo_hinh, cac_doan, ten_rieng, goi_y=None):
        phan = ["Đây là các đoạn chữ rời rạc chụp từ màn hình game (menu, bảng thông tin, mô tả, nút bấm, "
                "tên nhân vật...). Dịch TỪNG đoạn. Mỗi bản dịch bắt đầu bằng đúng số thứ tự dạng [số] như "
                "đầu vào. Không gộp, không bỏ đoạn nào. Tên riêng đứng một mình thì giữ nguyên. "
                "Chữ trong ngoặc tròn ở đầu mỗi đoạn chỉ là gợi ý loại chữ – KHÔNG đưa vào bản dịch."]
        if ten_rieng:
            phan.append("Tên riêng giữ nguyên: " + ", ".join(ten_rieng))
        phan.append("\n".join(f"[{i + 1}] " + (f"({goi_y[i]}) " if goi_y else "") + d
                               for i, d in enumerate(cac_doan)))
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
        self.lich_su = {}
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

    def dich(self, van_ban, ma_vung, mo_ta, goi_lai=None):
        """Tra ve (ban_dich, nguon, tien_usd, loi)."""
        may = "claude" if self.dung_claude() else "google"
        cu = self._tim(may, van_ban)
        if cu is not None:
            return self._sua(cu), "đã lưu", 0.0, None
        tien, loi = 0.0, None
        if may == "claude":
            try:
                thap = van_ban.lower()
                ten = [t for t in self.ten_rieng if t.lower() in thap]
                kq, vao, ra = self.claude.dich(self.khoa_api, self.cfg["mo_hinh"], van_ban, mo_ta,
                                               self.lich_su.get(ma_vung, [])[-2:], ten, goi_lai)
                tien = self.tien(vao, ra)
            except Exception as e:
                loi = self._loi_claude(e)
                may, kq = "google", google_dich(van_ban)
        else:
            kq = google_dich(van_ban)
        self._luu(may, van_ban, kq)
        with self.khoa:
            self.lich_su[ma_vung] = (self.lich_su.get(ma_vung, []) + [(van_ban, kq)])[-4:]
        return self._sua(kq), ("Claude" if may == "claude" else "Google"), tien, loi

    def luu_google(self, van_ban, vi):
        self._luu("google", van_ban, vi)

    def dich_nhieu(self, cac_doan, goi_y=None):
        may = "claude" if self.dung_claude() else "google"
        ket_qua = [self._tim(may, d) for d in cac_doan]
        thieu = [i for i, r in enumerate(ket_qua) if r is None]
        tien, loi = 0.0, None
        if thieu and may == "claude":
            try:
                kq, vao, ra = self.claude.dich_nhieu(self.khoa_api, self.cfg["mo_hinh"],
                                                     [cac_doan[i] for i in thieu], self.ten_rieng,
                                                     [goi_y[i] for i in thieu] if goi_y else None)
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


# ================================================================ Dich offline (CPU)

MO_HINH_OFFLINE = "quickmt-en-vi"
TEP_MO_HINH = ["config.json", "source_vocabulary.json", "target_vocabulary.json",
               "src.spm.model", "tgt.spm.model", "model.bin"]


class DichOffline:
    """Mo hinh quickmt-en-vi (~400 MB) chay bang CTranslate2 tren CPU – dich ~0.05-0.2 giay/cau."""

    def __init__(self):
        self.thu_muc = os.path.join(DU_LIEU, "mo_hinh", MO_HINH_OFFLINE)
        self.tr = None
        self.sp_nguon = self.sp_dich = None
        self.khoa = threading.Lock()
        self.trang_thai = "chua_tai"   # chua_tai | dang_tai | dang_nap | san_sang | loi | thieu_thu_vien
        self.thong_bao = ""

    def san_sang(self):
        return self.tr is not None

    def da_tai(self):
        return all(os.path.isfile(os.path.join(self.thu_muc, t)) and os.path.getsize(os.path.join(self.thu_muc, t)) > 0
                   for t in TEP_MO_HINH)

    @staticmethod
    def co_thu_vien():
        try:
            import ctranslate2  # noqa: F401
            import sentencepiece  # noqa: F401
            return True
        except Exception:
            return False

    def tai(self, bao):
        self.trang_thai = "dang_tai"
        os.makedirs(self.thu_muc, exist_ok=True)
        for ten in TEP_MO_HINH:
            dich = os.path.join(self.thu_muc, ten)
            if os.path.isfile(dich) and os.path.getsize(dich) > 0:
                continue
            url = f"https://huggingface.co/quickmt/{MO_HINH_OFFLINE}/resolve/main/{ten}"
            tam = dich + ".part"
            yc = urllib.request.Request(url, headers={"User-Agent": "DichGame"})
            with urllib.request.urlopen(yc, timeout=60) as r, open(tam, "wb") as f:
                tong = int(r.headers.get("Content-Length") or 0)
                da, pt_cu = 0, -1
                while True:
                    khuc = r.read(512 * 1024)
                    if not khuc:
                        break
                    f.write(khuc)
                    da += len(khuc)
                    if tong > 1_000_000:
                        pt = da * 100 // tong
                        if pt != pt_cu:
                            pt_cu = pt
                            bao(f"Đang tải mô hình dịch offline: {pt}% ({da / 1e6:.0f}/{tong / 1e6:.0f} MB)")
            os.replace(tam, dich)

    def nap(self):
        import ctranslate2
        import sentencepiece as spm
        so_luong = max(2, min(6, (os.cpu_count() or 8) // 4))  # chua CPU cho game
        tr = ctranslate2.Translator(self.thu_muc, device="cpu", compute_type="int8",
                                    inter_threads=1, intra_threads=so_luong)
        self.sp_nguon = spm.SentencePieceProcessor(model_file=os.path.join(self.thu_muc, "src.spm.model"))
        self.sp_dich = spm.SentencePieceProcessor(model_file=os.path.join(self.thu_muc, "tgt.spm.model"))
        self.tr = tr
        self.trang_thai = "san_sang"

    def _giai_ma(self, manh):
        try:
            return self.sp_dich.decode(manh)
        except Exception:
            return self.sp_dich.decode_pieces(manh)

    def dich_nhieu(self, cac_cau):
        """Dich tung dong; dong dang "Ten: loi thoai" thi giu ten, chi dich loi thoai."""
        cac_dong, vi_tri = [], []
        for i, cau in enumerate(cac_cau):
            for dong in cau.split("\n"):
                dong = dong.strip()
                m = re.match(r"^([A-Z][A-Za-z'.-]*(?: [A-Z][A-Za-z'.-]*){0,2}):\s+(.+)$", dong)
                ten, noi = (m.group(1), m.group(2)) if m else ("", dong)
                vi_tri.append((i, ten))
                cac_dong.append(noi)
        can = [k for k, d in enumerate(cac_dong) if d]
        ket = {}
        if can:
            with self.khoa:
                kq = self.tr.translate_batch([self.sp_nguon.encode(cac_dong[k], out_type=str) for k in can],
                                             beam_size=2, max_decoding_length=256)
            for k, r in zip(can, kq):
                ket[k] = self._giai_ma(r.hypotheses[0]).strip()
        ra = [[] for _ in cac_cau]
        for k, (i, ten) in enumerate(vi_tri):
            vi = ket.get(k, "")
            if vi:
                ra[i].append(f"{ten}: {vi}" if ten else vi)
        return ["\n".join(x) for x in ra]

    def dich(self, cau):
        return self.dich_nhieu([cau])[0]


# ================================================================ Giong doc (long tieng)

GIONG = {"vi-VN-NamMinhNeural": "Nam Minh (nam)", "vi-VN-HoaiMyNeural": "Hoài My (nữ)"}


class GiongDoc:
    """Doc ban dich bang giong Microsoft Edge (edge-tts), phat bang MCI cua Windows.
    Co cau moi thi ngat cau cu. Tuy chon giam tieng game (pycaw) trong luc doc."""
    BI_DANH = "dichgame_giong"

    def __init__(self, cfg, khi_loi):
        self.cfg = cfg
        self.khi_loi = khi_loi
        self.so = 0
        self.vol_goc = {}
        self.da_com = False
        self.viec = ViecNen(self._lam, khi_loi)
        self.tao_truoc = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.bo_nho = {}

    @staticmethod
    def co_thu_vien():
        try:
            import edge_tts  # noqa: F401
            return True
        except Exception:
            return False

    def doc(self, chu):
        if not self.cfg.get("giong_doc") or not chu or chu.startswith("["):
            return
        noi = "\n".join(re.sub(r"^[A-Z][A-Za-z'.-]*(?: [A-Z][A-Za-z'.-]*){0,2}:\s+", "", d)
                        for d in chu.split("\n")).strip()
        if noi:
            self.so += 1
            self.viec.gui(self.so, noi)

    def dung(self):
        self.so += 1  # vong phat dang chay se tu dung

    def _mci(self, lenh):
        buf = ctypes.create_unicode_buffer(128)
        ctypes.windll.winmm.mciSendStringW(lenh, buf, 127, None)
        return buf.value

    def _tao_am(self, chu, toc):
        import asyncio
        import edge_tts

        async def chay():
            com = edge_tts.Communicate(chu, self.cfg.get("giong", "vi-VN-NamMinhNeural"), rate=f"{toc:+d}%")
            du = bytearray()
            async for k in com.stream():
                if k.get("type") == "audio":
                    du.extend(k.get("data") or b"")
            return bytes(du)

        return asyncio.run(chay())

    def _am(self, chu, toc):
        """Am thanh cua 1 doan (co nho lai: cau lap lai doc ngay)."""
        k = (self.cfg.get("giong"), toc, chu)
        am = self.bo_nho.get(k)
        if am is None:
            am = self._tao_am(chu, toc)
            if am:
                self.bo_nho[k] = am
                if len(self.bo_nho) > 300:
                    self.bo_nho.pop(next(iter(self.bo_nho)))
        return am

    @staticmethod
    def _cat_cau(chu):
        """Cat thanh tung cau ngan de doc cau dau ngay, khong cho tao xong ca doan."""
        ra = []
        for m in re.split(r"(?<=[.!?…])\s+|\n+", chu):
            m = m.strip()
            if not m:
                continue
            if ra and len(ra[-1]) < 25:
                ra[-1] += " " + m
            else:
                ra.append(m)
        return ra or [chu]

    def _toc(self, chu):
        toc = int(self.cfg.get("toc_do_giong", 25))
        if self.cfg.get("toc_tu_dong", True):
            toc += min(30, max(0, (len(chu) - 60) // 4))  # cau dai -> doc nhanh hon
        return max(-30, min(80, toc))

    def _lam(self, so, chu):
        if so != self.so:
            return
        toc = self._toc(chu)
        cac_cau = self._cat_cau(chu)
        sau = self.tao_truoc.submit(self._am, cac_cau[0], toc)
        da_giam = False
        try:
            for i in range(len(cac_cau)):
                am = sau.result()
                if i + 1 < len(cac_cau):  # tao truoc cau tiep theo trong luc doc cau nay
                    sau = self.tao_truoc.submit(self._am, cac_cau[i + 1], toc)
                if so != self.so:
                    return
                if not am:
                    continue
                if not da_giam:
                    self._giam_game()
                    da_giam = True
                self._phat(am, so, i)
                if so != self.so:
                    return
        finally:
            if self.viec.viec is None:  # khong con cau nao cho doc -> tra lai tieng game
                self._tra_game()

    def _phat(self, am, so, i):
        tep = os.path.join(tempfile.gettempdir(), f"dichgame_giong_{(so * 7 + i) % 6}.mp3")
        self._mci(f"close {self.BI_DANH}")
        with open(tep, "wb") as f:
            f.write(am)
        self._mci(f'open "{tep}" type mpegvideo alias {self.BI_DANH}')
        am_luong = max(0.0, min(1.0, float(self.cfg.get("am_luong_giong", 1.0))))
        self._mci(f"setaudio {self.BI_DANH} volume to {int(am_luong * 1000)}")
        self._mci(f"play {self.BI_DANH}")
        try:
            time.sleep(0.03)
            while so == self.so and self._mci(f"status {self.BI_DANH} mode") == "playing":
                time.sleep(0.03)
        finally:
            self._mci(f"stop {self.BI_DANH}")
            self._mci(f"close {self.BI_DANH}")

    def _giam_game(self):
        muc = float(self.cfg.get("giam_tieng_game", 1.0))
        if muc >= 0.999 or self.vol_goc:
            return
        try:
            if not self.da_com:
                import comtypes
                comtypes.CoInitialize()
                self.da_com = True
            from pycaw.pycaw import AudioUtilities
            for phien in AudioUtilities.GetAllSessions():
                tien_trinh = phien.Process
                if tien_trinh is None or tien_trinh.pid == os.getpid():
                    continue
                v = phien.SimpleAudioVolume
                goc = v.GetMasterVolume()
                self.vol_goc[tien_trinh.pid] = (v, goc)
                v.SetMasterVolume(goc * muc, None)
        except Exception:
            pass

    def _tra_game(self):
        for v, goc in list(self.vol_goc.values()):
            try:
                v.SetMasterVolume(goc, None)
            except Exception:
                pass
        self.vol_goc = {}


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
        try:
            d = _tai_json(f"https://api.github.com/repos/{repo}/releases/latest")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(f"kho {repo} chưa có bản phát hành nào (Release) – hãy đăng bản đầu tiên")
            raise
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


def moi_truong_sach():
    """Bien moi truong cho app moi: bo thong tin thu muc tam cua app cu (PyInstaller),
    neu khong app moi se tim python312.dll trong thu muc tam da bi xoa va bao loi."""
    mei = getattr(sys, "_MEIPASS", "") or ""
    env = {k: v for k, v in os.environ.items()
           if not (k.upper().startswith("_PYI_") or k.upper().startswith("_MEIPASS")
                   or k.upper() in ("TCL_LIBRARY", "TK_LIBRARY", "PYTHONHOME", "PYTHONPATH"))}
    if mei and "PATH" in env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                      if p and not p.lower().startswith(mei.lower()))
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


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
            f.write("@echo off\r\nchcp 65001 >nul\r\n"
                    "set _PYI_APPLICATION_HOME_DIR=\r\nset _PYI_ARCHIVE_FILE=\r\nset _PYI_PARENT_PROCESS_LEVEL=\r\n"
                    "set _PYI_SPLASH_IPC=\r\nset _MEIPASS2=\r\nset TCL_LIBRARY=\r\nset TK_LIBRARY=\r\n"
                    "set PYINSTALLER_RESET_ENVIRONMENT=1\r\n"
                    "ping 127.0.0.1 -n 4 >nul\r\n:lap\r\n"
                    f'move /y "{moi}" "{hien}" >nul 2>nul\r\n'
                    "if errorlevel 1 (ping 127.0.0.1 -n 2 >nul & goto lap)\r\n"
                    f'start "" "{hien}"\r\ndel "%~f0"\r\n')
        subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000, close_fds=True, env=moi_truong_sach())
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
    subprocess.Popen([sys.executable, os.path.join(THU_MUC_APP, "dich_game.py")], cwd=THU_MUC_APP,
                     env=moi_truong_sach())
    return True


# ================================================================ Khung hien ban dich

class KhungBanDich:
    LE = 10

    def __init__(self, root, ma, khi_doi):
        self.ma = ma
        self.ten = ""
        self.can_giua = True
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
        font = ("Segoe UI", self.co_chu, "bold")
        rong_chu = max(60, self.w - 2 * le)
        x0, neo, can = (self.w // 2, "n", "center") if self.can_giua else (le, "nw", "left")
        chu = self.van_ban
        y0 = le
        if self.dang_chinh:
            nen = "#2b2b33"
            cv.configure(bg=nen)
            cv.create_text(le, 6, text=f"■ {self.ten}", font=("Segoe UI", 9, "bold"), fill="#ffcc33", anchor="nw")
            y0 = 26
            if not chu:
                chu = "Kéo để di chuyển • kéo góc ◢ đổi độ rộng • lăn chuột đổi cỡ chữ"
        else:
            nen = MAU_TRONG if self.kieu == "phu_de" else MAU_NEN
            cv.configure(bg=nen)
        day = self.vien + (1 if self.co_chu >= 26 and self.vien else 0) if nen == MAU_TRONG else 0
        ve_chu_vien(cv, x0, y0, chu, font, rong_chu, neo, can, day)
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

    def hien(self, van_ban, ten, can_giua, x, y, w, co_chu, kieu, do_dam, vien):
        trang_thai = (van_ban, ten, can_giua, int(x), int(y), int(w), int(co_chu), kieu, do_dam, int(vien),
                      self.dang_chinh)
        if trang_thai == self._ve_cuoi and self.dang_hien:
            return
        self._ve_cuoi = trang_thai
        self.van_ban, self.ten, self.can_giua = van_ban, ten, can_giua
        self.x, self.y, self.w = int(x), int(y), int(w)
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

    def huy(self):
        try:
            self.win.destroy()
        except Exception:
            pass

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
        self.dung = False
        threading.Thread(target=self._chay, daemon=True).start()

    def gui(self, *tham_so):
        with self.dk:
            self.viec = tham_so
            self.dk.notify()

    def _chay(self):
        while not self.dung:
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
        self.t_doi_chu = 0.0
        self.t_doc = 0.0


# ================================================================ App chinh

class App:
    def __init__(self):
        self.cfg = nang_cap_cau_hinh(tron(CAU_HINH_MAC_DINH, doc_json(FILE_CAU_HINH, {})))
        self.root = tk.Tk()
        self.root.title(f"Dịch Game v{APP_VERSION}")
        self.root.configure(bg=UI_NEN)
        self.root.resizable(False, False)
        bieu_tuong = os.path.join(getattr(sys, "_MEIPASS", THU_MUC_APP), "icon.ico")
        try:
            self.root.iconbitmap(bieu_tuong)
        except Exception:
            pass
        self.q = queue.Queue()
        self.bo_dich = BoDich(self.cfg)
        self.man = man_hinh_chinh()
        self.khung = {}
        self.trang_thai = {}
        self.van_ban = {}
        self.viec_dich = {}
        self.viec_doc = {}
        self.anh_xem = {}
        self.lbl_xem = {}
        self.toan_man = LopToanManHinh(self.root, self.man)
        self.vung_dang_sua = self.cfg["cac_vung"][0]["id"]
        self.hien_ban_dich = True
        self.dang_chon = False
        self.dang_chinh_khung = False
        self.xem_vung = False
        self.toan_man_bat = False
        self.mot_lan_hien = False
        self.lan_toan_man = 0.0
        self.doan_tm = []
        self.khoa_tm = threading.Lock()
        self.ban_moi = None
        self.xem_thu_den = 0.0
        self.tam_dung = threading.Event()
        self.ep_dich = threading.Event()
        self.can_toan_man = threading.Event()
        self.dung = threading.Event()
        self.viec_toan_man = ViecNen(self._xu_ly_toan_man, self._loi_nen)
        self.offline = DichOffline()
        self.giong = GiongDoc(self.cfg, self._loi_giong)
        self.nen_claude = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        self._giao_dien()
        vt = self.cfg.get("vi_tri_bang")
        if vt and -50 <= vt[0] < self.man["width"] - 100 and -10 <= vt[1] < self.man["height"] - 100:
            self.root.geometry(f"+{int(vt[0])}+{int(vt[1])}")
        self._dang_ky_phim()
        self.root.after(300, lambda: an_khoi_anh_chup(self.root))
        threading.Thread(target=self._khoi_dong_offline, daemon=True).start()
        threading.Thread(target=self._vong_lap, daemon=True).start()
        for v in self._ds():
            if v["loai"] == "phu_de":
                self._viec_dich(v["id"]).gui(None, "")  # mo san ket noi toi Claude
        self.root.after(50, self._xu_ly_hang_doi)
        self.root.after(2000, self._giu_tren_cung)
        self.root.after(30000, self._luu_dinh_ky)
        if self.cfg.get("tu_kiem_tra_cap_nhat"):
            self.root.after(4000, lambda: self._kiem_tra_cap_nhat(im_lang=True))
        self.root.protocol("WM_DELETE_WINDOW", self.thoat)

    # ------------------------------------------------------------ du lieu vung
    def _ds(self):
        return self.cfg["cac_vung"]

    def _v(self, ma):
        for v in self.cfg["cac_vung"]:
            if v["id"] == ma:
                return v
        return None

    def _st(self, ma):
        if ma not in self.trang_thai:
            self.trang_thai[ma] = TrangThai()
        return self.trang_thai[ma]

    def _khung(self, ma):
        if ma not in self.khung:
            self.khung[ma] = KhungBanDich(self.root, ma, self._khung_doi_bang_chuot)
        return self.khung[ma]

    def _viec_dich(self, ma):
        if ma not in self.viec_dich:
            self.viec_dich[ma] = ViecNen(self._thuc_hien_dich, self._loi_nen)
        return self.viec_dich[ma]

    def _viec_doc(self, ma):
        if ma not in self.viec_doc:
            self.viec_doc[ma] = ViecNen(self._xu_ly_vung, self._loi_nen)
        return self.viec_doc[ma]

    def _kd(self, v):
        if v.get("khung"):
            return list(v["khung"])
        if v.get("vung"):
            return [v["vung"][0], v["vung"][1], v["vung"][2]]
        return None

    def _ma_theo_phim(self, tien_to):
        ds = self._ds()
        i = 0 if tien_to == "hoi_thoai" else 1
        return ds[i]["id"] if i < len(ds) else None

    # ------------------------------------------------------------ phan tu giao dien
    def _nut(self, cha, chu, lenh=None, kieu="thuong", rong=None, cmd=None, nho=False):
        mau = {"thuong": (UI_O, UI_CHU, UI_O_HOVER), "chinh": (UI_DO, "#ffffff", UI_DO_HOVER)}[kieu]
        b = tk.Button(cha, text=chu, command=cmd or (lambda: self.lenh(lenh)), bg=mau[0], fg=mau[1],
                      activebackground=mau[2], activeforeground=mau[1], relief="flat", bd=0,
                      highlightthickness=0, padx=self._p(8 if nho else 12), pady=self._p(3 if nho else 6),
                      cursor="hand2", font=self._f(9) if nho else self._f(10))
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

    def _f(self, co, kieu=""):
        ti_le = float(self.cfg.get("co_giao_dien", 0.85))
        co = max(6, round(co * ti_le))
        return ("Segoe UI", co, kieu) if kieu else ("Segoe UI", co)

    def _p(self, so):
        return max(1, round(so * float(self.cfg.get("co_giao_dien", 0.85))))

    def _the(self, cha, tieu_de):
        ngoai = tk.Frame(cha, bg=UI_THE, padx=self._p(14), pady=self._p(10))
        ngoai.pack(fill="x", pady=(0, self._p(10)))
        tk.Label(ngoai, text=tieu_de.upper(), bg=UI_THE, fg=UI_VANG,
                 font=self._f(9, "bold")).pack(anchor="w", pady=(0, 6))
        return ngoai

    def _hang(self, cha, pady=3):
        h = tk.Frame(cha, bg=cha["bg"])
        h.pack(fill="x", pady=pady)
        return h

    def _nhan(self, cha, chu="", mau=UI_CHU, font=None, **kw):
        return tk.Label(cha, text=chu, bg=cha["bg"], fg=mau, font=font or self._f(10), **kw)

    def _o_chon(self, cha, chu, bien, lenh):
        return tk.Checkbutton(cha, text=chu, variable=bien, command=lenh, bg=cha["bg"], fg=UI_CHU,
                              selectcolor=UI_O, activebackground=cha["bg"], activeforeground=UI_CHU,
                              font=self._f(9), bd=0, highlightthickness=0, cursor="hand2")

    def _cap(self, cha, lua_chon, lenh_cua):
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
        goc = tk.Frame(self.root, bg=UI_NEN, padx=self._p(14), pady=self._p(12))
        goc.pack(fill="both", expand=True)
        self.goc = goc
        rong_chu = self._p(470)

        dau = tk.Frame(goc, bg=UI_NEN)
        dau.pack(fill="x", pady=(0, self._p(8)))
        tk.Label(dau, text="DỊCH GAME", bg=UI_NEN, fg=UI_CHU, font=self._f(16, "bold")).pack(side="left")
        tk.Label(dau, text=f"  v{APP_VERSION}", bg=UI_NEN, fg=UI_PHU, font=self._f(9)).pack(
            side="left", pady=(self._p(6), 0))
        self.nut_thu_gon = self._nut(dau, "", "thu_gon", nho=True)
        self.nut_thu_gon.pack(side="right")

        tt = tk.Frame(goc, bg=UI_THE, padx=self._p(10), pady=self._p(5))
        tt.pack(fill="x", pady=(0, self._p(8)))
        self.lbl_tt = tk.Label(tt, text="Đang khởi động...", bg=UI_THE, fg=UI_PHU, font=self._f(9),
                               wraplength=rong_chu, justify="left", anchor="w")
        self.lbl_tt.pack(fill="x")
        self.lbl_tg = tk.Label(tt, text="", bg=UI_THE, fg=UI_PHU, font=self._f(8),
                               wraplength=rong_chu, justify="left", anchor="w")
        self.lbl_tg.pack(fill="x")

        # --- thanh thu gon (chi hien khi bam Thu gon)
        self.khung_mini = tk.Frame(goc, bg=UI_NEN)
        self.nut_tu_dong_mini = self._nut(self.khung_mini, "", "bat_tat_tu_dong", nho=True)
        self.nut_tu_dong_mini.pack(side="left", padx=(0, 3))
        self._nut(self.khung_mini, f"Ẩn/Hiện ({p['an_hien'].upper()})", "an_hien", nho=True).pack(
            side="left", padx=(0, 3))
        self.nut_toan_man_mini = self._nut(self.khung_mini, "", "dich_man_hinh", nho=True)
        self.nut_toan_man_mini.pack(side="left", padx=(0, 3))
        self.nut_giong_mini = self._nut(self.khung_mini, "", "giong_bat_tat", nho=True)
        self.nut_giong_mini.pack(side="left", padx=(0, 3))
        self._nut(self.khung_mini, "Thoát", kieu="chinh", cmd=self.thoat, nho=True).pack(side="right")

        # --- thanh chon the
        self.thanh_the = tk.Frame(goc, bg=UI_NEN)
        self.nut_the = {}
        for ma, ten in (("chinh", "Chính"), ("khung", "Khung dịch"), ("cai_dat", "Cài đặt")):
            b = self._nut(self.thanh_the, ten, cmd=lambda m=ma: self.lenh("the:" + m))
            b.pack(side="left", padx=(0, self._p(3)), expand=True, fill="x")
            self.nut_the[ma] = b
        self.noi_dung = tk.Frame(goc, bg=UI_NEN)
        self.trang = {m: tk.Frame(self.noi_dung, bg=UI_NEN) for m in ("chinh", "khung", "cai_dat")}
        trai = self.trang["cai_dat"]
        chinh = self.trang["chinh"]
        phai = self.trang["khung"]

        # ---------- Dich AI
        t = self._the(trai, "Dịch bằng AI")
        self.lbl_khoa = self._nhan(t, font=self._f(9))
        self.lbl_khoa.pack(anchor="w")
        h = self._hang(t)
        self.o_khoa = tk.Entry(h, show="•", width=26, bg=UI_O, fg=UI_CHU, insertbackground=UI_CHU,
                               relief="flat", font=self._f(10))
        self.o_khoa.pack(side="left", ipady=4, padx=(0, 6))
        self._nut(h, "Lưu mã", cmd=self._luu_khoa, nho=True).pack(side="left", padx=(0, 2))
        self._nut(h, "Thử", cmd=self._thu_claude, nho=True).pack(side="left")
        h = self._hang(t)
        self._nhan(h, "Bộ dịch:", UI_PHU, self._f(9)).pack(side="left", padx=(0, 8))
        khung, self.nut_bo_dich = self._cap(h, [("claude", "Claude AI"), ("google", "Google (miễn phí)")],
                                            lambda g: self.lenh("bo_dich_" + g))
        khung.pack(side="left")
        self.lbl_tien = self._nhan(t, mau=UI_PHU, font=self._f(9))
        self.lbl_tien.pack(anchor="w", pady=(4, 0))
        self.bien_google = tk.BooleanVar(value=bool(self.cfg["hien_google_truoc"]))
        self._o_chon(t, "Hiện bản Google trước trong lúc chờ Claude (nhanh hơn)", self.bien_google,
                     self._doi_google_truoc).pack(anchor="w", pady=(4, 0))

        t = self._the(trai, "Dịch offline (chạy bằng CPU)")
        self.lbl_offline = self._nhan(t, "", UI_PHU, self._f(9), wraplength=self._p(430), justify="left")
        self.lbl_offline.pack(anchor="w")
        self.nut_tai_mo_hinh = self._nut(t, "Tải mô hình quickmt-en-vi (~400 MB)", cmd=self._tai_mo_hinh, nho=True)
        self.nut_tai_mo_hinh.pack(anchor="w", pady=(4, 2))
        self._nhan(t, "Hội thoại dịch bằng:", UI_PHU, self._f(9)).pack(anchor="w", pady=(4, 0))
        h = self._hang(t)
        khung, self.nut_che_do = self._cap(h, [("offline", "Offline"), ("offline_claude", "Offline + Claude"),
                                               ("claude", "Claude"), ("google", "Google")],
                                           lambda g: self.lenh("che_do:" + g))
        khung.pack(side="left")
        self.bien_thay = tk.BooleanVar(value=bool(self.cfg.get("thay_bang_claude")))
        self._o_chon(t, "Hội thoại: đổi sang bản Claude khi có (chữ sẽ đổi 1 lần)", self.bien_thay,
                     self._doi_thay).pack(anchor="w", pady=(4, 0))
        self.bien_thay_cd = tk.BooleanVar(value=bool(self.cfg.get("co_dinh_thay_claude", True)))
        self._o_chon(t, "Vùng cố định (túi đồ, tài liệu): đổi sang bản Claude khi có", self.bien_thay_cd,
                     self._doi_thay_cd).pack(anchor="w")

        # ---------- Vung dich (danh sach)
        t = self._the(chinh, "Vùng dịch (app tự nhớ)")
        self.khung_ds_vung = tk.Frame(t, bg=UI_THE)
        self.khung_ds_vung.pack(fill="x")
        self.nut_them_vung = self._nut(t, "+ Thêm vùng", cmd=self._them_vung, nho=True)
        self.nut_them_vung.pack(anchor="w", pady=(6, 0))

        # ---------- Dieu khien
        t = self._the(chinh, "Điều khiển")
        self.nut_tu_dong = self._nut(t, "", "bat_tat_tu_dong")
        self.nut_tu_dong.pack(fill="x", pady=2)
        h = self._hang(t)
        self._nut(h, f"Dịch ngay ({p['dich_ngay'].upper()})", "dich_ngay").pack(side="left", expand=True,
                                                                                fill="x", padx=(0, 4))
        self._nut(h, f"Ẩn / Hiện ({p['an_hien'].upper()})", "an_hien").pack(side="left", expand=True, fill="x")
        self.nut_toan_man = self._nut(t, "", "dich_man_hinh")
        self.nut_toan_man.pack(fill="x", pady=(6, 2))
        h = self._hang(t)
        self._nhan(h, "Kiểu dịch cả màn hình:", UI_PHU, self._f(9)).pack(side="left", padx=(0, 8))
        khung, self.nut_kieu_toan_man = self._cap(h, [("lien_tuc", "Liên tục"), ("mot_lan", "1 lần")],
                                                  lambda g: self.lenh("toan_man_" + g))
        khung.pack(side="left")

        # ---------- Khung dich
        t = self._the(phai, "Khung dịch")
        h = self._hang(t)
        self._nhan(h, "Kiểu:", UI_PHU, self._f(9), width=9, anchor="w").pack(side="left")
        khung, self.nut_kieu = self._cap(h, [("phu_de", "Phụ đề (chỉ chữ)"), ("khung", "Khung nền tối")],
                                         lambda g: self.lenh("kieu_" + g))
        khung.pack(side="left")
        self.nut_chinh = self._nut(t, "", "chinh_khung")
        self.nut_chinh.pack(fill="x", pady=(6, 4))

        def cong_tru(cha, ten, tru, cong, rong_ten=12):
            h = self._hang(cha, 2)
            nhan = self._nhan(h, ten, UI_PHU, self._f(9), width=rong_ten, anchor="w")
            nhan.pack(side="left")
            self._nut(h, "−", cmd=lambda: self.lenh(tru), nho=True, rong=2).pack(side="left")
            gt = self._nhan(h, "", UI_CHU, self._f(10, "bold"), width=6)
            gt.pack(side="left")
            self._nut(h, "+", cmd=lambda: self.lenh(cong), nho=True, rong=2).pack(side="left")
            return nhan, gt

        self.lbl_dam_ten, self.lbl_dam = cong_tru(t, "", "giam_do_dam", "tang_do_dam")
        _, self.lbl_vien = cong_tru(t, "Viền chữ:", "giam_vien", "tang_vien")

        tk.Frame(t, bg=UI_O, height=1).pack(fill="x", pady=8)
        h = self._hang(t)
        self._nhan(h, "Chỉnh khung của:", UI_PHU, self._f(9)).pack(side="left", padx=(0, 6))
        self.khung_chon_sua = tk.Frame(h, bg=UI_THE)
        self.khung_chon_sua.pack(side="left")
        h = self._hang(t, 2)
        self._nhan(h, "Vị trí:", UI_PHU, self._f(9), width=12, anchor="w").pack(side="left")
        for chu, hanh in (("◀", "trai"), ("▲", "len"), ("▼", "xuong"), ("▶", "phai")):
            self._nut(h, chu, cmd=lambda hh=hanh: self.lenh(f"khung:{self.vung_dang_sua}:{hh}"),
                      nho=True, rong=2).pack(side="left", padx=1)
        _, self.lbl_co_chu = cong_tru(t, "Cỡ chữ:", "co_chu_giam", "co_chu_tang")
        _, self.lbl_do_rong = cong_tru(t, "Độ rộng:", "rong_giam", "rong_tang")
        self._nhan(t, "Phím: Ctrl+mũi tên dời khung vùng 1 • Ctrl+Shift+mũi tên dời khung vùng 2",
                   UI_PHU, self._f(8), wraplength=self._p(430), justify="left").pack(anchor="w", pady=(4, 0))

        # ---------- Giong doc (the Chinh)
        t = self._the(chinh, "Giọng đọc (lồng tiếng)")
        self.nut_giong = self._nut(t, "", "giong_bat_tat")
        self.nut_giong.pack(fill="x", pady=2)
        h = self._hang(t)
        self._nhan(h, "Giọng:", UI_PHU, self._f(9), width=12, anchor="w").pack(side="left")
        khung, self.nut_chon_giong = self._cap(h, list(GIONG.items()), lambda g: self.lenh("giong:" + g))
        khung.pack(side="left")
        _, self.lbl_toc_giong = cong_tru(t, "Tốc độ đọc:", "toc_giong_giam", "toc_giong_tang")
        _, self.lbl_am_giong = cong_tru(t, "Âm lượng giọng:", "am_giong_giam", "am_giong_tang")
        self.bien_toc_tu_dong = tk.BooleanVar(value=bool(self.cfg.get("toc_tu_dong", True)))
        self._o_chon(t, "Câu dài thì tự đọc nhanh hơn (theo kịp game)", self.bien_toc_tu_dong,
                     self._doi_toc_tu_dong).pack(anchor="w")
        h = self._hang(t)
        self._nhan(h, "Tiếng game khi đọc:", UI_PHU, self._f(9)).pack(side="left", padx=(0, 6))
        khung, self.nut_giam_game = self._cap(h, [(1.0, "Giữ nguyên"), (0.5, "50%"), (0.25, "25%"), (0.0, "Tắt")],
                                              lambda g: self.lenh(f"giam_game:{g}"))
        khung.pack(side="left")

        # ---------- Xem vung chup
        t = self._the(trai, "App đang nhìn thấy gì")
        self.nut_xem = self._nut(t, "", "xem_vung")
        self.nut_xem.pack(fill="x", pady=(0, 4))
        self.khung_xem = tk.Frame(t, bg=UI_THE)
        self.khung_xem.pack(fill="x")

        # ---------- He thong
        t = self._the(trai, "Hệ thống")
        h = self._hang(t)
        self._nhan(h, "Cỡ giao diện:", UI_PHU, self._f(9)).pack(side="left", padx=(0, 6))
        khung, self.nut_co_gd = self._cap(h, [(0.7, "70%"), (0.85, "85%"), (1.0, "100%")],
                                          lambda g: self.lenh(f"co_gd:{g}"))
        khung.pack(side="left")
        h = self._hang(t)
        self.nut_cach_chup = self._nut(h, "", "doi_cach_chup", nho=True)
        self.nut_cach_chup.pack(side="left", padx=(0, 4))
        self._nut(h, "Thư mục dữ liệu", cmd=lambda: os.startfile(DU_LIEU), nho=True).pack(side="left")
        h = self._hang(t)
        self.nut_cap_nhat = self._nut(h, "Kiểm tra cập nhật", cmd=self._kiem_tra_cap_nhat, nho=True)
        self.nut_cap_nhat.pack(side="left", padx=(0, 4))
        self._nut(h, "Thoát", kieu="chinh", cmd=self.thoat, nho=True).pack(side="right")

        self._ve_ds_vung()
        self._sap_xep_giao_dien()
        self._cap_nhat_nut()

    def _sap_xep_giao_dien(self):
        """Hien the dang chon, hoac thanh thu gon."""
        for w in (self.khung_mini, self.thanh_the, self.noi_dung):
            w.pack_forget()
        if self.cfg.get("thu_gon"):
            self.lbl_tg.pack_forget()
            self.khung_mini.pack(fill="x")
        else:
            self.lbl_tg.pack(fill="x")
            self.thanh_the.pack(fill="x", pady=(0, self._p(8)))
            self.noi_dung.pack(fill="both", expand=True)
            the = self.cfg.get("the_dang_mo", "chinh")
            if the not in self.trang:
                the = "chinh"
            for m, khung in self.trang.items():
                if m == the:
                    khung.pack(fill="both", expand=True)
                else:
                    khung.pack_forget()

    def _ve_lai_giao_dien(self):
        chu_tt = self.lbl_tt.cget("text")
        mau_tt = self.lbl_tt.cget("fg")
        self.goc.destroy()
        self._giao_dien()
        self.lbl_tt.config(text=chu_tt, fg=mau_tt)

    def _ve_ds_vung(self):
        """Ve lai danh sach vung, nut chon vung de chinh khung va o xem truoc."""
        ds = self._ds()
        if not self._v(self.vung_dang_sua):
            self.vung_dang_sua = ds[0]["id"]
        for w in self.khung_ds_vung.winfo_children():
            w.destroy()
        self.lbl_vung = {}
        self.nut_loc = {}
        for i, v in enumerate(ds):
            h = self._hang(self.khung_ds_vung, 3)
            phim = ""
            if i < 2:
                phim = f" ({self.cfg['phim_tat']['chon_hoi_thoai' if i == 0 else 'chon_nhiem_vu'].upper()})"
            self._nhan(h, v["ten"], font=self._f(10, "bold"), width=10, anchor="w").pack(side="left")
            self.lbl_vung[v["id"]] = self._nhan(h, "", UI_PHU, self._f(8), width=17, anchor="w")
            self.lbl_vung[v["id"]].pack(side="left")
            self._nut(h, "✕", cmd=lambda m=v["id"]: self._xoa_vung(m), nho=True, rong=2).pack(side="right")
            self._nut(h, "Chọn" + phim, cmd=lambda m=v["id"]: self.chon_vung(m), nho=True).pack(side="right",
                                                                                                padx=2)
            b = self._nut(h, "", cmd=lambda m=v["id"]: self.lenh(f"loc:{m}"), nho=True)
            b.pack(side="right", padx=2)
            self.nut_loc[v["id"]] = b
        self.nut_them_vung.config(state="normal" if len(ds) < SO_VUNG_TOI_DA else "disabled")

        for w in self.khung_chon_sua.winfo_children():
            w.destroy()
        self.nut_sua = {}
        for v in ds:
            b = self._nut(self.khung_chon_sua, v["ten"], cmd=lambda m=v["id"]: self.lenh(f"sua:{m}"), nho=True)
            b.pack(side="left", padx=(0, 2))
            self.nut_sua[v["id"]] = b

        for w in self.khung_xem.winfo_children():
            w.destroy()
        self.lbl_xem, self.anh_xem = {}, {}
        for v in ds:
            self._nhan(self.khung_xem, v["ten"], UI_PHU, self._f(8)).pack(anchor="w")
            self.lbl_xem[v["id"]] = tk.Label(self.khung_xem, text="(tắt)", fg=UI_PHU, bg="#0d0e12",
                                             width=48, height=2)
            self.lbl_xem[v["id"]].pack(pady=(0, 3), anchor="w")
        self._cap_nhat_nut()

    def _bao(self, chu, loai="ok"):
        mau = {"ok": UI_XANH, "loi": UI_LOI, "canh_bao": UI_VANG, "phu": UI_PHU}.get(loai, UI_PHU)
        self.lbl_tt.config(text=chu, fg=mau)

    def _cap_nhat_nut(self):
        c, p = self.cfg, self.cfg["phim_tat"]
        self.nut_tu_dong.config(text=f"Tự động dịch: {'BẬT' if c['tu_dong_dich'] else 'TẮT'}  "
                                     f"({p['bat_tat_tu_dong'].upper()})")
        self._dat_mau_nut(self.nut_tu_dong, c["tu_dong_dich"])
        self.nut_tu_dong_mini.config(text=f"Tự động: {'BẬT' if c['tu_dong_dich'] else 'TẮT'}")
        self._dat_mau_nut(self.nut_tu_dong_mini, c["tu_dong_dich"])
        self.nut_toan_man_mini.config(text=f"Cả màn hình ({p['dich_man_hinh'].upper()})")
        self._dat_mau_nut(self.nut_toan_man_mini, self.toan_man_bat or self.mot_lan_hien)
        self.nut_thu_gon.config(text="▼ Mở rộng" if c.get("thu_gon") else "▲ Thu gọn")
        gd = bool(c.get("giong_doc"))
        self.nut_giong.config(text=f"Giọng đọc: {'BẬT' if gd else 'TẮT'}  ({p['bat_tat_giong'].upper()})")
        self._dat_mau_nut(self.nut_giong, gd)
        self.nut_giong_mini.config(text=f"Giọng: {'BẬT' if gd else 'TẮT'}")
        self._dat_mau_nut(self.nut_giong_mini, gd)
        for g, b in self.nut_chon_giong.items():
            self._dat_mau_nut(b, c.get("giong") == g)
        self.lbl_toc_giong.config(text=f"{int(c.get('toc_do_giong', 25)):+d}%")
        self.lbl_am_giong.config(text=f"{round(float(c.get('am_luong_giong', 1.0)) * 100)}%")
        for g, b in self.nut_giam_game.items():
            self._dat_mau_nut(b, abs(g - float(c.get("giam_tieng_game", 1.0))) < 0.01)
        for g, b in self.nut_che_do.items():
            self._dat_mau_nut(b, c.get("che_do_hoi_thoai") == g)
        o = self.offline
        chu_o = {"san_sang": ("✓ Sẵn sàng – hội thoại được dịch ngay trên máy bằng CPU, không cần mạng.", UI_XANH),
                 "dang_tai": (o.thong_bao or "Đang tải mô hình...", UI_VANG),
                 "dang_nap": ("Đang nạp mô hình vào bộ nhớ...", UI_VANG),
                 "chua_tai": ("Chưa tải mô hình (khoảng 400 MB, chỉ tải 1 lần).", UI_VANG),
                 "loi": (f"Lỗi: {o.thong_bao}", UI_LOI),
                 "thieu_thu_vien": ("Thiếu thư viện ctranslate2 / sentencepiece – hãy cập nhật lên bản exe mới.",
                                    UI_LOI)}.get(o.trang_thai, ("", UI_PHU))
        self.lbl_offline.config(text=chu_o[0], fg=chu_o[1])
        self.nut_tai_mo_hinh.config(state="disabled" if o.trang_thai in ("dang_tai", "dang_nap", "san_sang")
                                    else "normal")
        for m, b in self.nut_the.items():
            self._dat_mau_nut(b, m == c.get("the_dang_mo", "chinh"))
        for g, b in self.nut_co_gd.items():
            self._dat_mau_nut(b, abs(g - float(c.get("co_giao_dien", 0.85))) < 0.01)
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
        for v in self._ds():
            lbl = self.lbl_vung.get(v["id"])
            if lbl:
                vv = v.get("vung")
                lbl.config(text=(f"{'phụ đề' if v['loai'] == 'phu_de' else 'cố định'} • "
                                 + (f"đã nhớ ✓ {vv[2]}×{vv[3]}" if vv else "chưa chọn")),
                           fg=UI_XANH if vv else UI_VANG)
            b = self.nut_loc.get(v["id"])
            if b:
                b.config(text="Lọc trắng ✓" if v.get("loc_trang") else "Lọc trắng ✗")
                self._dat_mau_nut(b, bool(v.get("loc_trang")))
            b = self.nut_sua.get(v["id"])
            if b:
                self._dat_mau_nut(b, v["id"] == self.vung_dang_sua)
        vs = self._v(self.vung_dang_sua)
        kd = self._kd(vs) if vs else None
        self.lbl_co_chu.config(text=str(vs["co_chu"]) if vs else "-")
        self.lbl_do_rong.config(text=str(kd[2]) if kd else "-")
        if c["toan_man_lien_tuc"]:
            self.nut_toan_man.config(text=f"Dịch cả màn hình: {'BẬT' if self.toan_man_bat else 'TẮT'}  "
                                          f"({p['dich_man_hinh'].upper()})")
        else:
            self.nut_toan_man.config(text=f"Dịch cả màn hình 1 lần  ({p['dich_man_hinh'].upper()})")
        self._dat_mau_nut(self.nut_toan_man, self.toan_man_bat or self.mot_lan_hien)
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

    def _doi_toc_tu_dong(self):
        self.cfg["toc_tu_dong"] = bool(self.bien_toc_tu_dong.get())
        self._luu_cau_hinh()

    def _doi_thay_cd(self):
        self.cfg["co_dinh_thay_claude"] = bool(self.bien_thay_cd.get())
        self._luu_cau_hinh()

    def _doi_thay(self):
        self.cfg["thay_bang_claude"] = bool(self.bien_thay.get())
        self._luu_cau_hinh()

    def _loi_giong(self, e):
        self.q.put(("trang_thai", f"Giọng đọc lỗi: {type(e).__name__}: {str(e)[:100]}"))

    # ------------------------------------------------------------ dich offline
    def _khoi_dong_offline(self, tai=False):
        o = self.offline
        if o.san_sang() or o.trang_thai in ("dang_tai", "dang_nap"):
            return
        if not o.co_thu_vien():
            o.trang_thai = "thieu_thu_vien"
            self.q.put(("offline",))
            return
        try:
            if not o.da_tai():
                if not tai and not str(self.cfg.get("che_do_hoi_thoai", "")).startswith("offline"):
                    o.trang_thai = "chua_tai"
                    self.q.put(("offline",))
                    return

                def bao(chu):
                    o.thong_bao = chu
                    self.q.put(("offline",))

                o.tai(bao)
            o.trang_thai = "dang_nap"
            self.q.put(("offline",))
            o.nap()
            self.q.put(("offline",))
            self.q.put(("trang_thai", "Đang chạy • Dịch offline (CPU) đã sẵn sàng"))
        except Exception as e:
            o.trang_thai = "loi"
            o.thong_bao = f"{type(e).__name__}: {str(e)[:120]}"
            self.q.put(("offline",))

    def _tai_mo_hinh(self):
        threading.Thread(target=self._khoi_dong_offline, kwargs={"tai": True}, daemon=True).start()

    def _doi_google_truoc(self):
        self.cfg["hien_google_truoc"] = bool(self.bien_google.get())
        self._luu_cau_hinh()

    def _loi_nen(self, e):
        self.q.put(("trang_thai", f"Lỗi: {type(e).__name__}: {e}"))

    # ------------------------------------------------------------ them / xoa vung
    def _them_vung(self):
        if len(self._ds()) >= SO_VUNG_TOI_DA:
            return
        ten = simpledialog.askstring("Thêm vùng dịch", "Tên vùng (ví dụ: Túi đồ, Kỹ năng, Thông báo):",
                                     parent=self.root)
        if not ten or not ten.strip():
            return
        loai = messagebox.askyesnocancel(
            "Loại vùng",
            "Chữ ở vùng này có thay đổi liên tục như phụ đề / hội thoại không?\n\n"
            "Có  = phụ đề (đọc rất nhanh, 6–7 lần mỗi giây)\n"
            "Không = chữ cố định: nhiệm vụ, menu, thông tin (đọc mỗi giây, tiết kiệm token)",
            parent=self.root)
        if loai is None:
            return
        v = vung_moi(f"vung_{int(time.time() * 1000)}", ten.strip()[:20], "phu_de" if loai else "co_dinh")
        self.cfg["cac_vung"].append(v)
        self.vung_dang_sua = v["id"]
        self._luu_cau_hinh()
        self._ve_ds_vung()
        self.chon_vung(v["id"])

    def _xoa_vung(self, ma):
        v = self._v(ma)
        if not v:
            return
        if len(self._ds()) <= 1:
            self._bao("Phải giữ lại ít nhất 1 vùng.", "canh_bao")
            return
        if not messagebox.askyesno("Xóa vùng", f"Xóa vùng \"{v['ten']}\"?", parent=self.root):
            return
        self.cfg["cac_vung"] = [x for x in self._ds() if x["id"] != ma]
        if ma in self.khung:
            self.khung.pop(ma).huy()
        for d in (self.trang_thai, self.van_ban):
            d.pop(ma, None)
        self._luu_cau_hinh()
        self._ve_ds_vung()

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
                    "Greetings, traveler. The road to Hernand is dangerous at night.", "lời thoại / phụ đề", [], [])
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
    def lenh(self, ten):
        c = self.cfg
        if ten == "chon_hoi_thoai" or ten == "chon_nhiem_vu":
            ma = self._ma_theo_phim("hoi_thoai" if ten == "chon_hoi_thoai" else "nhiem_vu")
            if ma:
                self.chon_vung(ma)
            return
        if ten.startswith("the:"):
            c["the_dang_mo"] = ten[4:]
            self._sap_xep_giao_dien()
        elif ten == "thu_gon":
            c["thu_gon"] = not c.get("thu_gon")
            self._sap_xep_giao_dien()
        elif ten.startswith("co_gd:"):
            c["co_giao_dien"] = float(ten[6:])
            self._luu_cau_hinh()
            self.root.after(10, self._ve_lai_giao_dien)
            return
        elif ten.startswith("che_do:"):
            c["che_do_hoi_thoai"] = ten[7:]
            if c["che_do_hoi_thoai"].startswith("offline") and self.offline.trang_thai in ("chua_tai", "loi"):
                self._tai_mo_hinh()
        elif ten in ("giong_bat_tat", "bat_tat_giong"):
            c["giong_doc"] = not c.get("giong_doc")
            if not c["giong_doc"]:
                self.giong.dung()
            elif not self.giong.co_thu_vien():
                self._bao("Thiếu thư viện edge-tts – hãy cập nhật lên bản exe mới.", "loi")
        elif ten.startswith("giong:"):
            c["giong"] = ten[6:]
        elif ten in ("toc_giong_tang", "toc_giong_giam"):
            c["toc_do_giong"] = max(-30, min(70, int(c.get("toc_do_giong", 25)) + (10 if ten.endswith("tang") else -10)))
        elif ten in ("am_giong_tang", "am_giong_giam"):
            c["am_luong_giong"] = round(max(0.1, min(1.0, float(c.get("am_luong_giong", 1.0))
                                                     + (0.1 if ten.endswith("tang") else -0.1))), 1)
        elif ten.startswith("giam_game:"):
            c["giam_tieng_game"] = float(ten[10:])
        elif ten.startswith("sua:"):
            self.vung_dang_sua = ten[4:]
            self._xem_thu()
        elif ten.startswith("loc:"):
            v = self._v(ten[4:])
            if v:
                v["loc_trang"] = not v.get("loc_trang")
                self.trang_thai.pop(v["id"], None)
        elif ten.startswith("khung:"):
            _, ma, hanh = ten.split(":")
            self._doi_khung(ma, hanh)
        elif ten in ("co_chu_tang", "co_chu_giam", "rong_tang", "rong_giam"):
            self._doi_khung(self.vung_dang_sua, ten)
        elif ten == "bat_tat_tu_dong":
            c["tu_dong_dich"] = not c["tu_dong_dich"]
        elif ten == "dich_ngay":
            self.ep_dich.set()
        elif ten == "an_hien":
            self.hien_ban_dich = not self.hien_ban_dich
            self._ve_lai()
        elif ten == "dich_man_hinh":
            with self.khoa_tm:
                self.doan_tm = []
            if c["toan_man_lien_tuc"]:
                self.toan_man_bat = not self.toan_man_bat
                if self.toan_man_bat:
                    self.lan_toan_man = 0.0
                    self.toan_man.cho("⏳ Đang bật dịch cả màn hình...")
                else:
                    self.toan_man.an()
            elif self.mot_lan_hien:
                self.mot_lan_hien = False
                self.toan_man.an()
            else:
                self.mot_lan_hien = True
                self.toan_man.cho("⏳ Đang đọc và dịch cả màn hình...")
                self.can_toan_man.set()
                self.ep_dich.set()
        elif ten in ("toan_man_lien_tuc", "toan_man_mot_lan"):
            c["toan_man_lien_tuc"] = ten == "toan_man_lien_tuc"
            self.toan_man_bat = self.mot_lan_hien = False
            self.toan_man.an()
        elif ten == "xem_vung":
            self.xem_vung = not self.xem_vung
            if not self.xem_vung:
                for m, lbl in self.lbl_xem.items():
                    lbl.config(image="", text="(tắt)", width=48, height=2)
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
        elif ten.rsplit("_", 1)[0] in ("hoi_thoai", "nhiem_vu") and ten.rsplit("_", 1)[1] in (
                "len", "xuong", "trai", "phai", "to", "nho"):
            tien_to, hanh = ten.rsplit("_", 1)
            ma = self._ma_theo_phim(tien_to)
            if ma:
                self._doi_khung(ma, {"to": "rong_tang", "nho": "rong_giam"}.get(hanh, hanh))
        elif ten == "thoat":
            self.thoat()
            return
        else:
            return
        self._cap_nhat_nut()
        self._luu_cau_hinh()

    def _doi_khung(self, ma, hanh):
        v = self._v(ma)
        if not v:
            return
        kd = self._kd(v)
        if not kd:
            self._bao(f"Chưa chọn vùng {v['ten']}.", "canh_bao")
            return
        if hanh == "len":
            kd[1] -= 20
        elif hanh == "xuong":
            kd[1] += 20
        elif hanh == "trai":
            kd[0] -= 20
        elif hanh == "phai":
            kd[0] += 20
        elif hanh == "rong_tang":
            kd[2] = int(kd[2] * 1.1)
        elif hanh == "rong_giam":
            kd[2] = max(150, int(kd[2] / 1.1))
        elif hanh == "co_chu_tang":
            v["co_chu"] = min(48, v["co_chu"] + 1)
        elif hanh == "co_chu_giam":
            v["co_chu"] = max(10, v["co_chu"] - 1)
        else:
            return
        v["khung"] = kd
        self.vung_dang_sua = ma
        self._xem_thu()
        self._cap_nhat_nut()
        self._luu_cau_hinh()

    def _khung_doi_bang_chuot(self, khung):
        v = self._v(khung.ma)
        if v:
            v["khung"] = [khung.x, khung.y, khung.w]
            v["co_chu"] = khung.co_chu
            self.vung_dang_sua = v["id"]
            self._cap_nhat_nut()
            self._luu_cau_hinh()

    def _xem_thu(self):
        self.xem_thu_den = time.time() + 2
        self._ve_lai()
        self.root.after(2100, self._ve_lai)

    def _ve_lai(self):
        c = self.cfg
        con = set()
        for v in self._ds():
            ma = v["id"]
            con.add(ma)
            kd = self._kd(v)
            chu = self.van_ban.get(ma, "")
            if not chu and time.time() < self.xem_thu_den:
                chu = f"({v['ten']} – xem thử)"
            hien = kd and not self.dang_chon and (self.dang_chinh_khung or (self.hien_ban_dich and chu))
            if hien:
                do_dam = c["do_dam_chu"] if c["kieu_hien"] == "phu_de" else c["do_mo"]
                self._khung(ma).hien(chu, v["ten"], v["loai"] == "phu_de", kd[0], kd[1], kd[2], v["co_chu"],
                                     c["kieu_hien"], do_dam, c["vien_chu"])
            elif ma in self.khung:
                self.khung[ma].an()
        for ma in list(self.khung):
            if ma not in con:
                self.khung.pop(ma).huy()

    # ------------------------------------------------------------ chon vung
    def chon_vung(self, ma):
        v = self._v(ma)
        if self.dang_chon or not v:
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
        cv.create_text(cx, cy, fill="white", font=self._f(22, "bold"),
                       text=f"Kéo chuột khoanh vùng chữ \"{v['ten'].upper()}\"   •   Esc để hủy")
        if v.get("vung"):
            x, y, w, h = v["vung"]
            cv.create_rectangle(x - tat_ca["left"], y - tat_ca["top"], x - tat_ca["left"] + w,
                                y - tat_ca["top"] + h, outline="#f0b54a", width=2, dash=(6, 4))
        dau = {}

        def dong():
            sel.destroy()
            self.dang_chon = False
            self.trang_thai.pop(ma, None)
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
                moi = [x1 + tat_ca["left"], y1 + tat_ca["top"], x2 - x1, y2 - y1]
                v["vung"] = moi
                v["khung"] = [moi[0], moi[1], moi[2]]  # khung dich doi theo vung moi
                self.van_ban[ma] = ""
                self.vung_dang_sua = ma
                self._luu_cau_hinh()
                self._bao(f"Đã lưu vùng {v['ten']} – lần sau mở app không cần chọn lại.")
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

            mot_lan = self.can_toan_man.is_set()
            lien_tuc = (self.toan_man_bat and not self.viec_toan_man.ban
                        and time.time() - self.lan_toan_man >= self.cfg["chu_ky_toan_man_giay"])
            if mot_lan or lien_tuc:
                self.can_toan_man.clear()
                self.lan_toan_man = time.time()
                sct.lam_moi(None)
                da_lam_moi = True
                try:
                    self.viec_toan_man.gui(sct.toan_man(), mot_lan)
                except Exception as e:
                    self.q.put(("toan_man", None, f"Không chụp được màn hình: {e}", mot_lan, 0))

            if self.tam_dung.is_set() or self.dang_chinh_khung:
                continue
            tu_dong = ep or self.cfg["tu_dong_dich"]
            if not tu_dong and not self.xem_vung:
                continue
            ds = [dict(v) for v in self.cfg["cac_vung"] if v.get("vung")]
            can = [v for v in ds if ep or v["loai"] == "phu_de" or dem % VONG_CO_DINH == 0]
            if not can:
                continue
            if not da_lam_moi:
                sct.lam_moi([v["vung"] for v in can])
            for v in can:
                try:
                    t0 = time.time()
                    anh = sct.cat(v["vung"])
                    self._gui_xem(anh, v["id"])
                    if not tu_dong:
                        continue
                    if v["loai"] == "phu_de":
                        self._xu_ly_vung(v, anh, ep, t0)
                    else:
                        self._viec_doc(v["id"]).gui(v, anh, ep, t0)
                except Exception as e:
                    self.q.put(("trang_thai", f"Lỗi ở vùng {v['ten']}: {e}"))
        sct.dong()

    def _gui_xem(self, anh, ma):
        st = self._st(ma)
        if not self.xem_vung or time.time() - st.lan_xem < 1.0:
            return
        st.lan_xem = time.time()
        anh = anh.copy()
        anh.thumbnail((360, 70))
        self.q.put(("xem", ma, anh))

    def _xu_ly_vung(self, v, anh, ep, t0):
        ma = v["id"]
        st = self._st(ma)
        tuy = TUY_LOAI[v["loai"]]
        loc = v.get("loc_trang")
        anh_doc = loc_chu_trang(anh, self.cfg["nguong_chu_trang"]) if loc else anh
        if ep:
            try:
                ten_tep = re.sub(r"[^A-Za-z0-9_]+", "_", bo_dau(v["ten"]))
                anh.save(os.path.join(DU_LIEU, f"anh_chup_{ten_tep}.png"))
                if loc:
                    anh_doc.save(os.path.join(DU_LIEU, f"anh_chup_{ten_tep}_da_loc.png"))
            except Exception:
                pass

        van_tay = dau_van_tay(anh_doc)
        hinh_dung_yen = anh_giong(van_tay, st.van_tay)
        if not ep and st.chu_ocr is not None and hinh_dung_yen:
            chu = st.chu_ocr
        else:
            try:
                chu = lam_sach(doc_chu(anh_doc))
            except Exception as e:
                self.q.put(("trang_thai", "Không đọc được chữ. Có thể Windows chưa cài gói đọc chữ "
                                          f"tiếng Anh (xem HUONG_DAN.txt). Lỗi: {e}"))
                return
            st.t_doc = time.time() - t0
            hien_tai = self.van_ban.get(ma) or ""
            khung = self.khung.get(ma)
            if (khung is not None and not khung.khong_bi_chup and len(chu) >= 15 and hien_tai
                    and chu_giong(bo_dau(chu), bo_dau(hien_tai), 0.75)):
                st.van_tay = van_tay  # dang doc phai ban dich cua chinh app -> bo qua lan doc nay
                return
            st.chu_ocr = chu
        st.van_tay = van_tay

        st.lan_trong = st.lan_trong + 1 if not chu else 0
        if st.chu_da_hien and chu and not chu_giong(so_hoa(chu), so_hoa(st.chu_da_hien), tuy["lech"]):
            st.lan_lech += 1
        else:
            st.lan_lech = 0
        dang_hien = bool(st.chu_da_hien or self.van_ban.get(ma))
        if dang_hien and (st.lan_trong >= tuy["an_trong"] or (st.chu_da_hien and st.lan_lech >= tuy["an_lech"])):
            st.chu_da_hien = ""
            st.lan_lech = 0
            self.q.put(("an", ma))

        if st.chu_cho is not None and chu_giong(so_hoa(chu), so_hoa(st.chu_cho), 0.9):
            st.so_lan_giong += 1
        else:
            st.so_lan_giong = 0
            if chu:
                st.t_doi_chu = t0  # luc thay chu moi lan dau
        st.chu_cho = chu
        on_dinh = (ep or st.so_lan_giong >= 1 or (v["loai"] == "phu_de" and het_cau(chu))
                   or (v["loai"] == "co_dinh" and hinh_dung_yen))
        if (not on_dinh and v["loai"] == "phu_de" and len(chu) >= 30
                and time.time() - getattr(st, "t_xem_som", 0) > 0.6):
            st.t_xem_som = time.time()  # chu dang chay tung chu: hien ban Google tam truoc
            threading.Thread(target=self._dich_som, args=(ma, st, chu), daemon=True).start()
        if not on_dinh or not chu:
            return
        if not ep and st.chu_da_hien:
            if chu == st.chu_da_hien:
                return
            chi_doi_so = so_hoa(chu) == so_hoa(st.chu_da_hien)
            if not chi_doi_so and chu_giong(so_hoa(chu), so_hoa(st.chu_da_hien), tuy["bo_qua"]):
                return

        st.chu_da_hien = chu
        self._viec_dich(ma).gui(v, chu)

    def _dich_som(self, ma, st, chu):
        try:
            vi = self.offline.dich(chu) if self.offline.san_sang() else google_dich(chu)
        except Exception:
            return
        # chi hien neu chua co ban dich chinh thuc moi hon cho cau nay
        if self.trang_thai.get(ma) is st and st.chu_cho and chu_giong(chu, st.chu_cho[:len(chu)], 0.85) \
                and not (st.chu_da_hien and st.chu_da_hien.startswith(chu[:20]) and len(st.chu_da_hien) >= len(chu)):
            self.q.put(("hien", ma, vi))

    def _thuc_hien_dich(self, v, chu):
        if not chu:
            if self.bo_dich.dung_claude():
                self.bo_dich.claude.lam_nong()
            return
        ma = v["id"]
        st = self._st(ma)

        def con_dung():
            return self.trang_thai.get(ma) is st and st.chu_da_hien == chu

        t_bat_dau = time.time()
        phu_de = v["loai"] == "phu_de"
        che_do = self.cfg.get("che_do_hoi_thoai", "offline_claude")
        if phu_de and che_do in ("offline", "offline_claude", "google"):
            self._dich_nhanh(v, chu, st, con_dung, che_do, t_bat_dau)
            return
        if not phu_de and che_do != "claude":
            self._dich_nhanh(v, chu, st, con_dung, "google" if che_do == "google" else "offline_claude",
                             t_bat_dau, thay=bool(self.cfg.get("co_dinh_thay_claude", True)), doc_giong=False,
                             mo_ta=f"chữ trong khung '{v['ten']}' (vật phẩm, tài liệu, nhiệm vụ, menu...)")
            return
        cu = self.bo_dich.tim(chu)
        if cu is not None:
            if con_dung():
                self.q.put(("hien", ma, cu))
                if phu_de:
                    self.giong.doc(cu)
                self.q.put(("thoi_gian", f"⏱ {v['ten']}: đọc chữ {st.t_doc * 1000:.0f}ms • lấy bản đã lưu"))
            return
        mo_ta = "lời thoại / phụ đề" if phu_de else f"chữ trong khung '{v['ten']}' (nhiệm vụ, menu, thông tin...)"
        do = {"google": None, "claude_dau": None}
        trang = {"google": False, "xong": False, "do_dai": 0, "lan_cuoi": 0.0}
        if self.bo_dich.dung_claude() and self.cfg.get("hien_google_truoc") and phu_de:
            def google_truoc():
                try:
                    vi = google_dich(chu)
                except Exception:
                    return
                do["google"] = time.time() - t_bat_dau
                if not trang["xong"] and trang["do_dai"] < 15 and con_dung():
                    trang["google"] = True
                    self.q.put(("hien", ma, vi))
            threading.Thread(target=google_truoc, daemon=True).start()

        def dang_ra(doan):
            if do["claude_dau"] is None:
                do["claude_dau"] = time.time() - t_bat_dau
            trang["do_dai"] = len(doan)
            if trang["google"]:
                return
            bay_gio = time.time()
            if bay_gio - trang["lan_cuoi"] > 0.1 and con_dung():
                trang["lan_cuoi"] = bay_gio
                self.q.put(("hien", ma, doan))

        try:
            ban_dich, nguon, tien, loi = self.bo_dich.dich(chu, ma, mo_ta, dang_ra)
            trang["xong"] = True
            if tien:
                self.q.put(("tien", tien))
            self.q.put(("trang_thai", loi or f"Đang chạy • {v['ten']}: {nguon}"))
        except Exception as e:
            trang["xong"] = True
            nguon = "lỗi"
            ban_dich = f"[Không dịch được: {type(e).__name__} {str(e)[:80]}]\n" + chu
            if con_dung():
                st.chu_da_hien = ""
        if ban_dich.strip() and con_dung():
            self.q.put(("hien", ma, ban_dich))
            if phu_de and nguon != "lỗi":
                self.giong.doc(ban_dich)
        xong = time.time() - t_bat_dau
        phan = [f"⏱ {v['ten']}: đọc chữ {st.t_doc * 1000:.0f}ms"]
        if do["google"] is not None:
            phan.append(f"Google {do['google'] * 1000:.0f}ms")
        if do["claude_dau"] is not None:
            phan.append(f"Claude chữ đầu {do['claude_dau'] * 1000:.0f}ms")
        phan.append(f"{nguon} xong {xong * 1000:.0f}ms")
        if st.t_doi_chu:
            phan.append(f"tổng từ lúc chữ hiện {(time.time() - st.t_doi_chu) * 1000:.0f}ms")
        self.q.put(("thoi_gian", " • ".join(phan)))

    def _dich_nhanh(self, v, chu, st, con_dung, che_do, t0, thay=None, doc_giong=True, mo_ta="lời thoại / phụ đề"):
        """Hoi thoai: hien ban dich NGAY (ban Claude da luu > offline > Google), dong bo voi phu de.
        Che do offline_claude: Claude dich ngam de luu, lan sau gap lai cau do hien ban Claude ngay."""
        ma = v["id"]
        vi, nguon = None, ""
        if che_do == "offline_claude":
            vi = self.bo_dich.tim(chu)
            if vi is not None:
                nguon = "bản Claude đã lưu"
        if vi is None and che_do in ("offline", "offline_claude") and self.offline.san_sang():
            try:
                vi = self.bo_dich._sua(self.offline.dich(chu))
                nguon = "offline"
            except Exception as e:
                self.q.put(("trang_thai", f"Dịch offline lỗi: {e}"))
        if vi is None:
            cu = self.bo_dich._tim("google", chu)
            try:
                vi = cu if cu is not None else google_dich(chu)
                if cu is None:
                    self.bo_dich.luu_google(chu, vi)
                vi = self.bo_dich._sua(vi)
                nguon = "Google"
            except Exception as e:
                vi = f"[Không dịch được: {type(e).__name__}]\n{chu}"
                nguon = "lỗi"
                if con_dung():
                    st.chu_da_hien = ""
        if con_dung():
            self.q.put(("hien", ma, vi))
            if nguon != "lỗi" and doc_giong:
                self.giong.doc(vi)
        bay_gio = time.time()
        phan = [f"⏱ {v['ten']}: đọc chữ {st.t_doc * 1000:.0f}ms", f"{nguon} {(bay_gio - t0) * 1000:.0f}ms"]
        if st.t_doi_chu:
            phan.append(f"tổng từ lúc chữ hiện {(bay_gio - st.t_doi_chu) * 1000:.0f}ms")
        self.q.put(("thoi_gian", " • ".join(phan)))

        if che_do == "offline_claude" and nguon in ("offline", "Google") and self.bo_dich.dung_claude():
            def claude_ngam():
                try:
                    kq, ng, tien, loi = self.bo_dich.dich(chu, ma, mo_ta)
                    if tien:
                        self.q.put(("tien", tien))
                    if loi:
                        self.q.put(("trang_thai", loi))
                    doi = self.cfg.get("thay_bang_claude") if thay is None else thay
                    if doi and ng == "Claude" and con_dung():
                        self.q.put(("hien", ma, kq))
                except Exception:
                    pass
            self.nen_claude.submit(claude_ngam)

    # ------------------------------------------------------------ dich ca man hinh
    def _xu_ly_toan_man(self, anh, mot_lan):
        try:
            self._xu_ly_toan_man_that(anh, mot_lan)
        except Exception as e:
            self.q.put(("toan_man", None, f"Lỗi dịch cả màn hình: {e}", mot_lan, 0))

    def _google_an_toan(self, chu):
        try:
            return google_dich(chu)
        except Exception:
            return None

    def _gui_toan_man(self, mot_lan, dang_cho=False):
        with self.khoa_tm:
            ds = [(d["vi"], d["hop"], d["cao"]) for d in self.doan_tm
                  if d["vi"] and d["vi"].strip().lower() != d["en"].strip().lower()]
            tong = len(self.doan_tm)
        phim = self.cfg["phim_tat"]["dich_man_hinh"].upper()
        if mot_lan:
            if tong == 0:
                ghi_chu = "Không thấy chữ tiếng Anh nào trên màn hình"
            elif dang_cho and not ds:
                ghi_chu = "⏳ Đang dịch..."
            else:
                ghi_chu = f"Bản dịch màn hình ({len(ds)} đoạn) – {phim} để tắt"
        else:
            ghi_chu = f"● Dịch cả màn hình: BẬT – {phim} để tắt"
        self.q.put(("toan_man", ds, ghi_chu, mot_lan, tong))

    def _xu_ly_toan_man_that(self, anh, mot_lan):
        if not mot_lan and not self.toan_man_bat:
            return
        vung_bo = [v["vung"] for v in self.cfg["cac_vung"] if v.get("vung")]
        moi = [d for d in gom_doan(ocr_toan_man(anh))
               if hop_le_toan_man(d[0]) and not la_tieng_viet(d[0])
               and not any(giao_nhau(d[1], r) for r in vung_bo)]
        with self.khoa_tm:
            cu = [] if mot_lan else self.doan_tm
            da_khop = set()
            for chu, hop, cao in moi:
                chon = None
                for i, d in enumerate(cu):
                    if i not in da_khop and trung_vi_tri(d["hop"], hop) \
                            and chu_giong(so_hoa(d["en"]), so_hoa(chu), 0.6):
                        chon = i
                        break
                if chon is None:
                    cu.append({"en": chu, "hop": hop, "cao": cao, "vi": None, "nguon": None, "vang": 0,
                               "lan_thay": 1, "dang_g": False, "dang_c": False})
                    da_khop.add(len(cu) - 1)
                else:
                    d = cu[chon]
                    da_khop.add(chon)
                    d.update(hop=hop, cao=cao, vang=0)
                    d["lan_thay"] += 1
                    if not chu_giong(so_hoa(d["en"]), so_hoa(chu), 0.85):  # chu doi that su
                        d.update(en=chu, vi=None, nguon=None, lan_thay=1, dang_g=False, dang_c=False)
            for i, d in enumerate(cu):
                if i not in da_khop:
                    d["vang"] += 1
            self.doan_tm = [d for d in cu if d["vang"] < 2]  # vang mat 2 lan quet moi xoa
            for d in self.doan_tm:
                if d["vi"] is None:
                    vi = self.bo_dich.tim(d["en"])
                    if vi is not None:
                        d["vi"], d["nguon"] = vi, "luu"
            dung_claude = self.bo_dich.dung_claude()
            can_g = [d for d in self.doan_tm if d["vi"] is None and not d["dang_g"]]
            can_c = [d for d in self.doan_tm if dung_claude and d["nguon"] in (None, "google")
                     and not d["dang_c"] and (mot_lan or d["lan_thay"] >= 2)]
            for d in can_g:
                d["dang_g"] = True
            for d in can_c:
                d["dang_c"] = True
        self._gui_toan_man(mot_lan, dang_cho=bool(can_g or can_c))

        if can_c:  # Claude chay rieng, khong chan lan quet sau
            threading.Thread(target=self._claude_toan_man, args=(can_c, mot_lan), daemon=True).start()
        if can_g:  # offline (neu co) hoac Google hien ngay
            ket_qua = None
            if self.offline.san_sang():
                try:
                    ket_qua = [self.bo_dich._sua(x) for x in self.offline.dich_nhieu([d["en"] for d in can_g])]
                except Exception:
                    ket_qua = None
            if ket_qua is None:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                    ket_qua = list(ex.map(self._google_an_toan, [d["en"] for d in can_g]))
            with self.khoa_tm:
                for d, vi in zip(can_g, ket_qua):
                    d["dang_g"] = False
                    if vi and d["vi"] is None:
                        d["vi"], d["nguon"] = vi, "google"
                        self.bo_dich.luu_google(d["en"], vi)
            self._gui_toan_man(mot_lan, dang_cho=bool(can_c))

    def _claude_toan_man(self, ds, mot_lan):
        cac_en = [d["en"] for d in ds]
        try:
            vis, tien, loi = self.bo_dich.dich_nhieu(cac_en, [goi_y_doan(d["en"], d["cao"]) for d in ds])
        except Exception as e:
            vis, tien, loi = None, 0.0, str(e)
        with self.khoa_tm:
            for i, d in enumerate(ds):
                d["dang_c"] = False
                if vis and vis[i] and d["en"] == cac_en[i]:
                    d["vi"], d["nguon"] = vis[i], "claude"
        if tien:
            self.q.put(("tien", tien))
        if loi:
            self.q.put(("trang_thai", loi))
        if mot_lan and not self.mot_lan_hien:
            return
        self._gui_toan_man(mot_lan)

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
                elif loai == "tien":
                    self.cfg["da_dung_usd"] = round(self.cfg["da_dung_usd"] + tin[1], 6)
                    self._cap_nhat_nut()
                elif loai == "offline":
                    self._cap_nhat_nut()
                elif loai == "thoi_gian":
                    self.lbl_tg.config(text=tin[1])
                elif loai == "xem":
                    lbl = self.lbl_xem.get(tin[1])
                    if self.xem_vung and lbl:
                        self.anh_xem[tin[1]] = ImageTk.PhotoImage(tin[2])
                        lbl.config(image=self.anh_xem[tin[1]], text="", width=0, height=0)
                elif loai == "toan_man":
                    _, ds, ghi_chu, mot_lan, tong = tin
                    if mot_lan:
                        if self.mot_lan_hien:
                            if ds is None or tong == 0:
                                self.toan_man.cho(ghi_chu)
                                self.root.after(2500, self._tat_mot_lan)
                            elif ds:
                                self.toan_man.hien(ds, ghi_chu)
                            else:
                                self.toan_man.cho(ghi_chu)
                    elif self.toan_man_bat:
                        if ds is None:
                            self._bao(ghi_chu, "loi")
                        else:
                            self.toan_man.hien(ds, ghi_chu)
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

    def _tat_mot_lan(self):
        if self.mot_lan_hien:
            with self.khoa_tm:
                tong = len(self.doan_tm)
            if tong == 0:
                self.mot_lan_hien = False
                self.toan_man.an()
                self._cap_nhat_nut()

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
            self.cfg["vi_tri_bang"] = [self.root.winfo_x(), self.root.winfo_y()]
        except Exception:
            pass
        try:
            self.giong.dung()
            time.sleep(0.15)
            self.giong._tra_game()
            self.nen_claude.shutdown(wait=False)
        except Exception:
            pass
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
