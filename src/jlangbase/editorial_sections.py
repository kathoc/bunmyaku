"""Section layout contracts; no paragraph-length quality thresholds."""
import re
import unicodedata


def validate_layout(response):
    blocks = response['paragraphs']
    headings = []
    for i, block in enumerate(blocks):
        match = re.match(r'^#{1,6}\s+(.+?)\s*$', block['text'])
        if not match:
            continue
        if block['text'].startswith('# '):
            raise ValueError('The article title belongs in brief.title, not display blocks')
        label = unicodedata.normalize('NFC', match[1])
        if any(unicodedata.category(c).startswith('P') for c in label):
            raise ValueError('Section headings cannot contain punctuation')
        if len(''.join(label.split())) > 13:
            raise ValueError('Section headings must be at most 13 characters')
        headings.append(i)
    heading_ids = {blocks[i]['id'] for i in headings}
    boundaries = response.get('paragraph_boundaries')
    if not isinstance(boundaries, list) or not all(isinstance(x, dict) for x in boundaries):
        raise ValueError('Need paragraph boundary records')
    if [x.get('paragraph_id') for x in boundaries] != [b['id'] for b in blocks if b['id'] not in heading_ids]:
        raise ValueError('Record every non-heading block boundary in order')
    for row in boundaries:
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in ('role', 'reason')):
            raise ValueError('Explain each boundary and its role')
    layout = response.get('section_layout')
    if not isinstance(layout, list) or not all(isinstance(x, dict) for x in layout):
        raise ValueError('Need section layout records')
    if [x.get('heading_id') for x in layout] != [blocks[i]['id'] for i in headings]:
        raise ValueError('Account for section headings in order')
    for n, row in enumerate(layout):
        end = headings[n + 1] if n + 1 < len(headings) else len(blocks)
        expected = [b['id'] for b in blocks[headings[n] + 1:end]]
        if not expected or row.get('body_ids') != expected:
            raise ValueError('Section body must match its contiguous display blocks')
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in ('draft_heading', 'reconsideration')):
            raise ValueError('Record the draft heading and its reconsideration')
