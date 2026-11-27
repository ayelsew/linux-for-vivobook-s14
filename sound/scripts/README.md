# Speaker measurement tools

Small tools to measure the laptop speakers with a microphone, so presets (and Linux vs Windows) are compared with
numbers instead of memory. Python standard library only. Recordings go to `logs/` (gitignored).

| File | What |
|---|---|
| `signals.py` | Writes `pink-6s.wav`, the test signal. Always byte-identical (SHA-256 printed), on Linux and Windows |
| `musictest.py` | `build`: picks the busiest 25 s of two songs and writes `music-test.wav` (sync chirps + excerpts, samples unchanged) for Linux vs Windows music takes. `null`: proves a recording of the effects' input is bit-identical to the file |
| `ee-capture.sh` | Plays `music-test.wav` through EasyEffects once per preset and records its output digitally (speaker sink monitor), the Linux side of the Windows loopback captures |
| `compare.py` | Aligns takes of `music-test.wav` (digital captures or mic takes) to the file and compares them over time: spectrum, how much the gain moves, compression slope, gain by input level, output dynamics. `--blind` writes level-matched copies under random names, `--csv` the block levels |
| `analyze.py` | Third-octave band levels of a recording, and B − A between two recordings |
| `server.py` + `measure.py` | Use a phone as a remote mic: the phone's browser records when `measure.py` asks |

## With a USB mic (preferred)

A USB mic gives cleaner numbers than a phone. Turn its hardware AGC off and keep the gain fixed (on Linux:
`amixer -c1` controls `Auto Gain Control` and `Mic Capture Volume`). Record while playing the signal:

```sh
python3 -I sound/measure/signals.py logs/sound-loops
SRC=$(pactl list short sources | awk '/usb.*Audio/ && !/monitor/ {print $2; exit}')
( sleep 1; pw-play logs/sound-loops/pink-6s.wav ) &
timeout --signal=INT 8 pw-record --target "$SRC" --rate 48000 --channels 1 --format s16 logs/usb-mic/take.wav
python3 -I sound/measure/analyze.py logs/usb-mic/flat.wav logs/usb-mic/take.wav --from 1.6 --to 6.8
```

Compare differences (B − A), not absolute levels: the mic's own response cancels out in a difference.

## With a phone

1. Open port 8443 for the local network: `sudo ufw allow from 192.168.1.0/24 to any port 8443 proto tcp`
   (close it again afterwards: `sudo ufw delete allow from 192.168.1.0/24 to any port 8443 proto tcp`).
2. `python3 -I sound/measure/server.py`, open the printed link on the phone, accept the self-signed certificate
   warning, tap Start. The page shows whether the browser really turned off auto gain and noise suppression.
3. `python3 -I sound/measure/measure.py record 8.5 --play logs/sound-loops/pink-6s.wav`

Phone mics are weak below about 125 Hz and overload easily: keep the speaker volume moderate.

Results of the first measurements are in [validate.md](../validate.md) Q7.

---

Author: [@ayelsew](https://github.com/ayelsew)
