# Touchpad Gestures

Edge gesture actions (volume, brightness, media, corner → MyASUS) work because the operating system ignores touches that start at the edge of the touchpad.
This is **palm rejection**: a touch that begins at the edge is treated as a palm and does not move the
cursor.

So nothing special about the gesture here, just a good idea to avoid wasted area with "palm rejection".

## So a little story about palm rejection in touchpads

### Touchpad vendors

Synaptics sells palm rejection as a feature of its touchpads (TypeGuard).
[Synaptics product brief](https://www.synaptics.com/sites/default/files/2020-11/touchpad-product-brief.pdf)

### macOS

Apple holds patents on palm rejection, such as
[US8952899 "Method and apparatus to reject accidental contact on a touchpad"](https://patents.google.com/patent/US8952899B2/en).

### Windows

- **2013 (Windows 8.1):** Microsoft created the **Precision Touchpad** standard together with Synaptics. The
  touchpad sends raw touches and Windows does the processing, palm rejection included.
  [How-To Geek](https://www.howtogeek.com/286905/what-is-a-precision-touchpad-on-windows-pcs/) ·
  [Microsoft design guide](https://learn.microsoft.com/en-us/windows-hardware/design/component-guidelines/windows-precision-touchpad-industrial-design-guide)
- Every Precision Touchpad must send a **confidence** bit per touch, which marks palms. The Linux
  `hid-multitouch` driver uses this bit for palm rejection since 2016.
  [Kernel discussion](https://lore.kernel.org/all/1466670690-77458-2-git-send-email-allen_hung@dell.com/T/)

### Linux (libinput)

- **2014:** Peter Hutterer added edge palm zones after a test on a Lenovo ThinkPad T440s: *"all but 2 touch
  points were located in the outer ~5% of the touchpad"* while typing. A touch that **starts** in the zone is
  a palm; a finger may move into it later. Hans de Goede objected in review that it would *"break any
  pointer-moves starting at the edge of the touchpad"*.
  [Patch](https://wayland-devel.freedesktop.narkive.com/0cU8jPs1/patch-libinput-touchpad-implement-edge-based-basic-palm-detection)
- **2017:** the zones were widened from 5% to 8% of the width (touchpads narrower than 70 mm get no zones).
  [Patch](https://wayland-devel.freedesktop.narkive.com/IykWqqJR/patch-libinput-1-3-touchpad-increase-palm-edge-zones-to-8)
- **Today:** zones on the left, right and top edges. A touch starting there does not move the cursor or
  tap; a fast movement that starts there does.
  [libinput docs: Palm detection](https://wayland.freedesktop.org/libinput/doc/latest/palm-detection.html) ·
  [bug 103606](https://bugs.freedesktop.org/show_bug.cgi?id=103606) ·
  [issue 159](https://gitlab.freedesktop.org/libinput/libinput/issues/159)

So kids I don't know about you guys but for me "Precision Touchpad" is a common thing nowadays considering that it is just an industry standard created in 2013, nothing special as the name makes it feel haha.

About the tradicional gestures like two fingers scroll, by my research libinput handlers it on linux. I saw that is possible to extends the lib with plugins to reimplement the gesture "native-like" like asus filter does, but I'm so lazy... So hello my old systemd with script :)