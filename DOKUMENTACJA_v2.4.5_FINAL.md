# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.5 FINAL]
**Wersja:** v2.4.5 [SPRITE ENGINE & STABILITY]
**Data Aktualizacji:** 22 Kwietnia 2026

## 1. Architektura Graficzna (Sprite Engine V3)
Wersja 2.4.5 to przełom w obsłudze grafiki 2D, wprowadzający standardy znane z profesjonalnych silników przygodowych.

### 1.1 Wizualna Biblioteka Zasobów (SPRITES)
*   **Grid Browser:** Nowy menedżer sprite'ów wyświetla wszystkie pliki PNG w formie siatki miniatur.
*   **Thumbnail Previews:** Silnik automatycznie generuje podgląd pierwszej klatki dla arkuszy animacji (Sprite Sheets).
*   **Sprite Tools:** Sidebar z narzędziami do edycji wybranych grafik:
    *   **Pipeta (Eyedropper):** Pobieranie koloru bezpośrednio z podglądu.
    *   **Usuwanie Koloru:** Fizyczne usuwanie tła (Chroma Key) z plików PNG z zachowaniem przezroczystości.
    *   **Auto-Remove BG:** Automatyczne czyszczenie tła na podstawie koloru narożnego piksela.

### 1.2 Fizyczna Optymalizacja (Physical TRIM)
*   **4-Side Tight Crop:** Narzędzie fizycznie przycina pliki PNG, usuwając puste piksele ze wszystkich stron (góra, dół, boki).
*   **Uniform Box Logic:** Każda klatka animacji po przycięciu ma identyczny wymiar, co eliminuje drgania (jittering).
*   **Auto-Update:** Silnik automatycznie aktualizuje wymiary i pozycje obiektów na wszystkich scenach po wykonaniu TRIM, aby postacie nie "pływały".

### 1.3 System Kontenera i Pivotu Bohatera
*   **Character Box:** Bohater posiada stały kontener (Box), który można swobodnie rysować/rozciągać na scenie (Resize Handle).
*   **Interactive Pivot Point:** W oknie `Avatar Config` użytkownik ustawia punkt odniesienia (Pivot - czerwona kropka), który definiuje "stopy" postaci.
*   **Stability:** Niezależnie od klatki animacji, postać stoi stabilnie względem Pivotu.

## 2. System i Stabilność
*   **Universal State Undo (CTRL+Z):** Pełny backup stanu projektu (JSON deep copy) przy każdej akcji. Cofa zmiany w bibliotece, ustawieniach gracza, przedmiotach i geometrii sceny.
*   **LIB Buttons:** Integracja przycisków LIB we wszystkich oknach ustawień, pozwalająca na wizualny wybór grafiki z biblioteki projektu.

---
*Dokumentacja wersji finalnej 2.4.5.*
