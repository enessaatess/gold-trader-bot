"""
Piyasa Saat Kontrolü
Altın piyasasının açık olup olmadığını kontrol eder.
"""
import datetime
from zoneinfo import ZoneInfo
from config import FIXED_HOLIDAYS


def is_market_open() -> bool:
    """
    Piyasanın açık olup olmadığını kontrol eder.

    Kurallar:
    - Hafta içi (Pazartesi-Cuma)
    - Cuma 22:00 UTC'den sonra kapalı
    - Hafta sonu kapalı
    - ABD/İngiltere tatillerinde kapalı
    - Gece 22:00-00:00 UTC arası düşük likidite nedeniyle kapalı
    """
    now_utc = datetime.datetime.now(ZoneInfo("UTC"))

    # Hafta sonu kontrolü (0=Pazartesi, 5=Cumartesi, 6=Pazar)
    if now_utc.weekday() >= 5:
        return False

    # Cuma 22:00 UTC sonrası kapanır
    if now_utc.weekday() == 4 and now_utc.hour >= 22:
        return False

    # Pazar 22:00 UTC öncesi açılmaz (sabah 6'ya kadar bekle)
    if now_utc.weekday() == 6 and now_utc.hour < 22:
        # Pazar günü 22:00'e kadar bekle
        if now_utc.hour < 22:
            return False

    # Tatil kontrolü
    date_str = now_utc.strftime("%m-%d")
    if date_str in FIXED_HOLIDAYS:
        return False

    # Dinamik tatiller kontrolü (Thanksgiving, Memorial Day, Labor Day, MLK Day)
    if _is_us_holiday(now_utc):
        return False

    # Gece arası düşük likidite: 22:00-02:00 UTC (gece yarısından sonra da kapalı)
    if now_utc.hour >= 22 or now_utc.hour < 2:
        return False

    return True


def _is_us_holiday(dt: datetime.datetime) -> bool:
    """ABD dinamik tatillerini kontrol eder."""
    month = dt.month
    day = dt.day
    weekday = dt.weekday()

    # Thanksgiving: 4. Perşembe (Kasım)
    if month == 11:
        # Kasım'ın 4. perşembesini bul
        first_day = datetime.datetime(dt.year, 11, 1)
        first_thursday = first_day + datetime.timedelta(days=(3 - first_day.weekday() + 7) % 7)
        thanksgiving = first_thursday + datetime.timedelta(weeks=3)
        if day == thanksgiving.day:
            return True

    # Memorial Day: 5. Pazartesi (Mayıs)
    if month == 5:
        # Mayıs'ın son pazartesi
        if day >= 25 and weekday == 0:
            return True

    # Labor Day: 1. Pazartesi (Eylül)
    if month == 9 and day <= 7 and weekday == 0:
        return True

    # MLK Day: 3. Pazartesi (Ocak)
    if month == 1 and 15 <= day <= 21 and weekday == 0:
        return True

    return False


def get_current_session() -> str:
    """
    Mevcut piyasa сеансыını döndürür.
    """
    now_utc = datetime.datetime.now(ZoneInfo("UTC"))
    hour = now_utc.hour

    # Gece (Sydney)
    if hour >= 22 or hour < 7:
        return "sydney"

    # Tokyo
    if hour < 9:
        return "tokyo"

    # Londra
    if hour < 17:
        return "london"

    # London-NY Overlap (en yüksek likidite)
    if 13 <= hour < 17:
        return "london_ny_overlap"

    # New York
    return "new_york"


def get_market_hours_info() -> dict:
    """Piyasa hakkında detaylı bilgi döndürür."""
    now_utc = datetime.datetime.now(ZoneInfo("UTC"))
    is_open = is_market_open()
    session = get_current_session()

    return {
        "is_open": is_open,
        "session": session,
        "utc_time": now_utc.isoformat(),
        "hour_utc": now_utc.hour,
        "weekday": now_utc.strftime("%A"),
    }


if __name__ == "__main__":
    # Test
    info = get_market_hours_info()
    print(f"Piyasa Açık: {info['is_open']}")
    print(f"Seans: {info['session']}")
    print(f"UTC Saat: {info['hour_utc']}")
    print(f"Gün: {info['weekday']}")