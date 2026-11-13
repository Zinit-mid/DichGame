# -*- coding: utf-8 -*-
"""Trang "Bản đồ" Crimson Desert: vị trí thú cưỡi huyền thoại, rương / đồ xịn (tiếng Việt).

Tên địa danh giữ tiếng Anh như trong game để dễ tìm trên bản đồ.
Dữ liệu tổng hợp từ các hướng dẫn công khai (11/2026), có thể lệch sau các bản cập nhật game.
"""
import json
import os
import urllib.parse
import webbrowser
import tkinter as tk

import giao_dien as gd

BAN_DO_ONLINE = [
    ("Bản đồ MapMaster", "Lọc rương, thú cưỡi, trang bị", "https://mapmaster.io/games/crimson-desert/maps/crimson-desert"),
    ("Bản đồ th.gl", "Có app overlay đè lên game", "https://crimsondesert.th.gl/"),
    ("Danh sách rương (Game8)", "Rương + két sắt có lời giải", "https://game8.co/games/Crimson-Desert/archives/587688"),
]

NHOM = [
    ("tat_ca", "Tất cả"),
    ("ngua", "Ngựa huyền thoại"),
    ("bay", "Rồng / bay"),
    ("thu", "Thú huyền thoại"),
    ("ruong", "Rương đồ xịn"),
    ("ket", "Két sắt (Strongbox)"),
]

# (nhom, ten, vung, vi tri, cach lay)
DU_LIEU = [
    # --- Ngua huyen thoai ---
    ("ngua", "Royler – ngựa trắng", "Pailune",
     "Silver Wolf Mountain, gần Snowgrass Shelter, cạnh một hồ băng hẻo lánh.",
     "Đuổi theo cho kịp rồi bấm E thuần ngựa (căn đuôi). Nên có thể lực (Stamina) cấp 8 trở lên."),
    ("ngua", "Rokade – ngựa đen", "Hernand (đông nam)",
     "Phía trái Pinnacle of Perception, trong lùm cây khô nhỏ ở tận đông nam Hernand.",
     "Đuổi theo và thuần giống Royler."),
    ("ngua", "Camora – ngựa đỏ", "Crimson Desert",
     "Đi về nam dọc Red River, trong khu rừng có Cây Đỏ (Red Tree).",
     "Đuổi theo và thuần giống Royler."),
    # --- Rong / bay ---
    ("bay", "Blackstar – rồng", "(Không nằm trên bản đồ)",
     "Mở khóa theo cốt truyện, không đi tìm được.",
     "Làm xong cốt truyện chính hết Chương 11 (nhiệm vụ \"Whispers in the Wind\"). Bay tối đa 15 phút, hồi 50 phút, "
     "không bay qua một số khu đông dân."),
    ("bay", "Wyvern (rồng con)", "Delesyia",
     "4 quả trứng gần Three Brothers Cliff.",
     "Cho ăn thịt sống khoảng 3 ngày trong game tới cấp lớn 3, rồi chọn Grow. Bay không giới hạn thời gian."),
    ("bay", "Kuku Bing (chim lượn)", "Demeniss (phía nam)",
     "Tòa tháp phía nam Demeniss, gần trại Bloodsteel.",
     "Dùng Force Palm phá bức tường bí mật, lấy quả trứng lớn, ấp ở tổ phía tây trại Bloodsteel."),
    ("bay", "Gà con Kuku (chim lượn)", "Nhiều nơi",
     "Chỗ có chim Kuku hoang và chim con.",
     "Cho ăn ngũ cốc (ngô / lúa mạch) rồi chọn Grow để đăng ký. Chỉ lượn, không bay lên được."),
    # --- Thu huyen thoai ---
    ("thu", "Gấu trắng (White Bear)", "Pailune (tây bắc)",
     "Gần Silver Wolf Mountain, phía nam White Wastes Sanctuary. Gấu ngủ trên sườn núi cùng 2 gấu con.",
     "Hạ cả đàn, lột da con lớn lấy White Bear Claws, mang tới Phù thủy (Witch) làm ấn triệu hồi."),
    ("thu", "Sói Silver Fang", "Hernand",
     "Hang đá ở Howling Hollow gần Hernand.",
     "Làm các nhiệm vụ phụ ở North Gate, hạ sói trong hang, mang chiến lợi phẩm tới Phù thủy."),
    ("thu", "Hươu Snowwhite Deer", "Pailune",
     "Phía trên chữ \"A\" của chữ Pailune trên bản đồ vùng.",
     "Hươu không đánh lại mà bỏ chạy – săn rồi mang chiến lợi phẩm tới Phù thủy."),
    ("thu", "Lợn rừng Rock Tusk", "Crimson Desert",
     "Trại Bordig, đông nam Tashkalp.",
     "Làm nhiệm vụ Savage Fang, hạ Ravok, mang Rock Tusk Boar's Tusk tới Phù thủy."),
    ("thu", "Dê núi Icicle Edge Alpine Ibex", "Pailune",
     "Wayward Woods, phía tây chữ \"I\" của Pailune.",
     "Làm nhiệm vụ The Sports Hunter, hạ Moren, mang sừng tới Phù thủy."),
    ("thu", "Lợn thần núi (Mountain God Boar)", "Pailune",
     "Rừng ở Pailune (theo nhiệm vụ).",
     "Nhận Lumberjack's Witness Report ở bảng thông báo, chặt cây tới khi boss hiện ra rồi hạ nó."),
    ("thu", "Hổ (Tiger)", "Demeniss (phía bắc)",
     "Rừng mưa phía bắc Demeniss, phía trên hồ nước tròn và tháp canh.",
     "Hạ hổ trắng trước. Dùng Force Palm khống chế hổ thường, cho ăn thịt sống tới khi tin tưởng 100%."),
    ("thu", "Sư tử (Lion)", "Phía bắc (gần Varnia)",
     "Tận phía bắc bản đồ, dưới Varnia, trên tảng đá cát phẳng. Cẩn thận mép vực.",
     "Hạ sư tử trắng trước, rồi khống chế + cho ăn thịt sống giống hổ."),
    ("thu", "Lạc đà Sandwalk", "Crimson Desert",
     "Theo nhiệm vụ của Redwind Merchant Guild.",
     "Làm nhiệm vụ Outlaws of the Desert, hạ thủ lĩnh Sandfang Marauder, nói chuyện với Canion."),
    # --- Ruong do xin ---
    ("ruong", "Shield of Conviction (khiên)", "Hernand",
     "Rương trên tháp chuông nhà thờ Church of Calphade (Calphadean Territory).", "Leo lên tháp chuông."),
    ("ruong", "Survivor's Solitude", "Hernand",
     "Rương sau thác nước trong Death's Grip Cavern (Everfrost Basin).", "Đi xuyên qua thác nước."),
    ("ruong", "Hollow Visage", "Hernand",
     "Rương sau thác nước trong Dawn Cave (Mountain of Frozen Souls).", "Đi xuyên qua thác nước."),
    ("ruong", "Soul Spear (giáo 2 tay)", "Hernand",
     "Một căn phòng trong Antumbra Ritual Grounds (The Argent Peaks).", ""),
    ("ruong", "Frozen Anguish", "Demeniss",
     "Rương dưới cầu thang ngay lối vào Spire of Frost (Eye of Ice).", ""),
    ("ruong", "Sydmon Bow (cung)", "Hernand",
     "Nằm giữa bụi hoa ở Hernand Highlands, ngay phía bắc chữ \"S\" của \"Highlands\".", "Nhặt dưới đất."),
    ("ruong", "Golden-Knotted Ancestral Bow (cung)", "Pailune",
     "Căn phòng cuối đường bẫy trong Pailune Ancestors' Ruins (Silver Wolf Mountain).", "Vượt qua dãy bẫy."),
    ("ruong", "Kylus Dagger (dao găm)", "Hernand",
     "Oakenshield Manor.", "Phần thưởng nhiệm vụ 'Woman Who Lost Her Husband'."),
    ("ruong", "Darkbringer", "Silver Mountains (bắc)",
     "White Wastes Sanctuary.", "Một trong những vũ khí mạnh nhất đầu game, phải đi xa lên phía bắc."),
    ("ruong", "Bộ Fallen Kingdom (áo choàng + kiếm Rapier)", "Pailune",
     "Icemoor Castle Ruins: áo choàng ở lối vào hang (dưới bên trái), kiếm cạnh thùng gỗ.", ""),
    ("ruong", "Frozen Heart Plate Armor (giáp)", "Delesyia",
     "Lâu đài Delesyia Castle (tận phía đông Pywel).", ""),
    ("ruong", "Rhonid Large Shield (khiên lớn)", "Hernand",
     "Lioncrest Manor, sau cánh cửa khóa.", ""),
    ("ruong", "Lifsoth Large Shield (khiên lớn)", "Witchwoods",
     "Nhà Phù thủy (Witch's House), trên ban công.", ""),
    ("ruong", "Sior Blaster", "Bowsprit Cape",
     "Hang Bowsprit Cape Cave.", ""),
    ("ruong", "Elite Vanguard Spear (giáo)", "Bowsprit Cape",
     "Hang gần Abyss Nexus cạnh Bowsprit Cape.", ""),
    ("ruong", "Odeck's Protector Plate Boots (giày)", "Sanctum",
     "Sanctum of Temperance – rương nằm sau hốc bị cỏ che.", "Nên đi sớm, đồ rất mạnh đầu game."),
    ("ruong", "Mirror of Night Shield (khiên)", "Sanctum",
     "Sanctum of Benediction.", "Nên đi sớm."),
    ("ruong", "Abyss Gear + bản vẽ Kuku Pack", "Sanctum",
     "Sanctum of Penitence – nhảy xuống hố gần con chó nâu.", "Nên đi sớm."),
    ("ruong", "Goblin King's Treasure Dagger", "Pororin Forest",
     "Mudridge Cabin – rương giấu dưới sàn gỗ.", ""),
    ("ruong", "Bản vẽ Palmar Pills (thuốc tăng chỉ số)", "Hernand",
     "Three Saints Falls Cave.", ""),
    # --- Ket sat ---
    ("ket", "Oath of Darkness", "Hernand", "Bluemont Manor – phòng ngủ Leon Roberts, tầng 2.", "Giải câu đố két sắt."),
    ("ket", "Saint's Necklace (dây chuyền)", "Hernand", "Hillside Manor – phòng đông nam.", "Giải câu đố két sắt."),
    ("ket", "Engraved Gold Earring (bông tai)", "Hernand", "Lioncrest Manor – phòng phía đông.", "Giải câu đố két sắt."),
    ("ket", "Dagger of Radiance (dao găm)", "Demeniss", "Church of West Demeniss (Byron Estate).", "Giải câu đố két sắt."),
    ("ket", "Witch's Earring (bông tai)", "Demeniss", "Southern Court – tầng 2.", "Giải câu đố két sắt."),
    ("ket", "Ancient Earring (bông tai)", "", "Azerian Manor – tầng 2, sau bức tường xoay.", "Giải câu đố két sắt."),
    ("ket", "Karanda's Necklace (dây chuyền)", "", "Western Court – tầng hầm.", "Giải câu đố két sắt."),
    ("ket", "Finely Crafted Gold Ring (nhẫn)", "", "Stellen Manor – trên tháp.", "Giải câu đố két sắt."),
    ("ket", "Flower Petal Earring (bông tai)", "Pororin Forest", "Mudridge Cabin.", "Giải câu đố két sắt."),
    ("ket", "Công thức Lavish Meal", "Hernand", "Hernand Castle – phòng khóa tầng trên cùng.", "Giải câu đố két sắt."),
]


def _tim_tren_mang(ten):
    goc = ten.split("–")[0].split("(")[0].strip()
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(f"Crimson Desert {goc} location"))


class TrangBanDo:
    def __init__(self, cha, f, p, thu_muc_du_lieu):
        self.cha = cha
        self.f = f
        self.p = p
        self.file = os.path.join(thu_muc_du_lieu, "ban_do_da_lay.json")
        try:
            with open(self.file, encoding="utf-8") as t:
                self.da_lay = set(json.load(t))
        except Exception:
            self.da_lay = set()
        self.nhom = "tat_ca"
        self.an_da_lay = tk.BooleanVar(value=False)
        self.tim = tk.StringVar()
        self.nut_nhom = {}
        self._xay()

    def _luu(self):
        try:
            os.makedirs(os.path.dirname(self.file), exist_ok=True)
            with open(self.file, "w", encoding="utf-8") as t:
                json.dump(sorted(self.da_lay), t, ensure_ascii=False)
        except Exception:
            pass

    def _xay(self):
        P, F = self.p, self.f
        c = self.cha
        # Ban do online
        the = tk.Frame(c, bg=gd.THE, padx=P(16), pady=P(12), highlightthickness=1, highlightbackground=gd.VIEN)
        the.pack(fill="x", pady=(0, P(10)))
        tk.Label(the, text="Mở bản đồ tương tác (trình duyệt)", bg=gd.THE, fg=gd.CHU, font=F(12, "bold"),
                 anchor="w").pack(fill="x")
        hang = tk.Frame(the, bg=gd.THE)
        hang.pack(fill="x", pady=(P(8), 0))
        for i, (ten, mo_ta, url) in enumerate(BAN_DO_ONLINE):
            o = tk.Frame(hang, bg=gd.THE)
            o.grid(row=0, column=i, sticky="ew", padx=(0, P(8)))
            hang.grid_columnconfigure(i, weight=1)
            gd.NutTron(o, ten, lambda u=url: webbrowser.open(u), kieu="chinh" if i == 0 else "thuong").pack(fill="x")
            tk.Label(o, text=mo_ta, bg=gd.THE, fg=gd.PHU, font=F(9)).pack(fill="x")

        # Loc
        loc = tk.Frame(c, bg=gd.NEN)
        loc.pack(fill="x", pady=(0, P(6)))
        for ma, ten in NHOM:
            b = gd.NutTron(loc, ten, lambda m=ma: self._chon_nhom(m), kieu="chinh" if ma == self.nhom else "thuong",
                           nho=True)
            b.pack(side="left", padx=(0, P(6)), pady=P(2))
            self.nut_nhom[ma] = b
        hang2 = tk.Frame(c, bg=gd.NEN)
        hang2.pack(fill="x", pady=(0, P(8)))
        tk.Label(hang2, text="Tìm:", bg=gd.NEN, fg=gd.PHU, font=F(10)).pack(side="left")
        o_tim = tk.Entry(hang2, textvariable=self.tim, bg=gd.O, fg=gd.CHU, insertbackground=gd.CHU, relief="flat",
                         font=F(11))
        o_tim.pack(side="left", fill="x", expand=True, padx=(P(6), P(12)), ipady=P(4))
        self.tim.trace_add("write", lambda *a: self._ve())
        tk.Checkbutton(hang2, text="Ẩn mục đã lấy", variable=self.an_da_lay, command=self._ve, bg=gd.NEN,
                       fg=gd.CHU, selectcolor=gd.O, activebackground=gd.NEN, activeforeground=gd.CHU,
                       font=F(10)).pack(side="left")
        self.lbl_dem = tk.Label(c, text="", bg=gd.NEN, fg=gd.PHU, font=F(10), anchor="w")
        self.lbl_dem.pack(fill="x")
        self.ds = tk.Frame(c, bg=gd.NEN)
        self.ds.pack(fill="both", expand=True)
        tk.Label(c, text="Tên địa danh giữ tiếng Anh như trong game. Dữ liệu tổng hợp từ hướng dẫn trên mạng, "
                         "có thể lệch sau các bản cập nhật. Bấm \"Tìm trên mạng\" để xem ảnh / video chỉ đường.",
                 bg=gd.NEN, fg=gd.PHU, font=F(9), justify="left", anchor="w", wraplength=P(700)).pack(fill="x",
                                                                                                     pady=P(10))
        self._ve()

    def _chon_nhom(self, ma):
        self.nhom = ma
        for m, b in self.nut_nhom.items():
            b.dat_kieu("chinh" if m == ma else "thuong")
        self._ve()

    def _loc(self):
        tu = self.tim.get().strip().lower()
        kq = []
        for d in DU_LIEU:
            nhom, ten, vung, vi_tri, cach = d
            if self.nhom != "tat_ca" and nhom != self.nhom:
                continue
            if self.an_da_lay.get() and ten in self.da_lay:
                continue
            if tu and tu not in " ".join(d).lower():
                continue
            kq.append(d)
        return kq

    def _ve(self):
        P, F = self.p, self.f
        for w in self.ds.winfo_children():
            w.destroy()
        ds = self._loc()
        tong = len([d for d in DU_LIEU if self.nhom == "tat_ca" or d[0] == self.nhom])
        xong = len([d for d in DU_LIEU if (self.nhom == "tat_ca" or d[0] == self.nhom) and d[1] in self.da_lay])
        self.lbl_dem.config(text=f"Đang hiện {len(ds)} mục · đã lấy {xong}/{tong}")
        ten_nhom = dict(NHOM)
        for nhom, ten, vung, vi_tri, cach in ds:
            da = ten in self.da_lay
            the = tk.Frame(self.ds, bg=gd.THE, padx=P(14), pady=P(10), highlightthickness=1,
                           highlightbackground=gd.XANH if da else gd.VIEN)
            the.pack(fill="x", pady=(0, P(8)))
            dau = tk.Frame(the, bg=gd.THE)
            dau.pack(fill="x")
            tk.Label(dau, text=("✔ " if da else "") + ten, bg=gd.THE, fg=gd.XANH if da else gd.CHU,
                     font=F(12, "bold"), anchor="w").pack(side="left")
            tk.Label(dau, text=ten_nhom.get(nhom, "") + (f" · {vung}" if vung else ""), bg=gd.THE, fg=gd.VANG,
                     font=F(9)).pack(side="left", padx=P(10))
            nut = tk.Frame(dau, bg=gd.THE)
            nut.pack(side="right")
            gd.NutTron(nut, "Bỏ đánh dấu" if da else "Đã lấy", lambda t=ten: self._doi(t),
                       kieu="thuong" if da else "xanh_la", nho=True).pack(side="right")
            gd.NutTron(nut, "Tìm trên mạng", lambda t=ten: _tim_tren_mang(t), kieu="vien",
                       nho=True).pack(side="right", padx=P(6))
            for nhan, chu in (("📍 Vị trí: ", vi_tri), ("🛠 Cách lấy: ", cach)):
                if not chu:
                    continue
                l = tk.Label(the, text=nhan + chu, bg=gd.THE, fg=gd.CHU if nhan.startswith("📍") else gd.PHU,
                             font=F(10), justify="left", anchor="w")
                l.pack(fill="x", pady=(P(4), 0))
                the.bind("<Configure>", lambda e, l=l: l.config(wraplength=max(200, e.width - 30)), add="+")
        if not ds:
            tk.Label(self.ds, text="Không có mục nào khớp.", bg=gd.NEN, fg=gd.PHU, font=F(11)).pack(pady=P(20))

    def _doi(self, ten):
        if ten in self.da_lay:
            self.da_lay.discard(ten)
        else:
            self.da_lay.add(ten)
        self._luu()
        self._ve()
