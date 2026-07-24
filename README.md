<h1 align="center">Burak Hoca Instagram Takipçi Paneli</h1>

<p align="center">
  <img src="burakhoca_instagram_icon.png" alt="Burak Hoca Instagram Takipçi Paneli" width="220">
</p>

<p align="center">
  <strong>Instagram takipçi listelerini düzenlemek ve kontrollü şekilde işlemek için geliştirilmiş Windows masaüstü uygulaması.</strong>
</p>

## Uygulama Hakkında

Burak Hoca Instagram Takipçi Paneli; Python, Selenium ve Tkinter kullanılarak geliştirilmiştir. Kullanıcı Instagram’a Chrome üzerinden normal şekilde giriş yaptıktan sonra uygulama, açılan takipçiler listesini algılar ve seçilen kullanıcıları işlem tablosuna aktarır.

Programın varsayılan dili Türkçedir.

## Temel Özellikler

- Açılan Instagram takipçiler penceresini otomatik algılama
- Belirlenen sayıda kullanıcıyı uygulama listesine aktarma
- Takipçiler penceresi erken kapatılırsa mevcut listeyle devam etme
- Kullanıcı profillerini Chrome’da sırayla açma
- İşlemler arasında ayarlanabilir saniye aralığı
- Canlı geri sayım ve ilerleme çubuğu
- `Bekliyor`, `Takip edildi`, `Atlandı` ve `Deneme` durumları
- Duraklatma ve kaldığı yerden devam etme
- Açık Chrome ve Instagram oturumunu tekrar kullanma
- Program yeniden açıldığında önceki listeyi geri yükleme

## Liste Yönetimi

- Kullanıcı adına göre arama
- Duruma göre filtreleme
- Sağ tık ile seçili kullanıcıyı silme
- Klavyedeki `Delete` tuşuyla kullanıcı silme
- Tüm listeyi onay alarak temizleme
- Başarısız işlemleri tekrar kuyruğuna alma
- Aynı kullanıcıyı tekrar işlemeyi önleme
- CSV dosyasından kullanıcı aktarma
- Listeyi CSV olarak dışa aktarma
- Kullanıcıya çift tıklayarak profili Chrome’da açma

## Güvenlik ve Kontrol

- Günlük işlem limiti
- En fazla 50 kişilik işlem sınırı
- Gerçek tıklama yapmadan akışı kontrol etmek için deneme modu
- Hata oluştuğunda tanılama raporu ve ekran görüntüsü
- Oturum ve işlem geçmişini yerel bilgisayarda saklama
- Ham ChromeDriver hataları yerine anlaşılır kullanıcı mesajları

> Instagram’ın kullanım koşullarına, işlem sınırlarına ve topluluk kurallarına uymak kullanıcının sorumluluğundadır.

## Arayüz Özellikleri

- Instagram, gece ve açık tema
- Açık temada koyu ve okunaklı yazılar
- Canlı işlem günlüğü
- Listeye alınan, takip edilen ve atlanan kullanıcı sayaçları
- Sistem tepsisine küçültme
- İşlem tamamlandığında masaüstü bildirimi
- Özgün mor–pembe kamera ikonu

## PC Otomatik Kapatma

Program Windows’un kendi kapatma zamanlayıcısını kullanır.

- Belirlenen dakika sonra bilgisayarı kapatma
- `23:30` gibi belirli bir saatte bilgisayarı kapatma
- Planlamadan önce güvenlik onayı
- Aktif kapatma planını iptal etme
- Planlanan tarih ve saati arayüzde gösterme

## Sistem Gereksinimleri

- Windows 10 veya Windows 11
- 64-bit işletim sistemi
- Google Chrome
- İnternet bağlantısı

Python, Selenium, Pillow, Pystray ve diğer gerekli Python bileşenleri hazır EXE ve Setup paketinin içinde bulunur.

## Setup ile Kurulum

Hazır kurulum paketi:

```text
setup/BurakHoca_InstagramPaneli_Setup.exe
```

Setup paketi:

- Uygulamayı Program Files klasörüne kurar
- Masaüstü ve Başlat menüsü kısayollarını oluşturur
- İsteğe bağlı olarak Windows başlangıcına ekler
- Kaldırma desteği sağlar
- Google Chrome bulunamazsa kullanıcıyı bilgilendirir

## Kaynak Koddan Çalıştırma

Gerekli paketleri kurun:

```powershell
python -m pip install -r requirements.txt
```

Uygulamayı başlatın:

```powershell
python takipci_masaustu.py
```

## EXE Oluşturma

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --collect-all selenium `
  --collect-all pystray `
  --icon burakhoca_instagram_icon.ico `
  --add-data "burakhoca_instagram_icon.ico;." `
  --name BurakHoca_InstagramPaneli `
  takipci_masaustu.py
```

Oluşturulan dosya:

```text
dist/BurakHoca_InstagramPaneli.exe
```

## Kullanım

1. Programı açın.
2. Takip edilecek kişi sayısını ve işlem aralığını belirleyin.
3. `Tarayıcıyı Aç ve Başlat` düğmesine basın.
4. Chrome’da Instagram’a giriş yapın.
5. İşlem yapmak istediğiniz profilin takipçiler penceresini açın.
6. Program kullanıcıları kendi tablosuna aktarır.
7. Liste tamamlandığında veya takipçiler penceresi kapatıldığında mevcut kullanıcılarla işlem başlar.

## Veri ve Gizlilik

Oturum bilgileri, işlem geçmişi, CSV verileri ve tanılama dosyaları kullanıcının bilgisayarında saklanır. Uygulama kullanıcı adı veya şifreyi kendi arayüzünde istemez; Instagram girişi doğrudan Chrome üzerinden yapılır.

## Kullanılan Teknolojiler

- Python
- Selenium
- Tkinter / ttk
- Pillow
- Pystray
- PyInstaller
- Inno Setup
- JavaScript

## Burak Hoca

- **Geliştirici:** Burak ÖZKAN
- **Instagram:** [@Burakhocafen](https://www.instagram.com/burakhocafen/)
- **Web:** [www.burakhoca.com](https://www.burakhoca.com)
- **Telefon / WhatsApp:** [0552 219 87 87](https://wa.me/905522198787)

## Lisans

Lisans ayrıntıları için [LICENSE](LICENSE) dosyasını inceleyebilirsiniz.
