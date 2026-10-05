import io
import unittest
import mido
from app import app, parse_midi, assign, TUNINGS


class ConverterTests(unittest.TestCase):
    def midi_bytes(self):
        midi = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.extend([mido.Message('note_on', note=64, velocity=100),
                      mido.MetaMessage('set_tempo', tempo=1000000, time=480),
                      mido.Message('note_off', note=64, time=480)])
        out = io.BytesIO()
        midi.save(file=out)
        return out.getvalue()

    def test_tempo_change_duration(self):
        notes, _ = parse_midi(self.midi_bytes())
        self.assertAlmostEqual(notes[0]['duration'], 1.5)

    def test_editable_beat_duration_and_tempo_map(self):
        notes, _, tempo_map = parse_midi(self.midi_bytes(), include_tempo=True)
        self.assertEqual(notes[0]['duration_beats'], 2)
        self.assertEqual(tempo_map[-1]['bpm'], 60)
        self.assertEqual(tempo_map[-1]['beat'], 1)
        self.assertEqual(tempo_map[-1]['seconds'], .5)

    def test_sustained_notes_use_different_strings(self):
        notes = [dict(pitch=64, start=0, duration=1), dict(pitch=64, start=.5, duration=1)]
        result, _ = assign(notes, TUNINGS['Standard'], 24)
        self.assertNotEqual(result[0]['string'], result[1]['string'])

    def test_out_of_range_is_reported(self):
        result, warnings = assign([dict(pitch=20, start=0, duration=1)], TUNINGS['Standard'], 24)
        self.assertEqual(result, [])
        self.assertEqual(len(warnings), 1)

    def test_upload_endpoint(self):
        response = app.test_client().post('/api/convert', data={'file': (io.BytesIO(self.midi_bytes()), 'riff.mid')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['notes']), 1)

    def test_invalid_midi(self):
        response = app.test_client().post('/api/convert', data={'file': (io.BytesIO(b'bad'), 'bad.mid')})
        self.assertEqual(response.status_code, 400)

    def test_preset_order_defaults_to_six_strings(self):
        response = app.test_client().get('/api/tunings')
        self.assertEqual(next(iter(response.json)), 'Standard')
        self.assertEqual(len(response.json['Standard']), 6)

    def test_default_conversion_uses_six_strings(self):
        response = app.test_client().post('/api/convert', data={'file': (io.BytesIO(self.midi_bytes()), 'riff.mid')})
        self.assertEqual(response.json['tuning'], TUNINGS['Standard'])

    def test_fit_counts_match_actual_conversion(self):
        midi = mido.MidiFile()
        midi.tracks.append(mido.MidiTrack([
            mido.Message('note_on', note=37, velocity=100),
            mido.Message('note_off', note=37, time=480),
            mido.Message('note_on', note=68, velocity=100),
            mido.Message('note_off', note=68, time=480)]))
        out = io.BytesIO()
        midi.save(file=out)
        client = app.test_client()
        for frets in (12, 24):
            response = client.post('/api/analyze', data={'file': (io.BytesIO(out.getvalue()), 'riff.mid'), 'frets': str(frets)})
            self.assertEqual(response.status_code, 200)
            for fit in response.json['fits']:
                converted = client.post('/api/convert', data={'file': (io.BytesIO(out.getvalue()), 'riff.mid'), 'tuning': fit['name'], 'frets': str(frets)})
                self.assertEqual(fit['fitted'], len(converted.json['notes']))
                self.assertEqual(fit['full'], not converted.json['warnings'])

    def test_fit_counts_respect_selected_track_and_overlap(self):
        midi = mido.MidiFile()
        midi.tracks.append(mido.MidiTrack([mido.Message('note_on', note=20, velocity=100), mido.Message('note_off', note=20, time=480)]))
        midi.tracks.append(mido.MidiTrack([mido.Message('note_on', note=88, velocity=100), mido.Message('note_on', note=88, velocity=100), mido.Message('note_off', note=88, time=480), mido.Message('note_off', note=88)]))
        out = io.BytesIO()
        midi.save(file=out)
        response = app.test_client().post('/api/analyze', data={'file': (io.BytesIO(out.getvalue()), 'riff.mid'), 'track': '1'})
        standard = response.json['fits'][0]
        self.assertEqual(standard['total'], 2)
        self.assertEqual(standard['fitted'], 1)
        self.assertFalse(standard['full'])


if __name__ == '__main__':
    unittest.main()
