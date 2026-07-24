@echo off
chcp 65001 >nul
title Takipci Masaustu EXE Olusturucu

echo ==========================================
echo Takipci Masaustu EXE Olusturuluyor
echo ==========================================
echo.

echo Gerekli kutuphaneler kuruluyor...
python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller selenium

echo.
echo Eski derleme dosyalari temizleniyor...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist takipci_masaustu.spec del /q takipci_masaustu.spec

echo.
echo EXE dosyasi olusturuluyor...

python -m PyInstaller ^
--onefile ^
--console ^
--clean ^
--noconfirm ^
--collect-all selenium ^
--name TakipciMasaustu ^
takipci_masaustu.py

echo.
echo ==========================================

if exist "dist\TakipciMasaustu.exe" (
    echo EXE BASARIYLA OLUSTURULDU
    echo.
    echo Dosya konumu:
    echo %cd%\dist\TakipciMasaustu.exe
    echo.
    start "" "%cd%\dist"
) else (
    echo EXE OLUSTURULAMADI
    echo Yukaridaki hata mesajlarini kontrol et.
)

echo ==========================================
echo.
pause