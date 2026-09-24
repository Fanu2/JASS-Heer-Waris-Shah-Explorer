# JASS Heer Waris Shah Explorer

A beautiful offline-first PySide6 desktop explorer for the JASS SQLite edition of **Heer Waris Shah**.

## Features

- Browse all numbered sections
- Punjabi Gurmukhi reading view
- Verse-by-verse presentation
- Explanatory notes panel
- Full-text search using SQLite FTS5
- Dark / light themes
- Source PDF page references
- Open the original source PDF from the application
- No cloud service or account required

## Folder

Keep these files together:

```text
JASS_Heer_Waris_Shah_Explorer/
├── heer_explorer.py
├── JASS_Heer_Waris_Shah.db
└── Heer_WarisShah_PunjabiLibrary.pdf   # optional, for source access
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install PySide6
```

Windows:

```powershell
.venv\Scripts\activate
pip install PySide6
```

## Run

```bash
python heer_explorer.py
```

## Database

The explorer uses the supplied `JASS_Heer_Waris_Shah.db` and does not modify the source database while browsing.

The database retains source-page references and an extraction note because the original PDF contains some embedded-font/Unicode artifacts. Critical textual verification should therefore use the source PDF page.

## Suggested future versions

- Gurmukhi ↔ Shahmukhi paired text
- Roman transliteration
- English translation layer
- Section bookmarks and favourites
- Reading history
- Export selected verses to TXT / PDF
- Advanced linguistic search
- Word frequency explorer
- Character/place/theme index
- Audio recitation integration
- Dedicated JASS Language Data Lab page
