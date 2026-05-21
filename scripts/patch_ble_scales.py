"""PlatformIO pre-build patch: fix a per-advertisement heap leak in the
esp-arduino-ble-scales dependency.

EurekaScalesPlugin::handles() calls NimBLEUtils::buildHexData(nullptr, ...), which
malloc's a buffer and transfers ownership to the caller, but never frees it. During
continuous BLE scanning (BLEScalePlugin scans with start(0) whenever the machine is out
of standby) this leaks one block per ambient advertisement until the heap is exhausted
and AsyncTCP can no longer allocate connection buffers -> web UI becomes unreachable.

The dependency is pulled from gitignored .pio/libdeps, so a clean build would silently
reintroduce the leak. This script reapplies the fix on every build. It is idempotent: if
the fix is already present (or the file/dependency is absent, e.g. the controller env)
it does nothing.

The canonical fix is recorded in patches/esp-arduino-ble-scales-buildhexdata-leak.patch.
Remove this script + its extra_scripts line once the upstream fix lands in
gaggimate/esp-arduino-ble-scales and the dependency is re-pinned to the merged commit.
"""
import os

Import("env")  # noqa: F821  (provided by PlatformIO)

BUGGY = """    char *pHex = NimBLEUtils::buildHexData(nullptr, (uint8_t*) deviceData.c_str(), deviceData.length());
    std::string md(pHex);"""

FIXED = """    char *pHex = NimBLEUtils::buildHexData(nullptr, (uint8_t*) deviceData.c_str(), deviceData.length());
    if (pHex == nullptr) {
      return false;
    }
    std::string md(pHex);
    free(pHex); // buildHexData(target=nullptr,...) malloc's and transfers ownership; must free or it leaks per advertisement"""

libdeps_dir = env.subst("$PROJECT_LIBDEPS_DIR")
pioenv = env.subst("$PIOENV")
eureka = os.path.join(libdeps_dir, pioenv, "esp-arduino-ble-scales", "src", "scales", "eureka.h")

if not os.path.isfile(eureka):
    # Dependency not present in this env (e.g. controller) — nothing to patch.
    Return()  # noqa: F821

with open(eureka, "r", encoding="utf-8") as f:
    src = f.read()

if "free(pHex)" in src:
    print("[patch_ble_scales] eureka.h already patched; skipping")
elif BUGGY in src:
    with open(eureka, "w", encoding="utf-8") as f:
        f.write(src.replace(BUGGY, FIXED, 1))
    print("[patch_ble_scales] applied buildHexData leak fix to eureka.h")
else:
    print("[patch_ble_scales] WARNING: expected buggy pattern not found in eureka.h; "
          "the upstream source may have changed — review the fix manually")
