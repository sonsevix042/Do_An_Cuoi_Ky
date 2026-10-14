"""Script phân tích dữ liệu chuyến bay tại Cảng HKQT Tân Sơn Nhất (VVTS / SGN).

Bao gồm:
  1. Thống kê Giá trị bị thiếu (Missing Values Analysis).
  2. Phát hiện & Thống kê Dữ liệu nhiễu / Ngoại lai (Noise & Outlier Detection).
  3. Báo cáo Thống kê Chuyên sâu về Chuyến bay & Tình trạng Delay.
"""

from collections import Counter, defaultdict
import csv
import datetime
import math
import os
import sys

# Cấu hình UTF-8 cho console Windows tránh lỗi font tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
  sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_flight_data(csv_path: str):
  """Đọc và parse dữ liệu từ file CSV chuyến bay VVTS."""
  if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Không tìm thấy file: {csv_path}")

  records = []
  with open(csv_path, mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
      records.append(row)
  return records


# ==============================================================================
# 1. THỐNG KÊ GIÁ TRỊ BỊ THIẾU (MISSING VALUES)
# ==============================================================================
def analyze_missing_values(records):
  total = len(records)
  print("\n" + "=" * 80)
  print("           1. BÁO CÁO THỐNG KÊ GIÁ TRỊ BỊ THIẾU (MISSING VALUES)")
  print("=" * 80)
  print(f"Tổng số bản ghi chuyến bay: {total}\n")
  print(
      f"{'Tên trường (Column)':<25} | {'Số lượng thiếu':<16} | {'Tỷ lệ (%)':<10}"
      f" | {'Đánh giá & Nguyên nhân'}"
  )
  print("-" * 80)

  missing_tokens = {"", "n/a", "none", "null"}
  missing_counts = defaultdict(int)

  for row in records:
    for col, val in row.items():
      if val is None or str(val).strip().lower() in missing_tokens:
        missing_counts[col] += 1

  # Giải thích nghiệp vụ cho 9 trường thông tin
  column_explanations = {
      "flight_date": "Ngày cất cánh theo lịch trình",
      "flight_number": "Số hiệu chuyến bay",
      "airline_name": "Tên hãng hàng không",
      "scheduled_dep_vn": "Giờ cất cánh dự kiến (Giờ VN)",
      "actual_dep_vn": "Giờ cất cánh thực tế (Chưa bay hoặc bị hủy sẽ trống/NA)",
      "generic_status": "Trạng thái tổng quát của chuyến bay",
      "is_canceled": "Trạng thái hủy chuyến",
      "is_diverted": "Trạng thái đổi hướng bay",
      "delay_minutes": "Chuyến bị hủy hoặc chưa có giờ bay thực tế/ước tính",
  }

  sorted_cols = sorted(missing_counts.items(), key=lambda x: x[1], reverse=True)
  for col, count in sorted_cols:
    pct = (count / total) * 100
    explanation = column_explanations.get(
        col, "Dữ liệu trống trong phản hồi API"
    )
    print(f"{col:<25} | {count:>14} | {pct:>8.1f}% | {explanation}")

  perfect_cols = [col for col in records[0].keys() if missing_counts[col] == 0]
  print("-" * 80)
  print(
      f"(*) Các trường dữ liệu đầy đủ 100% ({len(perfect_cols)} trường):\n   "
      f" {', '.join(perfect_cols)}"
  )


# ==============================================================================
# 2. PHÂN TÍCH DỮ LIỆU NHIỄU, BẤT THƯỜNG & NGOẠI LAI (NOISE & ANOMALIES)
# ==============================================================================
def analyze_data_noise_and_anomalies(records):
  total = len(records)
  print("\n" + "=" * 80)
  print(
      "      2. PHÂN TÍCH DỮ LIỆU NHIỄU, BẤT THƯỜNG & NGOẠI LAI (NOISE &"
      " ANOMALIES)"
  )
  print("=" * 80)

  early_flights = []
  extreme_delays = []
  unknown_flights = []
  seen_keys = set()
  duplicates = []
  valid_delays = []

  for row in records:
    # A. Kiểm tra trùng lặp bản ghi
    key = (row.get("flight_number"), row.get("scheduled_dep_vn"))
    if key in seen_keys:
      duplicates.append(row)
    else:
      seen_keys.add(key)

    # B. Kiểm tra trạng thái bất thường
    status = str(row.get("generic_status", "")).lower()
    if status in {"unknown", ""} or "unknown" in status:
      unknown_flights.append(row)

    # C. Phân tích giá trị độ trễ
    delay_val = row.get("delay_minutes")
    if delay_val not in {"", None, "N/A"}:
      try:
        val = float(delay_val)
        valid_delays.append(val)
        if val < 0:
          early_flights.append((row, val))
        elif val >= 180:  # Trễ trên 3 tiếng
          extreme_delays.append((row, val))
      except ValueError:
        pass

  print("[A] Kiểm tra Trùng lặp (Duplicate Detection):")
  if duplicates:
    print(
        f"    - Phát hiện {len(duplicates)} chuyến bay trùng lặp số hiệu và giờ"
        " lịch trình."
    )
  else:
    print(
        "    - Hoàn toàn KHÔNG có bản ghi trùng lặp (Khử trùng lặp thành công"
        " 100%)."
    )

  print(
      "\n[B] Chuyến bay cất cánh sớm (Negative Delay / Early Departures):"
  )
  print(
      f"    - Số lượng: {len(early_flights)} chuyến"
      f" ({len(early_flights)/total*100:.1f}% tổng số chuyến)."
  )
  if early_flights:
    early_flights.sort(key=lambda x: x[1])
    earliest = early_flights[0]
    print(
        f"    - Chuyến cất cánh sớm nhất: {earliest[0]['flight_number']} ("
        f"{earliest[0]['airline_name']}) - Sớm {abs(earliest[1]):.0f} phút."
    )

  print("\n[C] Chuyến bay trạng thái không xác định / Thiếu radar:")
  print(
      f"    - Số lượng: {len(unknown_flights)} chuyến"
      f" ({len(unknown_flights)/total*100:.1f}%)."
  )

  print(
      "\n[D] Phân tích Ngoại lai Độ trễ (Outlier Detection theo Quy tắc"
      " IQR):"
  )
  if len(valid_delays) >= 4:
    valid_delays.sort()
    n = len(valid_delays)
    q1 = valid_delays[n // 4]
    median = valid_delays[n // 2]
    q3 = valid_delays[(3 * n) // 4]
    iqr = q3 - q1
    upper_bound = q3 + 1.5 * iqr
    severe_bound = q3 + 3.0 * iqr

    mild_outliers = [v for v in valid_delays if v > upper_bound]
    severe_outliers = [v for v in valid_delays if v > severe_bound]

    print(
        f"    - Tứ phân vị: Q1 = {q1:.1f}m | Median = {median:.1f}m | Q3 ="
        f" {q3:.1f}m | IQR = {iqr:.1f}m"
    )
    print(
        f"    - Ngưỡng ngoại lai trên (Q3 + 1.5*IQR): > {upper_bound:.1f} phút"
        f" -> Có {len(mild_outliers)} chuyến."
    )
    print(
        f"    - Ngưỡng ngoại lai cực đoan (Q3 + 3*IQR) : > {severe_bound:.1f}"
        f" phút -> Có {len(severe_outliers)} chuyến."
    )

  print(
      "\n[E] Top Chuyến bay bị Trễ nhiều nhất (Extreme Delay Outliers):"
  )
  if extreme_delays:
    extreme_delays.sort(key=lambda x: x[1], reverse=True)
    print(
        f"    {'Số hiệu':<10} | {'Hãng bay':<25} | {'Giờ dự kiến (VN)':<20} | {'Độ trễ'}"
    )
    print("    " + "-" * 65)
    for r, d in extreme_delays[:5]:
      print(
          f"    {r['flight_number']:<10} | {r['airline_name'][:23]:<25} |"
          f" {r['scheduled_dep_vn']:<20} | {d:>5.0f} phút (~{d/60:.1f}h)"
      )


# ==============================================================================
# 3. THỐNG KÊ CHI TIẾT KHAI THÁC & DELAY TẠI VVTS
# ==============================================================================
def analyze_flight_performance_statistics(records):
  total = len(records)
  print("\n" + "=" * 80)
  print(
      "      3. BÁO CÁO THỐNG KÊ CHI TIẾT HOẠT ĐỘNG CHUYẾN BAY TẠI VVTS (SGN)"
  )
  print("=" * 80)

  canceled_count = sum(
      1 for r in records if str(r.get("is_canceled")).lower() == "true"
  )
  diverted_count = sum(
      1 for r in records if str(r.get("is_diverted")).lower() == "true"
  )

  delays = []
  delayed_gte_15m = 0
  on_time_count = 0

  for r in records:
    if str(r.get("is_canceled")).lower() == "true":
      continue
    val = r.get("delay_minutes")
    if val not in {"", None, "N/A"}:
      try:
        d = float(val)
        delays.append(d)
        if d >= 15:
          delayed_gte_15m += 1
        else:
          on_time_count += 1
      except ValueError:
        pass

  print("[A] Tổng quan Chỉ số Đúng giờ (OTP - On-Time Performance):")
  print(f"    - Tổng số chuyến bay ghi nhận   : {total:>6}")
  print(
      f"    - Số chuyến bay bị HỦY         : {canceled_count:>6} ("
      f"{canceled_count/total*100:5.1f}%)"
  )
  print(f"    - Số chuyến bay ĐỔI HƯỚNG      : {diverted_count:>6}")
  if delays:
    evaluated_total = len(delays)
    print(f"    - Số chuyến có thông tin giờ bay: {evaluated_total:>6}")
    print(
        f"    - Số chuyến Đúng giờ (< 15 phút): {on_time_count:>6} ("
        f"{on_time_count/evaluated_total*100:5.1f}% OTP)"
    )
    print(
        f"    - Số chuyến Bị trễ   (>= 15 phút): {delayed_gte_15m:>6} ("
        f"{delayed_gte_15m/evaluated_total*100:5.1f}%)"
    )
    avg_d = sum(delays) / len(delays)
    delays_sorted = sorted(delays)
    median_d = delays_sorted[len(delays_sorted) // 2]
    std_d = math.sqrt(sum((x - avg_d) ** 2 for x in delays) / len(delays))
    print(f"    - Độ trễ trung bình             : {avg_d:>6.1f} phút")
    print(f"    - Độ trễ trung vị (Median)      : {median_d:>6.1f} phút")
    print(f"    - Độ lệch chuẩn (Std Dev)       : {std_d:>6.1f} phút")

  # Thống kê theo Hãng hàng không
  print(
      "\n[B] Thống kê Tình trạng Delay theo Hãng Hàng Không (Top 8 Hãng):"
  )
  print(
      f"    {'Hãng hàng không':<25} | {'Tổng chuyến':<12} | {'Trễ (>=15m)':<12}"
      f" | {'Tỷ lệ trễ':<10} | {'Độ trễ TB'}"
  )
  print("    " + "-" * 75)

  airline_data = defaultdict(lambda: {"total": 0, "delayed": 0, "delays": []})
  for r in records:
    airline = r.get("airline_name") or "Khác"
    airline_data[airline]["total"] += 1
    d_val = r.get("delay_minutes")
    if d_val not in {"", None, "N/A"}:
      try:
        d = float(d_val)
        airline_data[airline]["delays"].append(d)
        if d >= 15:
          airline_data[airline]["delayed"] += 1
      except ValueError:
        pass

  top_airlines = sorted(
      airline_data.items(), key=lambda x: x[1]["total"], reverse=True
  )[:8]
  for name, stat in top_airlines:
    cnt = stat["total"]
    del_cnt = stat["delayed"]
    pct = (del_cnt / cnt) * 100 if cnt > 0 else 0
    avg_delay = (
        (sum(stat["delays"]) / len(stat["delays"])) if stat["delays"] else 0
    )
    print(
        f"    {name[:24]:<25} | {cnt:>11} | {del_cnt:>11} | {pct:>8.1f}% |"
        f" {avg_delay:>6.1f}m"
    )

  # Thống kê theo Ngày bay
  print("\n[C] Thống kê Tình trạng Delay theo Ngày bay (flight_date):")
  print(
      f"    {'Ngày bay':<20} | {'Tổng chuyến':<12} | {'Trễ (>=15m)':<12} | {'Tỷ lệ trễ'}"
  )
  print("    " + "-" * 60)

  date_data = defaultdict(lambda: {"total": 0, "delayed": 0})
  for r in records:
    f_date = r.get("flight_date") or "N/A"
    date_data[f_date]["total"] += 1
    d_val = r.get("delay_minutes")
    if d_val not in {"", None, "N/A"}:
      try:
        if float(d_val) >= 15:
          date_data[f_date]["delayed"] += 1
      except ValueError:
        pass

  for f_date, stat in sorted(date_data.items()):
    tot = stat["total"]
    del_c = stat["delayed"]
    p = (del_c / tot) * 100 if tot > 0 else 0
    print(f"    {f_date:<20} | {tot:>11} | {del_c:>11} | {p:>8.1f}%")

  # Thống kê theo Khung giờ trong ngày
  print(
      "\n[D] Thống kê Tỷ lệ Trễ chuyến theo Khung giờ Khởi hành tại VVTS:"
  )
  print(
      f"    {'Khung giờ (Giờ địa phương VN)':<30} | {'Tổng chuyến':<12} | {'Số chuyến trễ':<14} | {'Tỷ lệ trễ'}"
  )
  print("    " + "-" * 75)

  hour_blocks = {
      "Đêm & Rạng sáng (00:00 - 05:59)": {"total": 0, "delayed": 0},
      "Buổi sáng       (06:00 - 11:59)": {"total": 0, "delayed": 0},
      "Buổi chiều      (12:00 - 17:59)": {"total": 0, "delayed": 0},
      "Buổi tối        (18:00 - 23:59)": {"total": 0, "delayed": 0},
  }

  for r in records:
    sched_time_str = r.get("scheduled_dep_vn")
    if sched_time_str and sched_time_str != "N/A":
      try:
        hour = int(sched_time_str.split(" ")[1].split(":")[0])
        if 0 <= hour < 6:
          b_key = "Đêm & Rạng sáng (00:00 - 05:59)"
        elif 6 <= hour < 12:
          b_key = "Buổi sáng       (06:00 - 11:59)"
        elif 12 <= hour < 18:
          b_key = "Buổi chiều      (12:00 - 17:59)"
        else:
          b_key = "Buổi tối        (18:00 - 23:59)"

        hour_blocks[b_key]["total"] += 1
        d_val = r.get("delay_minutes")
        if d_val not in {"", None, "N/A"} and float(d_val) >= 15:
          hour_blocks[b_key]["delayed"] += 1
      except Exception:
        pass

  for block_name, b_stat in hour_blocks.items():
    b_tot = b_stat["total"]
    b_del = b_stat["delayed"]
    b_pct = (b_del / b_tot) * 100 if b_tot > 0 else 0
    print(f"    {block_name:<30} | {b_tot:>11} | {b_del:>13} | {b_pct:>8.1f}%")

  print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
  csv_file = os.path.join(
      os.path.dirname(__file__), "vvts_departures_delay.csv"
  )
  if not os.path.exists(csv_file):
    csv_file = "vvts_departures_delay.csv"

  data = load_flight_data(csv_file)
  analyze_missing_values(data)
  analyze_data_noise_and_anomalies(data)
  analyze_flight_performance_statistics(data)