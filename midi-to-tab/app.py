import io
from collections import defaultdict, deque

import mido
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")
app.json.sort_keys = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
TUNINGS = {
    "Standard": [40, 45, 50, 55, 59, 64],
    "Drop D": [38, 45, 50, 55, 59, 64],
    "D standard": [38, 43, 48, 53, 57, 62],
    "Drop C": [36, 43, 48, 53, 57, 62],
    "Open G": [38, 43, 50, 55, 59, 62],
    "Open D": [38, 45, 50, 54, 57, 62],
    "7-string standard": [35, 40, 45, 50, 55, 59, 64],
}


def parse_midi(data, include_tempo=False):
    midi = mido.MidiFile(file=io.BytesIO(data))
    if midi.type == 2:
        raise ValueError("Independent-pattern MIDI (type 2) is unsupported. Export a type 0 or 1 song.")
    events = []
    names = {}
    for track_id, track in enumerate(midi.tracks):
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "track_name":
                names[track_id] = msg.name
            events.append((tick, track_id, msg))
    events.sort(key=lambda e: e[0])
    active = defaultdict(deque)
    notes = []
    tempo, last_tick, seconds = 500000, 0, 0.0
    tempo_map = [dict(beat=0, seconds=0, bpm=120)]
    for tick, track, msg in events:
        seconds += mido.tick2second(tick - last_tick, midi.ticks_per_beat, tempo)
        last_tick = tick
        if msg.type == "set_tempo":
            tempo = msg.tempo
            tempo_map.append(dict(beat=tick/midi.ticks_per_beat, seconds=seconds,
                                  bpm=mido.tempo2bpm(tempo)))
        elif msg.type in ("note_on", "note_off") and msg.channel != 9:
            key = (track, msg.channel, msg.note)
            if msg.type == "note_on" and msg.velocity:
                active[key].append((seconds, tick, msg.velocity))
            elif active[key]:
                start, start_tick, velocity = active[key].popleft()
                notes.append(dict(pitch=msg.note, start=start, duration=max(.02, seconds-start),
                                  beat=start_tick/midi.ticks_per_beat, duration_beats=max(.01, (tick-start_tick)/midi.ticks_per_beat), track=track, velocity=velocity))
    for (track, channel, pitch), pending in active.items():
        for start, tick, velocity in pending:
            notes.append(dict(pitch=pitch, start=start, duration=max(.1, seconds-start),
                              beat=tick/midi.ticks_per_beat, duration_beats=max(.01, (last_tick-tick)/midi.ticks_per_beat), track=track, velocity=velocity))
    notes.sort(key=lambda n: (n["start"], n["pitch"]))
    if len(notes) > 20000:
        raise ValueError("Please export a shorter part (maximum 20,000 notes).")
    if include_tempo:
        return notes, names, tempo_map
    return notes, names


def assign(notes, tuning, max_fret):
    result, warnings = [], []
    occupied = [0.0] * len(tuning)
    position = 3
    for note in notes:
        candidates = [(i, note["pitch"] - pitch) for i, pitch in enumerate(tuning)
                      if 0 <= note["pitch"] - pitch <= max_fret and occupied[i] <= note["start"] + .001]
        if not candidates:
            warnings.append(f"{note['start']:.2f}s: MIDI note {note['pitch']} has no available string; omitted from tab playback.")
            continue
        string, fret = min(candidates, key=lambda p: abs(p[1]-position) + p[1]*.08)
        occupied[string] = note["start"] + note["duration"]
        if fret:
            position = fret
        result.append({**note, "string": string, "fret": fret})
    return result, warnings


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/tunings")
def tunings():
    return jsonify(TUNINGS)


@app.post("/api/convert")
@app.post("/api/analyze")
def convert():
    try:
        upload = request.files.get("file")
        if not upload:
            raise ValueError("Choose a MIDI file first.")
        tuning = TUNINGS[request.form.get("tuning", "Standard")]
        max_fret = int(request.form.get("frets", 24))
        if not 12 <= max_fret <= 24:
            raise ValueError("Frets must be between 12 and 24.")
        notes, names, tempo_map = parse_midi(upload.read(), include_tempo=True)
        tracks = [{"id": t, "name": names.get(t, f"Track {t+1}"), "count": sum(n['track']==t for n in notes)}
                  for t in sorted({n['track'] for n in notes})]
        selected = request.form.get("track", "all")
        if selected != "all":
            notes = [n for n in notes if n["track"] == int(selected)]
        if not notes:
            raise ValueError("No pitched notes found. Drum-channel notes are excluded.")
        if request.path == "/api/analyze":
            fits = []
            for name, preset in TUNINGS.items():
                fitted, _ = assign(notes, preset, max_fret)
                fits.append(dict(name=name, strings=len(preset), fitted=len(fitted),
                                 total=len(notes), full=len(fitted) == len(notes)))
            return jsonify(fits=fits, tracks=tracks)
        for note_id, note in enumerate(notes):
            note['id'] = note_id
        assigned, warnings = assign(notes, tuning, max_fret)
        return jsonify(notes=assigned, tracks=tracks, tuning=tuning, warnings=warnings,
                       source_notes=notes, tempo_map=tempo_map, tuning_name=request.form.get('tuning', 'Standard'),
                       total=len(notes), duration=max(n['start']+n['duration'] for n in notes))
    except (ValueError, KeyError, OSError, EOFError) as exc:
        return jsonify(error=str(exc) or "This file could not be read as MIDI."), 400


@app.errorhandler(413)
def too_large(error):
    return jsonify(error="File too large. Maximum upload is 8 MB."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
