# Validate on Windows: where the volume goes and what Dolby does with it

Checklist for a Claude Code session (or a person) on the **Windows 11 side of the dual boot** of this
ASUS Vivobook S 14 S5406SA. It is self-contained: the Linux session's memory does not exist on Windows.
Write the answers in the **Results** section at the end of this file, with the date and how each was found.

## Why

On Linux (CachyOS, PipeWire 1.6, EasyEffects 8.3.3) we rebuilt the Windows Dolby DAX3 speaker tuning as
EasyEffects presets (`easyeffects/`, built from `DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml`, see
`Good on Windows.md`). Each preset does: +6 dB boost → 20-band EQ → speaker protection (multiband compressor
on 277–1163 Hz, thresholds −29 to −20 dBFS, from Dolby's "regulator") → limiter at −1 dBFS.

Result: the sound was **harsh** (cymbals hiss, lack definition). The volume slider is **almost mute at
0–20 %** and **distorts at 80–100 %**.

What we know on Linux (measured):
- The system volume slider is the **codec hardware gain** (ALSA control `Speaker`, 0–87 = −65.25 to 0 dB),
  applied **after** EasyEffects. EasyEffects always gets the full-level signal.
- So the speaker protection acts on the full-level signal at **any** volume.
- The volume slider uses a cubic curve (20 % ≈ −42 dB, 50 % ≈ −18 dB, 80 % ≈ −6 dB).
- The distortion near 100 % already happened with no effects at all (live USB test).

Hypothesis (**not verified**): the protection squashes the mids even at low volume, so the highs stick out.
Proposed fix: a PipeWire filter-chain virtual sink, so the volume is applied **before** the protection, with
the codec gain fixed at a safe maximum.

Before building that, we need to know how Windows does it.

Already known from the Dolby XML (read on Linux, 2026-11-26):
- `volume-modeler-enable` = **0 in every profile**. `volume-modeler` is Dolby's volume-dependent
  processing. So Dolby probably does **not** change its processing with the volume level.
- `volume-leveler-enable` = 1 only in `personalize_user1/2/3`. `ieq-enable` (Intelligent EQ) = 1 only in
  `dynamic` and `music`.
- `regulator-enable` = 1 in every profile. In the `<tuning-vlldp>` block, `regulator-speaker-dist-enable` = 1
  and the thresholds are the ones above.
- There is only one endpoint in the XML: `internal_speaker`. No tuning for headphones.

If Dolby ignores the volume and Windows also applies the volume in the codec after Dolby, then **Windows has
the same order as Linux today**, and the harshness has another cause. That is what this checklist must find out.

## Rules

- **Read only.** Don't change drivers, registry, Dolby or Realtek settings, except for the listening tests
  below. Put every setting back as you found it.
- Don't copy Dolby, Realtek or ASUS files into the repository (they are proprietary). Record facts and
  numbers only.
- No admin rights needed, except where noted.

## Questions

### Q1. Is the speaker volume applied in hardware (codec) or in software?

Definitive method: `IAudioEndpointVolume::QueryHardwareSupport` on the speaker endpoint. If bit
`ENDPOINT_HARDWARE_SUPPORT_VOLUME` (0x1) is set, the volume is in the codec, after the APOs. If not, the
audio engine applies it in software.

How: PowerShell with a small C# `Add-Type` (COM interop: `MMDeviceEnumerator` →
`GetDefaultAudioEndpoint(eRender, eMultimedia)` → `Activate(IAudioEndpointVolume)`). Also record:
- `QueryHardwareSupport` (all bits: 0x1 volume, 0x2 mute, 0x4 meter)
- `GetVolumeRange` (min, max, step in dB). Compare with the Linux codec range: −65.25 to 0 dB, 0.75 dB steps.
- The device name, so we know it was the speaker endpoint ("Speakers (Realtek(R) Audio)").

Make sure the default playback device is the speakers, not headphones, HDMI or Bluetooth.

### Q2. Volume curve: slider % → dB

With the same COM interface: for slider 10, 20, 30 … 100 %, `SetMasterVolumeLevelScalar` then
`GetMasterVolumeLevel` (dB). Or just read it at a few positions while moving the slider by hand. Put the
original volume back afterwards.

Linux for comparison: 20 % ≈ −42 dB, 50 % ≈ −18 dB, 80 % ≈ −6 dB, 100 % = 0 dB.

### Q3. Where does Dolby sit in the chain?

Registry, read only: `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\{endpoint-id}\FxProperties`.
The value names `{d04e05a6-594b-4fb6-a80d-01af5eed7d1d},N` hold the APO CLSIDs:

| N | Slot |
|---|---|
| 1 | Pre-mix (SFX, per stream) |
| 2 | Post-mix (MFX, legacy) |
| 3 | UI |
| 5 | Stream effect (SFX) |
| 6 | Mode effect (MFX) |
| 7 | Endpoint effect (EFX) |

Resolve each CLSID under `HKCR\CLSID\{…}` (or `HKLM\SOFTWARE\Classes\AudioEngine\AudioProcessingObjects`)
to know which is Dolby and which is Realtek. Record the slot of each one, and also the speaker endpoint id.

### Q4. Does Dolby's sound change with the volume? (listening)

Dolby Access, profile **Dynamic**. Same song (with cymbals and bass), Dolby on and off:
- at low volume (~20 %) and at high volume (~80 %).
- Does the balance (bass / mids / highs) change with the volume, or only the loudness?
- Is it harsh like on Linux? Are the cymbals clean?
- Does it distort at 90–100 %?

Write down the Dolby Access settings in use: profile, Intelligent EQ (Off / Open / Rich / Focused, or
balanced / warm / detailed), "Dolby Atmos for built-in speakers", volume leveler, dialog enhancer.

### Q5. Is anything protecting the speakers outside Dolby?

- Does the Realtek Audio Control app have speaker protection, a limiter or "loudness"?
- With Dolby off (Dolby Access → off), at 100 % volume: does it distort like Linux at 90–100 %?
  If Windows without Dolby distorts too, the protection is Dolby's alone. If not, something else (Realtek APO
  or driver) protects or limits the volume.

### Q6. Is the 0–20 % range also quiet on Windows?

Simple listening: at 10 % and 20 %, is it clearly audible? Compare with Linux, where it is almost mute.

### Q7. Measure the speakers with a USB mic (added 2026-11-26)

**Why.** On Linux, a USB mic and pink noise showed (table below) that the bare speakers are fairly even from 250 Hz
to 10 kHz and put out nothing measurable below 125 Hz. The Linux Music preset adds **about +10 dB at 8–16 kHz** over
the bare speakers. That is exactly Dolby's Music EQ as written in the XML, and it is the likely cause of the harsh
cymbals. So the question is no longer "did we convert Dolby right", but **what Windows really plays**. Whatever Windows
does that the XML doesn't show (Intelligent EQ, the Realtek APOs after Dolby, anything else) shows up as a difference
against the Linux numbers.

This part changes two settings for the test (speaker volume and mic level). Write down the old values first and put
them back at the end.

**Setup. It must match the Linux measurement, or the numbers can't be compared:**
- **Same mic, same place.** The USB mic "Usb Audio Device" (Generalplus `1b3f:2008`, mono, 16-bit, 48 kHz). The
  laptop and the mic were marked on the desk before rebooting: don't move either of them.
- **Mic level +21.0 dB.** Settings → System → Sound → Input → Usb Audio Device → Properties (or the classic Sound
  control panel → Recording → Properties → Levels; right-click the number to show dB). Advanced tab: 48000 Hz,
  16 bit. If there is an AGC / "Automatic gain" checkbox, turn it off. Audio enhancements off. On Linux the mic's
  hardware AGC was off and its gain was +21 dB (ALSA `Mic Capture Volume` 22 of 30, −12 to +33 dB).
- **Speaker volume −13.3 dB**, set exactly with `IAudioEndpointVolume::SetMasterVolumeLevel(-13.3)` on the speaker
  endpoint (the COM code from Q1/Q2). Not by eye on the slider: the Windows curve is different (40 % ≈ −13.6 dB).
  On Linux the slider was at 60 %, which is −13.3 dB on the codec.
- **Default playback: Speakers (Realtek(R) Audio).** Spatial sound off. Close other audio apps. Quiet room.
- **Test signal:** `python sound/measure/signals.py <dir>` writes `pink-6s.wav` (6 s pink noise, −20 dBFS RMS). Its
  SHA-256 must be `a0f34603600d2e0c2a311b74c0d045540b003ddacb7f1f823a6477b55d332996`. Without Python, copy the file
  from Linux (`logs/sound-loops/pink-6s.wav`).

**Each take:** start recording, play `pink-6s.wav` 1 s later through the default output (any player without its own
effects, for example `System.Media.SoundPlayer` in PowerShell), stop at 8 s. Save as WAV, 48 kHz, mono, 16-bit. Any
recorder that doesn't process the sound works (ffmpeg with `-f dshow`, or a small WASAPI capture in C# like the Q1
code). Check, read only, that the mic's capture endpoint has no APOs in its `FxProperties`.

| File | Dolby Access |
|---|---|
| `win-silence.wav` | nothing playing, 4 s |
| `win-dolby-off.wav` | Dolby off |
| `win-music-ieq-off.wav` | Music, Intelligent EQ Off |
| `win-music-ieq-balanced.wav` | Music, Intelligent EQ Balanced |
| `win-dynamic.wav` | Dynamic |

Also note the recorded peak level of each take. On Linux the loudest take (Music) peaked at −13.2 dBFS. A take that
peaks near 0 dBFS has clipped: lower the mic level for every take, and write down the new value.

**Analysis:** `python sound/measure/analyze.py A.wav B.wav --from 1.6 --to 6.8` prints each third-octave band of A,
of B and B − A. Without Python, bring the WAV files back to Linux (USB stick) and analyze them there. Fill these:
1. `win-dolby-off` alone, next to **Linux Flat**. Same mic, gain, volume and signal, so the difference is what
   Windows does with Dolby off. That's the Realtek layer, or Dolby still processing when "off".
2. `win-music-ieq-off` − `win-dolby-off`, next to **Linux Music − Flat**. Is Dolby itself +10 dB at 8–16 kHz?
3. `win-music-ieq-balanced` − `win-music-ieq-off`. What Intelligent EQ does, on average.
4. `win-dynamic` − `win-dolby-off`, next to **Linux Dynamic − Flat**.

Pink noise is a steady signal. Intelligent EQ and the speaker protection react to the content, so with music they may
behave differently. This is a first, repeatable look, not the full story.

**Also, read only: Realtek's own settings.** Look for parameters of the Realtek APOs (Q3) in `realtekuapo2.inf`, the
HDA extension INF, and the Realtek device key under
`HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}\00xx`. Look for names with EQ,
biquad, speaker, GFX/LFX, gain or limiter in them. Record names, types and decoded numbers, not the proprietary files.

**Linux reference** (2026-11-26, CachyOS, EasyEffects 8.3.3, same mic at +21 dB, speaker at −13.3 dB,
`pink-6s.wav`, analysis 1.6–6.8 s). Values in dBFS of the recording, not acoustic SPL; the mic's own response is in
the absolute column, but cancels in the differences. Music is the final preset (high-pass 80 Hz); Dynamic was
measured with the high-pass at 125 Hz, which only affects 125–250 Hz. Below 100 Hz every take was at the silence
level. Peaks: Flat −18.0, Music −13.2, Dynamic −16.6 dBFS.

| Band (Hz) | Silence | Linux Flat | Linux Music − Flat | Linux Dynamic − Flat |
|---|---|---|---|---|
| 100 | -75.9 | -74.7 | -0.5 | -0.2 |
| 125 | -76.9 | -71.1 | -2.2 | -4.5 |
| 160 | -76.7 | -60.1 | -0.9 | -4.0 |
| 200 | -78.1 | -50.5 | +0.1 | -1.8 |
| 250 | -78.7 | -45.8 | +0.5 | -0.5 |
| 315 | -79.7 | -43.6 | +0.0 | -0.3 |
| 400 | -80.6 | -44.2 | -0.2 | -0.1 |
| 500 | -82.2 | -44.1 | -0.8 | +0.0 |
| 630 | -82.8 | -44.9 | -1.3 | +0.0 |
| 800 | -84.0 | -45.9 | -1.4 | +1.2 |
| 1000 | -84.4 | -45.6 | -3.3 | +0.4 |
| 1250 | -85.8 | -42.7 | -5.8 | -1.7 |
| 1600 | -86.4 | -42.7 | -4.0 | -0.6 |
| 2000 | -85.5 | -44.5 | -1.3 | +1.0 |
| 2500 | -86.4 | -42.5 | +0.9 | +2.2 |
| 3150 | -85.5 | -43.9 | +1.5 | +2.9 |
| 4000 | -85.3 | -44.0 | -0.5 | +1.8 |
| 5000 | -85.0 | -43.2 | -0.4 | -0.1 |
| 6300 | -84.5 | -44.8 | +1.5 | +1.3 |
| 8000 | -84.1 | -43.7 | +9.7 | +4.4 |
| 10000 | -83.2 | -42.2 | +11.1 | +4.8 |
| 12500 | -82.3 | -47.9 | +11.1 | +3.7 |
| 16000 | -81.6 | -48.7 | +9.5 | +3.0 |

### Q8. Record the same music on both systems (added 2026-11-27)

**Why.** Q7 showed that with pink noise the Linux presets and Windows Dolby have the same spectrum, yet Windows still
sounds better by ear. Pink noise is steady, while music changes all the time, so the difference is probably in how
the processing reacts to it (regulator, Intelligent EQ, limiter). This test plays the **same music, byte for byte,**
on both systems and records it with the same mic, so the recordings can be compared by ear (blind, level-matched)
and over time.

**Test file.** `logs/music-test/music-test.wav`, built on Linux by `sound/measure/musictest.py build` from two songs
recorded from Spotify with `record-loop.sh`. 56.6 s, 48 kHz, 24-bit stereo. SHA-256
`7b18fb4ac3154ddcef9bbc920ff27f4a12cfdfc5f01c797e2d222a78ece9b696`. Layout (also in `music-test.json`):

| Time in file | What |
|---|---|
| 1.0 s | sync chirp (0.3 s sweep 300 Hz–6 kHz, −12 dBFS) |
| 2.3–27.3 s | *Conquer*, 2:44.5–3:09.5 |
| 28.8 s | sync chirp |
| 30.1–55.1 s | *The Diner*, 1:34.0–1:59.0 |

It is copyrighted music: copy it by USB stick, keep it in `logs/` (gitignored), never commit or upload it. Check
the SHA-256 on Windows before using it (`Get-FileHash`).

**The music must reach Dolby unchanged.** On Linux this is proven: `musictest.py null` on a recording of the
EasyEffects input found every sample identical to the file (2026-11-27). On Windows:
- Play with a player that does no processing and no resampling, at stream volume 1.0. The device format must be
  48 kHz (as in Q7). Prefer a small WASAPI **shared-mode** render client in C# (24-bit int → float32 is exact).
  `System.Media.SoundPlayer` may not accept 24-bit files.
- Try a null test: record the speaker endpoint with WASAPI **loopback** while playing the file, save it as float32
  or 24-bit WAV, and run `python sound/measure/musictest.py null music-test.wav loopback.wav`. If it is bit-exact,
  the file reaches the engine unchanged. If it is not, write down what changed: loopback may be taken after the
  APOs, so a non-exact result with Dolby on doesn't prove anything; with Dolby **off** it should be close.

**Setup: the same as Q7, except the mic level.** Same mic and the same desk marks, AGC off, recorded in **RAW mode**
(skips the mic's Voice Clarity APOs), speaker set to **−13.30 dB** with `SetMasterVolumeLevel` (as in Q7), spatial
sound off, other audio apps closed. **Mic +15.0 dB**, not +21: at +21 dB the Linux music takes peaked at −1.9 dBFS,
too close to clipping, so they were redone at +15 dB. Write down the old values and put them back afterwards.

**Each take:** start recording, start the file 1 s later, stop at 60 s. 48 kHz, mono, 16-bit WAV. Note the peak.
Files go to `logs/win-music/`:

| File | Dolby Access |
|---|---|
| `win-music-dolby-off.wav` | Dolby off |
| `win-music-music-ieq-off.wav` | Music, Intelligent EQ Off |
| `win-music-music-ieq-balanced.wav` | Music, Intelligent EQ Balanced |
| `win-music-dynamic.wav` | Dynamic |

**Linux takes, done 2026-11-27** (CachyOS, EasyEffects 8.3.3, mic +15 dB, speaker slider 60 % = −13.31 dB, ALSA
`Speaker` at −12.75 dB, played with `pw-play --target easyeffects_sink`), in `logs/linux-music/`:

| File | Preset | Peak dBFS | RMS dBFS |
|---|---|---|---|
| `linux-silence.wav` | (nothing playing, 4 s) | −49.9 | −56.6 |
| `linux-music-Flat.wav` | Flat (no effects) | −8.7 | −27.2 |
| `linux-music-S5406SA-Dolby-music.wav` | Music | −7.9 | −27.6 |
| `linux-music-S5406SA-Dolby-dynamic.wav` | Dynamic | −7.7 | −26.6 |

The first try at +21 dB is in `logs/linux-music/gain21/`; it measured exactly 6 dB higher, so the mic was not
compressing. A Windows take must not peak above about −1 dBFS: if one does, lower the mic for all four takes and write
down the new value. Bring the Windows files back to Linux. The comparison script is written there.

## What each answer means for Linux

| Finding | Consequence on Linux |
|---|---|
| Q1 hardware volume + Dolby ignores volume (Q4 no balance change) | Windows has the same order as Linux. The filter-chain isn't needed for that reason; look for the harshness elsewhere (Intelligent EQ, high-frequency gains, limiter) |
| Q1 software volume (before or inside the audio engine) | Dolby sees the volume-scaled signal: build the filter-chain sink with the volume before the protection |
| Q2 curve much flatter than cubic | Change the volume curve on Linux (or the codec range) |
| Q5 Windows without Dolby is clean at 100 % | The codec max or a Realtek limit differs: find it before setting a safe codec maximum on Linux |
| Q7 Windows Music − Dolby off is also ≈ +10 dB at 8–16 kHz | Dolby really is that bright; the softer highs on Windows come from Intelligent EQ (Q7.3) or from the Realtek layer (Q7.1). Copy those |
| Q7 Windows Music − Dolby off is much less than +10 dB in the highs | Something on Windows holds the highs back (Realtek APOs, or Dolby blocks the XML doesn't show). Copy the measured Windows difference onto the Linux preset instead of the XML values |
| Q7.1 Windows Dolby off differs from Linux Flat | That difference is the Realtek layer (or Dolby still active when off): add it to Linux as a fixed EQ |

## Results

### 2026-11-26: measured by a Claude Code session on Windows 11 Home 10.0.26300

Method: PowerShell + C# `Add-Type` COM interop (`MMDeviceEnumerator.GetDefaultAudioEndpoint(eRender,
eMultimedia)` → `IAudioEndpointVolume`), and read-only `reg query` / `Get-ItemProperty`. Volume restored
to its original value (scalar 0.5006) afterwards. Nothing else changed.

Default endpoint: **Speakers (Realtek(R) Audio)**, id `{0.0.0.00000000}.{1eebda14-61a1-4d8d-bdde-73c79badc0cd}`.
It was the only active render endpoint (headphones unplugged; HDMI, BT and USB not present).

#### Q1. Hardware volume: **yes**

| Call | Value |
|---|---|
| `QueryHardwareSupport` | **0x7**: volume + mute + meter all in hardware |
| `GetVolumeRange` | **−65.25 to 0 dB**, step 0.03125 dB |
| `GetVolumeStepInfo` | 51 steps (keyboard steps of 2 %) |
| `GetChannelCount` | 2 |

The range is exactly the Linux codec range (`Speaker` 0–87, −65.25 to 0 dB). So Windows uses the same codec
amplifier and applies the volume **after** the APOs (Dolby + Realtek), just like Linux does after EasyEffects.
The 0.03125 dB step is what the driver reports. The codec itself moves in 0.75 dB steps.

#### Q2. Volume curve: **much flatter than Linux**

| Slider | Windows (dB) | Linux (dB) |
|---|---|---|
| 1 % | −56.99 | |
| 2 % | −51.67 | |
| 5 % | −42.03 | |
| 10 % | −33.24 | |
| 20 % | **−23.65** | ≈ −42 |
| 30 % | −17.82 | |
| 40 % | −13.62 | |
| 50 % | **−10.33** | ≈ −18 |
| 60 % | −7.63 | |
| 70 % | −5.33 | |
| 80 % | **−3.34** | ≈ −6 |
| 90 % | −1.58 | |
| 100 % | 0.00 | 0 |

At 20 % Windows is about **18 dB louder** than Linux, and at 50 % about 8 dB louder. Windows reaches Linux's
"20 %" level (−42 dB) at only 5 %. This alone explains "almost mute at 0–20 %" on Linux. Both reach 0 dB at
100 %, so the top end is identical (and so is any distortion at 100 %, see Q5).

#### Q3. Chain on the speaker endpoint

`FxProperties` uses the **composite** keys (Windows 8.1+), not the single slots 1–7 in the table above. Each
composite list runs in order: Dolby first, then Realtek.

| Key `{d04e05a6-…},N` | Slot | APOs (in order) |
|---|---|---|
| 13 | Stream effect (SFX) | `{0EBD8605-…}` **Dolby** → `{905069CC-…}` Realtek CRtkAPOSFX2 |
| 14 | Mode effect (MFX) | `{90609662-…}` Realtek CRtkAPOMFX2 (no Dolby) |
| 15 | Endpoint effect (EFX) | `{0EBD8607-…}` **Dolby** → `{90705486-…}` Realtek CRtkAPOEFX2 |
| 19 | Offload SFX | `{0EBD8611-…}` **Dolby** |
| 20 | Offload MFX | `{0EBD8612-…}` **Dolby** → `{90C0662B-…}` Realtek CRtkAPOMFX2 |
| 1, 2, 3, 5, 6, 7 | legacy slots | not set |

- Dolby CLSIDs `0EBD86xx` aren't registered as normal COM classes. Property `{0ebd86xx-…},100` points them to
  device `SWD\DRIVERENUM\{25C1BC6B-…}#DOLBYAPO_DAX3APOSVC` ("DolbyAPO SWC Device"), package
  `dax3_swc_aposvc.inf`, version **3.30805.851.0**. That package includes `DolbyAPOvlldp*.dll`, which
  matches the `<tuning-vlldp>` block in the XML.
- Realtek APOs: `RltkAPOU642.dll` ("Realtek LFX/GFX DSP component"), package `realtekuapo2.inf`.
- Processing modes (`{d3993a3f-…},5/6/7`): SFX/MFX run on default, movies, media, communications and
  notification streams (MFX also on speech). EFX runs **default only**, so every stream goes through it.
- Services running: `DolbyDAXAPI`, `RtkAudioUniversalService`. Apps: Dolby Access 3.27.12250.0, Realtek
  Audio Control 1.51.352.0, ASUS PC Assistant 4.0.82.0.
- The Realtek `OVWrap2`/`OVWrapN` packages are OpenVINO/GNA/NPU runtimes. That looks like AI noise
  suppression for the microphone, not playback. Not confirmed.

**Conclusion of Q1–Q3:** the order is the same as on Linux today: Dolby DSP (including the regulator) on the
full-level signal, then the codec hardware gain. Dolby could get endpoint-volume notifications, but its
volume-dependent block (`volume-modeler`) is disabled in the XML. So **the filter-chain sink isn't needed to
copy Windows**. The real differences found so far:
1. **Volume curve** (Q2): Linux is 8–18 dB quieter in the low/mid range. Fix the curve on Linux.
2. **Realtek APOs run after Dolby** in SFX, MFX and EFX. Their processing isn't in the Dolby XML and wasn't
   copied to EasyEffects. It may add EQ or limiting, so this is a candidate for the harshness and distortion
   difference (Q5 listening will tell).

#### Q4. Dolby by ear (user, 2026-11-26)

- The Dolby Access UI says **Dynamic** "identifies the content and makes automatic adjustments". So Dynamic is
  probably **not a fixed preset**: it seems to switch or adapt the tuning according to the content. A fixed
  EasyEffects preset can't copy it exactly.
- **Game, Movie, Music and Voice sound clearly different** from each other.
- **Music** has its own Intelligent EQ choice: **Off / Detailed / Balanced / Warm**. Music with IEQ off is
  the most static profile, so it's the best match for a fixed EasyEffects preset.
- Windows **Spatial sound** was on. Turning it off made no audible difference.
- **85–100 %: slight distortion** (with Dolby on). Linux without effects also distorts near 100 % (live USB).
  So this is a **physical limit of the speakers/amplifier**, not a Linux problem. On the Windows curve, 85 %
  ≈ −2.4 dB codec gain.
- Not answered: does the balance change with volume, and Dolby on vs off at 20 / 80 %. Q4 opened new questions
  (what Dynamic really does) more than it answered the old ones.

#### Q5. Protection outside Dolby

- **Realtek Audio Console** shows only: volume (the same Windows endpoint volume), L/R balance, sample rate
  and bit depth. **No speaker protection, limiter or loudness setting for playback.** (The microphone page has
  many Realtek features: to look at later.)
- The Realtek APOs are still in the chain after Dolby (Q3), but nothing about them is exposed in the UI.
- **Dolby off at 100 %: the distortion is the same** as with Dolby on. Dolby's regulator doesn't prevent it.
  This confirms it is a hardware limit (Q4) and that nothing else on Windows protects the speakers from it.
- **Windows with Dolby off sounds close to Linux with the EasyEffects presets.** So the presets don't reproduce
  what makes Dolby sound good. Either they have little effect, or they miss the Dolby blocks that matter.
- The presets **are** applied: Linux without a preset sounds worse than with one. Ranking by ear, worst to best:
  **Linux raw < Linux preset ≈ Windows Dolby off < Windows Dolby on.**
- So "Windows Dolby off" is **not** raw speakers. Something still processes the sound there. Candidates
  (not verified): the **Realtek APOs**, which stay in the chain (Q3); or Dolby keeping its speaker tuning
  (audio-optimizer/regulator) when the Dolby Access switch is off. The presets seem to recover that base layer,
  but not what the Dolby profile adds on top.

#### Q6. Low volume

**10–20 % is clearly audible on Windows.** This matches Q2: Windows at 20 % is at −23.65 dB, against about
−42 dB on Linux.

### What this means for Linux

| # | Change | Source |
|---|---|---|
| 1 | **Use the Windows volume curve** (or one close to it) instead of the cubic curve. This fixes the almost-mute 0–20 %. | Q2, Q6 |
| 2 | **Cap the codec gain at about −3 dB** (≈ Windows 80–85 %). The top 2–3 dB distort on both systems. | Q1, Q4 |
| 3 | **No filter-chain needed for ordering.** Windows also runs Dolby on the full-level signal, before the codec gain. | Q1, Q3 |
| 4 | For the harshness, **compare with Dolby Music + IEQ Off**, not Dynamic. Dynamic adapts to content and a fixed preset can't copy it. Build or check the EasyEffects preset from the `music` profile with IEQ disabled, then compare by ear. | Q4 |
| 5 | Still unknown: what the Realtek APOs after Dolby do. They have no UI. | Q3, Q5 |
| 6 | **The presets sound like Dolby off** (they are applied and better than raw). List which Dolby blocks the presets copy (graphic EQ, audio-optimizer, bass enhancer, virtualizer, IEQ, dialog enhancer) and which they skip. What the profile adds on top (IEQ in Music, the profile-specific EQ and bass) is the part still missing. | Q5 |

### 2026-11-27: Q7 measured with the USB mic (Claude Code session on Windows 11 Home 10.0.26300)

**Setup, as asked:** same mic and same desk marks. `pink-6s.wav` regenerated with `signals.py`, SHA-256
`a0f34603…332996` (match). Mic endpoint set to **+21.0 dB** (range −12 to +33 dB, 1.5 dB steps, hardware: 0x7), and
the user turned off AGC in the Sound control panel. Speaker set to **−13.30 dB** with `SetMasterVolumeLevel`. Spatial
sound off. Old values written down and put back afterwards: speaker −3.69 dB (scalar 0.7816), mic +27.0 dB.

**Mic capture endpoint is not APO-free.** Its MFX slot (`{d04e05a6-…},14`) holds three Microsoft `VocaEffectPack`
(Voice Clarity) APOs, enabled in the default, speech and communications modes. ffmpeg/dshow would record through
them. So the takes were recorded with a small C# WASAPI client in **RAW mode** (`AUDCLNT_STREAMOPTIONS_RAW`; the
endpoint says it supports RAW, `{8943b373-…},2` = true). That mode skips the capture APOs. Device format 48 kHz, 1 ch,
16-bit. Engine float → 16-bit mono WAV. Playback with `System.Media.SoundPlayer` through the default output (so
through Dolby and Realtek), 1 s after the capture started. 8 s takes. Files in `logs/win-usb-mic/` (gitignored).

| File | Dolby Access | Peak dBFS |
|---|---|---|
| `win-silence.wav` | (nothing playing, 4 s) | −39.9 (DC/subsonic only; bands −75 to −89) |
| `win-dolby-off.wav` | Dolby off | −16.4 |
| `win-music-ieq-off.wav` | Music, IEQ Off | −13.0 |
| `win-music-ieq-balanced.wav` | Music, IEQ Balanced | −15.6 |
| `win-dynamic.wav` | Dynamic | −15.7 |

No take clipped. Mic level unchanged for all takes. Analysis `analyze.py --from 1.6 --to 6.8`. Below 100 Hz every
take is at the silence level, as on Linux.

| Band (Hz) | Win silence | Win Dolby off | 1. Win off − Linux Flat | 2. Win Music − off | Linux Music − Flat | 3. IEQ Balanced − Off | 4. Win Dynamic − off | Linux Dynamic − Flat |
|---|---|---|---|---|---|---|---|---|
| 100 | -77.9 | -75.5 | -0.8 | +0.8 | -0.5 | +1.8 | +1.5 | -0.2 |
| 125 | -80.8 | -68.7 | +2.4 | +0.7 | -2.2 | +2.7 | +1.6 | -4.5 |
| 160 | -80.6 | -56.6 | +3.5 | +0.9 | -0.9 | +2.6 | +1.9 | -4.0 |
| 200 | -80.6 | -46.7 | +3.8 | +0.5 | +0.1 | +2.1 | +1.5 | -1.8 |
| 250 | -82.9 | -42.4 | +3.4 | +0.4 | +0.5 | +1.8 | +1.4 | -0.5 |
| 315 | -83.3 | -40.4 | +3.2 | -0.7 | +0.0 | +1.5 | +0.6 | -0.3 |
| 400 | -83.8 | -41.0 | +3.2 | -1.9 | -0.2 | +0.7 | -0.5 | -0.1 |
| 500 | -85.3 | -41.2 | +2.9 | -3.1 | -0.8 | +0.9 | -1.1 | +0.0 |
| 630 | -85.6 | -42.3 | +2.6 | -3.8 | -1.3 | +0.9 | -0.8 | +0.0 |
| 800 | -87.4 | -43.3 | +2.6 | -4.0 | -1.4 | +1.2 | +0.4 | +1.2 |
| 1000 | -87.6 | -43.6 | +2.0 | -5.2 | -3.3 | +1.2 | +0.8 | +0.4 |
| 1250 | -88.8 | -41.4 | +1.3 | -7.9 | -5.8 | +1.0 | -1.6 | -1.7 |
| 1600 | -88.9 | -41.5 | +1.2 | -6.5 | -4.0 | +0.6 | -1.0 | -0.6 |
| 2000 | -88.3 | -43.6 | +0.9 | -3.8 | -1.3 | -0.1 | +0.5 | +1.0 |
| 2500 | -88.9 | -42.3 | +0.2 | -1.7 | +0.9 | -0.5 | +1.5 | +2.2 |
| 3150 | -87.9 | -43.5 | +0.4 | -0.4 | +1.5 | -1.0 | +2.4 | +2.9 |
| 4000 | -87.8 | -43.0 | +1.0 | -1.9 | -0.5 | -1.5 | +2.3 | +1.8 |
| 5000 | -87.5 | -42.4 | +0.8 | -1.3 | -0.4 | -1.8 | +0.5 | -0.1 |
| 6300 | -87.1 | -46.9 | -2.1 | +0.1 | +1.5 | -2.2 | +1.6 | +1.3 |
| 8000 | -86.9 | -41.3 | +2.4 | **+9.4** | +9.7 | -2.5 | +5.2 | +4.4 |
| 10000 | -86.1 | -42.2 | +0.0 | **+11.0** | +11.1 | -2.7 | +5.7 | +4.8 |
| 12500 | -85.3 | -45.4 | +2.5 | **+10.3** | +11.1 | -3.4 | +4.6 | +3.7 |
| 16000 | -84.7 | -51.3 | -2.6 | **+10.7** | +9.5 | -3.8 | +3.6 | +3.0 |

What it shows (pink noise, steady signal):
1. **Windows Dolby off ≈ Linux Flat**, plus about **+3 dB at 160–800 Hz**, fading to 0 by 2 kHz. Above 2 kHz they are
   within ±1 dB (the ±2.5 dB at 6.3k, 8k, 12.5k, 16k swing both ways, which looks like placement or noise, not EQ). So
   the Realtek layer, or whatever is still active with Dolby off, is a **gentle low-mid lift, not a big hidden EQ**.
   This matches the ear test (Q5: "Windows Dolby off ≈ Linux preset").
2. **Dolby Music really is +10 dB at 8–16 kHz on Windows**, the same as the Linux preset to within 1 dB. The XML
   conversion is right in the highs. The only difference: Windows dips **400 Hz–3 kHz about 2–2.5 dB deeper** than
   the Linux preset.
3. **Intelligent EQ Balanced** tilts toward warmer sound: +2 to +2.7 dB at 100–250 Hz, about +1 dB in the mids,
   −2.5 to −3.8 dB at 8–16 kHz. Music + Balanced is still about +7 dB over Dolby off in the highs.
4. **Dynamic matches Linux Dynamic** within about 1 dB from 250 Hz to 16 kHz. The only real difference is 125–200 Hz:
   Windows +1.5 to +1.9, Linux −1.8 to −4.5 (the 125 Hz high-pass in that Linux take).

**Realtek's own settings (read only).** The Realtek HDA device key (`…\{4d36e96c-…}\0002`, driver 6.0.9761.1,
`oem37.inf`) has only `Settings\EQ_AGC_CONTROL = 0`, `OmniSpeaker = 0`, `Win10Cloud = 0` and
`DefaultDefaultMicGain = 9600`. Some subkeys were not readable without admin. The INF has `SSTPPCfg\{GUID}\SPK\EFX|MFX`
entries with only `Enabled`, `Position` and `IsMandatory` flags, for many GUIDs (looks like a list for several
OEMs). **No EQ coefficients, gains or limiter values in readable form.** No `oem*.inf` names `realtekuapo2` or
`RltkAPOU64`, so that INF lives only in the DriverStore (not searched).

### What Q7 means for Linux

| # | Finding | Change |
|---|---|---|
| 7 | With steady pink noise, **Windows Dolby matches the Linux presets** (Music within 1 dB above 6 kHz, Dynamic within about 1 dB above 250 Hz). The +10 dB highs are real Dolby. | Don't cut the highs to "fix" the conversion. It isn't wrong. |
| 8 | Windows adds about +3 dB at 160–800 Hz even with Dolby off. | Add it to every preset as a fixed low-shelf/peak (≈ +3 dB, 160–800 Hz, back to 0 by 2 kHz). |
| 9 | Windows Music dips the mids 2–2.5 dB more (400 Hz–3 kHz). | Optional: deepen the Music mid dip by about 2 dB. Small. |
| 10 | IEQ Balanced = bass +2.5, highs −3. | A Linux "Music Balanced" preset: Music + that tilt. With #8, it softens the highs that sounded harsh. |
| 11 | Spectra match, but Windows still **sounds better** by ear (Q5). | The difference is probably **dynamic**, which pink noise doesn't show: how the regulator/compressor and IEQ react to music, or artifacts from the EasyEffects multiband compressor/limiter. Next test: record the **same music clip** on both systems with this setup, and compare spectra over time and by ear. |

### 2026-11-27: Q8 music takes (Claude Code session on Windows 11 Home 10.0.26300)

**Setup, as asked.** `logs/music-test/music-test.wav` SHA-256 `7b18fb4a…e9b696` (match). The user confirmed the desk
marks, Spatial sound off, other audio apps closed, mic AGC off. Mic set to **+15.0 dB**, speaker to **−13.30 dB**
(scalar 0.4088) with `SetMasterVolumeLevel`. Old values written down and put back afterwards: speaker −3.69 dB
(scalar 0.7816), mic +27.0 dB. Dolby Access was left on **Dynamic** (the last take).

**Method.** A small C# WASAPI tool (not in the repo):
- **Mic:** shared mode, **RAW** (`AUDCLNT_STREAMOPTIONS_RAW`), engine format 48 kHz 1 ch float32 → 16-bit mono WAV.
- **Playback:** shared-mode render client on the default endpoint (Speakers (Realtek(R) Audio), mix format
  48 kHz 2 ch float32), stream volume untouched (1.0). The 24-bit samples are converted to float32 (`x / 2^23`, exact).
  No resampling: the file and the device are both 48 kHz stereo.
- **Loopback:** a capture of the speaker endpoint during each take, saved as float32 stereo
  (`logs/music-test/null-win-loopback-*.wav`).

Playback started 1.01–1.02 s after the capture was opened. The mic stream itself starts about 0.8 s after that
(the takes hold 59.2 s of a 60 s window), so the file starts about 0.2 s into each recording, not 1 s. Both chirps
and both songs are inside every take. Align on the chirps.

| File (`logs/win-music/`) | Dolby Access | Peak dBFS | RMS dBFS |
|---|---|---|---|
| `win-silence.wav` | (nothing playing, 3.6 s) | −46.2 | −50.6 |
| `win-music-dolby-off.wav` | Dolby off | −11.0 | −29.5 |
| `win-music-music-ieq-off.wav` | Music, IEQ Off | −10.7 | −31.5 |
| `win-music-music-ieq-balanced.wav` | Music, IEQ Balanced | −10.9 | −32.3 |
| `win-music-dynamic.wav` | Dynamic | −12.1 | −31.0 |

No take clipped, and the mic level stayed at +15 dB for all of them. Windows takes are about 2–4 dB lower than the
Linux takes (Flat −8.7 / −27.2). Level-match before comparing by ear. The silence floor is higher than on Linux
(RMS −50.6 vs −56.6); in Q7 the Windows silence was DC/subsonic, with the bands at −75 to −89 dB.

**Null test.** `musictest.py null` on the Dolby-off loopback: **not bit-exact** ("No exact match for the start of the
file"). Aligned by correlation instead (stdlib script, scratchpad), offset 68.7 ms:

| Loopback | Part | Gain vs file | Residual (re signal) | Max \|diff\| |
|---|---|---|---|---|
| Dolby off | song 1, L/R | +0.00 dB | −63.2 / −63.9 dB | 1.5e-2 |
| Dolby off | chirp 2 | +0.00 dB | −70.9 dB | 2.4e-4 |
| Dolby off | song 2, L/R | +0.00 dB | −64.7 / −64.9 dB | 1.3e-2 |
| Music, IEQ Off | chirp 1 and 2 | −5.17 dB | −9.0 dB | 0.16 |
| Music, IEQ Off | songs | −0.9 to +0.4 dB | −8.7 to −14.4 dB | 0.97 |

- **Dolby off:** the difference grows with the level (RMS diff −79 dBFS for \|x\| < 0.25, −61 dBFS for \|x\| > 0.9)
  and stays about 63 dB below the signal. The file peak 0.9979 becomes 0.9851. A difference that follows the level
  like this looks like a tiny linear change (float processing or a very small filter), not a limiter. So **the music
  reaches the APO chain unchanged, and the stages before the loopback point are transparent with Dolby off, to about
  −63 dB.**
- The first chirp of the Dolby-off loopback doesn't line up (residual −1.5 dB) while the rest does. It looks like a
  dropout when the loopback stream started. It doesn't affect the songs.
- **With Dolby Music on, the loopback carries Dolby's processing.** The 300 Hz–6 kHz chirp is 5.2 dB lower (the
  Music mid dip), and the songs are heavily changed. So the loopback is taken **after Dolby** (at least after its SFX;
  whether it is also after the EFX and Realtek APOs is not known). The Q7 +3 dB at 160–800 Hz with Dolby off doesn't
  show in the Dolby-off loopback, so it comes from a stage after the loopback point (EFX), or from the acoustics.

### What Q8 means for Linux

| # | Finding | Change |
|---|---|---|
| 12 | The four Windows music takes are ready in `logs/win-music/`, same mic and setup as the Linux takes. | Bring them to Linux and run the comparison (level-matched, aligned on the chirps). |
| 13 | **The loopback is a digital copy of Dolby's output**, with no mic or room in between. The music-ieq-off, music-ieq-balanced and dynamic loopbacks (`logs/music-test/null-win-loopback-*.wav`) show what Dolby does to the music, sample by sample. | Compare them with a capture of the EasyEffects **output** of the same file on Linux. The level over time shows how Dolby's regulator reacts, and the spectrum over time shows IEQ. That is more exact than the mic takes. Caveat: Realtek's EFX may come after the loopback point. |

### 2026-11-27: Q8 compared on Linux (CachyOS, kernel 7.3.5, EasyEffects 8.3.3)

**Captures.** `sound/measure/ee-capture.sh` played `music-test.wav` into `easyeffects_sink` once per preset and
recorded the speaker sink monitor (float32 stereo, before the codec gain). The output is in
`logs/music-test/linux-ee-out-*.wav`. **The Flat capture is bit-exact** against the file (`musictest.py null`), so
the monitor is exactly what EasyEffects outputs. It is the Linux counterpart of the Windows loopback.

**Comparison.** `sound/measure/compare.py` aligns each take to the file and cuts it into 0.34 s blocks. For each
block and band it measures the gain (take − file). It aligns coarsely on the level envelope, then to the sample on
the differentiated music of each song. The reference band is 150 Hz–20 kHz, because the speakers play almost
nothing below 150 Hz and the bass would dominate a full-band level. Full reports: `logs/music-test/compare-digital.txt`
and `compare-mic.txt`. Block levels: `digital-blocks.csv` and `mic-blocks.csv`.

Columns: **W off** = Windows Dolby off, **L Flat** = Linux Flat, **W Mus** = Windows Music with IEQ off, **L Mus** =
Linux `S5406SA-Dolby-music`, **W Bal** = Windows Music with IEQ Balanced, **W Dyn** = Windows Dynamic, **L Dyn** =
Linux `S5406SA-Dolby-dynamic`.

Digital (Windows loopback vs EasyEffects output). Median gain per band relative to 150 Hz–20 kHz, in dB:

| Band | W off | L Flat | W Mus | L Mus | W Bal | W Dyn | L Dyn |
|---|---|---|---|---|---|---|---|
| 20–150 Hz | 0.0 | 0.0 | +2.0 | **−7.1** | +2.8 | +0.4 | **−7.9** |
| 150–500 Hz | 0.0 | 0.0 | +1.2 | 0.0 | +1.6 | +0.8 | −0.7 |
| 500 Hz–2 kHz | 0.0 | 0.0 | −4.1 | −2.2 | −4.5 | −2.0 | −0.5 |
| 2–5 kHz | 0.0 | 0.0 | −0.5 | +1.0 | −1.6 | +0.1 | +1.8 |
| 5–10 kHz | 0.0 | 0.0 | +4.0 | +4.1 | +5.1 | +2.3 | +1.2 |
| 10–20 kHz | 0.0 | 0.0 | +11.1 | +11.1 | +12.4 | +6.7 | +3.7 |

Movement (p90 − p10 of the block gain, in dB). 0 means a fixed EQ; a higher number means the processing reacts to
the music:

| Band | W off | L Flat | W Mus | L Mus | W Bal | W Dyn | L Dyn |
|---|---|---|---|---|---|---|---|
| 20–150 Hz | 0.0 | 0.0 | 0.5 | **7.6** | 3.0 | 3.3 | **7.6** |
| 150–500 Hz | 0.0 | 0.0 | 1.2 | 0.9 | 3.1 | 4.1 | 0.9 |
| 500 Hz–2 kHz | 0.0 | 0.0 | 1.9 | 1.9 | 3.8 | **6.7** | 0.9 |
| 2–5 kHz | 0.0 | 0.0 | 0.6 | 0.5 | 3.3 | **6.0** | 0.4 |
| 5–10 kHz | 0.0 | 0.0 | 5.5 | 5.1 | 8.3 | 8.0 | 2.3 |
| 10–20 kHz | 0.0 | 0.0 | 0.7 | 0.5 | 1.6 | 5.2 | 0.5 |

Slopes (block gain against block input level): Windows Dynamic −0.2 to −0.4 dB/dB in every band, and −0.3 across
150 Hz–20 kHz. Its gain by input level goes from +1.2 dB on the quietest fifth of the blocks to −1.0/−1.7 dB on the
loudest. Linux presets: −0.4 in 20–150 Hz (the high-pass, not compression; see #15) and about 0 elsewhere.

Peak and RMS of the whole file: Windows Music/Dynamic RMS −9.7/−9.2 dBFS (file −9.8), with about 1000 samples at
0 dBFS. Linux Music/Dynamic RMS −13.8/−13.1 dBFS, with 216/359 samples at 0 dBFS. The 4 dB is the bass the 80 Hz
high-pass removes. In 150 Hz–20 kHz the levels are within 0.5 dB (W Mus −1.2, L Mus −0.7).

Mic takes (the same setup on both systems). Level in 150 Hz–20 kHz: W off −14.4, L Flat −12.0, W Mus −16.3, L Mus
−12.4, W Bal −17.0, W Dyn −15.5, L Dyn −11.5 dB. The movement in every band from 500 Hz up matches the digital table
to within 0.5 dB, and the spectra show the same differences as the digital ones. `analyze.py` in third-octave bands,
W off − L Flat: **−2.4 dB ± 0.3 dB in every band from 100 Hz to 12.5 kHz.**

Blind, level-matched copies of the seven mic takes: `logs/music-test/blind-mic/` (key in `key.txt`).

### What the comparison means for Linux

| # | Finding | Change |
|---|---|---|
| 14 | **Nothing after Dolby changes the tone on Windows.** With music, Dolby off is Linux Flat minus 2.4 dB, flat from 100 Hz to 12.5 kHz. The mic takes also match the digital loopbacks. So the loopback is all there is to copy, and the Realtek APOs only lower the level. | **Drop #8** (the +3 dB 160–800 Hz lift). Q7's pink-noise result is not repeated with music, so it was probably a setup artifact. Windows is 2.4–4 dB quieter at the same slider, so level-match every by-ear comparison, or louder Linux will win by default. |
| 15 | **Bass: the only big difference is the 80 Hz high-pass.** Below 150 Hz Linux Music is 9 dB lower than Dolby Music (mic: 3.6 dB less at 20–150 Hz). Dolby has no high-pass. The 7.6 dB "movement" in that band is **not** compression: band0 of the multiband compressor has ratio 1. The high-pass cuts 40 Hz much more than 120 Hz, so the band's gain changes with which bass notes play. Corrected 2026-11-27. | Test the Music preset with the high-pass off (`S5406SA-Dolby-music-nohp`), level-matched against the current one. **Tested by ear 2026-11-27: no audible difference** (the speakers play almost nothing below 125 Hz), so the bass is not why Windows sounds better. |
| 16 | **Music: the tone and the 5–10 kHz movement already match.** Linux Music follows Dolby Music within about 1 dB at 5–20 kHz, and its 5–10 kHz movement is 5.1 dB against 5.5. The mid dip is 1.9 dB shallower (500 Hz–2 kHz) and 2–5 kHz is 1.5 dB higher. | This confirms #9 with music: deepen the 500 Hz–2 kHz dip by about 2 dB and take about 1.5 dB from 2–5 kHz. |
| 17 | **Windows Dynamic is a multiband leveler; Linux Dynamic isn't.** Dolby Dynamic moves every band by 3–8 dB, compresses at about −0.3 dB/dB, and gives quiet blocks +1.2 dB and loud ones −1 to −1.7 dB. Linux Dynamic is static above 150 Hz (movement 0.4–0.9), and its spectrum differs too (10–20 kHz 3 dB lower, 500 Hz–2 kHz 1.5 dB higher). | Rebuild Dynamic: a gentle multiband compressor across 150 Hz–20 kHz (about 1.5:1, a low threshold, slow attack/release), then retune its EQ against the W Dyn column. Lower priority than #15 and #16. |
| 18 | **IEQ Balanced is a dynamic EQ.** It moves 3–4 dB in the mids and 8 dB at 5–10 kHz. Against Music its median is bass +0.8 dB and 10–20 kHz **+1.3 dB** (mic: +0.6 and +2.2). That **contradicts #10** (bass +2.5, highs −3), which came from pink noise. | Don't build #10 as written. If a Balanced preset is wanted, base it on these music numbers. A real IEQ needs a dynamic EQ (LSP has one), which isn't worth it yet. |
| 19 | The Linux presets may add about 135 ms (Music) or 155 ms (Dynamic) of latency. The aligned offset grew by that much against Flat in the same capture method. **Not verified**: part of it could be pw-record start-up jitter. | Check with `pw-top` or the EasyEffects latency readout. If it's real, it matters for lip-sync in videos. |

---

Author: [@ayelsew](https://github.com/ayelsew)
