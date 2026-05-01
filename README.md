# Voice Chat

Private text and voice chat for small groups over Tailscale.

## What it does

- Hosts a room with TCP text/image messaging and UDP voice relay
- Generates a shareable invite code
- Lets people join with the invite and chat over their Tailscale network

## Current status

This project is usable as a local prototype on Windows, but it still needs more end-to-end testing and packaging polish before wider distribution.

## Requirements

- Python 3.9+
- Tailscale installed and connected
- A working microphone and speaker/output device for voice chat
- `libopus.dll` in the repo root

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

`main.py` also launches the same GUI entry point.

Use the in-app `Diagnostics` button if startup, Tailscale detection, audio devices, or port binding seem wrong.

## Host a room

1. Make sure Tailscale is connected.
2. Click `Detect Tailscale IP` or enter your Tailscale IP/DNS name manually.
3. Click `Start Hosted Room`.
4. Share the generated invite code with the people joining.

The app also writes `invite.txt` and `invite.json` locally for convenience.

## Join a room

1. Make sure Tailscale is connected.
2. Paste the invite code into `Join Room`.
3. Click `Join Room`.

## Notes

- If voice dependencies or audio devices are missing, text chat can still connect and work.
- Image preview is currently limited to formats Tkinter can display directly.
- The app assumes the host machine is reachable over Tailscale on the configured TCP and UDP ports.

## Smoke test

```powershell
python -m unittest discover -s tests -v
python scripts/smoke_test.py
```

## Packaging

There is a checked-in `app.spec` for PyInstaller and a helper script for repeatable local packaging:

```powershell
.\package.ps1
```

The build should land in `dist\voice-chat\` or as `dist\voice-chat.exe` depending on the PyInstaller mode on that machine.
