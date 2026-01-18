# Thikr App - Build Instructions

## File to Distribute
**Single file:** `dist\Thikr.exe`

Users just need this one file - no Python or dependencies required!

---

## Development Workflow

### 1. Test Changes (Development Mode)
```bash
# Run directly with Python for testing
py thikr.py
```

### 2. Build Executable (For Distribution)
```bash
# Build the standalone .exe file
py -m PyInstaller Thikr.spec --clean
```

The executable will be created at: `dist\Thikr.exe`

---

## Project Structure

```
ذكر_Thikr/
├── thikr.py              # Main source code (EDIT THIS)
├── Thikr.spec            # Build configuration
├── requirements.txt      # Python dependencies
├── data/                 # Data files (not needed for .exe)
│   ├── athkar.json
│   ├── settings.json
│   └── user_settings.json
├── build/                # Build cache (can delete)
└── dist/
    └── Thikr.exe         # DISTRIBUTE THIS FILE
```

---

## Adding New Features

1. **Edit** `thikr.py` with your changes
2. **Test** by running `py thikr.py`
3. **Build** with `py -m PyInstaller Thikr.spec --clean`
4. **Distribute** the new `dist\Thikr.exe`

---

## Important Notes

- User data is stored in: `%APPDATA%\Thikr\user_settings.json`
- Users can update the app by replacing `Thikr.exe` - their settings will be preserved
- The .exe file is ~200-300 MB because it includes the entire Python runtime and PyQt6

---

## Clean Build (if needed)

```bash
# Remove old build files
rm -rf build dist

# Rebuild from scratch
py -m PyInstaller Thikr.spec
```

---

## Requirements for Building

- Python 3.10+
- PyQt6 (`pip install PyQt6`)
- PyInstaller (`pip install pyinstaller`)

Install all dependencies:
```bash
pip install -r requirements.txt
pip install pyinstaller
```
