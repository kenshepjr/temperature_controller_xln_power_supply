# Single Heater PID Controller — XLN / ISR

A Python-based GUI application for controlling a substrate heater using a BK Precision XLN3640 DC power supply and an Omega DP32PT thermocouple reader, with a software PID controller for closed-loop temperature regulation. Supports manual voltage/current setpoints and automatic PID mode with a configurable temperature ramp rate and a preheat sequence.

## Features

- **Manual and Auto (PID) Mode**: Toggle between direct voltage control and closed-loop PID temperature control from the GUI
- **Temperature Ramp Rate Limiting**: Actual setpoint ramps toward the desired setpoint at a configurable rate (default 0.35 °C/s max); ramp rate is calculated from thermocouple history and displayed live
- **Ramp Rate Safety Indicator**: The ramp rate display turns red if the measured rate exceeds 0.3 °C/s (20 °C/min limit stated in the GUI)
- **Preheat Sequence**: Sets a fixed preheat voltage (4.0 V), runs a 5-minute countdown, then activates PID at countdown end
- **Live Plotting**: Real-time temperature and PID setpoint plots with full-range and scrolling time-window views
- **Data Logging**: Timestamped automatic save of heater and PID data to `.npy` on quit
- **PID Integrator Set Button**: Manually seed the integrator to the current voltage setpoint to reduce startup transients

## Requirements

### Hardware

- BK Precision XLN3640 DC Power Supply (0–36V, 40A)
- Omega DP32PT Thermocouple Reader
- Serial/USB connections to both instruments

### Software Dependencies

```
numpy
matplotlib
tkinter  (included with standard Python)
pyserial
```

### Required Modules (same directory)

```
mod_thermocouple.py       # Omega DP32PT interface
mod_PID_XLN_ISR.py            # PID controller
mod_XLN3640.py            # BK Precision XLN3640 interface (not included in this repo)
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/kenshepjr/single_heater_pid_xln_isr
cd single_heater_pid_xln_isr
```

2. Install required dependencies:
```bash
pip install numpy matplotlib pyserial
```

3. Update COM port assignments in the main script:
```python
ports['BKP PS'] = 'COM28'   # BK Precision XLN3640 power supply
ports['TC']     = 'COM13'   # Omega DP32PT thermocouple
```
Linux equivalents are commented out in the script:
```python
# ports['BKP PS'] = '/dev/ttyUSB0'
# ports['TC']     = '/dev/ttyUSB1'
```

## Usage

### Basic Operation

1. Connect the XLN3640 and thermocouple reader to USB/serial
2. Update COM port assignments as above
3. Run the latest working version:
```bash
python cont_single_heater_PID_XLN_ISR_V3.py
```

### GUI Layout

The window has two side-by-side panels: **Heater Temperature** (left) and **PID Loop** (right).

#### Heater Temperature Panel

| Section | Control | Description |
|---|---|---|
| Plot | Temperature vs Time | Live thermocouple reading; Full Time / Delta T radio buttons |
| Thermocouple | Temperature (C) | Live readout from Omega DP32PT |
| Thermocouple | Ramp Rate (°C/s) | Measured over last 60 data points; turns red if > 0.3 °C/s |
| Power Supply | Actual V / A / Ω / W | Live readback from XLN3640 |
| Power Supply | Set-Point V / A | Editable; press Enter or click away to apply |
| Power Supply | Output Enable/Disable | Toggles XLN3640 output; indicator oval green = on, red = off |
| Widgets | Clock (min) | Elapsed time since app start |
| Widgets | Data Point | Update loop iteration counter |
| Widgets | Quit | Disables output, saves data, closes ports, exits |

#### PID Loop Panel

| Section | Control | Description |
|---|---|---|
| Plot | Desired SP / Actual SP vs Time | Live PID setpoint tracking plot |
| Mode Select | Switch to Auto / Manual | Toggles PID mode; indicator rectangle green = auto, red = manual |
| Mode Select | Enable Preheat | Starts 5-minute preheat at 4.0 V, then activates PID at end of countdown |
| Mode Select | Timer (mm:ss) | Countdown display during preheat; read-only during sequence |
| PID Variables | Desired Set-Point (C) | Target temperature entered by user |
| PID Variables | Actual Set-Point | Ramped setpoint fed to PID (read-only) |
| PID Variables | Current Value | Live thermocouple reading fed to PID (read-only) |
| PID Variables | Error | Setpoint − CV (read-only) |
| PID Variables | Modified Value (MV) | PID output voltage sent to power supply (read-only) |
| PID Variables | Int | Current integrator value (read-only) |
| PID Variables | P / I / D | Editable gain values; press Enter or click away to apply |
| Ramp Rate | Ramp Rate (°C/s) | Desired ramp rate used by the setpoint ramping logic |
| Bottom | Set PID Integrator | Seeds integrator to current SP_V to reduce startup jump |

### PID Control Loop

Each update cycle (100 ms, 10 Hz):

1. The desired setpoint (D_SP) is stepped toward the actual setpoint (A_SP) by at most `max_ramp_rate × dt_seconds` = 0.35 × 0.35 = 0.1225 °C per step. This hardcoded `dt_seconds = 0.35` overrides the timer-derived value.
2. `C.update(CV)` computes `MV = Kp×error + Integrator + Kd×(error − prev_error)` with anti-windup clipping at ±50.
3. MV is clipped to [0, 24] V by the PID module's `Hi`/`Low` limits.
4. In Auto mode, MV is written directly to `Sub_PS.set_voltage()`.
5. Ramp rate is calculated from the last 60 data points. If > 0.3 °C/s, the ramp rate field turns red.

### Data Saving

On quit, data is saved automatically as a `.npy` file with timestamp format:
```
YYYY_MM_DD-HH_MM_SS_xln_Substrate_Heater.npy
```

The file contains heater and PID data horizontally stacked. Heater columns:

| Index | Column |
|---|---|
| 0 | Absolute timestamp |
| 1 | Time (min) |
| 2 | Temperature (°C) |
| 3 | Voltage setpoint (V) |
| 4 | Current setpoint (A) |
| 5 | Actual voltage (V) |
| 6 | Actual current (A) |
| 7 | Output state |
| 8 | Ramp rate (°C/s) |

PID columns follow (mode, time, D_SP, A_SP, CV, error, rate, Kp, Ki, Kd, integrator, derivator).

> **Known logging gap**: `'power'` is added to `Data_Structure_Heater.vars` in V3 and is displayed live, but `data_update()` and `save_prep()` do not include it in the saved arrays. Calculated power is not logged to disk.

## File Structure

### `cont_single_heater_PID_XLN_ISR_V3.py` *(latest working version)*

Main application containing:

- `PID_Display`: GUI class for the PID loop panel — setpoint entry, gain entry, preheat button, countdown timer, mode indicator, setpoint plot
- `Heater_GUI`: GUI class for the heater panel — temperature display, ramp rate indicator, power supply readback, voltage/current setpoint entry, output enable, temperature plot
- `Data_Structure_Heater`: Tkinter variable storage and logging for heater data
- `Data_Structure_PID`: Tkinter variable storage and logging for PID data
- `initialize_controllers()`: Opens serial connections, reads initial instrument state, initializes PID object with tuned gains
- `update()`: Main 100ms loop — ramp logic, PID calculation, safety checks, readback, plot updates
- `_quit()`: Disables power supply output, saves both data structures, closes serial ports

### `cont_single_heater_PID_XLN_ISR_V2.py`

Previous version. See Version History for differences.

### `mod_PID_XLN_ISR.py` / `mod_PID_ISR.py`

PID controller module (original author: J. Ulbrandt):

- `PID`: Discrete PID class with anti-windup
    - Output clipped to `[Low, High]` = [0.0, 24.0] V
    - Integrator clamped to `[Int_Min, Int_Max]` = [-50, 50]
    - If MV goes out of bounds, integrator is unwound by subtracting the last error contribution before clipping
    - `update(CV, dt=0.1)`: Computes new MV; `dt` parameter present but not used in calculations (discrete difference, not time-scaled)
- `ramp()`: Stub function, not implemented

### `mod_thermocouple.py`

Omega DP32PT interface:

- `TC`: Serial communication class
    - 19200 baud, 8 data bits, odd parity, 1 stop bit, 50ms timeout
    - `get_temp()`: Sends `*G110 \r`, reads response, parses the value after `+` and strips `\r`
    - `_readline()`: Manual byte-by-byte reader that terminates on `\r` (does not use `ser.readline()`)

## Communication Protocol — Omega DP32PT

| Parameter | Value |
|---|---|
| Baud rate | 19200 |
| Data bits | 8 |
| Parity | **Odd** |
| Stop bits | 1 |
| Timeout | 0.05 s |

Command to read temperature: `*G110 \r`

Response format: `+XXX.X\r` — value is parsed by splitting on `+` and stripping `\r`.

## Known Issues



- **`dt_seconds` hardcoded**: The update loop sets `dt_seconds = 0.35` unconditionally, overriding the timer-derived value of `dt/1000 = 0.1`. The actual setpoint step per loop iteration is therefore 3.5× larger than the timer interval implies.
- **Gain scheduling commented out**: V3 has the automatic Kd/Kp change at 250°C fully commented out. If the system was previously relying on this for high-temperature stability, it must be re-enabled manually.

## Multi-Controller Synchronization

A file-based synchronization scaffold is present but fully commented out in both versions. It writes `Substrate_Heater_Controller is ready` to `controller_ready.txt` and waits for all expected controllers before continuing. It is not active for standalone use.

Expected controllers when sync is active:
- `Substrate_Heater_Controller`
- `TPG261_Controller`
- `MKS_Pressure_Controller`
- `BKP_Arb_Waveform_Controller`
- `Ircon_Modline_Plus_Controller`

## Version History

### V2 — `cont_single_heater_PID_XLN_ISR_V2.py`

- Initial working version
- PID gains: `Kp=1.5`, `Ki=0.0010`, `Kd=25`
- `_countdown()` sets `enable_PID = 60` — PID activates 60 seconds **before** preheat countdown ends
- `_preheat()` else branch calls `Sub_PS.set_output(0)` explicitly to turn off the supply when preheat is cancelled, but does not call `GUI['Substrate']._output()` — the output indicator goes out of sync with actual hardware state
- `Data_Structure_Heater.keys` does not include `'power'` — no power readback or display
- Power supply panel has no Power (W) column
- Window frame label is `'Substrate Temperature'`; GUI dict key is `'Sub Heater GUI'`
- Gain scheduling at 250°C threshold active in the `update()` loop: Kd switches from 25 → 0.20, Kp from default → 0.5 above 250°C, back to 25 below

### V3 — `cont_single_heater_PID_XLN_ISR_V3.py` *(latest working version)*

Changes from V2:

- PID gains retuned: `Kp=1.5`, `Ki=0.0015` (+50%), `Kd=0.2` (was 25 — major reduction)
- `_countdown()` sets `enable_PID = 0` — PID activates at the **end** of the preheat countdown, not 60 s before
- `_countdown()` now sets `PID_Data.pid_vars['actual_sp']` to the live thermocouple reading on every tick during preheat, so PID starts from current temperature rather than 0°C
- `_countdown()` adds explicit `PID_Data.pid_vars['mode'].set(1)` at end of countdown for redundancy alongside `GUI['PID']._output()`
- `_preheat()` else branch removes `Sub_PS.set_output(0)` and relies solely on `GUI['Substrate']._output()` toggle
- `Data_Structure_Heater.keys` adds `'power'`; `initialize_controllers()` and `update()` call `Sub_PS.calculate_power()`; power displayed live in GUI — but not saved to `.npy` (see Known Issues)
- Power supply panel adds Power (W) read-only column
- Gain scheduling at 250°C is fully commented out
- Window frame label changed to `'Heater Temperature'`; internal dict key changed to `'Heater'`
- Default port changed from `COM9` to `COM28` for ISR lab setup; `COM9` left as commented-out alternative for UVM

## Configuration Options

### PID Output Limits (in `mod_PID_ISR.py`)

| Parameter | Value |
|---|---|
| `Hi` (max voltage output) | 24.0 V |
| `Low` (min voltage output) | 0.0 V |
| `Int_Max` | 50 |
| `Int_Min` | −50 |

### Update Loop

| Parameter | Value |
|---|---|
| Loop interval | 100 ms (10 Hz) |
| Ramp rate limit | 0.35 °C/s (hardcoded `max_ramp_rate`) |
| Ramp safety threshold (GUI red) | 0.3 °C/s |
| Ramp rate calculation window | 60 data points |

## License

MIT License — see LICENSE file for details.

## Authors

- Original PID module and thermocouple module: J. Ulbrandt
- Controller GUI: J. Ulbrandt, K. Shepherd Jr (edited 2025/03/31)

## Support

For issues, questions, or contributions, open an issue on the GitHub repository or contact the author. Manuals for the XLN3640 and Omega DP32PT should be placed in the `manuals/` directory.
