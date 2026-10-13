import pandas as pd
import requests
import io
import time
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# ---------------------------------------------------------
# 1. Khai báo các thông số
# ---------------------------------------------------------
station = "VVTS"  # Tân Sơn Nhất (VVNB cho Nội Bài)
start_date = pd.Timestamp("2025-01-01")
end_date = pd.Timestamp("2026-10-01")

# ---------------------------------------------------------
# 2. Cấu hình Session chống Ban IP & Tự động Retry
# ---------------------------------------------------------
session = requests.Session()

# Tự động thử lại tối đa 5 lần nếu gặp lỗi mạng hoặc server quá tải (429, 500, 502, 503, 504)
# Thời gian chờ giữa các lần thử tăng dần (2s, 4s, 8s...)
retries = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Đổi User-Agent để tránh bị hệ thống chống bot chặn
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WeatherDataCollector/1.0 (contact: your_email@domain.com)"
}

# ---------------------------------------------------------
# 3. Chia nhỏ khoảng thời gian theo từng tháng để tải
# ---------------------------------------------------------
date_ranges = pd.date_range(start=start_date, end=end_date, freq='MS')
all_dfs = []

print(f"Bắt đầu thu thập dữ liệu trạm {station} từ {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}...\n")

for i, current_start in enumerate(date_ranges):
    # Tính ngày cuối của tháng hiện tại
    current_end = current_start + pd.offsets.MonthEnd(1)
    if current_end > end_date:
        current_end = end_date

    url = (
        f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
        f"station={station}&data=all"
        f"&year1={current_start.year}&month1={current_start.month}&day1={current_start.day}"
        f"&year2={current_end.year}&month2={current_end.month}&day2={current_end.day}"
        f"&tz=Etc%2FUTC&format=onlycomma"
    )

    print(f"[{i+1}/{len(date_ranges)}] Đang tải tháng {current_start.strftime('%m/%Y')}...")

    try:
        # Giới hạn timeout 30s tránh treo script
        response = session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200 and len(response.text.strip()) > 0:
            df_chunk = pd.read_csv(io.StringIO(response.text), comment='#')
            
            # Kiểm tra xem dữ liệu trả về có hợp lệ không
            if not df_chunk.empty and 'station' in df_chunk.columns:
                all_dfs.append(df_chunk)
                print(f"   -> Thành công: Lấy được {len(df_chunk)} dòng.")
            else:
                print("   -> Bỏ qua: Không có dữ liệu trong khoảng thời gian này.")
        else:
            print(f"   -> Lỗi HTTP mã: {response.status_code}")

    except Exception as e:
        print(f"   -> Lỗi khi kết nối: {e}")

    # Tạm nghỉ 1.5 giây giữa mỗi lượt tải để không bị coi là tấn công dDOS
    time.sleep(1.5)

# ---------------------------------------------------------
# 4. Gộp dữ liệu và xuất file CSV
# ---------------------------------------------------------
if all_dfs:
    df_final = pd.concat(all_dfs, ignore_index=True)
    
    # Loại bỏ các bản ghi bị trùng lặp (nếu có)
    df_final = df_final.drop_duplicates()

    print("\n" + "="*40)
    print("--- HOÀN THÀNH TẢI DỮ LIỆU ---")
    print(f"Tổng số dòng dữ liệu thu được: {len(df_final)}")
    print("="*40)
    
    output_filename = f"weather_{station}_{start_date.strftime('%Y%m')}_to_{end_date.strftime('%Y%m')}.csv"
    df_final.to_csv(output_filename, index=False)
    print(f"\nĐã lưu toàn bộ dữ liệu vào file: {output_filename}")
else:
    print("\nKhông thu thập được dữ liệu nào.")