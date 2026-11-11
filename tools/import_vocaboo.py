#!/usr/bin/env python3
"""Import the Level 3–5 workbook (字彙王 Level 3–5 練習題本) from the Vocaboo repo
(shuanmaker-web/vocab-app, data/questions.json) into material/l35-NN.txt.

Usage:  python3 tools/import_vocaboo.py path/to/vocab-app/data/questions.json
Then:   python3 tools/build_data.py path/to/ecdict.csv

Vocaboo's answers and Chinese glosses were checked item by item against the workbook's
official answer key, so nothing here is marked as derived (~!). Question text was
transcribed from photos; see Vocaboo tools/CHECKLIST_uncertain.md.

Each unit has 20 questions: 1–5 文意字彙 (fill), 6–10 選擇題 (choice, 4 options),
11–15 and 16–20 配合題 (bank of 6 words each).
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, 'material')

# units whose question text the Vocaboo checklist flags as uncertain (photo edges / glare)
UNCERTAIN = {19: '部分句子左側邊緣被切到，開頭文字依語意補回', 29: '部分句子左側邊緣被切到，開頭文字依語意補回',
             33: '部分句子左側邊緣被切到，開頭文字依語意補回', 35: '部分句子左側邊緣被切到，開頭文字依語意補回；Q12、Q13 的人名（Tom / Dan）為補回',
             44: '照片邊緣或反光處，個別字詞可能有誤', 45: '照片邊緣或反光處，個別字詞可能有誤',
             55: '照片邊緣或反光處，個別字詞可能有誤', 56: '照片邊緣或反光處，個別字詞可能有誤',
             57: '照片邊緣或反光處，個別字詞可能有誤', 58: '照片邊緣或反光處，個別字詞可能有誤'}


def one_line(s):
    return ' '.join(str(s).split())


def analysis(q):
    lemma = q['wid'][2:] if q.get('wid', '').startswith('m-') else q['ans']
    out = [f"~詞義 {lemma}（{q['pos']}）{q['zh']}"]
    if q.get('full'):
        out.append(f"~原文 {one_line(q['full'])}")
    return out


def unit_text(u, qs):
    qs = sorted(qs, key=lambda x: x['no'])
    types = [q['type'] for q in qs]
    assert types == ['fill'] * 5 + ['mcq'] * 5 + ['match'] * 10, (u, types)
    note = '字彙王 Level 3–5 練習題本。答案與中文詞義已與教材官方解答逐題核對；題目文字為照片轉錄。'
    if u in UNCERTAIN:
        note += f'本單元請抽查：{UNCERTAIN[u]}。'
    L = [f'# Level 3–5 · Unit {u} — imported from Vocaboo (vocab-app data/questions.json) by tools/import_vocaboo.py',
         '# Do not edit by hand; re-run the importer instead.',
         f'@section l35-{u:02d} | Unit {u} | Vocabulary practice · Unit {u} | 文意字彙・選擇題・配合題',
         f'@overview {note}', '']
    L += ['@group A 文意字彙（1–5）：依提示寫出正確的字', '']
    for q in qs[:5]:
        L += [f"Q {q['no']} | fill | 文意字彙", f"stem: {one_line(q['q'])}", f"= {q['ans']}", *analysis(q), '']
    L += ['@group B 選擇題（6–10）', '']
    for q in qs[5:10]:
        opts = q['opts']
        assert len(opts) == 4 and q['ans'] in opts, (u, q['no'])
        L += [f"Q {q['no']} | choice | 選擇題", f"stem: {one_line(q['q'])}"]
        L += [f'{chr(65 + i)}: {one_line(o)}' for i, o in enumerate(opts)]
        L += [f"= {chr(65 + opts.index(q['ans']))}", *analysis(q), '']
    for start in (10, 15):
        grp = qs[start:start + 5]
        bank = grp[0]['opts']
        assert all(x['opts'] == bank for x in grp) and len(bank) == 6, (u, start)
        L += [f"@group C 配合題（{grp[0]['no']}–{grp[-1]['no']}）：從單字庫選出最適合的字", '', '@bank']
        L += [f'{chr(65 + i)}: {one_line(o)}' for i, o in enumerate(bank)]
        L += ['']
        for q in grp:
            assert q['ans'] in bank, (u, q['no'])
            L += [f"Q {q['no']} | bank | 配合題", f"stem: {one_line(q['q'])}",
                  f"= {chr(65 + bank.index(q['ans']))}", *analysis(q), '']
    return '\n'.join(L).rstrip() + '\n'


def main():
    src = sys.argv[1]
    data = json.load(open(src, encoding='utf-8'))
    by = collections.defaultdict(list)
    for q in data['questions']:
        by[q['unit']].append(q)
    for u in sorted(by):
        with open(os.path.join(MAT, f'l35-{u:02d}.txt'), 'w', encoding='utf-8') as f:
            f.write(unit_text(u, by[u]))
    print(f'units={len(by)} questions={sum(len(v) for v in by.values())} -> material/l35-*.txt')


if __name__ == '__main__':
    main()
