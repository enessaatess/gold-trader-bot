"""
Telegram Bildirim Sistemi
İşlem bildirimleri ve günlük raporlar gönderir.
"""
import os
from datetime import datetime
from typing import Optional
from loguru import logger

import config


def send_telegram_message(text: str) -> bool:
    """
    Telegram'a mesaj gönderir.

    Args:
        text: Gönderilecek mesaj

    Returns:
        bool: Başarılı ise True
    """
    token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram ayarları yapılmamış")
        return False

    try:
        import requests

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            logger.info("Telegram mesajı gönderildi")
            return True
        else:
            logger.error(f"Telegram hatası: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Telegram bağlantı hatası: {e}")
        return False


def send_trade_notification(action: str, grams: float, price_try: float,
                             reasoning: str, confidence: float,
                             portfolio: dict, session: str) -> bool:
    """
    Alım/satım bildirimi gönderir.
    """
    emoji = "🟢" if action == "BUY" else "🔴"
    action_text = "ALIM YAPILDI" if action == "BUY" else "SATIM YAPILDI"

    total = grams * price_try

    message = f"""
{emoji} *{action_text}*
━━━━━━━━━━━━━━━━━━━━━━━━
📦 Miktar  : {grams:.4f} gr altın
💰 Fiyat   : ₺{price_try:,.2f} / gr
💸 Toplam  : ₺{total:,.2f}
📊 Seans   : {session}

🧠 AI Gerekçesi:
{reasoning}
Güven: %{confidence*100:.0f}

💼 YENİ KASA:
Altın: {portfolio.get('gold_grams', 0):.2f} gr | Nakit: ₺{portfolio.get('cash_try', 0):,.0f}
Toplam: ₺{portfolio.get('total_value_try', 0):,.0f} (%{portfolio.get('pnl_pct', 0):+.2f})
Kalan: {portfolio.get('days_remaining', 0)} gün

🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def send_hold_notification(reasoning: str, portfolio: dict) -> bool:
    """
    HOLD kararı bildirimi gönderir (opsiyonel, günde max 1).
    """
    message = f"""
🟡 *HOLD - BEKLEMEDE*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Durum: İşlem yapılmadı

🧠 Neden:
{reasoning}

💼 MEVCUT KASA:
Altın: {portfolio.get('gold_grams', 0):.2f} gr | Nakit: ₺{portfolio.get('cash_try', 0):,.0f}
Toplam: ₺{portfolio.get('total_value_try', 0):,.0f} (%{portfolio.get('pnl_pct', 0):+.2f})

🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def send_market_closed_notification() -> bool:
    """
    Piyasa kapalı bildirimi gönderir.
    """
    message = f"""
🔴 *PİYASA KAPALI*
━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Pazar günü piyasa kapalı.
Bot beklemeye alındı.

💼 Mevcut portföy değeri korunuyor.
Bir sonraki çalışmada tekrar kontrol edilecek.

🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def send_daily_report(portfolio: dict, trades_count: int, daily_pnl: float = 0) -> bool:
    """
    Günlük rapor gönderir.
    """
    emoji = "📈" if daily_pnl >= 0 else "📉"

    message = f"""
📊 *GÜNLÜK RAPOR*
━━━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d %B %Y')}

💰 *Genel Performans:*
• Toplam: ₺{portfolio.get('total_value_try', 0):,.0f}
• Kar/Zarar: %{portfolio.get('pnl_pct', 0):+.2f}
• Kalan Gün: {portfolio.get('days_remaining', 0)}

📊 *Bugünkü İşlemler:*
• İşlem sayısı: {trades_count}
• Günlük PnL: %{daily_pnl:+.2f}

💼 *Portföy:*
• Altın: {portfolio.get('gold_grams', 0):.2f} gr
• Nakit: ₺{portfolio.get('cash_try', 0):,.0f}

🕐 Rapor saati: {datetime.now().strftime('%H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def send_alarm_notification(message_text: str, portfolio: dict) -> bool:
    """
    Alarm bildirimi gönderir (portföy %20 düşünce vb).
    """
    message = f"""
🚨 *ALARM!*
━━━━━━━━━━━━━━━━━━━━━━━━
{message_text}

💼 Portföy: ₺{portfolio.get('total_value_try', 0):,.0f} (%{portfolio.get('pnl_pct', 0):+.2f})

🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def send_stop_loss_notification(final_report: dict) -> bool:
    """
    Stop-loss sonrası final rapor gönderir.
    """
    message = f"""
🛑 *FİŞ ÇEKİLDİ - BOT DURDURULDU*
━━━━━━━━━━━━━━━━━━━━━━━━
Portföy başlangıcın %{config.STOP_LOSS_PCT*100}'ine düştü.

📊 *FINAL RAPOR:*
• Başlangıç: ₺{final_report.get('initial_value', 0):,.0f}
• Final: ₺{final_report.get('final_value', 0):,.0f}
• Toplam PnL: %{final_report.get('total_pnl', 0):+.2f}
• Toplam İşlem: {final_report.get('total_trades', 0)}

Bot 30 gün dolana kadar bekletilebilir
veya manuel olarak yeniden başlatılabilir.

🕐 {datetime.now().strftime('%d %b %Y, %H:%M')} UTC
"""

    return send_telegram_message(message.strip())


def format_portfolio_display(portfolio: dict) -> str:
    """
    Portföyü terminal için güzel bir formatta gösterir.
    """
    return f"""
╔══════════════════════════════════════╗
║      ⬡ ALTIN TRADER BOT — KASA ⬡   ║
╠══════════════════════════════════════╣
║  🥇 Altın    :  {portfolio.get('gold_grams', 0):.2f} gr            ║
║  💵 Nakit    :  ₺{portfolio.get('cash_try', 0):,.0f}             ║
║  📊 Toplam   :  ₺{portfolio.get('total_value_try', 0):,.0f}            ║
║  📈 Kar/Zarar:  %{portfolio.get('pnl_pct', 0):+.2f}             ║
║  📅 Gün      :  {portfolio.get('days_elapsed', 0)} / {config.EXPERIMENT_DAYS}             ║
╚══════════════════════════════════════╝
"""


if __name__ == "__main__":
    # Test
    logger.info("Telegram test mesajı gönderiliyor...")

    test_portfolio = {
        "gold_grams": 87.5,
        "cash_try": 15200,
        "total_value_try": 81550,
        "pnl_pct": 12.48,
        "days_remaining": 22
    }

    # Gerçek token olmadan çalışmayacak
    # send_trade_notification("BUY", 10.0, 78500, "Test işlemi", 0.75, test_portfolio, "london_ny_overlap")