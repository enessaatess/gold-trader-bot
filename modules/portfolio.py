"""
Sanal Kasa & Portföy Yönetimi
SQLite veritabanında portföy durumunu takip eder.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

import config


def get_db_connection():
    """SQLite veritabanı bağlantısı oluşturur."""
    # Dizini oluştur
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row

    # Tabloları oluştur
    init_database(conn)

    return conn


def init_database(conn):
    """Veritabanı tablolarını oluşturur."""
    cursor = conn.cursor()

    # Portföy anlık durum
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            gold_grams REAL NOT NULL,
            cash_try REAL NOT NULL,
            gold_price_try REAL NOT NULL,
            total_value_try REAL NOT NULL,
            pnl_pct REAL NOT NULL
        )
    """)

    # İşlem geçmişi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            grams REAL NOT NULL,
            price_try REAL NOT NULL,
            total_try REAL NOT NULL,
            reasoning TEXT,
            confidence REAL,
            session TEXT
        )
    """)

    # Günlük özet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            start_value_try REAL,
            end_value_try REAL,
            daily_pnl_pct REAL,
            trades_count INTEGER,
            gold_grams_eod REAL,
            cash_try_eod REAL,
            high_price_try REAL,
            low_price_try REAL
        )
    """)

    # Sistem durumu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()


def initialize_portfolio(conn) -> dict:
    """
    Portföyü başlatır veya mevcut durumu döndürür.
    """
    cursor = conn.cursor()

    # Sistem durumunu kontrol et
    cursor.execute("SELECT value FROM system_state WHERE key = 'status'")
    status_row = cursor.fetchone()

    if status_row is None:
        # İlk çalışma - portföyü başlat
        logger.info("Portföy başlatılıyor...")

        # Başlangıç değerini hesapla
        # GoldAPI'den fiyat alınırsa güncellenecek, şimdilik varsayılan
        initial_price_try = 80000  # Yaklaşık 2500 USD * 32

        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('status', 'running')
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('start_date', datetime('now'))
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('initial_gold_grams', ?
        )""", (config.INITIAL_GOLD_GRAMS,))
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('initial_cash_try', ?
        )""", (config.INITIAL_CASH_TRY,))
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('initial_price_try', ?
        )""", (initial_price_try,))

        initial_value = (config.INITIAL_GOLD_GRAMS * initial_price_try) + config.INITIAL_CASH_TRY
        cursor.execute("""
            INSERT OR REPLACE INTO system_state (key, value)
            VALUES ('initial_value_try', ?)
        """, (initial_value,))

        conn.commit()

    # Mevcut portföy durumunu getir
    cursor.execute("SELECT value FROM system_state WHERE key = 'current_gold_grams'")
    gold_row = cursor.fetchone()
    current_gold = float(gold_row["value"]) if gold_row else config.INITIAL_GOLD_GRAMS

    cursor.execute("SELECT value FROM system_state WHERE key = 'current_cash_try'")
    cash_row = cursor.fetchone()
    current_cash = float(cash_row["value"]) if cash_row else config.INITIAL_CASH_TRY

    cursor.execute("SELECT value FROM system_state WHERE key = 'initial_value_try'")
    init_row = cursor.fetchone()
    initial_value = float(init_row["value"]) if init_row else 0

    return {
        "gold_grams": current_gold,
        "cash_try": current_cash,
        "initial_value_try": initial_value
    }


def get_portfolio_status(conn, current_price_try: float) -> dict:
    """
    Portföyün anlık durumunu döndürür.
    """
    cursor = conn.cursor()

    # Mevcut altın ve nakit
    cursor.execute("SELECT value FROM system_state WHERE key = 'current_gold_grams'")
    gold_row = cursor.fetchone()
    gold_grams = float(gold_row["value"]) if gold_row else config.INITIAL_GOLD_GRAMS

    cursor.execute("SELECT value FROM system_state WHERE key = 'current_cash_try'")
    cash_row = cursor.fetchone()
    cash_try = float(cash_row["value"]) if cash_row else config.INITIAL_CASH_TRY

    cursor.execute("SELECT value FROM system_state WHERE key = 'initial_value_try'")
    init_row = cursor.fetchone()
    initial_value = float(init_row["value"]) if init_row else 0

    # Toplam değer
    gold_value = gold_grams * current_price_try
    total_value = gold_value + cash_try

    # Kar/zarar
    pnl_pct = ((total_value - initial_value) / initial_value * 100) if initial_value > 0 else 0

    # Gün sayısı
    cursor.execute("SELECT value FROM system_state WHERE key = 'start_date'")
    start_row = cursor.fetchone()
    start_date = start_row["value"] if start_row else datetime.now().isoformat()

    try:
        start = datetime.fromisoformat(start_date)
        days_elapsed = (datetime.now() - start).days
    except:
        days_elapsed = 0

    days_remaining = config.EXPERIMENT_DAYS - days_elapsed

    # Snapshot kaydet
    cursor.execute("""
        INSERT INTO portfolio_snapshots
        (timestamp, gold_grams, cash_try, gold_price_try, total_value_try, pnl_pct)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), gold_grams, cash_try, current_price_try, total_value, pnl_pct))

    conn.commit()

    return {
        "gold_grams": round(gold_grams, 4),
        "cash_try": round(cash_try, 2),
        "gold_value_try": round(gold_value, 2),
        "total_value_try": round(total_value, 2),
        "initial_value_try": round(initial_value, 2),
        "pnl_pct": round(pnl_pct, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": max(0, days_remaining)
    }


def execute_trade(conn, action: str, grams: float, price_try: float,
                  reasoning: str = "", confidence: float = 0, session: str = "") -> bool:
    """
    İşlemi uygular ve veritabanına kaydeder.
    """
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()
    total_try = grams * price_try

    # Mevcut değerleri al
    cursor.execute("SELECT value FROM system_state WHERE key = 'current_gold_grams'")
    gold_row = cursor.fetchone()
    current_gold = float(gold_row["value"]) if gold_row else config.INITIAL_GOLD_GRAMS

    cursor.execute("SELECT value FROM system_state WHERE key = 'current_cash_try'")
    cash_row = cursor.fetchone()
    current_cash = float(cash_row["value"]) if cash_row else config.INITIAL_CASH_TRY

    if action == "BUY":
        # Altın al (nakit azalır)
        if current_cash < total_try:
            logger.warning(f"Yetersiz nakit! Gerekli: {total_try:.2f}, Mevcut: {current_cash:.2f}")
            return False

        current_gold += grams
        current_cash -= total_try
        logger.info(f"ALIM: {grams:.4f} gr @ {price_try:.2f} = {total_try:.2f} TL")

    elif action == "SELL":
        # Altın sat (nakit artar)
        if current_gold < grams:
            logger.warning(f"Yetersiz altın! Gerekli: {grams:.4f}, Mevcut: {current_gold:.4f}")
            return False

        current_gold -= grams
        current_cash += total_try
        logger.info(f"SATIM: {grams:.4f} gr @ {price_try:.2f} = {total_try:.2f} TL")

    else:
        logger.warning(f"Geçersiz işlem: {action}")
        return False

    # Güncelle
    cursor.execute("""
        INSERT OR REPLACE INTO system_state (key, value)
        VALUES ('current_gold_grams', ?)
    """, (current_gold,))

    cursor.execute("""
        INSERT OR REPLACE INTO system_state (key, value)
        VALUES ('current_cash_try', ?)
    """, (current_cash,))

    # İşlem geçmişine kaydet
    cursor.execute("""
        INSERT INTO transactions
        (timestamp, action, grams, price_try, total_try, reasoning, confidence, session)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, action, grams, price_try, total_try, reasoning, confidence, session))

    conn.commit()
    return True


def get_recent_trades(conn, limit: int = 10) -> list:
    """Son işlemleri getirir."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    return [dict(row) for row in cursor.fetchall()]


def get_system_status(conn) -> dict:
    """Sistem durumunu getirir."""
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM system_state")
    rows = cursor.fetchall()

    status = {}
    for row in rows:
        key = row["key"]
        value = row["value"]

        # Sayısal değerlere çevir
        try:
            if "." in value:
                value = float(value)
            else:
                value = int(value)
        except:
            pass

        status[key] = value

    return status


def update_system_status(conn, key: str, value: str):
    """Sistem durumunu günceller."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO system_state (key, value)
        VALUES (?, ?)
    """, (key, str(value)))
    conn.commit()


def get_daily_stats(conn, date: str = None) -> dict:
    """Belirli bir günün istatistiklerini getirir."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_summary WHERE date = ?", (date,))
    row = cursor.fetchone()

    return dict(row) if row else {}


if __name__ == "__main__":
    # Test
    conn = get_db_connection()
    portfolio = initialize_portfolio(conn)
    print(f"Başlangıç portföy: {portfolio}")

    status = get_portfolio_status(conn, 80000)
    print(f"Portföy durumu: {status}")