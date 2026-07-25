<h1 align="center">Burak Hoca Instagram Paneli</h1>

<p align="center">
  <img src="burakhoca_instagram_icon.png" alt="Burak Hoca Instagram Paneli" width="220">
</p>

<p align="center">
  <strong>Takipçi listesi işleme ve zamanlanmış gönderi yönetimini tek masaüstü uygulamasında birleştiren Windows paneli.</strong>
</p>

## Güncel Sürüm

**v3.4.0**

Uygulama açılışta iki çalışma alanı sunar:

1. **Takipçi Otomasyonu**
2. **Instagram Yönetim Sistemi**

Her iki ekrandan da güvenli biçimde ana menüye dönülebilir. Pencereler farklı ekran çözünürlüklerine uyum sağlar; yanlışlıkla tam ekran veya büyütülmüş moda geçirilmesi engellenmiştir.

## Takipçi Otomasyonu

- Chrome üzerinden açılan Instagram takipçi listesini algılama
- Seçilen kullanıcıları otomatik olarak işlem listesine aktarma
- Takipçiler penceresi erken kapatılırsa alınan mevcut listeyle devam etme
- Kullanıcı profillerini sırayla açıp işleme
- **1–100.000** arası kişi sayısı
- **10–600 saniye** arası gerçek işlem aralığı
- Canlı geri sayım, ilerleme çubuğu ve işlem günlüğü
- Duraklatma, devam ettirme ve güvenli durdurma
- Program kapatılıp açıldığında bekleyen listeyi geri yükleme
- Daha önce işlenen kullanıcıları tekrar işlemeyi önleme
- Günlük işlem limiti
- Tıklama yapmadan akışı sınamak için deneme modu

### Liste Yönetimi

- Kullanıcı adına göre arama
- Duruma göre filtreleme
- Sağ tık menüsü veya `Delete` tuşuyla tek kullanıcı silme
- Tüm listeyi onay alarak temizleme
- Başarısız işlemleri yeniden deneme
- CSV dosyasından kullanıcı aktarma
- Listeyi CSV dosyasına aktarma
- Kullanıcıya çift tıklayarak profili Chrome’da açma

### PC Otomatik Kapatma

- Belirlenen dakika sonra bilgisayarı kapatma
- Belirli bir saatte kapatma (`23:30` gibi)
- Planlamadan önce kullanıcı onayı
- Aktif kapatma planını iptal etme
- Planlanan zamanı panelde gösterme

## Instagram Yönetim Sistemi

- Bilgisayardan görsel seçme ve önizleme
- Gönderi açıklaması hazırlama ve karakter sayacı
- Tanıtım metni şablonu
- Etiket önerileri
- Gönderiyi hemen paylaşma
- Tarih ve saat belirleyerek yayın kuyruğuna ekleme
- Bekleyen, yayınlanan ve başarısız gönderi sayaçları
- Kuyruktaki içeriği yeniden editöre alma
- Seçili kaydı silme
- Başarısız yayınları yeniden deneme
- Kalıcı Chrome profili sayesinde açık Instagram oturumunu kullanma

> **Hikâye paylaşımı devre dışıdır.** Instagram web arayüzündeki kısıtlamalar nedeniyle güvenilir çalışmadığı için panel yalnızca gönderi yayınlar.

Planlanan yayınların çalışması için program ve bilgisayar yayın saatinde açık olmalıdır. İlk kullanımda `Chrome'u Aç` düğmesiyle açılan tarayıcıdan Instagram hesabına giriş yapılmalıdır.

## Güvenlik ve Gizlilik

- Instagram kullanıcı adı ve şifresi uygulama arayüzünde istenmez.
- Giriş işlemi doğrudan Chrome ve Instagram üzerinde yapılır.
- Chrome oturumu ve kuyruk verileri yalnızca yerel kullanıcı profilinde tutulur.
- Hata raporlarında tam sayfa HTML veya ekran görüntüsü saklanmaz.
- Kısa hata kayıtlarından Windows kullanıcı yolu, URL sorguları ve tam medya yolu ayıklanır.
- Haricî komutlar kabuk metniyle değil, sabit parametre listeleriyle çalıştırılır.
- Uygulama verileri Git deposuna ve kurulum paketine eklenmez.

Yerel çalışma verileri genel olarak şu klasörde saklanır:

```text
%LOCALAPPDATA%\BurakHocaInstagramPaneli
```

Bu klasörde yayın kuyruğu ve Instagram için ayrılmış Chrome profili bulunabilir. Bilgisayardaki Windows hesabına erişimi olan kişiler bu verilere erişebileceği için kullanıcı hesabınızı parola ile koruyun.

> Otomatik işlemleri kullanırken Instagram’ın kullanım koşullarına, topluluk kurallarına ve hesap sınırlarına uymak kullanıcının sorumluluğundadır. Yoğun otomasyon hesap kısıtlamasına yol açabilir.

## Sistem Gereksinimleri

- Windows 10 veya Windows 11
- 64-bit işletim sistemi
- Güncel Google Chrome
- İnternet bağlantısı

Hazır EXE ve Setup paketinde Python ile gerekli uygulama kütüphaneleri bulunur. Chrome yine bilgisayarda kurulu olmalıdır.

## Setup ile Kurulum

Hazır kurulum paketi:

```text
setup\BurakHoca_InstagramPaneli_Setup.exe
```

Setup:

- Uygulamayı `Program Files` altına kurar
- Başlat menüsü kısayolu oluşturur
- İsteğe bağlı masaüstü kısayolu oluşturur
- İsteğe bağlı Windows başlangıç kısayolu sunar
- Kaldırma desteği sağlar
- Chrome bulunamazsa kullanıcıyı bilgilendirir

## Kurulumsuz EXE

```text
dist\BurakHoca_InstagramPaneli.exe
```

EXE tek dosyadır. İlk açılış, paket geçici olarak hazırlandığı için birkaç saniye sürebilir.

## Kaynak Koddan Çalıştırma

Python 3.12 veya daha yeni bir 64-bit Python sürümü önerilir.

```powershell
python -m pip install -r requirements.txt
python takipci_masaustu.py
```

Selenium Manager uygun Chrome sürücüsünü gerektiğinde otomatik olarak yönetir; ayrıca `chromedriver.exe` indirip proje klasörüne koymak gerekmez.

## EXE Derleme

Projede bulunan PyInstaller yapılandırmasını kullanın:

```powershell
python -m PyInstaller --noconfirm --clean BurakHoca_InstagramPaneli.spec
```

Oluşan dosya:

```text
dist\BurakHoca_InstagramPaneli.exe
```

## Setup Derleme

Inno Setup 6 kurulduktan sonra:

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" `
  "BurakHoca_InstagramPaneli_Setup.iss"
```

Oluşan dosya:

```text
setup\BurakHoca_InstagramPaneli_Setup.exe
```

## Kullanılan Teknolojiler

- Python
- Tkinter / ttk
- Selenium
- Pillow
- Pystray
- PyInstaller
- Inno Setup

## İletişim

- **Geliştirici:** Burak ÖZKAN
- **Instagram:** [@burakhocafen](https://www.instagram.com/burakhocafen/)
- **Web:** [www.burakhoca.com](https://www.burakhoca.com)
- **Telefon / WhatsApp:** [0552 219 87 87](https://wa.me/905522198787)

## Lisans

Lisans ayrıntıları için [LICENSE](LICENSE) dosyasını inceleyebilirsiniz.
