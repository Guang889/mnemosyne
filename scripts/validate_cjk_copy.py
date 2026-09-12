#!/usr/bin/env python3
"""Run the actual candidate init on an exclusive copy; never open source writable.

Run from the candidate checkout with PYTHONPATH=. and a verified embedding dim.
This validates migration and SQL writes, not the external embedding service.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from mnemosyne.core.beam import _BeamConnection, _cjk_bigram, init_beam, _get_connection


def content_digest(conn):
    result = {}
    for table in ("working_memory", "episodic_memory"):
        rows = conn.execute(f"SELECT id, content FROM {table} ORDER BY id").fetchall()
        result[table] = (len(rows), hashlib.sha256(json.dumps([tuple(r) for r in rows], ensure_ascii=False).encode()).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve()
    if source == destination:
        parser.error("source and destination must differ")
    # Exclusive creation prevents overwriting any existing backup or runtime DB.
    with destination.open("xb"):
        pass
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            before = content_digest(dst)
    try:
        init_beam(destination)
        conn = _get_connection(destination)
        assert content_digest(conn) == before
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT version FROM cjk_fts_schema").fetchone()[0] == 1
        # Every historical CJK record must match its own token, not another row.
        checked = {}
        for table, fts, key in (("working_memory", "fts_working", "id"), ("episodic_memory", "fts_episodes", "rowid")):
            checked[table] = 0
            for ident, content in conn.execute(f"SELECT {key}, content FROM {table}"):
                tokens = [t for t in _cjk_bigram(content or '').split() if len(t) == 2 and all('\u3400' <= c <= '\u4dbf' or '\u4e00' <= c <= '\u9fff' for c in t)]
                if tokens:
                    assert conn.execute(f"SELECT 1 FROM {fts} WHERE {key}=? AND {fts} MATCH ?", (ident, '"' + tokens[0] + '"')).fetchone()
                    checked[table] += 1
        print("historical_cjk_records_checked", checked)
        sql_before = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall()
        init_beam(destination)
        assert content_digest(conn) == before
        assert conn.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall() == sql_before
        with closing(sqlite3.connect(destination, factory=_BeamConnection)) as writer:
            writer.execute("BEGIN")
            try:
                for table, fts, key in (("working_memory", "fts_working", "id"), ("episodic_memory", "fts_episodes", "rowid")):
                    import uuid
                    test_id = 'cjk-copy-' + uuid.uuid4().hex
                    writer.execute(f"INSERT INTO {table}(id,content) VALUES(?,?)", (test_id, "独立熊猫 Привет café"))
                    ident = writer.execute(f"SELECT {key} FROM {table} WHERE id=?", (test_id,)).fetchone()[0]
                    def match(word):
                        return writer.execute(f"SELECT 1 FROM {fts} WHERE {key}=? AND {fts} MATCH ?", (ident, '"' + word + '"')).fetchone()
                    assert match('熊猫')
                    writer.execute(f"UPDATE {table} SET content=? WHERE id=?", ("验证海豚", test_id))
                    assert not match('熊猫')
                    assert match('海豚')
                    writer.execute(f"DELETE FROM {table} WHERE id=?", (test_id,))
                    assert not match('海豚')
                    writer.execute(f"INSERT INTO {fts}({fts}) VALUES ('integrity-check')")
            finally:
                writer.rollback()
        assert content_digest(conn) == before
        for fts in ("fts_working", "fts_episodes"):
            conn.execute(f"INSERT INTO {fts}({fts}) VALUES ('integrity-check')")
        conn.commit()
        print(json.dumps({"result": "PASS", "copy": str(destination), "source_content": before}, ensure_ascii=False))
    finally:
        _get_connection(destination).close()


if __name__ == "__main__":
    main()
