## Dịch Game v6.21.1

- Tomb Raider (2013): giọng Lara lấy mẫu từ giọng tiếng Anh gốc của Lara trong game (không dùng giọng Rise nữa).
- Giọng Việt to, rõ hơn: đoạn nhân vật gốc nói thì thào vẫn có giọng Việt đủ nghe.
- Các đoạn đã lồng bằng giọng cũ được làm lại tự động khi bấm Lồng tiếng.

## Dịch Game v6.21.0

- Tomb Raider (2013): thêm LỒNG TIẾNG VIỆT cho lời thoại lúc chơi (Bước 4 trong trang game).
  - Đọc thẳng phụ đề tiếng Việt có sẵn trong game (bản Việt hóa của nhóm khác) – không tốn tiền dịch.
  - Lara dùng giọng mẫu đã duyệt ở Rise of the Tomb Raider; nhân vật khác lấy giọng mẫu từ giọng gốc.
  - Nút "Cài giọng Việt vào game" / "Gỡ giọng Việt" (ghi vào patch2_ENGLISH, giữ bản gốc).
  - Cắt cảnh (giọng trộn với nhạc) chưa lồng – làm ở bản sau.
- Game đã có Việt hóa sẵn: app nhận ra và không dịch lại chữ tiếng Việt.

## Dịch Game v6.20.8

- Rise of the Tomb Raider: sửa phụ đề lời thoại LÚC ĐANG CHƠI còn tiếng Anh. Game lấy phụ đề này từ file chữ riêng trong các gói bản vá (update), không phải file phim – app giờ dò và Việt hóa cả các file này.
- Phụ đề trở lại CÓ DẤU khi cài có dấu (bản 6.20.7 ép không dấu là không cần).
- Lần đầu mở trang Rise sẽ quét thêm lời thoại (vài phút). Có câu mới → bấm Dịch, rồi Cài Việt hóa lại.

## Dịch Game v6.20.7

- Rise of the Tomb Raider: font tiếng Việt đã chạy – menu, nhiệm vụ, chữ trong game hiện CÓ DẤU đầy đủ.
- Phụ đề lời thoại (file phim .mul) game không nhận chữ có dấu (hiện lại tiếng Anh) → phụ đề luôn ghi không dấu để vẫn là tiếng Việt.

## Dịch Game v6.20.6

- Tomb Raider: sửa lỗi không nhận ra font chữ của game (đọc sai vị trí tài nguyên). Cài có dấu sẽ thêm được chữ tiếng Việt vào font.

## Dịch Game v6.20.5

- Cột menu bên trái tự rộng ra vừa đủ để hiện ĐẦY ĐỦ tên các mục (Shadow of the Tomb Raider, Tomb Raider (2013) (Steam)...), ở mọi cỡ chữ / tỉ lệ hiển thị.

## Dịch Game v6.20.4

- Tomb Raider: khi không tìm thấy font chữ của game, app ghi file chẩn đoán (font_chan_doan.txt) để tìm nguyên nhân.

## Dịch Game v6.20.3

- Tomb Raider: nếu ghép giọng Việt vào một đoạn thoại bị lỗi, app vẫn giữ PHỤ ĐỀ tiếng Việt cho đoạn đó (trước đây cả đoạn trở về tiếng Anh mà không báo). Lỗi được ghi vào loi_cai.txt và báo số lượng sau khi cài.

## Dịch Game v6.20.2

- Tomb Raider: sửa lỗi còn vài trăm câu phụ đề "đã dịch" nhưng vẫn là tiếng Anh (máy dịch trả lại nguyên câu) – nay app dịch lại các câu này.
- Chú thích âm thanh trong <...> (vd <coughing>) được phép dịch – trước đây làm cả câu bị bỏ qua.

## Dịch Game v6.20.1

- Sửa lỗi dò font Rise of the Tomb Raider chạy rất lâu (hàng giờ): trước đây mỗi tài nguyên trong một khối nén lớn đều bị giải nén lại từ đầu; nay mỗi khối chỉ giải nén một lần. Thanh tiến độ hiện số tài nguyên đã kiểm.

## Dịch Game v6.20.0 – Rise of the Tomb Raider: font tiếng Việt CÓ DẤU đầy đủ

- Bấm "Cài Việt hóa (có dấu)" (hoặc "Cài gói thử (có dấu)"): app tự thêm chữ tiếng Việt (ă â đ ê ô ơ ư + 5 dấu, chữ hoa và thường) vào font chữ của game. Chữ được ghép từ chính kiểu chữ DIN của game nên nhìn đồng bộ.
- Lần đầu app dò font của game mất vài phút (máy được giữ thức); các lần sau dùng lại kết quả.
- Không làm được font thì app báo lý do và vẫn cài như cũ (ghép dấu tạm). "Không dấu" không đổi.

## Dịch Game v6.19.2

- Bảng điều khiển của app chỉ ẩn khỏi ảnh chụp / quay màn hình KHI ĐANG DỊCH MÀN HÌNH (Tự động bật, F12). Không dịch thì chụp màn hình, quay video, chia sẻ màn hình thấy app bình thường.
- Khung bản dịch (chữ hiện đè lên game) vẫn luôn ẩn khỏi ảnh chụp để app không tự đọc lại bản dịch.

## Dịch Game v6.19.1

- Sửa lỗi "Dò font của game" báo "'utf-8' codec can't encode… surrogates not allowed" lúc ghi báo cáo (gần xong).

## Dịch Game v6.19.0 – Việt hóa Tomb Raider (2013) và Shadow of the Tomb Raider

- Thẻ Tomb Raider (2013) (cả bản Steam và Epic GOTY) và Shadow of the Tomb Raider giờ có nút "Việt hóa" như Rise: dịch toàn bộ chữ trong game (Claude / Offline), cài gói thử kiểm tra font, cài có dấu / không dấu, gỡ, dò font.
- Tomb Raider 2013: app tạo lại gói patch2 (bản gốc được giữ thành bigfile._orig.patch2.000.tiger); Gỡ = trả lại bản gốc.
- Shadow: tạo gói mod riêng, không sửa file gốc; Gỡ = xóa gói.
- Mỗi game có trang công cụ riêng ở cột trái, mở cùng lúc không lẫn nhau. Bản dịch lưu riêng từng game.
- Phụ đề phim và lồng tiếng: hiện vẫn chỉ có cho Rise.
- "Dò font của game" đọc được gói của cả 3 game; kết quả ra Desktop\DoFont_TR2013 / DoFont_SotTR / DoFont_RotTR.

## Dịch Game v6.18.0 – Dò file chữ cho mọi game

- Mỗi game trong Thư viện có nút mới "Dò file chữ": app dò đúng thư mục game đó, liệt kê file nào chứa chữ tiếng Anh (đường dẫn, loại file, số câu, câu mẫu) và có nút "Mở thư mục" để xem file.
- Đánh dấu ✓ file muốn Việt hóa → dịch bằng Claude / Offline, hoặc "Xuất Excel để tự dịch" rồi "Nạp file đã dịch".
- "Ghi vào game" luôn giữ bản gốc; "Trả lại bản gốc" để về tiếng Anh. Có tùy chọn "Không dấu" khi game hiện ô vuông.
- Đọc / ghi được: JSON (cả RPG Maker), CSV, XML, INI/LANG, PO, YAML, TXT, Ren'Py .rpy, Unreal .locres. Gói nén riêng của game (.pak, .assets...) được báo "chưa hỗ trợ".

## Dịch Game v6.17.0 – Tomb Raider: công cụ dò font

- Thêm nút "Dò font của game" (cửa sổ Tomb Raider, bước 3): app quét toàn bộ dữ liệu game để tìm font chữ (Scaleform, TrueType) và kiểm tra font có đủ chữ tiếng Việt có dấu không.
- Kết quả nằm ở Desktop\DoFont_RotTR. Gửi file GuiClaude_DoFont.zip (hoặc bao_cao_font.txt) cho Claude để làm bản Việt hóa CÓ DẤU.
- Máy được giữ thức trong lúc dò; bấm "Tạm dừng" để ngừng.

## Dịch Game v6.16.0 – Lồng tiếng đọc được tên riêng

- Tên riêng tiếng nước ngoài (Kliff, Oongka, Hernand, Pywel, Lara, Konstantin...) được phiên âm sang cách đọc tiếng Việt trước khi VieNeu đọc (Kliff → "Cờ líp", Hernand → "Hơ nan"). Phụ đề vẫn giữ tên gốc.
- Có mã Claude: app nhờ Claude phiên âm toàn bộ tên riêng một lần (rất rẻ), lưu lại dùng mãi. Không có mạng: dùng quy tắc phiên âm tự động.
- Áp dụng cho lồng tiếng Crimson Desert (Kliff, phần A, phần B) và Rise of the Tomb Raider.

## Dịch Game v6.15.0 – Crimson Desert: lồng tiếng bằng giọng bạn tự ghi âm

- Lồng tiếng Crimson Desert (phần A nhân vật + phần B dân thường) dùng giọng bạn tự ghi âm trong thư mục DichGame_LongTieng\giong_rieng theo bảng phân bổ phan_bo.json (Kliff = giọng nam chính, Oongka = lính canh, Yann = nam phụ, Damian = nam già, Nairah = nữ chính, phù thủy = giọng phù thủy...).
- Nhân vật nào đổi giọng thì app tự xóa câu đã đọc bằng giọng cũ và đọc lại; nhân vật không đổi giữ nguyên.

## Dịch Game v6.14.1

- Tomb Raider: giữ máy không ngủ trong lúc dịch và lồng tiếng (chạy qua đêm được).

## Dịch Game v6.14.0 – Tomb Raider: giọng Lara mạnh mẽ hơn

- Giọng mẫu mới: app tự nghe khoảng 24 câu của mỗi nhân vật và chọn 3 câu nói TO, DỨT KHOÁT nhất (ưu tiên câu có dấu "!"), bỏ câu thì thầm / lẩm bẩm.
- Giọng Việt đậm và rõ hơn: bỏ âm trầm đục, tăng nhẹ dải rõ chữ, nén đỉnh để to mà không vỡ tiếng.
- Thêm chọn "Độ to giọng Việt": Như gốc / To, chắc (+4 dB, mặc định) / Rất to (+8 dB).
- Giọng mẫu và câu đọc được làm lại từ đầu với cách chọn mới (giọng cũ không dùng nữa).

## Dịch Game v6.13.1 – Tomb Raider

- Gói "Lồng tiếng thử" giờ lấy đúng đoạn LEO NÚI TUYẾT đầu game (Jonah: "Wait till you see this view…", "Take my hand!", rơi khỏi vách băng...).
- Nhận thêm giọng nằm ở kênh trái/phải và tên kênh bị cắt ngắn (75/79 đoạn hội thoại nhiều kênh lồng tiếng được).

## Dịch Game v6.13.0 – Tomb Raider: lồng tiếng cả hội thoại nhiều người

- Lồng tiếng được cả các đoạn hội thoại nhiều nhân vật (ví dụ đoạn leo núi tuyết đầu game với Jonah): app tự tìm kênh giọng của từng nhân vật, chỉ thay giọng, giữ nguyên nhạc và tiếng động.
- Gói thử "10 câu đầu game" giờ bắt đầu từ đoạn leo núi tuyết.
- Lần đầu mở trang Tomb Raider sau khi cập nhật, app quét lại lời thoại (1–3 phút).

## Dịch Game v6.12.0 – Tomb Raider

- Sửa chữ có dấu ra ô vuông: font game chỉ có À Á Ì Í Ù…, thiếu Ế Ụ Ọ Ớ Ử Đ. Giờ "Cài Việt hóa (có dấu)" tự ghép chữ cái + dấu rời cho các chữ font thiếu, Đ thành D.
- "Lồng tiếng thử" lấy 10 đoạn thoại ĐẦU GAME (tự dịch các câu đó trước, không cần chờ dịch hết) để dễ nghe thử.

## Dịch Game v6.11.1

- Sửa lỗi nặng: cài Việt hóa Tomb Raider có lồng tiếng xong thì game mất luôn cả chữ tiếng Việt và vẫn nói tiếng Anh – bảng file trong gói chưa xếp theo thứ tự nên game không tìm thấy. Bấm "Cài Việt hóa" lại một lần.

## Dịch Game v6.11.0 – Tomb Raider: phụ đề phim + lồng tiếng Việt

- Rise of the Tomb Raider: Việt hóa luôn **phụ đề đoạn phim và lời thoại** (nằm trong file .mul, trước đây vẫn tiếng Anh). Câu phụ đề được gộp vào bước "Bắt đầu dịch".
- Mới: **Bước 4 – Lồng tiếng Việt** bằng VieNeu: giọng giống nhân vật gốc (Lara, Nadia, Jonah...), đặt đúng thời điểm phụ đề. Tự ghi file âm thanh của game, không cần cài thêm phần mềm.
  - "Lồng tiếng thử (10 câu Lara)" → Cài Việt hóa → vào game nghe thử trước khi làm hết.
  - Đoạn phim nhiều kênh âm thanh: chỉ Việt hóa phụ đề, giữ giọng gốc.
- Cài Việt hóa chạy nền, hiện tiến độ (gói có phụ đề + giọng nặng hơn trước).

## Dịch Game v6.10.1

- Sửa: nút "Danh sách rương" trên trang Bản đồ Crimson Desert không mở được (trang Game8 chặn) – đổi sang trang khác
- Sửa: Việt hóa Rise of the Tomb Raider cài xong vào game vẫn tiếng Anh – thiếu file gói chung .000.000.tiger, giờ app tự tạo (Gỡ cũng xóa luôn)

## Dịch Game v6.10.0 – Bản đồ Crimson Desert

- Thêm trang "Bản đồ Crimson Desert" ở menu Công cụ game
- Vị trí và cách lấy thú cưỡi huyền thoại: ngựa trắng Royler, ngựa đen Rokade, ngựa đỏ Camora, rồng Blackstar, Wyvern, gấu trắng, sói Silver Fang, hươu tuyết...
- Vị trí rương và két sắt có đồ xịn (vũ khí, khiên, giáp, trang sức), lọc theo nhóm, ô tìm kiếm
- Nút "Đã lấy" để đánh dấu, "Tìm trên mạng" để xem ảnh / video chỉ đường
- Nút mở nhanh bản đồ tương tác MapMaster, th.gl, Game8

## Dịch Game v6.9.1

- Sửa: "Mod tăng ô chứa đồ 1440" không tạo được mod với Crimson Desert 2.05 (game đổi cấu trúc bảng túi đồ) – giờ tìm từng kho theo tên (Character, CampWareHouse, Housing_Dresser…)

## Dịch Game v6.9.0 – giao diện kiểu DMM

- Menu bên trái như DMM: Thư viện game, Dịch màn hình, Công cụ game (Crimson Desert, Rise of the Tomb Raider), Cài đặt
- Thư viện game: mỗi game là một thẻ, nút Việt hóa / Nạp bản dịch / Gỡ / Thư mục nằm bên phải
- Công cụ Việt hóa Crimson Desert và Rise of the Tomb Raider mở ngay trong cửa sổ chính, kéo xuống được, không bị che
- Chữ tự xuống dòng theo cỡ cửa sổ – thu nhỏ không bị cắt chữ, phóng to chữ đều
- Trang Dịch màn hình: 2 cột khi cửa sổ rộng, tự xếp 1 cột khi hẹp
- Thanh trạng thái ở dưới cùng (đèn xanh / vàng / đỏ); màu xanh dương giống DMM

## Dịch Game v6.8.1

- Mới: Crimson Desert → nút "Mod tăng ô chứa đồ 1440" – tự đọc bảng túi đồ của bản game đang cài và tạo gói DMM:
  - TangO_1440_AnToan.json: túi đồ 732 ô, kho riêng / tủ quần áo / tủ lạnh Kuku / sưu tầm / hái lượm / biểu tượng 1440 ô
  - TangO_1440_TatCa.json: tất cả 1440 ô, kể cả túi đồ (vượt mức an toàn)

## Dịch Game v6.8.0 – giao diện dễ nhìn hơn

- Font mới Be Vietnam Pro (đóng gói sẵn, không cần cài), chữ to hơn; Cài đặt → Hiển thị chọn Vừa / To / Rất to
- Nút bo góc, to, có biểu tượng; màu theo ý nghĩa: đỏ = hành động chính, xám = phụ, viền đỏ = gỡ / xóa
- Có bản mới: thanh màu cam ngay trên cùng với nút "Cập nhật ngay" và "Xem có gì mới"
- Cài đặt làm lại: menu bên trái (Máy dịch & mã API, Chi phí, Giọng đọc, Phím tắt, Hiển thị, Hệ thống)
- Ô mã API có nút hiện / ẩn mã
- Đổi phím tắt ngay trong app: bấm vào phím rồi nhấn tổ hợp phím mới
- Chữ bản dịch hiện trên game cũng dùng font mới

## Dịch Game v6.7.0

- Mới: Việt hóa Rise of the Tomb Raider – chọn game trong Thư viện → nút "Việt hóa Rise of the Tomb Raider"
  - Bước 1: cài gói thử (chỉ đổi chữ menu) để kiểm tra font có hiện dấu tiếng Việt không
  - Bước 2: dịch toàn bộ chữ của game bằng Claude hoặc Offline (giữ tên riêng, lưu lại để lần sau chỉ dịch câu mới)
  - Bước 3: cài Việt hóa có dấu hoặc không dấu; gỡ 1 chạm
  - Không sửa file gốc của game: app tạo 1 gói mới bigfile._mod.viethoa_dichgame (theo cách của TR Reboot Mod Tools)

## Dịch Game v6.6.0 – giao diện mới

- Giao diện mới 3 cột, nền tối:
  - Trái: THƯ VIỆN GAME (quét game Steam/Epic/GOG, thêm game, tìm game, trạng thái Việt hóa từng game)
  - Giữa: game đang chọn – nút 1 chạm: Cài / nạp bản dịch, Việt hóa Crimson Desert, Gỡ bản dịch; xem gói DMM đã tạo
  - Phải: DỊCH MÀN HÌNH – công tắc lớn Bật/Tắt (F8), chọn máy dịch, vùng quét chữ, khung chữ dịch
- Đèn trạng thái trên cùng: xanh đang dịch • vàng đang kết nối • đỏ đã dừng
- Mới: máy dịch DeepL (cần mã API, có gói miễn phí) – nhập mã ở Cài đặt
- Mới: nạp bản dịch từ file .zip, .rar, .7z hoặc file text (tự sao lưu file gốc, gỡ được)
- Mới: thanh trượt độ đậm và cỡ chữ, chọn màu chữ / màu nền khung dịch, xem trước ngay
- Mới: nút "Cửa sổ game" đặt vùng quét = cả cửa sổ game; nút "Phím tắt" xem toàn bộ phím
- Mã API, giới hạn tiền, giọng đọc, hệ thống chuyển vào nút "Cài đặt"

## Dịch Game v6.5.0

- Mới: lồng tiếng Việt cho TẤT CẢ nhân vật Crimson Desert, chia 2 phần:
  - Phần A – nhân vật cốt truyện (Kliff + khoảng 220 người có tên, ~21.000 câu)
  - Phần B – dân thường (lính, người đi đường, chủ tiệm…, ~42.000 câu)
- Mỗi người được nhái giọng gốc của chính họ (tự lấy mẫu từ game), câu dài đọc nhanh hơn cho vừa thời gian
- Mới: chọn âm lượng giọng Việt (Như cũ / To / Rất to), mặc định To; đổi âm lượng chỉ cần bấm lại, không phải đọc lại
- File làm việc để ở ổ đĩa còn trống nhiều nhất (thư mục DichGame_LongTieng); kết quả nằm trên Desktop
- Giữ máy thức trong lúc chạy; tắt giữa chừng thì lần sau làm tiếp

## Dịch Game v6.4.1

- Sửa lỗi lồng tiếng tự động dừng giữa chừng ở câu rất ngắn ("t_out values must be in the range") – câu lỗi giờ được bỏ qua bước ép thời gian chứ không làm dừng cả việc
- Bấm lại nút là làm tiếp từ câu đang dở

## Dịch Game v6.4.0

- Mới: nút "Lồng tiếng Kliff TỰ ĐỘNG" trong cửa sổ Việt hóa Crimson Desert – app tự lấy giọng gốc Kliff làm mẫu, cho VieNeu (card màn hình) đọc toàn bộ câu Kliff đã Việt hóa bằng giọng nhái Kliff, câu dài thì đọc nhanh hơn cho vừa thời gian, rồi Wwise đóng gói thành Desktop\LongTieng_Kliff_DMM.zip
- Giữ máy không ngủ trong lúc chạy; tắt giữa chừng thì lần sau làm tiếp
- Đóng gói giọng: tự sửa tên file bị dư đuôi ".wav.wav"

## Dịch Game v6.3.3

- Sửa: máy có Desktop nằm trong OneDrive – các file xuất ra (gói Việt hóa, LongTieng_Kliff, gói giọng) giờ nằm đúng Desktop bạn đang thấy
- Đóng gói giọng: tự tìm WAV ở cả Desktop cũ lẫn Desktop OneDrive
