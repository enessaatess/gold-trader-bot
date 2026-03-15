"""
Haber Analizörü
NewsAPI'den altın/dolar/enflasyon haberlerini çeker ve duyarlılık skoru üretir.
"""
import requests
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

import config


def fetch_news_sentiment() -> dict:
    """
    Altın ve dolar hakkında son haberleri çeker ve duyarlılık skorunu hesaplar.

    Returns:
        dict: {"score": float, "headlines": list, "source": str}
    """
    api_key = config.NEWS_API_KEY
    if not api_key:
        logger.warning("NEWS_API_KEY ayarlanmamış")
        return {"score": 0.0, "headlines": [], "source": "disabled"}

    keywords = " OR ".join(config.NEWS_KEYWORDS)

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": keywords,
            "language": config.NEWS_LANGUAGE,
            "sortBy": "publishedAt",
            "pageSize": config.NEWS_PAGE_SIZE,
            "apiKey": api_key
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                return {"score": 0.0, "headlines": [], "source": "newsapi"}

            # Duyarlılık analizi
            score = _analyze_sentiment(articles)
            headlines = [a.get("title", "")[:80] for a in articles[:5]]

            logger.info(f"Haber duyarlılık skoru: {score}")

            return {
                "score": round(score, 2),
                "headlines": headlines,
                "source": "newsapi",
                "article_count": len(articles)
            }

        elif response.status_code == 429:
            logger.warning("NewsAPI rate limit aşıldı")
            return {"score": 0.0, "headlines": [], "source": "rate_limited"}

        else:
            logger.error(f"NewsAPI hatası: {response.status_code}")
            return {"score": 0.0, "headlines": [], "source": "error"}

    except Exception as e:
        logger.error(f"NewsAPI bağlantı hatası: {e}")
        return {"score": 0.0, "headlines": [], "source": "error"}


def _analyze_sentiment(articles: list) -> float:
    """
    Haber başlıklarından duyarlılık skorunu hesaplar.
    -1 (çok negatif) ile +1 (çok pozitif) arasında değer döndürür.
    """
    # Pozitif ve negatif kelimeler
    positive_words = [
        "rise", "rising", "gain", "gains", "bullish", "surge", "surged",
        "soar", "soared", "high", "higher", "positive", "growth",
        "optimistic", "strong", "strength", "boom", "breakthrough",
        "invest", "investment", "profit", "profits"
    ]

    negative_words = [
        "fall", "falling", "drop", "dropped", "bearish", "crash", "crashed",
        "decline", "declining", "low", "lower", "negative", "recession",
        "fear", "risk", "danger", "warning", "sell", "selling",
        "loss", "losses", "bear", "bears", "plunge", "plunged"
    ]

    positive_words_tr = [
        "yükseliş", "kazanç", "pozitif", "büyüme", "yatırım", "kar"
    ]

    negative_words_tr = [
        "düşüş", "kayıp", "negatif", "risk", "kriz", "endişe"
    ]

    total_score = 0

    for article in articles:
        title = (article.get("title", "") + " " + article.get("description", "")).lower()

        # Pozitif kelime say
        pos_count = sum(1 for word in positive_words if word in title)
        pos_count += sum(1 for word in positive_words_tr if word in title)

        # Negatif kelime say
        neg_count = sum(1 for word in negative_words if word in title)
        neg_count += sum(1 for word in negative_words_tr if word in title)

        # Makale skoru
        if pos_count > neg_count:
            total_score += 0.2
        elif neg_count > pos_count:
            total_score -= 0.2

    # Normalize et (-1 ile +1 arasına)
    # Her haber max ±0.2 katkı sağlar, 5 haber max ±1.0
    normalized = max(-1.0, min(1.0, total_score))

    return normalized


def get_dxy_impact() -> float:
    """
    DXY (Dolar Endeksi) değişim etkisini simüle eder.
    Gerçek uygulamada ayrı bir API kullanılabilir.
    Şimdilik rastgele küçük bir değer döndürür.
    """
    import random
    # -0.5% ile +0.5% arasında rastgele
    dxy_change = random.uniform(-0.5, 0.5)
    return round(dxy_change, 2)


if __name__ == "__main__":
    # Test
    logger.info("Haber duyarlılık test ediliyor...")
    result = fetch_news_sentiment()
    print(f"Sonuç: {result}")