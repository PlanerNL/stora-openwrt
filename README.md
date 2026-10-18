# stora-openwrt

Extras for **OpenWrt on the Netgear Stora (MS2000/MS2110)**, plus a patcher that adds them to an
OpenWrt firmware file before you flash it.

What you get in the web interface (LuCI):

- **Services → Disks & RAID**: prepare a disk (erase, partition, ext4), create RAID 1 (mirror) or
  RAID 0 (stripe), see the SMART health of each disk, share the volume on the network and manage the
  network-share users. Everything from the browser, no SSH needed.
- **System → Shut down**: shut the Stora down safely and switch it off.
- **A working power button / `poweroff`**: on stock OpenWrt the Stora only halts and the disks and fan
  keep running. With this patch it really switches off.

## Usage

1. Build a firmware for the Netgear Stora with the [OpenWrt Firmware Selector](https://firmware-selector.openwrt.org)
   and add these packages:

   ```
   luci ksmbd-server luci-app-ksmbd hd-idle luci-app-hd-idle kmod-ata-marvell-sata kmod-fs-ext4 e2fsprogs block-mount fdisk mdadm smartmontools
   ```

   Download the file with **sysupgrade** in its name.

2. Download **[stora-patch.py](https://github.com/PlanerNL/stora-openwrt/releases/latest/download/stora-patch.py)**
   and put it in the same folder as the firmware.

3. Run it (Python 3.8 or newer; nothing else is needed):

   | System | Command |
   |---|---|
   | Windows (PowerShell) | `py stora-patch.py openwrt-...-netgear_stora-squashfs-sysupgrade.bin` |
   | macOS / Linux | `python3 stora-patch.py openwrt-...-netgear_stora-squashfs-sysupgrade.bin` |

   No Python on Windows? Install it from [python.org](https://www.python.org/downloads/) or with
   `winget install Python.Python.3.12`.

4. Flash the new `...-patched.bin` in LuCI: **System → Backup / Flash Firmware → Flash image**.

The patcher checks that the file is a sysupgrade image for the Stora, warns about missing packages and
verifies the result before writing it. Running it on an already patched file is fine.

## How it works

A sysupgrade image is a tar archive (`CONTROL`, `kernel`, `root`) with OpenWrt metadata appended.
The patcher reads the SquashFS root file system, adds the files from `src/`, rebuilds only the metadata
of the file system (all existing file data is copied byte for byte) and writes a new image with the
original metadata. The kernel is not touched. It uses only the Python standard library.

Because the content changes, the OpenWrt signature is removed. OpenWrt on the Stora accepts unsigned
images as long as the metadata is present (which it is).

### The power-off fix

The Stora device tree in OpenWrt points the power-off line at `<&gpio0 40 GPIO_ACTIVE_LOW>`, but
GPIO bank 0 has only 32 lines, so the kernel's `gpio-poweroff` driver never probes. The line is
MPP40 = `<&gpio1 8 GPIO_ACTIVE_HIGH>` (tested: driving GPIO 40 high cuts the power).
Until that is fixed upstream, `src/sbin/poweroff` marks a real power-off and
`src/etc/init.d/stora-power` unmounts the data disks, stops RAID arrays, syncs and then sets GPIO 40
high at the end of the shutdown. Reboots are not affected.

## Repository layout

| Path | Contents |
|---|---|
| `stora-patch.py` | The patcher (generated, single file) |
| `src/` | Files that are added to the firmware |
| `tools/` | Patcher sources and `build.py`, which regenerates `stora-patch.py` from `tools/` and `src/` |
| `extras/99-diskprep-firstboot.sh` | Alternative: a first-boot script for the Firmware Selector that installs the pages (max. 20 KB) |

After changing anything in `src/` or `tools/`, run `python3 tools/build.py` and commit the new
`stora-patch.py`. Bump `tools/VERSION` for a new release.

## Disclaimer

Creating a volume erases the selected disks. Flashing firmware always carries some risk; keep a way to
recover (serial console) when you try a new build. Use at your own risk.
