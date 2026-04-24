# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.3]
**Wersja:** v2.4.3 [FINAL STABLE]
**Data Aktualizacji:** 22 Kwietnia 2026

## 1. Architektura Systemu (Nowości)
System przeszedł znaczną ewolucję w stosunku do v2.3.x:
*   **Item System:** Dodano klasę `Item` w `engine_data.py`. Przedmioty mają teraz swoje ID, nazwy i ikony.
*   **Project Global Data:** `GamifikatorProject` obsługuje teraz globalne słowniki `items` oraz `dialogues`, a także globalny ekwipunek gracza.
*   **Geometry Engine:** Wykorzystanie biblioteki `Shapely` do automatycznego scalania wielokątów (`unary_union`). Rozwiązuje to problem nachodzących na siebie obszarów chodzenia (Walkable Areas).

## 2. Funkcje Edytora v2.4.3
### 2.1 Zarządzanie Obiektami
*   **Object Tree:** Nowy widok drzewa obiektów po prawej stronie. Pozwala na szybkie wybieranie HP i Area bez klikania na scenie.
*   **Undo System:** Zapamiętuje do 15 ostatnich zmian w pokojach (pod `Ctrl+Z`).
*   **Context Menus:** Prawy przycisk myszy na liście obiektów pozwala na szybkie usuwanie (🗑 Delete).

### 2.2 Nowe parametry Hotpointów
Hotpointy (HP) zyskały zaawansowane parametry interakcji:
*   `give_item_id`: ID przedmiotu wręczanego graczowi po interakcji.
*   `require_item_id`: Blokada interakcji, jeśli gracz nie posiada danego przedmiotu.
*   `dialogue_id`: Powiązanie z systemem dialogowym (v2.4+).

### 2.3 Nawigacja i Widok
*   **View Scaling:** Edytor automatycznie skaluje widok (`view_scale`), aby dopasować projekt do Twojego ekranu (np. 1920x1080 na mniejszym oknie).
*   **Smart Polygon Merging:** Przy rysowaniu obszarów `Walkable`, edytor automatycznie łączy nowy wielokąt z istniejącymi, tworząc jedną spójną siatkę kolizji.

## 3. Instrukcja Obsługi
*   **Ctrl+Z:** Cofnij ostatnią zmianę.
*   **Prawy Klik na Scenie:** Szybki dostęp do ustawień Hotpointa.
*   **Double Click w Tree:** Otwarcie ustawień obiektu.
*   **DEL:** Usunięcie zaznaczonego obiektu.

---
*Plik wygenerowany automatycznie podczas sesji backupu v2.4.3.*
