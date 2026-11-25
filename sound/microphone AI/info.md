 HDX_AsusExt_APOT_G5-TSE_AG40_AA51_AF68_N_LNL.inf together with …_pc_2-90-rev_360-on-off.inf: the microphone AI.
These add Realtek's "Gen5" microphone processing, which is what MyASUS calls AI noise cancelling. The settings they turn on include:
- SpeakerTrack
- StudioHQ single-direction mode and all-around (360°) mode
- TSE / GTSE ("target speech", which keeps only your voice)
- AI noise suppression (AINS)

The 2-90-rev_360 in the file name most likely means 2 microphones, with a 90° pickup mode and a 360° pickup mode.

The bad news is that all of it lives in closed binary model files: NNAEC.rbin, PSE_AM19*.rbin, SCAPSE_AH88p*.rbin, netstate2_*.dat and gen5pkey_….mdat, about 175 MB in total. Linux can't use them. What we can do is document the features and rebuild them with free tools:
- Noise removal: RNNoise or DeepFilterNet in EasyEffects
- Echo cancellation: PipeWire's echo-cancel module

## Where the files come from

All files were copied on 2026-11-25 from the Windows driver store of this laptop
(`C:\Windows\System32\DriverStore\FileRepository\`). They come from two Realtek driver extension packages,
version 6.0.9761.1 (2024-11-19), both bound to the codec `INTELAUDIO\FUNC_01&VEN_10EC&DEV_0294&SUBSYS_104310C4`.

| File | Size | Package (folder in `FileRepository`) |
|---|---|---|
| `NNAEC.rbin` | 0.2 MB | `hdx_asusext_apot_g5-tse_ag40_aa51_af68_n_lnl.inf_amd64_a9dbcb9196738f06` |
| `PSE_AM19.rbin` | 9.0 MB | same |
| `PSE_AM19_enroll.rbin` | 61.9 MB | same |
| `SCAPSE_AH88p.rbin` | 16.1 MB | same |
| `SCAPSE_AH88p_enroll.rbin` | 45.2 MB | same |
| `UBD_AA51_85.rbin` | 2.6 MB | same |
| `netstate2_AF68.dat` | 10.3 MB | same |
| `netstate2_AG40_n_lnl.dat` | 18.2 MB | same |
| `netstate2_spkrverf.rbin` | 16.9 MB | same |
| `gen5pkey_asus-pc_tse_2-90-rev.mdat` | 0.1 MB | `hdx_asusext_apot_g5-tse_pc_2-90-rev_360-on-off.inf_amd64_238188b6c62b4b64` |

The second package also has `gen5CapCond_asus-pc_tse_2_360-on-off.cond` and `gen5RenCond_asus-pc_tse_off.cond`
(not copied here).

## Who uses them

1. **The INF files register them.** When Windows installs the extension packages, the INFs write the file
   paths into the registry key of the Realtek audio device:
   `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}\<nnnn>\APOTunings`

   | Value | Set by | Points to |
   |---|---|---|
   | `TuningFileBasePath`, `TuningFiles`, `TuningVersion` = 242 | `HDX_AsusExt_APOT_G5-TSE_pc_2-90-rev_360-on-off.inf` | `gen5pkey_…mdat` and the two `.cond` files |
   | `ExtraTunings` = `NParam` | `HDX_AsusExt_APOT_G5-TSE_AG40_AA51_AF68_N_LNL.inf` | the `NParam` subkey |
   | `NParam\{021C6000-DB7C-4A30-8977-483AEF576090},<n>` | same | one value per model file (all the other files above) |

2. **The Realtek effects (APO) read them.** The Realtek Audio Effects Component (`realtekuapo2.inf`, version
   13.1368.1488.435) has the DLLs that run the microphone processing:
   - `RltkAPOU642.dll` and `RtkMicUUn642.dll`, both "Realtek(r) LFX/GFX DSP component"

   Both reference `.rbin` files and Windows cryptography functions. The model files are **not** encrypted
   (see below), so the cryptography is probably for something else, such as checking signatures or a license.
   Windows runs APOs inside the audio engine (`audiodg.exe`).
   `RltkAPOU642.dll` is also loaded by `RtkAudUService64.exe` (Realtek Audio Universal Service).

3. **The user controls it** through MyASUS ("AI noise cancelling") and Realtek Audio Control, which turn the
   features on or off through the `SysRecCustomizedFx_Gen5UI` settings in `HDX_AsusExt_APOT_G5-TSE_PC.inf`.

## The whole bundle

The feature is not one package: it is 8 driver packages, plus MyASUS as the on/off switch. Every file runs
from the Windows driver store; nothing is copied to `System32` or `Program Files`.

Base directory: `C:\Windows\System32\DriverStore\FileRepository\`

### 1. Base driver

`hdxsstasus.inf_amd64_2019e426b20e37a6\`: Realtek HD Audio driver (ASUS build for Intel SST), 6.0.9761.1.

| File | Size | What it is |
|---|---|---|
| `RTKVHD64.sys` | 6.7 MB | Kernel driver |
| `RTAIODAT.DAT` | 60.9 MB | Realtek data file |
| `HDXSSTASUS.inf`, `HDXRT.CAT` | | Install file and signature |

### 2. ASUS extensions (settings for this laptop)

| Folder | Files | Role |
|---|---|---|
| `hdx_asusext_dolby_dsp_wrap36_rtkgen5_pc.inf_amd64_e73fd12c9dc533e9\` | `.inf`, `.cat` | Plugs the Realtek microphone effects into the microphone path |
| `hdx_asusext_apot_g5-tse_pc.inf_amd64_7c8ea8e1d61d84b1\` | `.inf`, `.cat` | Turns on the feature switches (TSE, SpeakerTrack, StudioHQ, noise suppression) |
| `hdx_asusext_apot_g5-tse_pc_2-90-rev_360-on-off.inf_amd64_238188b6c62b4b64\` | `gen5pkey_asus-pc_tse_2-90-rev.mdat`, `gen5CapCond_asus-pc_tse_2_360-on-off.cond`, `gen5RenCond_asus-pc_tse_off.cond`, `.inf`, `.cat` | Tuning and settings for this model |
| `hdx_asusext_apot_g5-tse_ag40_aa51_af68_n_lnl.inf_amd64_a9dbcb9196738f06\` | The 9 `.rbin` / `.dat` models, `.inf`, `.cat` | The neural network weights |

### 3. Microphone effect (the code that does the processing)

`realtekuapo2.inf_amd64_6fe665139c994700\`: Realtek Audio Effects Component, 13.1368.1488.435.

| File | Size | What it is |
|---|---|---|
| `RltkAPOU642.dll` | 10.9 MB | Effect code |
| `RtkMicUUn642.dll` | 10.9 MB | Effect code (microphone) |
| `RtkIntU642.dll` | 10.9 MB | Effect code |
| `RtkUApo2Api.dll` | 0.7 MB | Interface the Realtek apps use to control the effects |

### 4. OpenVINO bridge (how it reaches the NPU)

| Folder | Files | Runs on |
|---|---|---|
| `ovwrapn.inf_amd64_b50177c055e66a48\` (11.0.6000.49) | `OVWrapN.dll`, `openvino.dll`, `openvino_c.dll`, `openvino_intel_npu_plugin.dll`, `openvino_intel_cpu_plugin.dll`, `openvino_ir_frontend.dll`, `tbb12.dll`, `tbbbind_2_5.dll`, `tbbmalloc.dll`, `tbbmalloc_proxy.dll`, `msvcp140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` | **NPU** (CPU plugin also included) |
| `ovwrap2.inf_amd64_c876bb71db037af9\` (11.0.6000.37) | `OVWrap2.dll`, `openvino.dll`, `openvino_c.dll`, `openvino_intel_gna_plugin.dll`, `gna.dll`, `tbb*.dll`, `msvcp140.dll`, `vcruntime140*.dll` | GNA (Intel's older low-power accelerator), probably for older laptops |

`ovwrapn.inf` registers `OVWrapN.dll` as a COM class (`InProcServer32`) for the microphone effect to load.
Its files are marked `PETrust` (`DRMLevel=1300`), which lets them load inside Windows' protected audio
process (`audiodg.exe`).

`openvino_ir_frontend.dll` is OpenVINO's loader for its standard model format (IR). The models here are in
Realtek's own format, so `OVWrapN.dll` probably builds or converts the network in code (not confirmed).

### 5. Realtek service (voice enrollment and app back end)

`realtekservice.inf_amd64_52565dfecdf94b98\`: Realtek Audio Universal Service, 1.0.808.8.

| File | What it is |
|---|---|
| `RtkAudUService64.exe` | The service (also loads `RltkAPOU642.dll`) |
| `MonoSeparationEnrollDll.dll`, `MonoSeparationGEnrollDll.dll` | Learn your voice (uses the `_enroll` models) |
| `SpeakerVerfDll.dll` | Speaker verification (uses `netstate2_spkrverf.rbin`) |
| `PTTdll.dll`, `RtCOM64.dll`, `RtDataProc64.dll`, `RtkApi64U.dll`, `RtkCfg64.dll`, `RtkAudUServiceConf64.dll`, `RtkAudUServiceRes64.dll` | Service support libraries |

### 6. Outside the driver store

| Where | What |
|---|---|
| MyASUS (`B9ECED6F.ASUSPCAssistant`, in `C:\Program Files\WindowsApps\`) | The "AI noise canceling" switch |
| `C:\ProgramData\ASUS\` | ASUS app data |
| `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e96c-e325-11ce-bfc1-08002be10318}\0002\APOTunings` | Registry: where the model and tuning files are listed |

### Not part of the microphone AI

- `realtekhsa.inf_*`: only installs the Realtek Audio Control app from the Store.
- `realtekasio.inf_*` (`RTHDASIO.dll`, `RTHDASIO64.dll`): ASIO driver for music software.

### How it fits together

```
MyASUS (switch)
   → RtkAudUService64.exe (service: enrollment, speaker verification)
   → RltkAPOU642.dll / RtkMicUUn642.dll (microphone effect, inside audiodg.exe)
        reads the model files listed in APOTunings\NParam
   → OVWrapN.dll → openvino.dll → openvino_intel_npu_plugin.dll → NPU
```

## It runs on the NPU

Tested on 2026-11-25 with Task Manager (Performance → NPU):

| Test | NPU |
|---|---|
| Discord and Google Meet, AI noise canceling **off** in MyASUS | 0 % |
| Camera blur on (Windows Studio Effects, a different feature) | Busy |
| AI noise canceling **on** in MyASUS, recording audio | **Busy** |

So the Realtek microphone AI runs on the **NPU** (Intel AI Boost), and only after you turn it on in MyASUS.

The bridge to the NPU is **Realtek OVWrapN Component** (`ovwrapn.inf`). "OV" is **OpenVINO**, Intel's
runtime for running neural networks on the CPU, GPU or NPU: the package ships `openvino.dll` and
`openvino_intel_npu_plugin.dll` (see "The whole bundle" below).

## Are the models encrypted? No

Checked on 2026-11-25 by measuring the files:

- **Readable header.** Every `.rbin` starts with the magic `BBBBBBBB` followed by plain big-endian numbers
  (`0001 0003` looks like a format version 1.3, then counts and sizes). The `.dat` files start with plain
  offsets/sizes. Encrypted files would look random from the first byte.
- **Entropy is too low for encryption.** Encrypted data is close to 8.0 bits per byte everywhere and does
  not compress. These files are 4.8–7.4 on average, compress to 66–94 %, and some parts are all zeros.
- **The numbers decode as weights.** Read as big-endian 32-bit floats, ~100 % of the values in the middle of
  most files are normal weight values (random bytes would give ~10 %). Example from `UBD_AA51_85.rbin`:
  `0.5744, 1.849, 0.6942, -7.962, -5.205, -1.057, …`.

| File | What is inside (most likely) |
|---|---|
| `PSE_AM19.rbin`, `PSE_AM19_enroll.rbin`, `SCAPSE_AH88p_enroll.rbin`, `UBD_AA51_85.rbin`, `netstate2_spkrverf.rbin`, `netstate2_AF68.dat`, `NNAEC.rbin` | 32-bit floats (FP32), big-endian |
| `SCAPSE_AH88p.rbin` | FP32 at the start and end, 16-bit integers in the middle (quantized weights) |
| `netstate2_AG40_n_lnl.dat` | Mostly 16-bit floats (FP16), big-endian, e.g. `-0.1421, -0.0095, 0.0762, 0.3118`. FP16 is the format NPUs prefer, and `n_lnl` may mean "NPU, Lunar Lake" (guess) |
| `gen5pkey_asus-pc_tse_2-90-rev.mdat` | Settings, not a network: little-endian floats like `8.0, 15.0, 0.5, 0.3, 30.0, 0.1`, 70 % zeros |

**But readable is not the same as usable.** The files hold the weights in Realtek's own container format.
The structure of the networks (which layers, in what order, what sizes) is not in a standard format like
ONNX or OpenVINO IR. It is probably defined in the code of the Realtek DLLs. Running these models on Linux
would need reverse engineering of the format and the DLLs, and the files are Realtek's property.

## What the names probably mean

These are guesses from the names, not confirmed:

| Name | Guess |
|---|---|
| `NNAEC` | Neural network acoustic echo cancellation |
| `PSE` / `SCAPSE` | (Personalized) speech enhancement: keeps your voice, removes others |
| `*_enroll` | Voice enrollment, to learn the user's voice for TSE ("target speech") |
| `netstate2_*` | Neural network weights ("network state") |
| `spkrverf` | Speaker verification (recognizing who is speaking) |
| `UBD` | Unknown |
| `gen5pkey` | Realtek Gen5 parameter key / tuning for this model |