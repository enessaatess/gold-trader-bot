"""
AI Karar Motoru
Groq API ile Llama modeli kullanarak alım/satım kararı üretir.
"""
import os
import json
from typing import Optional
from loguru import logger

try:
    from groq import Groq
except ImportError:
    logger.error("groq kütüphanesi yüklü değil!")
    raise

import config


# Sistem promptu
SYSTEM_PROMPT = """Sen 15 yıllık deneyimli bir XAU/USD spot altın traderısın.
Görevin: 30 günlük sanal deney süresinde portföy değerini maksimize etmek.
Asla tüm sermayeyi tek işleme koyma. Risk yönetimi her şeyden önce gelir.

Karar verirken şunlara dikkat et:
- RSI 30 altı: aşırı satım → alım fırsatı
- RSI 70 üstü: aşırı alım → satım düşün
- MACD bullish crossover → pozitif sinyal
- MACD bearish crossover → negatif sinyal
- Bollinger alt bandı kırılımı → alım fırsatı
- Bollinger üst bandı kırılımı → dikkatli ol
- DXY yükselişi → altın baskı altında
- DXY düşüşü → altın için olumlu
- Haber skoru +0.5 üstü → pozitif katalizör
- Haber skoru -0.5 altı → negatif katalizör

Yalnızca aşağıdaki JSON formatında cevap ver, başka hiçbir şey yazma:
{
  "action": "BUY" | "SELL" | "HOLD",
  "amount_grams": float,
  "confidence": 0.0-1.0,
  "reasoning": "Kısa açıklama"
}

Aksiyon kuralları:
- Sadece portföyün en fazla %5'ini tek işlemde kullan
- Güven %55'in altındaysa HOLD yap
- Günde max 8 işlem
- 30 dk içinde tekrar işlem yapma"""


def get_ai_decision(market_data: dict) -> Optional[dict]:
    """
    Groq API'ye market verilerini gönderir ve karar alır.

    Args:
        market_data: Piyasa verileri (fiyat, indikatörler, haber, portföy)

    Returns:
        dict: {"action": str, "amount_grams": float, "confidence": float, "reasoning": str}
    """
    api_key = config.GROQ_API_KEY

    if not api_key:
        logger.error("GROQ_API_KEY ayarlanmamış!")
        return None

    try:
        client = Groq(api_key=api_key)

        # Kullanıcı mesajını hazırla
        user_message = json.dumps(market_data, indent=2, ensure_ascii=False)

        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=config.GROQ_TEMPERATURE,
            max_tokens=config.GROQ_MAX_TOKENS,
            response_format={"type": "json_object"}
        )

        # JSON yanıtını parse et
        content = response.choices[0].message.content

        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            # JSON değilse, JSON parçası bulmaya çalış
            logger.warning(f"AI yanıtı düzgün JSON değil: {content[:200]}")
            decision = _extract_json_from_text(content)

        # Alanları normalize et
        decision = _normalize_decision(decision)

        logger.info(f"AI Kararı: {decision.get('action')} | Güven: {decision.get('confidence')}")

        return decision

    except Exception as e:
        logger.error(f"Groq API hatası: {e}")
        return None


def _extract_json_from_text(text: str) -> dict:
    """Metin içinden JSON parçasını çıkartır."""
    import re

    # JSON objesi bulmaya çalış
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    # Bulunamazsa varsayılan HOLD döndür
    return {
        "action": "HOLD",
        "amount_grams": 0,
        "confidence": 0,
        "reasoning": "JSON parse hatası"
    }


def _normalize_decision(decision: dict) -> dict:
    """Karar sözlüğünü normalize eder."""
    action = decision.get("action", "HOLD").upper()

    # Geçersiz aksiyonları düzelt
    if action not in ["BUY", "SELL", "HOLD"]:
        action = "HOLD"

    # Miktarı float'a çevir
    try:
        amount = float(decision.get("amount_grams", 0))
    except:
        amount = 0

    # Güveni 0-1 arasına sınırla
    try:
        confidence = float(decision.get("confidence", 0))
        confidence = max(0, min(1, confidence))
    except:
        confidence = 0

    reasoning = str(decision.get("reasoning", ""))

    return {
        "action": action,
        "amount_grams": amount,
        "confidence": confidence,
        "reasoning": reasoning
    }


def apply_risk_rules(decision: dict, portfolio: dict, current_price: float) -> dict:
    """
    Karar üzerinde risk kurallarını uygular.

    Args:
        decision: AI kararı
        portfolio: Mevcut portföy durumu
        current_price: Mevcut altın fiyatı (TRY/gram)

    Returns:
        dict: Risk kuralları uygulanmış karar
    """
    # Portföy toplam değeri
    total_value = portfolio.get("total_value_try", 0)
    initial_value = portfolio.get("initial_value_try", total_value)

    # Stop-loss kontrolü: Portföy başlangıcın %10'una düştü mü?
    if total_value < initial_value * (1 - config.STOP_LOSS_PCT):
        logger.warning("STOP-LOSS tetiklendi! İşlemler durduruluyor.")
        return {
            "action": "STOP",
            "amount_grams": 0,
            "confidence": 1.0,
            "reasoning": f"Stop-loss: Portföy {config.STOP_LOSS_PCT*100}% düştü"
        }

    # Min confidence kontrolü
    if decision.get("confidence", 0) < config.MIN_CONFIDENCE:
        logger.info(f"Güven {config.MIN_CONFIDENCE*100}% altında, HOLD'a çevrildi")
        decision["action"] = "HOLD"
        decision["reasoning"] += " (Güven düşük olduğu için HOLD)"

    # Max position kontrolü (%5)
    max_position_value = total_value * config.MAX_POSITION_PCT
    max_grams = max_position_value / current_price

    if decision.get("action") == "BUY":
        requested_grams = decision.get("amount_grams", 0)
        if requested_grams > max_grams:
            logger.info(f"İstenen miktar sınırlandı: {requested_grams:.2f} -> {max_grams:.2f} gr")
            decision["amount_grams"] = max_grams
            decision["reasoning"] += f" (Max pozisyon sınırı uygulandı: {max_grams:.2f} gr)"

    # Satış için: Portföyde yeterli altın var mı?
    if decision.get("action") == "SELL":
        gold_grams = portfolio.get("gold_grams", 0)
        requested_sell = decision.get("amount_grams", 0)

        if requested_sell > gold_grams:
            logger.warning(f"Yeterli altın yok, satış sınırlandı: {gold_grams:.2f} gr")
            decision["amount_grams"] = gold_grams
            decision["reasoning"] += " (Mevcut altın miktarına sınırlandı)"

    return decision


if __name__ == "__main__":
    # Test
    test_data = {
        "timestamp": "2025-12-10T14:30:00Z",
        "current_price_usd": 2345.50,
        "current_price_try": 75800,
        "usd_try_rate": 32.3,
        "portfolio": {
            "gold_grams": 87.5,
            "cash_try": 15200,
            "total_value_try": 81550,
            "initial_value_try": 72500,
            "pnl_pct": 12.48
        },
        "indicators": {
            "rsi_14": 58.3,
            "macd_signal_direction": "bullish",
            "bb_position": "mid",
            "ema_50_vs_ema200": "above",
            "price_change_1h_pct": 0.34,
            "price_change_24h_pct": -0.8
        },
        "news_sentiment_score": 0.3,
        "dxy_change_pct": -0.4,
        "session": "london_ny_overlap",
        "days_remaining": 22
    }

    logger.info("AI karar test ediliyor...")
    # Not: Gerçek API anahtarı olmadan çalışmayacak
    # decision = get_ai_decision(test_data)
    # print(decision)