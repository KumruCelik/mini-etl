# mini-etl — Tasarım Kararları

## Problem

Bir veri hattı üç iş yapar: oku, dönüştür, yaz. Zor olan bu üçü değil,
aralarındaki gerçekler:

- **Veri belleğe sığmıyor.** Hedef: 5 GB'lık bir dosyayı 200 MB RAM'de işlemek.
- **Satırların bir kısmı bozuk.** Tek bozuk satır tüm işi durdurmamalı.
- **Reddedilen satıra sonradan bakılabilmeli.** "Kaç satır düştü" yetmez,
  "hangi satır ve neden" gerekiyor.
- **Kaynak geçici olarak hata verebilir.** HTTP kaynağında tekrar deneme şart.
- **İş bitince ne olduğu bilinmeli.** Kaç satır okundu, yazıldı, reddedildi,
  ne kadar sürdü.

Kimin için: kendi veri hatlarımı kurarken tekrar tekrar yazdığım okuma/
dönüştürme/yazma iskeletini bir kez yazıp yeniden kullanmak. Üretim ölçeğinde
bir araç değil; Airflow veya Spark'ın yerini almıyor.

## Temel soyutlama

Her katman bir **generator** döndürür ve zincirlenir. Veri hiçbir noktada
tamamen belleğe girmez.

```
CsvSource.oku()  ──►  Iterator[Record]
                            │
                    temizle >> dogrula >> zenginlestir
                            │
                            ├──► dead_letter.jsonl  (bozuk satır + hata)
                            ▼
                   SqliteSink.yaz()  ──►  yazılan satır sayısı

              Rapor: okundu / yazıldı / reddedildi / süre
```

Bunun kanıtını Hafta 2'de yazdım: bir generator, sonucu istenene kadar hiçbir
şey üretmiyor (`test_tembellik`). Aynı davranış burada bellek garantisinin
temeli.

---

## Karar 1 — Kayıt tipi

**Seçim:** `Record = dict[str, Any]`

**Gerekçe:** Şema veriden gelir, koddan değil. Framework hangi CSV'yi okuyacağını
önceden bilmek zorunda kalmaz; aynı kod her sütun düzeniyle çalışır.

**Reddedilenler:**

- `dataclass` — Tip güvenli olurdu ve mypy alan adlarını denetlerdi. Ama her
  yeni veri kaynağı için yeni bir sınıf yazmak gerekirdi; `mini-etl` bilmediği
  bir CSV'yi okuyamaz hale gelirdi. Genel amaçlı olmaktan çıkıp tek bir projeye
  özel bir araç olurdu.
- `TypedDict` — Sözlük esnekliği + statik tip verirdi, ama şema yine derleme
  zamanında sabit olmalıydı. Aynı sorun.

**Bedeli:** Tip güvenliği yok. `kayit["ad"]` yazım hatası çalışma zamanında
çıkar. Bunu `dogrula` transform'u ile çalışma zamanında telafi ediyorum —
şema denetimi tip sisteminde değil, hattın içinde.

---

## Karar 2 — Transform arayüzü

**Seçim:** Hibrit. Kullanıcı satır seviyesinde fonksiyon yazar
(`Record -> Record`), framework onu akış seviyesine yükseltirken her satırı
`try/except` ile sarar. Ham akış transform'u (`Iterator -> Iterator`) yazma
kapısı da açık kalır.

**Gerekçe:** İki dünyanın da gereken tarafını alıyor. Kullanıcı basit fonksiyon
yazıyor, hata izolasyonunu framework üstleniyor; ama pencereleme ve gruplama
gibi satırlar arası işler için ham akış yolu duruyor.

Bu, Hafta 2'de yazdığım `yakala` decorator'ının aynı fikri: fonksiyonu sar,
hatayı framework yönetsin.

**Reddedilenler:**

- **Sadece satır seviyesi** — En basit ve en kolay test edilir, hata izolasyonu
  bedava gelirdi. Ama satırlar arası hiçbir iş yapılamazdı: pencereleme,
  gruplama, tekilleştirme, satır sayısını değiştiren filtreleme imkânsız
  olurdu. Ödevin "generator tabanlı streaming" vurgusu zayıflardı.
- **Sadece akış seviyesi** — En güçlü tasarım; her şey yapılabilirdi. Ama tek
  bozuk satır generator'ı öldürür ve tüm akış durur. Satır bazlı hata toplama
  için her transform'un içine ayrı ayrı hata yönetimi yazmak gerekirdi —
  tekrar eden kod ve unutulacak yerler.

---

## Karar 3 — Kompozisyon (`>>`)

**Seçim:** `__rshift__` yalnızca `Transform`'lar arasında çalışır. `Source` ve
`Sink` zincirin dışında, `Pipeline`'a parametre olarak verilir.

```python
hat = Pipeline(
    kaynak=CsvSource("girdi.csv"),
    donusum=temizle >> dogrula >> zenginlestir,
    hedef=SqliteSink("cikti.db"),
)
rapor = hat.calistir()
```

`a >> b` ifadesi `a.__rshift__(b)` çağrısına dönüşüyor ve **yeni bir Transform**
döndürüyor. Yani `a >> b >> c` tek bir nesne. Bu, Hafta 2'de `Kutu[T].esle`
ile yaptığım kompozisyonun aynısı.

**Reddedilen:** `Source >> Transform >> Sink` zinciri. Daha akıcı okunurdu ama
`>>` operatörünün üç farklı tip kombinasyonunu ele alması gerekirdi
(Source→Transform, Transform→Transform, Transform→Sink) ve her birinin dönüş
tipi farklı olurdu. Tek sorumluluk daha temiz.

---

## Karar 4 — Hata yönetimi

**Seçim:** Bağlam nesnesi (`Rapor`) akışla birlikte taşınır.

```python
class Transform:
    def __call__(self, akis: Iterator[Record], rapor: Rapor) -> Iterator[Record]:
        return self._fn(akis, rapor)

    def __rshift__(self, other: "Transform") -> "Transform":
        return Transform(lambda akis, rapor: other(self(akis, rapor), rapor))
```

Satır seviyesindeki bir fonksiyon hata fırlatırsa, yükseltici sarmalayıcı onu
yakalar, `rapor.reddet(kayit, hata)` çağırır ve akış devam eder.

**dead_letter formatı** — JSONL, her satır bir kayıt:

```json
{"kayit": {"id": "3", "yas": "abc"}, "hata": "ValueError: invalid literal for int()", "asama": "dogrula"}
```

Orijinal kayıt olduğu gibi saklanıyor; düzeltip yeniden çalıştırmak mümkün olsun.

**Retry** — Yalnızca `Source` katmanında, ve yalnızca ağ kaynaklarında. Üstel
geri çekilme (`gecikme * 2**deneme`). Transform'larda retry yok: bir dönüşüm
deterministiktir, ikinci denemede de aynı hatayı verir.

**Reddedilenler:**

- **Rapor'u Transform kurulurken vermek** — İmza tek parametreli kalırdı. Ama
  transform'lar hat çalışmadan önce kuruluyor; aynı transform nesnesini iki
  farklı çalıştırmada kullanamazdım.
- **Bozuk satırı akışta özel bir işaretle taşımak** — Esnek olurdu, `Pipeline`
  sonda ayıklardı. Ama her transform'un o işareti tanıyıp atlaması gerekirdi;
  unutulan bir yerde işaret veri sanılırdı.

**Bedeli:** İmza iki parametreli. Karşılığında gizli global durum yok, hangi
raporun kullanıldığı çağrı yerinden okunuyor.

---

## Karar 5 — stdlib sınırı

**Seçim:** `core/` saf stdlib, `cli.py` bağımlılık kullanabilir.

**Gerekçe:** "Sadece stdlib" kuralı kütüphanenin özü için anlamlı — çekirdeği
kimse bir bağımlılık zinciri yüklemeden kullanabilmeli. CLI ve config okuma
ise kabuktur; orada `typer` çok daha az kodla daha iyi bir arayüz veriyor.

Somut sınır: `src/mini_etl/core/` içindeki hiçbir dosyada harici import yok.
Bunu bir testle zorunlu kılacağım (aşağıda).

**Reddedilenler:**

- **Her şey saf stdlib** — `argparse` + `tomllib` ile mümkündü ve "bu kütüphane
  hiçbir şeye bağımlı değil" güçlü bir cümle olurdu. Ama `argparse` typer'dan
  çok daha fazla kod ister ve ödev açıkça `typer` + `pipeline.yaml` istiyor.
- **Serbest** — Ödevin lafzına birebir uyardı ama "sadece stdlib" kuralı
  tamamen kırılırdı ve çekirdek de bağımlılık taşırdı.

---

## Test stratejisi

### 1. Source nasıl test edilir

**Dosya tabanlı kaynaklar (`CsvSource`, `JsonlSource`):** `pytest`'in `tmp_path`
fixture'ı her teste temiz bir geçici klasör veriyor. Küçük bir CSV yazıp okuyorum.
Gerçek dosya kullanmamın sebebi, ayrıştırma davranışının (başlık satırı, tırnak,
alan içi virgül) sahte akışla test edilememesi — Hafta 1'de `cut`'ın alan içi
virgülde bozulduğunu görmüştüm, o hatayı burada yakalamak istiyorum.

**`HttpSource`:** Gerçek ağ isteği atmıyorum. Bunun yerine kaynağa **getirici
fonksiyonu dışarıdan veriyorum** (bağımlılık enjeksiyonu):

```python
HttpSource(url, getirici=sahte_getirici)
```

Testte `sahte_getirici` önce iki kez hata fırlatıp sonra veri döndürüyor —
böylece retry mantığını gerçek ağ olmadan doğruluyorum. `monkeypatch` da
kullanılabilirdi ama enjeksiyon daha açık: bağımlılık imzada görünüyor.

**`conftest.py`** içine ortak fixture'lar: örnek CSV üreten `ornek_csv`,
sahte kaynak üreten `sahte_kaynak`.

### 2. Hata yolu nasıl test edilir

Üç satırlık girdi, ortadaki bozuk:

```
id,yas
1,30
2,abc      ← int'e çevrilemez
3,25
```

Beklentiler:
- Sink'e **2 satır** yazılmış
- `rapor.okunan == 3`, `rapor.yazilan == 2`, `rapor.reddedilen == 1`
- `dead_letter` dosyasında **1 kayıt** var ve içinde orijinal satır
  (`{"id": "2", "yas": "abc"}`) ile hata mesajı geçiyor
- **Akış durmadı** — 3. satır işlendi

Son madde en önemlisi: hata izolasyonunun asıl iddiası bu.

### 3. Bellek iddiası nasıl ölçülür

"5 GB'ı 200 MB'da işler" CI'da test edilemez. İddiayı ölçülebilir hale
getirmenin yolu **mutlak bellek yerine ölçekleme davranışına** bakmak:

`tracemalloc` (stdlib) ile tepe bellek kullanımını iki farklı girdi boyutunda
ölçüyorum — N satır ve 10N satır. Akış gerçekten tembelse tepe bellek **sabit
kalmalı**, 10 kat artmamalı:

```python
assert tepe_10n < tepe_n * 2  # sabit sayılır
```

İkinci bir test, tembelliği doğrudan kanıtlıyor: kaynak olarak **sonsuz** bir
generator veriyorum ve hattan `islice` ile ilk 5 satırı alıyorum. Hat sonlanıyorsa
akışı hiçbir noktada tamamen tüketmiyor demektir. Hafta 2'deki `test_tembellik`in
hat ölçeğindeki hali.

README'ye girecek grafik bu ölçümden çıkacak: x ekseni girdi satır sayısı,
y ekseni tepe bellek.

### 4. hypothesis ile değişmezler

Property-based test, tek tek örnek yerine **her zaman doğru olması gereken
kuralları** test eder. Üçünü seçtim:

| Değişmez | Neden bu |
|---|---|
| `len(filtrele(f)(akis)) <= len(akis)` | Filtre satır ekleyemez. Bir gün filtrenin yanlışlıkla kayıt çoğaltması, bu testle anında yakalanır. |
| `len(esle(f)(akis)) == len(akis)` | Eşleme satır sayısını korumalı. Hata izolasyonu eklerken yanlışlıkla satır düşürmek kolay bir hata — bu test onu yakalar. |
| `(a >> b)(akis) == b(a(akis))` | Kompozisyonun tanımı bu. `__rshift__` implementasyonunun doğruluğunu tek bir kuralla kanıtlıyor. |

Örnek tabanlı testler benim düşündüğüm durumları kontrol ediyor; property
testleri **düşünmediğim** durumları arıyor. İkisi farklı işler.

### 5. Mimari kuralın testi

Karar 5'teki "çekirdek saf stdlib" bir iddia; testle zorunlu kılıyorum:
`core/` altındaki her `.py` dosyasının import satırlarını okuyup stdlib dışı
bir modül geçip geçmediğine bakan bir test. Kural dokümanda kalırsa bir gün
ihlal edilir; testte olursa edilemez.

---

## Modül yapısı

```
src/mini_etl/
├── core/
│   ├── record.py     Record tip takma adı, Rapor sınıfı
│   ├── source.py     Source Protocol + CsvSource, JsonlSource, HttpSource
│   ├── transform.py  Transform sınıfı, __rshift__, esle/filtrele/dogrula fabrikaları
│   ├── sink.py       Sink Protocol + CsvSink, SqliteSink, StdoutSink
│   └── pipeline.py   Pipeline: kaynak + dönüşüm + hedefi birleştirir, Rapor üretir
└── cli.py            typer arayüzü, config okuma

tests/
├── conftest.py       ortak fixture'lar (tmp_path tabanlı örnek dosyalar)
├── test_source.py
├── test_transform.py
├── test_sink.py
├── test_pipeline.py
├── test_hata_yonetimi.py
├── test_bellek.py
├── test_ozellikler.py   hypothesis değişmezleri
└── test_mimari.py       çekirdek saf stdlib mi
```

`Source` ve `Sink` birer `Protocol`; kalıtım şart değil, şekil uyması yeterli.
Testte sahte kaynak yazmak için hiçbir şeyden türetmem gerekmiyor.

---

## Neyi yapmayacağım

- **Paralel çalıştırma.** Akış tabanlı tasarımda paralellik, sıra garantisini
  ve hata izolasyonunu karmaşıklaştırır. Tek işlemcili doğru çalışan bir hat,
  paralel çalışan yanlış bir hattan iyidir. Ödev 2.3'te ayrıca ölçeceğim.
- **Artımlı çalıştırma (checkpoint).** "Kaldığı yerden devam et" özelliği
  durum saklamayı gerektirir; bu, framework'ü bir orkestratöre dönüştürür.
  Kapsam dışı.
- **Şema çıkarımı.** Kayıt tipi olarak `dict` seçtim; şemayı tahmin etmek
  yerine `dogrula` transform'unda açıkça yazmayı tercih ediyorum.
- **Dağıtık çalıştırma.** Spark'ın işi.
- **Gerçek zamanlı kaynaklar (Kafka vb.).** Sonlu akış varsayımı üzerine
  kurulu; `Rapor` işin bitmesini bekliyor.
- **Metrik dışa aktarımı (Prometheus vb.).** `Rapor` bir nesne olarak
  döndürülüyor; onu nereye yazacağı çağıranın işi.
- **Dönüşümlerin geri alınması.** Hat tek yönlü.

## Bilinen sınırlar

- `dict` kullanımı tip güvenliğini çalışma zamanına erteliyor.
- `Transform` imzası iki parametreli; kullanıcı ham akış transform'u yazarken
  `rapor`'u da ele almak zorunda.
- `tekrarsiz_lazy` tarzı durum tutan transform'lar sabit bellekli değil —
  benzersiz değer sayısıyla büyürler. Bunu belgeleyeceğim.
- Bellek testi ölçekleme davranışını ölçüyor, mutlak 200 MB iddiasını değil.

---

## Uygulama sonrası notlar

Bu bölüm, tasarım yazıldıktan sonra uygulama sırasında verilen kararları ve
değişen varsayımları kaydeder. Yukarıdaki kararlar kod yazılmadan önce
alınmıştı; aşağıdakiler koda dokunurken ortaya çıktı.

### Karar 6 — `JsonlSink`, `SqliteSink` ve `HttpSource` yazılmadı

`JsonlSink` yazmak `CsvSink`'in aynısını farklı bir serileştirme ile yazmak
demekti: yeni bir tasarım sorunu çözmüyor, yalnızca genişlik ekliyordu.
`HttpSource` + yeniden deneme mantığı kendi başına ilginç ama bu haftanın
konusu olan akış ve hata yalıtımı ile ilgisi yok.

Haftanın bütçesi genişlik yerine derinliğe ayrıldı: hata yalıtımı, dead letter
dosyası ve ölçülmüş bellek davranışı.

`Sink` ve `Source` protokolleri bunları eklemeyi ucuz tutuyor — yeni bir sınıf,
yaklaşık 15 satır, çekirdekte hiçbir değişiklik yok. Maliyet ertelendi,
biriktirilmedi.

### Karar 7 — CLI'da `argparse`, `typer` değil

Tasarımda "`cli.py` bağımlılık kullanabilir" denmişti. Uygulamada stdlib'deki
`argparse` seçildi.

Gerekçe: arayüz iki konumsal argüman ve üç bayraktan ibaret. `typer`ın
sağladığı kolaylık bu ölçekte ek bağımlılığın maliyetini karşılamıyor.
Kullanıcı `pip install` etmeden çalışması ayrıca değerli.

Reddedilen alternatif: `typer`. Yirmi komutlu, alt komutlu bir araçta tercih
edilirdi.

### Tasarımdan sapmalar

| Ne değişti | Neden |
| --- | --- |
| `Transform.__call__` imzası `(akis)` → `(akis, rapor)` | Karar 4'te öngörülmüştü, Aşama 2'de uygulandı. Kırıcı değişiklik, `feat(core)!` ile işaretlendi. |
| `Transform`a `ad` alanı eklendi | Tasarımda yoktu. `HataKaydi.asama` alanını doldurabilmek için gerekti: bir kaydın hangi adımda reddedildiğini bilmeden hata ayıklamak mümkün değil. |
| CLI'da `--zorunlu` adımı `--sec`ten önce çalışıyor | Ters sırada, seçilmeyen bir sütun zorunlu tutulursa her kayıt `KeyError` alır. Adım sırası sonucu değiştiriyor. |

### Ölçüm: akış iddiası doğrulandı

`scripts/bellek.py`, `tracemalloc` ile tepe belleği ölçüyor.

| Satır | Dosya | Akış | Hepsini belleğe al |
| --- | --- | --- | --- |
| 20.000 | 0.36 MB | 0.23 MB | 10.80 MB |
| 200.000 | 3.98 MB | 0.23 MB | 108.17 MB |

Veri 10 kat arttığında naif yöntemin belleği 10 kat arttı, akışınki değişmedi.
`O(n)` ile `O(1)` arasındaki fark.

Yan bulgu: 3.98 MB'lık ham CSV, Python nesnelerine dönüşünce 108 MB yer
kapladı — 27 katı. Bu oran `dict` ve `str` nesnelerinin kabuk maliyetinden
geliyor ve "dosya küçük, belleğe sığar" tahminlerinin neden yanıldığını
açıklıyor.

### Güncellenmiş bilinen sınırlar

1. **Reddedilen kayıtlar bellekte birikiyor.** `Rapor.hatalar` bir liste; iş
   sonunda dosyaya yazılıyor. Reddedilen oranı yüksekse bellek şişer — yani
   akış garantisi yalnızca *başarılı* kayıtlar için geçerli. Doğru çözüm
   `Rapor`a bir yazıcı enjekte edip hataları anında akıtmak. Bu sürümde
   yapılmadı; tipik iş yükünde reddedilen oranı %1'in altında varsayıldı.
2. **`CsvSink` başlıkları ilk kayıttan alıyor.** Sonraki kayıtlarda farklı
   anahtar varsa `DictWriter` hata verir. Şema değişkenliğine karşı korumasız.
3. **Paralellik yok.** Tek süreç, tek çekirdek. Boru hattı yapısı paralelleşmeye
   uygun ama bu sürümde denenmedi.
