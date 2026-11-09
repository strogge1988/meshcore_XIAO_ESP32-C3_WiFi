#include <cstdint>
#include <cstddef>
struct SerialType {void println(const char*) {} void flush() {} };
SerialType Serial;
struct Preferences {bool begin(const char*,bool) {return true;} bool getBool(const char*,bool) {return false;} bool remove(const char*) {return true;} void end() {} size_t putBool(const char*,bool) {return 1;} };
struct WiFiType {int status() {return 0;}}; WiFiType WiFi;
struct ESPType {void restart() {}}; ESPType ESP;
constexpr int WL_CONNECTED = 3;
uint32_t millis() {return 100;}
void delay(int) {}
#define MESHCORE_C3_EXCLUSIVE_WIFI_SETUP
#if defined(MESHCORE_C3_EXCLUSIVE_WIFI_SETUP)
// MC_C3_EXCLUSIVE_PATCH_V1
// Modes: provision via BLE, or normal Wi-Fi over TCP/5000; never both concurrently.
// The one-shot NVS marker deliberately survives ESP.restart() and power loss.
namespace {
  constexpr uint32_t MC_INITIAL_WIFI_TIMEOUT_MS = 60000UL;
  constexpr uint32_t MC_AFTER_CONNECTED_TIMEOUT_MS = 300000UL;
  constexpr const char* MC_PREFS_NAMESPACE = "mcc3wifi";
  constexpr const char* MC_RECOVERY_KEY = "ble_next";
  bool mc_use_wifi_only = false;
  bool mc_has_connected_to_wifi = false;
  uint32_t mc_wifi_offline_since = 0;

  bool mc_consume_ble_recovery_request() {
    Preferences p;
    if (!p.begin(MC_PREFS_NAMESPACE, false)) {
      Serial.println("[MC-C3] Cannot open recovery preferences; fail safe into BLE setup");
      return true;
    }
    bool requested = p.getBool(MC_RECOVERY_KEY, false);
    if (requested) p.remove(MC_RECOVERY_KEY); // one-shot: next restart attempts Wi-Fi again
    p.end();
    return requested;
  }

  void mc_restart_into_ble_recovery() {
    Preferences p;
    if (!p.begin(MC_PREFS_NAMESPACE, false)) {
      Serial.println("[MC-C3] Recovery NVS unavailable; continuing Wi-Fi retry");
      return;
    }
    size_t written = p.putBool(MC_RECOVERY_KEY, true);
    p.end();
    if (written != 1) {
      Serial.println("[MC-C3] Recovery flag could not be saved; continuing retry");
      return;
    }
    Serial.println("[MC-C3] Wi-Fi unavailable: rebooting once into BLE setup");
    Serial.flush();
    delay(80);
    ESP.restart();
  }

  void mc_wifi_recovery_tick() {
    if (!mc_use_wifi_only) return;
    uint32_t now = millis();
    if (WiFi.status() == WL_CONNECTED) {
      mc_has_connected_to_wifi = true;
      mc_wifi_offline_since = 0;
      return;
    }
    if (mc_wifi_offline_since == 0) {
      mc_wifi_offline_since = now == 0 ? 1 : now;
      return;
    }
    uint32_t timeout = mc_has_connected_to_wifi
        ? MC_AFTER_CONNECTED_TIMEOUT_MS : MC_INITIAL_WIFI_TIMEOUT_MS;
    if (static_cast<uint32_t>(now - mc_wifi_offline_since) >= timeout) {
      mc_restart_into_ble_recovery();
      // If NVS failed, do not hammer flash at every loop() iteration.
      mc_wifi_offline_since = now;
    }
  }
}  // namespace
#endif

