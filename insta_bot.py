"""Instagram için dayanıklı, etkileşimli Selenium yardımcısı."""

from __future__ import annotations

import getpass
import os
import sys
import time
import traceback
from pathlib import Path

try:
    from termcolor import colored
except ImportError:
    def colored(text: str, *_args, **_kwargs) -> str:
        return text

try:
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver import Chrome
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    print("Selenium kurulu değil. Şunu çalıştırın:")
    print(f'"{sys.executable}" -m pip install -r requirements.txt')
    raise SystemExit(1)


WAIT = 25


class InstagramBot:
    def __init__(self, username: str, password: str) -> None:
        self.username = username.strip().lstrip("@")
        self.password = password
        options = ChromeOptions()
        options.add_argument("--disable-notifications")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        try:
            # Selenium Manager uygun Chrome sürücüsünü otomatik yönetir.
            self.browser = Chrome(options=options)
        except WebDriverException:
            driver = Path(__file__).with_name("chromedriver.exe")
            if not driver.exists():
                raise
            service = ChromeService(
                executable_path=str(driver), log_output=os.devnull
            )
            self.browser = Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.browser, WAIT)

    def message(self, text: str, color: str = "cyan") -> None:
        print(colored(text, color))

    def click(self, by: str, selector: str, timeout: int = WAIT) -> None:
        WebDriverWait(self.browser, timeout).until(
            EC.element_to_be_clickable((by, selector))
        ).click()

    def login(self) -> None:
        self.message("Tarayıcı açılıyor...", "yellow")
        self.browser.get("https://www.instagram.com/accounts/login/")
        try:
            self.click(
                By.XPATH,
                "//button[contains(.,'İzin Ver') or contains(.,'Allow all') "
                "or contains(.,'Reddet') or contains(.,'Decline')]",
                5,
            )
        except TimeoutException:
            pass

        # Instagram formu hesaba/bölgeye göre iki farklı alan adı kullanıyor:
        # klasik formda username/password, yeni Meta formunda email/pass.
        username = self.wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input[name='username'],input[name='email']")
            )
        )
        password = self.browser.find_element(
            By.CSS_SELECTOR, "input[name='password'],input[name='pass']"
        )
        username.send_keys(self.username)
        password.send_keys(self.password)
        # Meta'nın yeni formunda submit öğesi görünür olsa da Selenium açısından
        # tıklanabilir bildirilmeyebiliyor. Enter formu doğal yoldan gönderir.
        password.send_keys(Keys.ENTER)

        try:
            WebDriverWait(self.browser, 15).until(
                lambda d: "/accounts/login" not in d.current_url
                or d.find_elements(By.CSS_SELECTOR, "[role='alert']")
            )
        except TimeoutException as exc:
            raise RuntimeError(
                "Giriş tamamlanamadı. Bilgilerinizi ve bağlantınızı kontrol edin."
            ) from exc
        alerts = self.browser.find_elements(By.CSS_SELECTOR, "[role='alert']")
        alert_text = " ".join(item.text.strip() for item in alerts if item.text.strip())

        # İki aşamalı doğrulama bir hata değildir. Instagram bazen kod ekranına
        # geçerken aynı role=alert alanında "Kod girişi doğrulanıyor" gösterir.
        page_text = self.browser.find_element(By.TAG_NAME, "body").text.lower()
        verification_pending = (
            "kod girişi doğrulanıyor" in alert_text.lower()
            or "güvenlik kodu" in page_text
            or "verification code" in page_text
            or "two_factor" in self.browser.current_url
            or "challenge" in self.browser.current_url
        )
        if verification_pending:
            self.message(
                "Doğrulama kodu gerekli. Kodu Chrome penceresinde girip "
                "işlemi tamamlayın.",
                "yellow",
            )
            input("Tarayıcıda doğrulama tamamlanınca burada Enter'a basın...")
            try:
                WebDriverWait(self.browser, 60).until(
                    lambda d: "challenge" not in d.current_url
                    and "two_factor" not in d.current_url
                    and "Kod girişi doğrulanıyor"
                    not in d.find_element(By.TAG_NAME, "body").text
                )
            except TimeoutException as exc:
                raise RuntimeError(
                    "Doğrulama tamamlanmadı. Kodu kontrol edip tekrar deneyin."
                ) from exc
        elif alert_text:
            raise RuntimeError(alert_text)
        self.message("Instagram girişi tamamlandı.", "green")
        for label in ("Şimdi Değil", "Not Now"):
            try:
                self.click(By.XPATH, f"//button[normalize-space()='{label}']", 3)
            except TimeoutException:
                pass

    @staticmethod
    def read_count(prompt: str) -> int:
        while True:
            try:
                value = int(input(prompt).strip())
                if 1 <= value <= 50:
                    return value
            except ValueError:
                pass
            print("Lütfen 1 ile 50 arasında bir sayı girin.")

    def open_people(self, username: str, kind: str) -> None:
        username = username.strip().lstrip("@")
        self.browser.get(f"https://www.instagram.com/{username}/")
        self.wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        body_text = self.browser.find_element(By.TAG_NAME, "body").text.lower()
        if (
            "profil mevcut değil" in body_text
            or "page isn't available" in body_text
            or "sorry, this page isn't available" in body_text
        ):
            raise RuntimeError(
                f"@{username} adlı profil mevcut değil. Kullanıcı adını kontrol edin."
            )

        label = "Takipçiler" if kind == "followers" else "Takip"
        english_label = "Followers" if kind == "followers" else "Following"
        try:
            self.click(
                By.XPATH,
                f"//a[contains(@href,'/{kind}/')]",
                12,
            )
        except TimeoutException:
            self.click(
                By.XPATH,
                f"//*[self::a or self::button]"
                f"[contains(normalize-space(),'{label}') or "
                f"contains(normalize-space(),'{english_label}')]",
                8,
            )
        self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
        )

    def scroll_dialog(self) -> None:
        dialog = self.browser.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        candidates = dialog.find_elements(
            By.XPATH, ".//div[@style and contains(@style,'overflow')]"
        )
        target = candidates[-1] if candidates else dialog
        self.browser.execute_script(
            "arguments[0].scrollTop=arguments[0].scrollHeight", target
        )
        time.sleep(1.5)

    def follow_followers(self) -> None:
        target = input("Takipçileri açılacak kullanıcı: ")
        count = self.read_count("Takip edilecek kişi sayısı (1-50): ")
        self.open_people(target, "followers")
        self.process_buttons(count, ("Takip Et", "Follow"), "kullanıcı takip edildi")

    def process_buttons(
        self, wanted: int, labels: tuple[str, ...], message: str
    ) -> None:
        completed, idle_rounds = 0, 0
        seen: set[str] = set()
        while completed < wanted and idle_rounds < 3:
            progress = False
            for button in self.browser.find_elements(
                By.CSS_SELECTOR, "div[role='dialog'] button"
            ):
                if completed >= wanted:
                    break
                if button.text.strip() not in labels or button.id in seen:
                    continue
                seen.add(button.id)
                try:
                    self.browser.execute_script("arguments[0].click()", button)
                    completed += 1
                    progress = True
                    self.message(f"{completed}. {message}.", "green")
                    time.sleep(3)
                except WebDriverException:
                    continue
            idle_rounds = 0 if progress else idle_rounds + 1
            self.scroll_dialog()
        self.message(f"Toplam {completed} işlem tamamlandı.")

    def unfollow(self) -> None:
        count = self.read_count("Takipten çıkarılacak kişi sayısı (1-50): ")
        self.open_people(self.username, "following")
        completed, idle_rounds = 0, 0
        while completed < count and idle_rounds < 3:
            buttons = self.browser.find_elements(
                By.XPATH,
                "//div[@role='dialog']//button[normalize-space()='Takiptesin' "
                "or normalize-space()='Following']",
            )
            progress = False
            for button in buttons:
                if completed >= count:
                    break
                try:
                    self.browser.execute_script("arguments[0].click()", button)
                    self.click(
                        By.XPATH,
                        "//button[normalize-space()='Takibi Bırak' "
                        "or normalize-space()='Unfollow']",
                        8,
                    )
                    completed += 1
                    progress = True
                    self.message(f"{completed}. kullanıcı takipten çıkarıldı.", "green")
                    time.sleep(3)
                except (TimeoutException, WebDriverException):
                    continue
            idle_rounds = 0 if progress else idle_rounds + 1
            self.scroll_dialog()
        self.message(f"Toplam {completed} kullanıcı takipten çıkarıldı.")

    def like_by_hashtag(self) -> None:
        tag = input("Etiket (# olmadan): ").strip().lstrip("#")
        count = self.read_count("Beğenilecek gönderi sayısı (1-50): ")
        self.browser.get(f"https://www.instagram.com/explore/tags/{tag}/")
        links = self.wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[href*='/p/'],a[href*='/reel/']")
            )
        )
        urls = list(dict.fromkeys(link.get_attribute("href") for link in links))
        completed = 0
        for url in urls:
            if completed >= count:
                break
            self.browser.get(url)
            try:
                self.click(
                    By.XPATH,
                    "//*[name()='svg' and (@aria-label='Beğen' or "
                    "@aria-label='Like')]/ancestor::div[@role='button'][1]",
                    10,
                )
                completed += 1
                self.message(f"{completed}. gönderi beğenildi.", "green")
                time.sleep(3)
            except TimeoutException:
                continue
        self.message(f"Toplam {completed} gönderi beğenildi.")

    def close(self) -> None:
        try:
            self.browser.quit()
        except WebDriverException:
            pass


def main() -> int:
    print(colored("BURAK HOCA INSTAGRAM TAKİP", "green"))
    username = input(colored("Kullanıcı adınız: ", "red")).strip()
    password = getpass.getpass(colored("Şifreniz: ", "red"))
    if not username or not password:
        print("Kullanıcı adı ve şifre boş bırakılamaz.")
        return 1

    bot: InstagramBot | None = None
    try:
        bot = InstagramBot(username, password)
        bot.login()
        actions = {
            "1": bot.follow_followers,
            "2": bot.unfollow,
            "3": bot.like_by_hashtag,
        }
        while True:
            print("\n1- Bir hesabın takipçilerini takip et")
            print("2- Takip edilen kişileri takipten çıkar")
            print("3- Etikete göre gönderi beğen")
            print("0- Çıkış")
            choice = input("Seçiminiz: ").strip()
            if choice == "0":
                return 0
            action = actions.get(choice)
            if action is None:
                print("Geçersiz seçim.")
                continue
            try:
                action()
            except RuntimeError as exc:
                print(colored(f"İşlem yapılamadı: {exc}", "red"))
            except (TimeoutException, WebDriverException):
                print(
                    colored(
                        "Instagram ekranındaki gerekli bölüm bulunamadı. "
                        "Kullanıcı adını ve sayfanın açık olduğunu kontrol edin.",
                        "red",
                    )
                )
    except (RuntimeError, WebDriverException, TimeoutException) as exc:
        message = str(exc).strip() or type(exc).__name__
        print(colored(f"Hata: {message}", "red"))
        try:
            log_path = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
            log_path = log_path.parent / "instagram_bot_hata.log"
            log_path.write_text(traceback.format_exc(), encoding="utf-8")
            print(f"Ayrıntılar kaydedildi: {log_path}")
        except OSError:
            pass
        return 1
    except KeyboardInterrupt:
        print("\nProgram kapatıldı.")
        return 0
    finally:
        if bot is not None:
            bot.close()


if __name__ == "__main__":
    exit_code = main()
    if getattr(sys, "frozen", False):
        try:
            input("\nPencereyi kapatmak için Enter'a basın...")
        except (EOFError, KeyboardInterrupt):
            pass
    raise SystemExit(exit_code)
