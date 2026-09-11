# mini-etl

CSV, JSONL ve HTTP kaynaklarını **akış hâlinde** okuyup dönüştüren, bozuk
kayıtları işi durdurmadan kenara ayıran küçük bir ETL kütüphanesi.

`mini_etl.core` yalnızca Python standart kütüphanesini kullanır.

## Ne yapar

- **Akış hâlinde çalışır.** Dosyanın tamamı belleğe alınmaz; bellek kullanımı
  dosya boyutundan bağımsızdır.
- **Bozuk kayıt işi öldürmez.** Hata veren satır reddedilir, sebebi ve hangi
  aşamada olduğu kaydedilir, akış kalan kayıtlarla devam eder.
- **Elemek ile reddetmek ayrılır.** Koşulu sağlamayan kayıt elenir (normal iş);
  koşulun kendisi patlarsa kayıt reddedilir (arıza). Rapor ikisini ayrı sayar.
- **Boru hattı veri olarak tanımlanabilir.** YAML dosyasıyla, kod yazmadan.

## Bileşenler

| Kaynak | Ne yapar |
| --- | --- |
| `CsvSource` | CSV dosyasını satır satır okur |
| `JsonlSource` | Her satırı bir JSON nesnesi olan dosyayı okur |
| `HttpSource` | HTTP uç noktasından JSON okur; geçici hatalarda (`429`, `5xx`, ağ) yeniden dener, `4xx`'te durur, `Retry-After`'a uyar |

| Dönüşüm | Ne yapar |
| --- | --- |
| `esle(f)` | Her kayda `f` uygular |
| `filtrele(kosul)` | Koşulu sağlamayanları **eler** |
| `dogrula(kosul, mesaj)` | Koşulu sağlamayanları **reddeder** |
| `yeniden_adlandir(esleme)` | Sütun adlarını değiştirir; çakışmayı reddeder |
| `tip_cevir(alanlar)` | Alanları verilen fonksiyonla çevirir |

Dönüşümler `>>` ile zincirlenir: `dogrula(...) >> tip_cevir(...)`

| Hedef | Ne yapar |
| --- | --- |
| `CsvSink` | CSV dosyasına yazar |
| `SqliteSink` | SQLite tablosuna parçalar hâlinde yazar |
| `StdoutSink` | JSONL olarak `stdout`'a yazar |

## Kurulum

```bash
uv sync --all-extras
```

## Kütüphane olarak

```python
from mini_etl.core.pipeline import Pipeline
from mini_etl.core.sink import CsvSink
from mini_etl.core.source import CsvSource
from mini_etl.core.transform import dogrula, tip_cevir

rapor = Pipeline(
    kaynak=CsvSource("girdi.csv"),
    hedef=CsvSink("cikti.csv"),
    donusum=dogrula(lambda k: k["id"] != "", "id bos olamaz") >> tip_cevir({"yas": int}),
    hata_dosyasi="hatalar.jsonl",
).calistir()

print(rapor.okunan, rapor.yazilan, rapor.reddedilen)
```

Reddedilen kayıtlar `hatalar.jsonl` dosyasına satır satır yazılır:

```json
{"kayit": {"id": "2", "yas": "abc"}, "hata": "ValueError: ...", "asama": "tip_cevir"}
```

Dosya yalnızca en az bir kayıt reddedilirse oluşturulur.

## YAML yapılandırma

```yaml
kaynak:
  tur: csv          # csv | jsonl | http
  yol: girdi.csv

donusumler:         # listede yazıldığı sırayla uygulanır
  - tur: zorunlu
    sutun: yas
  - tur: yeniden_adlandir
    esleme:
      ad: isim
  - tur: tip_cevir
    alanlar:
      yas: int      # int | float | str | bool

hedef:
  tur: stdout       # csv | sqlite | stdout

hatalar: bozuk.jsonl
```

```bash
uv run python -m mini_etl.cli --config pipeline.yaml
```

Yapılandırma **veri** olarak okunur: `yaml.safe_load` kullanılır ve tip
çeviriciler `eval` yerine bir beyaz listeden çözülür.

## Komut satırı

```bash
uv run python -m mini_etl.cli girdi.csv cikti.csv --zorunlu yas --sec id,ad
```

| Seçenek | Ne yapar |
| --- | --- |
| `--config p.yaml` | Boru hattını YAML dosyasından kurar |
| `--sec ad,yas` | Yalnızca bu sütunları tutar |
| `--zorunlu yas` | Bu sütunu boş olan kayıtları eler |
| `--hatalar h.jsonl` | Reddedilen kayıtları bu dosyaya yazar |
| `--log-seviye` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--duz-log` | JSON yerine insan okunabilir günlük |

Çıkış kodları:

| Kod | Anlamı |
| --- | --- |
| `0` | İş tamam, reddedilen yok |
| `1` | İş tamam, bazı kayıtlar reddedildi |
| `2` | Kurulum hatası — iş hiç başlamadı |

## Günlükleme

Günlükler `stderr`'e yazılır. Varsayılan biçim tek satırlık JSON:

```json
{"zaman": "...", "seviye": "INFO", "mesaj": "bitti", "okunan": 3, "yazilan": 2}
```

Kütüphane olarak kullanıldığında günlükçü sessizdir; açmak için:

```python
from mini_etl.gunluk import kur

kur(seviye="DEBUG")
```

`DEBUG` seviyesinde her reddedilen kayıt ayrı ayrı görünür.

## Bellek davranışı

`scripts/bellek.py` aynı işi iki yöntemle yapar ve her yöntemi **iki bağımsız
araçla** ölçer:

- `tracemalloc` — yalnızca Python nesneleri, yalnızca bu süreç
- `ru_maxrss` — işletim sisteminin gördüğü gerçek tepe bellek

Her yöntem **ayrı bir süreçte** çalışır: `ru_maxrss` sürecin tüm ömrü için bir
yüksek-su işaretidir, aynı süreçte iki yöntem ölçülemez.

| Satır | Dosya | Akış · tracemalloc | Akış · RSS | Liste · tracemalloc | Liste · RSS |
| --- | --- | --- | --- | --- | --- |
| 20.000 | 0.36 MB | **0.22 MB** | 17.4 MB | 10.80 MB | 45.1 MB |
| 200.000 | 3.98 MB | **0.22 MB** | 17.5 MB | 108.17 MB | 288.3 MB |

**Ana bulgu:** veri 10 kat arttığında naif yöntemin belleği 10 kat arttı;
akışınki **değişmedi** — ve bu, iki aracın ikisinde de böyle görünüyor. Fark
bir yüzde farkı değil, karmaşıklık farkı: `O(n)` yerine `O(1)`.

**İkinci bulgu:** iki araç aynı sonuca varıyor ama aynı sayıyı vermiyor. İki
yöntem arasındaki fark `tracemalloc`'a göre 108 MB, `ru_maxrss`'e göre 271 MB.
`tracemalloc` gerçeğin yaklaşık **%40'ını** gösteriyor ve bu oran her iki
ölçekte de aynı — sabit bir ek yük değil, orantılı bir sapma.

Sebep: `tracemalloc` *istenen* baytları sayar, işletim sistemi *ayrılan
sayfaları* verir. Aradaki fark pymalloc'un boyut sınıfına yuvarlamasından,
1 MB'lık arena tanesinden (bir arena ancak tamamen boşalınca geri verilir) ve
parçalanmadan geliyor.

Pratik sonuç: `tracemalloc` iki yaklaşımı **karşılaştırmak** için doğru araç,
**kapasite planlaması** için değil. Saf Python kodunda 2.5 kat iyimser;
`polars` gibi Rust tabanlı bir kütüphanede sapma 148 kata çıkıyor
([ölçüm](https://github.com/KumruCelik/perf-lab/blob/main/LOG.md)).

`ru_maxrss`'te **oran** değil **fark** okunmalı: 17.4 MB'lık taban (yorumlayıcı
ve modüller) her iki yöntemde de var ve oranı bastırıyor.

Kendin ölçmek için:

```bash
uv run python scripts/bellek.py --satir 500000
```

## Tasarım

Tasarım kararları, reddedilen alternatifler ve gerekçeleri
[DESIGN.md](DESIGN.md) dosyasında.

## Bilinen sınırlar

- Reddedilen kayıtlar bellekte biriktirilip iş sonunda yazılır. Akış garantisi
  yalnızca **başarılı** kayıtlar için geçerli.
- `HttpSource` yanıtın tamamını belleğe alır; akış garantisi taşımaz.
- Yeniden denemede jitter yok (thundering herd riski).
- `CsvSink` ve `SqliteSink` sütunları **ilk kayıttan** alır. Sonraki kayıtlarda
  farklı anahtarlar varsa yazım hata verir.
- Paralellik yok: tek süreç, tek çekirdek.

## Testler ve kapsam

Kapsam eşiği `pyproject.toml`'da **%98** olarak sabitlenmiş; eşiğin altına düşen
bir değişiklik testleri kırar. Böylece rakam bir iddia olmaktan çıkıp garanti
oluyor.

Kapsam dışında kalan tek yer `_http_getir`'in gövdesi: gerçek bir ağ isteği
yapıyor ve testlerde her zaman sahte bir `getir` enjekte ediliyor. Bu satırlar
`# pragma: no cover` ile **gizlenmedi** — kapsam dışına almak, o satırların bir
daha asla sorgulanmayacağı anlamına gelir. Fonksiyon ileride büyürse eklenen
her satır sessizce denetim dışında kalırdı.

`__main__` blokları hariç tutuldu: pytest modülü import ettiği için o satırlar
tasarım gereği çalışamaz.

## Geliştirme

```bash
make install   # bağımlılıklar
make lint      # ruff check + ruff format --check + mypy
make test      # pytest + kapsam
```

`make lint` yerelde CI ile birebir aynı kontrolleri çalıştırır.
