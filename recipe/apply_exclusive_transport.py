#!/usr/bin/env python3
"""Apply an exclusive BLE-setup / Wi-Fi-runtime patch to MeshCore companion-v1.18.0.

This is deliberately anchored to the 1.18.0 upstream main.cpp: unexpected source
changes cause a hard failure instead of silently producing incorrect firmware.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TARGET = Path('examples/companion_radio/main.cpp')
MACRO = 'MESHCORE_C3_EXCLUSIVE_WIFI_SETUP'


def replace_exactly_once(source: str, anchor: str, replacement: str, label: str) -> str:
    found = source.count(anchor)
    if found != 1:
        raise ValueError(f'{label}: expected exactly one upstream anchor, found {found}; refusing unsafe patch')
    return source.replace(anchor, replacement, 1)


def transform(source: str) -> str:
    if 'MC_C3_EXCLUSIVE_PATCH_V1' in source:
        raise ValueError('Source already patched; refusing to patch twice')

    source = replace_exactly_once(
        source,
        '#include "MyMesh.h"\n',
        '#include "MyMesh.h"\n'
        f'#ifdef {MACRO}\n'
        '#include <Preferences.h>\n'
        '#include <WiFi.h>\n'
        '#endif\n',
        'exclusive-mode includes',
    )

    # Before setup(): one-shot NVS recovery flag plus a Wi-Fi-only watchdog.
    # Wi-Fi and Bluetooth are never initialized within the same boot.
    recovery = f'''#if defined({MACRO})
// MC_C3_EXCLUSIVE_PATCH_V1
// Modes: provision via BLE, or normal Wi-Fi over TCP/5000; never both concurrently.
// The one-shot NVS marker deliberately survives ESP.restart() and power loss.
namespace {{
  constexpr uint32_t MC_INITIAL_WIFI_TIMEOUT_MS = 60000UL;
  constexpr uint32_t MC_AFTER_CONNECTED_TIMEOUT_MS = 300000UL;
  constexpr const char* MC_PREFS_NAMESPACE = "mcc3wifi";
  constexpr const char* MC_RECOVERY_KEY = "ble_next";
  bool mc_use_wifi_only = false;
  bool mc_has_connected_to_wifi = false;
  uint32_t mc_wifi_offline_since = 0;

  bool mc_consume_ble_recovery_request() {{
    Preferences p;
    if (!p.begin(MC_PREFS_NAMESPACE, false)) {{
      Serial.println("[MC-C3] Cannot open recovery preferences; fail safe into BLE setup");
      return true;
    }}
    bool requested = p.getBool(MC_RECOVERY_KEY, false);
    if (requested) p.remove(MC_RECOVERY_KEY); // one-shot: next restart attempts Wi-Fi again
    p.end();
    return requested;
  }}

  void mc_restart_into_ble_recovery() {{
    Preferences p;
    if (!p.begin(MC_PREFS_NAMESPACE, false)) {{
      Serial.println("[MC-C3] Recovery NVS unavailable; continuing Wi-Fi retry");
      return;
    }}
    size_t written = p.putBool(MC_RECOVERY_KEY, true);
    p.end();
    if (written != 1) {{
      Serial.println("[MC-C3] Recovery flag could not be saved; continuing retry");
      return;
    }}
    Serial.println("[MC-C3] Wi-Fi unavailable: rebooting once into BLE setup");
    Serial.flush();
    delay(80);
    ESP.restart();
  }}

  void mc_wifi_recovery_tick() {{
    if (!mc_use_wifi_only) return;
    uint32_t now = millis();
    if (WiFi.status() == WL_CONNECTED) {{
      mc_has_connected_to_wifi = true;
      mc_wifi_offline_since = 0;
      return;
    }}
    if (mc_wifi_offline_since == 0) {{
      mc_wifi_offline_since = now == 0 ? 1 : now;
      return;
    }}
    uint32_t timeout = mc_has_connected_to_wifi
        ? MC_AFTER_CONNECTED_TIMEOUT_MS : MC_INITIAL_WIFI_TIMEOUT_MS;
    if (static_cast<uint32_t>(now - mc_wifi_offline_since) >= timeout) {{
      mc_restart_into_ble_recovery();
      // If NVS failed, do not hammer flash at every loop() iteration.
      mc_wifi_offline_since = now;
    }}
  }}
}}  // namespace
#endif

'''
    source = replace_exactly_once(
        source,
        '\nvoid setup() {\n',
        '\n' + recovery + 'void setup() {\n',
        'exclusive recovery functions',
    )

    # Locate the BLE PIN initialization after preference loading. Avoid matching
    # whitespace or platform-specific #error formatting in the preceding lines.
    ble_anchor = '#ifdef BLE_PIN_CODE // 123456 by default'
    ble_pos = source.find(ble_anchor)
    if source.count(ble_anchor) != 1 or ble_pos == -1:
        raise ValueError('post-store transport selection: expected exactly one upstream anchor; refusing unsafe patch')
    setup_pos = source.find('void setup() {')
    if not (setup_pos >= 0 and ble_pos > setup_pos and
            'the_mesh.begin();' in source[setup_pos:ble_pos]):
        raise ValueError('post-store transport selection: BLE anchor is not after mesh initialization')
    source = replace_exactly_once(
        source,
        ble_anchor,
        f'#if defined({MACRO})\n'
        '  // Read persisted Wi-Fi settings only AFTER the MeshCore data store is ready.\n'
        '  bool mc_recovery_requested = mc_consume_ble_recovery_request();\n'
        '  mc_use_wifi_only = !mc_recovery_requested &&\n'
        '      the_mesh.getNodePrefs()->wifi_enabled &&\n'
        '      the_mesh.getNodePrefs()->wifi_ssid[0] != 0;\n'
        '  Serial.printf("[MC-C3] Starting %s transport\\n",\n'
        '                mc_use_wifi_only ? "Wi-Fi only" : "BLE setup");\n'
        '#endif\n'
        + ble_anchor,
        'post-store transport selection',
    )

    source = replace_exactly_once(
        source,
        '  bluetooth_interface.begin(BLE_NAME_PREFIX, the_mesh.getNodePrefs()->node_name, the_mesh.getBLEPin());\n'
        '  interface_manager.addInterface(InterfaceType::Bluetooth, &bluetooth_interface);',
        f'#if defined({MACRO})\n'
        '  if (!mc_use_wifi_only) {\n'
        '#endif\n'
        '    bluetooth_interface.begin(BLE_NAME_PREFIX, the_mesh.getNodePrefs()->node_name, the_mesh.getBLEPin());\n'
        '    interface_manager.addInterface(InterfaceType::Bluetooth, &bluetooth_interface);\n'
        f'#if defined({MACRO})\n'
        '  }\n'
        '#endif',
        'conditional BLE interface',
    )

    source = replace_exactly_once(
        source,
        '  wifi_enabled = the_mesh.getNodePrefs()->wifi_enabled;\n'
        '  if (wifi_enabled && wifi_ssid[0]) {',
        '  wifi_enabled = the_mesh.getNodePrefs()->wifi_enabled;\n'
        f'#if defined({MACRO})\n'
        '  // BLE recovery boots intentionally keep the Wi-Fi interface inactive.\n'
        '  wifi_enabled = wifi_enabled && mc_use_wifi_only;\n'
        '#endif\n'
        '  if (wifi_enabled && wifi_ssid[0]) {',
        'conditional Wi-Fi interface',
    )

    # Patch only the final tail of loop(): the reconnect logic continues to operate.
    tail_anchor = '''      last_wifi_reconnect_attempt = millis();
    }
  }
#endif
}
'''
    tail_replacement = '''      last_wifi_reconnect_attempt = millis();
    }
  }
#endif
''' + f'''#if defined({MACRO})
  mc_wifi_recovery_tick();
#endif
}}
'''
    if not source.endswith(tail_anchor):
        raise ValueError('loop tail differs from upstream 1.18.0; refusing unsafe patch')
    source = source[:-len(tail_anchor)] + tail_replacement

    return source


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository', nargs='?', default='MeshCore', help='path to MeshCore checkout')
    args = p.parse_args()
    target = Path(args.repository) / TARGET
    if not target.is_file():
        p.error(f'cannot find {target}')
    original = target.read_text(encoding='utf-8')
    result = transform(original)
    target.write_text(result, encoding='utf-8')
    print(f'Applied exclusive-mode patch to {target}')


if __name__ == '__main__':
    main()
