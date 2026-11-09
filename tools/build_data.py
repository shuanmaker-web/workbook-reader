#!/usr/bin/env python3
"""Build data.js + dictionary.js for the Workbook reader from tools/../material/*.txt

Usage:  python3 tools/build_data.py [path/to/ecdict.csv]
  - data.js        window.EXAM   (sections, word entries, passages, questions, analyses)
  - dictionary.js  window.DICTIONARY (tap-to-define: workbook glosses first, then ECDICT, converted to Traditional)

Material grammar (see material/*.txt headers):
  @section id | 標題 | English | range      @pages 6,7     @overview text
  @group title            starts a group (word entries / passages / questions follow)
  @page n                 source page of the following word entries
  = word                  start a word entry (outside Q blocks); plain lines = senses
  > phrase  中文          phrase line (two spaces between phrase and 中文)
  +同義 / +反義 / +諺語 text   note;  +例 English | 中文   example
  * 96指考 | English | 中文   boxed exam sentence
  @bank  ... "A: text" lines until a blank line     (answer bank for 'bank' questions)
  @passage ... @end         paragraphs separated by blank lines; [[n]] = blank of question n
  Q n | type | src          type: choice | multi | bank | fill | trans
    stem: ...   (continuation lines start with two spaces)   A: ... J: ...
    = answer                 (fill: alternatives separated by " | "; trans: one reference translation, shown on reveal, not auto-graded)
    ~ text / ~label text / ~! text (derived by Claude)       analysis lines
    (trans uses ~替換 word: alt1 / alt2 for the book's 替換詞 lists)
"""
import csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, 'material')

UNITS = [
    {'id': 'u1', 'title': 'Unit 1', 'sub': '單字、片語・綜合測驗・篇章結構・閱讀測驗'},
    {'id': 'u2', 'title': 'Unit 2', 'sub': '單字、片語・文意選填・篇章結構・閱讀測驗'},
    {'id': 'u3', 'title': 'Unit 3', 'sub': '開頭：單字表'},
    {'id': 'tr', 'title': '翻譯', 'sub': '翻譯（一）表目的句法・翻譯（二）以動詞開頭'},
]
# section id -> (unit, title, english, range, pages, overview) for sections whose file has no full @section header
VOCAB_META = {
    'u1-vocab': ('u1', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [6, 7, 8, 9, 10],
                 '學測重點單字與片語。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
    'u2-vocab': ('u2', '單字、片語', 'Key words & phrases', 'A 單字 · B 片語', [22, 23, 24, 25, 26],
                 '學測重點單字與片語。點單字旁的 ☆ 可收進「我的單字」；點例句裡的任何英文字可查詞義。'),
    'u3-vocab': ('u3', '單字、片語（開頭）', 'Key words (opening page)', 'A 單字', [35],
                 'Unit 3 目前只有開頭一頁的單字表，其餘內容之後再補。'),
}
# sections whose id prefix is not the unit id
UNIT_OF = {'tr-1': 'tr', 'tr-2': 'tr'}
ORDER = ['u1-vocab', 'u1-drill', 'u1-cloze', 'u1-struct', 'u1-reading',
         'u2-vocab', 'u2-drill', 'u2-cloze', 'u2-struct', 'u2-reading', 'u3-vocab',
         'tr-1', 'tr-2']
FILES = {'u1-vocab': 'u1-words.txt', 'u1-drill': 'u1-drill.txt', 'u1-cloze': 'u1-cloze.txt',
         'u1-struct': 'u1-struct.txt', 'u1-reading': 'u1-reading.txt',
         'u2-vocab': 'u2-words.txt', 'u2-drill': 'u2-drill.txt', 'u2-cloze': 'u2-cloze.txt',
         'u2-struct': 'u2-struct.txt', 'u2-reading': 'u2-reading.txt', 'u3-vocab': 'u3-words.txt',
         'tr-1': 'trans-1.txt', 'tr-2': 'trans-2.txt'}

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
                q['ans'] = line[2:].strip()
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
        if q['ans'] is None: err(where, 0, 'no answer'); continue
        t = q['type']
        if t in ('choice', 'bank'):
            if not re.fullmatch(r'[A-J]', q['ans']) or ord(q['ans']) - 65 >= len(q['opts']):
                err(where, 0, f'bad answer {q["ans"]!r}')
        elif t == 'multi':
            if not re.fullmatch(r'[A-J]{2,}', q['ans']) or any(ord(c) - 65 >= len(q['opts']) for c in q['ans']):
                err(where, 0, f'bad multi answer {q["ans"]!r}')
        elif t == 'fill':
            if q['opts']: err(where, 0, 'fill with options')
        elif t == 'trans':
            if q['opts']: err(where, 0, 'trans with options')
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
                out += [it['stem']] + it['opts'] + [a['t'] for a in it['an'] if a['l'] in ('', '原文', '文意', '替換', '補充') ]
                out.append(it['ans'] if it['type'] in ('fill', 'trans') else '')
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
    exam = {'title': 'Workbook 隨身讀', 'units': UNITS, 'sections': secs,
            'notice': '本 app 依書本掃描整理：書中印有解析的題目照抄書上的解析；書中沒有解答的題目，答案與解析由 Claude 推導（標示「推導」），請老師審閱後再給學生使用。原書權利屬原權利人。'}
    with open(os.path.join(ROOT, 'data.js'), 'w', encoding='utf-8') as f:
        f.write('window.EXAM=' + json.dumps(exam, ensure_ascii=False, separators=(',', ':')) + ';\n')
    ecp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '..', 'work', 'ecdict', 'ecdict.csv')
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
