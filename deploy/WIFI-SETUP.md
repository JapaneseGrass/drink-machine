# In-app WiFi provisioning

Lets you connect the machine to a new venue's WiFi from your phone — no SSH, no
monitor. At a location with no known network, the Pi raises a **DrinkMachine**
setup hotspot; you join it, open the app's **Network** page, enter the venue's
WiFi name + password, and the Pi switches over to it.

## One-time install (run on the Pi, needs sudo)

1. **Let the app manage WiFi** (sudoers rule so it can run `nmcli` as root):
   ```bash
   sudo cp ~/drink-machine/deploy/drinkmachine-sudoers /etc/sudoers.d/drinkmachine
   sudo chmod 440 /etc/sudoers.d/drinkmachine
   sudo visudo -c            # should print "parsed OK"
   ```

2. **Auto-raise the setup hotspot when offline** (boot fallback service):
   ```bash
   sudo cp ~/drink-machine/deploy/wifi-fallback.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable wifi-fallback
   ```

3. **Reload the app** so the Network page + WiFi API go live:
   ```bash
   sudo systemctl restart drinkmachine
   ```

## Using it at a new location

1. Power on the Pi. It tries to join a remembered network; finding none, it
   raises the **DrinkMachine** hotspot (password set in the `DrinkMachine`
   nmcli profile).
2. On your phone, join **DrinkMachine**, then open **http://10.42.0.1:8000**.
3. Go to **Set Up Pumps → Network** (or `/network`).
4. Type the venue's WiFi name + password (or tap **Scan**), then **Connect**.
5. The Pi switches to the venue WiFi and the setup hotspot drops. Reconnect your
   phone to the venue WiFi and reopen **http://AngelsRaspberryPi4.local:8000**.

The venue network is now remembered, so next time you're there the Pi joins it
automatically with no setup.

## Notes / limitations

- The boot fallback only runs **at boot**. If WiFi drops mid-use it won't
  re-raise the hotspot until a reboot.
- A single-radio Pi can't scan while hosting the hotspot, so **Scan** may be
  empty in setup mode — it falls back to a list cached at boot, and manual entry
  always works.
- The sudoers rule lets the app run `nmcli` as root, and the app has no login.
  On a trusted home/party LAN that's fine; don't expose the app to the public
  internet as-is.
