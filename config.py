"""
Altın Trader Bot - Konfigürasyon Dosyası
Tüm sabitler ve ayarlar burada tanımlanır.
"""
import os
from pathlib import Path

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent

# Veritabanı yolu
DB_PATH = PROJECT_ROOT / "data" / "portfolio.db"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# === API KEY'LERI (Environment Variables) ===
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GOLDAPI_KEY = os.environ.get("GOLDAPI_KEY", "")
METALS_API_KEY = os.environ.get("METALS_API_KEY", "")  # Yedek
OPENEXCHANGE_KEY = os.environ.get("OPENEXCHANGE_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# === BAŞLANGIÇ DEĞERLERİ ===
INITIAL_GOLD_GRAMS = float(os.environ.get("INITIAL_GOLD_GRAMS", "100"))
INITIAL_CASH_TRY = float(os.environ.get("INITIAL_CASH_TRY", "0"))

# === RİSK YÖNETİMİ PARAMETRELERİ ===
MAX_POSITION_PCT = float(os.environ.get("MAX_POSITION_PCT", "0.05"))  # Max %5 tek işlem
STOP_LOSS_PCT = float(os.environ.get("STOP_LOSS_PCT", "0.10"))  # %10 düşünce dur
MAX_DAILY_TRADES = int(os.environ.get("MAX_DAILY_TRADES", "8"))
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.55"))  # %55 altı HOLD
COOLDOWN_MINUTES = int(os.environ.get("COOLDOWN_MINUTES", "30"))
POLL_INTERVAL_MINUTES = int(os.environ.get("POLL_INTERVAL_MINUTES", "15"))

# === DENEY SÜRESİ ===
EXPERIMENT_DAYS = 30

# === MARKET HOLIDAYS (ABD + İngiltere) ===
# Dinamik tatiller dışında sabit tarihler
FIXED_HOLIDAYS = [
    "01-01",  # Yılbaşı
    "12-25",  # Noel
    "12-26",  # Boxing Day
    "07-04",  # ABD Bağımsızlık Günü
]

# === LİKİDİTE SAATLERİ (UTC) ===
# Piyasa saatleri
MARKET_OPEN_HOUR = 0   # UTC
MARKET_CLOSE_HOUR = 22  # UTC
LIQUIDITY_OVERLAP_START = 13  # London-NY overlap başlangıcı
LIQUIDITY_OVERLAP_END = 17   # London-NY overlap bitişi
NIGHT_HOUR_START = 22  # Gece düşük likidite başlangıcı
NIGHT_HOUR_END = 0    # Gece bitişi

# === GROQ MODEL AYARLARI ===
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TEMPERATURE = 0.3
GROQ_MAX_TOKENS = 500

# === GÜNLÜK RAPOR SAATİ (UTC) ===
DAILY_REPORT_HOUR = 23
DAILY_REPORT_MINUTE = 0

# === HABER FILTRELEME ===
NEWS_KEYWORDS = ["gold", "XAU", "inflation", "Federal Reserve", "USD", "dinar", "central bank"]
NEWS_LANGUAGE = "en"
NEWS_PAGE_SIZE = 10