# -*- coding: utf-8 -*-
"""
VIET HOA GAME - launcher tu do game da cai (Steam / Epic / GOG / chon tay)
va cai / go goi Viet hoa. Windows 10/11.

  - Danh muc goi Viet hoa: danh_muc.json tren GitHub (kho VietHoaGame)
  - Truoc khi cai: sao luu file goc vao %APPDATA%\\VietHoaGame\\sao_luu
  - Khoi phuc: tra lai file goc, xoa file goi da them
  - Game cap nhat de mat Viet hoa -> bao "Cai lai"
"""

APP_VERSION = "0.5.0"
REPO = "Zinit-mid/VietHoaGame"

import ctypes
import glob
import hashlib
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
import urllib.error
import urllib.request
import zipfile

try:
    import winreg
except ImportError:  # chay thu ngoai Windows
    winreg = None

DONG_GOI = getattr(sys, "frozen", False)
THU_MUC_APP = os.path.dirname(sys.executable if DONG_GOI else os.path.abspath(__file__))
TAI_NGUYEN = getattr(sys, "_MEIPASS", THU_MUC_APP)
DU_LIEU = os.path.join(os.environ.get("APPDATA") or THU_MUC_APP, "VietHoaGame")
THU_MUC_SAO_LUU = os.path.join(DU_LIEU, "sao_luu")
THU_MUC_TAI = os.path.join(DU_LIEU, "tai_ve")
FILE_DA_CAI = os.path.join(DU_LIEU, "da_cai.json")
FILE_CAU_HINH = os.path.join(DU_LIEU, "cau_hinh.json")
URL_DANH_MUC = f"https://raw.githubusercontent.com/{REPO}/main/danh_muc.json"

# appid Steam khong phai game
STEAM_BO_QUA = {"228980", "1070560", "1391110", "1628350", "1493710", "250820", "1826330"}


# ================================================================ Tien ich

def doc_json(duong_dan, mac_dinh):
    try:
        with open(duong_dan, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return mac_dinh


def ghi_json(duong_dan, du_lieu):
    os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
    tam = duong_dan + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)
    os.replace(tam, duong_dan)


def so_phien_ban(s):
    return tuple(int(x) for x in re.findall(r"\d+", str(s))[:4]) or (0,)


def bam_tep(duong_dan):
    h = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        for khuc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(khuc)
    return h.hexdigest()


def tai_tep(url, duong_dan, bao=None):
    yc = urllib.request.Request(url, headers={"User-Agent": "VietHoaGame"})
    tam = duong_dan + ".dang_tai"
    with urllib.request.urlopen(yc, timeout=30) as r, open(tam, "wb") as f:
        tong = int(r.headers.get("Content-Length") or 0)
        da = 0
        while True:
            khuc = r.read(256 * 1024)
            if not khuc:
                break
            f.write(khuc)
            da += len(khuc)
            if bao and tong:
                bao(f"Đang tải... {da * 100 // tong}%")
    os.replace(tam, duong_dan)


def _tai_json(url):
    yc = urllib.request.Request(url, headers={"User-Agent": "VietHoaGame",
                                              "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(yc, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def la_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ================================================================ Do game

def doc_reg(goc, khoa, ten):
    if winreg is None:
        return None
    for co in (0, getattr(winreg, "KEY_WOW64_64KEY", 0), getattr(winreg, "KEY_WOW64_32KEY", 0)):
        try:
            with winreg.OpenKey(goc, khoa, 0, winreg.KEY_READ | co) as k:
                return winreg.QueryValueEx(k, ten)[0]
        except OSError:
            continue
    return None


def doc_vdf(chu):
    """Doc file .vdf / .acf cua Steam thanh dict (khoa viet thuong)."""
    the = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', chu)
    vi_tri = 0

    def khoi():
        nonlocal vi_tri
        d = {}
        while vi_tri < len(the):
            chuoi, ngoac = the[vi_tri]
            vi_tri += 1
            if ngoac == "}":
                return d
            if ngoac == "{":
                continue
            khoa = chuoi.lower()
            if vi_tri < len(the) and the[vi_tri][1] == "{":
                vi_tri += 1
                d[khoa] = khoi()
            elif vi_tri < len(the):
                d[khoa] = the[vi_tri][0].replace("\\\\", "\\")
                vi_tri += 1
        return d

    return khoi()


def _doc_tep_chu(duong_dan):
    with open(duong_dan, encoding="utf-8", errors="replace") as f:
        return f.read()


def tim_steam():
    goc = []
    if winreg is not None:
        goc.append(doc_reg(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"))
        goc.append(doc_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"))
        goc.append(doc_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"))
    goc.append(os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam"))
    thu_vien = []
    for g in goc:
        if not g or not os.path.isdir(g):
            continue
        thu_vien.append(g)
        vdf = os.path.join(g, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                d = doc_vdf(_doc_tep_chu(vdf)).get("libraryfolders", {})
                for v in d.values():
                    p = v.get("path") if isinstance(v, dict) else v
                    if isinstance(p, str) and p:
                        thu_vien.append(p)
            except Exception:
                pass
    da_xem, kq = set(), []
    for tv in thu_vien:
        chuan = os.path.normcase(os.path.normpath(tv))
        if chuan in da_xem:
            continue
        da_xem.add(chuan)
        for acf in glob.glob(os.path.join(tv, "steamapps", "appmanifest_*.acf")):
            try:
                a = doc_vdf(_doc_tep_chu(acf)).get("appstate", {})
            except Exception:
                continue
            ma = str(a.get("appid", ""))
            thu_muc = os.path.join(tv, "steamapps", "common", a.get("installdir", ""))
            if not ma or ma in STEAM_BO_QUA or not a.get("installdir") or not os.path.isdir(thu_muc):
                continue
            kq.append({"nguon": "steam", "ma": ma, "ten": a.get("name") or a.get("installdir"),
                       "thu_muc": thu_muc, "phien_ban": str(a.get("buildid", ""))})
    return kq


def tim_epic():
    pd = os.environ.get("ProgramData", r"C:\ProgramData")
    kq = []
    for item in glob.glob(os.path.join(pd, "Epic", "EpicGamesLauncher", "Data", "Manifests", "*.item")):
        d = doc_json(item, {})
        thu_muc = d.get("InstallLocation") or ""
        if not thu_muc or not os.path.isdir(thu_muc) or d.get("bIsApplication") is False:
            continue
        kq.append({"nguon": "epic", "ma": str(d.get("AppName") or d.get("CatalogItemId") or thu_muc),
                   "ten": d.get("DisplayName") or os.path.basename(thu_muc), "thu_muc": thu_muc,
                   "phien_ban": str(d.get("AppVersionString", ""))})
    return kq


def tim_gog():
    if winreg is None:
        return []
    kq = []
    for khoa_goc in (r"SOFTWARE\WOW6432Node\GOG.com\Games", r"SOFTWARE\GOG.com\Games"):
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, khoa_goc)
        except OSError:
            continue
        with k:
            i = 0
            while True:
                try:
                    con = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                ten = doc_reg(winreg.HKEY_LOCAL_MACHINE, khoa_goc + "\\" + con, "gameName")
                thu_muc = doc_reg(winreg.HKEY_LOCAL_MACHINE, khoa_goc + "\\" + con, "path")
                ban = doc_reg(winreg.HKEY_LOCAL_MACHINE, khoa_goc + "\\" + con, "ver") or ""
                if thu_muc and os.path.isdir(thu_muc) and not any(g["ma"] == con for g in kq):
                    kq.append({"nguon": "gog", "ma": con, "ten": ten or os.path.basename(thu_muc),
                               "thu_muc": thu_muc, "phien_ban": str(ban)})
        if kq:
            break
    return kq


def tim_tat_ca(game_tay):
    kq = []
    for ham in (tim_steam, tim_epic, tim_gog):
        try:
            kq += ham()
        except Exception:
            pass
    for g in game_tay or []:
        if os.path.isdir(g.get("thu_muc", "")):
            kq.append({"nguon": "tay", "ma": os.path.normcase(os.path.normpath(g["thu_muc"])),
                       "ten": g.get("ten") or os.path.basename(g["thu_muc"]), "thu_muc": g["thu_muc"],
                       "phien_ban": ""})
    da, gon = set(), []
    for g in kq:
        k = os.path.normcase(os.path.normpath(g["thu_muc"]))
        if k not in da:
            da.add(k)
            gon.append(g)
    return sorted(gon, key=lambda g: g["ten"].lower())


def thu_muc_desktop():
    """Desktop that nguoi dung dang thay (ke ca khi OneDrive chuyen Desktop sang OneDrive\\Desktop)."""
    try:
        import ctypes.wintypes as wt

        class GUID(ctypes.Structure):
            _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16),
                        ("d", ctypes.c_ubyte * 8)]
        g = GUID(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
        p = wt.LPWSTR()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
            kq = p.value
            ctypes.windll.ole32.CoTaskMemFree(p)
            if kq and os.path.isdir(kq):
                return kq
    except Exception:
        pass
    for p in (os.path.join(os.environ.get("OneDrive") or "", "Desktop"),
              os.path.join(os.environ.get("USERPROFILE") or "", "Desktop")):
        if os.path.isdir(p) and os.environ.get("OneDrive" if "OneDrive" in p else "USERPROFILE"):
            return p
    return os.path.join(os.environ.get("USERPROFILE") or DU_LIEU, "Desktop")


def la_crimson(g):
    return (g["nguon"] == "steam" and str(g["ma"]) == "3321460") or os.path.isfile(
        os.path.join(g["thu_muc"], "bin64", "CrimsonDesert.exe"))


def khoa_game(g):
    return f"{g['nguon']}:{g['ma']}"


# ================================================================ Danh muc goi

def doc_danh_muc():
    """Danh muc moi nhat tren GitHub; mat mang thi dung ban kem trong app."""
    try:
        d = _tai_json(URL_DANH_MUC + f"?t={int(time.time())}")
        ghi_json(os.path.join(DU_LIEU, "danh_muc_da_tai.json"), d)
        return d, True
    except Exception:
        d = doc_json(os.path.join(DU_LIEU, "danh_muc_da_tai.json"), None) \
            or doc_json(os.path.join(TAI_NGUYEN, "danh_muc.json"), {"goi": []})
        return d, False


def goi_khop(goi, g):
    """Goi Viet hoa nay co danh cho game g khong."""
    if goi.get("thu_nghiem"):
        return False
    nd = goi.get("nhan_dien") or {}
    if str(g["ma"]) in [str(x) for x in nd.get(g["nguon"], [])]:
        return True
    for tep in nd.get("file", []):
        if os.path.isfile(os.path.join(g["thu_muc"], tep)):
            return True
    return False


def tim_goi(danh_muc, g):
    for goi in danh_muc.get("goi", []):
        if goi_khop(goi, g):
            return goi
    return None


def goi_thu(danh_muc):
    return next((x for x in danh_muc.get("goi", []) if x.get("thu_nghiem")), None)


def ho_tro_phien_ban(goi, g):
    ds = [str(x) for x in (goi.get("phien_ban_game") or [])]
    return not ds or not g.get("phien_ban") or str(g["phien_ban"]) in ds


# ================================================================ Cai / khoi phuc

class LoiCai(Exception):
    pass


def _duong_dan_an_toan(goc, tuong_doi):
    tuong_doi = tuong_doi.replace("\\", "/")
    if tuong_doi.startswith("/") or re.match(r"^[A-Za-z]:", tuong_doi) or ".." in tuong_doi.split("/"):
        raise LoiCai(f"gói có đường dẫn không hợp lệ: {tuong_doi}")
    dich = os.path.normpath(os.path.join(goc, tuong_doi))
    if os.path.commonpath([os.path.normcase(dich), os.path.normcase(os.path.normpath(goc))]) != \
            os.path.normcase(os.path.normpath(goc)):
        raise LoiCai(f"gói có đường dẫn không hợp lệ: {tuong_doi}")
    return dich


def _loi_quyen(e):
    if isinstance(e, PermissionError):
        return LoiCai("không ghi được vào thư mục game. Hãy TẮT GAME rồi thử lại; nếu vẫn lỗi, "
                      "bấm \"Chạy bằng quyền quản trị\".")
    return e


class QuanLyCai:
    def __init__(self):
        self.da_cai = doc_json(FILE_DA_CAI, {})

    def luu(self):
        ghi_json(FILE_DA_CAI, self.da_cai)

    def thu_muc_sao_luu(self, g):
        return os.path.join(THU_MUC_SAO_LUU, re.sub(r"[^\w.-]", "_", khoa_game(g)))

    def ban_ghi(self, g):
        return self.da_cai.get(khoa_game(g))

    def trang_thai(self, g, goi):
        """chua_ho_tro | co_viet_hoa | da_cai | can_cai_lai | co_ban_moi | khac_phien_ban"""
        bg = self.ban_ghi(g)
        if bg:
            if bg.get("phien_ban_game") and g.get("phien_ban") and bg["phien_ban_game"] != g["phien_ban"]:
                return "can_cai_lai"
            for t in bg.get("tep", []):
                p = os.path.join(g["thu_muc"], t["duong_dan"])
                try:
                    if not os.path.isfile(p) or (os.path.getsize(p) != t.get("kich_thuoc", os.path.getsize(p))
                                                 or bam_tep(p) != t["sha256"]):
                        return "can_cai_lai"
                except OSError:
                    return "can_cai_lai"
            if goi and not bg.get("thu_nghiem") and so_phien_ban(goi.get("phien_ban")) > so_phien_ban(
                    bg.get("phien_ban_goi")):
                return "co_ban_moi"
            return "da_cai"
        if goi:
            return "co_viet_hoa" if ho_tro_phien_ban(goi, g) else "khac_phien_ban"
        return "chua_ho_tro"

    def tai_goi(self, goi, bao):
        os.makedirs(THU_MUC_TAI, exist_ok=True)
        ten = re.sub(r"[^\w.-]", "_", f"{goi['id']}-{goi.get('phien_ban', '0')}.zip")
        p = os.path.join(THU_MUC_TAI, ten)
        if not (os.path.isfile(p) and (not goi.get("sha256") or bam_tep(p) == goi["sha256"])):
            bao(f"Đang tải gói {goi.get('ten', goi['id'])}...")
            tai_tep(goi["url"], p, bao)
        if goi.get("sha256") and bam_tep(p) != goi["sha256"]:
            os.remove(p)
            raise LoiCai("gói tải về bị lỗi (sai mã kiểm tra) – hãy thử lại")
        return p

    def cai(self, g, goi, tep_zip, bao):
        k = khoa_game(g)
        cu = self.da_cai.get(k)
        sl = self.thu_muc_sao_luu(g)
        os.makedirs(sl, exist_ok=True)
        tep_cu = {t["duong_dan"]: t for t in (cu or {}).get("tep", [])}
        ds_moi = []
        try:
            with zipfile.ZipFile(tep_zip) as z:
                muc = [n for n in z.namelist() if n.startswith("tep/") and not n.endswith("/")]
                if not muc:
                    raise LoiCai("gói không có file nào trong thư mục tep/")
                for i, n in enumerate(muc):
                    tuong_doi = n[4:]
                    dich = _duong_dan_an_toan(g["thu_muc"], tuong_doi)
                    ban_sao = _duong_dan_an_toan(sl, tuong_doi)
                    t_cu = tep_cu.get(tuong_doi)
                    if t_cu is None:
                        co_goc = os.path.isfile(dich)
                        if co_goc:
                            os.makedirs(os.path.dirname(ban_sao), exist_ok=True)
                            shutil.copy2(dich, ban_sao)
                    else:
                        co_goc = t_cu.get("co_goc", False)
                        # game cap nhat da ghi de file -> file hien tai la ban goc moi
                        if os.path.isfile(dich) and bam_tep(dich) != t_cu["sha256"]:
                            os.makedirs(os.path.dirname(ban_sao), exist_ok=True)
                            shutil.copy2(dich, ban_sao)
                            co_goc = True
                    os.makedirs(os.path.dirname(dich), exist_ok=True)
                    with z.open(n) as nguon, open(dich + ".viethoa_tam", "wb") as ra:
                        shutil.copyfileobj(nguon, ra)
                    os.replace(dich + ".viethoa_tam", dich)
                    ds_moi.append({"duong_dan": tuong_doi, "sha256": bam_tep(dich),
                                   "kich_thuoc": os.path.getsize(dich), "co_goc": co_goc})
                    bao(f"Đang cài... {i + 1}/{len(muc)} file")
        except Exception as e:
            # ghi lai nhung file da thay de khoi phuc duoc
            if ds_moi or cu:
                gop = {t["duong_dan"]: t for t in (cu or {}).get("tep", [])}
                gop.update({t["duong_dan"]: t for t in ds_moi})
                self.da_cai[k] = dict(cu or {}, ten=g["ten"], thu_muc=g["thu_muc"], tep=list(gop.values()),
                                      goi_id=goi["id"], phien_ban_goi="?", loi_do_dang=True)
                self.luu()
            raise _loi_quyen(e)
        # file cua goi cu khong con trong goi moi -> tra ve ban goc
        con = {t["duong_dan"] for t in ds_moi}
        for dd, t in tep_cu.items():
            if dd not in con:
                self._tra_mot(g, sl, t)
        self.da_cai[k] = {"ten": g["ten"], "thu_muc": g["thu_muc"], "goi_id": goi["id"],
                          "phien_ban_goi": str(goi.get("phien_ban", "")), "phien_ban_game": g.get("phien_ban", ""),
                          "thu_nghiem": bool(goi.get("thu_nghiem")), "luc": time.strftime("%Y-%m-%d %H:%M"),
                          "tep": ds_moi}
        self.luu()

    def _tra_mot(self, g, sl, t):
        dich = _duong_dan_an_toan(g["thu_muc"], t["duong_dan"])
        ban_sao = _duong_dan_an_toan(sl, t["duong_dan"])
        if t.get("co_goc"):
            if not os.path.isfile(ban_sao):
                raise LoiCai(f"mất bản sao lưu của {t['duong_dan']} – hãy dùng 'Kiểm tra tệp' của Steam/Epic")
            shutil.copy2(ban_sao, dich)
        elif os.path.isfile(dich):
            os.remove(dich)

    def khoi_phuc(self, g, bao):
        k = khoa_game(g)
        bg = self.da_cai.get(k)
        if not bg:
            raise LoiCai("game này chưa cài Việt hóa")
        sl = self.thu_muc_sao_luu(g)
        loi = []
        tep = bg.get("tep", [])
        for i, t in enumerate(tep):
            try:
                self._tra_mot(g, sl, t)
            except LoiCai as e:
                loi.append(str(e))
            except Exception as e:
                raise _loi_quyen(e)
            bao(f"Đang khôi phục... {i + 1}/{len(tep)} file")
        if loi:
            raise LoiCai("; ".join(loi[:3]))
        del self.da_cai[k]
        self.luu()
        shutil.rmtree(sl, ignore_errors=True)


# ================================================================ Tu cap nhat

def lay_ban_moi():
    try:
        d = _tai_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError("kho chưa có bản phát hành nào")
        raise
    tep = {a.get("name"): a.get("browser_download_url") for a in d.get("assets", [])}
    return {"phien_ban": str(d.get("tag_name", "")).lstrip("vV"), "exe": tep.get("VietHoaGame.exe")}


def moi_truong_sach():
    mei = getattr(sys, "_MEIPASS", "") or ""
    env = {k: v for k, v in os.environ.items()
           if not (k.upper().startswith("_PYI_") or k.upper().startswith("_MEIPASS")
                   or k.upper() in ("TCL_LIBRARY", "TK_LIBRARY", "PYTHONHOME", "PYTHONPATH"))}
    if mei and "PATH" in env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                      if p and not p.lower().startswith(mei.lower()))
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def ap_dung_cap_nhat(tt, bao):
    if not DONG_GOI:
        raise RuntimeError("bản chạy bằng Python: hãy tải code mới từ GitHub")
    if not tt.get("exe"):
        raise RuntimeError("bản phát hành không có VietHoaGame.exe")
    moi = os.path.join(DU_LIEU, "VietHoaGame_moi.exe")
    tai_tep(tt["exe"], moi, bao)
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


def chay_quyen_quan_tri():
    if DONG_GOI:
        tep, tham_so = sys.executable, ""
    else:
        tep, tham_so = sys.executable, f'"{os.path.abspath(__file__)}"'
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", tep, tham_so, None, 1) > 32


# ================================================================ Giao dien

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

TRANG_THAI = {
    "chua_ho_tro": ("Chưa có Việt hóa", UI_PHU),
    "co_viet_hoa": ("Có Việt hóa – chưa cài", UI_VANG),
    "khac_phien_ban": ("Có Việt hóa nhưng chưa hợp phiên bản game này", UI_VANG),
    "da_cai": ("Đã cài Việt hóa ✓", UI_XANH),
    "can_cai_lai": ("Game vừa cập nhật – cần cài lại", UI_LOI),
    "co_ban_moi": ("Có bản Việt hóa mới", UI_VANG),
    "dang_kiem_tra": ("Đang kiểm tra...", UI_PHU),
}
TEN_NGUON = {"steam": "Steam", "epic": "Epic", "gog": "GOG", "tay": "Thêm tay"}


class App:
    def __init__(self, cha=None, khi_dong=None):
        """cha: cua so Tk cua app Dich Game -> mo launcher thanh cua so con (khong tu cap nhat rieng)."""
        import tkinter as tk
        from tkinter import filedialog, messagebox
        self.nhung = cha is not None
        self.khi_dong = khi_dong
        self.tk, self.filedialog, self.messagebox = tk, filedialog, messagebox
        os.makedirs(DU_LIEU, exist_ok=True)
        self.cfg = doc_json(FILE_CAU_HINH, {})
        self.cfg.setdefault("game_tay", [])
        self.ql = QuanLyCai()
        self.danh_muc, self.danh_muc_moi = {"goi": []}, False
        self.games, self.trang = [], {}
        self.q = queue.Queue()
        self.dang_ban = False
        self.ban_moi = None

        self.root = tk.Toplevel(cha) if self.nhung else tk.Tk()
        self.root.title("Việt hóa game" if self.nhung else f"Việt Hóa Game v{APP_VERSION}")
        if self.nhung:
            self.root.protocol("WM_DELETE_WINDOW", self.dong)
        self.root.configure(bg=UI_NEN)
        self.root.geometry("820x600")
        self.root.minsize(620, 420)
        try:
            self.root.iconbitmap(os.path.join(TAI_NGUYEN, "icon.ico"))
        except Exception:
            pass
        self._giao_dien()
        self.root.after(100, self._xu_ly_hang_doi)
        self.root.after(200, self.quet)
        if not self.nhung:
            threading.Thread(target=self._kiem_tra_cap_nhat, daemon=True).start()

    # ---------------------------------------------------------- dung giao dien
    def _nut(self, cha, chu, cmd, chinh=False, nho=False):
        tk = self.tk
        nen, hover = (UI_DO, UI_DO_HOVER) if chinh else (UI_O, UI_O_HOVER)
        b = tk.Label(cha, text=chu, bg=nen, fg="#ffffff" if chinh else UI_CHU, cursor="hand2",
                     font=("Segoe UI", 9 if nho else 10, "bold" if chinh else "normal"),
                     padx=10 if nho else 14, pady=3 if nho else 6)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(bg=hover))
        b.bind("<Leave>", lambda e: b.config(bg=nen))
        return b

    def _giao_dien(self):
        tk = self.tk
        dau = tk.Frame(self.root, bg=UI_NEN, padx=16, pady=12)
        dau.pack(fill="x")
        tk.Label(dau, text="Việt Hóa Game", bg=UI_NEN, fg=UI_CHU, font=("Segoe UI", 16, "bold")).pack(side="left")
        if not self.nhung:
            tk.Label(dau, text=f"v{APP_VERSION}", bg=UI_NEN, fg=UI_PHU, font=("Segoe UI", 9)).pack(
                side="left", padx=(8, 0), pady=(6, 0))
        self.nut_cap_nhat = self._nut(dau, "Kiểm tra cập nhật", self.cap_nhat, nho=True)
        if not self.nhung:
            self.nut_cap_nhat.pack(side="right")
        if not la_admin():
            self._nut(dau, "Chạy bằng quyền quản trị", self._quyen_quan_tri, nho=True).pack(side="right", padx=6)

        thanh = tk.Frame(self.root, bg=UI_NEN, padx=16)
        thanh.pack(fill="x")
        self._nut(thanh, "↻ Quét lại game", self.quet, chinh=True).pack(side="left")
        self._nut(thanh, "+ Thêm game bằng tay", self.them_tay).pack(side="left", padx=6)
        self.bien_loc = tk.BooleanVar(value=bool(self.cfg.get("chi_co_viet_hoa", False)))
        tk.Checkbutton(thanh, text="Chỉ hiện game có Việt hóa", variable=self.bien_loc, command=self._doi_loc,
                       bg=UI_NEN, fg=UI_CHU, selectcolor=UI_O, activebackground=UI_NEN,
                       activeforeground=UI_CHU, font=("Segoe UI", 9)).pack(side="left", padx=10)

        khung = tk.Frame(self.root, bg=UI_NEN, padx=16, pady=10)
        khung.pack(fill="both", expand=True)
        self.cv = tk.Canvas(khung, bg=UI_NEN, highlightthickness=0)
        thanh_cuon = tk.Scrollbar(khung, orient="vertical", command=self.cv.yview)
        self.ds = tk.Frame(self.cv, bg=UI_NEN)
        self.ds.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cua_so_ds = self.cv.create_window((0, 0), window=self.ds, anchor="nw")
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.cua_so_ds, width=e.width))
        self.cv.configure(yscrollcommand=thanh_cuon.set)
        self.cv.pack(side="left", fill="both", expand=True)
        thanh_cuon.pack(side="right", fill="y")
        self.root.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(int(-e.delta / 120), "units"))

        day = tk.Frame(self.root, bg=UI_THE, padx=16, pady=8)
        day.pack(fill="x", side="bottom")
        self.lbl_tt = tk.Label(day, text="", bg=UI_THE, fg=UI_PHU, font=("Segoe UI", 9), anchor="w",
                               justify="left", wraplength=760)
        self.lbl_tt.pack(fill="x")

    def _bao(self, chu, mau=UI_PHU):
        self.lbl_tt.config(text=chu, fg=mau)

    def _ve_danh_sach(self):
        tk = self.tk
        for w in self.ds.winfo_children():
            w.destroy()
        thu = goi_thu(self.danh_muc)
        thu_tu = {"can_cai_lai": 0, "co_ban_moi": 1, "da_cai": 2, "co_viet_hoa": 3, "khac_phien_ban": 4,
                  "dang_kiem_tra": 5, "chua_ho_tro": 6}
        ds = sorted(self.games, key=lambda g: (thu_tu.get(self.trang.get(khoa_game(g), "dang_kiem_tra"), 9),
                                               g["ten"].lower()))
        hien = 0
        for g in ds:
            k = khoa_game(g)
            tt = self.trang.get(k, "dang_kiem_tra")
            if self.bien_loc.get() and tt in ("chua_ho_tro", "dang_kiem_tra"):
                continue
            hien += 1
            goi = tim_goi(self.danh_muc, g)
            the = tk.Frame(self.ds, bg=UI_THE, padx=12, pady=8)
            the.pack(fill="x", pady=(0, 6))
            trai = tk.Frame(the, bg=UI_THE)
            trai.pack(side="left", fill="x", expand=True)
            tk.Label(trai, text=g["ten"], bg=UI_THE, fg=UI_CHU, font=("Segoe UI", 11, "bold"),
                     anchor="w").pack(fill="x")
            bg = self.ql.ban_ghi(g)
            chu_tt, mau = TRANG_THAI[tt]
            if bg and bg.get("thu_nghiem") and tt == "da_cai":
                chu_tt = "Đã cài GÓI THỬ ✓ (bấm Khôi phục để gỡ)"
            if goi and tt in ("co_viet_hoa", "co_ban_moi"):
                chu_tt += f" • gói v{goi.get('phien_ban', '?')}"
            tk.Label(trai, text=chu_tt, bg=UI_THE, fg=mau, font=("Segoe UI", 9), anchor="w").pack(fill="x")
            tk.Label(trai, text=f"{TEN_NGUON.get(g['nguon'], g['nguon'])} • {g['thu_muc']}", bg=UI_THE,
                     fg=UI_PHU, font=("Segoe UI", 8), anchor="w").pack(fill="x")
            phai = tk.Frame(the, bg=UI_THE)
            phai.pack(side="right")
            if bg:
                self._nut(phai, "Khôi phục bản gốc", lambda g=g: self.khoi_phuc(g), nho=True).pack(
                    side="right", padx=(4, 0))
            if goi and tt in ("co_viet_hoa", "can_cai_lai", "co_ban_moi", "khac_phien_ban") and not (
                    bg and bg.get("thu_nghiem")):
                chu = {"co_viet_hoa": "Cài Việt hóa", "can_cai_lai": "Cài lại", "co_ban_moi": "Cập nhật Việt hóa",
                       "khac_phien_ban": "Vẫn cài"}[tt]
                self._nut(phai, chu, lambda g=g, goi=goi: self.cai(g, goi), chinh=True, nho=True).pack(
                    side="right", padx=(4, 0))
            elif bg and bg.get("thu_nghiem") and tt == "can_cai_lai" and thu:
                self._nut(phai, "Cài lại gói thử", lambda g=g: self.cai(g, thu), nho=True).pack(
                    side="right", padx=(4, 0))
            elif not bg and thu:
                self._nut(phai, "Cài gói thử", lambda g=g: self._hoi_goi_thu(g, thu), nho=True).pack(
                    side="right", padx=(4, 0))
            if la_crimson(g):
                self._nut(phai, "Việt hóa bằng Claude", lambda g=g: self.mo_cd(g), chinh=True, nho=True).pack(
                    side="right", padx=(4, 0))
            if g["nguon"] == "tay":
                self._nut(phai, "Bỏ", lambda g=g: self.bo_tay(g), nho=True).pack(side="right", padx=(4, 0))
        if not hien:
            tk.Label(self.ds, text=("Không tìm thấy game nào. Bấm \"+ Thêm game bằng tay\" để chọn thư mục game."
                                    if not self.bien_loc.get() else "Chưa có game nào đã cài trên máy có Việt hóa."),
                     bg=UI_NEN, fg=UI_PHU, font=("Segoe UI", 10)).pack(pady=30)

    # ---------------------------------------------------------- viec nen
    def _nen(self, viec, xong_chu=None):
        if self.dang_ban:
            self._bao("Đang làm việc khác, đợi chút...", UI_VANG)
            return
        self.dang_ban = True

        def chay():
            try:
                kq = viec(lambda s: self.q.put(("bao", s, UI_PHU)))
                if xong_chu:
                    self.q.put(("bao", xong_chu if isinstance(xong_chu, str) else xong_chu(kq), UI_XANH))
            except Exception as e:
                self.q.put(("bao", f"Lỗi: {e}", UI_LOI))
            finally:
                self.q.put(("xong",))
        threading.Thread(target=chay, daemon=True).start()

    def _xu_ly_hang_doi(self):
        try:
            while True:
                tin = self.q.get_nowait()
                if tin[0] == "bao":
                    self._bao(tin[1], tin[2])
                elif tin[0] == "games":
                    self.games, self.danh_muc, self.danh_muc_moi = tin[1], tin[2], tin[3]
                    self.trang = {}
                    self._ve_danh_sach()
                elif tin[0] == "trang":
                    self.trang.update(tin[1])
                    self._ve_danh_sach()
                elif tin[0] == "xong":
                    self.dang_ban = False
                elif tin[0] == "ban_moi":
                    self.ban_moi = tin[1]
                    self.nut_cap_nhat.config(text=f"Cập nhật lên v{tin[1]['phien_ban']}", bg=UI_DO, fg="#ffffff")
                elif tin[0] == "goi":
                    try:
                        tin[1]()
                    except Exception:
                        pass
                elif tin[0] == "thoat":
                    self.root.after(500, self.root.destroy)
        except queue.Empty:
            pass
        if not getattr(self, "dang_dong", False):
            self.root.after(100, self._xu_ly_hang_doi)

    def _kiem_trang(self, games, danh_muc, bao):
        kq = {}
        for i, g in enumerate(games):
            try:
                kq[khoa_game(g)] = self.ql.trang_thai(g, tim_goi(danh_muc, g))
            except Exception:
                kq[khoa_game(g)] = "chua_ho_tro"
        return kq

    def quet(self):
        def viec(bao):
            bao("Đang tìm game đã cài và tải danh mục Việt hóa...")
            games = tim_tat_ca(self.cfg.get("game_tay"))
            dm, moi = doc_danh_muc()
            self.q.put(("games", games, dm, moi))
            self.q.put(("trang", self._kiem_trang(games, dm, bao)))
            co = sum(1 for g in games if tim_goi(dm, g))
            return f"Tìm thấy {len(games)} game • {co} game có Việt hóa" + (
                "" if moi else " • (không tải được danh mục mới – dùng danh mục cũ)")
        self._nen(viec, lambda kq: kq)

    def _cap_nhat_mot(self, g):
        self.q.put(("trang", {khoa_game(g): self.ql.trang_thai(g, tim_goi(self.danh_muc, g))}))

    def cai(self, g, goi):
        def viec(bao):
            p = self.ql.tai_goi(goi, bao)
            self.ql.cai(g, goi, p, bao)
            self._cap_nhat_mot(g)
        self._nen(viec, f"Đã cài {'gói thử' if goi.get('thu_nghiem') else 'Việt hóa'} cho {g['ten']} ✓")

    def _hoi_goi_thu(self, g, thu):
        if self.messagebox.askyesno(
                "Cài gói thử",
                f"Gói thử chỉ THÊM file {', '.join(thu.get('tep_mau', ['VIET_HOA_THU.txt']))} vào thư mục game "
                f"\"{g['ten']}\" để kiểm tra launcher, không sửa file nào của game.\n\n"
                "Sau đó bấm \"Khôi phục bản gốc\" để gỡ.\n\nCài thử?"):
            self.cai(g, thu)

    def khoi_phuc(self, g):
        if not self.messagebox.askyesno("Khôi phục bản gốc",
                                        f"Gỡ Việt hóa và trả \"{g['ten']}\" về file gốc?"):
            return

        def viec(bao):
            self.ql.khoi_phuc(g, bao)
            self._cap_nhat_mot(g)
        self._nen(viec, f"Đã khôi phục bản gốc cho {g['ten']} ✓")

    def them_tay(self):
        p = self.filedialog.askdirectory(title="Chọn thư mục cài game (thư mục có file .exe của game)")
        if not p:
            return
        p = os.path.normpath(p)
        if not any(os.path.normcase(x["thu_muc"]) == os.path.normcase(p) for x in self.cfg["game_tay"]):
            self.cfg["game_tay"].append({"ten": os.path.basename(p), "thu_muc": p})
            ghi_json(FILE_CAU_HINH, self.cfg)
        self.quet()

    def bo_tay(self, g):
        self.cfg["game_tay"] = [x for x in self.cfg["game_tay"]
                                if os.path.normcase(os.path.normpath(x["thu_muc"])) != g["ma"]]
        ghi_json(FILE_CAU_HINH, self.cfg)
        self.quet()

    def _doi_loc(self):
        self.cfg["chi_co_viet_hoa"] = bool(self.bien_loc.get())
        ghi_json(FILE_CAU_HINH, self.cfg)
        self._ve_danh_sach()

    def _quyen_quan_tri(self):
        try:
            if chay_quyen_quan_tri():
                self.root.after(300, self.root.destroy)
        except Exception as e:
            self._bao(f"Không mở được quyền quản trị: {e}", UI_LOI)

    def _kiem_tra_cap_nhat(self):
        try:
            tt = lay_ban_moi()
            if so_phien_ban(tt["phien_ban"]) > so_phien_ban(APP_VERSION):
                self.q.put(("ban_moi", tt))
        except Exception:
            pass

    def cap_nhat(self):
        if not self.ban_moi:
            def viec(bao):
                bao("Đang kiểm tra bản mới...")
                tt = lay_ban_moi()
                if so_phien_ban(tt["phien_ban"]) > so_phien_ban(APP_VERSION):
                    self.q.put(("ban_moi", tt))
                    return f"Có bản mới v{tt['phien_ban']} – bấm nút Cập nhật"
                return f"Bạn đang dùng bản mới nhất (v{APP_VERSION})"
            self._nen(viec, lambda kq: kq)
            return
        tt = self.ban_moi

        def viec(bao):
            ap_dung_cap_nhat(tt, bao)
            self.q.put(("thoat",))
        self._nen(viec, "Đang khởi động lại bản mới...")

    # ---------------------------------------------------------- Viet hoa Crimson Desert bang Claude
    def mo_cd(self, g):
        import viet_hoa_cd as vcd
        tk = self.tk
        if getattr(self, "cua_so_cd", None) is not None:
            try:
                self.cua_so_cd.lift()
                return
            except Exception:
                pass
        w = tk.Toplevel(self.root)
        self.cua_so_cd = w
        w.title("Việt hóa Crimson Desert")
        w.configure(bg=UI_NEN, padx=18, pady=14)
        w.geometry("640x520")
        w.protocol("WM_DELETE_WINDOW", lambda: self._dong_cd(w))
        nhan = lambda chu, mau=UI_CHU, co=10, dam=False: tk.Label(
            w, text=chu, bg=UI_NEN, fg=mau, font=("Segoe UI", co, "bold" if dam else "normal"),
            anchor="w", justify="left", wraplength=600)
        hang0 = tk.Frame(w, bg=UI_NEN)
        hang0.pack(fill="x")
        self.cd_dot = 1
        self.cd_nut_dot = {}
        for d in sorted(vcd.DOT):
            b = self._nut(hang0, f"Đợt {d}", lambda d=d: self._chon_dot(d), nho=True)
            b.pack(side="left", padx=(0, 4))
            self.cd_nut_dot[d] = b
        self.cd_ten_dot = nhan(vcd.DOT[1]["ten"], co=12, dam=True)
        self.cd_ten_dot.pack(fill="x", pady=(8, 0))
        nhan("• Giữ nguyên tiếng Anh: tên nhân vật, tên riêng, tên vật phẩm.\n"
             "• Dùng mã Claude của app Dịch Game trên máy này. Đã dịch câu nào thì lưu lại, "
             "lần sau chỉ dịch câu mới.\n"
             "• Kết quả là gói zip để nhập vào DMM (game 2.04+ không cho sửa file trực tiếp). "
             "Vào game để ngôn ngữ English.", UI_PHU, 9).pack(fill="x", pady=(6, 10))
        self.cd_tk = nhan("Đang đọc chữ của game...", UI_CHU, 10)
        self.cd_tk.pack(fill="x")
        hang_m = tk.Frame(w, bg=UI_NEN)
        hang_m.pack(fill="x", pady=(12, 0))
        tk.Label(hang_m, text="Máy dịch:", bg=UI_NEN, fg=UI_CHU, font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.cd_may = "claude"
        self.cd_nut_may = {}
        for k, chu in (("claude", "Claude (tốn tiền, hay hơn)"), ("offline", "Offline (miễn phí)")):
            b = self._nut(hang_m, chu, lambda k=k: self._chon_may(k), nho=True)
            b.pack(side="left", padx=2)
            self.cd_nut_may[k] = b
        hang = tk.Frame(w, bg=UI_NEN)
        hang.pack(fill="x", pady=(8, 4))
        tk.Label(hang, text="Giới hạn tiền mỗi lần chạy:", bg=UI_NEN, fg=UI_CHU,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        self.cd_gh = 2.0
        self.cd_nut_gh = {}
        for v in (1.0, 2.0, 5.0):
            b = self._nut(hang, f"${v:.0f}", lambda v=v: self._chon_gh(v), nho=True)
            b.pack(side="left", padx=2)
            self.cd_nut_gh[v] = b
        self._chon_gh(2.0)
        hang2 = tk.Frame(w, bg=UI_NEN)
        hang2.pack(fill="x", pady=10)
        self.cd_nut_chay = self._nut(hang2, "Bắt đầu dịch", lambda: self._cd_chay(g), chinh=True)
        self.cd_nut_chay.pack(side="left")
        self._nut(hang2, "Tạm dừng", self._cd_dung).pack(side="left", padx=6)
        self._nut(hang2, "Xuất gói cho DMM", lambda: self._cd_xuat(g)).pack(side="left")
        hang3 = tk.Frame(w, bg=UI_NEN)
        hang3.pack(fill="x", pady=(2, 6))
        self._nut(hang3, "Lồng tiếng Kliff – trích file giọng (thử)", lambda: self._cd_trich_giong(g),
                  nho=True).pack(side="left")
        self._nut(hang3, "Đóng gói giọng Việt cho DMM (thử)", lambda: self._cd_dong_giong(g),
                  nho=True).pack(side="left", padx=6)
        self.cd_tien_do = nhan("", UI_VANG, 10)
        self.cd_tien_do.pack(fill="x", pady=(6, 0))
        self.cd_viec = None
        self.cd_dang_chay = False
        self._chon_dot(1)

        def nap():
            try:
                viec = vcd.ViecDich(g["thu_muc"], 1).nap()
                self.q.put(("goi", lambda: self._cd_da_nap(viec)))
            except Exception as e:
                self.q.put(("goi", lambda e=e: self.cd_tk.config(text=f"Lỗi đọc game: {e}", fg=UI_LOI)))
        threading.Thread(target=nap, daemon=True).start()

    def _chon_dot(self, d):
        import viet_hoa_cd as vcd
        if self.cd_dang_chay:
            self.cd_tien_do.config(text="Đang dịch – bấm Tạm dừng trước khi đổi đợt.", fg=UI_VANG)
            return
        self.cd_dot = d
        for k, b in self.cd_nut_dot.items():
            b.config(bg=UI_DO if k == d else UI_O)
            b.bind("<Leave>", lambda e, b=b, k=k: b.config(bg=UI_DO if k == self.cd_dot else UI_O))
        self.cd_ten_dot.config(text=vcd.DOT[d]["ten"])
        self._chon_may("offline" if d >= 2 else "claude", ve=False)
        if self.cd_viec is not None:
            self.cd_viec.dot = d
            self._cd_da_nap(self.cd_viec)

    def _chon_may(self, k, ve=True):
        if self.cd_dang_chay:
            return
        self.cd_may = k
        for m, b in self.cd_nut_may.items():
            b.config(bg=UI_DO if m == k else UI_O)
            b.bind("<Leave>", lambda e, b=b, m=m: b.config(bg=UI_DO if m == self.cd_may else UI_O))
        if ve and self.cd_viec is not None:
            self._cd_da_nap(self.cd_viec)

    def _chon_gh(self, v):
        self.cd_gh = v
        for k, b in self.cd_nut_gh.items():
            b.config(bg=UI_DO if k == v else UI_O)
            b.bind("<Leave>", lambda e, b=b, k=k: b.config(bg=UI_DO if k == self.cd_gh else UI_O))

    def _cd_da_nap(self, viec):
        import viet_hoa_cd as vcd
        self.cd_viec = viec
        viec.dot = self.cd_dot
        tk_ = viec.thong_ke()
        gia, _ = vcd.doc_gia()
        usd = vcd.ViecDich.uoc_tinh_usd(tk_["ky_tu_con"], gia)
        dau = (f"{tk_['tong']:,} câu khác nhau • đã dịch {tk_['da_dich']:,} • còn {tk_['con']:,} câu "
               f"({tk_['ky_tu_con']:,} ký tự)\n")
        if self.cd_may == "offline":
            ok, ly_do = vcd.co_offline()
            duoi = ("Dịch offline bằng CPU: miễn phí, chất lượng vừa phải, mất khoảng "
                    f"{max(1, tk_['ky_tu_con'] // 60000)}–{max(2, tk_['ky_tu_con'] // 25000)} phút."
                    if ok else f"⚠ Không dịch offline được: {ly_do}")
        else:
            duoi = (f"Ước tính chi phí phần còn lại: khoảng {usd:.2f} USD (≈ {usd * 26000:,.0f}đ)"
                    + ("" if vcd.doc_khoa_claude() else
                       "\n⚠ Chưa có mã Claude: mở app Dịch Game, dán mã vào ô rồi bấm Lưu mã."))
        self.cd_tk.config(fg=UI_CHU, text=(dau + duoi).replace(",", "."))

    def _cd_chay(self, g):
        import viet_hoa_cd as vcd
        if self.cd_viec is None or self.cd_dang_chay:
            return
        khoa = vcd.doc_khoa_claude()
        if self.cd_may == "claude" and not khoa:
            self.cd_tien_do.config(text="Chưa có mã Claude – lưu mã trong app Dịch Game trước.", fg=UI_LOI)
            return
        self.cd_dang_chay = True
        self.cd_nut_chay.config(text="Đang dịch...")
        viec = self.cd_viec
        gh = self.cd_gh
        bat_dau = time.time()

        def bao(s):
            self.q.put(("goi", lambda s=s: self.cd_tien_do.config(text=s, fg=UI_VANG)))

        def tien_do(xong, tong, tien):
            con = (time.time() - bat_dau) / max(xong, 1) * (tong - xong)
            chu = (f"Đã dịch {xong:,}/{tong:,} câu ({xong * 100 // tong}%) • "
                   + (f"đã tốn {tien:.3f} USD " if self.cd_may == "claude" else "offline, miễn phí ")
                   + f"• còn khoảng {con / 60:.0f} phút").replace(",", ".")
            self.q.put(("goi", lambda: self.cd_tien_do.config(text=chu, fg=UI_VANG)))

        def chay():
            try:
                xong = (viec.chay_offline(bao, tien_do) if self.cd_may == "offline"
                        else viec.chay(khoa, gh, bao, tien_do))
                if xong:
                    bao(f"Dịch xong đợt {viec.dot} ✓ (tốn {viec.tien:.3f} USD). Bấm \"Xuất gói cho DMM\".")
            except Exception as e:
                bao(f"Lỗi: {e}")
            finally:
                self.q.put(("goi", lambda: (setattr(self, "cd_dang_chay", False),
                                            self.cd_nut_chay.config(text="Bắt đầu dịch"),
                                            self._cd_da_nap(viec))))
        threading.Thread(target=chay, daemon=True).start()

    def _cd_dung(self):
        if self.cd_viec is not None and self.cd_dang_chay:
            self.cd_viec.dung.set()
            self.cd_tien_do.config(text="Đang dừng sau các lô đang dịch dở...", fg=UI_VANG)

    def _cd_xuat(self, g):
        if self.cd_viec is None:
            return
        if self.cd_dang_chay:
            self.cd_tien_do.config(text="Đợi dịch xong hoặc bấm Tạm dừng trước khi xuất gói.", fg=UI_VANG)
            return
        p = os.path.join(thu_muc_desktop(), "VietHoa_CrimsonDesert.zip")
        viec = self.cd_viec

        def xuat():
            try:
                tk_ = viec.xuat_goi(p)
                so = sum(tk_.values())
                self.q.put(("goi", lambda: self.cd_tien_do.config(
                    text=f"Đã xuất gói ({so:,} câu tiếng Việt) ra Desktop: VietHoa_CrimsonDesert.zip\n"
                         "Trong DMM: tắt gói thử cũ → Import file này → bật → Mount Mods.".replace(",", "."),
                    fg=UI_XANH)))
                try:
                    subprocess.Popen(["explorer", "/select,", p])
                except Exception:
                    pass
            except Exception as e:
                self.q.put(("goi", lambda e=e: self.cd_tien_do.config(text=f"Lỗi xuất gói: {e}", fg=UI_LOI)))
        threading.Thread(target=xuat, daemon=True).start()

    def _cd_trich_giong(self, g):
        if self.cd_viec is None or self.cd_dang_chay:
            return
        ra = os.path.join(thu_muc_desktop(), "LongTieng_Kliff")
        viec = self.cd_viec
        self.cd_dang_chay = True

        def bao(s):
            self.q.put(("goi", lambda s=s: self.cd_tien_do.config(text=s, fg=UI_VANG)))

        def chay():
            try:
                kq = viec.trich_giong_kliff(ra, bao)
                m = kq["mau"]
                chu = (f"Đã lấy {kq['so']:,} câu thoại Kliff ({kq['co_viet']:,} câu đã có bản Việt hóa) "
                       f"ra Desktop\\LongTieng_Kliff.\n"
                       f"Định dạng giọng gốc: {m.get('ten_codec', '?')} • {m.get('tan_so', '?')} Hz • "
                       f"{m.get('kenh', '?')} kênh. Chụp dòng này gửi Claude.").replace(",", ".")
                self.q.put(("goi", lambda: self.cd_tien_do.config(text=chu, fg=UI_XANH)))
                try:
                    subprocess.Popen(["explorer", ra])
                except Exception:
                    pass
            except Exception as e:
                bao(f"Lỗi trích giọng: {e}")
            finally:
                self.q.put(("goi", lambda: setattr(self, "cd_dang_chay", False)))
        threading.Thread(target=chay, daemon=True).start()

    def _cd_dong_giong(self, g):
        if self.cd_viec is None or self.cd_dang_chay:
            return
        import viet_hoa_cd as vcd
        thu = os.path.join(thu_muc_desktop(), "LongTieng_Kliff")
        for khac in (os.path.join(os.environ.get("USERPROFILE") or "", "Desktop", "LongTieng_Kliff"),
                     os.path.join(os.environ.get("OneDrive") or "", "Desktop", "LongTieng_Kliff")):
            dv = os.path.join(thu, "wav_tieng_viet")
            co_wav = os.path.isdir(dv) and any(x.lower().endswith(".wav") for x in os.listdir(dv))
            dk = os.path.join(khac, "wav_tieng_viet")
            if not co_wav and os.path.isdir(dk) and any(x.lower().endswith(".wav") for x in os.listdir(dk)):
                thu = khac
                break
        wwise = vcd.ViecDich.tim_wwise_console()
        if not wwise:
            p = self.filedialog.askopenfilename(title="Chọn WwiseConsole.exe (trong thư mục cài Wwise\\Authoring\\x64\\Release\\bin)",
                                                filetypes=[("WwiseConsole.exe", "WwiseConsole.exe")])
            if not p:
                return
            wwise = p
        zip_ra = os.path.join(thu_muc_desktop(), "LongTieng_Kliff_DMM.zip")
        viec = self.cd_viec
        self.cd_dang_chay = True

        def bao(s):
            self.q.put(("goi", lambda s=s: self.cd_tien_do.config(text=s, fg=UI_VANG)))

        def chay():
            try:
                dong = viec.dong_goi_giong(thu, zip_ra, wwise, bao)
                chu = ("Đã tạo Desktop\\LongTieng_Kliff_DMM.zip – Import vào DMM, bật, Mount Mods rồi vào game nghe thử.\n"
                       + "\n".join(dong[:12]))
                self.q.put(("goi", lambda: self.cd_tien_do.config(text=chu, fg=UI_XANH)))
            except Exception as e:
                bao(f"Lỗi đóng gói giọng: {e}")
            finally:
                self.q.put(("goi", lambda: setattr(self, "cd_dang_chay", False)))
        threading.Thread(target=chay, daemon=True).start()

    def _dong_cd(self, w):
        if self.cd_dang_chay and self.cd_viec is not None:
            self.cd_viec.dung.set()
        self.cua_so_cd = None
        w.destroy()

    def dong(self):
        if getattr(self, "cua_so_cd", None) is not None:
            try:
                self._dong_cd(self.cua_so_cd)
            except Exception:
                pass
        self.dang_dong = True
        try:
            self.root.destroy()
        except Exception:
            pass
        if self.khi_dong:
            self.khi_dong()

    def chay(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().chay()
