# SMA Tracker für Home Assistant

Ein Home Assistant Custom Component zum Tracken des Abstands zwischen dem aktuellen Kurs und dem Simple Moving Average (SMA) für verschiedene Aktienindizes und Wertpapiere. Die Daten stammen von Yahoo Finance.

## Features

- **SMA-Berechnung**: Automatische Berechnung des Simple Moving Average für konfigurierbare Zeiträume (2-500 Handelstage)
- **Abstandsanzeige**: Zeigt die prozentuale Differenz zwischen aktuellem Kurs und SMA
- **Farbcodierung**: Intelligente Farbanzeige basierend auf dem Abstand:
  - 🟢 **Grün**: > 2% über der SMA (deutlich über dem Durchschnitt)
  - 🟡 **Gelb**: 0% bis < 2% über der SMA (nah an der SMA)
  - 🔴 **Rot**: ≤ 0% (unter oder gleich der SMA)
- **Yahoo Finance Integration**: Echte Marktdaten mit 2 Jahren Historien
- **Flexible Updates**: Konfigurierbare Update-Intervalle (5-1440 Minuten)
- **Multi-Index Support**: Unterstützt beliebige Yahoo Finance Symbole

## Unterstützte Symbole

Beispiele für konfigurierbare Indizes und Wertpapiere:

- **DAX**: `^GDAXI`
- **S&P 500**: `^GSPC`
- **Nasdaq**: `^IXIC`
- **Dow Jones**: `^DJI`
- **Euro Stoxx 50**: `^STOXX50E`
- **Nikkei 225**: `^N225`
- **Einzelaktien**: z.B. `AAPL`, `MSFT`, `SIEMENS.DE`, etc.

Weitere Symbole finden Sie auf [Yahoo Finance](https://finance.yahoo.com/).

## Installation

### Via HACS (empfohlen)

1. Öffnen Sie Home Assistant
2. Gehen Sie zu **HACS** → **Integrationen**
3. Klicken Sie auf **+ Benutzerdefiniert durchsuchen** (oben rechts)
4. Geben Sie die Repository-URL ein
5. Wählen Sie **Integration** als Kategorie
6. Klicken Sie auf **Installieren**
7. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie das Repository herunter
2. Kopieren Sie den Ordner `sma_tracker` in Ihr `custom_components` Verzeichnis:
   ```
   ~/.homeassistant/custom_components/sma_tracker/
   ```
3. Starten Sie Home Assistant neu

## Konfiguration

### Via UI (empfohlen)

1. Gehen Sie zu **Einstellungen** → **Geräte und Dienste**
2. Klicken Sie auf **Neue Integration erstellen**
3. Suchen Sie nach **SMA Tracker**
4. Füllen Sie die Konfigurationsfelder aus:
   - **Yahoo Finance Symbol**: z.B. `^GDAXI` für den DAX
   - **Anzeigename (optional)**: z.B. "DAX SMA200"
   - **SMA-Zeitraum**: Anzahl der Handelstage für die SMA-Berechnung (default: 200)
   - **Aktualisierungsintervall**: Wie oft die Daten aktualisiert werden in Minuten (default: 15)

### Konfigurationsbeispiele

**DAX mit SMA200 (alle 15 Minuten aktualisieren)**:
- Symbol: `^GDAXI`
- Anzeigename: `DAX`
- SMA-Zeitraum: `200`
- Aktualisierungsintervall: `15`

**S&P 500 mit SMA50 (täglich aktualisieren)**:
- Symbol: `^GSPC`
- Anzeigename: `S&P 500`
- SMA-Zeitraum: `50`
- Aktualisierungsintervall: `1440`

## Entitäten

Nach der Konfiguration erstellt die Integration folgende Entitäten:

### Sensor: `sensor.{name}_sma{period}_abstand`

**Wert**: Prozentuale Differenz zwischen aktuellem Kurs und SMA

**Attribute**:
- `current_price`: Aktueller Kurs
- `sma_value`: Aktueller SMA-Wert
- `symbol`: Yahoo Finance Symbol
- `sma_period`: Konfigurierter SMA-Zeitraum
- `currency`: Währung des Indexes

**Farben (RGB)**:
- Grün: `(0, 255, 0)` für Werte > 2%
- Gelb: `(255, 255, 0)` für Werte 0% bis < 2%
- Rot: `(255, 0, 0)` für Werte ≤ 0%

## Automation Beispiele

### Benachrichtigung bei Unterschreitung der SMA

```yaml
automation:
  - alias: "DAX unterschreitet SMA"
    trigger:
      platform: numeric_state
      entity_id: sensor.dax_sma200_abstand
      below: 0
    action:
      service: notify.notify
      data:
        message: "DAX ist unter die SMA200 gefallen!"
```

### Lovelace Card

```yaml
type: entities
entities:
  - entity: sensor.dax_sma200_abstand
    name: DAX SMA200 Abstand
```

## Fehlerbehebung

### Fehler: "Not enough historical data"

Die Integration konnte nicht genug historische Daten von Yahoo Finance abrufen. Dies kann passieren, wenn:
- Das Symbol nicht existiert
- Yahoo Finance für dieses Symbol keine 2 Jahre Daten hat

**Lösung**: Überprüfen Sie das Yahoo Finance Symbol und verringern Sie ggf. den SMA-Zeitraum.

### Fehler: "HTTP 404"

Das Symbol existiert nicht oder ist ungültig.

**Lösung**: Überprüfen Sie das Symbol auf [Yahoo Finance](https://finance.yahoo.com/).

### Integration lädt nicht

- Überprüfen Sie die Logs in Home Assistant
- Starten Sie Home Assistant neu

## Häufig Gestellte Fragen

**F: Warum nutzt ihr Yahoo Finance?**
A: Yahoo Finance bietet kostenlose, zuverlässige Daten für Indizes und Einzelaktien ohne API-Key.

**F: Kann ich mehrere Indizes gleichzeitig tracken?**
A: Ja! Sie können mehrere Konfigurationseinträge erstellen, einen für jeden Index.

**F: Wie genau ist die SMA-Berechnung?**
A: Die SMA wird über die letzten 2 Jahre täglicher Daten berechnet. Die Genauigkeit ist sehr hoch.

**F: Kann ich den SMA-Zeitraum ändern?**
A: Ja, aber Sie müssen einen neuen Konfigurationseintrag erstellen. Jede Kombination aus Symbol und SMA-Zeitraum ist eindeutig.

## Lizenz

MIT License - Siehe LICENSE Datei für Details

## Support

Für Probleme, Fragen oder Feature-Requests öffnen Sie bitte ein Issue auf GitHub.

---

**Hinweis**: Diese Integration ist ein Community-Projekt und wird nicht von Home Assistant oder Yahoo Finance unterstützt.
