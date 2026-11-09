"""Check anchors, exclusivity, recovery, and failure-on-unknown-upstream behavior.

Uses minimal upstream-shaped fixtures; it is NOT a compiler or hardware test.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_exclusive_transport import transform  # noqa: E402


# Excerpts from official MeshCore 1.18.0 main.cpp, joined with placeholder bodies.
UPSTREAM_SHAPED_MAIN = '''#include <Arduino.h>
#include <Mesh.h>
#include "MyMesh.h"
#ifdef ENABLE_WIFI_INTERFACE
  bool wifi_enabled = false;
#endif

void setup() {
  Serial.begin(115200);
#elif defined(ESP32)
  SPIFFS.begin(true);
  store.begin();
  the_mesh.begin();
#else
  #error "need to define filesystem"
#endif
#ifdef BLE_PIN_CODE
  // set pin
#endif
#if defined(BLE_PIN_CODE)
  bluetooth_interface.begin(BLE_NAME_PREFIX, the_mesh.getNodePrefs()->node_name, the_mesh.getBLEPin());
  interface_manager.addInterface(InterfaceType::Bluetooth, &bluetooth_interface);
#endif
#ifdef ENABLE_WIFI_INTERFACE
  wifi_enabled = the_mesh.getNodePrefs()->wifi_enabled;
  if (wifi_enabled && wifi_ssid[0]) {
    WiFi.begin(wifi_ssid, wifi_pwd);
  }
#endif
}

void loop() {
#ifdef ENABLE_WIFI_INTERFACE
  if (wifi_enabled) {
    if (wifi_needs_reconnect) {
      last_wifi_reconnect_attempt = millis();
    }
  }
#endif
}
'''


class ExclusiveBuildPatchTests(unittest.TestCase):
    def test_build_patch_contains_exclusive_mode(self):
        patched = transform(UPSTREAM_SHAPED_MAIN)
        self.assertIn('mc_use_wifi_only = !mc_recovery_requested', patched)
        self.assertIn('if (!mc_use_wifi_only)', patched)
        self.assertIn('wifi_enabled = wifi_enabled && mc_use_wifi_only;', patched)
        self.assertIn('mc_wifi_recovery_tick();', patched)
        self.assertIn('MC_INITIAL_WIFI_TIMEOUT_MS = 60000UL', patched)
        self.assertIn('MC_AFTER_CONNECTED_TIMEOUT_MS = 300000UL', patched)
        self.assertIn('p.remove(MC_RECOVERY_KEY)', patched)
        self.assertIn('ESP.restart();', patched)

    def test_refuse_unknown_upstream(self):
        with self.assertRaisesRegex(ValueError, 'anchor'):
            transform('#include "MyMesh.h"\nvoid setup() {}\n')

    def test_refuse_double_application(self):
        patched = transform(UPSTREAM_SHAPED_MAIN)
        with self.assertRaisesRegex(ValueError, 'already patched'):
            transform(patched)


if __name__ == '__main__':
    unittest.main()
