# Wii U NUS → WUA Converter

A three-step workflow and GUI tool for downloading Wii U games from Nintendo's servers and converting them into `.wua` archives ready to load in [Cemu](https://github.com/cemu-project/cemu).

---

## What It Does

Wii U games are distributed in Nintendo's encrypted NUS format — a folder containing `title.tmd`, `title.tik`, and the encrypted content. Cemu's preferred format is `.wua` — a [ZArchive](https://github.com/Exzap/ZArchive) bundle that holds a Base game, its Update, and any DLC all in one file.

This project handles the full pipeline:

1. **Download** — grab the encrypted NUS package directly from Nintendo's servers
2. **Decrypt** — strip encryption from every game folder at once
3. **Compile** — GUI tool that groups Base + Update + DLC by title ID and builds each group into a single `.wua`

---

## Step 1 — Download from Nintendo

### Requirement

- **WiiUDownloader** — [https://github.com/Xpl0itU/WiiUDownloader](https://github.com/Xpl0itU/WiiUDownloader)

WiiUDownloader lets you search for and download any Wii U title (Base, Update, DLC) directly from Nintendo's NUS servers. Each title lands in its own folder containing the encrypted NUS files (`title.tmd`, `title.tik`, and the `.app` content files).

---

## Step 2 — Batch Decrypt

### Requirement

- **cdecrypt** — [https://github.com/VitaSmith/cdecrypt](https://github.com/VitaSmith/cdecrypt)

Place `cdecrypt.exe` in the same folder as your downloaded game folders, then run the script below. It finds every folder that contains a `title.tmd` + `title.tik` pair and decrypts it in-place.

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

## Step 3 — Compile .WUA Archives

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

Titles that share the same lower 8 hex digits of their title ID are grouped together. When you click **Compile**, each group is staged into the correct ZArchive subdirectory structure (`<titleId>_v<version>/`) and passed to `zarchive.exe`, producing a single `.wua` file that Cemu loads with the update and DLC automatically applied.

### Workflow

1. Set **Source Library** — the folder containing your decrypted game subfolders
2. Set **Destination Directory** — where `.wua` files will be written
3. Point to your compiled **zarchive.exe**
4. Click **Deep Audit Folders** — the grid populates in real time as folders are discovered, showing each title's type (Base / Update / DLC) and whether a `.wua` already exists
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
| WiiUDownloader | Download encrypted NUS titles from Nintendo | https://github.com/Xpl0itU/WiiUDownloader |
| cdecrypt | Decrypt Wii U NUS dumps | https://github.com/VitaSmith/cdecrypt |
| ZArchive / zarchive.exe | Build `.wua` / `.zar` archives | https://github.com/Exzap/ZArchive |
| Cemu | Wii U emulator that loads `.wua` | https://github.com/cemu-project/cemu |
