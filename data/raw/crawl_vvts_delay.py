"""Script thu thập dữ liệu chuyến bay và tình trạng delay tại Sân bay Tân Sơn Nhất (VVTS / SGN).

Nguồn: Flightradar24 Airport Schedule API (JSON Endpoint).
"""

import datetime
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

# Cấu hình UTF-8 cho Windows console tránh lỗi charmap
if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
  sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("VVTS_Crawler")

AIRPORT_CODE = "sgn"
BASE_URL = "https://api.flightradar24.com/common/v1/airport.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
    " Gecko) Chrome/128.0.0.0 Safari/537.36"
)
VN_TZ = datetime.timezone(datetime.timedelta(hours=7))  # Giờ Việt Nam UTC+7


def fetch_page(
    page: int, limit: int = 100, retries: int = 3, delay: float = 1.0
) -> Optional[Dict[str, Any]]:
  """Gửi HTTP request lấy dữ liệu một trang chuyến bay từ API Flightradar24."""
  params = [
      ("code", AIRPORT_CODE),
      ("plugin[]", ""),
      ("plugin-setting[schedule][mode]", "departures"),
      ("page", str(page)),
      ("limit", str(limit)),
  ]
  url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
  req = urllib.request.Request(
      url,
      headers={
          "User-Agent": USER_AGENT,
          "Accept": "application/json",
          "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
          "Referer": (
              f"https://www.flightradar24.com/data/airports/{AIRPORT_CODE}"
          ),
      },
  )

  for attempt in range(1, retries + 1):
    try:
      with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.getcode() == 200:
          return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
      logger.warning("Trang %d: Lỗi kết nối %s (Thử lại %d/%d)", page, e, attempt, retries)
    time.sleep(delay * (2 ** (attempt - 1)))
  return None


def parse_flight_item(raw_flight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
  """Bóc tách và chuẩn hóa dữ liệu chuyến bay, chỉ trích xuất 9 trường yêu cầu."""
  try:
    flight = raw_flight.get("flight", {})
    if not flight:
      return None

    ident = flight.get("identification", {})
    flight_number = (
        ident.get("number", {}).get("default") or ident.get("callsign") or "N/A"
    )

    airline_info = flight.get("airline", {})
    airline_name = (
        airline_info.get("name") or airline_info.get("short") or "N/A"
    )

    time_info = flight.get("time", {})
    sched_ts = time_info.get("scheduled", {}).get("departure")
    real_ts = time_info.get("real", {}).get("departure")
    est_ts = time_info.get("estimated", {}).get("departure")

    status_info = flight.get("status", {})
    status_text = status_info.get("text") or "N/A"
    generic_status = (
        status_info.get("generic", {}).get("status", {}).get("text") or "N/A"
    )

    is_canceled = (
        generic_status.lower() == "canceled"
        or "canceled" in status_text.lower()
    )
    is_diverted = bool(
        status_info.get("generic", {}).get("status", {}).get("diverted")
    )

    actual_or_est_ts = real_ts if real_ts else est_ts
    delay_minutes = None

    if sched_ts and actual_or_est_ts and not is_canceled:
      delay_minutes = round((actual_or_est_ts - sched_ts) / 60)

    def to_vn_str(ts: Optional[int]) -> str:
      if not ts:
        return "N/A"
      return datetime.datetime.fromtimestamp(ts, tz=VN_TZ).strftime(
          "%Y-%m-%d %H:%M:%S"
      )

    flight_date_str = "N/A"
    if sched_ts:
      flight_date_str = datetime.datetime.fromtimestamp(
          sched_ts, tz=VN_TZ
      ).strftime("%Y-%m-%d")

    return {
        "flight_date": flight_date_str,
        "flight_number": flight_number,
        "airline_name": airline_name,
        "scheduled_dep_vn": to_vn_str(sched_ts),
        "actual_dep_vn": to_vn_str(real_ts),
        "generic_status": generic_status,
        "is_canceled": is_canceled,
        "is_diverted": is_diverted,
        "delay_minutes": delay_minutes,
    }
  except Exception as err:
    logger.debug("Lỗi parse item: %s", err)
    return None


def crawl_vvts_departures(
    include_past: bool = True,
    include_future: bool = True,
    max_pages_per_direction: int = 6,
    request_delay: float = 1.0,
) -> List[Dict[str, Any]]:
  """Quét toàn bộ chuyến bay cả quá khứ (đã bay) và tương lai (sắp bay)."""
  flights_dict: Dict[str, Dict[str, Any]] = {}
  pages_to_crawl = []
  if include_past:
    pages_to_crawl.extend(range(-1, -max_pages_per_direction - 1, -1))
  if include_future:
    pages_to_crawl.extend(range(1, max_pages_per_direction + 1))

  logger.info(
      "Bắt đầu thu thập dữ liệu VVTS (SGN) trên %d trang...", len(pages_to_crawl)
  )

  for page in pages_to_crawl:
    direction_label = "Quá khứ" if page < 0 else "Hiện tại/Tương lai"
    logger.info("Đang tải [%s] Trang %d...", direction_label, page)
    data = fetch_page(page=page, limit=100, delay=request_delay)
    if not data:
      continue

    sched_data = (
        data.get("result", {})
        .get("response", {})
        .get("airport", {})
        .get("pluginData", {})
        .get("schedule", {})
        .get("departures", {})
    )
    raw_items = sched_data.get("data", [])
    if not raw_items:
      continue

    page_count = 0
    for raw_item in raw_items:
      parsed = parse_flight_item(raw_item)
      if parsed:
        u_key = f"{parsed['flight_number']}_{parsed['scheduled_dep_vn']}"
        if u_key not in flights_dict:
          flights_dict[u_key] = parsed
          page_count += 1

    logger.info(
        "-> Trang %d: Thu được %d chuyến mới (Tổng tích lũy: %d)",
        page,
        page_count,
        len(flights_dict),
    )
    time.sleep(request_delay)

  flight_list = list(flights_dict.values())
  flight_list.sort(key=lambda x: x.get("scheduled_dep_vn") or "")
  return flight_list


def export_to_csv_and_json(
    flights: List[Dict[str, Any]], base_name: str = "vvts_departures_delay"
) -> None:
  """Xuất file JSON và CSV (UTF-8 BOM tương thích Excel)."""
  if not flights:
    return
  with open(f"{base_name}.json", "w", encoding="utf-8") as f:
    json.dump(flights, f, ensure_ascii=False, indent=2)

  try:
    import pandas as pd

    df = pd.DataFrame(flights)
    df.to_csv(f"{base_name}.csv", index=False, encoding="utf-8-sig")
  except Exception:
    import csv

    with open(
        f"{base_name}.csv", "w", newline="", encoding="utf-8-sig"
    ) as f:
      writer = csv.DictWriter(f, fieldnames=flights[0].keys())
      writer.writeheader()
      writer.writerows(flights)
  logger.info(
      "Đã lưu kết quả thành công vào %s.csv và %s.json", base_name, base_name
  )


if __name__ == "__main__":
  results = crawl_vvts_departures(
      include_past=True,
      include_future=False,
      max_pages_per_direction=6,
      request_delay=1.0,
  )
  export_to_csv_and_json(results, base_name="vvts_departures_delay")