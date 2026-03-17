# ⬡ ALTIN TRADER BOT — Teknik Dokümantasyon v1.2

> ⚠️ **Bu sistem tamamen sanal bir deneydir. Gerçek para veya gerçek altın içermez. Yalnızca eğitim ve deney amaçlıdır.**

---

## İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Sistem Mimarisi](#2-sistem-mimarisi)
3. [Sunucu — GitHub Actions](#3-sunucu--github-actions)
4. [AI Motoru — Groq API](#4-ai-motoru--groq-api)
5. [Veri Kaynakları & API'lar](#5-veri-kaynakları--apılar)
6. [Altın Piyasası Saatleri & İşlem Kuralları](#6-altın-piyasası-saatleri--işlem-kuralları)
7. [AI Karar Motoru — Prompt & Mantık](#7-ai-karar-motoru--prompt--mantık)
8. [Sanal Kasa & Portföy Takibi](#8-sanal-kasa--portföy-takibi)
9. [Telegram Bildirim Sistemi](#9-telegram-bildirim-sistemi)
10. [Başlatma / Durdurma / Bekletme](#10-başlatma--durdurma--bekletme)
11. [Proje Dosya Yapısı](#11-proje-dosya-yapısı)
12. [Ortam Değişkenleri (.env / GitHub Secrets)](#12-ortam-değişkenleri-env--github-secrets)
13. [Python Bağımlılıkları](#13-python-bağımlılıkları)
14. [GitHub Actions Workflow Dosyası](#14-github-actions-workflow-dosyası)
15. [Maliyet Analizi](#15-maliyet-analizi)
16. [Geliştirme Yol Haritası](#16-geliştirme-yol-haritası)
17. [Kurulum Rehberi — Adım Adım](#17-kurulum-rehberi--adım-adım)

---

## 1. Proje Özeti

Altın Trader Bot; gerçek piyasa verilerine dayalı, tamamen sanal bir altın portföyünü yöneten, yapay zeka destekli otomatik alım-satım deneyidir. Sistem, kullanıcı tarafından belirlenen miktarda sanal altınla başlar, canlı spot fiyatlarını takip eder ve profesyonel bir altın traderının kullandığı tekniklerle işlem kararları üretir. Borsalar kapalı olduğunda (hafta sonu, resmi tatiller) kesinlikle işlem yapmaz.

| Parametre | Değer |
|-----------|-------|
| Deney Süresi | 30 gün |
| Başlangıç Portföyü | Kullanıcı tarafından belirlenir (ör: 100 gr sanal altın) |
| Piyasa Verisi | Gerçek zamanlı — ücretsiz API'lar |
| AI Motoru | **Groq API — llama-3.1-8b-instant (ücretsiz)** |
| Sunucu | **GitHub Actions (public repo = tamamen ücretsiz)** |
| Bildirim Kanalı | Telegram Bot |
| İşlem Yasağı | Hafta sonu + ABD & İngiltere resmi tatilleri |
| Fis Çekme Koşulu | Portföy değeri başlangıcın %10'una düşerse |

---

## 2. Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS                           │
│         Cron: Her 15 dakikada bir (Pazartesi-Cuma)         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │price_fetcher│  │ indicators  │  │  news_analyzer   │   │
│  │ GoldAPI.io  │  │ RSI/MACD/BB │  │   NewsAPI.org    │   │
│  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘   │
│         └────────────────┼──────────────────┘             │
│                          ▼                                  │
│               ┌──────────────────┐                         │
│               │  market_hours.py │                         │
│               │ Piyasa açık mı?  │                         │
│               └────────┬─────────┘                         │
│                   ✅ Açık │ ❌ Kapalı → Çalışma durdur     │
│                          ▼                                  │
│               ┌──────────────────┐                         │
│               │  ai_decision.py  │                         │
│               │   Groq API       │                         │
│               │ llama-3.1-8b     │                         │
│               └────────┬─────────┘                         │
│                        ▼                                    │
│          ┌──────────────────────────────┐                  │
│          │         portfolio.py         │                  │
│          │  BUY / SELL / HOLD → SQLite  │                  │
│          └──────────────┬───────────────┘                  │
│                         ▼                                   │
│              ┌───────────────────┐                         │
│              │  telegram_bot.py  │                         │
│              │  İşlem bildirimi  │                         │
│              └───────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

**Veri akışı (her çalışmada):**

1. Piyasa saati kontrolü → kapalıysa çıkış
2. Spot fiyat + döviz kuru çek
3. Teknik indikatörleri hesapla
4. Haber duyarlılık skorunu al
5. Groq API'ye tüm veriyi gönder → BUY/SELL/HOLD kararı al
6. Kararı uygula, SQLite'a kaydet
7. Telegram bildirimi gönder

---

## 3. Sunucu — GitHub Actions

### Neden GitHub Actions?

| Özellik | Detay |
|---------|-------|
| Maliyet | **Public repo'da tamamen ücretsiz, süresiz** |
| Cron desteği | Her 5 dakikaya kadar ayarlanabilir |
| Güvenilirlik | %99.9+ uptime (GitHub altyapısı) |
| Kurulum | Sadece `.yml` dosyası yazmak yeterli |
| Secret yönetimi | API key'ler GitHub Secrets'ta güvenli saklanır |
| Log görüntüleme | GitHub web arayüzünden her çalışma izlenebilir |

### Önemli Notlar

- **Public repo kullanılmalı** → private repoda ayda 2.000 dakika limiti var, public'te sınırsız
- Cron'un minimum aralığı 5 dakikadır; bu proje 15 dakika kullanır
- GitHub, yoğun saatlerde cron tetiklemelerini 1-15 dakika geç çalıştırabilir — bu proje için sorun değil
- Her çalışma yaklaşık 30-60 saniye sürer → SQLite DB dosyası GitHub artifact olarak saklanır

### Kaç Dakika Harcayacak?

```
30 gün × 24 saat × 4 çalışma/saat = 2.880 çalışma
Her çalışma ≈ 1 dakika
TOPLAM ≈ 2.880 dakika/ay

Public repo'da: SINIRSIS → ÜCRETSİZ ✅
```

---

## 4. AI Motoru — Groq API

### Neden Groq?

Groq, kendi ürettiği LPU (Language Processing Unit) donanımı üzerinde açık kaynak modeller çalıştırır. Ücretsiz tier kredi kartı gerektirmez ve bu proje için fazlasıyla yeterlidir.

### Ücretsiz Tier Limitleri (Güncel)

| Model | İstek/Dakika | İstek/Gün | Bu Proje İhtiyacı |
|-------|-------------|-----------|-------------------|
| **llama-3.1-8b-instant** | 30 RPM | **14.400 RPD** | 96/gün ✅ |
| llama-3.3-70b-versatile | 30 RPM | 1.000 RPD | Yetmez |
| llama-3.1-70b | 30 RPM | 2.000 RPD | Yetmez |

**Proje günde 96 istek kullanır → 14.400 limitin %0.67'si. Tamamen güvende.**

### Kayıt

- `console.groq.com` → Sign Up → API Keys → New Key
- Kredi kartı gerekmez

### Kod Örneği

```python
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(market_data)}
    ],
    temperature=0.3,
    max_tokens=500
)

decision = json.loads(response.choices[0].message.content)
```

---

## 5. Veri Kaynakları & API'lar

Profesyonel altın traderları şu kaynakları takip eder; sistem de aynı verileri kullanır:

| API | URL | Ücretsiz Limit | Kullanım |
|-----|-----|---------------|---------|
| **GoldAPI.io** | goldapi.io | 100 istek/gün | XAU/USD, XAU/TRY spot fiyat |
| **Open Exchange Rates** | openexchangerates.org | 1.000 istek/ay | USD/TRY kuru |
| **NewsAPI.org** | newsapi.org | 100 istek/gün | Altın/dolar/enflasyon haberleri |
| **Alpha Vantage** | alphavantage.co | 25 istek/gün | GLD ETF geçmiş veri (yedek) |

**API kullanım hesabı (15 dk poll):**

```
GoldAPI   → 96 istek/gün  ≤ 100 ✅  (biraz sıkışık — 20 dk'ya çekilebilir)
Exchange  → 96 istek/gün  ≤ 1000 ✅
NewsAPI   → 4 istek/gün   ≤ 100 ✅  (sadece sabah/öğle/akşam/gece çekilir)
```

**GoldAPI yedek stratejisi:** Günlük 100 limit aşılırsa son bilinen fiyat + küçük simüle gürültü kullanılır. Alternatif: `metals-api.com` (100 istek/ay yedek olarak tutulur).

---

## 6. Altın Piyasası Saatleri & İşlem Kuralları

### Altın Piyasası Hakkında Gerçek

Spot altın (XAU/USD), hisse senedi borsası gibi belirli saatlerde kapanmaz. Dünya genelinde sürekli işlem görür:

- **Pazartesi-Cuma: 24 saat açık**
- **Hafta sonu: KAPALI** (Cuma 22:00 UTC → Pazar 22:00 UTC)
- **Resmi tatiller:** ABD ve İngiltere tatillerinde likidite çok düşer, işlem risklidir

### Piyasa Seansları (UTC saatiyle)

| Seans | UTC Saati | Özellik |
|-------|-----------|---------|
| Sydney | 22:00 – 07:00 | Düşük hacim |
| Tokyo | 00:00 – 09:00 | Orta hacim |
| Londra | 08:00 – 17:00 | **Yüksek hacim** |
| **Londra-NY Overlap** | **13:00 – 17:00** | **En yüksek likidite → En iyi işlem saati** |
| New York | 13:00 – 22:00 | Yüksek hacim |
| Gece arası | 22:00 – 00:00 | Düşük likidite, spread geniş |

### `market_hours.py` Mantığı

```python
import datetime
from zoneinfo import ZoneInfo

# ABD ve İngiltere'nin ortak büyük tatilleri (LBMA gold settlement kapanır)
MARKET_HOLIDAYS = [
    "01-01",  # Yılbaşı
    "12-25",  # Noel
    "12-26",  # Boxing Day (İngiltere)
    "07-04",  # ABD Bağımsızlık Günü
    "11-28",  # Thanksgiving (4. Perşembe - dinamik hesaplanmalı)
    "05-26",  # Memorial Day (dinamik)
    "09-01",  # Labor Day (dinamik)
    "01-20",  # MLK Day (dinamik)
]

def is_market_open() -> bool:
    now_utc = datetime.datetime.now(ZoneInfo("UTC"))
    
    # Hafta sonu kontrolü (5=Cumartesi, 6=Pazar)
    if now_utc.weekday() >= 5:
        return False
    
    # Cuma 22:00 UTC sonrası kapanır
    if now_utc.weekday() == 4 and now_utc.hour >= 22:
        return False
    
    # Pazar 22:00 UTC öncesi açılmaz
    if now_utc.weekday() == 6 and now_utc.hour < 22:
        return False
    
    # Tatil kontrolü
    date_str = now_utc.strftime("%m-%d")
    if date_str in MARKET_HOLIDAYS:
        return False
    
    # Gece arası düşük likidite: 22:00-00:00 UTC — işlem yapma
    if now_utc.hour == 22 or now_utc.hour == 23:
        return False
    
    return True
```

### Botu Tercihli Çalıştırma Saatleri

Bot her 15 dakikada tetiklense de en kaliteli kararlar şu saatlerde alınır (Türkiye saati = UTC+3):

| Periyot | Türkiye Saati | Neden Önemli |
|---------|--------------|--------------|
| Londra açılışı | 11:00 – 14:00 | Güçlü momentum başlar |
| **Londra-NY overlap** | **16:00 – 20:00** | **En iyi işlem penceresi** |
| NY kapanış | 01:00 – 02:00 | Günlük kapanış hareketi |

---

## 7. AI Karar Motoru — Prompt & Mantık

### Sistem Promptu (Sabit)

```
Sen 15 yıllık deneyimli bir XAU/USD spot altın traderısın.
Görevin: 30 günlük sanal deney süresinde portföy değerini 
maksimize etmek. Asla tüm sermayeyi tek işleme koyma.
Risk yönetimi her şeyden önce gelir.

Karar verirken şunlara dikkat et:
- RSI 30 altı: aşırı satım → alım fırsatı
- RSI 70 üstü: aşırı alım → satım düşün
- MACD bullish crossover → pozitif sinyal
- Bollinger üst bandı kırılımı → dikkatli ol
- DXY yükselişi → altın baskı altında
- Haber skoru +0.5 üstü → pozitif katalizör

SADECE JSON döndür, başka hiçbir şey yazma.
```

### Kullanıcı Mesajı (Her 15 dk)

```json
{
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
    "macd_signal": "bullish",
    "bb_position": "mid",
    "ema50_vs_ema200": "above",
    "price_change_1h_pct": 0.34,
    "price_change_24h_pct": -0.8
  },
  "news_sentiment_score": 0.3,
  "dxy_change_pct": -0.4,
  "session": "london_ny_overlap",
  "days_remaining": 22
}
```

### Beklenen AI Cevabı

```json
{
  "action": "BUY",
  "amount_grams": 10.0,
  "confidence": 0.75,
  "reasoning": "RSI 58 orta bölgede, MACD bullish. DXY zayıflıyor (-0.4%). Haber skoru pozitif. London-NY overlap saatinde yüksek likidite. Kademeli alım yapılabilir."
}
```

### Risk Yönetimi Kuralları (Kod Seviyesinde)

AI kararına ek olarak sistem şu kuralları otomatik uygular:

```python
MAX_POSITION_PCT = 0.05       # Tek işlemde max portföyün %5'i
STOP_LOSS_PCT = 0.10          # Portföy başlangıcın %10'una düşünce dur
MAX_DAILY_TRADES = 8          # Günde max 8 işlem
MIN_CONFIDENCE = 0.55         # %55 altı güven → HOLD'a çevir
COOLDOWN_MINUTES = 30         # İki işlem arası min 30 dk bekle
```

---

## 8. Sanal Kasa & Portföy Takibi

### SQLite Şeması

```sql
-- Portföy anlık durum
CREATE TABLE portfolio_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    gold_grams  REAL NOT NULL,
    cash_try    REAL NOT NULL,
    gold_price_try REAL NOT NULL,
    total_value_try REAL NOT NULL,
    pnl_pct     REAL NOT NULL
);

-- İşlem geçmişi
CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    action      TEXT NOT NULL,    -- BUY / SELL
    grams       REAL NOT NULL,
    price_try   REAL NOT NULL,
    total_try   REAL NOT NULL,
    reasoning   TEXT,
    confidence  REAL,
    session     TEXT              -- hangi seansta yapıldı
);

-- Günlük özet
CREATE TABLE daily_summary (
    date              TEXT PRIMARY KEY,
    start_value_try   REAL,
    end_value_try     REAL,
    daily_pnl_pct     REAL,
    trades_count      INTEGER,
    gold_grams_eod    REAL,
    cash_try_eod      REAL,
    high_price_try    REAL,
    low_price_try     REAL
);

-- Sistem durumu
CREATE TABLE system_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);
-- Örnek kayıtlar:
-- ("status", "running") / "paused" / "stopped"
-- ("start_date", "2025-12-01")
-- ("initial_value_try", "72500")
```

### Kasa Ekran Formatı

```
╔══════════════════════════════════════╗
║      ⬡ ALTIN TRADER BOT — KASA ⬡   ║
╠══════════════════════════════════════╣
║  🥇 Altın    :  87.50 gr            ║
║  💵 Nakit    :  ₺15,200             ║
║  📊 Toplam   :  ₺81,550             ║
║  📈 Kar/Zarar:  +%12.48             ║
║  📅 Gün      :  8 / 30              ║
║  ⏱  Seans    :  London-NY Overlap   ║
╚══════════════════════════════════════╝
```

---

## 9. Telegram Bildirim Sistemi

### Bot Kurulumu

1. Telegram'da `@BotFather` ile konuş
2. `/newbot` → İsim ver → Token al
3. Kendi Telegram ID'ni öğren: `@userinfobot`'a mesaj at
4. `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` değerlerini kaydet

### Mesaj Tipleri

| Tip | Tetikleyici | İçerik |
|-----|-------------|--------|
| İşlem Bildirimi | Her BUY/SELL | Eylem, miktar, fiyat, AI gerekçesi, kasa durumu |
| HOLD Bildirimi | Opsiyonel (günde max 1) | Bekleme gerekçesi |
| Günlük Rapor | Her gün 23:00 UTC | Özet PnL, işlem sayısı, kasa durumu |
| Piyasa Kapalı | Hafta sonu başında | "Pazar günü piyasa kapalı, bekliyorum" |
| Alarm | Portföy %20 düşünce | Uyarı mesajı |
| Fis Çekildi | %10 eşiği aşılınca | Final raporu + kapanış özeti |

### Örnek İşlem Mesajı

```
🟢 ALIM YAPILDI
━━━━━━━━━━━━━━━━━━━━━━━━
📦 Miktar  : 12.5 gr altın
💰 Fiyat   : ₺78,500 / gr
💸 Toplam  : ₺981,250
📊 Seans   : London-NY Overlap

🧠 AI Gerekçesi:
RSI 35'e geriledi (aşırı satım bölgesi).
DXY 0.6% zayıfladı. Haber skoru pozitif
(+0.42). MACD bullish crossover oluştu.
Güven: %78

💼 YENİ KASA:
Altın: 87.5 gr | Nakit: ₺15,200
Toplam: ₺81,550 (+%12.5)
Kalan: 22 gün

🕐 10 Ara 2025, 17:32 UTC
```

### Telegram Kontrol Komutları

Telegram'dan bota aşağıdaki komutları gönderebilirsin:

| Komut | İşlev |
|-------|-------|
| `/start` | Botu başlat |
| `/stop` | Botu durdur |
| `/pause` | Geçici beklet (işlem yapma, sadece izle) |
| `/resume` | Bekletmeden devam et |
| `/status` | Anlık kasa durumu |
| `/history` | Son 10 işlem |
| `/report` | Anlık özet raporu |

> **Not:** Telegram komutları GitHub Actions ile entegre çalışmaz — botun Telegram'dan komut alabilmesi için küçük bir webhook veya polling servisi gerekir. Bu proje için en basit çözüm: komutlar `system_state` tablosuna kaydedilir, bir sonraki çalışmada okunur.

---

## 10. Başlatma / Durdurma / Bekletme

### Sistem Durumları

```
RUNNING  → Normal çalışıyor, işlem yapıyor
PAUSED   → Çalışıyor ama işlem yapmıyor (sadece izliyor)
STOPPED  → Tamamen durdu (GitHub Actions workflow devre dışı)
FINISHED → 30 gün doldu veya fis çekildi
```

### GitHub Actions Üzerinden Kontrol

Workflow dosyasına `workflow_dispatch` eklenerek GitHub arayüzünden elle tetiklenebilir veya durdurulabilir:

```yaml
on:
  schedule:
    - cron: '*/15 * * * 1-5'   # Pazartesi-Cuma her 15 dk
  workflow_dispatch:             # Elle tetikleme butonu
    inputs:
      command:
        description: 'Komut (start/pause/resume/stop)'
        required: false
        default: 'status'
```

---

## 11. Proje Dosya Yapısı

```
gold-trader-bot/                      ← GitHub'da PUBLIC repo
│
├── .github/
│   └── workflows/
│       └── trader.yml                ← GitHub Actions cron workflow
│
├── main.py                           ← Ana giriş noktası
├── config.py                         ← Sabitler ve ayarlar
├── requirements.txt                  ← Python bağımlılıkları
│
├── modules/
│   ├── market_hours.py               ← Piyasa açık/kapalı kontrolü
│   ├── price_fetcher.py              ← GoldAPI + döviz kuru
│   ├── indicators.py                 ← RSI, MACD, Bollinger, EMA
│   ├── news_analyzer.py              ← Haber duyarlılık skoru
│   ├── ai_decision.py                ← Groq API entegrasyonu
│   ├── portfolio.py                  ← Sanal kasa yönetimi
│   ├── telegram_bot.py               ← Bildirim gönderme + komutlar
│   └── report_generator.py           ← Günlük rapor oluşturma
│
├── data/
│   └── portfolio.db                  ← SQLite (artifact olarak saklanır)
│
└── logs/
    └── goldbot.log                   ← Çalışma logları
```

---

## 12. Ortam Değişkenleri (.env / GitHub Secrets)

GitHub Actions'ta `.env` dosyası yerine **GitHub Secrets** kullanılır. Bunlar şifreli olarak saklanır ve workflow'da `${{ secrets.DEGISKEN_ADI }}` ile erişilir.

```
# === ALTIN FİYAT ===
GOLDAPI_KEY=your_key_here
METALS_API_KEY=your_key_here              # yedek

# === DÖVİZ KURU ===
OPENEXCHANGE_KEY=your_key_here

# === HABER ===
NEWS_API_KEY=your_key_here

# === GROQ AI ===
GROQ_API_KEY=gsk_...

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN=123456789:AAF...
TELEGRAM_CHAT_ID=987654321

# === PORTFÖY ===
INITIAL_GOLD_GRAMS=100
INITIAL_CASH_TRY=0

# === RİSK YÖNETİMİ ===
MAX_POSITION_PCT=0.05
STOP_LOSS_PCT=0.10
MAX_DAILY_TRADES=8
MIN_CONFIDENCE=0.55
POLL_INTERVAL_MINUTES=15
```

---

## 13. Python Bağımlılıkları

```
# requirements.txt
groq>=0.9.0                  # Groq AI (Llama)
python-telegram-bot>=20.0    # Telegram
requests>=2.31.0             # HTTP istekleri
pandas>=2.0.0                # Veri işleme
ta>=0.10.0                   # Teknik analiz (RSI, MACD, Bollinger, EMA)
python-dotenv>=1.0.0         # .env desteği (lokal geliştirme)
sqlalchemy>=2.0.0            # SQLite ORM
numpy>=1.24.0                # Sayısal işlemler
loguru>=0.7.0                # Gelişmiş loglama
schedule>=1.2.0              # Yedek zamanlayıcı
```

---

## 14. GitHub Actions Workflow Dosyası

```yaml
# .github/workflows/trader.yml
name: Gold Trader Bot

on:
  schedule:
    # UTC saatiyle her 15 dakika — sadece Pazartesi-Cuma
    # Altın piyasası UTC 00:00-22:00 arası aktif (piyasa_hours.py ikinci kontrol yapar)
    - cron: '*/15 0-22 * * 1-5'
  workflow_dispatch:
    inputs:
      command:
        description: 'Manuel komut (status/pause/resume)'
        required: false
        default: 'status'

jobs:
  run-trader:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Kodu çek
        uses: actions/checkout@v4

      - name: Python kur
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Bağımlılıkları yükle
        run: pip install -r requirements.txt

      - name: Önceki veritabanını indir (artifact)
        uses: actions/download-artifact@v4
        with:
          name: portfolio-db
          path: data/
        continue-on-error: true   # İlk çalışmada artifact yoktur, hata vermesin

      - name: Botu çalıştır
        env:
          GOLDAPI_KEY: ${{ secrets.GOLDAPI_KEY }}
          OPENEXCHANGE_KEY: ${{ secrets.OPENEXCHANGE_KEY }}
          NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          INITIAL_GOLD_GRAMS: ${{ secrets.INITIAL_GOLD_GRAMS }}
          INITIAL_CASH_TRY: ${{ secrets.INITIAL_CASH_TRY }}
          MAX_POSITION_PCT: "0.05"
          STOP_LOSS_PCT: "0.10"
          MAX_DAILY_TRADES: "8"
          MIN_CONFIDENCE: "0.55"
        run: python main.py

      - name: Veritabanını artifact olarak kaydet
        uses: actions/upload-artifact@v4
        if: always()    # Hata olsa bile kaydet
        with:
          name: portfolio-db
          path: data/portfolio.db
          retention-days: 35    # 30 gün + 5 gün tampon
```

> **Neden artifact?** GitHub Actions her çalışmada temiz bir ortam başlatır. SQLite dosyasının kalıcı olması için artifact olarak yüklenir ve bir sonraki çalışmada indirilir. Bu yaklaşım ücretsiz ve güvenilirdir.

---

## 15. Maliyet Analizi

| Servis | Kullanım (30 gün) | Ücret |
|--------|-------------------|-------|
| GitHub Actions (public repo) | ~2.880 çalışma | **Ücretsiz** |
| GoldAPI.io | ~2.000 istek | **Ücretsiz** |
| Open Exchange Rates | ~2.000 istek | **Ücretsiz** |
| NewsAPI.org | ~120 istek | **Ücretsiz** |
| Groq API (llama-3.1-8b) | ~2.880 istek | **Ücretsiz** |
| Telegram Bot | Sınırsız mesaj | **Ücretsiz** |
| **TOPLAM** | | **$0** |

---

## 16. Geliştirme Yol Haritası

### Faz 1 — Temel Altyapı (1-2 gün)
- [ ] GitHub repo oluştur (PUBLIC)
- [ ] SQLite şeması ve `portfolio.py` yaz
- [ ] `market_hours.py` yaz ve test et
- [ ] GoldAPI + döviz kuru entegrasyonu test et

### Faz 2 — Analiz & AI (1-2 gün)
- [ ] Teknik indikatörler implement et (RSI, MACD, Bollinger, EMA)
- [ ] Haber duyarlılık skoru yaz
- [ ] Groq API bağlantısı ve prompt test et
- [ ] JSON parse + karar alma döngüsü tamamla

### Faz 3 — Telegram & Raporlama (1 gün)
- [ ] Telegram bot kur, test mesajı gönder
- [ ] İşlem bildirimi formatını tamamla
- [ ] Günlük rapor oluşturmayı test et
- [ ] Komut sistemi (/status vb.) implement et

### Faz 4 — GitHub Actions (1 gün)
- [ ] `trader.yml` workflow dosyasını yaz
- [ ] Tüm secret'ları GitHub'a ekle
- [ ] Artifact sistemi test et (upload/download)
- [ ] İlk cron çalışmasını gözlemle

### Faz 5 — 30 Günlük Deney
- [ ] `INITIAL_GOLD_GRAMS` değerini belirle
- [ ] Botu başlat
- [ ] Telegram'dan günlük takip et

---

## 17. Kurulum Rehberi — Adım Adım

Bu bölüm, teknik bilgisi olmayan birinin projeyi sıfırdan kurmasını sağlayacak adım adım kılavuzdur.

---

### Adım 1 — GitHub Hesabı Aç

1. `github.com` adresine git
2. **Sign Up** → Hesap oluştur (varsa giriş yap)
3. Yeni bir **public** repository oluştur:
   - Repository name: `gold-trader-bot`
   - **Public** seç ✅
   - **Add a README file** işaretle
   - **Create repository** tıkla

---

### Adım 2 — Groq API Key Al

1. `console.groq.com` adresine git
2. **Sign Up** → Google veya email ile kayıt ol (kredi kartı gerekmez)
3. Sol menüden **API Keys** → **Create API Key**
4. Key adını yaz: `gold-trader-bot`
5. Çıkan `gsk_...` ile başlayan anahtarı kopyala ve bir yere kaydet

---

### Adım 3 — GoldAPI Key Al

1. `goldapi.io` adresine git
2. **Get Free API Key** → Email ile kayıt ol
3. Dashboard'dan API Key'i kopyala

---

### Adım 4 — Open Exchange Rates Key Al

1. `openexchangerates.org` adresine git
2. **Sign Up for Free** → Free plan seç
3. Dashboard'dan **App ID**'yi kopyala

---

### Adım 5 — NewsAPI Key Al

1. `newsapi.org` adresine git
2. **Get API Key** → Email ile kayıt ol
3. Dashboard'dan API Key'i kopyala

---

### Adım 6 — Telegram Bot Kur

1. Telegram uygulamasını aç
2. Arama kutusuna `@BotFather` yaz ve aç
3. `/newbot` gönder
4. Bot adı sor → istediğin bir isim yaz (ör: `Gold Trader Bot`)
5. Bot kullanıcı adı sor → benzersiz bir şey yaz, `_bot` ile bitmeli (ör: `myGoldTrader_bot`)
6. BotFather sana bir **TOKEN** verir: `123456789:AAF...` şeklinde — kopyala
7. Şimdi kendi Telegram ID'ni öğren:
   - `@userinfobot` hesabını ara ve aç
   - `/start` gönder
   - Sana `Your ID: 987654321` gibi bir numara verecek — kopyala

---

### Adım 7 — GitHub Secrets'a API Key'leri Ekle

GitHub repo sayfanda:

1. **Settings** (sağ üst) → Sol menüden **Secrets and variables** → **Actions**
2. **New repository secret** tıkla
3. Her key için ayrı ayrı ekle:

| Secret Adı | Değer |
|------------|-------|
| `GOLDAPI_KEY` | GoldAPI'den aldığın key |
| `OPENEXCHANGE_KEY` | OpenExchangeRates App ID |
| `NEWS_API_KEY` | NewsAPI key |
| `GROQ_API_KEY` | `gsk_...` ile başlayan Groq key |
| `TELEGRAM_BOT_TOKEN` | BotFather'dan aldığın token |
| `TELEGRAM_CHAT_ID` | userinfobot'tan öğrendiğin ID |
| `INITIAL_GOLD_GRAMS` | Kaç gram altınla başlayacaksın (ör: `100`) |
| `INITIAL_CASH_TRY` | Başlangıç nakit (ör: `0`) |

---

### Adım 8 — Kodu Yükle (AI Coder ile)

AI coder'a bu teknik dokümanı ver ve şunu söyle:

> "Bu dokümana göre `gold-trader-bot` projesini Python ile yaz. Bölüm 16'daki yol haritasını takip et. Tüm dosyaları üret."

Üretilen dosyaları GitHub repo'na yükle:

**Yöntem A — GitHub web arayüzü (kolay):**
1. Repo sayfanda **Add file** → **Upload files**
2. Tüm dosyaları sürükle-bırak
3. **Commit changes**

**Yöntem B — Git CLI (tercihli):**
```bash
git clone https://github.com/KULLANICIN/gold-trader-bot.git
cd gold-trader-bot
# Dosyaları kopyala
git add .
git commit -m "Initial commit"
git push origin main
```

---

### Adım 9 — Botu Başlat

1. GitHub repo sayfanda **Actions** sekmesine tıkla
2. Sol tarafta **Gold Trader Bot** workflow'unu gör
3. İlk çalışma otomatik başlamaz — **Run workflow** butonuna tıkla
4. Sonrasında cron otomatik devreye girer (Pazartesi-Cuma her 15 dk)

---

### Adım 10 — Telegram'dan Takip Et

- Her işlem yapıldığında Telegram'dan bildirim alırsın
- Her gece 23:00'de günlük rapor gelir
- **Actions** sekmesinden her çalışmanın logunu görebilirsin

---

### Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Workflow çalışmıyor | Actions sekmesinde enabled mi kontrol et |
| API hatası | İlgili Secret'ın doğru girildiğini kontrol et |
| Telegram mesaj gelmiyor | CHAT_ID'nin doğru olduğundan emin ol |
| Veritabanı sıfırlandı | Artifact upload adımında hata olabilir, logu incele |
| Rate limit hatası | GoldAPI günlük 100 limiti aşıldı — poll süresini 20 dk'ya çek |

---

*Altın Trader Bot v1.2 — Tamamen ücretsiz, tamamen sanal, tamamen deney amaçlı.*
