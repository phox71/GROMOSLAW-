# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.4]
**Wersja:** v2.4.4 [SCALING FIX]
**Data Aktualizacji:** 22 Kwietnia 2026

## 1. Nowości w v2.4.4 (Scaling & Inventory)
Wersja 2.4.4 skupiła się na poprawnym wyświetlaniu projektów na różnych ekranach oraz fundamentach mechaniki przygodowej.

### 1.1 Scaling Engine
*   **Adaptive Viewport:** Edytor oblicza `view_scale` na podstawie rozdzielczości projektu (np. 1920x1080) i dostępnego miejsca w oknie Tkinter. Wszystkie współrzędne kliknięć i rysowania są automatycznie przeliczane.
*   **AGS-style Dynamic Scaling:** Każdy obszar `WalkableArea` posiada parametry `min_scale` (horyzont) i `max_scale` (blisko kamery). Postać gracza płynnie zmienia rozmiar podczas ruchu w pionie (Y), co daje efekt głębi 3D w 2D.

### 1.2 System Przedmiotów i Logika
*   **Items Manager:** Globalna baza przedmiotów projektu. Każdy przedmiot ma unikalne ID, nazwę i ikonę (PNG).
*   **Interakcje Ekwipunku:** 
    *   `give_item_id`: Automatyczne dodanie przedmiotu do ekwipunku po kliknięciu HP.
    *   `require_item_id`: Blokada interakcji. Hotpoint reaguje tylko wtedy, gdy gracz "trzyma" (ma aktywny) konkretny przedmiot.
*   **Runtime Inventory:** W trybie PLAY pod prawym dolnym rogiem znajduje się przycisk ITEM, otwierający wizualny zasobnik.

### 1.3 Zaawansowana Geometria
*   **Shapely Integration:** Edytor wykorzystuje bibliotekę `Shapely` do operacji na poligonach. 
*   **Smart Merging:** Nowe obszary chodzenia są automatycznie łączone (`unary_union`) z istniejącymi, co zapobiega błędom nawigacji na stykach.
*   **Nearest Point Pathfinding:** Jeśli gracz kliknie poza obszar `Walkable`, silnik znajduje najbliższy punkt na krawędzi poligonu i tam kieruje postać.

## 2. Skróty i Obsługa
*   **ITEMS (Góra):** Zarządzanie bazą przedmiotów.
*   **PLAY MODE (F5 / ESC):** Testowanie gry.
*   **Prawy Klik na HP:** Szybka edycja parametrów (w tym `Swap PNG` i `Opacity`).
*   **DEL:** Usuwanie zaznaczonego obiektu z Treeview.

---
*Dokumentacja wygenerowana dla wersji v2.4.4.*
