# Wii U Decrypted → WUA Converter

A two-step workflow and GUI tool for converting a library of encrypted Wii U game dumps into `.wua` archives ready to load in [Cemu](https://github.com/cemu-project/cemu).

---

## What It Does

Wii U games dumped from disc or NAND come in an encrypted format with a `title.tmd` / `title.tik` pair. Cemu's preferred format is `.wua` — a [ZArchive](https://github.com/Exzap/ZArchive) bundle that can contain a Base game, its Update, and any DLC all in one file.

This project handles both steps:

1. **Batch decrypt** — strip encryption from every game folder at once using `cdecrypt`
2. **Batch compile** — GUI tool that scans your decrypted library, groups Base + Update + DLC by title ID, and compiles each group into a single `.wua` file

---

## Step 1 — Batch Decrypt

### Requirement

- **cdecrypt** — [https://github.com/VitaSmith/cdecrypt](https://github.com/VitaSmith/cdecrypt)

Place `cdecrypt.exe` in the same folder as your encrypted game folders, then run the script below. It will find every folder that contains a `title.tmd` + `title.tik` pair and decrypt it in-place.

```bat
@echo off
for /d %%G in (*) do (
    if exist "%%G\title.tmd" (
        if exist "%%G\title.tik" (
            echo Decrypting game: %%G
            cdecrypt.exe "%%G\title.tmd" "%%G\title.tik"
        )
    )
)
echo Done!
pause
```

After this step each game folder will contain the standard decrypted layout:

```
GameName/
├── code/
├── content/
└── meta/
    └── meta.xml
```

---

## Step 2 — Compile .WUA Archives

### Requirements

- **Python 3.8+**
- **zarchive.exe** — compiled from [https://github.com/Exzap/ZArchive](https://github.com/Exzap/ZArchive)

### Running the GUI

```
python wua_generator_gui.py
```

### How It Works

The GUI reads `title_id` and `title_version` from each folder's `meta/meta.xml`. Title IDs follow a known prefix convention:

| Prefix | Type |
|--------|------|
| `00050000` | Base game |
| `0005000e` | Update |
| `0005000c` | DLC |

Titles that share the same lower 8 hex digits of their title ID are grouped together. When you click **Compile**, each group is staged into the correct ZArchive subdirectory structure (`<titleId>_v<version>/`) and passed to `zarchive.exe`, producing a single `.wua` file that Cemu can load with the update and DLC automatically applied.

### Workflow

1. Set **Source Library** — the folder containing your decrypted game subfolders
2. Set **Destination Directory** — where `.wua` files will be written
3. Point to your compiled **zarchive.exe**
4. Click **Deep Audit Folders** — the grid populates in real time as folders are discovered
5. Click **Compile Playable .WUA Archives** — progress bar tracks each group being compiled

The GUI saves your paths between sessions in `wua_generator_settings.json` next to the script.

---

## Output Structure (inside each .wua)

```
<game>.wua
├── 0005000012345678_v0/      ← Base game
│   ├── code/
│   ├── content/
│   └── meta/
├── 0005000e12345678_v64/     ← Update
│   ├── code/
│   ├── content/
│   └── meta/
└── 0005000c12345678_v0/      ← DLC
    ├── code/
    ├── content/
    └── meta/
```

---

## Dependencies

| Tool | Purpose | Link |
|------|---------|-------|
| cdecrypt | Decrypt Wii U title dumps | https://github.com/VitaSmith/cdecrypt |
| ZArchive / zarchive.exe | Build `.wua` / `.zar` archives | https://github.com/Exzap/ZArchive |
| Cemu | Wii U emulator that loads `.wua` | https://github.com/cemu-project/cemu |
