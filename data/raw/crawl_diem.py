import pandas as pd
import requests
import io

# 1. Khai báo các thông số bạn muốn lấy
station = "VVTS"       # Mã sân bay Tân Sơn Nhất (Đổi thành VVNB nếu muốn lấy Nội Bài)
start_year, start_month, start_day = 2026, 1, 1
end_year, end_month, end_day = 2026, 10, 1

# 2. Tạo đường link URL tự động
url = (
    f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
    f"station={station}&data=all"
    f"&year1={start_year}&month1={start_month}&day1={start_day}"
    f"&year2={end_year}&month2={end_month}&day2={end_day}"
    f"&tz=Etc%2FUTC&format=onlycomma"
)

print("Đang tải dữ liệu từ IEM...")

# 3. Gửi request lấy dữ liệu về
response = requests.get(url)

if response.status_code == 200:
    # 4. Đọc dữ liệu CSV trực tiếp vào Pandas DataFrame
    # comment='#' dùng để bỏ qua các dòng chú thích đầu file của IEM
    df = pd.read_csv(io.StringIO(response.text), comment='#')
    
    print("--- TẢI THÀNH CÔNG ---")
    print(f"Tổng số dòng dữ liệu thu được: {len(df)}")
    
    # Hiển thị 5 dòng đầu tiên
    print("\n Dữ liệu mẫu 5 dòng đầu:")
    print(df[['station', 'valid', 'tmpf', 'dwpf', 'relh', 'drct', 'sknt', 'mslp']].head())
    
    # 5. Lưu ra file CSV trên máy tính
    output_filename = f"weather_{station}_{start_year}_to_{end_year}.csv"
    df.to_csv(output_filename, index=False)
    print(f"\nĐã lưu file thành công tại: {output_filename}")
else:
    print(f"Lỗi tải dữ liệu, mã lỗi: {response.status_code}")