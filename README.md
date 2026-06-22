# Freight Rate Monitor — Website tự cập nhật (B-lite)

Website tĩnh theo dõi cước vận tải biển (dầu thô / sản phẩm / hàng rời / LPG), host miễn phí trên **GitHub Pages**, có một **bot GitHub Action** tự cập nhật các driver thị trường mỗi sáng (ngày làm việc).

## Phần nào tự cập nhật, phần nào không?

| Khối | Tự cập nhật? | Nguồn |
|---|---|---|
| 📡 Driver thị trường (giá dầu/xăng/diesel, tồn kho, xuất khẩu) | ✅ Bot mỗi sáng | EIA API (miễn phí) |
| Chart BDI (Baltic Dry) nhúng | ✅ Tự mới khi mở trang | TradingView |
| Số cước Baltic BDTI/BCTI/BLPG + TC + scorecard | ❌ Bản chụp định kỳ | Không có API free (cần feed trả phí Kpler/Baltic) |

> Vì sao số cước Baltic không tự cập nhật: các chỉ số Baltic là dữ liệu **trả phí, không có API miễn phí**. Muốn tự động hoàn toàn cần đăng ký feed trả phí (Kpler/LSEG/Baltic) rồi nối thêm vào `fetch_data.py`.

## Cài đặt 1 lần (~10 phút, gần như không cần code)

### 1) Lấy EIA API key (miễn phí)
- Vào https://www.eia.gov/opendata/register.php → nhập email → nhận key ngay trong email.

### 2) Tạo repository GitHub
- Tạo repo mới (vd `freight-monitor`), **Public** (để dùng GitHub Pages miễn phí).
- Upload toàn bộ các file trong thư mục này vào repo (kéo-thả trên giao diện web GitHub cũng được):
  - `index.html`, `data.json`, `fetch_data.py`, `README.md`
  - thư mục `.github/workflows/update.yml`

### 3) Thêm EIA key vào Secrets
- Repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `EIA_API_KEY` · Value: dán key vừa lấy → Save.

### 4) Bật GitHub Pages
- Repo → **Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / `/ (root)` → Save.
- Sau ~1 phút sẽ có link dạng `https://<tên-bạn>.github.io/freight-monitor/`. Đây là website của bạn — mở hằng ngày trên điện thoại/máy tính, không cần Claude.

### 5) Chạy bot lần đầu (tùy chọn, để có số mới ngay)
- Repo → tab **Actions** → chọn workflow **"Update freight drivers (EIA)"** → **Run workflow**.
- Sau đó bot tự chạy **07:00 sáng giờ VN, thứ 2–6** (sửa giờ trong `.github/workflows/update.yml`, dòng `cron`).

## Tùy chỉnh
- **Đổi giờ chạy:** sửa `cron: "0 0 * * 1-5"` trong `update.yml` (giờ UTC; 00:00 UTC = 07:00 VN).
- **Thêm/bớt chỉ số EIA:** sửa danh sách `SERIES` trong `fetch_data.py` (series_id tra tại https://www.eia.gov/opendata/browser/).
- **Cập nhật số cước Baltic/scorecard:** sửa trực tiếp trong `index.html` (mục `MKT` và `SEED`), hoặc để trợ lý Claude cập nhật định kỳ rồi thay file.

## Chạy thử ở máy (tùy chọn)
```bash
export EIA_API_KEY=your_key_here
python fetch_data.py        # tạo/cập nhật data.json
python -m http.server 8000  # mở http://localhost:8000
```
