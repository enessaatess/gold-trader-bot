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


def _send_market_closed_if_needed():
    """
    Piyasa kapalı bildirimini spam'ı önlemek için sadece 3 saatte bir gönderir.
    Bir dosyaya son gönderim zamanını kaydederek kontrol eder.
    """
    import json
    from datetime import datetime

    state_file = os.path.join(os.path.dirname(__file__), "logs", "market_closed_state.json")
    cooldown_hours = 3

    try:
        # Son gönderim zamanını kontrol et
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
            last_sent = datetime.fromisoformat(state.get('last_sent', '2020-01-01T00:00:00'))
            hours_since = (datetime.now() - last_sent).total_seconds() / 3600
            if hours_since < cooldown_hours:
                logger.info(f"Piyasa kapalı bildirimi {cooldown_hours - hours_since:.1f} saat sonra gönderilecek")
                return
    except Exception:
        pass

    # Bildirimi gönder ve zamanı kaydet
    telegram_bot.send_market_closed_notification()
    try:
        with open(state_file, 'w') as f:
            json.dump({'last_sent': datetime.now().isoformat()}, f)
    except Exception:
        pass


def main():
    """
    Ana bot döngüsü.
    """
    from datetime import datetime

    # Adım adım bildirim için başlangıç zamanı
    step_start = datetime.now()
    steps_completed = []

    def log_step(step_name: str):
        """Her adımı logla ve listeye ekle"""
        elapsed = (datetime.now() - step_start).total_seconds()
        logger.info(f"[{elapsed:.1f}s] {step_name}")
        steps_completed.append(f"✓ {step_name}")

    logger.info("="*50)
    logger.info("⬡ ALTIN TRADER BOT BAŞLADI ⬡")
    logger.info("="*50)

    # 1. Piyasa saat kontrolü
    log_step("Piyasa saati kontrol ediliyor...")
    market_info = market_hours.get_market_hours_info()
    is_open = market_info["is_open"]

    if not is_open:
        log_step("Piyasa KAPALI - İşlem yapılmıyor")
        logger.info(f"  └─ Sebep: {market_info['session']} (UTC {market_info['hour_utc']}:00)")
        _send_market_closed_if_needed()
        return

    log_step(f"Piyasa AÇIK ({market_info['session']})")

    current_session = market_hours.get_current_session()
    logger.info(f"Mevcut seans: {current_session}")

    # 2. Fiyat verilerini çek
    log_step("Fiyat verileri çekiliyor...")
    price_data = price_fetcher.fetch_gold_price()

    if not price_data:
        log_step("HATA: Fiyat alınamadı!")
        return

    log_step("Fiyat verileri alındı")

    xau_usd = price_data["xau_usd"]
    xau_try = price_data["xau_try"]
    usd_try = price_data["usd_try"]

    logger.info(f"XAU/USD: ${xau_usd} | XAU/TRY: ₺{xau_try} | USD/TRY: {usd_try}")

    # 3. Veritabanı bağlantısı ve portföy durumu
    log_step("Veritabanı bağlantısı...")
    conn = portfolio.get_db_connection()
    portfolio.initialize_portfolio(conn)
    portfolio_status = portfolio.get_portfolio_status(conn, xau_try)

    log_step("Portföy durumu okundu")

    # Stop-loss kontrolü
    if report_generator.check_stop_loss(portfolio_status):
        log_step("STOP-LOSS TETİKLENDİ!")
        final_report = report_generator.get_total_performance(conn)
        telegram_bot.send_stop_loss_notification(final_report)
        portfolio.update_system_status(conn, "status", "stopped")
        conn.close()
        return

    # Deney süresi doldu mu?
    if report_generator.is_experiment_finished(conn):
        log_step("30 günlük deney süresi doldu!")
        final_report = report_generator.get_total_performance(conn)
        telegram_bot.send_stop_loss_notification(final_report)
        portfolio.update_system_status(conn, "status", "finished")
        conn.close()
        return

    # Günlük rapor zamanı mı?
    now = datetime.now()
    if now.hour == config.DAILY_REPORT_HOUR and now.minute < 30:
        log_step("Günlük rapor oluşturuluyor...")
        report_generator.generate_daily_summary(conn)
        daily_trades = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE date(timestamp) = date('now')"
        ).fetchone()[0]
        telegram_bot.send_daily_report(portfolio_status, daily_trades)

    # 4. Teknik indikatörleri hesapla
    log_step("Teknik indikatörler hesaplanıyor...")
    ind = indicators._default_indicators()
    log_step(f"İndikatörler: RSI={ind['rsi_14']}, MACD={ind['macd_signal_direction']}")

    # 5. Haber duyarlılık skoru
    log_step("Haber analizi yapılıyor...")
    news = news_analyzer.fetch_news_sentiment()
    news_score = news.get("score", 0)
    dxy_change = news_analyzer.get_dxy_impact()
    log_step(f"Haber skoru: {news_score}, DXY: {dxy_change:+.2f}%")

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
    log_step("AI kararı bekleniyor...")
    decision = ai_decision.get_ai_decision(market_data)

    if not decision:
        log_step("HATA: AI kararı alınamadı!")
        return

    log_step("AI kararı alındı")

    # 8. Risk kurallarını uygula
    decision = ai_decision.apply_risk_rules(
        decision,
        portfolio_status,
        xau_try
    )

    action = decision.get("action", "HOLD")
    log_step(f"KARAR: {action}")

    # 9. İşlemi uygula ve bildirim gönder
    trade_made = False

    if action == "BUY":
        grams = decision.get("amount_grams", 0)
        if grams > 0:
            log_step(f"İŞLEM: ALIM {grams:.4f} gr")
            success = portfolio.execute_trade(
                conn, "BUY", grams, xau_try,
                decision.get("reasoning", ""),
                decision.get("confidence", 0),
                current_session
            )
            if success:
                trade_made = True
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
            log_step(f"İŞLEM: SATIM {grams:.4f} gr")
            success = portfolio.execute_trade(
                conn, "SELL", grams, xau_try,
                decision.get("reasoning", ""),
                decision.get("confidence", 0),
                current_session
            )
            if success:
                trade_made = True
                portfolio_status = portfolio.get_portfolio_status(conn, xau_try)
                telegram_bot.send_trade_notification(
                    "SELL", grams, xau_try,
                    decision.get("reasoning", ""),
                    decision.get("confidence", 0),
                    portfolio_status,
                    current_session
                )

    elif action == "HOLD":
        log_step(f"HOLD: {decision.get('reasoning', 'Şartlar uygun değil')[:100]}...")

    # 10. Portföy durumunu logla
    portfolio_status = portfolio.get_portfolio_status(conn, xau_try)
    print(telegram_bot.format_portfolio_display(portfolio_status))

    # 11. Adım adım özet gönder (sadece piyasa açıkken)
    total_elapsed = (datetime.now() - step_start).total_seconds()
    steps_text = "\n".join(steps_completed)

    summary = f"""
🔄 *BOT ÇALIŞTI - ÖZET*
━━━━━━━━━━━━━━━━━━━━━━
⏱️ Süre: {total_elapsed:.1f} saniye

📊 *Adımlar:*
{steps_text}

📈 *Fiyatlar:*
• XAU/USD: ${xau_usd}
• XAU/TRY: ₺{xau_try}
• USD/TRY: ₺{usd_try}

💼 *Portföy:*
• Altın: {portfolio_status.get('gold_grams', 0):.2f} gr
• Nakit: ₺{portfolio_status.get('cash_try', 0):,.0f}
• Toplam: ₺{portfolio_status.get('total_value_try', 0):,.0f} ({portfolio_status.get('pnl_pct', 0):+.2f}%)

🎯 *Karar:* {action}
🕐 {datetime.now().strftime('%d %b %H:%M')} TR
"""

    telegram_bot.send_telegram_message(summary.strip())

    # Bağlantıyı kapat
    conn.close()

    logger.info("Bot döngüsü tamamlandı.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Beklenmeyen hata: {e}")
        sys.exit(1)