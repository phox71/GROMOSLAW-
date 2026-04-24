# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.8]
**Wersja:** v2.4.8 [ITEM SYSTEM + UI POLISH]
**Data:** 25 Kwietnia 2026

---

## Zmiany względem v2.4.7

### 1. System Itemów

Gracz może zbierać przedmioty i używać ich do interakcji z hotpointami.

#### Nowe pola w Hotpoint
```python
is_item = False        # Ten hotpoint można podnieść (znika po podniesieniu)
required_item = ""     # ID hotpointa wymaganego w ekwipunku do interakcji
```

#### Logika w Play Mode
1. Gracz klika hotpoint z `is_item=True` → przedmiot trafia do `player_inventory`, hotpoint znika
2. Hotpoint z `required_item="hp_klucz"` → gracz musi mieć `"hp_klucz"` w ekwipunku
3. Przy złym/brakującym przedmiocie → losowy komunikat z `project.wrong_item_msgs`
4. Zebrane itemy nie blokują przejścia — usunięcie z widoku jest natychmiastowe

#### Pasek ekwipunku (Play Mode)
Lewy górny róg ekranu: `🎒  id_itemu1  id_itemu2  ...` (max 5 ostatnich)

#### Edycja w ustawieniach hotpointa
Sekcja **ITEM** w oknie EDIT HOTPOINT SETTINGS:
- Checkbox: `Jest przedmiotem (gracz może podnieść)`
- Pole: `Wymagany przedmiot (ID)` — ID innego hotpointa

#### Wiadomości przy złym przedmiocie
```python
project.wrong_item_msgs = [
    "To nie jest właściwy przedmiot.",
    "Potrzebuję czegoś innego.",
    "Hmm... nie sądzę.",
    "To tu nie pasuje.",
]
```
Lista edytowalna w kodzie projektu lub przyszłym UI.

---

### 2. UI — Przyciski narzędzi z etykietami

Przyciski Select / Walkable / Hotpoint w lewym pasku narzędzi mają teraz etykiety tekstowe pod ikonką. Aktywny tryb: ikona biała + tekst biały. Nieaktywny: ikona szara + tekst szary.

---

### 3. Sidebar — SCENY / OBIEKTY

- Nagłówek **SCENY** nad listą scen
- Nagłówek **OBIEKTY** nad drzewem obiektów
- Przycisk **✏** obok `+ SCENA` → zmiana nazwy bieżącej sceny
- Double-click na scenie w liście → zmiana nazwy (to samo co ✏)

---

### 4. Ctrl+Z wszędzie

`save_undo()` wywoływany automatycznie przed:
- Przeciąganiem hotpointa (move)
- Przeciąganiem pozycji gracza
- Resize hotpointa (każda krawędź)

Poprzednio undo działało tylko przy edycji ustawień i usuwaniu.

---

### 5. Placeholder gracza — walk.png

Kiedy gracz nie ma przypisanego PNG animacji, zamiast białego owalu rysowany jest `walk.png` (ikona ludzika) w kolorze białym, skalowany zgodnie z `player.scale`.

---

### 6. Dialogi/Komentarze nad hotpointem

Dymki komentarzy hotpointów (stary system `active_dialogs`) rysowane są **40px powyżej górnej krawędzi** hotpointa, z ciemnym tłem. Wcześniej rysowały się dokładnie na górnej krawędzi.

---

### 7. DIALOGI — poprawki UX

- Przycisk `+ CHOICE` zmieniony na `+ CHOICE (player)` — jasne, że to odpowiedź gracza
- Przy `+ NPC`: domyślny speaker = ID hotpointa przypisanego do dialogu (jeśli ustawiony)
- `ZAPISZ META` → automatycznie uzupełnia speaker NPC nodes które mają jeszcze domyślną wartość `"NPC"`

---

### 8. Zabezpieczenia przed utratą danych

- **Nowy projekt**: pytanie "Bieżący projekt zostanie zamknięty bez zapisania. Kontynuować?"
- **Zamknięcie okna**: pytanie "Projekt nie został zapisany. Wyjść bez zapisywania?"

---

## Architektura plików

| Plik | Opis |
|------|------|
| `editor.py` | Główny edytor wizualny (Tkinter) — v2.4.8 |
| `engine_data.py` | Klasy danych: `Hotpoint`, `WalkableArea`, `GamifikatorProject` |

## Nowe pola w `Hotpoint`
- `is_item` — bool, domyślnie `False`
- `required_item` — str, ID wymaganego przedmiotu (pusty = brak wymagania)

## Nowe pola w `GamifikatorProject`
- `wrong_item_msgs` — lista stringów, komunikaty przy złym przedmiocie

## Nowy stan w edytorze (Play Mode)
- `player_inventory` — lista ID zebranych itemów
- `collected_items` — set ID hotpointów usuniętych z planszy

## Stos technologiczny
- Python 3.12 + Tkinter + Pillow + NumPy + Shapely
- Format projektu: `.phx` (JSON)
- Build: PyInstaller 6.19.0
