# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.6]
**Wersja:** v2.4.6 [ANIMATORATOR + BUGFIXES]
**Data Aktualizacji:** 24 Kwietnia 2026

---

## Zmiany względem v2.4.5

### 1. ANIMATORATOR — Nowy moduł wykrywania klatek animacji

Nowy przycisk **ANIMATORATOR** (fioletowy) w głównym toolbarze. Okno do automatycznego wykrywania, normalizacji i zapisu animacji ze sprite sheetów.

#### Algorytm wykrywania klatek
- **AUTO-TRIM:** Całość sprite sheet jest przycinana ze wszystkich stron (góra, dół, boki) z użyciem kanału alfa.
- **Projekcja kolumnowa:** Dla każdej kolumny X sumowane są wartości alfa. Kolumny z sumą = 0 to przerwy między klatkami.
- **Odporne na nieregularne odstępy:** Przerwy krótsze niż 3px są ignorowane — wewnętrzna transparentność postaci nie dzieli klatki na pół.
- **Minimalna szerokość klatki:** 4px (filtr szumu).

#### Jednolite kontenery (brak drgań)
- Wszystkie wykryte klatki dostają identyczny kontener rozmiaru `max_w × max_h`.
- Treść każdej klatki jest wyrównana: **do dołu** (stopy zawsze w tym samym punkcie Y) i **do środka** (oś X stabilna).
- Gwarantuje brak pionowego i poziomego "skakania" animacji.

#### Podgląd i zapis
- Animowany podgląd z regulowanym FPS (1–30).
- Kliknięcie miniatury klatki przeskakuje do niej w podglądzie.
- **Zapis:** Tworzy standardowy sprite sheet PNG (klatki poziomo, identyczne wymiary) obok pliku źródłowego. Wpis trafia do `project.animations` — kompatybilny z polem `path` w CONFIGURE PLAYER → animations.

#### Format wpisu w bibliotece
```json
{
  "name": "walk_right",
  "sheet_path": "C:/..../walk_right_anim.png",
  "frames": 8,
  "frame_w": 64,
  "frame_h": 96,
  "fps": 12
}
```

---

### 2. Naprawa chodzenia w Play Mode z PNG bohatera

**Problem:** Jeśli `draw_player()` rzucał wyjątek (np. resize do 0×0 przy małym scale, uszkodzony PNG), linia `self.root.after(100, self.engine_loop)` nigdy nie była wywoływana — pętla silnika umierała i gracz przestawał się ruszać.

**Naprawki:**
- `engine_loop` — `refresh_canvas()` opakowany w `try/except`; `root.after()` jest teraz zawsze wywoływane (pętla jest niezniszczalna).
- `draw_player` — dodany `max(1, ...)` na wymiary resize (zapobiega `resize(0, 0)`); `frames = max(1, frames)` zapobiega dzieleniu przez zero; cały blok obrazu opakowany w `try/except` z fallbackiem do białego koła.

---

### 3. System timing komentarzy (z v2.4.0)

W ustawieniach Hotpointa: **Czas wyśw. (s)** i **Przerwa (s)**. Komentarze wyświetlają się sekwencyjnie, poprzedni zawsze znika przed pojawieniem się następnego.

---

## Architektura plików (aktualna)

| Plik | Opis |
|------|------|
| `editor.py` | Główny edytor wizualny (Tkinter) |
| `engine_data.py` | Klasy danych: `Hotpoint`, `WalkableArea`, `GamifikatorProject` |

### Nowe pola w `GamifikatorProject`
- `sprites` — biblioteka sprite'ów `{id: {name, path}}`
- `animations` — biblioteka ANIMATORATORA `{id: {name, sheet_path, frames, frame_w, frame_h, fps}}`

---

## Stos technologiczny
- Python 3.12 + Tkinter + Pillow + NumPy + Shapely
- Format projektu: `.phx` (JSON)
- Build: PyInstaller
