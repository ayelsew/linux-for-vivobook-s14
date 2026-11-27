# Sound: tech debt

## Volume curve and speaker cap (postponed 2026-11-26)

**Problem.** The Linux volume slider is much quieter than Windows in the low and mid range. The top 2–3 dB distort on
both systems (a limit of the speakers and amplifier). Measured in `validate.md` (Q2, Q4, Q6):

| Slider | Windows | Linux (cubic) | Linux slider for the Windows level |
|---|---|---|---|
| 20 % | −23.65 dB | ≈ −42 dB | ≈ 40 % |
| 50 % | −10.33 dB | ≈ −18 dB | ≈ 67 % |
| 85 % | ≈ −2.4 dB | ≈ −4.2 dB | ≈ 91 % |

The Windows curve is close to `gain = x^1.7` (Linux is `x^3`). Workaround until fixed: turn the slider up more and
stay under about 89 % (−3 dB).

**Why it can't be changed by config today.** The card (`sof-hda-dsp`, ALC294) runs in **UCM** mode. In PipeWire 1.6.11
ACP, UCM profile sets start with an empty decibel-fix table (`spa/plugins/alsa/acp/alsa-ucm.c`, `ps->decibel_fixes`)
and UCM paths have no `volume-limit`. pipewire-pulse always maps the slider with the cubic curve, and plasma-pa has no
curve option. `api.alsa.ignore-dB` makes the curve worse (linear steps, 20 % ≈ −52 dB).

**Planned fix.** Disable UCM for this card only and use a custom ACP profile set in
`~/.config/alsa-card-profile/mixer/profile-sets/` (ACP reads it from there, no sudo), selected by a WirePlumber rule
(`api.alsa.use-ucm = false`, `device.profile-set = ...`):
- A `[DecibelFix Speaker]` table that relabels each hardware step so that slider % gives the Windows dB.
  Step `n` has real dB `−65.25 + 0.75·n` (0–87). Real −3 dB (step 83) gets the label 0 dB, and steps above it get
  labels above 0 dB, so 100 % is capped at −3 dB.
- A custom speaker path with `Master` set to `volume = zero` (fixed at 0 dB), so the whole volume goes through
  `Speaker` and the table.
- The same wiring as the UCM HiFi verb (from `alsaucm -c hw:0 dump text`):

| Device | PCM | Controls | Jack |
|---|---|---|---|
| Speaker | `hw:0,0` | Master + Speaker | – |
| Headphones | `hw:0,0` | Master + Headphone | Headphone Jack |
| Internal mic (DMIC) | `hw:0,6` | Dmic0 | – |
| Headset mic | `hw:0,0` capture | Capture + Mic Boost | Headset Mic Jack |
| HDMI 1/2/3 | `hw:0,3` / `4` / `5` | – | `HDMI/DP,pcm=N Jack` |

**Risk.** A wrong line in the profile can hide a device, leave it silent or break headphone switching. Test every row
above (plug headphones in and out), and check that the internal mic still works (SOF DMIC controls such as
`Dmic0 Capture DRC`, `TDFB`). Undo: delete the WirePlumber rule and the profile set, then
`systemctl --user restart pipewire wireplumber pipewire-pulse`.

**Priority: low.** It is comfort only (where the slider sits), not sound quality.

---

Author: [@ayelsew](https://github.com/ayelsew)
