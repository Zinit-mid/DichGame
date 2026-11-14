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
