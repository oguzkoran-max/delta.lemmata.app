# ADR-0001: Tool-First Product and Paper

**Durum:** Kabul edildi  
**Tarih:** 2026-07-10  
**Son kullanıcı teyidi:** 2026-07-10, English-only v0.1 ve no-code should not mean no-method tezi

## Bağlam

Delta'nın ilk tartışmalarında De Amicis veya Pinokyo edebî araştırması makalenin başrolüne yerleşebiliyordu. Kullanıcının ana amacı yeni bir edebî vaka makalesinden önce genel kullanıma açık bir DBB tool'u geliştirmek ve bilimsel olarak "bu tool çalışıyor" diyebilmekti.

## Karar

Delta ürün ve makale bakımından tool-first olacaktır. Makale scholar-led tasarım, uncertainty, interpretive guardrails, validation ve FAIR-oriented reproducibility katkılarını inceler.

v0.1 arayüzü, lda.lemmata.app ile ürün ailesi tutarlılığı ve daha dar QA kapsamı için yalnız İngilizce olacaktır. Uygulama metinleri kod içine dağılmayacak; sonraki Türkçe ve İtalyanca yerelleştirme için merkezi bir metin kataloğuna hazır tasarlanacaktır.

Makalenin ana tezi şudur: no-code erişim tek başına yöntemsel yeterlilik değildir. Delta, corpus confounds, parameter sensitivity, interpretive limits ve reproducibility öğelerini sonuç ekranının ve export'un zorunlu parçaları haline getirir.

Pinokyo yalnız worked example'dır. De Amicis, Delta ile üretilebilecek sonraki edebiyat merkezli ve TÜBİTAK bağlantılı bağımsız çıktı olarak korunur.

AI-assisted development ana ürün katkısı veya başlık değildir. ADR-0008'de tanımlanan scholarly vibe coding, provenance coverage yeterliyse ikincil ve refleksif development case; yetersizse yöntem/disclosure bilgisi olarak kalır.

## Sonuçlar

- Makale başlığı Pinokyo veya De Amicis üzerine kurulmaz.
- Pinokyo bölümü yaklaşık %10-15 ile sınırlanır.
- Makale araç özelliklerini öven tanıtım yazısı değil, kanıtlı bir tool evaluation olur.
- v0.1'de pedagogical gain, general usability veya ease iddiası kurulmaz; daha geniş kullanıcı çalışması ayrı bir sonraki araştırmadır.
- Desteklenen akışlara başlamak için önce R/Python öğrenmek veya kod yazmak gerekmediği söylenebilir; bu cümle pedagogical gain ya da general ease claim'i değildir.
- v0.1'de dil seçici bulunmaz; bütün kullanıcı akışı İngilizce test edilir.

## Reddedilen Alternatifler

- De Amicis coğrafya sorusunu makalenin ana tezi yapmak
- Pinokyo sürüm araştırmasını makalenin ana tezi yapmak
- SVC'yi ikinci kez ana kuramsal katkı yapmak
