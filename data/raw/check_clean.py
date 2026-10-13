from pathlib import Path
import pandas as pd
import numpy as np

# 1. THIET LAP DUONG DAN TUYET DOI
BASE_DIR = Path(__file__).resolve().parent
FILE_NAME = "weather_VVTS_202501_to_202610.csv"  # Thay bang ten file CSV cua ban
FILE_PATH = BASE_DIR / FILE_NAME

if not FILE_PATH.exists():
    print(f"Loi: Khong tim thay file tai: {FILE_PATH}")
    print("Huong dan: Dat file CSV vao cung thu muc voi file script Python nay.")
    exit()

# 2. TU DIEN GIAI THICH VIET TAT CAC FEATURE CUA IEM
FEATURE_DESCRIPTIONS = {
    'station': 'Ma tran quan trac (ICAO code)',
    'valid': 'Thoi gian quan trac (UTC)',
    'lon': 'Kinh do tram quan trac',
    'lat': 'Vi do tram quan trac',
    'tmpf': 'Nhieu do khong khi (do F)',
    'dwpf': 'Nhiet do diem suong (do F)',
    'relh': 'Do am tuong doi (%)',
    'drct': 'Huong gio (do, 0-360)',
    'sknt': 'Toc do gio (knots)',
    'p01i': 'Luong mua tich luy 1 gio (inches)',
    'alti': 'Ap suat khi ap ke (inches Hg)',
    'mslp': 'Ap suat muc nuoc bien (hPa / mb)',
    'vsby': 'Tam nhin xa (dam / miles)',
    'gust': 'Toc do gio giat (knots)',
    'skyc1': 'Ma do phu may tang 1 (CLR, FEW, BKN, OVC...)',
    'skyc2': 'Ma do phu may tang 2',
    'skyc3': 'Ma do phu may tang 3',
    'skyc4': 'Ma do phu may tang 4',
    'skyl1': 'Chieu cao chan may tang 1 (feet)',
    'skyl2': 'Chieu cao chan may tang 2 (feet)',
    'skyl3': 'Chieu cao chan may tang 3 (feet)',
    'skyl4': 'Chieu cao chan may tang 4 (feet)',
    'wxcodes': 'Ma hien thuong thoi tiet dac biet (mua, dong, mu...)',
    'ice_accretion_1hr': 'Do day dong bang tich luy 1 gio (inches)',
    'ice_accretion_3hr': 'Do day dong bang tich luy 3 gio (inches)',
    'ice_accretion_6hr': 'Do day dong bang tich luy 6 gio (inches)',
    'peak_wind_gust': 'Toc do gio giat dinh (knots)',
    'peak_wind_drct': 'Huong gio giat dinh (do)',
    'feel': 'Nhiet do cam nhan / Wind Chill / Heat Index (do F)',
    'metar': 'Chuoi ban tin METAR goc chua giai ma'
}

# 3. DOC VA LAM SACH BAN DAU
df = pd.read_csv(FILE_PATH, comment='#')

# Doi cac ky tu rong va 'M' (Missing value cua IEM) thanh NaN
df_check = df.replace(['M', ' ', 'None', 'null'], np.nan)
total_rows = len(df_check)

print("BAO CAO KIEM TRA TOAN BO FEATURES DU LIEU IEM")
print(f"Duong dan: {FILE_PATH}")
print(f"Tong so dong: {total_rows}")
print("=" * 80)

# 4. CHUYEN DOI KIEU DU LIEU SO CAN THIET
numeric_cols = [
    'lon', 'lat', 'tmpf', 'dwpf', 'relh', 'drct', 'sknt', 'p01i',
    'alti', 'mslp', 'vsby', 'gust', 'skyl1', 'skyl2', 'skyl3', 'skyl4',
    'ice_accretion_1hr', 'ice_accretion_3hr', 'ice_accretion_6hr',
    'peak_wind_gust', 'peak_wind_drct', 'feel'
]

for col in numeric_cols:
    if col in df_check.columns:
        df_check[col] = pd.to_numeric(df_check[col], errors='coerce')

# 5. CHECK 1: BANG TY LE KHUYET DU LIEU KEM GIAC THICH FEATURE
print("\n[CHECK 1] BANG DANH GIA CAC FEATURE VA TY LE KHUYET DU LIEU:")
missing_stats = df_check.isnull().sum()
missing_percent = (missing_stats / total_rows) * 100

missing_df = pd.DataFrame({
    'So luong khuyet': missing_stats,
    'Ty le khuyet (%)': missing_percent.round(2)
})

# Them cot giai thich nghia viet tat tu tu dien
missing_df['Giai thich feature'] = missing_df.index.map(
    lambda x: FEATURE_DESCRIPTIONS.get(x, 'Chua co mo ta')
)

# Sap xep lai thu tu cac cot de de quan sat
missing_df = missing_df[['Giai thich feature', 'So luong khuyet', 'Ty le khuyet (%)']]

# In toan bo bang khong bi cat ngan
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 1000)

print(missing_df.to_string())

# 6. CHECK 2: KIEM TRA TRUNG LAP MOC THOI GIAN
print("\n" + "-" * 80)
print("[CHECK 2] KIEM TRA TRUNG LAP MOC THOI GIAN (valid):")
if 'valid' in df_check.columns:
    duplicates = df_check.duplicated(subset=['valid'], keep=False)
    num_duplicates = duplicates.sum()

    if num_duplicates > 0:
        print(f"CANH BAO: Phat hien {num_duplicates} dong bi trung moc thoi gian!")
        print(df_check[duplicates][['valid', 'tmpf', 'sknt']].head())
    else:
        print("Thanh cong: Khong co moc thoi gian nao bi trung lap.")

# 7. CHECK 3: KIEM TRA LOGIC CAC FEATURE
print("\n" + "-" * 80)
print("[CHECK 3] KIEM TRA LOGIC CAC FEATURE TOAN DIEN:")
anomalies = []

# a. Toa do (lon, lat)
if 'lat' in df_check.columns:
    inv_lat = df_check[(df_check['lat'] < -90) | (df_check['lat'] > 90)]
    if not inv_lat.empty:
        anomalies.append(f"- Vi do (lat) ngoai khoang [-90, 90]: {len(inv_lat)} dong")

if 'lon' in df_check.columns:
    inv_lon = df_check[(df_check['lon'] < -180) | (df_check['lon'] > 180)]
    if not inv_lon.empty:
        anomalies.append(f"- Kinh do (lon) ngoai khoang [-180, 180]: {len(inv_lon)} dong")

# b. Nhiet do & Nhiet do cam nhan (tmpf, dwpf, feel)
if 'feel' in df_check.columns:
    inv_feel = df_check[(df_check['feel'] < 30) | (df_check['feel'] > 130)]
    if not inv_feel.empty:
        anomalies.append(f"- Nhiet do cam nhan (feel) bat thuong (< 30F hoac > 130F): {len(inv_feel)} dong")

# c. Tam nhin xa (vsby - dam)
if 'vsby' in df_check.columns:
    inv_vsby = df_check[(df_check['vsby'] < 0) | (df_check['vsby'] > 15)]
    if not inv_vsby.empty:
        anomalies.append(f"- Tam nhin (vsby) am hoac > 15 dam: {len(inv_vsby)} dong")

# d. Ap suat (mslp - hPa, alti - inch Hg)
if 'mslp' in df_check.columns:
    inv_mslp = df_check[(df_check['mslp'] < 900) | (df_check['mslp'] > 1080)]
    if not inv_mslp.empty:
        anomalies.append(f"- Ap suat muc nuoc bien (mslp) ngoai khoang 900-1080 hPa: {len(inv_mslp)} dong")

# e. Gio & Gio giat (sknt, gust)
if 'gust' in df_check.columns and 'sknt' in df_check.columns:
    inv_gust = df_check[df_check['gust'] < df_check['sknt']]
    if not inv_gust.empty:
        anomalies.append(f"- Gio giat (gust) nho hon toc do gio trung binh (sknt): {len(inv_gust)} dong")

# IN KET QUA LOGIC
if anomalies:
    print("Phat hien cac gia tri di biet:")
    for a in anomalies:
        print(a)
else:
    print("Thanh cong: Tat ca cac feature deu nam trong khoang gia tri logic cho phep.")

# 8. CHECK 4: KIEM TRA MONG GIU LIEU GIUAC CAC KHOANG THOI GIAN
print("\n" + "-" * 80)
print("[CHECK 4] KIEM TRA GIAN DOAN THOI GIAN (> 3 tieng):")
if 'valid' in df_check.columns:
    df_check['valid_dt'] = pd.to_datetime(df_check['valid'])
    df_check = df_check.sort_values('valid_dt')
    df_check['time_diff'] = df_check['valid_dt'].diff()

    large_gaps = df_check[df_check['time_diff'] > pd.Timedelta(hours=3)]
    if not large_gaps.empty:
        print(f"CANH BAO: Phat hien {len(large_gaps)} khoang gian doan du lieu > 3 tieng:")
        print(large_gaps[['valid', 'time_diff']].head())
    else:
        print("Thanh cong: Chuoi thoi gian lien tuc, khong co khoang mat du lieu qua 3 tieng.")