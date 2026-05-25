# P4：提交上游 PR

**进入条件**：P3 完成（至少 2 周实测数据）
**完成标准**：PR 已提交，切换回上游版本

---

## GitHub Issue 更新

在已有 Issue 中补充：

- P2 验证截图（FTS 直查结果 + embedding dim 输出）
- P3 量化数据（命中率修改前后对比、主观感受变化）

---

## PR 描述模板

```
## Problem

FTS5 defaults to the `unicode61` tokenizer, which splits on whitespace only.
CJK text has no spaces, so entire sentences are indexed as single tokens.
Any sub-word query against Chinese content returns 0 results.

Repro: SELECT * FROM fts_episodes WHERE fts_episodes MATCH '腾讯云' → 0 rows

## Solution

Bigram pre-processing (zero new dependencies):
- `_cjk_bigram()`: CJK chars → unigram + bigram tokens; Latin/digits kept as-is
- Registered as SQLite UDF `cjk_bigram` in `_get_connection()`
- Applied on write side (FTS triggers) and read side (_fts_search, _fts_search_working)
- em_ad delete trigger also updated to use cjk_bigram(old.content) to correctly clean index entries

Also adds configurable embedding endpoint support to embeddings.py:
- MNEMOSYNE_EMBEDDING_BASE_URL (embedding-specific, avoids polluting OPENROUTER_BASE_URL)
- DASHSCOPE_API_KEY in key fallback chain
- text-embedding-v4 added to _get_embedding_dim with 1024 dim

## Test Results

[从 P3 数据填入]
- 中文关键词 FTS 命中率：0% → XX%
- 使用周期：X 周

## Files changed

- mnemosyne/core/beam.py: ~50 lines (bigram tokenizer + trigger + query-side)
- mnemosyne/core/embeddings.py: ~6 lines (env var + dim table)
```

---

## 合并后操作

```bash
# 切换回上游官方版本
docker exec -u hermes hermes \
  /opt/hermes/.venv/bin/pip install mnemosyne
docker restart hermes
```

移除 VPS 上的 `mnemosyne-src` 目录（可选）。
