"""
Optional helper for creating a safe demonstration folder.

Run:
    python3 demo_test_files.py

It creates:
    demo_data/
        Documents/
        Images/
        ...
and several sample files.

This does NOT touch your Downloads/Desktop/etc.
"""

from pathlib import Path

def create_demo_data(base_path=None):
    """
    Creates a demonstration folder with various file types and deliberate duplicates.
    Safe for local testing without modifying real personal files.
    """
    base = Path(base_path) if base_path else Path("demo_data")
    base.mkdir(parents=True, exist_ok=True)

    samples = {
        "resume.pdf": b"Demo resume content for FileSense demonstration.\n" * 50,
        "resume_copy.pdf": b"Demo resume content for FileSense demonstration.\n" * 50,
        "notes.txt": b"OSTF Python FileSense project demonstration notes.\n",
        "meeting_minutes.docx": b"Project kickoff minutes and action items.\n",
        "photo.jpg": b"Fake image binary stream data for demo photo.\n" * 200,
        "photo_copy.jpg": b"Fake image binary stream data for demo photo.\n" * 200,
        "backup_photo.jpg": b"Fake image binary stream data for demo photo.\n" * 200,
        "song.mp3": b"Fake audio MP3 stream header and tags.\n" * 300,
        "project.zip": b"PK\x03\x04Demo archive bytes for project zip file.\n" * 150,
        "script.py": b"# FileSense demonstration script\nprint('Hello from FileSense')\n",
        "styles.css": b"body { font-family: sans-serif; background: #0f172a; }\n",
        "dataset.csv": b"id,name,role\n1,Alice,Engineer\n2,Bob,Designer\n3,Charlie,Product\n",
        "presentation.pptx": b"Slide 1: Architecture\nSlide 2: Algorithms\n",
        "recording.mp4": b"Fake video binary frame data for FileSense demo.\n" * 500,
    }

    for name, content in samples.items():
        (base / name).write_bytes(content)

    return base.resolve()

if __name__ == "__main__":
    folder = create_demo_data()
    print(f"Demo folder created at: {folder}")
    print("Select this folder in FileSense and click Scan.")

