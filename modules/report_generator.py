"""
Rapor Üretici
Günlük ve özet raporlar oluşturur.
"""
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

import config
from modules import portfolio as portfolio_module


def generate_daily_summary(conn, date: str = None) -> dict:
    """
    Belirli bir günün özetini oluşturur.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    cursor = conn.cursor()

    # Günün ilk ve son snapshot'ını al
    cursor.execute("""
        SELECT * FROM portfolio_snapshots
        WHERE date(timestamp) = date(?)
        ORDER BY timestamp ASC
        LIMIT 1
    """, (date,))
    start_snapshot = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM portfolio_snapshots
        WHERE date(timestamp) = date(?)
        ORDER BY timestamp DESC
        LIMIT 1
    """, (date,))
    end_snapshot = cursor.fetchone()

    if not start_snapshot or not end_snapshot:
        return {}

    # Günün işlemlerini say
    cursor.execute("""
        SELECT COUNT(*) as count FROM transactions
        WHERE date(timestamp) = date(?)
    """, (date,))
    trades_count = cursor.fetchone()["count"]

    # Fiyat aralığı
    cursor.execute("""
        SELECT MIN(gold_price_try) as low, MAX(gold_price_try) as high
        FROM portfolio_snapshots
        WHERE date(timestamp) = date(?)
    """, (date,))
    price_range = cursor.fetchone()

    start_value = start_snapshot["total_value_try"] if start_snapshot else 0
    end_value = end_snapshot["total_value_try"] if end_snapshot else 0

    daily_pnl = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0

    summary = {
        "date": date,
        "start_value_try": start_value,
        "end_value_try": end_value,
        "daily_pnl_pct": round(daily_pnl, 2),
        "trades_count": trades_count,
        "gold_grams_eod": end_snapshot["gold_grams"] if end_snapshot else 0,
        "cash_try_eod": end_snapshot["cash_try"] if end_snapshot else 0,
        "high_price_try": price_range["high"] if price_range else 0,
        "low_price_try": price_range["low"] if price_range else 0,
    }

    # Veritabanına kaydet
    cursor.execute("""
        INSERT OR REPLACE INTO daily_summary
        (date, start_value_try, end_value_try, daily_pnl_pct, trades_count,
         gold_grams_eod, cash_try_eod, high_price_try, low_price_try)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (summary["date"], summary["start_value_try"], summary["end_value_try"],
          summary["daily_pnl_pct"], summary["trades_count"],
          summary["gold_grams_eod"], summary["cash_try_eod"],
          summary["high_price_try"], summary["low_price_try"]))

    conn.commit()

    return summary


def get_weekly_performance(conn) -> dict:
    """
    Haftalık performans özetini döndürür.
    """
    cursor = conn.cursor()

    # Son 7 gün
    cursor.execute("""
        SELECT * FROM daily_summary
        WHERE date >= date('now', '-7 days')
        ORDER BY date DESC
    """)

    days = cursor.fetchall()

    if not days:
        return {"weekly_pnl": 0, "total_trades": 0, "days": []}

    total_pnl = sum(day["daily_pnl_pct"] for day in days)
    total_trades = sum(day["trades_count"] for day in days)

    return {
        "weekly_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "days": [dict(d) for d in days]
    }


def get_total_performance(conn) -> dict:
    """
    Tüm zamanların performansını döndürür.
    """
    cursor = conn.cursor()

    # Toplam işlem sayısı
    cursor.execute("SELECT COUNT(*) as count FROM transactions")
    total_trades = cursor.fetchone()["count"]

    # Toplam alım ve satım
    cursor.execute("""
        SELECT action, SUM(grams) as total_grams, SUM(total_try) as total_try
        FROM transactions
        GROUP BY action
    """)
    trade_summary = {row["action"]: row for row in cursor.fetchall()}

    # Mevcut portföy
    status = portfolio_module.get_system_status(conn)

    initial_value = float(status.get("initial_value_try", 0))
    current_gold = float(status.get("current_gold_grams", 0))
    current_cash = float(status.get("current_cash_try", 0))

    # Son fiyatı tahmin et (veya varsayılan)
    cursor.execute("""
        SELECT gold_price_try FROM portfolio_snapshots
        ORDER BY timestamp DESC LIMIT 1
    """)
    last_price_row = cursor.fetchone()
    last_price = last_price_row["gold_price_try"] if last_price_row else 80000

    current_value = (current_gold * last_price) + current_cash

    total_pnl = ((current_value - initial_value) / initial_value * 100) if initial_value > 0 else 0

    return {
        "initial_value_try": initial_value,
        "current_value_try": current_value,
        "total_pnl_pct": round(total_pnl, 2),
        "total_trades": total_trades,
        "total_bought_grams": trade_summary.get("BUY", {}).get("total_grams", 0),
        "total_sold_grams": trade_summary.get("SELL", {}).get("total_grams", 0),
        "current_gold_grams": current_gold,
        "current_cash_try": current_cash
    }


def check_stop_loss(portfolio: dict) -> bool:
    """
    Stop-loss durumunu kontrol eder.
    """
    initial = portfolio.get("initial_value_try", 0)
    current = portfolio.get("total_value_try", 0)

    if initial <= 0:
        return False

    threshold = initial * (1 - config.STOP_LOSS_PCT)

    return current < threshold


def is_experiment_finished(conn) -> bool:
    """
    30 günlük deney süresinin dolup dolmadığını kontrol eder.
    """
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM system_state WHERE key = 'start_date'")
    row = cursor.fetchone()

    if not row:
        return False

    try:
        start_date = datetime.fromisoformat(row["value"])
        days_elapsed = (datetime.now() - start_date).days

        return days_elapsed >= config.EXPERIMENT_DAYS
    except:
        return False


if __name__ == "__main__":
    # Test
    conn = portfolio_module.get_db_connection()
    summary = generate_daily_summary(conn)
    print(f"Günlük özet: {summary}")