# TripBridge veri hikayesi

Bu not, altı CSV extract’inin teknik sözlüğü değil; verinin **ne anlattığı**. İleride yapacağımız temizlik, yükleme ve analize başlamadan önce ortak resmi netleştirmek için yazıldı.

TripBridge, Avustralya merkezli kurgusal bir seyahat operasyonu. Extract tarihi **17 Ağustos 2026**. Hikaye kabaca iki yıllık: müşteri kayıtları **17 Ağustos 2024**’te başlıyor; onaylı seyahatler 2027’ye kadar uzanıyor. Tüm isimler, e-postalar (`.test`) ve işlem referansları sentetik.

---

## Bir cümlelik hikaye

Bir kişi üye olur, bazen üyelik alır, bazen kampanya görür, bir seyahat rezervasyonu yapar, ödeme dener, gerekirse iade alır.

Altı dosya bu cümleyi altı sahneye böler.

| Sahne | Dosya | Satır | Ne anlatır |
|---|---|---:|---|
| Kim bu kişi? | `data/customers.csv` | 50.000 | Profil, ev, onay, hesap durumu |
| Üye mi? | `data/memberships.csv` | 70.000 | Tier, dönem, ücret, yenileme |
| Nereye gidiyor? | `data/bookings.csv` | 400.000 | Ürün, rota, tutar, kanal, rezervasyon sonucu |
| Para nasıl geçti? | `data/payments.csv` | 450.000 | Deneme, yöntem, tutar, başarı/başarısızlık |
| Para geri geldi mi? | `data/refunds.csv` | 30.000 | İade nedeni, tutar, sonuç |
| Pazarlama işe yaradı mı? | `data/campaign_events.csv` | 500.000 | Mesaj yolculuğu: gönderildi → açıldı → tıklandı → dönüştü |

Para birimleri karışık (çoğunlukla AUD, az NZD/USD/EUR/GBP). Toplamları **aynı para birimi içinde** okumak gerekir; extract’te kur tablosu yok.

---

## Pair’ler: tablolar nasıl bağlanır

Zincir müşteriden başlar. Her bağ aynı kişiyi taşır; yetim (orphan) foreign key yok.

```text
customers 1──N memberships
    │
    ├── 1──N bookings ──(opsiyonel)── memberships
    │         │
    │         ├── 1──N payments ── 1──N refunds
    │         │                         │
    │         └─────────────────────────┘  (iade hem ödeme hem rezervasyona bağlı)
    │
    └── 1──N campaign_events ──(opsiyonel)── bookings   [yalnız CONVERTED]
```

| Pair | Anahtar | İş kuralı |
|---|---|---|
| müşteri ↔ üyelik | `customer_id` | Bir müşterinin 0–3 üyeliği olabilir. 41.000 müşterinin en az bir kaydı var; 9.000’i üye değil. |
| müşteri ↔ rezervasyon | `customer_id` | 40.299 kişi rezervasyon yapmış. 6.000 kişi hiç rezervasyon yapmamış. |
| üyelik ↔ rezervasyon | `membership_id` | Opsiyonel. Doluysa üyelik **aynı müşteriye** aittir ve rezervasyon tarihinde geçerlidir. ~144.000 rezervasyonda boştur (üye değil, dönem dışı veya kasıtlı boşluk). |
| rezervasyon ↔ ödeme | `booking_id` + `customer_id` | Her rezervasyonun en az bir ödeme denemesi var. ~36.000 rezervasyon depozito + kalan; ~14.000 rezervasyon başarısız deneme + retry. |
| ödeme ↔ iade | `payment_id` | İade, ödemeden **sonra** gelir ve kümülatif iade o ödemeyi aşmaz. |
| kampanya ↔ rezervasyon | `conversion_booking_id` | Yalnız dönüşüm olaylarında, o müşterinin kendi rezervasyonu. Atıf opsiyonel (~11.200 satırda dolu). |

Teknik sözlük: `DATA_DICTIONARY.md`. Kasıtlı kalite sorunları: `DATA_QUALITY_NOTES.md`.

---

## Dimension’lar: hikayeyi nasıl keseriz

Ölçüm (tutar, yolcu, olay sayısı) dimension’larla dilimlenir. Aşağıdakiler analizin doğal kesitleridir.

**Müşteri.** `city`, `state`, `country` (yaklaşık %97 Avustralya), `gender`, `customer_status` (ACTIVE / INACTIVE / CLOSED), `marketing_consent` (true / false / boş). `signup_date` ve `date_of_birth` zaman ve yaş kesitidir.

**Üyelik.** `membership_type` (STANDARD, PLUS, PREMIUM, CORPORATE), `membership_status` (ACTIVE, EXPIRED, CANCELLED, SUSPENDED), `renewal_type` (AUTO, MANUAL, NONE). Ücret her zaman AUD’dir; rezervasyon başka kurlarda olabilir.

**Rezervasyon.** `booking_type` (FLIGHT, HOTEL, PACKAGE, CAR_HIRE, TOUR), `origin` / `destination`, `booking_currency`, `channel` (WEB, MOBILE_APP, CALL_CENTRE, AGENT), `booking_status`, `passenger_count`. `booking_date` ile `travel_date` iki ayrı zaman boyutu: sipariş vs seyahat.

**Ödeme.** `payment_method`, `payment_currency` (rezervasyonla aynı), `payment_status` (SUCCESS, PENDING, FAILED, DECLINED, REVERSED).

**İade.** `refund_reason` (müşteri iptali, havayolu iptali, hizmet hatası, fiyat düzeltmesi vb.), `refund_status` (COMPLETED, PENDING, REJECTED).

**Kampanya.** `campaign_name` / `campaign_type` (SEASONAL, TACTICAL, MEMBER, LIFECYCLE), `channel` (EMAIL, SMS, PUSH, IN_APP), `event_type`, `device_type`, `offer_code`.

---

## Her dosya ne demek istiyor

### customers — “Bu kişi kim, hâlâ bizimle mi?”

`customer_id` kalıcı kimliktir. İsim, e-posta, telefon ve doğum tarihi kişiyi tanıtır; e-posta doğal anahtara yakındır ama 25 çift aynı kişilik bilgilerini paylaşır, ID’leri farklıdır (dedup egzersizi). `marketing_consent` boşsa “hayır” değil, **bilinmiyor**. CLOSED hesap kapanmıştır; INACTIVE sessizdir; ACTIVE günlük operasyondadır.

### memberships — “Bu kişi ne kadar bağlı, hangi indirim haklı?”

Üyelik bir abonelik dönemidir, ömür boyu rozet değil. Aynı kişi STANDARD’dan PLUS/PREMIUM’a geçebilir; eski satır EXPIRED/CANCELLED kalır. Rezervasyon indirimi büyük ölçüde bu tiere bağlıdır. `annual_fee` üyelik geliridir; seyahat cirosu `bookings` / `payments` tarafındadır.

### bookings — “Ne satıldı, ne kadara, ne oldu?”

Operasyonun kalbi. `gross_booking_amount` liste fiyatı, `discount_amount` düşülen indirim, net = brüt − indirim. Ödemeler neti aşamaz.

Durumlar ayrı hikayelerdir:

- **COMPLETED** — seyahat gerçekleşmiş (~%73)
- **CONFIRMED** — gelecek seyahat, henüz bitmemiş
- **CANCELLED** — iptal; yine de iade edilemeyen tedarikçi ücreti kalmış olabilir
- **PARTIALLY_REFUNDED** / **FULLY_REFUNDED** — iade tablosuyla tutarlı olmak zorunda

HOTEL / CAR_HIRE / TOUR’da `origin` bazen boştur: her üründe kalkış şehri anlamlı değil.

### payments — “Para gerçekten tahsil edildi mi?”

Bir satır = bir deneme, kesin tahsilat değil. SUCCESS ciroya yakındır; FAILED / DECLINED retry’ı anlatır; REVERSED geri çekilmiş tahsilattır; PENDING henüz kapanmamıştır. Aynı rezervasyonda iki SUCCESS (depozito + kalan) normaldir. İptal rezervasyonda SUCCESS, iade edilmeyen kesinti olabilir.

### refunds — “Neden ve ne kadarı geri gitti?”

İade ödemeyi takip eder, rezervasyonu yeniden yazmaz. Tam iade, tamamlanmış iadelerin başarılı ödemeye eşitlenmesi demektir. Kısmi iade, sıfır ile tam arasında bir tamamlanmış tutardır. PENDING / REJECTED, rezervasyonu FULLY_REFUNDED yapmaz.

### campaign_events — “Mesaj görüldü mü, rezervasyona bağlandı mı?”

Bir satır tek bir dokunuştur, kampanyanın tamamı değil. Tipik yolculuk: SENT → DELIVERED → OPENED → CLICKED → CONVERTED (veya BOUNCED / UNSUBSCRIBED). `campaign_id` o ayın gönderim örneği, `campaign_name` aile adıdır (ör. `SUMMER_ESCAPE`, `NEW_MEMBER_WELCOME`). `offer_code` her mesajda yoktur.

---

## İleride işe yarayacak “kir”

Kaynak kasıtlı olarak biraz kirli; PK/FK kırılmamış. Analizde sürpriz olmasın diye kısa liste:

- 750 telefonsuz müşteri; 250 belirsiz consent; 120 büyük harfli e-posta
- 25 sahte-çift müşteri (aynı kişi gibi, farklı ID)
- 80 rezervasyonda `travel_date` < `booking_date` (1–2 gün)
- 600 eski rezervasyonun `updated_at`’i extract’e yakın (incremental watermark)
- Kampanya kanalında karışık büyük/küçük harf; 200 tekrar gibi olay (farklı `event_id`)
- Az sayıda mesaj, consent’i true olmayan müşteriye gitmiş

Ayrıntı: `DATA_QUALITY_NOTES.md`. Hacim ve dağılımlar: `GENERATION_SUMMARY.md`.
