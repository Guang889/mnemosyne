import sqlite3, sys
sys.path.insert(0, '.')
from mnemosyne.core.beam import _cjk_bigram

# --- 1. bigram 函数 ---
cases = [
    ('腾讯云VPS',    '腾 腾讯 讯 讯云 云 VPS'),
    ('然然',         '然 然然 然'),
    ('Docker容器',   'Docker 容 容器 器'),
    ('5美元',        '5 美 美元 元'),
    ('English',      'English'),
    ('中English混',  '中 English 混'),
]
for inp, exp in cases:
    got = _cjk_bigram(inp)
    assert got == exp, f'FAIL {inp!r}: got {got!r}, want {exp!r}'
print('bigram 函数 6/6 通过')

# --- 2. FTS 端到端 ---
conn = sqlite3.connect(':memory:')
conn.create_function('cjk_bigram', 1, _cjk_bigram)
conn.execute('CREATE VIRTUAL TABLE fts USING fts5(content)')

memories = [
    '腾讯云VPS部署了Docker',
    'Honcho费用约5美元',
    '然然是AI助手',
    'config.yaml的custom_providers必须是list格式',
]
for m in memories:
    conn.execute('INSERT INTO fts(content) VALUES(?)', (_cjk_bigram(m),))

def search(q):
    bigram_q = ' OR '.join(_cjk_bigram(q).split())
    return conn.execute(
        'SELECT content FROM fts WHERE fts MATCH ?', (bigram_q,)
    ).fetchall()

queries = ['腾讯云', 'Docker', '然然', '5美元', 'config', 'list格式']
for q in queries:
    rows = search(q)
    assert rows, f'FAIL: {q!r} 未命中'
    print(f'  {q!r} -> {len(rows)} 条')
print('FTS 端到端 6/6 通过')
