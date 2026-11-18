#!/usr/bin/env python3
"""Build data.js + dictionary.js for the Workbook reader from tools/../material/*.txt

Usage:  python3 tools/build_data.py [path/to/ecdict.csv]
  - data.js        window.EXAM   (sections, word entries, passages, questions, analyses)
  - dictionary.js  window.DICTIONARY (tap-to-define: workbook glosses first, then ECDICT, converted to Traditional)

Books: edit BOOKS / UNITS below. To add a new book's material: add its units to UNITS (with 'book'),
its sections to ORDER and FILES, then put the .txt files in material/.

Material grammar (see material/*.txt headers):
  @section id | 標題 | English | range      @pages 6,7     @overview text
  @group title            starts a group (word entries / passages / questions follow)
  @page n                 source page of the following word entries
  = word                  start a word entry (outside Q blocks); plain lines = senses
  [ˈfɔnɪk]                phonetic (first "[...]" line of an entry; shown next to the headword)
  > phrase  中文          phrase line (two spaces between phrase and 中文)
  +同義 / +反義 / +諺語 text   note;  +例 English | 中文   example
  * 96指考 | English | 中文   boxed exam sentence
  @bank  ... "A: text" lines until a blank line     (answer bank for 'bank' questions)
  @passage ... @end         paragraphs separated by blank lines; [[n]] = blank of question n
  Q n | type | src          type: choice | multi | bank | fill | trans | write
    stem: ...   (continuation lines start with two spaces)   A: ... J: ...
    = answer                 (fill: alternatives separated by " | "; trans: one reference translation, shown on reveal, not auto-graded)
    ~ text / ~label text / ~! text (derived by Claude)       analysis lines
    (trans uses ~替換 word: alt1 / alt2 for the book's 替換詞 lists)
    write: writing prompt; "= model essay" is optional (" ¶ " = paragraph break); students write on paper
"""
import csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, 'material')

# Books = the top level of the app (home page shows one card per book).
# Every unit belongs to exactly one book; a book with no sections yet shows its `plan` as "準備中".
BOOKS = [
    {'id': 'dmg', 'title': 'Grand Slam', 'english': '', 'sub': '單字・綜合測驗・文意選填・篇章結構・閱讀・翻譯', 'plan': []},
    {'id': 'cloze', 'title': 'Cloze Power-Up', 'english': '', 'sub': '克漏字', 'plan': []},
    {'id': 'win', 'title': 'Beat the GSAT', 'english': '', 'sub': '綜合測驗・文意選填・篇章結構・閱讀測驗・混合題', 'plan': []},
    {'id': 'l35', 'title': 'Level 3–5', 'english': '', 'sub': '字彙王練習題本・文意字彙・選擇題・配合題', 'plan': []},
]
UNITS = [
    # kind: 'unit' (regular units), 'trans' (translation) or 'write' (writing) — the app's quick-switch bar has one tab per kind.
    {'id': 'u1', 'book': 'dmg', 'kind': 'unit', 'title': 'Unit 1', 'sub': '單字、片語・綜合測驗・篇章結構・閱讀測驗'},
    {'id': 'u2', 'book': 'dmg', 'kind': 'unit', 'title': 'Unit 2', 'sub': '單字、片語・文意選填・篇章結構・閱讀測驗'},
    {'id': 'u3', 'book': 'dmg', 'kind': 'unit', 'title': 'Unit 3', 'sub': '單字、片語・綜合測驗・篇章結構・閱讀測驗'},
    {'id': 'u4', 'book': 'dmg', 'kind': 'unit', 'title': 'Unit 4', 'sub': '單字、片語・文意選填・篇章結構・閱讀測驗'},
    {'id': 'gs1', 'book': 'dmg', 'kind': 'unit', 'title': '特訓（一）', 'sub': '大滿貫特訓（一）・詞彙題'},
    {'id': 'tr1', 'book': 'dmg', 'kind': 'trans', 'title': '翻譯（一）', 'sub': '表目的句法'},
    {'id': 'tr2', 'book': 'dmg', 'kind': 'trans', 'title': '翻譯（二）', 'sub': '以動詞開頭'},
    {'id': 'tr3', 'book': 'dmg', 'kind': 'trans', 'title': '翻譯（三）', 'sub': '現在完成式'},
    {'id': 'tr4', 'book': 'dmg', 'kind': 'trans', 'title': '翻譯（四）', 'sub': '名詞子句'},
    {'id': 'trr1', 'book': 'dmg', 'kind': 'trans', 'title': '複習（一）', 'sub': '翻譯複習（一）'},
    {'id': 'wr1', 'book': 'dmg', 'kind': 'write', 'title': '寫作（一）', 'sub': '表個人看法／意見／經驗分享'},
    {'id': 'wr2', 'book': 'dmg', 'kind': 'write', 'title': '寫作（二）', 'sub': '表達優缺／利弊／正反面'},
    {'id': 'w8', 'book': 'win', 'kind': 'unit', 'title': 'Unit 8', 'sub': '綜合測驗・文意選填・篇章結構・閱讀測驗・混合題'},
    {'id': 'w9', 'book': 'win', 'kind': 'unit', 'title': 'Unit 9', 'sub': '綜合測驗・文意選填・篇章結構・閱讀測驗・混合題'},
    {'id': 'w10', 'book': 'win', 'kind': 'unit', 'title': 'Unit 10', 'sub': '綜合測驗・文意選填・篇章結構・閱讀測驗・混合題'},
    {'id': 'cz41', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 41', 'sub': 'Energy・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz42', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 42', 'sub': 'Energy・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz43', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 43', 'sub': 'Energy・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz44', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 44', 'sub': 'Energy・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz45', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 45', 'sub': 'Technology・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz46', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 46', 'sub': 'Technology・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz47', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 47', 'sub': 'Technology・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz48', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 48', 'sub': 'Technology・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz49', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 49', 'sub': 'Plants・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz50', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 50', 'sub': 'Plants・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz51', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 51', 'sub': 'Plants・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz52', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 52', 'sub': 'Plants・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz53', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 53', 'sub': 'Society・綜合測驗・文意選填・篇章結構'},
    {'id': 'cz54', 'book': 'cloze', 'kind': 'unit', 'title': 'Unit 54', 'sub': 'Society・綜合測驗・文意選填・篇章結構'},
]
assert all(u['book'] in {b['id'] for b in BOOKS} for u in UNITS), 'unit with unknown book'
assert all(u.get('kind') in ('unit', 'trans', 'write') for u in UNITS), 'unit without kind'
# section id -> (unit, title, english, range, pages, overview) for sections whose file has no full @section header
VOCAB_META = {
    'u1-vocab': ('u1', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [6, 7, 8, 9, 10],
                 '學測重點單字與片語。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
    'u2-vocab': ('u2', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [22, 23, 24, 25, 26],
                 '學測重點單字與片語。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
    'u3-vocab': ('u3', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [],
                 '學測重點單字與片語（附音標）。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
    'u4-vocab': ('u4', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [],
                 '學測重點單字與片語（附音標）。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
}
# sections whose id prefix is not the unit id
UNIT_OF = {'tr-1': 'tr1', 'tr-2': 'tr2', 'tr-3': 'tr3', 'tr-4': 'tr4', 'tr-r1': 'trr1',
           'wr-1': 'wr1', 'wr-2': 'wr2', 'gs1-vocab': 'gs1',
           'gsat-08': 'w8', 'gsat-09': 'w9', 'gsat-10': 'w10',
           'cloze-41': 'cz41', 'cloze-42': 'cz42', 'cloze-43': 'cz43', 'cloze-44': 'cz44',
           'cloze-45': 'cz45', 'cloze-46': 'cz46', 'cloze-47': 'cz47', 'cloze-48': 'cz48',
           'cloze-49': 'cz49', 'cloze-50': 'cz50', 'cloze-51': 'cz51', 'cloze-52': 'cz52',
           'cloze-53': 'cz53', 'cloze-54': 'cz54'}

# Level 3–5 (imported from Vocaboo by tools/import_vocaboo.py): one section per workbook unit,
# material/l35-NN.txt, grouped ten units per sidebar group.
L35_UNITS = sorted(int(f[4:6]) for f in os.listdir(MAT) if f.startswith('l35-') and f.endswith('.txt'))
for g in range(0, max(L35_UNITS or [0]), 10):
    lo, hi = g + 1, min(g + 10, max(L35_UNITS))
    UNITS.append({'id': f'l35g{g // 10 + 1}', 'book': 'l35', 'kind': 'unit', 'title': f'Unit {lo}–{hi}', 'sub': '文意字彙・選擇題・配合題'})
for n in L35_UNITS:
    UNIT_OF[f'l35-{n:02d}'] = f'l35g{(n - 1) // 10 + 1}'
ORDER = ['u1-vocab', 'u1-drill', 'u1-cloze', 'u1-struct', 'u1-reading',
         'u2-vocab', 'u2-drill', 'u2-cloze', 'u2-struct', 'u2-reading',
         'u3-vocab', 'u3-drill', 'u3-cloze', 'u3-struct', 'u3-reading',
         'u4-vocab', 'u4-drill', 'u4-cloze', 'u4-struct', 'u4-reading', 'gs1-vocab',
         'tr-1', 'tr-2', 'tr-3', 'tr-4', 'tr-r1', 'wr-1', 'wr-2',
         'cloze-41', 'cloze-42', 'cloze-43', 'cloze-44',
         'cloze-45', 'cloze-46', 'cloze-47', 'cloze-48',
         'cloze-49', 'cloze-50', 'cloze-51', 'cloze-52',
         'cloze-53', 'cloze-54',
         'gsat-08', 'gsat-09', 'gsat-10']
FILES = {'u1-vocab': 'u1-words.txt', 'u1-drill': 'u1-drill.txt', 'u1-cloze': 'u1-cloze.txt',
         'u1-struct': 'u1-struct.txt', 'u1-reading': 'u1-reading.txt',
         'u2-vocab': 'u2-words.txt', 'u2-drill': 'u2-drill.txt', 'u2-cloze': 'u2-cloze.txt',
         'u2-struct': 'u2-struct.txt', 'u2-reading': 'u2-reading.txt',
         'u3-vocab': 'u3-words.txt', 'u3-drill': 'u3-drill.txt', 'u3-cloze': 'u3-cloze.txt',
         'u3-struct': 'u3-struct.txt', 'u3-reading': 'u3-reading.txt',
         'u4-vocab': 'u4-words.txt', 'u4-drill': 'u4-drill.txt', 'u4-cloze': 'u4-cloze.txt',
         'u4-struct': 'u4-struct.txt', 'u4-reading': 'u4-reading.txt', 'gs1-vocab': 'gs1-vocab.txt',
         'tr-1': 'trans-1.txt', 'tr-2': 'trans-2.txt', 'tr-3': 'trans-3.txt', 'tr-4': 'trans-4.txt',
         'tr-r1': 'trans-r1.txt', 'wr-1': 'write-1.txt', 'wr-2': 'write-2.txt',
         'cloze-41': 'cloze-41.txt', 'cloze-42': 'cloze-42.txt',
         'cloze-43': 'cloze-43.txt', 'cloze-44': 'cloze-44.txt',
         'cloze-45': 'cloze-45.txt', 'cloze-46': 'cloze-46.txt',
         'cloze-47': 'cloze-47.txt', 'cloze-48': 'cloze-48.txt',
         'cloze-49': 'cloze-49.txt', 'cloze-50': 'cloze-50.txt',
         'cloze-51': 'cloze-51.txt', 'cloze-52': 'cloze-52.txt',
         'cloze-53': 'cloze-53.txt', 'cloze-54': 'cloze-54.txt',
         'gsat-08': 'gsat-08.txt', 'gsat-09': 'gsat-09.txt', 'gsat-10': 'gsat-10.txt'}
ORDER += [f'l35-{n:02d}' for n in L35_UNITS]
FILES.update({f'l35-{n:02d}': f'l35-{n:02d}.txt' for n in L35_UNITS})

errors = []
def err(f, ln, msg):
    errors.append(f'{f}:{ln}: {msg}')

def parse_file(sid, fname):
    path = os.path.join(MAT, fname)
    lines = open(path, encoding='utf-8').read().split('\n')
    sec = {'id': sid, 'items': [], 'pages': [], 'overview': ''}
    if sid in VOCAB_META:
        u, t, e, r, p, o = VOCAB_META[sid]
        sec.update(unit=u, title=t, english=e, range=r, pages=p, overview=o)
    cur_page = None
    cur_entries = None
    entry = None
    bank = None
    passage = None
    q = None
    mode = None          # 'entries' | 'bank' | 'passage' | 'q'
    last_bank = None

    def close_q():
        nonlocal q
        if q:
            sec['items'].append(q)
            q = None

    def flush_entries():
        nonlocal cur_entries, entry
        if cur_entries is not None and cur_entries['list']:
            sec['items'].append(cur_entries)
        cur_entries = None
        entry = None

    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip()
        # ---- passage mode
        if mode == 'passage':
            if line == '@end':
                passage['paras'] = [p for p in passage['paras'] if p]
                sec['items'].append(passage)
                passage = None
                mode = None
            elif line == '':
                passage['paras'].append('')
            else:
                if passage['paras'] and passage['paras'][-1] != '':
                    passage['paras'][-1] += ' ' + line
                else:
                    if passage['paras'] and passage['paras'][-1] == '':
                        passage['paras'][-1] = line
                    else:
                        passage['paras'].append(line)
            continue
        # ---- Q block mode
        if mode == 'q':
            if line == '':
                close_q(); mode = None
                continue
            m = re.match(r'^([A-J]):\s?(.*)$', line)
            if line.startswith('  ') and q.get('stem') is not None and not m:
                q['stem'] += '\n' + line.strip()
            elif line.startswith('stem:'):
                q['stem'] = line[5:].strip()
            elif m:
                q['opts'].append(m.group(2).strip())
                if ord(m.group(1)) - 65 != len(q['opts']) - 1:
                    err(fname, ln, f'option letter {m.group(1)} out of order')
            elif line.startswith('= '):
                q['ans'] = line[2:].strip().replace(' ¶ ', '\n\n')
            elif line.startswith('~'):
                body = line[1:]
                derived = False
                if body.startswith('!'):
                    derived = True; body = body[1:]
                label = ''
                mm = re.match(r'^(\S+)\s+(.*)$', body) if not body.startswith(' ') else None
                if mm and not derived:
                    label, body = mm.group(1), mm.group(2)
                else:
                    body = body.strip()
                q['an'].append({'l': label, 't': body, **({'d': 1} if derived else {})})
            else:
                err(fname, ln, f'unrecognized line in Q block: {line[:40]}')
            continue
        # ---- bank mode
        if mode == 'bank':
            m = re.match(r'^([A-J]):\s?(.*)$', line)
            if m:
                bank['opts'].append(m.group(2).strip())
                continue
            sec['items'].append(bank); last_bank = bank; bank = None; mode = None
            if line == '':
                continue
        # ---- normal mode
        if line == '' or line.startswith('#'):
            continue
        if line.startswith('@section'):
            parts = [p.strip() for p in line[len('@section'):].split('|')]
            if parts[0] != sid:
                err(fname, ln, f'section id {parts[0]} != expected {sid}')
            if len(parts) >= 4:
                u = UNIT_OF.get(sid, sid.split('-')[0])
                sec.update(unit=u, title=parts[1], english=parts[2], range=parts[3])
            continue
        if line.startswith('@pages'):
            sec['pages'] = [int(x) for x in line[6:].split(',') if x.strip()]; continue
        if line.startswith('@overview'):
            sec['overview'] = line[9:].strip(); continue
        if line.startswith('@group'):
            flush_entries(); close_q()
            sec['items'].append({'t': 'group', 'title': line[6:].strip()})
            continue
        if line.startswith('@page'):
            flush_entries()
            cur_page = int(line[5:].strip())
            continue
        if line.startswith('@bank'):
            flush_entries()
            bank = {'t': 'bank', 'opts': []}; mode = 'bank'; continue
        if line.startswith('@passage'):
            flush_entries()
            passage = {'t': 'passage', 'paras': ['']}; mode = 'passage'; continue
        m = re.match(r'^Q\s+(\d+)\s*\|\s*(\w+)\s*\|\s*(.*)$', line)
        if m:
            flush_entries()
            q = {'t': 'q', 'n': int(m.group(1)), 'type': m.group(2), 'src': m.group(3).strip(),
                 'stem': None, 'opts': [], 'ans': None, 'an': []}
            if q['type'] == 'bank':
                if not last_bank:
                    err(fname, ln, 'bank question without @bank')
                else:
                    q['opts'] = list(last_bank['opts'])
            mode = 'q'
            continue
        # ---- entries
        if line.startswith('= '):
            if cur_entries is None:
                cur_entries = {'t': 'entries', 'page': cur_page, 'list': []}
            entry = {'w': line[2:].strip(), 's': [], 'p': [], 'n': [], 'e': [], 'b': []}
            cur_entries['list'].append(entry)
            continue
        if entry is None:
            err(fname, ln, f'line outside any block: {line[:40]}')
            continue
        if re.fullmatch(r'\[[^\[\]]+\]', line.strip()) and not entry.get('ph'):
            entry['ph'] = line.strip()[1:-1]
            continue
        if line.startswith('> '):
            body = line[2:].strip()
            mm = re.split(r'\s{2,}', body, maxsplit=1)
            entry['p'].append([mm[0], mm[1] if len(mm) > 1 else ''])
        elif line.startswith('+例'):
            body = line[2:].strip()
            en, _, zh = body.partition(' | ')
            entry['e'].append([en.strip(), zh.strip()])
        elif line.startswith('+'):
            mm = re.match(r'^\+(\S+)\s+(.*)$', line)
            if not mm:
                err(fname, ln, 'bad note line')
            else:
                entry['n'].append([mm.group(1), mm.group(2).strip()])
        elif line.startswith('* '):
            parts = [x.strip() for x in line[2:].split(' | ')]
            if len(parts) != 3:
                err(fname, ln, 'boxed sentence needs 3 fields')
            else:
                entry['b'].append(parts)
        else:
            entry['s'].append(line.strip())
    if mode == 'q' and q: close_q()
    if mode == 'bank' and bank: sec['items'].append(bank)
    flush_entries(); close_q()
    if mode == 'passage':
        err(fname, len(lines), 'unterminated @passage')
    return sec

def validate(sec):
    f = sec['id']
    qs = [i for i in sec['items'] if i['t'] == 'q']
    nums = [q['n'] for q in qs]
    if len(set(nums)) != len(nums):
        err(f, 0, 'duplicate question numbers')
    for q in qs:
        where = f'{f} Q{q["n"]}'
        if q['stem'] is None: err(where, 0, 'no stem')
        if q['ans'] is None and q['type'] != 'write': err(where, 0, 'no answer'); continue
        t = q['type']
        if t in ('choice', 'bank'):
            if not re.fullmatch(r'[A-J]', q['ans']) or ord(q['ans']) - 65 >= len(q['opts']):
                err(where, 0, f'bad answer {q["ans"]!r}')
        elif t == 'multi':
            if not re.fullmatch(r'[A-J]{2,}', q['ans']) or any(ord(c) - 65 >= len(q['opts']) for c in q['ans']):
                err(where, 0, f'bad multi answer {q["ans"]!r}')
        elif t == 'fill':
            if q['opts']: err(where, 0, 'fill with options')
        elif t in ('trans', 'write'):
            if q['opts']: err(where, 0, f'{t} with options')
        else:
            err(where, 0, f'unknown type {t}')
        if t == 'choice' and len(q['opts']) < 2: err(where, 0, 'choice needs options')
        if not q['an']: err(where, 0, 'no analysis')
    for it in sec['items']:
        if it['t'] == 'passage':
            for p in it['paras']:
                for n in re.findall(r'\[\[(\d+)\]\]', p):
                    if int(n) not in nums:
                        err(f, 0, f'passage blank [[{n}]] has no question')
        if it['t'] == 'entries':
            for e in it['list']:
                if not (e['s'] or e['p'] or e['n'] or e['e']):
                    err(f, 0, f'entry {e["w"]!r} has no content')
    for q in qs:
        m = re.match(r'^(?:類題|試題演練) (\d+)', q['src'])
        q['show'] = int(m.group(1)) if m else q['n']
    # every blank question inside a passage must be referenced (informational)

def collect_text(sections):
    out = []
    for s in sections:
        for it in s['items']:
            if it['t'] == 'passage': out += it['paras']
            elif it['t'] == 'bank': out += it['opts']
            elif it['t'] == 'q':
                out += [it['stem']] + it['opts'] + [a['t'] for a in it['an'] if a['l'] in ('', '原文', '文意', '替換', '補充', '詞義') ]
                out.append(it['ans'] if it['type'] in ('fill', 'trans', 'write') and it['ans'] else '')
            elif it['t'] == 'entries':
                for e in it['list']:
                    out.append(e['w'])
                    out += [p[0] for p in e['p']] + [x[0] for x in e['e']] + [b[1] for b in e['b']]
                    out += [n[1] for n in e['n']]
    return out

TOKEN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")

CONTEXT = {
    'vaaler': '人名：Johan Vaaler（約翰・瓦勒），挪威發明家，與迴紋針的發明有關',
    'gem': '公司名：Gem Manufacturing Ltd.（英國），生產雙迴圈迴紋針；此處的 Gem clip 指該款迴紋針',
    'oslo': '地名：奧斯陸（挪威首都）', 'norway': '地名：挪威', 'norwegian': 'a. 挪威的；n. 挪威人',
    'norwegians': 'n. 挪威人（複數）', 'nazis': 'n. 納粹黨人', 'mozart': '人名：莫札特（作曲家）',
    'beethoven': '人名：貝多芬（作曲家）', 'franklin': '人名：富蘭克林（Benjamin Franklin，美國開國元勳）',
    'armonica': 'n. 玻璃琴（富蘭克林發明的樂器）', 'assam': '地名：阿薩姆邦（印度）',
    'chatgpt': '專有名詞：ChatGPT（OpenAI 的對話式 AI）', 'doc': '人名：Doc（動畫《Doc McStuffins》的女主角）',
    'mcstuffins': '人名：McStuffins（動畫《Doc McStuffins》的姓氏）', 'nee': '人名：Chris Nee（《Doc McStuffins》的創作者）',
    'mariana': '地名：馬里亞納（海溝）', 'pcbs': '縮寫：PCBs 多氯聯苯（一種持久性有機汙染物）',
    'pbdes': '縮寫：PBDEs 多溴二苯醚（一種持久性有機汙染物）', 'pops': '縮寫：POPs 持久性有機汙染物',
    'pcb': '縮寫：PCB 多氯聯苯', 'who': '縮寫：WHO 世界衛生組織', 'mri': '縮寫：MRI 磁振造影', 'pet': 'n. 寵物；此處 PET scans 指正子斷層掃描',
    'ac': '縮寫：AC 交流電', 'dc': '縮寫：DC 直流電', 'glamping': 'n. 豪華露營（glamorous + camping）', 'yurts': 'n. 蒙古包（yurt 的複數）',
    'nt': '縮寫：NT$ 新臺幣',
    'jade': '地名：玉山（Mt. Jade / Jade Mountain，臺灣最高峰）', 'gary': '人名：Gary（蓋瑞）',
    'jessica': '人名：Jessica（潔西卡）', 'amy': '人名：Amy（艾咪）', 'mark': '人名：Mark（馬克）',
    'tom': '人名：Tom（湯姆）', 'david': '人名：David（大衛）',
    'taitung': '地名：臺東', 'wangs': '人名：the Wangs 王家（一家人）',
    'scammers': 'n. 詐騙者（scammer 的複數）', 'propagandas': 'n. 宣傳（propaganda 的複數）',
    'kemball': '人名：Laurence Kemball-Cook，Pavegen 發電地磚的發明人', 'pavegen': '專有名詞：Pavegen（踩踏發電地磚品牌）',
    'fosen': '地名：Fosen Vind（挪威大型風力發電複合案場）', 'geitfjellet': '地名：Geitfjellet（挪威風力發電場之一）',
    'hitra': '地名：Hitra（挪威島嶼，風力發電場所在地）', 'snillfjord': '地名：Snillfjord（挪威島嶼，風力發電場所在地）',
    'gosun': '專有名詞：GoSun（太陽能燒烤爐品牌）', 'bloom': '專有名詞：Bloom Energy Corporation（燃料電池公司）',
    'saccharomyces': '生物學名：Saccharomyces cerevisiae 釀酒酵母菌', 'cerevisiae': '生物學名：Saccharomyces cerevisiae 釀酒酵母菌',
    'electrocytes': 'n. 發電細胞（electrocyte 的複數，電魚體內產生電流的特化細胞）',
    'elephantnose': '專有名詞：elephantnose fish 象鼻魚（一種能發電的非洲淡水魚）',
    'asimov': '人名：Isaac Asimov（以撒・艾西莫夫，科幻小說家）', 'kaohsiung': '地名：高雄',
    'melbourne': '地名：墨爾本（澳洲城市）',
    'nguyen': '人名：Dong Nguyen（阮東，Flappy Bird 的開發者，越南人）', 'hanoi': '地名：河內（越南首都）',
    'faby': '專有名詞：Faby（Flappy Bird 遊戲中小鳥角色的暱稱）',
    'jr': '縮寫：JR（Japan Railways，日本鐵路公司，如 JR Tokai、JR East）',
    'siemens': '專有名詞：Siemens（西門子，德國跨國科技公司）', 'hamburg': '地名：漢堡（德國城市）',
    'fuxing': '專有名詞：復興號（Fuxing，中國大陸高速列車型號）', 'beijing': '地名：北京',
    'carrier': '人名：Willis Carrier（威利斯・開利，現代冷氣機發明人）',
    'ifetch': '專有名詞：iFetch（自動拋球遛狗裝置品牌）',
    'neo': '人名：Neo（電影《駭客任務》男主角）',
    'matrix': '專有名詞：The Matrix（電影《駭客任務》）',
    # Grand Slam Unit 3–4
    'camino': '專有名詞：Camino de Santiago 聖雅各之路（西班牙朝聖路線）；camino 為西班牙語「道路」',
    'frances': '專有名詞：Camino Frances 法國之路（聖雅各之路最熱門的路線）',
    'portugues': '專有名詞：Camino Portugues 葡萄牙之路（聖雅各之路的路線之一）',
    'santiago': '地名：Santiago（de Compostela）聖地牙哥－德孔波斯特拉（西班牙朝聖地）；Santiago 也指聖雅各',
    'ka': '專有名詞：Ka Mate（毛利戰舞哈卡的一種）', 'mate': '專有名詞：Ka Mate（毛利戰舞哈卡的一種）；一般字義 n. 夥伴；配偶',
    'kapa': '專有名詞：Kapa o Pango（2005 年為紐西蘭全黑隊創作的哈卡戰舞）',
    'pango': '專有名詞：Kapa o Pango（2005 年為紐西蘭全黑隊創作的哈卡戰舞）',
    'louis': '人名：Louis XIV 路易十四（法國國王）', 'sorbet': 'n. 雪酪（以果汁、糖和水冰凍而成，不含乳製品的冰品）',
    'maniq': '專有名詞：Maniq 馬尼克人（泰國南部的狩獵採集族群）',
    'jahai': '專有名詞：Jahai 賈海語（馬來半島狩獵採集族群使用的語言）',
    'aminobutyric': '化學名：gamma-aminobutyric acid（GABA）γ-胺基丁酸，一種抑制性神經傳導物質',
    'popole': '人名：Popole Misenga（剛果出身的柔道選手，代表難民奧運代表隊參賽）',
    'misenga': '人名：Popole Misenga（剛果出身的柔道選手，代表難民奧運代表隊參賽）',
    'tsmc': '專有名詞：TSMC 台積電（台灣積體電路製造公司）',
    'hon': '專有名詞：Hon Hai 鴻海（鴻海精密工業）', 'hai': '專有名詞：Hon Hai 鴻海（鴻海精密工業）',
    'superfood': 'n. 超級食物（被認為營養價值特別高的食物）', 'superfoods': 'n. 超級食物（superfood 的複數）',
    'desalinating': 'v. 將（海水）淡化、去除鹽分（desalinate 的 -ing 形）',
    'unresearched': 'a. 尚未被研究的',
    # Beat the GSAT Unit 8–10
    'curcumin': 'n. 薑黃素（薑黃中的主要活性成分）', 'jayanti': '印度語：jayanti，意為「戰勝疾病者」（古印度對薑黃的稱呼）',
    'schengen': '專有名詞：Schengen Agreement 申根協定（歐洲多國互免邊境檢查）',
    'acropolis': '地名：Acropolis 雅典衛城（希臘）', 'colosseum': '地名：Colosseum 羅馬競技場（義大利）',
    'narayana': '人名：Narayana Peesapaty（印度發明家，可食用餐具 Bakey\'s 創辦人）',
    'peesapaty': '人名：Narayana Peesapaty（印度發明家，可食用餐具 Bakey\'s 創辦人）',
    'bakey': '專有名詞：Bakey\'s（印度可食用餐具公司）', "bakey's": '專有名詞：Bakey\'s（印度可食用餐具公司）',
    'hayao': '人名：Hayao Miyazaki 宮崎駿（日本動畫導演）', 'miyazaki': '人名：Hayao Miyazaki 宮崎駿（日本動畫導演）',
    "miyazaki's": '人名：宮崎駿的', 'sen': '人名：Sen 千（《神隱少女》女主角千尋）',
    'yubaba': '人名：Yubaba 湯婆婆（《神隱少女》中的魔女）', 'jiufen': '地名：九份（新北市的老金礦小鎮）',
    'dogo': '地名：Dogo Onsen 道後溫泉（日本愛媛縣）', 'onsen': '日語：onsen 溫泉',
    'cyberbully': 'n. 網路霸凌者；v. 網路霸凌', 'cyberbullies': 'n. 網路霸凌者（cyberbully 的複數）',
    'boysdancetoo': '主題標籤：#boysdancetoo（男生也跳舞）',
    'theta': 'n. 希臘字母 θ；Theta rhythm θ 腦波（冥想、放鬆時出現）',
    # Cloze Power-Up Unit 49–52「Plants」
    'trysdale': '人名：Trysdale（O. Henry 短篇小說中的男主角）',
    'ventomarme': '西班牙語：Ventomarme，意為「來帶我走」（O. Henry 短篇小說中仙人掌上的學名雙關）',
    'subterranea': '生物學名：Pinanga subterranea（婆羅洲發現的地下開花結果棕櫚）',
    'pinanga': '生物學名：Pinanga subterranea（婆羅洲發現的地下開花結果棕櫚）',
    'borneo': '地名：婆羅洲（東南亞島嶼）',
    'chinchon': '人名：Countess of Chinchón 欽瓊伯爵夫人（傳說中奎寧樹命名由來的西班牙貴族）',
    'cinchona': '專有名詞：cinchona 金雞納樹（樹皮可提煉奎寧，用於治療瘧疾）',
    'quinine': 'n. 奎寧（治療瘧疾的藥物，提煉自金雞納樹皮）',
    'quina': '西班牙語：quina，金雞納樹的別名',
    'ecuador': '地名：厄瓜多（南美洲國家）',
    'jalapa': '生物學名：Mirabilis jalapa 紫茉莉（又稱「四點鐘花」）',
    'mirabilis': '生物學名：Mirabilis jalapa 紫茉莉（又稱「四點鐘花」）',
    'cuscuta': '生物學名：Cuscuta 菟絲子屬（俗稱「女巫的頭髮」的寄生植物）',
    'guyana': '地名：蓋亞那（南美洲國家，國徽圖案含王蓮）',
    'amazonica': '生物學名：Victoria amazonica 亞馬遜王蓮（以英國維多利亞女王命名）',
    'caimans': 'n. 凱門鱷（caiman 的複數，南美洲的鱷魚近親）',
    'yamaki': '人名／專有名詞：the Yamaki pine，山木家族栽培並捐贈給美國國家植物園的著名日本五葉松盆栽',
    'hiroshima': '地名：廣島（日本城市，二戰原子彈轟炸地點）',
    'arboretum': 'n. 植物園（尤指以樹木收藏為主的植物園，如 U.S. National Arboretum）',
    # Cloze Power-Up Unit 53–54「Society」
    'kacey': '人名：Kacey Wong 黃國才（香港藝術家，以可變形街頭雕塑聞名）',
    'wong': '人名：Kacey Wong 黃國才（香港藝術家，以可變形街頭雕塑聞名）',
    'polygyny': 'n. 一夫多妻制', 'polyandry': 'n. 一妻多夫制',
    'neubauer': '人名：Luisa Neubauer（德國漢堡出身的年輕氣候運動人士）',
    'luisa': '人名：Luisa Neubauer（德國漢堡出身的年輕氣候運動人士）',
    'strongminds': '專有名詞：StrongMinds（總部位於美國紐澤西、於尚比亞與烏干達提供憂鬱症治療的慈善組織）',
    'zambia': '地名：尚比亞（非洲南部國家）', 'uganda': '地名：烏干達（非洲東部國家）',
    'utopia': '專有名詞：Utopia《烏托邦》（Thomas More 於 1516 年所著，描述理想社會的著作；亦指書中虛構的島嶼）',
    'xenophobia': 'n. 仇外心理、排外情結', 'xenophobic': 'a. 仇外的、排外的',
    'ageism': 'n. 年齡歧視',
}

def build_dictionary(sections, ecdict_path):
    book = {}   # lemma -> list of sense strings
    for s in sections:
        for it in s['items']:
            if it['t'] != 'entries': continue
            for e in it['list']:
                w = e['w'].strip().lower()
                if not re.fullmatch(r"[a-z]+", w) or not e['s']:
                    continue
                gloss = ' ｜ '.join(e['s'])
                book.setdefault(w, [])
                if gloss not in book[w]:
                    book[w].append(gloss)
    tokens = set()
    for txt in collect_text(sections):
        for m in TOKEN.findall(txt or ''):
            t = m.lower().replace('’', "'")
            tokens.add(t)
            if t.endswith("'s"): tokens.add(t[:-2])
    tokens.discard('')
    # --- ECDICT
    from opencc import OpenCC
    cc = OpenCC('s2tw')
    csv.field_size_limit(10 ** 9)
    ec = {}
    need = set(tokens) | set(book)
    if not os.path.exists(ecdict_path):
        print('WARNING: ECDICT csv not found; dictionary = book glosses only')
    else:
      with open(ecdict_path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            w = row['word'].lower()
            if w in need:
                ec[w] = row
    # lemma follow-ups
    lem_need = set()
    for t, row in ec.items():
        m = re.search(r'(?:^|/)0:([^/]+)', row['exchange'] or '')
        if m: lem_need.add(m.group(1).lower())
    lem_need -= set(ec)
    if lem_need:
        with open(ecdict_path, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                w = row['word'].lower()
                if w in lem_need: ec[w] = row

    def fmt(row):
        tr = (row['translation'] or '').replace('\\n', '\n')
        lines = [cc.convert(x.strip()) for x in tr.split('\n') if x.strip()]
        txt = '；'.join(lines[:4])
        if len(txt) > 95:
            cut = txt[:95]
            k = max(cut.rfind(','), cut.rfind('；'), cut.rfind('、'))
            txt = cut[:k] if k > 40 else cut
        return txt

    dic = {}
    miss = []
    for t in sorted(tokens | set(book)):
        row = ec.get(t)
        phon = (row['phonetic'] if row else '') or ''
        lemma = None
        if row:
            m = re.search(r'(?:^|/)0:([^/]+)', row['exchange'] or '')
            if m: lemma = m.group(1).lower()
        if t in book:
            dic[t] = {'meaning': ' ｜ '.join(book[t]), 'phonetic': phon, 'book': 1}
        elif lemma and lemma in book:
            dic[t] = {'meaning': f'{lemma} 的變化形　' + ' ｜ '.join(book[lemma]), 'phonetic': phon, 'book': 1}
        elif t in CONTEXT:
            dic[t] = {'meaning': CONTEXT[t], 'phonetic': ''}
        elif row and (row['translation'] or '').strip():
            dic[t] = {'meaning': fmt(row), 'phonetic': phon}
        elif lemma and lemma in ec and (ec[lemma]['translation'] or '').strip():
            dic[t] = {'meaning': f'{lemma} 的變化形　' + fmt(ec[lemma]), 'phonetic': phon}
        else:
            miss.append(t)
    return dic, miss

def main():
    secs = []
    for sid in ORDER:
        sec = parse_file(sid, FILES[sid])
        validate(sec)
        secs.append(sec)
    if errors:
        print('\n'.join(errors)); print(f'{len(errors)} error(s)'); sys.exit(1)
    exam = {'title': 'Workbook 隨身讀', 'books': BOOKS, 'units': UNITS, 'sections': secs,
            'notice': '本 app 依書本掃描整理：書中印有解析的題目照抄書上的解析；書中沒有解答的題目，答案與解析由 Claude 推導（標示「推導」），請老師審閱後再給學生使用。原書權利屬原權利人。'}
    with open(os.path.join(ROOT, 'data.js'), 'w', encoding='utf-8') as f:
        f.write('window.EXAM=' + json.dumps(exam, ensure_ascii=False, separators=(',', ':')) + ';\n')
    ecp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', 'work', 'ecdict', 'ecdict.csv')
    if not os.path.exists(ecp) and os.path.exists(os.path.join(ROOT, 'dictionary.js')):
        # don't overwrite the full ECDICT dictionary with a book-glosses-only one
        print('ECDICT csv not found: data.js rebuilt, dictionary.js left unchanged')
        dic, miss = {}, []
    else:
        dic, miss = build_dictionary(secs, ecp)
        with open(os.path.join(ROOT, 'dictionary.js'), 'w', encoding='utf-8') as f:
            f.write('window.DICTIONARY=' + json.dumps(dic, ensure_ascii=False, separators=(',', ':')) + ';\n')
    nq = sum(1 for s in secs for i in s['items'] if i['t'] == 'q')
    ne = sum(len(i['list']) for s in secs for i in s['items'] if i['t'] == 'entries')
    nd = sum(1 for s in secs for i in s['items'] if i['t'] == 'q' for a in i['an'] if a.get('d'))
    print(f'sections={len(secs)} questions={nq} word-entries={ne} derived-analyses={nd} dict={len(dic)} no-gloss={len(miss)}')
    if miss: print('no gloss for:', ' '.join(miss[:80]))

if __name__ == '__main__':
    main()
