# Changelog

## [1.6.0] - 2026-09-30

### Added

- Phase 0 OS updates: read `/etc/cleepos_version`, bundled `os-catalog.json`
- RPC `get_os_info`, `get_os_updates`, `check_os_updates`
- Soft gate: block Cleep update when catalog marks OS update as required first
- OS updates tab: show CleepOs version, check for updates, apply minor OS playbook
- RPC `update_os` with shared update lock, progress events, reboot after success

## [1.5.0] - 2026-09-28

### Fixed

- If Cleep update enabled, never update applications
- Disabling auto update while updates were in progress will block later updates
- Send event to UI to say action is terminated
- Update application that crashes create deadlock in queue
- Better circular dependency detection
- Do not trigger cleep restart while app uninstall failed
- Fix typo in message log
- Missing need_restart flag reset
- Progress bar can never reach 100%
- Fix invalid var in ui
- Propery clean downloaded files

### Changed

- Add lock to avoid concurrency issues (for example simultaneous install and update)
- Implement progress during cleep update
- FS check before install
- Better error message

## [1.4.1] - 2024-10-18

### Updated

- Add log during application installation during compat checks

## [1.4.0] - 2024-10-12

### Fixed

- Fix documentation

### Changed

- Migrate to Cleep components
- Update after core changes (TaskFactory)

## [1.3.0] - 2023-02-12

### Changed

- Use new core AppsSources lib to handle multi apps sources

## [1.2.4] - 2022-02-22

### Fixed

- Fix problem to install dependencies from package

## [1.2.3] - 2022-01-31

### Fixed

- Copy package file instead instead of moving it

## [1.2.2] - 2022-01-31

### Fixed

- Fix compatibility check

### Added

- Check if applciation is already up to date before updating it

## [1.2.1] - 2022-01-30

### Added

- Add option to check compatibility

## [1.2.0] - 2021-07-09

### Added

- Add way to install module from zip package (useful for CI)

### Fixed

- Fix bug during uninstall: single package files wasn't uninstalled
- Fix bug when restarting previous installation

## [1.1.2] - 2021-06-08

- Remove useless tools file (transient file to wait for cleep v0.0.27)

## [1.1.1] - 2021-05-24

- Fix fatal issue during module update

## [1.1.0] - 2021-05-19

- Do not send need restart event if no actions performed
- Fix Dependencies installation of locally installed apps (for dev)
- Introduce compat flag to handle core releases
- Properly install/uninstall library modules

## [1.0.3] - 2021-05-11

- Backend: send need restart event after install/unsinstall/update
- Backend: add improvement to send end of process when really terminated
- Frontend: improve UI layout
- Frontend: fix cleep update displayed info after refresh

## [1.0.2] - 2021-05-04

- Frontend: fix typo
- Frontend: fix small layout issue
- Backend: fix final process status that was not properly sent
- Improve code quality and confidence

## [1.0.1] - 2021-04-11

- Fix tests
- Remove logging forced to TRACE

## [1.0.0] - 2020-12-13

- First release
