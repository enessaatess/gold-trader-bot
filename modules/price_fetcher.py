"""
Fiyat Verisi Çekme
GoldAPI.io ve yedek olarak Metals-API'den altın fiyatı çeker.
"""
import os
import requests
import random
import time
from typing import Optional
from loguru import logger

import config


def fetch_gold_price() -> Optional[dict]:
    """
    GoldAPI.io'dan altın fiyatını çeker.

    Returns:
        dict: {"xau_usd": float, "xau_try": float, "usd_try": float}
    """
    api_key = config.GOLDAPI_KEY
    if not api_key:
        logger.warning("GOLDAPI_KEY ayarlanmamış, yedek kullanılıyor")
        return _get_fallback_price()

    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json"
    }

    try:
        # XAU/USD çek
        response = requests.get(
            "https://www.goldapi.io/api/XAU/USD",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            xau_usd = data.get("price", 0)
            logger.info(f"GoldAPI'den XAU/USD: ${xau_usd}")
        elif response.status_code == 429:
            logger.warning("GoldAPI rate limit aşıldı, yedek fiyat kullanılıyor")
            return _get_fallback_price()
        else:
            logger.error(f"GoldAPI hatası: {response.status_code}")
            return _get_fallback_price()

    except Exception as e:
        logger.error(f"GoldAPI bağlantı hatası: {e}")
        return _get_fallback_price()

    # USD/TRY kurunu çek
    usd_try = fetch_usd_try_rate()
    if not usd_try:
        logger.error("USD/TRY kuru alınamadı")
        return None

    xau_try = xau_usd * usd_try

    return {
        "xau_usd": round(xau_usd, 2),
        "xau_try": round(xau_try, 2),
        "usd_try": round(usd_try, 4),
        "source": "goldapi"
    }


def fetch_usd_try_rate() -> Optional[float]:
    """
    Open Exchange Rates'dan USD/TRY kurunu çeker.
    """
    api_key = config.OPENEXCHANGE_KEY
    if not api_key:
        logger.warning("OPENEXCHANGE_KEY ayarlanmamış")
        return None

    try:
        # Free tier sadece USD base destekler
        url = f"https://openexchangerates.org/api/latest.json?app_id={api_key}&base=USD&symbols=TRY"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            rate = data.get("rates", {}).get("TRY")
            if rate:
                logger.info(f"USD/TRY kuru: {rate}")
                return rate
        else:
            logger.error(f"OpenExchangeRates hatası: {response.status_code}")

    except Exception as e:
        logger.error(f"OpenExchangeRates bağlantı hatası: {e}")

    return None


def _get_fallback_price() -> dict:
    """
    API limiti aşıldığında veya hata olduğunda yedek fiyat döndürür.
    Son bilinen fiyata küçük bir simüle gürültü ekler.
    """
    # Varsayılan fiyat (yaklaşık güncel değer)
    base_xau_usd = 2650.0
    base_usd_try = 32.5

    # %0.5'e kadar rastgele değişim
    noise = 1 + random.uniform(-0.005, 0.005)
    xau_usd = base_xau_usd * noise
    usd_try = base_usd_try * (1 + random.uniform(-0.002, 0.002))
    xau_try = xau_usd * usd_try

    logger.warning(f"Yedek fiyat kullanılıyor: XAU/USD=${xau_usd:.2f}, USD/TRY={usd_try:.4f}")

    return {
        "xau_usd": round(xau_usd, 2),
        "xau_try": round(xau_try, 2),
        "usd_try": round(usd_try, 4),
        "source": "fallback"
    }


def get_historical_prices(days: int = 30) -> list:
    """
    Geçmiş fiyat verileri için (ileride teknik indikatörler için kullanılacak).
    Şimdilik basit bir mock data döndürür.
    """
    # Gerçek uygulamada GoldAPI'nin historical endpoint'i kullanılabilir
    # veya SQLite'dan son X günün verileri çekilebilir
    return []


if __name__ == "__main__":
    # Test
    logger.info("Fiyat test ediliyor...")
    price = fetch_gold_price()
    print(f"Sonuç: {price}")