# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR
## Wersja: 0.1 (Szkielet + Pokoje)
## Data: 2026-04-21

### 1. Cel Projektu
Silnik gier Point & Click na PC/Android/iOS. Inspirowany klasykami gatunku.

### 2. Architektura
- **Język:** Python 3.14
- **GUI:** Tkinter + Pillow (PIL) dla zaawansowanej obsługi grafiki.
- **Format Projektu:** `*.phx` (JSON).

### 3. Struktura Danych (PHX)
```json
{
    "name": "Nazwa Projektu",
    "resolution": "1920x1080",
    "rooms": {
        "room_id": {
            "name": "Nazwa",
            "background": "path/to/img.png",
            "hotpoints": [],
            "walkable": []
        }
    },
    "items": {},
    "start_room_id": ""
}
```

### 4. Interfejs (UI Design)
- Stylistyka: Photoshop 2026 (Dark Theme).
- Kolory: Background #181818, Panel #2b2b2b, Accent #007acc.
- Narzędzia: Select (S), Walkable (W), Hotpoint (H).

### ### 6. Walkable Areas
Obszary, po których może poruszać się gracz.
- Definiowane jako wielokąty (minimum 3 punkty).
- Parametry:
    - `scale_min`: Skalowanie (%) postaci na górnej krawędzi obszaru (oś Y).
    - `scale_max`: Skalowanie (%) postaci na dolnej krawędzi obszaru (oś Y).
- Funkcja: Zapewnia efekt perspektywy w grze 2D.

### 7. Skróty Klawiszowe
- **S:** Narzędzie Select
- **W:** Narzędzie Walkable
- **H:** Narzędzie Hotpoint
- **Right Click:** Zakończ rysowanie wielokąta Walkable.
