@echo off
chcp 65001 >nul
title OIS IDPK - Localhost Dev Server
cls
echo ===================================================================
echo     OIS IDPK - Lokální vývojové prostředí (Localhost)
echo ===================================================================
echo.
echo Adresa webu: http://127.0.0.1:8080 nebo http://localhost:8080
echo Veřejnost na produkci tuto verzi neuvidí!
echo.

if not exist .venv\Scripts\python.exe (
    echo [CHYBA] Virtuální prostředí .venv nebylo nalezeno.
    echo Vytvořte ho příkazem: py -3.11 -m venv .venv
    pause
    exit /b
)

if not exist .env (
    echo [UPOZORNĚNÍ] Soubor .env neexistuje!
    echo Pokud chcete plný přístup k Supabase, zkopírujte .env.example do .env a doplňte klíče.
    echo.
)

.\.venv\Scripts\python.exe main.py
pause
