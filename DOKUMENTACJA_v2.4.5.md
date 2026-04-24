# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.5]
**Wersja:** v2.4.5 [SPRITE ENGINE]
**Data Aktualizacji:** 22 Kwietnia 2026

## 1. Nowości w v2.4.5 (Smart Sprite Engine & Library)
Wersja 2.4.5 wprowadza profesjonalne zarządzanie zasobami graficznymi oraz fizyczną optymalizację arkuszy sprite'ów.

### 1.1 Smart Sprite Engine V3
*   **Auto-Trim (Internal):** Podczas renderowania silnik automatycznie wykrywa faktyczną zawartość klatki, ignorując puste piksele.
*   **Uniform Container:** Każda klatka animacji jest osadzana w identycznym "pudełku" (największy wspólny rozmiar), co całkowicie eliminuje drgania (jittering).
*   **Bottom-Center Pivot:** Punkt (X, Y) obiektu jest teraz środkiem jego dolnej krawędzi (`anchor="s"`). Obiekty "stoją" stabilnie na ziemi nawet przy zmianie animacji.

### 1.2 Sprites Manager & Optimizer
*   **Global Sprite Library:** Nowe menu **SPRITES** pozwala na masowe dodawanie plików PNG do projektu. Zasoby są zapamiętywane w pliku `.phx`.
*   **Physical TRIM:** Narzędzie do fizycznej modyfikacji plików PNG. 
    *   Skanuje arkusz, usuwa puste przestrzenie wokół grafiki.
    *   Centruje klatki względem dołu.
    *   **Nadpisuje oryginał**, tworząc idealnie zoptymalizowany arkusz sprite'ów.
*   **LIB Integration:** W ustawieniach Hotpointów przycisk **LIB** pozwala na natychmiastowe wybranie grafiki z biblioteki projektu zamiast szukania pliku na dysku.

### 1.3 System Animacji Sprite Sheet
*   **Frames Count:** Parametr określający podział paska PNG na równe klatki.
*   **Live Preview:** Okno ustawień Hotpointa zawiera teraz:
    *   Widok arkusza z czerwonymi liniami cięcia.
    *   Animowany podgląd końcowy w czasie rzeczywistym.

## 2. Skróty i Obsługa
*   **SPRITES (Góra):** Zarządzanie biblioteką i fizyczna optymalizacja PNG.
*   **LIB (HP Settings):** Wybór grafiki z biblioteki projektu.
*   **PLAY MODE (F5 / ESC):** Testowanie gry z nowym silnikiem animacji.

---
*Dokumentacja wygenerowana dla wersji v2.4.5.*
