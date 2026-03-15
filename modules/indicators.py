"""
Teknik İndikatörler
RSI, MACD, Bollinger Bands, EMA hesaplamaları.
"""
import pandas as pd
import numpy as np
from typing import Optional
from loguru import logger

# TA-Lib alternatifi olarak ta kütüphanesi
try:
    from ta.trend import EMAIndicator, MACDIndicator, SMAIndicator
    from ta.momentum import RSIIndicator
    from ta.volatility import BollingerBands
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    logger.warning("ta kütüphanesi bulunamadı, basit hesaplamalar kullanılacak")


def calculate_indicators(prices: list) -> dict:
    """
    Verilen fiyat listesinden teknik indikatörleri hesaplar.

    Args:
        prices: Fiyat listesi (en az 50 eleman)

    Returns:
        dict: İndikatör değerleri
    """
    if len(prices) < 50:
        # Yeterli veri yoksa varsayılan değerler döndür
        return _default_indicators()

    df = pd.DataFrame({"close": prices})

    try:
        # RSI (14 periyot)
        rsi = RSIIndicator(close=df["close"], window=14)
        rsi_value = rsi.rsi().iloc[-1]

        # MACD
        macd = MACDIndicator(close=df["close"])
        macd_value = macd.macd().iloc[-1]
        macd_signal = macd.macd_signal().iloc[-1]
        macd_hist = macd.macd_diff().iloc[-1]

        # MACD yönü
        if macd_value > macd_signal:
            macd_direction = "bullish"
        elif macd_value < macd_signal:
            macd_direction = "bearish"
        else:
            macd_direction = "neutral"

        # Bollinger Bands
        bb = BollingerBands(close=df["close"], window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_mid = bb.bollinger_mavg().iloc[-1]
        current_price = df["close"].iloc[-1]

        # Fiyatın Bollinger içindeki pozisyonu
        if current_price > bb_upper:
            bb_position = "upper"
        elif current_price < bb_lower:
            bb_position = "lower"
        else:
            bb_position = "mid"

        # EMA
        ema_50 = EMAIndicator(close=df["close"], window=50).ema_indicator().iloc[-1]
        ema_200 = EMAIndicator(close=df["close"], window=200).ema_indicator().iloc[-1]

        if ema_50 > ema_200:
            ema_relation = "above"
        elif ema_50 < ema_200:
            ema_relation = "below"
        else:
            ema_relation = "equal"

        # Fiyat değişimleri
        price_1h_ago = df["close"].iloc[-1] if len(df) >= 4 else df["close"].iloc[-1]
        price_24h_ago = df["close"].iloc[-1] if len(df) >= 24 else df["close"].iloc[-1]

        change_1h = ((df["close"].iloc[-1] - price_1h_ago) / price_1h_ago) * 100
        change_24h = ((df["close"].iloc[-1] - price_24h_ago) / price_24h_ago) * 100

        return {
            "rsi_14": round(rsi_value, 2),
            "macd": round(macd_value, 2),
            "macd_signal": round(macd_signal, 2),
            "macd_hist": round(macd_hist, 2),
            "macd_signal_direction": macd_direction,
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "bb_mid": round(bb_mid, 2),
            "bb_position": bb_position,
            "ema_50": round(ema_50, 2),
            "ema_200": round(ema_200, 2),
            "ema_50_vs_ema200": ema_relation,
            "price_change_1h_pct": round(change_1h, 2),
            "price_change_24h_pct": round(change_24h, 2),
        }

    except Exception as e:
        logger.error(f"İndikatör hesaplama hatası: {e}")
        return _default_indicators()


def _default_indicators() -> dict:
    """Varsayılan indikatör değerleri (yeterli veri olmadığında kullanılır)."""
    return {
        "rsi_14": 50.0,
        "macd": 0,
        "macd_signal": 0,
        "macd_hist": 0,
        "macd_signal_direction": "neutral",
        "bb_upper": 0,
        "bb_lower": 0,
        "bb_mid": 0,
        "bb_position": "mid",
        "ema_50": 0,
        "ema_200": 0,
        "ema_50_vs_ema200": "equal",
        "price_change_1h_pct": 0,
        "price_change_24h_pct": 0,
    }


def get_indicator_signals(indicators: dict) -> dict:
    """
    İndikatörlerden alım/satım sinyalleri üretir.

    Returns:
        dict: Sinyal bilgileri
    """
    signals = {
        "rsi_signal": "neutral",
        "macd_signal": "neutral",
        "bb_signal": "neutral",
        "ema_signal": "neutral",
        "overall_score": 0
    }

    # RSI sinyali
    rsi = indicators.get("rsi_14", 50)
    if rsi < 30:
        signals["rsi_signal"] = "oversold"  # Alım fırsatı
        signals["overall_score"] += 2
    elif rsi > 70:
        signals["rsi_signal"] = "overbought"  # Satım düşün
        signals["overall_score"] -= 2
    else:
        signals["rsi_signal"] = "neutral"

    # MACD sinyali
    macd_dir = indicators.get("macd_signal_direction", "neutral")
    if macd_dir == "bullish":
        signals["macd_signal"] = "bullish"
        signals["overall_score"] += 1
    elif macd_dir == "bearish":
        signals["macd_signal"] = "bearish"
        signals["overall_score"] -= 1

    # Bollinger sinyali
    bb_pos = indicators.get("bb_position", "mid")
    if bb_pos == "lower":
        signals["bb_signal"] = "oversold"
        signals["overall_score"] += 1
    elif bb_pos == "upper":
        signals["bb_signal"] = "overbought"
        signals["overall_score"] -= 1

    # EMA sinyali
    ema_rel = indicators.get("ema_50_vs_ema200", "equal")
    if ema_rel == "above":
        signals["ema_signal"] = "bullish"
        signals["overall_score"] += 1
    elif ema_rel == "below":
        signals["ema_signal"] = "bearish"
        signals["overall_score"] -= 1

    return signals


if __name__ == "__main__":
    # Test
    import random
    # Mock fiyatlar
    prices = [2600 + random.uniform(-50, 50) for _ in range(60)]
    ind = calculate_indicators(prices)
    print("İndikatörler:", ind)

    signals = get_indicator_signals(ind)
    print("Sinyaller:", signals)