# Good on Windows

The speakers of this laptop are small. On Windows they sound good because **Dolby Atmos (DAX3)** processes
the audio with a tuning made for this exact model:
[DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml](DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml).

The file name says which hardware it is for: Realtek codec `0294` (ALC294) with subsystem `1043:10C4`
(this laptop). Tuning version 11, dated 2025-01-15.

Linux has no Dolby. To sound like Windows, this processing must be rebuilt with free tools
(EasyEffects or a PipeWire filter-chain).

## Speakers

- 2 front speakers (Left → output 0, Right → output 1), no delay, no subwoofer.
- Sample rate 48 kHz.

## Profiles

The Dolby Access app lets you choose a profile. Each one is a different set of effects:

| Profile | Speaker EQ | Compressor | Volume leveler | Dialog enhancer | Surround | Intelligent EQ | Volume boost | Extra PEQ |
|---|---|---|---|---|---|---|---|---|
| dynamic | yes | yes | no | yes | yes | balanced | 96 | — |
| movie | yes | yes | no | yes | yes | no | 96 | — |
| music | yes | yes | no | no | no | balanced | 96 | 1200 Hz −4 dB, 14200 Hz +3.5 dB |
| game | yes | yes | no | no | yes | no | 96 | — |
| voice | yes | yes | no | yes | no | no | 96 | 1200 Hz −4 dB |
| voice_onlinecourse | yes | yes | no | yes | no | no | 64 | 1200 Hz −4 dB |
| personalize_user1/2/3 | yes | no | yes | yes | yes | no | 96 | — |
| off | no | no | no | no | no | no | 0 | — |

In all profiles: virtual bass, bass enhancer and graphic EQ are off, and the virtualizer front speaker
angle is 10°.

## Speaker EQ (audio optimizer)

This is the most important part: it corrects the frequency response of the speakers. It has 20 bands, the
same for both speakers. The values in the XML are most likely in 1/16 dB (Dolby's unit, e.g. `-192` =
−12 dB). They are converted to dB below.

| Band (Hz, 48 kHz) | 47 | 141 | 234 | 328 | 469 | 656 | 844 | 1031 | 1313 | 1688 | 2250 | 3000 | 3750 | 4688 | 5813 | 7125 | 9000 | 11250 | 13875 | 19688 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dynamic | 0 | 0 | 0 | −1.5 | −2.1 | −2.5 | −1 | −2 | −5 | −2.5 | −1 | 0 | 0 | −3 | −2.5 | 0 | 2 | 1 | 0 | 0 |
| movie | 0 | 0 | 1.5 | 1 | 0 | −2.5 | −1 | −2 | −2 | −1.5 | 0 | 0 | 0 | −3 | −2.5 | 0 | 2 | 1 | 0 | 0 |
| music | 0 | 0 | 0 | −1.5 | −2.1 | −2.5 | −1 | −2.5 | −5 | −3 | −1.5 | 0 | −3 | −3 | −3.5 | 0 | 7 | 3.5 | 5.5 | 2.5 |
| game | 0 | 0 | 0 | −1.5 | −2.1 | −2.5 | −1 | −1.5 | −3 | 1 | 1.5 | 1 | 0 | −1.5 | −1.1 | 2.5 | 2 | 1 | 0 | 0 |
| voice, voice_onlinecourse | 0 | 0 | 0 | −1.5 | −2.1 | −2.5 | −1 | −2.5 | −5 | −3 | −1.5 | 0 | 0 | −3 | −3 | 0 | 2 | 1 | 0 | 0 |
| personalize_user1/2/3 | 0 | 0 | 0 | −1.5 | −2.1 | −2.5 | −1 | −2 | −2 | −1.5 | 0 | 0 | 0 | −3 | −2.5 | 0 | 2 | 1 | 0 | 0 |

In short: a cut of the "boxy" mids around 300 Hz – 2 kHz (strongest at 1.3 kHz) and around 5 kHz, and a
small boost at 9 kHz. The music profile boosts the highs much more.

