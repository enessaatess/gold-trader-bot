#!/usr/bin/env python3
"""
Altın Trader Bot - Ana Giriş Noktası
"""
import sys
import os

# Loguru yapılandırması
from loguru import logger

# Log dosyası
log_file = os.path.join(os.path.dirname(__file__), "logs", "goldbot.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logger.add(log_file,
           rotation="10 MB",
           retention="7 days",
           level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

# Config ve modüller
import config
from modules import (
    market_hours,
    price_fetcher,
    indicators,
    news_analyzer,
    ai_decision,
    portfolio,
    telegram_bot,
    report_generator
)


def main():
    """
    Ana bot döngüsü.
    """
    logger.info("="*50)
    logger.info("⬡ ALTIN TRADER BOT BAŞLADI ⬡")
    logger.info("="*50)

    # 1. Piyasa saat kontrolü
    if not market_hours.is_market_open():
        logger.info("Piyasa kapalı veya düşük likidite. İşlem yapılmıyor.")
        telegram_bot.send_market_closed_notification()
        return

    current_session = market_hours.get_current_session()
    logger.info(f"Mevcut seans: {current_session}")

    # 2. Fiyat verilerini çek
    logger.info("Fiyat verileri çekiliyor...")
    price_data = price_fetcher.fetch_gold_price()

    if not price_data:
        logger.error("Fiyat alınamadı, çıkılıyor")
        return

    xau_usd = price_data["xau_usd"]
    xau_try = price_data["xau_try"]
    usd_try = price_data["usd_try"]

    logger.info(f"XAU/USD: ${xau_usd} | XAU/TRY: ₺{xau_try} | USD/TRY: {usd_try}")

    # 3. Veritabanı bağlantısı ve portföy durumu
    conn = portfolio.get_db_connection()
    portfolio.initialize_portfolio(conn)

    portfolio_status = portfolio.get_portfolio_status(conn, xau_try)

    # Stop-loss kontrolü
    if report_generator.check_stop_loss(portfolio_status):
        logger.error("STOP-LOSS TETİKLENDİ!")
        final_report = report_generator.get_total_performance(conn)
        telegram_bot.send_stop_loss_notification(final_report)
        portfolio.update_system_status(conn, "status", "stopped")
        return

    # Deney süresi doldu mu?
    if report_generator.is_experiment_finished(conn):
        logger.info("30 günlük deney süresi doldu!")
        final_report = report_generator.get_total_performance(conn)
        telegram_bot.send_stop_loss_notification(final_report)
        portfolio.update_system_status(conn, "status", "finished")
        return

    # Günlük rapor zamanı mı?
    from datetime import datetime
    now = datetime.now()
    if now.hour == config.DAILY_REPORT_HOUR and now.minute < 30:
        # Günlük özet oluştur ve gönder
        report_generator.generate_daily_summary(conn)
        daily_trades = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE date(timestamp) = date('now')"
        ).fetchone()[0]
        telegram_bot.send_daily_report(portfolio_status, daily_trades)

    # 4. Teknik indikatörleri hesapla (varsayılan değerler şimdilik)
    # Gerçek uygulamada historical veri çekilecek
    ind = indicators._default_indicators()
    logger.info(f"İndikatörler: RSI={ind['rsi_14']}, MACD={ind['macd_signal_direction']}")

    # 5. Haber duyarlılık skoru
    logger.info("Haber duyarlılığı analiz ediliyor...")
    news = news_analyzer.fetch_news_sentiment()
    news_score = news.get("score", 0)
    logger.info(f"Haber skoru: {news_score}")

    # DXY etkisi (simüle)
    dxy_change = news_analyzer.get_dxy_impact()

    # 6. AI kararı için verileri hazırla
    market_data = {
        "timestamp": datetime.now().isoformat(),
        "current_price_usd": xau_usd,
        "current_price_try": xau_try,
        "usd_try_rate": usd_try,
        "portfolio": portfolio_status,
        "indicators": ind,
        "news_sentiment_score": news_score,
        "dxy_change_pct": dxy_change,
        "session": current_session,
        "days_remaining": portfolio_status.get("days_remaining", 30)
    }

    # 7. AI'dan karar al
    logger.info("AI kararı bekleniyor...")
    decision = ai_decision.get_ai_decision(market_data)

    if not decision:
        logger.error("AI kararı alınamadı")
        return

    # 8. Risk kurallarını uygula
    decision = ai_decision.apply_risk_rules(
        decision,
        portfolio_status,
        xau_try
    )

    action = decision.get("action", "HOLD")

    logger.info(f"Karar: {action} | Miktar: {decision.get('amount_grams', 0):.4f} gr | Güven: {decision.get('confidence', 0)*100:.0f}%")

    # 9. İşlemi uygula ve bildirim gönder
    if action == "BUY":
        grams = decision.get("amount_grams", 0)
        if grams > 0:
            success = portfolio.execute_trade(
                conn, "BUY", grams, xau_try,
                decision.get("reasoning", ""),
                decision.get("confidence", 0),
                current_session
            )
            if success:
                # Portföyü güncelle
                portfolio_status = portfolio.get_portfolio_status(conn, xau_try)
                telegram_bot.send_trade_notification(
                    "BUY", grams, xau_try,
                    decision.get("reasoning", ""),
                    decision.get("confidence", 0),
                    portfolio_status,
                    current_session
                )

    elif action == "SELL":
        grams = decision.get("amount_grams", 0)
        if grams > 0:
            success = portfolio.execute_trade(
                conn, "SELL", grams, xau_try,
                decision.get("reasoning", ""),
                decision.get("confidence", 0),
                current_session
            )
            if success:
                portfolio_status = portfolio.get_portfolio_status(conn, xau_try)
                telegram_bot.send_trade_notification(
                    "SELL", grams, xau_try,
                    decision.get("reasoning", ""),
                    decision.get("confidence", 0),
                    portfolio_status,
                    current_session
                )

    elif action == "HOLD":
        # Sadece günde bir kez HOLD bildirimi (opsiyonel)
        logger.info(f"HOLD: {decision.get('reasoning', 'Şartlar uygun değil')}")

    # 10. Portföy durumunu logla
    portfolio_status = portfolio.get_portfolio_status(conn, xau_try)
    print(telegram_bot.format_portfolio_display(portfolio_status))

    # Bağlantıyı kapat
    conn.close()

    logger.info("Bot döngüsü tamamlandı.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Beklenmeyen hata: {e}")
        sys.exit(1)