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
