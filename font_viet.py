# -*- coding: utf-8 -*-
"""
Them chu tieng Viet co dau vao font Scaleform (DefineFont3) cua game – vi du thu vien font "gfxfontlib" cua
Rise of the Tomb Raider (font DIN-Bold, chi co chu Latin-1).

Cach lam: giu nguyen kieu chu cua game – chu Viet duoc GHEP tu chu cai goc cua font (a, e, o, u, y...) + dau cua
chinh font (sac, huyen, nga, mu, trang, cham) ; dau hoi va rau (o, u) lay hinh tu font Be Vietnam Pro (OFL) cua app,
co lai cho vua kich thuoc. Rau / gach ngang chu "đ" duoc HOP (union) voi net chu de khong co vung chong len nhau.
"""
import struct
import unicodedata
import zlib


# ================================================================ doc / ghi bit SWF

class _BR:
    def __init__(s, b, p=0):
        s.b, s.p = b, p * 8

    def ub(s, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((s.b[s.p >> 3] >> (7 - (s.p & 7))) & 1)
            s.p += 1
        return v

    def sb(s, n):
        v = s.ub(n)
        if n and v & (1 << (n - 1)):
            v -= 1 << n
        return v

    def align(s):
        s.p = (s.p + 7) & ~7


class _BW:
    def __init__(s):
        s.o, s.cur, s.n = bytearray(), 0, 0

    def ub(s, n, v):
        for i in range(n - 1, -1, -1):
            s.cur = (s.cur << 1) | ((v >> i) & 1)
            s.n += 1
            if s.n == 8:
                s.o.append(s.cur)
                s.cur = s.n = 0

    def sb(s, n, v):
        s.ub(n, v & ((1 << n) - 1))

    def bytes(s):
        if s.n:
            s.o.append(s.cur << (8 - s.n))
            s.cur = s.n = 0
        return bytes(s.o)


def _bits(*vals):
    n = 1
    for v in vals:
        while not (-(1 << (n - 1)) <= v < (1 << (n - 1))):
            n += 1
    return n


def doc_hinh(b):
    """SHAPE cua 1 glyph -> danh sach duong vien, moi duong: [('M',x,y), ('L',x,y) | ('Q',cx,cy,x,y), ...]"""
    r = _BR(b)
    fb, lb = r.ub(4), r.ub(4)
    x = y = 0
    vien, cur = [], None
    while True:
        if r.ub(1) == 0:
            fl = r.ub(5)
            if fl == 0:
                break
            if fl & 1:
                n = r.ub(5)
                x, y = r.sb(n), r.sb(n)
                cur = [('M', x, y)]
                vien.append(cur)
            if fl & 2:
                r.ub(fb)
            if fl & 4:
                r.ub(fb)
            if fl & 8:
                r.ub(lb)
            if fl & 16:
                raise ValueError("glyph có kiểu tô mới – không hỗ trợ")
        else:
            thang = r.ub(1)
            n = r.ub(4) + 2
            if thang:
                if r.ub(1):
                    dx, dy = r.sb(n), r.sb(n)
                elif r.ub(1):
                    dx, dy = 0, r.sb(n)
                else:
                    dx, dy = r.sb(n), 0
                x, y = x + dx, y + dy
                cur.append(('L', x, y))
            else:
                cx, cy = x + r.sb(n), y + r.sb(n)
                x, y = cx + r.sb(n), cy + r.sb(n)
                cur.append(('Q', cx, cy, x, y))
    return vien


def ghi_hinh(vien):
    w = _BW()
    w.ub(4, 1)
    w.ub(4, 0)
    x = y = 0
    dau = True
    for c in vien:
        for op in c:
            if op[0] == 'M':
                nx, ny = int(round(op[1])), int(round(op[2]))
                w.ub(1, 0)
                w.ub(5, 1 | (2 if dau else 0))
                n = _bits(nx, ny)
                w.ub(5, n)
                w.sb(n, nx)
                w.sb(n, ny)
                if dau:
                    w.ub(1, 1)
                dau = False
                x, y = nx, ny
            elif op[0] == 'L':
                nx, ny = int(round(op[1])), int(round(op[2]))
                dx, dy = nx - x, ny - y
                x, y = nx, ny
                if not dx and not dy:
                    continue
                w.ub(1, 1)
                w.ub(1, 1)
                if dx and dy:
                    n = max(2, _bits(dx, dy))
                    w.ub(4, n - 2)
                    w.ub(1, 1)
                    w.sb(n, dx)
                    w.sb(n, dy)
                elif dx == 0:
                    n = max(2, _bits(dy))
                    w.ub(4, n - 2)
                    w.ub(1, 0)
                    w.ub(1, 1)
                    w.sb(n, dy)
                else:
                    n = max(2, _bits(dx))
                    w.ub(4, n - 2)
                    w.ub(1, 0)
                    w.ub(1, 0)
                    w.sb(n, dx)
            else:
                cx, cy = int(round(op[1])), int(round(op[2]))
                ax, ay = int(round(op[3])), int(round(op[4]))
                a, b, c2, d = cx - x, cy - y, ax - cx, ay - cy
                x, y = ax, ay
                n = max(2, _bits(a, b, c2, d))
                w.ub(1, 1)
                w.ub(1, 0)
                w.ub(4, n - 2)
                for v in (a, b, c2, d):
                    w.sb(n, v)
    w.ub(1, 0)
    w.ub(5, 0)
    return w.bytes()


def _rect(v):
    w = _BW()
    n = _bits(*v)
    w.ub(5, n)
    for a in v:
        w.sb(n, a)
    return w.bytes()


class Font3:
    """The DefineFont3 (ma 75)."""

    def __init__(s, d):
        s.fid, s.co, s.lang, nl = struct.unpack_from("<HBBB", d, 0)
        s.ten = d[5:5 + nl]
        p = 5 + nl
        n = struct.unpack_from("<H", d, p)[0]
        p += 2
        rong = s.co & 8
        offs = struct.unpack_from(f"<{n + 1}{'I' if rong else 'H'}", d, p)
        s.hinh = [d[p + offs[i]:p + offs[i + 1]] for i in range(n)]
        p += offs[n]
        if s.co & 4:
            s.ma = list(struct.unpack_from(f"<{n}H", d, p))
            p += 2 * n
        else:
            s.ma = list(d[p:p + n])
            p += n
        s.bo_cuc = None
        if s.co & 0x80:
            asc, desc, lead = struct.unpack_from("<HHh", d, p)
            p += 6
            adv = list(struct.unpack_from(f"<{n}h", d, p))
            p += 2 * n
            r = _BR(d, p)
            for _ in range(n):
                k = r.ub(5)
                for _ in range(4):
                    r.sb(k)
                r.align()
            p = r.p >> 3
            kc = struct.unpack_from("<H", d, p)[0]
            p += 2
            ker = []
            for _ in range(kc):
                if s.co & 4:
                    a, b, v = struct.unpack_from("<HHh", d, p)
                    p += 6
                else:
                    a, b, v = struct.unpack_from("<BBh", d, p)
                    p += 4
                ker.append((a, b, v))
            s.bo_cuc = {"asc": asc, "desc": desc, "lead": lead, "adv": adv, "ker": ker}
        s.con_lai = d[p:]

    def ghi(s):
        n = len(s.hinh)
        thu_tu = sorted(range(n), key=lambda i: s.ma[i])
        hinh = [s.hinh[i] for i in thu_tu]
        tong = sum(len(x) for x in hinh)
        rong = bool(s.co & 8) or (2 * (n + 1) + tong) > 0xFFFF
        co = (s.co & ~0x08) | (0x08 if rong else 0) | 0x04
        ra = bytearray(struct.pack("<HBBB", s.fid, co, s.lang, len(s.ten)) + s.ten + struct.pack("<H", n))
        k = 4 if rong else 2
        o = k * (n + 1)
        offs = []
        for x in hinh:
            offs.append(o)
            o += len(x)
        offs.append(o)
        ra += struct.pack(f"<{n + 1}{'I' if rong else 'H'}", *offs)
        for x in hinh:
            ra += x
        ra += struct.pack(f"<{n}H", *[s.ma[i] for i in thu_tu])
        if s.bo_cuc:
            L = s.bo_cuc
            ra += struct.pack("<HHh", L["asc"], L["desc"], L["lead"])
            ra += struct.pack(f"<{n}h", *[L["adv"][i] for i in thu_tu])
            ra += _rect((0, 0, 0, 0)) * n
            ra += struct.pack("<H", len(L["ker"]))
            for a, b, v in L["ker"]:
                ra += struct.pack("<HHh", a, b, v)
        ra += s.con_lai
        return bytes(ra)


def tach_the(g):
    """GFX/SWF (khong nen) -> (dau, [(ma_the, du_lieu)])"""
    r = _BR(g, 8)
    nb = r.ub(5)
    r.p += 4 * nb
    r.align()
    p = (r.p >> 3) + 4
    dau, the = g[:p], []
    while p + 2 <= len(g):
        cl = struct.unpack_from("<H", g, p)[0]
        c, n = cl >> 6, cl & 63
        p += 2
        if n == 63:
            n = struct.unpack_from("<I", g, p)[0]
            p += 4
        the.append((c, g[p:p + n]))
        p += n
        if c == 0:
            break
    return dau, the


def gop_the(dau, the):
    ra = bytearray(dau)
    for c, d in the:
        if len(d) >= 63 or c in (75, 48, 1005):
            ra += struct.pack("<HI", (c << 6) | 63, len(d))
        else:
            ra += struct.pack("<H", (c << 6) | len(d))
        ra += d
    struct.pack_into("<I", ra, 4, len(ra))
    return bytes(ra)


def giai_gfx(b):
    """GFX/CFX/FWS/CWS -> ban khong nen (giu chu ky GFX/FWS)."""
    if b[:3] in (b"CFX", b"CWS"):
        d = zlib.decompress(b[8:])
        return (b"GFX" if b[:1] == b"C" and b[1:3] == b"FX" else b"FWS") + b[3:8] + d
    return b


# ================================================================ hinh hoc

def _phang(vien, buoc=10):
    """Duong vien -> da giac (diem), duong cong chia nho."""
    pts = []
    x = y = 0
    for op in vien:
        if op[0] == 'M':
            x, y = op[1], op[2]
            pts.append((x, y))
        elif op[0] == 'L':
            x, y = op[1], op[2]
            pts.append((x, y))
        else:
            for k in range(1, buoc + 1):
                t = k / buoc
                a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
                pts.append((a * x + b * op[1] + c * op[3], a * y + b * op[2] + c * op[4]))
            x, y = op[3], op[4]
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6:
        pts.pop()
    return pts


def _dien_tich(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def _trong(p, poly):
    x, y = p
    ok = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            ok = not ok
    return ok


class _N:
    __slots__ = ("x", "y", "next", "prev", "giao", "vao", "ban", "a", "tham")

    def __init__(s, x, y, giao=False, a=0.0):
        s.x, s.y, s.giao, s.a = x, y, giao, a
        s.next = s.prev = s.ban = None
        s.vao = False
        s.tham = False


def _vong(pts):
    ns = [_N(x, y) for x, y in pts]
    for i, n in enumerate(ns):
        n.next = ns[(i + 1) % len(ns)]
        n.prev = ns[i - 1]
    return ns


def hop(A, B):
    """Hop (union) 2 da giac don -> danh sach da giac (Greiner-Hormann)."""
    B = [(x + 0.0137, y + 0.0291) for x, y in B]          # tranh truong hop giao dung dinh
    sa, sb = _vong(A), _vong(B)
    giao = []
    for i, p in enumerate(sa):
        p1, p2 = (p.x, p.y), (sa[(i + 1) % len(sa)].x, sa[(i + 1) % len(sa)].y)
        for j, q in enumerate(sb):
            q1, q2 = (q.x, q.y), (sb[(j + 1) % len(sb)].x, sb[(j + 1) % len(sb)].y)
            d = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0])
            if abs(d) < 1e-12:
                continue
            ta = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / d
            tb = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / d
            if 0 < ta < 1 and 0 < tb < 1:
                x, y = p1[0] + ta * (p2[0] - p1[0]), p1[1] + ta * (p2[1] - p1[1])
                giao.append((i, ta, j, tb, x, y))
    if not giao:
        if _trong(A[0], B):
            return [B]
        if _trong(B[0], A):
            return [A]
        return [A, B]
    # chen diem giao vao 2 vong
    theo_a, theo_b = {}, {}
    cap = []
    for i, ta, j, tb, x, y in giao:
        na, nb = _N(x, y, True, ta), _N(x, y, True, tb)
        na.ban, nb.ban = nb, na
        theo_a.setdefault(i, []).append(na)
        theo_b.setdefault(j, []).append(nb)
        cap.append(na)

    def chen(ds, theo):
        for i, lst in theo.items():
            lst.sort(key=lambda n: n.a)
            cur = ds[i]
            nxt = cur.next
            for n in lst:
                cur.next, n.prev = n, cur
                cur = n
            cur.next, nxt.prev = nxt, cur
    chen(sa, theo_a)
    chen(sb, theo_b)

    def danh_dau(dau, khac):
        trong = _trong((dau.x, dau.y), khac)
        n = dau
        while True:
            if n.giao:
                n.vao = not trong
                trong = not trong
            n = n.next
            if n is dau:
                break
    danh_dau(sa[0], B)
    danh_dau(sb[0], A)
    # hop = dao co vao/ra roi di nhu phep giao
    for v in (sa[0], sb[0]):
        n = v
        while True:
            if n.giao:
                n.vao = not n.vao
            n = n.next
            if n is v:
                break
    kq = []
    for c in cap:
        if c.tham:
            continue
        poly = []
        n = c
        while True:
            n.tham = True
            if n.ban:
                n.ban.tham = True
            if n.vao:
                while True:
                    poly.append((n.x, n.y))
                    n = n.next
                    if n.giao:
                        break
            else:
                while True:
                    poly.append((n.x, n.y))
                    n = n.prev
                    if n.giao:
                        break
            n = n.ban
            if n.tham and (n is c or n.ban is c):
                break
            if len(poly) > 100000:
                raise ValueError("lỗi hợp hình")
        kq.append(poly)
    # bo da giac la (lo) – chi giu da giac lon nhat
    kq.sort(key=lambda p: -abs(_dien_tich(p)))
    return kq[:1]


def _thanh_vien(poly, chieu):
    """Da giac -> duong vien SWF (dung chieu cua vien ngoai cua font)."""
    if (_dien_tich(poly) < 0) != (chieu < 0):
        poly = poly[::-1]
    return [('M', poly[0][0], poly[0][1])] + [('L', x, y) for x, y in poly[1:]] + [('L', poly[0][0], poly[0][1])]


def _hop_vien(vien_goc, them, chieu):
    """Hop da giac 'them' vao vien ngoai cua glyph (vien ngoai dau tien cham vao no)."""
    ra = list(vien_goc)
    for i, c in enumerate(ra):
        pts = _phang(c)
        if (_dien_tich(pts) < 0) != (chieu < 0):
            continue                                  # lo (vd: long chu o) – bo qua
        if not any(_trong(p, pts) for p in them) and not any(_trong(p, them) for p in pts):
            # co the van cat nhau ma khong chua dinh -> thu hop
            pass
        u = hop(pts, them)
        if len(u) == 1 and abs(_dien_tich(u[0])) > abs(_dien_tich(pts)) + 1:
            ra[i] = _thanh_vien(u[0], chieu)
            return ra
    return ra + [_thanh_vien(them, chieu)]


def _bien(vien_ds):
    xs, ys = [], []
    for c in vien_ds:
        for op in c:
            xs += [op[1]] + ([op[3]] if op[0] == 'Q' else [])
            ys += [op[2]] + ([op[4]] if op[0] == 'Q' else [])
    return min(xs), max(xs), min(ys), max(ys)


def _bien_doi(vien_ds, sx=1.0, sy=1.0, dx=0.0, dy=0.0, tam=(0, 0)):
    """Co dan quanh 'tam' roi dich chuyen."""
    cx, cy = tam
    ra = []
    for c in vien_ds:
        cc = []
        for op in c:
            if op[0] == 'Q':
                cc.append(('Q', (op[1] - cx) * sx + cx + dx, (op[2] - cy) * sy + cy + dy,
                           (op[3] - cx) * sx + cx + dx, (op[4] - cy) * sy + cy + dy))
            else:
                cc.append((op[0], (op[1] - cx) * sx + cx + dx, (op[2] - cy) * sy + cy + dy))
        ra.append(cc)
    return ra


# ================================================================ TrueType (lay dau hoi, rau)

def _ttf_vien(ttf, ma):
    b = ttf
    n = struct.unpack_from(">H", b, 4)[0]
    t = {}
    for i in range(n):
        tag, _, o, l = struct.unpack_from(">4sIII", b, 12 + 16 * i)
        t[tag.decode("latin-1")] = o
    upem = struct.unpack_from(">H", b, t["head"] + 18)[0]
    fmt = struct.unpack_from(">h", b, t["head"] + 50)[0]
    ng = struct.unpack_from(">H", b, t["maxp"] + 4)[0]

    def loca(i):
        return struct.unpack_from(">H", b, t["loca"] + 2 * i)[0] * 2 if fmt == 0 else \
            struct.unpack_from(">I", b, t["loca"] + 4 * i)[0]
    # cmap format 4
    o = t["cmap"]
    gid = None
    for i in range(struct.unpack_from(">H", b, o + 2)[0]):
        _, _, off = struct.unpack_from(">HHI", b, o + 4 + 8 * i)
        q = o + off
        if struct.unpack_from(">H", b, q)[0] != 4:
            continue
        seg = struct.unpack_from(">H", b, q + 6)[0] // 2
        ends = struct.unpack_from(f">{seg}H", b, q + 14)
        sts = struct.unpack_from(f">{seg}H", b, q + 16 + 2 * seg)
        dts = struct.unpack_from(f">{seg}h", b, q + 16 + 4 * seg)
        ro = q + 16 + 6 * seg
        rof = struct.unpack_from(f">{seg}H", b, ro)
        for k in range(seg):
            if sts[k] <= ma <= ends[k]:
                if rof[k] == 0:
                    gid = (ma + dts[k]) & 0xFFFF
                else:
                    g = struct.unpack_from(">H", b, ro + 2 * k + rof[k] + 2 * (ma - sts[k]))[0]
                    gid = (g + dts[k]) & 0xFFFF if g else 0
                break
        if gid:
            break
    if not gid or gid >= ng:
        raise ValueError(f"font thiếu ký tự U+{ma:04X}")
    p = t["glyf"] + loca(gid)
    nc = struct.unpack_from(">h", b, p)[0]
    if nc < 0:
        raise ValueError("glyph ghép – không hỗ trợ")
    p += 10
    ends = struct.unpack_from(f">{nc}H", b, p)
    p += 2 * nc
    p += 2 + struct.unpack_from(">H", b, p)[0]
    npt = ends[-1] + 1
    fl = []
    while len(fl) < npt:
        f = b[p]
        p += 1
        fl.append(f)
        if f & 8:
            fl += [f] * b[p]
            p += 1
    xs, v = [], 0
    for f in fl:
        if f & 2:
            v += b[p] if f & 16 else -b[p]
            p += 1
        elif not f & 16:
            v += struct.unpack_from(">h", b, p)[0]
            p += 2
        xs.append(v)
    ys, v = [], 0
    for f in fl:
        if f & 4:
            v += b[p] if f & 32 else -b[p]
            p += 1
        elif not f & 32:
            v += struct.unpack_from(">h", b, p)[0]
            p += 2
        ys.append(v)
    vien, st = [], 0
    for en in ends:
        c = [(xs[i], -ys[i], fl[i] & 1) for i in range(st, en + 1)]     # lat truc y (SWF y huong xuong)
        st = en + 1
        k = next((i for i, q in enumerate(c) if q[2]), None)
        if k is None:
            dau = ((c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2)
            ds = c[1:] + c[:1]
        else:
            dau = c[k][:2]
            ds = c[k + 1:] + c[:k + 1]
        ops = [('M', dau[0], dau[1])]
        ctrl = None
        for x, y, on in ds:
            if on:
                ops.append(('Q', ctrl[0], ctrl[1], x, y) if ctrl else ('L', x, y))
                ctrl = None
            else:
                if ctrl:
                    m = ((ctrl[0] + x) / 2, (ctrl[1] + y) / 2)
                    ops.append(('Q', ctrl[0], ctrl[1], m[0], m[1]))
                ctrl = (x, y)
        if ctrl:
            ops.append(('Q', ctrl[0], ctrl[1], dau[0], dau[1]))
        vien.append(ops)
    return vien, upem


# ================================================================ ghep chu Viet

DAU_TREN = {"̀": "huyen", "́": "sac", "̃": "nga", "̉": "hoi"}
DAU_MU = {"̂": "mu", "̆": "trang"}


def _can_them():
    ds = []
    for goc in "aăâeêioôơuưyAĂÂEÊIOÔƠUƯY":
        for dau in ("", "̀", "́", "̃", "̉", "̣"):
            ds.append(unicodedata.normalize("NFC", goc + dau))
    return [c for c in dict.fromkeys(ds + ["đ", "Đ"]) if len(c) == 1]


CHU_VIET = _can_them()


def them_tieng_viet(gfx, ttf_mau, bao=lambda s: None):
    """gfx: file GFX/SWF chua DefineFont3 (vd gfxfontlib). ttf_mau: bytes font TrueType co dau hoi + rau.
    -> (gfx_moi, so_chu_them)."""
    g = giai_gfx(gfx)
    dau, the = tach_the(g)
    tong = 0
    for k, (ma_the, d) in enumerate(the):
        if ma_the != 75:
            continue
        f = Font3(d)
        if not f.bo_cuc or ord("a") not in f.ma or ord("à") not in f.ma:
            continue
        so = _them_vao_font(f, ttf_mau)
        if so:
            the[k] = (75, f.ghi())
            tong += so
    return gop_the(dau, the), tong


def _them_vao_font(f, ttf_mau):
    vi_tri = {c: i for i, c in enumerate(f.ma)}

    def vien(ch):
        return doc_hinh(f.hinh[vi_tri[ord(ch)]])

    def adv(ch):
        return f.bo_cuc["adv"][vi_tri[ord(ch)]]

    co_san = set(f.ma)
    thieu = [c for c in CHU_VIET if ord(c) not in co_san]
    if not thieu:
        return 0
    chieu = _dien_tich(_phang(vien("o")[0]))     # chieu vien ngoai cua font

    def dau_tu(ghep, goc):
        a = vien(ghep)
        b = {tuple(c[0][1:3]) for c in vien(goc)}
        return [c for c in a if tuple(c[0][1:3]) not in b]

    # --- dau cua chinh font (chu thuong), chuan hoa: tam x = 0, day y = 0
    def chuan(vs):
        x0, x1, y0, y1 = _bien(vs)
        return _bien_doi(vs, dx=-(x0 + x1) / 2, dy=-y1), (x1 - x0, y1 - y0)
    dau_thuong = {"sac": chuan(dau_tu("á", "a")), "huyen": chuan(dau_tu("à", "a")),
                  "mu": chuan(dau_tu("â", "a")), "nga": chuan(dau_tu("ã", "a"))}
    dau_hoa = {"sac": chuan(dau_tu("Á", "A")), "huyen": chuan(dau_tu("À", "A")),
               "mu": chuan(dau_tu("Â", "A")), "nga": chuan(dau_tu("Ã", "A"))}
    lech = {}                                      # sac lech phai, huyen lech trai so voi tam chu
    for ten, gh, goc in (("sac", "á", "a"), ("huyen", "à", "a"), ("mu", "â", "a")):
        x0, x1, _, _ = _bien(dau_tu(gh, goc))
        b0, b1, _, _ = _bien(vien(goc))
        lech[ten] = (x0 + x1) / 2 - (b0 + b1) / 2
    lech["nga"] = lech["mu"]
    _, _, _, day_thuong = _bien(dau_tu("á", "a"))  # y day cua dau (chu thuong)
    _, _, _, day_hoa = _bien(dau_tu("Á", "A"))
    trang = chuan(vien("˘")) if ord("˘") in co_san else None
    cham = chuan(vien("˙")) if ord("˙") in co_san else chuan(vien("."))
    # dau hoi, rau tu font TrueType
    x_cao = -_bien(vien("x"))[2]
    hoi_v, upem = _ttf_vien(ttf_mau, 0x0309)
    rau_v, _ = _ttf_vien(ttf_mau, 0x031B)
    ty = x_cao / 540.0 * (upem / 1000.0) ** -1     # Be Vietnam Pro: chieu cao chu x = 540 / 1000
    rau_v = _bien_doi(rau_v, ty, ty)
    sx_ = (dau_thuong["sac"][1][1]) * 0.95 / (_bien(hoi_v)[3] - _bien(hoi_v)[2])
    hoi = chuan(_bien_doi(hoi_v, sx_, sx_))
    dau_thuong["hoi"] = hoi
    dau_hoa["hoi"] = hoi
    lech["hoi"] = 0

    def dat(ds_dau, tam_x, day_y, ty_le=1.0):
        vs, _ = ds_dau
        return _bien_doi(vs, ty_le, ty_le, tam_x, day_y)

    so = 0
    for ch in thieu:
        if ch in "đĐ":
            if ch == "Đ" and ord("Ð") in co_san:
                vs, a = vien("Ð"), adv("Ð")
            elif ch == "đ":
                vs, a = _d_gach(vien("d"), chieu), adv("d")
            else:
                continue
            _them(f, ord(ch), vs, a)
            so += 1
            continue
        d = unicodedata.normalize("NFD", ch)
        goc, dau = d[0], d[1:]
        hoa = goc.isupper()
        mu = next((DAU_MU[c] for c in dau if c in DAU_MU), None)
        rau = "̛" in dau
        thanh = next((DAU_TREN[c] for c in dau if c in DAU_TREN), None)
        nang = "̣" in dau
        # chu nen: dung chu co san cua font neu da co phan mu / thanh
        nen_ch = goc
        if goc == "i" and (thanh or mu):
            nen_ch = "ı"
        con_thanh = thanh
        if mu == "mu" and not thanh:
            nen_ch = unicodedata.normalize("NFC", goc + "̂")
        elif not mu and thanh in ("sac", "huyen", "nga") and not rau:
            c2 = unicodedata.normalize("NFC", goc + {"sac": "́", "huyen": "̀", "nga": "̃"}[thanh])
            if ord(c2) in co_san:
                nen_ch, con_thanh = c2, None
        if ord(nen_ch) not in co_san:
            nen_ch = goc
            con_thanh = thanh
        vs = [list(c) for c in vien(nen_ch)]
        a = adv(nen_ch)
        b0, b1, b2, b3 = _bien(vien(goc if goc != "i" else "ı"))
        tam = (b0 + b1) / 2
        bo = dau_hoa if hoa else dau_thuong
        day = day_hoa if hoa else day_thuong
        tren = []                                  # cac dau phia tren
        dinh = day                                 # y dinh hien tai cua chong dau
        if mu == "mu" and nen_ch in (goc, "ı"):
            m = dat(bo["mu"], tam + lech["mu"], day)
            tren += m
            dinh = _bien(m)[2]
        elif mu == "mu":
            m = [c for c in vs if _bien([c])[3] <= day + 1]
            dinh = _bien(m)[2] if m else day
        if mu == "trang" and trang:
            m = dat(trang, tam, day)
            tren += m
            dinh = _bien(m)[2]
        if rau:
            vs = _gan_rau(vs, rau_v, goc, chieu, x_cao, hoa, b1, b2)
            a = max(a, int(_bien(vs)[1] + 300))
        if con_thanh:
            dm = bo[con_thanh]
            if mu == "mu":
                if con_thanh == "nga":
                    m = dat(dm, tam + lech["mu"], dinh - 450, 0.8)
                else:
                    mx1 = _bien(tren or [c for c in vs if _bien([c])[3] <= day + 1])[1]
                    w = dm[1][0] * 0.78
                    m = dat(dm, mx1 - 700 + w / 2, day - 1500, 0.78)
            elif mu == "trang":
                m = dat(dm, tam, dinh - 400, 0.8)
            else:
                m = dat(dm, tam + lech.get(con_thanh, 0), day)
            tren += m
        if nang:
            m = dat(cham, tam, cham[1][1] + 1200)
            if goc in "yY" and _cham_vao(vs, m):
                for dx in range(500, 6000, 500):
                    m2 = _bien_doi(m, dx=dx)
                    if not _cham_vao(vs, m2):
                        m = m2
                        break
            tren += m
        _them(f, ord(ch), vs + tren, a)
        so += 1
    return so


def _cham_vao(vs, m):
    x0, x1, y0, y1 = _bien(m)
    for c in vs:
        p = _phang(c)
        for x, y in p:
            if x0 - 150 <= x <= x1 + 150 and y0 - 150 <= y <= y1 + 150:
                return True
    return False


def _them(f, ma, vs, a):
    if ma in f.ma:
        return
    f.ma.append(ma)
    f.hinh.append(ghi_hinh(vs))
    f.bo_cuc["adv"].append(int(a))


def _d_gach(vs, chieu):
    """Chu đ = chu d + gach ngang qua than doc ben phai."""
    pts_than = [op for c in vs for op in c if op[0] == 'L']
    x0, x1, y0, y1 = _bien(vs)
    # than doc: 2 diem tren cung (y nho nhat)
    dinh = sorted({op[1] for op in pts_than if abs(op[2] - y0) < 1})
    if len(dinh) >= 2:
        trai, phai = dinh[0], dinh[-1]
    else:
        trai, phai = x1 - (x1 - x0) * 0.3, x1
    day_net = (y0 * 0.17)                          # do day gach ~ 1/6 chieu cao
    yg = y0 + (-y0) * 0.11
    gach = [(trai - (phai - trai) * 0.75, yg), (phai + (phai - trai) * 0.3, yg),
            (phai + (phai - trai) * 0.3, yg - day_net * -1 if False else yg + abs(day_net) * 0.6),
            (trai - (phai - trai) * 0.75, yg + abs(day_net) * 0.6)]
    return _hop_vien(vs, gach, chieu)


def _gan_rau(vs, rau_v, goc, chieu, x_cao, hoa, b1, b2):
    """Gan rau (o, u) vao canh phai tren cua chu – hop voi net chu."""
    r0, r1, r2, r3 = _bien(rau_v)
    cao = -b2                                     # chieu cao chu nen
    # Be Vietnam Pro: rau vuot dinh chu ~ 0.2 chieu cao chu x, mep phai vuot chu ~ 10 (o) / 115 (u) don vi / 540
    vuot_dinh = x_cao * (111 / 540.0)
    vuot_phai = x_cao * ((10 if goc in "oO" else 115) / 540.0)
    dx = (b1 + vuot_phai) - r1
    dy = (b2 - vuot_dinh) - r2
    rv = _bien_doi(rau_v, dx=dx, dy=dy)
    pts = _phang(rv[0], 12)
    return _hop_vien(vs, pts, chieu)
