# Update [![Coverage Status](https://coveralls.io/repos/github/tangb/cleepapp-update/badge.svg?branch=master)](https://coveralls.io/github/tangb/cleepapp-update?branch=master) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/59cdca41e1984f83b035c639104c0d44)](https://www.codacy.com/gh/CleepDevice/cleepapp-update/dashboard?utm_source=github.com&amp;utm_medium=referral&utm_content=CleepDevice/cleepapp-update&amp;utm_campaign=Badge_Grade)

![update](https://github.com/CleepDevice/cleepapp-update/raw/master/resources/update.jpg)

Update module for Cleep.

This core application keeps your device up to date:

- **Applications** — check and install updates from the Cleep market
- **Cleep** — upgrade the Cleep core package
- **CleepOs** — apply minor system upgrades on the same Debian suite (for example bullseye → newer bullseye snapshot)

## OS updates

The **OS** tab shows the current CleepOs version (`/etc/cleepos_version`), lets you check the catalog, run a **dry-run** (apt simulation only), then **Apply**.

OS update metadata comes from [`CleepDevice/cleep-os`](https://github.com/CleepDevice/cleep-os) (`os-versions.json` + `playbooks/`). The app caches the last successful download under `/tmp/cleep/`.

After a successful apply:

- a **Reboot to apply changes** button appears in the **top bar** (device reboot — packages need a full Pi reboot, not a Cleep-only restart)
- the last attempt (status, date, error) is saved in module config
- you can open the upgrade log from the UI

Optional **OS conf leftover report** (Options): path-only scan of leftover `.dpkg-*` / `.ucf-*` files after an upgrade — never configuration file contents — to help improve future migrations.

## Automatic updates

In Options you can enable automatic daily checks/updates for Cleep and/or applications. OS upgrades stay manual.
