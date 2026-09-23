# FileSense

**Smart File Organizer & Duplicate Detector**

A Python-based OSTF tiny project that helps users analyze and organize a messy folder.

## Features

- Scan a selected folder recursively
- Categorize files by extension
- Calculate total storage usage
- Detect duplicate files using SHA-256
- Estimate recoverable storage
- Display the largest files
- Organize files into category folders
- Generate a text report
- User confirmation before moving files
- Works offline
- No API keys or paid services

## Technologies

- Python 3
- Tkinter
- pathlib
- shutil
- hashlib
- datetime
- collections

All functionality is based on Python's standard library.

## Project Structure

```text
FileSense/
├── main.py
├── scanner.py
├── organizer.py
├── duplicate_finder.py
├── report.py
├── requirements.txt
└── README.md
```

## Requirements

Python 3.9+ is recommended.

On macOS, verify Python:

```bash
python3 --version
```

Tkinter is normally included with the official Python installer. Test it with:

```bash
python3 -m tkinter
```

If a small Tk window opens, Tkinter is working.

## Run

Open Terminal inside the FileSense folder:

```bash
python3 main.py
```

## How to demonstrate it

1. Create a test folder.
2. Put several documents, images, videos, and ZIP files inside it.
3. Make a few copies of the same files.
4. Open FileSense.
5. Select the test folder.
6. Click **Scan**.
7. Show:
   - Total files
   - Storage usage
   - Duplicate files
   - Recoverable storage
   - Categories
   - Largest files
8. Generate a report.
9. Click **Organize Files** after confirming.

### Important

Always demonstrate using a test folder first. The organizer moves files into category folders.

## Example

Before:

```text
DemoFolder/
├── resume.pdf
├── resume_copy.pdf
├── photo.jpg
├── song.mp3
├── project.zip
└── notes.txt
```

After organization:

```text
DemoFolder/
├── Documents/
│   ├── resume.pdf
│   ├── resume_copy.pdf
│   └── notes.txt
├── Images/
│   └── photo.jpg
├── Music/
│   └── song.mp3
└── Archives/
    └── project.zip
```

## Project objective

The objective is to demonstrate how Python can be used to solve a practical file-management problem through automation, hashing, file-system operations, GUI programming, and report generation.

## Future enhancements

- Drag-and-drop folders
- SQLite scan history
- Scheduled cleanup
- Configurable file categories
- Export reports as CSV/PDF
- Dark mode
- Storage charts
- File age analysis
- "Safe cleanup" recommendations
