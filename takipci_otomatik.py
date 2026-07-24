"""Kullanıcının açtığı Instagram takipçi listesini sırayla takip eder."""

from __future__ import annotations

import random
import sys
import time
import traceback
from pathlib import Path

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def read_count() -> int:
    while True:
        try:
            value = int(input("Kaç kişi takip edilsin? (1-10000): ").strip())
            if 1 <= value <=10000:
                return value
        except ValueError:
            pass
        print("Lütfen 1 ile 10000 arasında bir sayı gir.")


def find_scroll_area(browser: Chrome, dialog):
    return browser.execute_script(
        """
        const root = arguments[0];
        const items = [...root.querySelectorAll('div')]
          .filter(x => x.scrollHeight > x.clientHeight + 40);
        items.sort((a, b) => b.scrollHeight - a.scrollHeight);
        return items[0] || root;
        """,
        dialog,
    )


def follow_from_open_dialog(browser: Chrome, wanted: int) -> int:
    print("\nİstediğin profilin takipçilerine tıkla.")
    print("Takipçi listesi açılınca program otomatik başlayacak...")
    dialog = WebDriverWait(browser, 600).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
    )

    completed = 0
    seen_profiles: set[str] = set()
    empty_rounds = 0

    while completed < wanted and empty_rounds < 8:
        progress = False
        buttons = dialog.find_elements(By.TAG_NAME, "button")

        for button in buttons:
            if completed >= wanted:
                break
            try:
                if button.text.strip().casefold() not in {"takip et", "follow"}:
                    continue

                row = button.find_element(
                    By.XPATH,
                    "./ancestor::div[.//a[contains(@href,'/')]][1]",
                )
                links = row.find_elements(By.CSS_SELECTOR, "a[href]")
                profile = next(
                    (
                        link.get_attribute("href")
                        for link in links
                        if link.get_attribute("href")
                        and "/explore/" not in link.get_attribute("href")
                    ),
                    button.id,
                )
                if profile in seen_profiles:
                    continue
                seen_profiles.add(profile)

                browser.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", button
                )
                time.sleep(0.5)
                browser.execute_script("arguments[0].click();", button)
                completed += 1
                progress = True
                print(f"{completed}/{wanted} kişi takip edildi.")

                # Çok hızlı seri işlem yapılmasını önler.
                time.sleep(random.uniform(4.0, 7.0))
            except (StaleElementReferenceException, WebDriverException):
                continue

        empty_rounds = 0 if progress else empty_rounds + 1
        try:
            dialog = browser.find_element(By.CSS_SELECTOR, "div[role='dialog']")
            scroll_area = find_scroll_area(browser, dialog)
            browser.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_area
            )
        except WebDriverException:
            break
        time.sleep(2)

    return completed


def main() -> int:
    browser: Chrome | None = None
    try:
        count = read_count()
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        print("Chrome açılıyor...")
        browser = Chrome(options=options)
        browser.get("https://www.instagram.com/")

        print("\n1) Açılan Chrome'da Instagram'a giriş yap.")
        print("2) Takipçilerini açmak istediğin profile git.")
        print("3) Profildeki 'takipçiler' sayısına tıkla.")
        print("Program listeyi algılayınca otomatik takip başlayacak.")

        completed = follow_from_open_dialog(browser, count)
        print(f"\nİşlem tamamlandı. Toplam {completed} kişi takip edildi.")
        return 0
    except TimeoutException:
        print("Takipçi penceresi zamanında açılmadı.")
        return 1
    except (WebDriverException, Exception) as exc:
        message = str(exc).strip() or type(exc).__name__
        print(f"Hata: {message}")
        try:
            target = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
            (target.parent / "takipci_otomatik_hata.log").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        except OSError:
            pass
        return 1
    finally:
        if browser is not None:
            try:
                browser.quit()
            except WebDriverException:
                pass


if __name__ == "__main__":
    code = main()
    try:
        input("\nPencereyi kapatmak için Enter'a bas...")
    except (EOFError, KeyboardInterrupt):
        pass
    raise SystemExit(code)
