# MeshCore 1.18.0 — XIAO ESP32-C3 + Wio-SX1262

**Komplettpaket für GitHub Actions** — kein Visual Studio Code und kein PlatformIO auf deinem PC erforderlich.

**Wichtig:** Dieses ZIP enthält **Build-Dateien**, noch **keine fertige Firmware `.bin`**. Die `.bin` wird von GitHub Actions erstellt, sofern der Build erfolgreich durchläuft. Die Sonderfirmware ist experimentell und nicht auf einem echten XIAO ESP32-C3 getestet.

## Installation in dein GitHub-Repository (ohne Ordner von Hand anzulegen)

1. Dieses ZIP **auf deinem Computer entpacken**. Die ZIP-Datei selbst **nicht** nach GitHub hochladen: GitHub entpackt ZIPs nicht.
2. In GitHub ein **leeres Repository** öffnen (oder den alten Inhalt vollständig entfernen). Auf `main` wechseln.
3. **Add file → Upload files** auswählen.
4. **Den Inhalt des entpackten Ordners** in das Upload-Feld ziehen (einschließlich `.github`, `tests` und der drei Dateien im Hauptverzeichnis). Falls Windows `.github` nicht anzeigt, versteckte Elemente einblenden. Nicht nur die oberste Verzeichnis-Hülle hochladen.
5. Im Upload-Bildschirm müssen diese Pfade sichtbar sein:

   ```text
   .github/workflows/build.yml
   tests/test_patch.py
   apply_exclusive_transport.py
   platformio.local.ini
   README.md
   ```

   **Kein Ordner `recipe` erforderlich!** Auch kein zusätzlicher Ordner `MeshCore_XIAO_C3_Komplettpaket_GitHub` im Repository.
6. **Commit changes** anklicken.
7. **Actions → MeshCore XIAO C3 - BLE Setup, WiFi Betrieb (1.18.0) → Run workflow** auswählen und `main` bestätigen. Immer **Run workflow** für einen neuen Commit, nicht `Re-run jobs` eines alten Laufs.
8. Bei Erfolg im fertigen Workflow-Lauf unter **Artifacts** das Paket **MeshCore-1.18.0-XIAO-C3-BLE-Setup-WiFi-Only** herunterladen. Darin sind:
   - `MeshCore-1.18.0-XIAO-C3-BLE-Setup-WiFi-Only.bin` — nur Applikation
   - `MeshCore-1.18.0-XIAO-C3-BLE-Setup-WiFi-Only-merged.bin` — komplettes Flash-Image
   - `SHA256SUMS.txt`

Wenn etwas fehlschlägt, schick den Text des **ersten rot markierten Schrittes** aus dem neuesten Lauf. Bitte nicht wieder alle Ordner löschen.

## Verhalten der experimentellen Firmware

- Hardware: Seeed XIAO ESP32-C3 mit seitlich aufgestecktem Seeed Wio-SX1262; offizielle MeshCore-Boarddefinition bleibt erhalten.
- Basistag: `companion-v1.18.0` (Commit `81dbae5`), Boardumgebung `Xiao_C3_companion_radio_ble`.
- **Ohne aktivierte, gespeicherte WLAN-Konfiguration:** Start mit Bluetooth LE zur Einrichtung in der MeshCore-App (Wi-Fi-Einstellungen mit einer geeigneten aktuellen App-Version konfigurieren, WLAN aktivieren).
- **Nach Neustart mit gültig gespeicherten WLAN-Einstellungen:** Nur WLAN/TCP (Standardport **5000**); Bluetooth wird nicht initialisiert. Der WLAN-Name und das Passwort werden **nicht** fest in die Firmware geschrieben.
- **Kein WLAN nach 60 Sekunden:** Einmaliger automatischer Neustart in einen BLE-Wiederherstellungsmodus. Nach einem früher erfolgreichen WLAN-Verbindungsaufbau wird erst nach 5 Minuten Ausfall umgeschaltet.
- Im BLE-Wiederherstellungsmodus Zugangsdaten korrigieren; **danach neu starten**. Der Marker für den Wiederherstellungsstart wird nur einmal verwendet und beim BLE-Start gelöscht. Zugangsdaten werden nicht automatisch zurückgesetzt.
- Die Umschaltung ist **kein Live-Wechsel**. Ein Neustart ist erforderlich. Bei funktionierender WLAN-Verbindung, aber falscher IP-/Netzwerk-Konfiguration, hilft der automatische BLE-Fallback nicht zwingend; notfalls neu flashen.

## Status / Einschränkungen

- In diesem Paket wurden lokale Python-Patch-Tests und eine Strukturprüfung durchgeführt; die echte PlatformIO-Kompilierung erfolgt erst in GitHub Actions.
- Auf dem ESP32-C3 ist der BLE-Setup/Wi-Fi-Only-Betrieb nicht offiziell freigegeben. Zu geringer Flash/RAM, inkompatible Framework-Versionen oder unerwartetes App-Verhalten sind möglich.
- Das Patch-Skript prüft Quellcode-Anker und bricht bei unerwarteter Upstream-Abweichung kontrolliert ab. **Nicht** blind andere MeshCore-Tags verwenden.
- Für ein komplettes erstmaliges Flashen ist die `*-merged.bin` mit dem für ESP32-C3 vollständige Images üblichen Offset `0x0` vorgesehen; bei einem anderen Flasher auf dessen Anforderungen achten. Vorhandene Geräteeinstellungen gegebenenfalls sichern, da ein Full-Flash sie beeinflussen kann.

## Enthaltene Dateien

```text
.github/workflows/build.yml      GitHub-Actions-Workflow
apply_exclusive_transport.py      Anpassung von MeshCore main.cpp
platformio.local.ini              PlatformIO-Build-Konfiguration
tests/test_patch.py               automatische Testfälle
README.md                         diese Anleitung
```

## Quellen

- Offizielles Release: https://github.com/meshcore-dev/MeshCore/releases/tag/companion-v1.18.0
- Board-Konfiguration: https://github.com/meshcore-dev/MeshCore/blob/companion-v1.18.0/variants/xiao_c3/platformio.ini
- Companion-Quellcode: https://github.com/meshcore-dev/MeshCore/blob/companion-v1.18.0/examples/companion_radio/main.cpp
