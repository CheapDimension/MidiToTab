# Fretboard ? MIDI to guitar tab

A Python/Flask web app that converts FL Studio MIDI exports into guitar tablature. Includes drag-and-drop upload, tuning presets with note-fit counts, track selection, synthesized playback, BPM control, note editing, and text tab export.

## Requirements

- Python 3.12 or newer with pip: https://www.python.org/downloads/
- A modern browser with Web Audio support (Chrome, Edge, Firefox, or Safari).
- Internet access for initial dependency installation.
- Optional: Node.js for the editor logic test. It is not needed to run the app.

## Windows setup

Extract `midi-to-tab-source.zip`. Open PowerShell inside the extracted `midi-to-tab` folder containing `app.py` and `requirements.txt`.

Run these commands once:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the app:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:5000** in your browser. Keep the terminal open while using the app. Stop the server with **Ctrl+C**. To start again, run the same start command; dependency installation is only needed initially or when requirements change. Virtual environment activation is unnecessary.

If `py` is unavailable but `python --version` reports Python 3.12 or newer, use `python -m venv .venv` instead.

## macOS / Linux setup

Open a terminal inside the extracted project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:5000**. Stop the server with **Ctrl+C**.

## Using the app

1. Export MIDI from FL Studio, then drop the `.mid` or `.midi` file onto the page or click to browse. Maximum upload: 8 MB; maximum pitched notes: 20,000.
2. Select the instrument track, or use all pitched tracks. Channel 10 percussion is excluded.
3. Compare tuning options by string count and fitted notes / total. Enable **Show only tunings that fit every note** to hide partial fits. Counts update when the track or maximum fret changes.
4. Click **Generate tab**. Presets include Standard, Drop D, D standard, Drop C, Open G, Open D, and seven-string Standard.
5. Play, pause, stop, seek, or change speed. MIDI velocity controls synthesized volume.
6. Change **BPM** to scale playback tempo. MIDI tempo changes are preserved and scaled together; note positions in beats remain unchanged.
7. Click a fret number to edit string, fret, start beat (1-based), length in beats, or velocity. You can delete it too. Overlapping sustained notes on the same string are rejected. **Reset edits** restores the generated tab and original tempo.
8. Download `.txt` to export edited fret positions and the chosen BPM. Onsets are rounded to sixteenth-note columns. The export does not encode durations or velocity and cannot be reimported into the editor.

Edits stay in the current browser session. Refreshing, uploading, or regenerating replaces them.

## Hosting on Render

Deploy this app as a **Web Service**, which serves both the Python backend and UI. No database or separate frontend hosting is required.

1. Create a GitHub repository and upload the project contents. Put `app.py`, `requirements.txt`, and `README.md` at its root, with `static/` and `tests/` alongside them. Include `.gitignore`. Do not upload `.venv/`, `__pycache__/`, `.git/`, or the ZIP.
2. Sign in at https://dashboard.render.com and select **New ? Web Service**.
3. Connect the GitHub repository and choose the branch to deploy.
4. Enter these settings:

| Setting | Value |
| --- | --- |
| Language / runtime | Python 3 |
| Root directory | Leave blank if `app.py` is at the repository root |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| Instance plan | Free for trying the app, or paid for regular availability |

If the project sits in a repository subfolder, set **Root directory** to that subfolder.

5. Create the service and wait for deployment. Render provides a public HTTPS URL such as `https://your-service.onrender.com`.
6. Open the URL and test upload, conversion, and playback. Subsequent pushes to the connected branch can trigger automatic deployment.

`requirements.txt` includes Gunicorn for non-Windows systems, including Render's Linux environment. Use Gunicorn on Render instead of the local Flask development server. Render supplies `PORT`; this version needs no app secrets or custom environment variables.

The free service sleeps after 15 minutes without inbound traffic; waking can take about a minute. MIDI uploads are processed in memory and are not saved by this app. Browser sessions have separate edits; there is no shared-project or persistent-storage feature.

Official documentation: [Deploy Flask](https://render.com/docs/deploy-flask), [Web Services](https://render.com/docs/web-services), [Free plan limitations](https://render.com/docs/free).

## Tests

From the project folder on Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node tests/test_editor.cjs
```

On macOS or Linux:

```sh
.venv/bin/python -m unittest discover -s tests
node tests/test_editor.cjs
```

Python tests cover conversion, tempo maps, overlap handling, tuning-fit counts, and invalid MIDI. The optional Node test checks editor logic with a simulated browser document.

## Limitations and troubleshooting

- Fingering is heuristic: full fit does not guarantee comfortable chord stretches. Dense piano voicings may need arranging.
- Unavailable or out-of-range notes are flagged and omitted from tab playback.
- Sustain pedal, pitch bends, and guitar articulations are not interpreted.
- Playback uses a synthesized plucked tone, not the FL Studio instrument sound.
- Visible tabs show note onsets on a beat grid, not full rhythmic notation with rests and ties.
- If port 5000 is occupied, stop the other local server first.
- If Render deployment fails, check its logs, root directory, and build/start commands.
- If audio is silent, click Play to enable browser audio and check device/tab volume.

## Source files

```text
midi-to-tab/
  app.py                    Flask backend and converter
  requirements.txt          Python dependencies
  README.md                 Setup, usage, hosting instructions
  .gitignore                Excludes environments and caches
  static/
    index.html              UI, tab rendering, playback
    editor.js               BPM and note editing
  tests/
    test_converter.py       Python conversion tests
    test_editor.cjs          Node editor logic checks
```
