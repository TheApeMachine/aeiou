from __future__ import annotations

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np


class MemoryStore:
    """Embedded SQLite stores for relational, vector, and graph data"""

    def __init__(self, db_path: str = "aeiou_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY,
                    ts INTEGER,
                    project TEXT,
                    spec TEXT,
                    ttl INTEGER DEFAULT 2592000,  -- 30 days
                    pinned BOOLEAN DEFAULT 0,
                    created_at REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY,
                    decision_id INTEGER,
                    action_type TEXT,
                    data TEXT,
                    result TEXT,
                    success BOOLEAN,
                    created_at REAL,
                    FOREIGN KEY (decision_id) REFERENCES decisions(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY,
                    item_id TEXT,
                    kind TEXT,
                    dim INTEGER,
                    vec BLOB,
                    meta TEXT,
                    ttl INTEGER DEFAULT 2592000,
                    created_at REAL,
                    UNIQUE(item_id, kind)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    kind TEXT,
                    uri TEXT,
                    meta TEXT,
                    ttl INTEGER DEFAULT 2592000,
                    created_at REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY,
                    src TEXT,
                    dst TEXT,
                    rel TEXT,
                    meta TEXT,
                    ttl INTEGER DEFAULT 2592000,
                    created_at REAL,
                    FOREIGN KEY (src) REFERENCES nodes(id),
                    FOREIGN KEY (dst) REFERENCES nodes(id)
                )
            """)

            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_kind ON embeddings(kind)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_src_rel ON edges(src, rel)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_dst_rel ON edges(dst, rel)")

    # Relational operations
    def store_decision(self, project: str, spec: Dict[str, Any], ttl_seconds: int = 2592000) -> int:
        """Store a decision in the relational store"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO decisions (ts, project, spec, ttl, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                int(time.time()),
                project,
                json.dumps(spec),
                ttl_seconds,
                time.time()
            ))
            return cursor.lastrowid

    def get_decisions(self, project: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent decisions for a project"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, ts, spec, pinned FROM decisions
                WHERE project = ? AND (pinned = 1 OR ts > ?)
                ORDER BY ts DESC LIMIT ?
            """, (project, time.time() - 2592000, limit)).fetchall()

            return [{
                'id': row[0],
                'timestamp': row[1],
                'spec': json.loads(row[2]),
                'pinned': bool(row[3])
            } for row in rows]

    def pin_decision(self, decision_id: int):
        """Pin a decision to prevent TTL expiration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE decisions SET pinned = 1 WHERE id = ?", (decision_id,))

    def forget_decision(self, decision_id: int):
        """Mark a decision for redaction (soft delete)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE decisions SET ttl = 0 WHERE id = ?", (decision_id,))

    # Vector operations
    def store_embedding(self, item_id: str, kind: str, vector: List[float], meta: Dict[str, Any] = None, ttl_seconds: int = 2592000):
        """Store a vector embedding"""
        vec_bytes = np.array(vector, dtype=np.float32).tobytes()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings (item_id, kind, dim, vec, meta, ttl, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                kind,
                len(vector),
                vec_bytes,
                json.dumps(meta or {}),
                ttl_seconds,
                time.time()
            ))

    def search_similar(self, query_vec: List[float], kind: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar vectors using cosine similarity"""
        query = np.array(query_vec, dtype=np.float32)
        query = query / np.linalg.norm(query)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT item_id, vec, meta FROM embeddings
                WHERE kind = ? AND created_at > ?
                ORDER BY created_at DESC
            """, (kind, time.time() - 2592000)).fetchall()

            similarities = []
            for row in rows:
                item_id, vec_bytes, meta = row
                vec = np.frombuffer(vec_bytes, dtype=np.float32)
                vec = vec / np.linalg.norm(vec)

                similarity = float(np.dot(query, vec))
                similarities.append({
                    'item_id': item_id,
                    'similarity': similarity,
                    'meta': json.loads(meta)
                })

            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]

    # Graph operations
    def store_node(self, node_id: str, kind: str, uri: str = "", meta: Dict[str, Any] = None, ttl_seconds: int = 2592000):
        """Store a graph node"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nodes (id, kind, uri, meta, ttl, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                node_id,
                kind,
                uri,
                json.dumps(meta or {}),
                ttl_seconds,
                time.time()
            ))

    def store_edge(self, src: str, dst: str, rel: str, meta: Dict[str, Any] = None, ttl_seconds: int = 2592000):
        """Store a graph edge"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO edges (src, dst, rel, meta, ttl, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                src,
                dst,
                rel,
                json.dumps(meta or {}),
                ttl_seconds,
                time.time()
            ))

    def get_node_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get neighbors of a node"""
        with sqlite3.connect(self.db_path) as conn:
            if relation:
                rows = conn.execute("""
                    SELECT dst, rel, meta FROM edges
                    WHERE src = ? AND rel = ? AND created_at > ?
                """, (node_id, relation, time.time() - 2592000)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT dst, rel, meta FROM edges
                    WHERE src = ? AND created_at > ?
                """, (node_id, time.time() - 2592000)).fetchall()

            return [{
                'target': row[0],
                'relation': row[1],
                'meta': json.loads(row[2])
            } for row in rows]

    def get_reverse_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get nodes that point to this node"""
        with sqlite3.connect(self.db_path) as conn:
            if relation:
                rows = conn.execute("""
                    SELECT src, rel, meta FROM edges
                    WHERE dst = ? AND rel = ? AND created_at > ?
                """, (node_id, relation, time.time() - 2592000)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT src, rel, meta FROM edges
                    WHERE dst = ? AND created_at > ?
                """, (node_id, time.time() - 2592000)).fetchall()

            return [{
                'source': row[0],
                'relation': row[1],
                'meta': json.loads(row[2])
            } for row in rows]

    # Memory lifecycle management
    def cleanup_expired(self):
        """Remove expired entries based on TTL"""
        cutoff = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # Remove expired decisions (unless pinned)
            conn.execute("""
                DELETE FROM decisions
                WHERE pinned = 0 AND (created_at + ttl) < ?
            """, (cutoff,))

            # Remove expired embeddings
            conn.execute("""
                DELETE FROM embeddings
                WHERE (created_at + ttl) < ?
            """, (cutoff,))

            # Remove expired nodes and edges
            conn.execute("""
                DELETE FROM nodes
                WHERE (created_at + ttl) < ?
            """, (cutoff,))

            conn.execute("""
                DELETE FROM edges
                WHERE (created_at + ttl) < ?
            """, (cutoff,))

    def compact_database(self):
        """Compact the database to reclaim space"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            for table in ['decisions', 'actions', 'embeddings', 'nodes', 'edges']:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count

            return stats

    def export_data(self, tables: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Export data from specified tables"""
        if tables is None:
            tables = ['decisions', 'embeddings', 'nodes', 'edges']

        export = {}

        with sqlite3.connect(self.db_path) as conn:
            for table in tables:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                columns = [desc[0] for desc in conn.execute(f"PRAGMA table_info({table})").fetchall()]

                export[table] = []
                for row in rows:
                    export[table].append(dict(zip(columns, row)))

        return export