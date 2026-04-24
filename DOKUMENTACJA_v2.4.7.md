# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR 2026 [v2.4.7]
**Wersja:** v2.4.7 [SCRIPTS + VISUAL EFFECTS]
**Data:** 24 Kwietnia 2026

---

## Zmiany względem v2.4.6

### 1. System Skryptów Python (SCRIPTS)

Nowy przycisk **SCRIPTS** (zielony) w toolbarze. Okno do pisania, zarządzania i uruchamiania skryptów Python powiązanych z pokojem lub całą grą.

#### Zakres i trigger
- **ROOM** — skrypt działa tylko w wybranym pokoju (auto-przypisanie do bieżącego pokoju)
- **GLOBAL** — skrypt działa we wszystkich pokojach
- **ON ENTER** — odpala się automatycznie przy wejściu do pokoju (start Play Mode)
- **ON EXIT** — odpala się przy wyjściu z pokoju
- **MANUAL** — wywoływany ręcznie (np. przez preset "Burza — STOP")

#### Kontekst wykonania skryptu
```python
game_state  # dict współdzielony między skryptami i silnikiem renderowania
project     # obiekt GamifikatorProject
room_id     # id bieżącego pokoju
log(msg)    # wypisz do konsoli LOGS
```

#### Kompilacja odporna na błędy wcięć
Silnik próbuje najpierw `textwrap.dedent`, przy `IndentationError` stripuje każdą linię osobno. Wklejony kod z różnym wcięciem działa poprawnie.

#### PRESETS
Fioletowy przycisk **📋 PRESETS** — gotowe skrypty wstawiane jednym kliknięciem:
- **Burza — START** (scope: room, trigger: on_enter)
- **Burza — STOP** (scope: room, trigger: manual)

#### Format w `project.scripts`
```json
{
  "scr_id": {
    "name": "burza_start",
    "code": "game_state[\"rain\"] = {...}",
    "scope": "room",
    "room_id": "r_1234567890",
    "trigger": "on_enter",
    "created": "2026-04-24 20:30"
  }
}
```

---

### 2. System efektów wizualnych (Visual Effects)

Silnik renderowania sprawdza `game_state` każdą klatką i rysuje efekty na wierzchu sceny.

#### Efekt: Deszcz + Pioruny
```python
game_state["rain"] = {
    "intensity": 1.0,        # moc deszczu 0.0–1.0 (160 kropel przy 1.0)
    "color": "#7fb8e8",      # kolor kropel
    "lightning_prob": 0.03,  # szansa pioruna na klatkę (~co 3s)
    "seed": 42,              # ziarno losowości kształtu deszczu
}
```

**Warstwy efektu (kolejność rysowania):**
1. Ciemny overlay nieba (`#000933`, stipple gray50)
2. Ukośne krople deszczu (deterministyczna trajektoria per-tick)
3. Błysk pioruna (biały stipple przez 2 klatki ~200ms)

`game_state` jest czyszczony automatycznie przy wyłączeniu Play Mode.

---

### 3. Refactor kodu (z v2.4.6)

- `engine_loop` → wydzielony `_update_player_position()`
- `on_canvas_down` → `_handle_select_click`, `_handle_hotpoint_click`, `_handle_walkable_click`
- `refresh_canvas` → `_draw_background`, `_draw_walkable_areas`, `_draw_hotpoints`, `_draw_dialogs`, `_draw_temp_polygon`, `_draw_effects`
- `draw_player` → `_draw_player_placeholder`
- `_as_hp()`, `_wa_pts()` — helpery konwersji
- `_safe_compile()` — kompilacja z fallbackiem

---

## Nowe pola w `GamifikatorProject`
- `sprites` — biblioteka sprite'ów `{id: {name, path}}`
- `animations` — biblioteka ANIMATORATORA `{id: {name, sheet_path, frames, frame_w, frame_h, fps}}`
- `scripts` — biblioteka skryptów `{id: {name, code, scope, room_id, trigger, created}}`

## Architektura plików
| Plik | Opis |
|------|------|
| `editor.py` | Główny edytor wizualny (Tkinter) — v2.4.7 |
| `engine_data.py` | Klasy danych: `Hotpoint`, `WalkableArea`, `GamifikatorProject` |

## Stos technologiczny
- Python 3.12 + Tkinter + Pillow + NumPy + Shapely
- Format projektu: `.phx` (JSON)
- Build: PyInstaller 6.19.0
