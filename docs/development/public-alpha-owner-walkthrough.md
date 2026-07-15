# Public-Alpha Owner Walkthrough

## Amaç ve Sınır

Bu kontrol, Oğuz Koran'ın Delta'nın minimum Public-alpha akışını yayından önce
ürün ve yöntem sahibi olarak incelemesi içindir. Otomatik test değildir, kullanıcı
çalışması değildir ve genel kullanım kolaylığı, öğretilebilirlik veya bilimsel
geçerlilik kanıtı üretmez. Barış Yücesan'ın sonraki structured expert walkthrough'u
bundan ayrı kalır.

Kontrol tek oturumda Upload'dan result export'a kadar bütün akışı izler. İnsan
kararı yalnız görünür dil, yöntem sınırı, yönlendirme ve kabul edilebilir davranış
içindir. R/stylo eşliği, güvenlik ve tarayıcı geometrisi mevcut otomatik kanıtlara
dayanır; owner walkthrough bu testlerin yerine geçmez.

## Oturumdan Önce

1. İncelenen build SHA ve alan adı kaydedilir.
2. Aynı SHA için GitHub `verify` ve `container` işleri yeşil olmalıdır.
3. Release hazırlığını yapan ajan
   `uv run python scripts/build_owner_walkthrough_bundle.py --output build/public-alpha-owner-walkthrough`
   komutuyla hak riski taşımayan deterministik paketi üretir. Oğuz yalnız paketteki
   üç TXT dosyasını yükler; manifest ve checksum dosyaları yüklenmez.
4. Her belge için başlık, birincil yazar, bibliyografik kaynak ve rights state
   önceden hazır tutulur.
5. Tarayıcı geliştirici araçları, sunucu veya terminal kullanımı Oğuz'dan
   beklenmez. Akış yalnız görünür web arayüzünden tamamlanır.

## Adım Adım Kontrol

### 1. Giriş ve Amaç

- Ana ekranda Delta'nın ne yaptığını kendi cümlenizle söyleyin.
- `Text Proximity`, `Group Comparison` ve `Style Over Time` amaçlarının farkını
  görünür açıklamalardan anlayıp anlamadığınızı kaydedin.
- Delta'nın yazarlığı kanıtlamadığını, confidence üretmediğini ve edebi yorumu
  otomatik yazmadığını açıkça bulabilmelisiniz.

**Geçiş ölçütü:** İlk ekranda ne yükleneceği, neden üç amaç olduğu ve aracın neyi
iddia etmediği anlaşılır. Bir terim yalnız teknik jargonla açıklanıyorsa wording
defect açılır.

### 2. Upload ve Corpus Belgeleme

- `Text Proximity` ve `Guided` seçin.
- Üç TXT dosyasını yükleyin.
- Her belge için author, bibliographic citation ve rights state alanlarını
  doldurun.
- Yanlış veya eksik bir alan bırakarak hata mesajının sizi doğru belge ve alana
  yönlendirdiğini kontrol edin; sonra alanı düzeltin.

**Geçiş ölçütü:** Kod, R, Python, shell veya dosya adı hilesi gerekmeden corpus
review ekranına ulaşılır. Hata metni ham metni, sunucu yolunu veya gizli bilgiyi
göstermez.

### 3. Rights ve Corpus Review

- Dosya ile eser eşlemesini ve rights action bilgisini okuyun.
- `Analysis only` seçiminin metni analiz etmeye izin verdiğini, fakat ham metni
  export etmeye izin vermediğini kendi cümlenizle açıklayın.
- Confirmation kutusunu yalnız kayıtlar doğruysa işaretleyin.

**Geçiş ölçütü:** Upload, analysis, result export ve public redistribution
izinlerinin aynı şey olmadığı anlaşılır. Belirsiz rights kaydı sessizce geçmez.

### 4. Preparation ve Corpus Health

- `Prepare texts and check corpus health` işlemini çalıştırın.
- Length, transformation, confound, overlap ve MFW capacity panellerinden en az
  bir uyarıyı okuyun.
- Uyarının corpus'u otomatik olarak temizlemediğini veya sorunu istatistiksel
  olarak gidermediğini açıklayın.

**Geçiş ölçütü:** Blocker ile warning ayrımı anlaşılır; her panelin neyi
göstermediği görünürdür. P007-AC-09 için özellikle warning dili kabul, düzeltme
veya ret gerekçesi kaydedilir.

### 5. Parametreler

- Dört karşılaştırmanın 100, 300, 500 ve 1000 MFW olduğunu doğrulayın.
- MFW'nin analizde en sık geçen kaç özelliğin kullanılacağını belirlediğini
  açıklayın.
- Culling değerinin yüzde 0, analysis unit'in whole text ve ölçünün Classic
  Delta olduğunu bulun.
- 500 MFW'nin yalnız sabit reading reference olduğunu, en iyi ayar olmadığını
  kendi cümlenizle söyleyin.
- `Research` seçeneğinin Public alpha'da neden kilitli olduğunu okuyun.

**Geçiş ölçütü:** Parametreler görünür, fakat sonuç görüldükten sonra değiştirilip
güzel sonuç seçilemez. Corpus 1000 MFW'yi desteklemiyorsa hücre sessizce daha
düşük değere indirilmez.

### 6. Analizi Çalıştırma

- Dört karşılaştırmayı ve interpretation limits metnini inceleyin.
- Confirmation kutusunu işaretleyip analizi başlatın.
- Bekleme, başarısızlık veya tamamlanma durumunun ne olduğunu görünür metinden
  takip edin.

**Geçiş ölçütü:** Tek tıklama birden fazla gizli deney gibi sunulmaz; tam dört
önceden açıklanmış hücre çalışır. Başarısız hücre varsa gizlenmez.

### 7. Sonuçları Okuma

- Overview'da dört hücrenin durumunu kontrol edin.
- 500-MFW reference ile başka bir complete hücre arasında yalnız görünümü
  değiştirin; bu seçimin yeni analiz çalıştırmadığını doğrulayın.
- Distance heatmap, nearest-neighbour table ve 2D map üzerinde aynı work ID'leri
  bulun.
- Yakınlığın yazarlık kanıtı, olasılık, etki, yaşlanma veya olgunlaşma anlamına
  gelmediğini kendi cümlenizle açıklayın.

**Geçiş ölçütü:** Görsel ve semantic table etiketleri aynı eserleri gösterir.
`What this shows` ve `What this does not show` sınırları yorumu frenler, sonucu
edebi hükme dönüştürmez.

### 8. İndirme ve Gizlilik

- Resolved parameter record ve result JSON dosyalarını indirin.
- Dosyalarda parametreler, work kimlikleri, hücre durumları ve sonuç tablolarının
  bulunduğunu; ham veya hazırlanmış metnin bulunmadığını doğrulayın.
- Arayüzün analizi `Analysis complete` olarak gösterdiğini kontrol edin.

**Geçiş ölçütü:** İndirilen sonuç, neyin hesaplandığını incelemeye yeterlidir;
raw text, token stream, feature words, capability, secret veya server path içermez.

### 9. Dar Ekran

- Tarayıcı penceresini yaklaşık telefon genişliğine daraltın.
- Ana akış, tablo kaydırma alanları, düğmeler ve açıklamaların üst üste binmeden
  kullanılabildiğini kontrol edin.

**Geçiş ölçütü:** Metin veya düğme kesilmez; sayfanın tamamı yatay kaymaya
zorlanmaz. Tablo kendi çerçevesinde kayabilir.

## Karar Kaydı

Her adım için yalnız şu sonuçlardan biri yazılır:

- `accepted`: Görünür davranış ve dil owner tarafından kabul edildi.
- `wording defect`: İşlev doğru, açıklama yanlış veya belirsiz.
- `functional defect`: Beklenen görev tamamlanamıyor veya yanlış state oluşuyor.
- `security/privacy blocker`: İçerik, yol, gizli bilgi veya başka oturum verisi
  görünür oldu.
- `method blocker`: Parametre, warning veya sonuç dili desteklenmeyen bilimsel
  iddiaya yöneltiyor.

Her defect için adım numarası, görünür build SHA, tarayıcı, beklenen davranış,
gözlenen davranış ve ekran görüntüsü kaydedilir. Ham corpus metni defect kaydına
kopyalanmaz.

## Aktivasyon Kararı

Minimum Public alpha yalnız şu koşullarda owner tarafından kabul edilebilir:

- Dokuz adımın tamamı yürütülmüş;
- security/privacy blocker ve method blocker sayısı sıfır;
- açık critical veya high functional defect sayısı sıfır;
- P007 warning dili açıkça kabul edilmiş;
- minimum P014 isolation, resource, proxy, health, rollback ve Lemmata smoke
  kapıları aynı release candidate üzerinde geçmiş;
- site açıkça `Public alpha` ve `experimental` olarak etiketlenmiş olmalıdır.

Kabul yalnız incelenen build için geçerlidir. Daha sonraki davranış değişikliği
yeni bir walkthrough veya hedefli retest gerektirir.
