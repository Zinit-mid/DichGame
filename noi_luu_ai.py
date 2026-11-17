"""Chuyen cac thu muc AI nang (mo hinh dich offline, Python + AI nghe tieng cua Phu de phim) sang o khac.
Du lieu that nam o o moi; cho cu tren o C la mot "loi tat thu muc" (junction) -> app khong can doi duong dan."""
import os
import shutil
import subprocess

GOC_DICHGAME = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DichGame")
GOC_VIETHOA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "VietHoaGame")
THU_MUC_CHA = "DichGame_AI"


def cac_muc():
    """[(ten hien thi, duong dan app dung, ten thu muc o noi moi)]"""
    return [("Mô hình dịch offline", os.path.join(GOC_DICHGAME, "mo_hinh"), "mo_hinh_dich_offline"),
            ("Phụ đề phim (Python + AI nghe tiếng)", os.path.join(GOC_VIETHOA, "phim"), "phu_de_phim")]


def la_loi_tat(p):
    try:
        if hasattr(os.path, "isjunction") and os.path.isjunction(p):
            return True
    except OSError:
        pass
    return os.path.islink(p)


def noi_that(p):
    return os.path.realpath(p)


def dung_luong(p):
    tong = 0
    for g, _, ts in os.walk(p):
        for t in ts:
            try:
                tong += os.path.getsize(os.path.join(g, t))
            except OSError:
                pass
    return tong


def _tao_loi_tat(lien_ket, dich):
    if os.name != "nt":
        os.symlink(dich, lien_ket, target_is_directory=True)
        return
    r = subprocess.run(["cmd", "/c", "mklink", "/J", lien_ket, dich], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, creationflags=0x08000000)
    if r.returncode != 0 or not os.path.isdir(lien_ket):
        raise OSError("không tạo được lối tắt thư mục: " + r.stdout.decode("utf-8", "replace").strip())


def chuyen(goc, dich, bao=lambda s: None):
    """Chuyen du lieu cua thu muc app dung `goc` sang `dich` (thu muc moi), roi dat loi tat goc -> dich."""
    cu = noi_that(goc)
    if os.path.normcase(os.path.abspath(cu)) == os.path.normcase(os.path.abspath(dich)):
        return "đã ở đúng chỗ"
    if os.path.normcase(os.path.abspath(dich)).startswith(os.path.normcase(os.path.abspath(cu)) + os.sep):
        raise OSError("không thể chuyển vào bên trong chính nó")
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    co_du_lieu = os.path.isdir(cu)
    if co_du_lieu:
        tong = max(1, dung_luong(cu))
        da = [0]

        def chep(a, b):
            shutil.copy2(a, b)
            da[0] += os.path.getsize(b)
            bao(f"Đang chép: {da[0] / 1e9:.2f}/{tong / 1e9:.2f} GB")
        shutil.copytree(cu, dich, copy_function=chep, dirs_exist_ok=True)
    else:
        os.makedirs(dich, exist_ok=True)
    # bo cho cu (loi tat thi chi go loi tat; thu muc that thi xoa – du lieu da chep sang dich)
    if la_loi_tat(goc):
        os.unlink(goc) if os.path.islink(goc) else os.rmdir(goc)   # chi go loi tat, khong dung du lieu
    elif os.path.isdir(goc):
        try:
            shutil.rmtree(goc)
        except OSError as e:
            raise OSError(f"không xóa được dữ liệu cũ (đang có phần mềm dùng?) – đóng phần đang dịch / "
                          f"tạo phụ đề rồi thử lại ({e})")
    os.makedirs(os.path.dirname(goc), exist_ok=True)
    _tao_loi_tat(goc, dich)
    if co_du_lieu and os.path.normcase(cu) != os.path.normcase(os.path.abspath(goc)) and os.path.isdir(cu):
        shutil.rmtree(cu, ignore_errors=True)        # du lieu o noi cu (lan chuyen truoc)
    return "xong"


def chuyen_het(thu_muc_cha, bao=lambda s: None):
    """Chuyen tat ca muc sang <thu_muc_cha>\\DichGame_AI\\... -> [(ten, ket qua)]"""
    kq = []
    for ten, goc, ten_moi in cac_muc():
        bao(f"Đang chuyển: {ten}...")
        try:
            kq.append((ten, chuyen(goc, os.path.join(thu_muc_cha, THU_MUC_CHA, ten_moi), bao)))
        except OSError as e:
            kq.append((ten, f"lỗi: {e}"))
    return kq
