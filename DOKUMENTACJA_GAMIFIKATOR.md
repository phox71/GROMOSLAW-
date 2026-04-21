# DOKUMENTACJA TECHNICZNA - GAMIFIKATOR
## Wersja: 1.2 (Ultimate Stable)
## Data: 2026-04-21

### 1. Architektura Systemu
- **editor.py**: Główny interfejs graficzny (Photoshop 2026 style).
- **engine_data.py**: Klasy danych projektu (Dataclasses), logika serializacji JSON.
- **Biblioteki**: Tkinter (GUI), Pillow (Grafika), Shapely (Geometria Walkable).

### 2. System Walkable (Obszary Chodzenia)
- **Łączenie**: Automatyczne scalanie nachodzących na siebie wielokątów (unary_union).
- **Snapping**: Przyciąganie punktów do startu przy odległości < 15px.
- **Skalowanie Y**: Gradientowa zmiana wielkości bohatera (MIN/MAX %).

### 3. System Hotpointów
- **Akcje**: Comment, Pick up, Talk to, LOCK, Move to.
- **Flow**: Możliwość ustawienia wielu reakcji (Unlock, Swap PNG, Dialog).
- **Dialogi**: System wielu linii komentarzy z czasem wyświetlania.

### 4. Player Avatar
- **Animacje**: Obsługa 4 kierunków (Idle, Right, Up, Down).
- **Mirroring**: Funkcja FLIP dla animacji lewo-prawo.
- **Spawn**: Ustawianie pozycji startowej gracza bezpośrednio na płótnie metodą Drag&Drop.

### 5. Funkcje Edytora
- **Undo (CTRL+Z)**: Historia 10 ostatnich zmian stanu sceny.
- **Konsola**: Przesuwalny panel logów z funkcją kopiowania błędów.
- **Usuwanie**: Klawisz DELETE usuwa zaznaczony obiekt (Player, HP, Area).

### 6. Instrukcja Odtwarzania
1. `pip install Pillow shapely`
2. Uruchom `editor.py`.
3. Projekt zapisywany w formacie `*.phx`.
