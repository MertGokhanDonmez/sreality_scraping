# Bezrealitky → Excel exporter

Bu proje, verilen Bezrealitky arama URL'sindeki **tüm sonuç sayfalarını** dolaşır, her ilanın detay sayfasını açar ve erişilebilen tüm alanları Excel'e aktarır.

## Çıktı sayfaları

- **Listings**: Her ilan için tek satır. Kira, aidat, enerji, depozito, toplam bilinen aylık maliyet, tam açıklama, ilan URL'si, tüm dinamik özellikler ve dinamik amenity sütunları.
- **Amenities**: Her özellik/olanak ayrı satır.
- **Nearby**: Çevredeki yerler ve mesafe metinleri ayrı satır.
- **Images**: Fotoğraf URL'leri ayrı satır.
- **Raw**: Ayrıştırılmış JSON'lar ve ham bölüm metinleri. Site yeni bir alan eklerse veri kaybolmasın diye tutulur.
- **Run_Info**: Kaynak URL ve çalışma istatistikleri.

## Kurulum

Python 3.10 veya daha yeni bir sürüm gerekir.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -U pip
pip install -e .
```

## Çalıştırma

```bash
bezrealitky-export \
  --url "https://www.bezrealitky.cz/vyhledat?disposition=DISP_1_1&disposition=DISP_1_KK&disposition=DISP_2_1&disposition=DISP_2_KK&estateType=BYT&location=fromMap&offerType=PRONAJEM&priceTo=17000&currency=CZK&provinces=praha&country=ceska-republika&locale=CS&searchPriceWithCharges=true&regionOsmIds=R435541 \
  --output "bezrealitky_prague_under_17000.xlsx"
```

Aynı komut modül olarak da çalışır:

```bash
python -m bezrealitky_scraper.cli --url "ARGRAMA_URLSI" --output sonuc.xlsx
```

Hızlı deneme için:

```bash
bezrealitky-export --max-pages 1 --max-listings 2 --output smoke_test.xlsx
```

## Testler

```bash
pip install -e ".[test]"
pytest --cov=bezrealitky_scraper --cov-report=term-missing
```

Canlı site testi varsayılan olarak kapalıdır; gerçek siteye istek gönderir:

```bash
RUN_LIVE_TESTS=1 pytest -m live -q
```

## Her sabah otomatik çalışma + mail gönderimi

`daily_run.py`, siteyi tarar; ilk çalıştırmada bulduğu tüm ilanları, sonraki her
çalıştırmada ise **yalnızca bir önceki çalıştırmadan beri yeni eklenen ilanları**
bir `.xlsx` dosyasına yazıp mail ile gönderir. Hangi ilanların daha önce
görüldüğü `state/seen_listings.json` içinde tutulur; mail başarıyla gönderilmeden
bu dosya güncellenmez, yani mail gönderimi başarısız olursa o günün yeni
ilanları bir sonraki çalıştırmada kaybolmaz, tekrar "yeni" sayılır.

### 1) Gmail App Password oluştur

Google Hesabı → Güvenlik → 2 Adımlı Doğrulama (açık olmalı) → Uygulama
Şifreleri → yeni bir şifre oluştur. Bu 16 haneli şifre normal Gmail şifren
**değildir**, sadece bu script için kullanılır.

### 2) Ayarları yapılandır

```bash
cp .env.example .env
nano .env   # SEARCH_URL, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, MAIL_TO doldur
```

`.env` dosyasını asla paylaşma / commit'leme; içinde şifre var.

### 3) Elle bir kez dene

```bash
./run_daily.sh
tail -f logs/cron.log
```

İlk çalıştırmada tüm mevcut ilanlar mail ile gelir (baseline). Script'i tekrar
çalıştırırsan (site değişmediyse) mail'de "0 yeni ilan" görürsün — bu doğru
davranıştır.

### 4) Ubuntu sunucuda her sabah 09:00'da otomatik çalıştır

```bash
crontab -e
```

Şu satırı ekle (yolu kendi kurulum dizinine göre düzelt):

```
0 9 * * * /home/kullanici/bezrealitky_excel_scraper/run_daily.sh
```

`run_daily.sh` zaten proje dizinine geçip `.venv` içindeki Python'u kullanıyor,
bu yüzden cron'un `PATH`i minimal olsa bile çalışır. VPN üzerinden zaten hep
bağlı çalışan bir sunucu kullandığın için ayrı bir "VPN'e bağlan" adımına
gerek yok — sunucu zaten o ağdan çıkıyor.

Çıktı dosyaları `output/bezrealitky_YYYY-MM-DD.xlsx` altında, loglar
`logs/cron.log` altında birikir; ikisini de zaman zaman temizleyebilirsin.

## Davranış ve sınırlar

- İstekler arasında varsayılan 0,8 saniye bekler; bu değeri düşürmek önerilmez.
- Yalnızca herkese açık ilan sayfalarını okur; giriş, mesajlaşma veya iletişim bilgisi toplamaya çalışmaz.
- Site HTML yapısını kökten değiştirirse parser testi hata verir. `Raw` sayfası, yeni/alışılmadık alanların kaybolmasını önler.
- Site kullanım koşulları ve robots.txt kuralları değişebilir. Çalıştırmadan önce güncel kuralları kontrol etmek kullanıcının sorumluluğundadır.
