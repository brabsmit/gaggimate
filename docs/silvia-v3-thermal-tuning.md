# Silvia V3 Thermal Tuning Proposal

## Problem

Shot profiles show a ~10°C temperature drop during extraction (94°C → 84°C over 25 seconds) on a Rancilio Silvia V3 with Gaggimate Pro 1.2. The single boiler (~300ml, 1100W heater) cannot keep up with the thermal demand of continuous water flow.

## Current PID Settings

| Parameter | Value |
|---|---|
| Kp | 112.315 |
| Ki | 0.658 |
| Kd | 1436.887 |
| Kff | 0.0 |
| Flow @ 1 bar | 10.205 |
| Flow @ 9 bar | 5.521 |
| Temp offset | 5°C |

## Proposed Config Changes

### 1. Enable thermal feedforward (Kff: 0.0 → 0.5)

With Kff=0, the heater is purely reactive — it waits for temperature to drop before responding. The feedforward system calculates thermal power needed based on flow rate and temperature delta (setpoint minus incoming water temp). At ~2 ml/s extraction flow and a 71°C delta, the boiler needs ~594W just to maintain temperature. Feedforward applies this proactively when the pump starts.

Start at 0.5, increase to 0.7–0.8 if temperature still drops too fast.

### 2. Increase integral gain (Ki: 0.658 → 2.0)

Ki is too low to compensate for sustained heat extraction during a shot. The integral term accumulates too slowly to fight ongoing thermal loss. Increasing 3x allows faster correction of the steady-state temperature droop that feedforward doesn't fully cover.

## Proposed Code Change

**File:** `lib/GaggiMateController/src/peripherals/Heater.cpp` — `calculateSafetyScaling()`

The safety scaling function throttles feedforward to 70% when the boiler is at setpoint (tempError=0). This is exactly when a shot starts and the thermal shock is greatest. Combined with the smoothing filter (safetyAlpha=0.85), feedforward takes several loop cycles to reach full power, by which time the boiler has already lost several degrees.

**Current:**
```cpp
float Heater::calculateSafetyScaling(float tempError) {
    if (tempError > 1.0f) {
        return 0.0f;
    } else if (tempError >= 0.0f) {
        return 0.7f + 0.3f * (1.0f - tempError / 1.0f);
    } else if (tempError > -1.0f) {
        return 0.7f + 0.3f * std::abs(tempError) / 1.0f;
    } else {
        return 1.0f;
    }
}
```

**Proposed:**
```cpp
float Heater::calculateSafetyScaling(float tempError) {
    if (tempError > 1.0f) {
        return 0.0f;
    } else if (tempError >= 0.0f) {
        return 0.95f + 0.05f * (1.0f - tempError / 1.0f);
    } else {
        return 1.0f;
    }
}
```

This raises the minimum safety floor from 70% to 95% at setpoint and removes the dead zone between 0 and -1°C. Feedforward only reduces when the boiler is above setpoint (where backing off is appropriate). Apply this change after enabling Kff and validating the config changes above.

## Validation Plan

1. Set Kff=0.5, pull a shot, compare temperature curve to baseline profiles (10.json, 11.json, 12.json)
2. If drop is still >5°C, increase Kff to 0.7
3. Apply Ki=2.0, pull another shot, verify steady-state droop improves
4. Apply the safety scaling code change, pull a shot, verify the initial temperature dip at shot start is reduced
