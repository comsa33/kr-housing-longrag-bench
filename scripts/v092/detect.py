#!/usr/bin/env python3
"""Detect v0.9.2 test-confirmed defect patterns in KR-Housing QA items (no API calls).

P1 dual_row        : table_numeric_reasoning / eligibility_reasoning item whose target cell's row is
                     followed (same table) by a continuation row (empty row label, no first-column
                     label) that has a non-empty cell in the same column -> row x column has two values.
                     Subset P1_strict: the continuation row text marks a dual-income criterion
                     (맞벌이 / 본인 및 배우자 / 모두 소득).
P2 multi_schedule  : schedule_reasoning item whose target column holds more than one schedule value
                     under the same row header (target row + its continuation rows, or, when the target
                     row itself has an empty label, all data rows of that column).
P3 header_misparse : item whose target cell's row label is a value (number/percent) named in the question
                     (loose), AND the table shows a misparse signature (strict): the column-0 header shares a
                     >=5-char prefix with the target column header (parallel data headings), or the table has
                     a single data row (so column 0 holds a value, not a row label).
Primary flags = P1 strict + P2 + P3 strict. Loose variants are kept in the output with strict=false.
Table cells are read from the internal working area (workspace_local/processed/**/table_cells.jsonl,
not released); pass --cells-root to point elsewhere.

Usage: python3 scripts/v092/detect.py data/qa_v0.6_dev.jsonl [--out all.jsonl] [--out-primary primary.jsonl]
"""
import json, glob, re, sys, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CELLS_ROOT = ROOT / 'workspace_local' / 'processed'
LEGAL = 'cross_document_legal_reasoning'
DUAL_KW = re.compile(r'맞벌이|본인\s*및\s*배우자|모두\s*소득|배우자\s*소득이\s*있')
VALUE_LIKE = re.compile(r'^[\s\d.,%~()\-+원만천억㎡세대호년월일회개인이상하초과미만]*\d[\s\d.,%~()\-+원만천억㎡세대호년월일회개인이상하초과미만]*$')

def load_cells(root=CELLS_ROOT):
    idx = {}
    for f in sorted(glob.glob(f'{root}/**/table_cells.jsonl', recursive=True)):
        for l in open(f, encoding='utf-8'):
            c = json.loads(l)
            idx.setdefault(c['table_id'], {})[(c['row_index'], c['col_index'])] = c
    return idx

def parse_cell_id(cid):
    m = re.match(r'^(.*)#r(\d+)c(\d+)$', cid)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None

def is_cont(tab, r):
    """Row r is a continuation row: exists, empty row label, no non-empty first-column cell."""
    rc = [k for k in tab if k[0] == r]
    if not rc: return False
    lab = (tab[rc[0]].get('row_header') or '').strip()
    c0 = tab.get((r, 0))
    return lab == '' and (c0 is None or not (c0.get('cell_text') or '').strip())

def txt(tab, r, c):
    x = tab.get((r, c)); return (x.get('cell_text') or '').strip() if x else ''

def detect(item, cells):
    out = []
    tt = item['task_type']
    for cid in item.get('cell_ids') or []:
        p = parse_cell_id(cid)
        if not p or p[0] not in cells: continue
        tid, r, c = p; tab = cells[tid]; tgt = tab.get((r, c))
        if tgt is None: continue
        rows = sorted({k[0] for k in tab})
        # following continuation rows of the target row
        conts = []; rr = r + 1
        while rr in rows and is_cont(tab, rr):
            conts.append(rr); rr += 1
        if tt in ('table_numeric_reasoning', 'eligibility_reasoning'):
            alts = [(x, txt(tab, x, c)) for x in conts if txt(tab, x, c) and txt(tab, x, c) != txt(tab, r, c)]
            if alts:
                row_text = ' '.join(txt(tab, alts[0][0], k[1]) for k in tab if k[0] == alts[0][0])
                out.append(dict(pattern='P1_dual_row', strict=bool(DUAL_KW.search(row_text)), cell=cid,
                                gold_cell=txt(tab, r, c)[:80], alt_cells=[a[1][:80] for a in alts]))
        if tt == 'schedule_reasoning':
            if is_cont(tab, r) or (tgt.get('row_header') or '').strip() == '':
                group = [x for x in rows if x > 0]          # label-less target: whole column
            else:
                group = [r] + conts
            vals = [txt(tab, x, c) for x in group if txt(tab, x, c)]
            if len(vals) > 1:
                out.append(dict(pattern='P2_multi_schedule', cell=cid, gold_cell=txt(tab, r, c)[:80], values=[v[:60] for v in vals]))
        lab = (tgt.get('row_header') or '').strip()
        if lab and VALUE_LIKE.match(lab) and lab in item['question'] and c != 0:
            # misparse signature: the first column's header is a parallel *data* heading, i.e. it shares a
            # long common prefix with the target column's header (e.g. '거주기간 초과자의 최초 …' vs
            # '거주기간 초과자의 2회차 …'), so the 'label' in column 0 is really a value of that column.
            h0 = re.sub(r'\s+', '', (tab.get((0, 0)) or {}).get('cell_text') or '')
            hc = re.sub(r'\s+', '', tgt.get('col_header') or '')
            pre = 0
            while pre < min(len(h0), len(hc)) and h0[pre] == hc[pre]: pre += 1
            # second signature: the table has a single data row, so column 0 holds a value, not a label.
            n_data_rows = len([x for x in rows if x > 0])
            out.append(dict(pattern='P3_header_misparse', strict=(pre >= 5 or n_data_rows == 1),
                            common_prefix=pre, n_data_rows=n_data_rows, cell=cid,
                            row_label=lab, gold_cell=txt(tab, r, c)[:80]))
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('qa'); ap.add_argument('--out')
    ap.add_argument('--out-primary', help='write primary flags only (P1/P3 strict, P2 all)')
    ap.add_argument('--cells-root', default=str(CELLS_ROOT))
    a = ap.parse_args(); cells = load_cells(a.cells_root)
    flags = []
    for l in open(a.qa, encoding='utf-8'):
        it = json.loads(l)
        if it['task_type'] == LEGAL: continue
        for f in detect(it, cells):
            flags.append(dict(qa_id=it['qa_id'], split=it['split'], task_type=it['task_type'], **f))
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as fo:
            for f in flags: fo.write(json.dumps(f, ensure_ascii=False) + '\n')
    if a.out_primary:
        with open(a.out_primary, 'w', encoding='utf-8') as fo:
            for f in flags:
                if f.get('strict', True): fo.write(json.dumps(f, ensure_ascii=False) + '\n')
    from collections import Counter
    print('loose:', Counter(f['pattern'] for f in flags))
    print('primary (P1/P3 strict, P2 all):', Counter(f['pattern'] for f in flags if f.get('strict', True)))
    print('items:', len({f['qa_id'] for f in flags}))
