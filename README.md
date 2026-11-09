# MeshCore 1.18.0 – XIAO ESP32-C3 + Wio-SX1262

**Ziel:** BLE **nur zur WLAN-Einrichtung**; im anschließenden Normalbetrieb **nur WLAN/TCP-Port 5000**. Bei nicht erreichbarem WLAN automatisch wieder BLE-Konfiguration anbieten.

**Status: Quellcode-Patch und GitHub-Actions-Build vorbereitet und statisch geprüft. Keine `.bin` vorhanden, nicht auf dem ESP32-C3 kompiliert oder getestet.** Die Erstellung der Binärdatei erfolgt auf einem GitHub-Actions-Runner.

## Hardware und Quellcode

- Seeed Studio XIAO ESP32-C3, Seeed Wio-SX1262 per XIAO-Seitenpins gestapelt (keine gesonderte Verkabelung).
- Offizielle Firmware-Version `companion-v1.18.0` / Commit `81dbae5`.
- Baut auf der Originalvariante `Xiao_C3_companion_radio_ble` und deren SX1262-Pinbelegung auf. Partitionierung `min_spiffs.csv` unverändert.
- Nutzt die von MeshCore vorgesehene Wi-Fi-Unterstützung (`ENABLE_WIFI_INTERFACE` und `helpers/wifi/*.cpp`) plus einen gezielten Patch an `examples/companion_radio/main.cpp`.
- Das ist eine **experimentelle Sonderversion**. Das offizielle Release aktiviert BLE und WLAN für den XIAO **ESP32-S3**, nicht für den ESP32-C3; Buildgröße, RAM und Laufzeitstabilität können Probleme machen.

## Verhalten des Firmware-Patches

1. **Ohne aktive gespeicherte WLAN-Konfiguration:** Companion startet mit BLE. WLAN wird nicht gestartet.
2. In der **MeshCore-App >=1.50.0** per BLE verbinden und unter den Wi-Fi-Einstellungen SSID und Kennwort speichern **und Wi-Fi aktivieren** (`wifi.enabled=1`). Keine WLAN-Zugangsdaten im Firmware-Image.
3. **Gerät über die App neu starten** (oder normale Reset-Taste kurz drücken). Das Gerät startet mit WLAN, **ohne BLE zu initialisieren**. Zugriff über Companion TCP auf Port **5000**, sofern das Handy/der PC das Gerät über LAN erreichen kann.
4. Schlägt der **erste WLAN-Verbindungsaufbau 60 s lang** fehl, schreibt die Firmware ein einmaliges Flag in den ESP32-NVS-Speicher und startet neu. Der nächste Boot läuft im BLE-Modus, und das Flag wird gelöscht.
5. Nach einer bereits erfolgreichen WLAN-Verbindung wartet die Firmware bei Verlust **5 Minuten**, bevor sie einmal in den BLE-Wiederherstellungsmodus startet. Kurzzeitige WLAN-Ausfälle führen also nicht sofort zur Umschaltung.
6. Im BLE-Wiederherstellungsmodus Einstellungen korrigieren und neu starten. Nach dem einmaligen BLE-Boot wird beim nächsten Neustart wieder WLAN probiert. Die Zugangsdaten werden durch den Recovery-Mechanismus nicht gelöscht.

**Hinweis:** Die Firmware wechselt nicht *im laufenden Betrieb* zwischen beiden Funkmodi. Ein Neustart trennt Bluetooth/WLAN zuverlässig, sodass beide Stacks nie gleichzeitig initialisiert werden. Die BLE-Wiederherstellung erfolgt automatisch, wenn das WLAN nicht verbunden werden kann; bei erreichbarem WLAN, aber falsch konfiguriertem LAN/Firewall/IP, bleibt als Notlösung ein erneutes Flashen. BOOT ist beim XIAO-C3 GPIO9 und gleichzeitig SPI-MISO für SX1262; die Firmware nutzt BOOT deshalb nicht als Reset-Signal.

## GitHub Actions: `.bin` ohne VS Code / PlatformIO auf dem PC erstellen

Du brauchst nur ein GitHub-Konto und ein **neues, möglichst privates Repository**.

1. In GitHub ein leeres Repository erstellen.
2. Diese **vier Dateien** mit den gezeigten Namen/Pfaden hochladen (GitHub-Website: **Add file > Create new file**; den vollständigen Pfad als Dateiname eingeben):
   - `.github/workflows/build-xiao-c3-exclusive.yml`
   - `apply_exclusive_transport.py`
   - `platformio.local.ini`
   - `tests/test_patch.py`

   `tests/cpp_syntax_check.cpp` ist nur ein zusätzlicher lokaler Syntax-Prüfstand; er ist für den GitHub-Workflow nicht nötig.
3. GitHub > **Actions** > **MeshCore 1.18.0 XIAO-C3 exclusive BLE setup + WiFi** > **Run workflow**.
4. Nach einem grünen Build unter **Artifacts** `MeshCore-1.18.0-XIAO-C3-exclusive-BLE-WiFi` herunterladen. Die ZIP-Datei enthält:
   - `MeshCore-1.18.0-XIAO-C3-Wio-SX1262-exclusive.bin` (App-Image)
   - `MeshCore-1.18.0-XIAO-C3-Wio-SX1262-exclusive-merged.bin` (vollständiges Flash-Image inklusive Bootloader/Partitionen)
   - `SHA256SUMS.txt`
5. **Nur wenn der Build grün ist**, die erzeugte Datei flashen. Beim erstmaligen Flashen auf das vorhandene Board ist das `*-merged.bin` üblicherweise die richtige Option. Auf den **ESP32-C3** und den **richtigen Flash-Offset** achten; zum Flashen des Merged-Images ist Offset `0x0` vorgesehen. Nicht blind die App-`.bin` mit Offset `0x0` flashen.

**Wenn der Workflow fehlschlägt:** Den `Actions`-Build-Log aufbewahren und die erste relevante Fehlerstelle weitergeben. Keine Firmware-Datei als erfolgreich ansehen, solange der Workflow nicht erfolgreich durchgelaufen ist. `tests/` dürfen nicht fehlen, sonst scheitert der Workflow bereits bei der Vorprüfung.

## Lokal (falls später doch gewünscht)

Den offiziellen Quellcode `companion-v1.18.0` auschecken, diese `platformio.local.ini` ins Root kopieren und den Patch anwenden:

```bash
python apply_exclusive_transport.py /pfad/zum/MeshCore
cd /pfad/zum/MeshCore
pio run -e Xiao_C3_companion_radio_ble_setup_wifi_only
pio run -e Xiao_C3_companion_radio_ble_setup_wifi_only -t mergebin
```

## Quellen

- https://github.com/meshcore-dev/MeshCore/releases/tag/companion-v1.18.0
- https://github.com/meshcore-dev/MeshCore/blob/companion-v1.18.0/examples/companion_radio/main.cpp
- https://github.com/meshcore-dev/MeshCore/blob/companion-v1.18.0/variants/xiao_c3/platformio.ini
- https://blog.meshcore.io/2026/10/15/release-1-18-0
- https://wiki.seeedstudio.com/XIAO_ESP32C3_Pin_Multiplexing/
