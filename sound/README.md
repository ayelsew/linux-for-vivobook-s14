# Sound System for ASUS Vivobook S 14 S5406SA

I am far from being a specialist/sound engineer, much less an audiophile, but in the moments that should be my leisure time, I am judging the quality of my headphones (PS: I only have 2, Buds4 Pro and a TRN Conch). So I use the little preference I have for sound to equalize my equipment.

## Sound EQ
This one took me a lot of time and work, and it is still not good. But in a few words: Dolby (DAX3) is a proprietary system developed for the Windows sound engine, and reverse engineering is not a thing that I really want to spend tokens on. So I cannot install it on Linux, and I followed a workaround: getting Dolby's presets from `C:\Windows\System32\DriverStore\FileRepository\dax3_ext_rtk.inf_amd64_*\`, in a file called `DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml`. It isn't much, because Dolby adds a "dynamic on demand EQ" layer, so even with that preset it won't sound the same... The XML name has some info that helped me identify the sound chip (`DEV_0294 = ALC294`) and the machine model (`SUBSYS_104310C4 = 1043 -> Asus ID and 10C4 board ID`), as I describe in [Hardware.inf.md](Hardware.inf.md).

Btw PC sound systems usually follow a recipe. On my laptop, as I understood it, it is:

| Component | Linux | Windows | Description |
|---|---|---|---|
| App | Spotify | Spotify | Any app that plays sound |
| Engine | PipeWire | Audiodg | Engine with plugins. Linux uses EasyEffects and Windows uses Dolby + Realtek components |
| DSP | SOF | Intel SST | Intel SST is the chip and also the firmware controlled by Windows. On Linux, SOF is the firmware for Intel SST |
| Codec | ALC294 | ALC294 | Both are the same because it is hardware level. It does DAC, ADC and Amp |

And the chain is wired as follows:

On Windows:

```
App(Spotify) -> Audiodg(Realtek + Dolby) -> DSP(Intel SST) -> Codec(ALC294) -> Speaker
```

On Linux:

```
App(Spotify) -> PipeWire(EasyEffects) -> ALSA(DSP(SOF)) -> Codec(ALC294) -> Speaker
```
> ALSA (_Advanced Linux Sound Architecture_) is the kernel's sound layer that drives the sound hardware.

DSP means Digital Signal Processor. It is usually a dedicated chip (on my laptop it is inside Lunar Lake) that applies equalization, noise suppression and spatial sound, but all of it depends on the model. It is really common in Bluetooth sound devices, and I really don't know why the EQ in computers like laptops and desktops is made at software level, consuming CPU, instead of using the dedicated DSP hardware... So here we just follow the recipe, and for playback the DSP becomes just a bridge.

EasyEffects will be my "Dolby" here, so I asked Mr Claudinho to convert `DEV_0294_SUBSYS_104310C4_PCI_SUBSYS_10C41043.xml` into EasyEffects presets. So now I have a sound with some "shape", and it sounds better than raw Linux sound.

See [easyeffects/README.md](easyeffects/README.md).

I also make a lot of test using an external mic to compare the sound make from Windows and Linux and let the IA compare the result, I don't have a ultra, mega fucking top external mic to do this test, but with my generic the difference was little. By for my ears the difference is more between then. So do by your self and tell me.


While researching EasyEffects I found a fake page of the project, so be careful. See the following link to understand it:
https://github.com/wwmm/easyeffects/discussions/5238


## Microphone and AI Noise Cancellation

Here Dolby has nothing to do, it is Realtek property + Intel SST. And it also use the NPU.

I'll bring more as soon as possible.

---

Author: [@ayelsew](https://github.com/ayelsew)
