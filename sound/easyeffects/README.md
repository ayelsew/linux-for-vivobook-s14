# EasyEffects presets from the Windows Dolby tuning

Speaker presets for EasyEffects 8.x, built from the Dolby Atmos (DAX3) tuning that Windows uses on this
laptop. See [Good on Windows.md](../Good%20on%20Windows.md) for what the Dolby file contains.

The presets here are for speakers only. [PENDING] P3 connector presets

## Install

Needs `easyeffects` and the LV2 version of the Linux Studio Plugins (`sudo pacman -S easyeffects lsp-plugins-lv2`).
Without it EasyEffects shows the plugins but they do nothing.

```sh
./install.sh                                   # speakers get S5406SA-Dolby-music-v2
./install.sh --preset S5406SA-Dolby-dynamic-v2 # or pick another one
./install.sh status
./install.sh uninstall
```

It runs as your user, with no sudo. It copies the presets, autoloads the chosen one **on the speakers only**
(headphones, Bluetooth and USB DACs stay flat) and starts EasyEffects at login in the background. You can change
the speaker preset later in EasyEffects → Presets → Autoload.

EasyEffects keeps its presets and settings per user, so **each account runs `install.sh` once**, logged in as
itself.

## Presets

| Preset | Dolby profile | Difference |
|---|---|---|
| `S5406SA-Dolby-dynamic` | dynamic | Mid cut, small boost at 9 kHz, +2.5 dB on highs Dobly is more "inteligent" by change it on demand, but this is the base |
| `S5406SA-Dolby-movie` | movie | Less mid cut, some low-mid (234–328 Hz) |
| `S5406SA-Dolby-music` | music | Same mid cut, strong high boost (+7 dB at 9 kHz, +5.5 dB at 13.9 kHz) |
| `S5406SA-Dolby-game` | game | Less cut at 1–3 kHz, boost at 7 kHz |
| `S5406SA-Dolby-voice` | voice | Mid cut plus −4 dB at 1.2 kHz, no high boost |
| `S5406SA-Dolby-music-v2` | music | Music plus an EQ measured against Windows: −1.9 dB at 1 kHz, −1 dB at 3.2 kHz, +0.7 dB at 10 kHz. Within 0.5 dB of Windows Music (IEQ Off) |
| `S5406SA-Dolby-dynamic-v2` | dynamic | Dynamic plus a gentle multiband leveler (ratio 1.7) in front and a matching EQ: moves with the music like Dolby Dynamic |

`presets/raw/` keeps the pure first conversion, as it came out: Dolby's +6 dB boost, the
compressor group gains (+1 dB lows, +2.5/+3 dB highs), no limiter oversampling and narrower EQ bells
(bandwidth = band spacing, up to 0.6 dB ripple between band centers). On Linux it sounded harsh (cymbals),
and I really don't know why. The presets in `presets/` differ from those, I turned down +6 dB to +3 dB.



## Rebuild

Needs the Dolby XML, copied from Windows
(`C:\Windows\System32\DriverStore\FileRepository\dax3_ext_rtk.inf_amd64_*\`). Then:


---

Author: [@ayelsew](https://github.com/ayelsew)
