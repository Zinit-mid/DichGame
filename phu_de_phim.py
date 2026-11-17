"""Phu de phim tieng Viet: link YouTube / trang video hoac file phim tren may
-> tai ve (yt-dlp) -> nghe ra chu (faster-whisper tren card man hinh) -> dich (Claude / offline)
-> file .srt cung ten dat canh phim -> mo phim bang trinh phat mac dinh (VLC, PotPlayer... tu nhan phu de).

Cong cu AI chay bang Python cua app VieNeu (da co tren may). Thu vien rieng cai vao
%APPDATA%\\VietHoaGame\\phim\\_thu_vien (pip --target) -> khong dung cham VieNeu."""
import hashlib
import json
import os
import queue
import re
import subprocess
import threading
import time

import viet_hoa_cd as vcd
from viet_hoa_cd import LoiDung

THU_MUC = os.path.join(vcd.DU_LIEU, "phim")
THU_VIEN = os.path.join(THU_MUC, "_thu_vien")
MO_HINH_DIR = os.path.join(THU_MUC, "_mo_hinh")
BAN_THU_VIEN = "1"
GOI_PIP = ["faster-whisper>=1.1.0", "yt-dlp[default]", "imageio-ffmpeg", "deno"]
GOI_CUDA = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12==9.*"]

HUONG_DAN_PHIM = """Bạn là dịch giả phụ đề phim chuyên nghiệp. Bạn nhận một mảng JSON các dòng phụ đề \
(theo đúng thứ tự trong phim, có thể là tiếng Anh hoặc ngôn ngữ khác) và trả về mảng JSON bản dịch tiếng Việt.

Quy tắc bắt buộc:
- CHỈ trả về một mảng JSON hợp lệ, CÙNG SỐ PHẦN TỬ, CÙNG THỨ TỰ. Không giải thích, không ```.
- Mỗi phần tử dịch đúng dòng tương ứng; dựa vào các dòng trước / sau để hiểu ngữ cảnh, xưng hô cho tự nhiên.
- Văn phong phụ đề Việt: ngắn gọn, tự nhiên, dễ đọc nhanh; xưng hô hợp quan hệ nhân vật.
- Giữ nguyên tên người, địa danh, thương hiệu. Dòng có thể bị nghe sai chính tả – đoán nghĩa hợp lý theo ngữ cảnh.
- Dòng chỉ là tiếng động / nhạc / vô nghĩa thì dịch ngắn gọn hoặc trả về nguyên văn.
"""

KICH_BAN = r'''
import json, os, sys, time
cfg = json.load(open(sys.argv[1], encoding="utf-8"))
sys.path.insert(0, cfg["lib"])
for d in cfg.get("dll", []):
    if os.path.isdir(d):
        try:
            os.add_dll_directory(d)
        except Exception:
            pass
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

def bao(*a):
    print(*a, flush=True)

nguon = cfg["nguon"]
if cfg.get("tai"):
    import yt_dlp, imageio_ffmpeg
    def moc(d):
        if d.get("status") == "downloading":
            tong = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if tong:
                bao("TAI", round(d.get("downloaded_bytes", 0) * 100 / tong, 1))
    tuy = {"outtmpl": os.path.join(cfg["thu_muc_tai"], "%(title).80s [%(id)s].%(ext)s"),
           "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*[height<=1080]+ba/b",
           "merge_output_format": "mp4", "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
           "progress_hooks": [moc], "noplaylist": True, "quiet": True, "no_warnings": True,
           "windowsfilenames": True}
    for g, _, ts in os.walk(cfg["lib"]):
        if "deno.exe" in ts or "deno" in ts:
            tuy["js_runtimes"] = {"deno": {"path": os.path.join(g, "deno.exe" if "deno.exe" in ts else "deno")}}
            break
    with yt_dlp.YoutubeDL(tuy) as y:
        tt = y.extract_info(nguon, download=True)
        p = y.prepare_filename(tt)
        if not os.path.isfile(p):
            p = os.path.splitext(p)[0] + ".mp4"
    bao("FILE", json.dumps({"duong_dan": p, "ten": tt.get("title", "")}, ensure_ascii=False))
    nguon = p
if cfg.get("chi_tai"):
    sys.exit(0)

from faster_whisper import WhisperModel
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
m = None
if cfg.get("gpu", True):
    try:
        m = WhisperModel(cfg["mo_hinh"], device="cuda", compute_type="float16", download_root=cfg["mo_hinh_dir"])
        bao("THIET_BI cuda")
    except Exception as e:
        bao("KHONG_CUDA", str(e)[:300])
        if not cfg.get("cho_cpu"):
            sys.exit(3)
if m is None:
    m = WhisperModel(cfg.get("mo_hinh_cpu", "small"), device="cpu", compute_type="int8",
                     cpu_threads=max(2, (os.cpu_count() or 4) - 2), download_root=cfg["mo_hinh_dir"])
    bao("THIET_BI cpu")
doan, tt = m.transcribe(nguon, language=cfg.get("ngon_ngu") or None, vad_filter=True,
                        word_timestamps=True, beam_size=5, condition_on_previous_text=False)
bao("NGON_NGU", tt.language, round(tt.duration, 1))
ra = []
for s in doan:
    ra.append({"a": s.start, "b": s.end, "chu": s.text,
               "tu": [[w.start, w.end, w.word] for w in (s.words or [])]})
    bao("TIEN", round(s.end, 1), round(tt.duration, 1))
with open(cfg["ra"], "w", encoding="utf-8") as f:
    json.dump({"ngon_ngu": tt.language, "giay": tt.duration, "doan": ra}, f, ensure_ascii=False)
bao("HET")
'''


# ---------------------------------------------------------------- chia dong / srt
def chia_dong(doan, toi_da_giay=6.0, toi_da_chu=84):
    """Doan Whisper (co moc thoi gian tung tu) -> cac dong phu de ngan [(a, b, chu)]."""
    ra = []
    for d in doan:
        tu = d.get("tu") or []
        if not tu:
            if d.get("chu", "").strip():
                ra.append((d["a"], d["b"], d["chu"].strip()))
            continue
        cur = []
        for i, w in enumerate(tu):
            cur.append(w)
            chu = "".join(x[2] for x in cur).strip()
            dai = cur[-1][1] - cur[0][0]
            het_cau = w[2].strip().endswith((".", "?", "!", "。", "？", "！")) and len(chu) >= 15
            phay = w[2].strip().endswith((",", ";", ":", "，")) and (dai >= toi_da_giay * 0.6 or len(chu) >= toi_da_chu * 0.6)
            if het_cau or phay or dai >= toi_da_giay or len(chu) >= toi_da_chu or i == len(tu) - 1:
                if chu:
                    ra.append((cur[0][0], cur[-1][1], chu))
                cur = []
    # noi dong qua ngan voi dong sau (< 0.6 giay va sat nhau)
    gon = []
    for a, b, c in ra:
        if gon and (gon[-1][1] - gon[-1][0] < 0.6) and a - gon[-1][1] < 0.3 and len(gon[-1][2]) + len(c) < 84:
            pa, _, pc = gon.pop()
            gon.append((pa, b, pc + " " + c))
        else:
            gon.append((a, b, c))
    return gon


def _gio(s):
    s = max(0.0, s)
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def xuong_dong(chu, rong=42):
    if len(chu) <= rong:
        return chu
    giua = len(chu) // 2
    vt = [i for i, ch in enumerate(chu) if ch == " "]
    if not vt:
        return chu
    i = min(vt, key=lambda x: abs(x - giua))
    return chu[:i].strip() + "\n" + chu[i:].strip()


def ghi_srt(duong_dan, dong):
    """dong: [(a, b, chu)] -> file .srt (UTF-8 co BOM de trinh phat Windows doc dung dau)."""
    ra = []
    for i, (a, b, c) in enumerate(dong, 1):
        nxt = dong[i][0] - 0.05 if i < len(dong) else float("inf")
        b2 = max(min(b + 0.4, nxt), min(a + 0.8, nxt), a + 0.2)   # hien lau them chut, khong de len dong sau
        ra.append(f"{i}\n{_gio(a)} --> {_gio(b2)}\n{xuong_dong(c)}\n")
    with open(duong_dan, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(ra))


def la_link(s):
    return bool(re.match(r"^\s*https?://", s or ""))


# ---------------------------------------------------------------- cong viec
class ViecPhim(vcd.ViecDich):
    HUONG_DAN = HUONG_DAN_PHIM

    def __init__(self, nguon):
        super().__init__("", 1)
        self.nguon = nguon.strip().strip('"')
        ma = hashlib.md5(self.nguon.encode("utf-8")).hexdigest()[:12]
        self.tm = os.path.join(THU_MUC, ma)
        os.makedirs(self.tm, exist_ok=True)
        self.file_bo_nho = os.path.join(self.tm, "bo_nho_dich.json")
        self.file_chu = os.path.join(self.tm, "chu_goc.json")
        self.file_phim = os.path.join(self.tm, "phim.json")
        self.bang_ten = vcd.BangTen(set())
        self.dong = []
        self.phim = None              # {"duong_dan", "ten"}
        try:
            with open(self.file_bo_nho, encoding="utf-8") as f:
                self.bo_nho = json.load(f)
        except Exception:
            self.bo_nho = {}
        try:
            with open(self.file_phim, encoding="utf-8") as f:
                self.phim = json.load(f)
            if not os.path.isfile(self.phim.get("duong_dan", "")):
                self.phim = None
        except Exception:
            pass
        if not la_link(self.nguon) and os.path.isfile(self.nguon):
            self.phim = {"duong_dan": self.nguon, "ten": os.path.basename(self.nguon)}
        self._nap_chu()

    def _nap_chu(self):
        try:
            with open(self.file_chu, encoding="utf-8") as f:
                d = json.load(f)
            self.dong = chia_dong(d["doan"])
            self.ngon_ngu = d.get("ngon_ngu")
        except Exception:
            self.dong = []

    def luu(self):
        with self.khoa:
            du = json.dumps(self.bo_nho, ensure_ascii=False)
        with open(self.file_bo_nho + ".tam", "w", encoding="utf-8") as f:
            f.write(du)
        os.replace(self.file_bo_nho + ".tam", self.file_bo_nho)

    def nen_dich(self, f, v, dot=None):
        return bool(v and re.search(r"\w", v))

    def _chuoi_cua_dot(self):
        for _, _, c in self.dong:
            if self.nen_dich(None, c):
                yield c

    # ---------- cong cu AI
    @staticmethod
    def tim_python():
        vn = vcd.ViecDich.tim_vieneu()
        if not vn:
            raise LoiDung("cần app VieNeu (bản GPU) đã cài trên máy – app dùng Python của VieNeu để chạy AI nghe tiếng")
        return vn

    def chuan_bi(self, bao, can_cuda=False):
        """Cai thu vien (lan dau / khi thieu CUDA) vao THU_VIEN bang pip cua Python VieNeu."""
        py, _, _ = self.tim_python()
        dau = os.path.join(THU_VIEN, "_xong_" + BAN_THU_VIEN + ("_cuda" if can_cuda else "") + ".txt")
        if os.path.isfile(dau):
            return
        goi = GOI_CUDA if can_cuda else GOI_PIP
        bao("Lần đầu: đang tải công cụ nghe tiếng (" + ("thư viện CUDA ~1,2 GB" if can_cuda else "~200 MB") +
            ") – chờ vài phút...")
        os.makedirs(THU_VIEN, exist_ok=True)
        an = 0x08000000 if os.name == "nt" else 0
        r = subprocess.run([py, "-m", "pip", "install", "--upgrade", "--target", THU_VIEN, "--ignore-installed",
                            "--no-warn-script-location", "--disable-pip-version-check"] + goi,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=an)
        with open(os.path.join(THU_MUC, "pip_nhat_ky.txt"), "ab") as f:
            f.write(r.stdout or b"")
        if r.returncode != 0:
            raise LoiDung("không tải được công cụ (cần mạng) – xem " + os.path.join(THU_MUC, "pip_nhat_ky.txt"))
        with open(dau, "w") as f:
            f.write(time.strftime("%Y-%m-%d"))

    def _dll(self):
        py, _, _ = self.tim_python()
        venv = os.path.dirname(os.path.dirname(py))
        ds = [os.path.join(venv, "Lib", "site-packages", "torch", "lib")]
        nv = os.path.join(THU_VIEN, "nvidia")
        if os.path.isdir(nv):
            for t in os.listdir(nv):
                ds.append(os.path.join(nv, t, "bin"))
        return ds

    def _chay(self, cfg, bao, tien_do):
        py, _, gpu = self.tim_python()
        cfg = dict(cfg, lib=THU_VIEN, dll=self._dll(), mo_hinh_dir=MO_HINH_DIR, gpu=gpu)
        os.makedirs(MO_HINH_DIR, exist_ok=True)
        kb = os.path.join(THU_MUC, "nghe_phim.py")
        with open(kb, "w", encoding="utf-8") as f:
            f.write(KICH_BAN)
        vj = os.path.join(self.tm, "viec.json")
        with open(vj, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        an = 0x08000000 if os.name == "nt" else 0
        cuoi, kq = [], {}
        nk = os.path.join(self.tm, "nhat_ky.txt")
        with open(nk, "a", encoding="utf-8", errors="replace") as fnk:
            p = subprocess.Popen([py, "-I", kb, vj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env=env, cwd=self.tm, creationflags=an)
            for dong in iter(p.stdout.readline, b""):
                d = dong.decode("utf-8", "replace").rstrip()
                fnk.write(d + "\n")
                if self.dung.is_set():
                    p.kill()
                    break
                t = d.split(" ", 1)
                if t[0] == "TAI":
                    tien_do("tai", float(t[1]), 100)
                elif t[0] == "FILE":
                    kq["file"] = json.loads(t[1])
                elif t[0] == "TIEN":
                    a, b = (float(x) for x in t[1].split())
                    tien_do("nghe", a, b)
                elif t[0] == "THIET_BI":
                    kq["thiet_bi"] = t[1]
                    bao("Đang nghe tiếng bằng " + ("card màn hình" if t[1] == "cuda" else "CPU (chậm hơn)") + "...")
                elif t[0] == "KHONG_CUDA":
                    kq["khong_cuda"] = True
                elif t[0] == "NGON_NGU":
                    kq["ngon_ngu"] = t[1].split()[0]
                elif d.strip():
                    cuoi = (cuoi + [d])[-5:]
            p.wait()
        if self.dung.is_set():
            raise LoiDung("đã dừng")
        if p.returncode == 3 and kq.get("khong_cuda"):
            return kq
        if p.returncode != 0:
            raise LoiDung("công cụ nghe tiếng bị lỗi – xem " + nk + "\n" + "\n".join(cuoi[-3:]))
        return kq

    def tai_va_nghe(self, bao, tien_do, ngon_ngu=None):
        self.chuan_bi(bao)
        if self.phim is None:
            if not la_link(self.nguon):
                raise LoiDung("không thấy file phim")
            thu_tai = os.path.join(os.path.expanduser("~"), "Videos", "DichGame")
            os.makedirs(thu_tai, exist_ok=True)
            bao("Đang tải phim về...")
            kq = self._chay({"nguon": self.nguon, "tai": True, "chi_tai": True, "thu_muc_tai": thu_tai,
                             "mo_hinh": "large-v3-turbo", "ra": self.file_chu}, bao, tien_do)
            if not kq.get("file"):
                raise LoiDung("không tải được phim từ link này")
            self.phim = kq["file"]
            with open(self.file_phim, "w", encoding="utf-8") as f:
                json.dump(self.phim, f, ensure_ascii=False)
        if self.dong:
            return
        bao("Đang nạp AI nghe tiếng (lần đầu tải mô hình ~1,6 GB)...")
        cfg = {"nguon": self.phim["duong_dan"], "mo_hinh": "large-v3-turbo", "ngon_ngu": ngon_ngu,
               "ra": self.file_chu}
        kq = self._chay(cfg, bao, tien_do)
        if kq.get("khong_cuda") and not kq.get("thiet_bi"):
            # card man hinh chua chay duoc (thieu thu vien CUDA) -> cai them roi thu lai; van loi thi dung CPU
            try:
                self.chuan_bi(bao, can_cuda=True)
                kq = self._chay(cfg, bao, tien_do)
            except LoiDung:
                if self.dung.is_set():
                    raise
            if kq.get("khong_cuda") and not kq.get("thiet_bi"):
                bao("Card màn hình chưa dùng được – chạy bằng CPU (chậm hơn nhiều)...")
                self._chay(dict(cfg, cho_cpu=True), bao, tien_do)
        self._nap_chu()
        if not self.dong:
            raise LoiDung("không nghe được lời thoại nào trong phim")

    def dich(self, khoa, may, bao, tien_do):
        if may == "claude" and khoa:
            self.chay(khoa, 2.0, bao, lambda a, b, usd: tien_do("dich", a, b))
        else:
            self.chay_offline(bao, lambda a, b, usd: tien_do("dich", a, b))

    def xuat_srt(self):
        """-> duong dan file .srt tieng Viet canh phim (hoac trong thu muc app neu khong ghi duoc)."""
        dong = [(a, b, self.bo_nho.get(c) or c) for a, b, c in self.dong]
        goc = os.path.splitext(self.phim["duong_dan"])[0]
        for p in (goc + ".srt", os.path.join(self.tm, os.path.basename(goc) + ".srt")):
            try:
                ghi_srt(p, dong)
                ghi_srt(os.path.join(self.tm, "goc.srt"), self.dong)
                return p
            except OSError:
                continue
        raise LoiDung("không ghi được file phụ đề")


# ---------------------------------------------------------------- giao dien
class TrangPhim:
    def __init__(self, khung, f, p, mau):
        import tkinter as tk
        import giao_dien as gd
        self.tk, self.gd, self.f, self.p = tk, gd, f, p
        self.m = mau
        self.q = queue.Queue()
        self.viec = None
        self.dang = False
        nen = mau["nen"]
        P = p
        nhan = lambda cha, chu, mau_chu=mau["chu"], co=10, dam=False: tk.Label(
            cha, text=chu, bg=nen, fg=mau_chu, font=f(co, "bold" if dam else "normal"), anchor="w", justify="left")
        l = nhan(khung, "• Dán link phim (YouTube và đa số trang video) hoặc chọn file phim trên máy.\n"
                        "• App tải phim về, AI nghe lời thoại, dịch sang tiếng Việt và tạo phụ đề KHỚP TỪNG CÂU.\n"
                        "• Phim 2 tiếng mất khoảng 5–15 phút. Xong app tự mở phim kèm phụ đề tiếng Việt.\n"
                        "• Không dùng được cho Netflix / Disney+ (có khóa bản quyền).", mau["phu"], 10)
        l.pack(fill="x", pady=(0, P(10)))
        khung.bind("<Configure>", lambda e: l.config(wraplength=max(300, e.width - 40)), add="+")
        h = tk.Frame(khung, bg=nen)
        h.pack(fill="x")
        self.o = tk.Entry(h, bg=mau["o"], fg=mau["chu"], insertbackground=mau["chu"], relief="flat",
                          font=f(11))
        self.o.pack(side="left", fill="x", expand=True, ipady=P(6))
        self.o.bind("<Return>", lambda e: self.bat_dau())
        gd.NutTron(h, "Chọn file phim", self.chon_file, nho=True).pack(side="left", padx=(P(8), 0))
        h2 = tk.Frame(khung, bg=nen)
        h2.pack(fill="x", pady=P(10))
        nhan(h2, "Máy dịch:", co=10).pack(side="left")
        self.may = "claude" if vcd.doc_khoa_claude() else "offline"
        self.nut_may = {}
        for ma, ten in (("claude", "Claude (hay, vài nghìn đồng/phim)"), ("offline", "Offline (miễn phí)")):
            b = gd.NutTron(h2, ten, lambda ma=ma: self._chon_may(ma), nho=True)
            b.pack(side="left", padx=(P(6), 0))
            self.nut_may[ma] = b
        self._chon_may(self.may)
        h3 = tk.Frame(khung, bg=nen)
        h3.pack(fill="x")
        self.nut_chay = gd.NutTron(h3, "Tạo phụ đề tiếng Việt", self.bat_dau, kieu="chinh")
        self.nut_chay.pack(side="left")
        gd.NutTron(h3, "Dừng", self.dung, nho=True).pack(side="left", padx=P(8))
        self.nut_mo = gd.NutTron(h3, "Mở phim", self.mo_phim, nho=True)
        self.nut_mo.pack(side="left")
        gd.NutTron(h3, "Mở thư mục", self.mo_thu_muc, nho=True).pack(side="left", padx=P(8))
        self.lbl = nhan(khung, "", mau["phu"], 10)
        self.lbl.pack(fill="x", pady=(P(12), 0))
        khung.bind("<Configure>", lambda e: self.lbl.config(wraplength=max(300, e.width - 40)), add="+")
        self.khung = khung
        khung.after(150, self._xu_ly)

    def _chon_may(self, ma):
        self.may = ma
        for m, b in self.nut_may.items():
            b.dat_kieu("chinh" if m == ma else "thuong")

    def _bao(self, chu, mau=None):
        self.q.put((chu, mau or self.m["vang"]))

    def _xu_ly(self):
        try:
            while True:
                chu, mau = self.q.get_nowait()
                self.lbl.config(text=chu, fg=mau)
        except queue.Empty:
            pass
        self.khung.after(150, self._xu_ly)

    def chon_file(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Chọn file phim", filetypes=[
            ("Phim", "*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.ts *.flv *.wmv *.mp3 *.m4a *.wav"), ("Tất cả", "*.*")])
        if p:
            self.o.delete(0, "end")
            self.o.insert(0, os.path.normpath(p))

    def dung(self):
        if self.viec is not None:
            self.viec.dung.set()

    def mo_phim(self):
        v = self.viec
        if v and v.phim and os.path.isfile(v.phim["duong_dan"]):
            os.startfile(v.phim["duong_dan"])

    def mo_thu_muc(self):
        v = self.viec
        p = v.phim["duong_dan"] if v and v.phim else os.path.join(os.path.expanduser("~"), "Videos", "DichGame")
        try:
            if os.path.isfile(p):
                subprocess.Popen(["explorer", "/select,", p])
            else:
                os.makedirs(p, exist_ok=True)
                os.startfile(p)
        except Exception:
            pass

    def bat_dau(self):
        if self.dang:
            return
        nguon = self.o.get().strip().strip('"')
        if not nguon:
            self._bao("Dán link phim hoặc chọn file phim trước.", self.m["loi"])
            return
        if not la_link(nguon) and not os.path.isfile(nguon):
            self._bao("Không thấy file phim này.", self.m["loi"])
            return
        self.dang = True
        self.viec = ViecPhim(nguon)
        may, khoa = self.may, vcd.doc_khoa_claude()
        threading.Thread(target=self._chay, args=(self.viec, may, khoa), daemon=True).start()

    def _chay(self, v, may, khoa):
        bd = time.time()

        def tien_do(buoc, a, b):
            if buoc == "tai":
                self._bao(f"Đang tải phim: {a:.0f}%")
            elif buoc == "nghe":
                con = (time.time() - bd) / max(a, 1) * (b - a) if a > 30 else 0
                self._bao(f"AI đang nghe lời thoại: {a / 60:.0f}/{b / 60:.0f} phút phim"
                          + (f" • còn khoảng {con / 60:.0f} phút" if con else ""))
            else:
                self._bao(f"Đang dịch: {a}/{b} dòng")
        try:
            v.tai_va_nghe(self._bao, tien_do)
            self._bao(f"Đã nghe xong {len(v.dong)} dòng – đang dịch...")
            v.dich(khoa, may, self._bao, tien_do)
            srt = v.xuat_srt()
            con = v.cau_can_dich()
            chu = (f"Xong ✓ Phụ đề tiếng Việt: {srt}\n" +
                   (f"⚠ {len(con)} dòng chưa dịch được (giữ nguyên) – bấm Tạo phụ đề lần nữa để dịch tiếp.\n" if con else "") +
                   "Đang mở phim… Nếu không thấy phụ đề: mở bằng VLC / PotPlayer, hoặc kéo file .srt vào cửa sổ phim.")
            self._bao(chu, self.m["xanh"])
            try:
                os.startfile(v.phim["duong_dan"])
            except Exception:
                pass
        except Exception as e:
            self._bao(f"Không làm được: {e}", self.m["loi"])
        finally:
            self.dang = False
