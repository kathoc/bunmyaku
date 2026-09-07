import json
import os
from pathlib import Path
import subprocess
import sys
from jlangbase.craft import reading_map
from jlangbase.db import text_hash


def review(text, paragraph):
    return {'text_hash': text_hash(text), 'reviewer': 'test', 'reviewer_kind': 'model', 'document_scope': 'opening_excerpt', 'nodes': [],
            'frictions': [{'id': 'scale', 'kind': 'scale_jump', 'anchor': {'paragraph': paragraph, 'quote': '3万回'},
                'foothold': {'paragraph': 1, 'quote': 'マリオ'}, 'reader_question': '本当か', 'benefit': '予想を変える仮説',
                'risk': '事実なら裏付けが必要', 'decision': 'test', 'decision_reason': '位置を比較', 'necessity': 'optional',
                'resolution': 'open', 'payoff': None, 'confidence': .8, 'claim_status': 'illustrative'}]}


def test_position_is_measured_not_scored():
    early = 'マリオを3万回遊んだ。\n\n調整について考える。'
    late = 'マリオの調整について考える。\n\n3万回遊んだ。'
    a = reading_map(early, review=review(early, 1), rhythm_backend='basic')
    b = reading_map(late, review=review(late, 2), rhythm_backend='basic')
    assert a['friction_locations'][0]['preceding_characters'] < b['friction_locations'][0]['preceding_characters']
    assert a['friction_locations'][0]['claim_status'] == 'illustrative'
    assert a['quality_score'] is b['quality_score'] is None
    assert a['paragraphs'][0]['numeric_cues'] == ['3万回']


def test_reading_map_with_no_site_packages_or_personal_environment(tmp_path):
    source = tmp_path / 'input.md'
    source.write_text('かなだけの、みじかいぶん。', encoding='utf-8')
    root = Path(__file__).resolve().parents[1]
    env = {'PYTHONPATH': str(root / 'src'), 'PYTHONIOENCODING': 'utf-8'}
    result = subprocess.run([sys.executable, '-S', '-m', 'jlangbase', 'reading-map', str(source),
                             '--rhythm-backend', 'basic', '--out', str(tmp_path / 'out')],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / 'out/reading-map.json').read_text())
    assert data['rhythm']['mora_coverage'] == 1
