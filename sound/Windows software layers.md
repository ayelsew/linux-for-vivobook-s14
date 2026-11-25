# Windows software layers

How the sound works on Windows for this laptop, from the hardware up to the apps. Hardware details are in
[Hardware.inf.md](Hardware.inf.md).

```
 Apps (Dolby Access, Realtek Audio Control, MyASUS)
        │
 Services (DolbyDAXAPI, RtkAudioUniversalService, IntelAudioService)
        │
 Effects / APOs (Dolby DAX3, Realtek effects, Voice Clarity)
        │
 Windows Audio (Audiosrv, AudioEndpointBuilder)
        │
 Drivers: Realtek HDA (+ ASUS extensions)   Intel SST (DMIC, BT, USB)
        │                                          │
 Codec Realtek ALC294 ──────── Intel SST DSP ──────┘
```

## 1. Intel Smart Sound Technology (the DSP)

All audio passes through the Intel DSP. Version 20.42.12134.0 (2025-05-14).

| INF | Device |
|---|---|
| `intcaudiobus.inf` | Intel SST BUS (the PCI controller `8086:A828`) |
| `intcoed.inf` | Intel SST OED (loads the DSP firmware) |
| `intcdmic.inf` | Digital microphones |
| `intcbtau.inf` | Bluetooth audio |
| `intcbtle.inf` | Bluetooth LE audio |
| `intcusb.inf` | USB audio |

## 2. Realtek codec driver

| INF | What it is | Version |
|---|---|---|
| `hdxsstasus.inf` | Realtek HD Audio, ASUS build for Intel SST machines | 6.0.9761.1 |

### ASUS extensions bound to this laptop

Extension INFs add settings for one model on top of the generic driver. These 5 are bound to
`DEV_0294&SUBSYS_104310C4`:

| INF | Provider |
|---|---|
| `hdx_asusext_dolby_dsp_wrap36_rtkgen5_pc.inf` | Realtek (Dolby wrapper for the Realtek effects) |
| `hdx_asusext_apot_g5-tse_ag40_aa51_af68_n_lnl.inf` | Realtek (`lnl` = Lunar Lake) |
| `hdx_asusext_apot_g5-tse_pc.inf` | Realtek |
| `hdx_asusext_apot_g5-tse_pc_2-90-rev_360-on-off.inf` | Realtek |
| `dax3_ext_rtk.inf` | Dolby: picks the tuning XML for this model (`DolbyAccessNoGaming`) |

## 3. Audio effects (APOs)

APOs (Audio Processing Objects) change the sound before it reaches the speakers or after it leaves the
microphones.

| INF | Name | Version |
|---|---|---|
| `dax3_swc_aposvc.inf` | DolbyAPO SWC Device (Dolby Atmos DAX3) | 3.30805.851.0 |
| `dax3_swc_hsa.inf` | DolbyAPO Software Device (HSA), links the Dolby Access app | 3.30803.830.0 |
| `realtekuapo2.inf` | Realtek Audio Effects Component | 13.1368.1488.435 |
| (Windows) | Voice Clarity (microphone noise removal) | — |

The Dolby APO reads
[DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml](DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml).
See [Good on Windows.md](Good%20on%20Windows.md).

## 4. Realtek software components

| INF | Name | Version |
|---|---|---|
| `realtekservice.inf` | Realtek Audio Universal Service | 1.0.808.8 |
| `realtekhsa.inf` | Realtek Hardware Support Application (installs Realtek Audio Control) | 11.0.6000.353 |
| `realtekasio.inf` | Realtek ASIO (low-latency audio for music apps) | 1.0.13.1 |
| `ovwrap2.inf`, `ovwrapn.inf` | Realtek OVWrap components | 11.0.6000.37 / 11.0.6000.49 |

## 5. Services

| Service | What it does |
|---|---|
| `Audiosrv`, `AudioEndpointBuilder` | Windows Audio |
| `DolbyDAXAPI` | Dolby DAX API Service: the Dolby Access app talks to the APO through it |
| `RtkAudioUniversalService` | Realtek Audio Universal Service (jack detection, Realtek app) |
| `IntelAudioService` | Intel Audio Service (DSP) |

## 6. Apps

| App | Version | What it does |
|---|---|---|
| Dolby Access | 3.27.12250.0 | Choose the Dolby profile (dynamic, movie, music, …) |
| Dolby Digital Plus Decoder OEM | 1.2.591.0 | Decoder for Dolby Digital Plus content |
| Realtek Audio Control | 1.51.352.0 | Realtek settings (jack, effects) |
| ASUS PC Assistant (MyASUS) | 4.0.82.0 | ASUS settings |

Read on 2026-11-25 on Windows 11 (Device Manager, `pnputil /enum-drivers`, services and Store apps).
