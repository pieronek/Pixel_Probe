
# RGB Under Cursor (Tkinter + WinAPI/GDI)

A small Windows utility that displays the global cursor position and the RGB color of the pixel under the cursor. The app is DPI-aware (Per-Monitor V2) and uses a robust WinAPI path (GDI `BitBlt` + `GetDIBits`) to read pixel data, which works more reliably than `GetPixel` across various DPI/compositing configurations.

![Screenshot](screenshots/demo.png)

## Features

- Live cursor coordinates (screen space)
- Live RGB readout under cursor + color swatch
- Per-Monitor V2 DPI awareness
- Simple Tkinter UI (Windows-only)

## Requirements

- Windows
- Python 3.8+
- Standard library only (`tkinter`, `ctypes`)

## Installation

```bash
git clone https://github.com/<USER>/<REPO>.git
cd <REPO>
python -m venv .venv
. .venv/Scripts/activate  # PowerShell: .venv\Scripts\Activate.ps1
pip install -U pip
```

## Run

```bash
python -m rgb_cursor.app
```

## Build (optional, PyInstaller)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name rgb-cursor src/rgb_cursor/app.py
# Output: dist/rgb-cursor.exe
```

## Development

```bash
pytest
ruff check .   # optional
black .        # optional
```

## Changelog

See CHANGELOG.md.

## Contributing

See CONTRIBUTING.md.

## Security

See SECURITY.md.

## License

MIT © Tomasz Zonenberg
