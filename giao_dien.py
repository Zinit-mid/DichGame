# -*- coding: utf-8 -*-
"""Phan giao dien dung chung: font Be Vietnam Pro (dong goi kem app) va nut bo goc."""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont

FONT = "Segoe UI"            # font chu thuong / dam (bold)
FONT_VUA = "Segoe UI Semibold"   # font nua dam cho tieu de, nut
TI_LE = 1.0                  # co chu chung (dat tu cau hinh)
DA_NAP = False

# mau
NEN = "#15161b"
SAU = "#0f1115"
CANH = "#12151b"
THE = "#1e2027"
VIEN = "#2a2f3a"
O = "#2a2d36"
O_HOVER = "#363a46"
CHU = "#eceef2"
PHU = "#9aa1ad"
DO = "#d4483e"
DO_HOVER = "#e65b50"
XANH = "#3ecf8e"
VANG = "#f0b54a"
LOI = "#ff6b6b"
CAM = "#e8891c"
CAM_HOVER = "#f59a33"


def thu_muc_tai_nguyen():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def nap_font():
    """Nap font Be Vietnam Pro (chi cho app nay, khong cai vao Windows). Goi truoc khi tao cua so."""
    global FONT, FONT_VUA, DA_NAP
    if DA_NAP:
        return FONT
    DA_NAP = True
    thu = os.path.join(thu_muc_tai_nguyen(), "fonts")
    try:
        import ctypes
        gdi = ctypes.windll.gdi32
        so = 0
        for t in ("BeVietnamPro-Regular.ttf", "BeVietnamPro-Bold.ttf", "BeVietnamPro-SemiBold.ttf",
                  "BeVietnamPro-Medium.ttf"):
            p = os.path.join(thu, t)
            if os.path.isfile(p) and gdi.AddFontResourceExW(p, 0x10, 0):   # FR_PRIVATE
                so += 1
        if so >= 3:
            FONT, FONT_VUA = "Be Vietnam Pro", "Be Vietnam Pro SemiBold"
    except Exception:
        pass
    return FONT


def font(co, kieu=""):
    """kieu: '' | 'normal' | 'bold' | 'vua' (nua dam)."""
    co = max(7, round(co * TI_LE))
    if kieu == "vua":
        return (FONT_VUA, co)
    if kieu == "bold":
        return (FONT, co, "bold")
    return (FONT, co)


KIEU_NUT = {
    # nen, chu, nen khi re chuot, vien
    "thuong": (O, CHU, O_HOVER, None),
    "chinh": (DO, "#ffffff", DO_HOVER, None),
    "bat": (DO, "#ffffff", DO_HOVER, None),
    "nguy_hiem": (None, "#ff8a80", "#3a1d1f", "#7a3330"),
    "cam": (CAM, "#ffffff", CAM_HOVER, None),
    "vien": (None, CHU, O, VIEN),
    "trang": ("#ffffff", "#9a4a00", "#ffe8cc", None),
    "trong_cam": (None, "#ffffff", CAM_HOVER, "#ffd29a"),
}


class NutTron(tk.Canvas):
    """Nut bo goc ve bang Canvas. Ho tro config(text=, bg=, fg=, state=) nhu nut thuong."""

    def __init__(self, cha, chu, lenh=None, kieu="thuong", nho=False, rong=None, phu="", co=None,
                 bieu_tuong="", ti_le=None):
        try:
            nen_cha = cha.cget("bg")
        except Exception:
            nen_cha = NEN
        super().__init__(cha, bg=nen_cha, highlightthickness=0, bd=0, cursor="hand2")
        self.p = (lambda n: max(1, round(n * (ti_le if ti_le else TI_LE))))
        self.nen_cha = nen_cha
        self.chu = chu
        self.phu = phu
        self.bieu_tuong = bieu_tuong
        self.lenh = lenh
        self.nho = nho
        self.rong_chu = rong
        self.trang_thai = "normal"
        self.dang_tren = False
        co = co or (10 if nho else 11)
        self.font = tkfont.Font(family=FONT_VUA, size=max(7, round(co * TI_LE)))
        self.font_phu = tkfont.Font(family=FONT, size=max(7, round((co - 2.5) * TI_LE)))
        self.dat_kieu(kieu, ve=False)
        self._dat_co()
        self.bind("<Configure>", lambda e: self._ve())
        self.bind("<Enter>", self._vao, add="+")
        self.bind("<Leave>", self._ra, add="+")
        self.bind("<ButtonRelease-1>", self._bam, add="+")
        self._san = True

    def bind(self, sequence=None, func=None, add=None):
        # code cu hay bind <Enter>/<Leave>/<Button-1> de doi mau: giu luon xu ly cua nut
        if self.__dict__.get("_san", False) and sequence in ("<Enter>", "<Leave>") and func is not None:
            add = "+"
        if self.__dict__.get("_san", False) and sequence == "<Button-1>" and func is not None:
            # nut nay bam bang ButtonRelease; Button-1 cua code cu -> chuyen thanh lenh
            self.lenh = lambda f=func: f(None)
            return None
        return super().bind(sequence, func, add)

    # ---------- tuong thich voi tk.Button / tk.Label
    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        ve = False
        if "text" in kw:
            self.chu = kw.pop("text")
            self._dat_co()
            ve = True
        if "bg" in kw:
            self.mau_nen = kw.pop("bg")
            ve = True
        if "fg" in kw:
            self.mau_chu = kw.pop("fg")
            ve = True
        if "state" in kw:
            self.trang_thai = kw.pop("state")
            ve = True
        if "command" in kw:
            self.lenh = kw.pop("command")
        if "width" in kw and not isinstance(kw["width"], int):
            kw.pop("width")
        for k in ("activebackground", "activeforeground", "relief", "padx", "pady", "font", "cursor"):
            kw.pop(k, None)
        if kw:
            super().configure(**kw)
        if ve:
            self._ve()

    config = configure

    def cget(self, k):
        if k == "text":
            return self.chu
        if k == "bg":
            return self.mau_nen
        return super().cget(k)

    def __setitem__(self, k, v):
        self.configure(**{k: v})

    def dat_kieu(self, kieu, ve=True):
        nen, chu, hover, vien = KIEU_NUT.get(kieu, KIEU_NUT["thuong"])
        self.kieu = kieu
        self.mau_nen = nen or self.nen_cha
        self.mau_chu = chu
        self.mau_hover = hover
        self.mau_vien = vien
        # ten cu dung trong app
        self.mau_nen_goc = self.mau_nen
        if ve:
            self._ve()

    def _dat_co(self):
        P = self.p
        rong = self.font.measure((self.bieu_tuong + "  " if self.bieu_tuong else "") + self.chu)
        if self.phu:
            rong = max(rong, self.font_phu.measure(self.phu))
        if self.rong_chu:
            rong = max(rong, self.font.measure("0") * self.rong_chu)
        cao = self.font.metrics("linespace") + (self.font_phu.metrics("linespace") + P(2) if self.phu else 0)
        dem_ngang, dem_doc = (P(12), P(6)) if self.nho else (P(18), P(10))
        if self.phu:
            dem_doc = P(12)
        super().configure(width=rong + 2 * dem_ngang, height=cao + 2 * dem_doc)

    def _bo_goc(self, x1, y1, x2, y2, r, **kw):
        r = max(1, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
        diem = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(diem, smooth=True, **kw)

    def _ve(self):
        try:
            self.delete("all")
            w, h = self.winfo_width(), self.winfo_height()
        except Exception:
            return
        if w <= 1:
            w, h = int(self.cget("width")), int(self.cget("height"))
        tat = self.trang_thai == "disabled"
        nen = self.mau_hover if (self.dang_tren and not tat) else self.mau_nen
        chu = "#6b7280" if tat else self.mau_chu
        if tat and self.kieu in ("chinh", "bat", "cam"):
            nen = O
        r = self.p(9)
        if nen and nen != self.nen_cha:
            self._bo_goc(1, 1, w - 1, h - 1, r, fill=nen, outline=self.mau_vien or nen)
        elif self.mau_vien:
            self._bo_goc(1, 1, w - 1, h - 1, r, fill=self.nen_cha, outline=self.mau_vien)
        nhan = (self.bieu_tuong + "  " if self.bieu_tuong else "") + self.chu
        if self.phu:
            lh = self.font.metrics("linespace")
            lp = self.font_phu.metrics("linespace")
            y0 = (h - lh - lp - self.p(2)) // 2
            self.create_text(w // 2, y0, text=nhan, font=self.font, fill=chu, anchor="n")
            self.create_text(w // 2, y0 + lh + self.p(2), text=self.phu, font=self.font_phu,
                             fill="#ffe1de" if self.kieu in ("chinh", "bat") else PHU, anchor="n")
        else:
            self.create_text(w // 2, h // 2, text=nhan, font=self.font, fill=chu)

    def _vao(self, e):
        self.dang_tren = True
        self._ve()

    def _ra(self, e):
        self.dang_tren = False
        self._ve()

    def _bam(self, e):
        if self.trang_thai == "disabled" or not self.lenh:
            return
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.lenh()
