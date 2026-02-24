"""Persistent memory system with SQLite and hybrid search."""

import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib


class MemoryManager:
    """Persistent memory with SQLite and hybrid search (vector + keyword)."""
    
    def __init__(self, db_path: Optional[str] = None, auto_save: bool = True):
        """Initialize memory manager.
        
        Args:
            db_path: Path to SQLite database (default: ~/.nucleo/memory.db)
            auto_save: Auto-save memories after each update
        """
        if db_path is None:
            db_path = str(Path.home() / '.nucleo' / 'memory.db')
        
        self.db_path = db_path
        self.auto_save = auto_save
        self._ensure_db()
    
    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                importance INTEGER DEFAULT 1,
                hash TEXT UNIQUE
            )
        """)
        
        # Keywords table (for FTS - Full Text Search)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        """)
        
        # Create FTS virtual table for fast text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                content=memories,
                content_rowid=id
            )
        """)
        
        # Embeddings table (placeholder for future vector DB)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER NOT NULL,
                embedding BLOB,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_memory(
        self,
        user_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: int = 1,
    ) -> int:
        """Save a memory to persistent storage.
        
        Args:
            user_id: User identifier
            content: Memory content
            tags: Optional list of tags
            importance: Import level (1-5)
            
        Returns:
            Memory ID
        """
        # Create hash to prevent duplicates
        memory_hash = hashlib.md5(f"{user_id}:{content}".encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO memories (user_id, content, tags, importance, hash)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, content, json.dumps(tags or []), importance, memory_hash))
            
            memory_id = cursor.lastrowid
            
            # Extract and save keywords (simple word tokenization)
            keywords = self._extract_keywords(content)
            for keyword in keywords:
                cursor.execute("""
                    INSERT INTO keywords (memory_id, keyword, weight)
                    VALUES (?, ?, ?)
                """, (memory_id, keyword, 1.0))
            
            # Update FTS index
            cursor.execute("""
                INSERT INTO memories_fts (rowid, content)
                VALUES (?, ?)
            """, (memory_id, content))
            
            conn.commit()
            return memory_id
            
        except sqlite3.IntegrityError:
            # Duplicate - return existing ID
            cursor.execute("SELECT id FROM memories WHERE hash = ?", (memory_hash,))
            result = cursor.fetchone()
            return result[0] if result else -1
        finally:
            conn.close()
    
    def recall_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_importance: int = 1,
    ) -> List[Dict[str, Any]]:
        """Recall relevant memories using hybrid search.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Maximum results
            min_importance: Minimum importance to return
            
        Returns:
            List of relevant memories
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Keyword search using FTS
        keywords = self._extract_keywords(query)
        keyword_placeholders = ' AND '.join(['content MATCH ?'] * len(keywords))
        
        if keyword_placeholders:
            cursor.execute(f"""
                SELECT m.id, m.content, m.timestamp, m.tags, m.importance
                FROM memories m
                JOIN memories_fts fts ON m.id = fts.rowid
                WHERE m.user_id = ? AND m.importance >= ? AND {keyword_placeholders}
                ORDER BY m.importance DESC, m.timestamp DESC
                LIMIT ?
            """, [user_id, min_importance] + keywords + [limit])
        else:
            cursor.execute("""
                SELECT id, content, timestamp, tags, importance
                FROM memories
                WHERE user_id = ? AND importance >= ?
                ORDER BY importance DESC, timestamp DESC
                LIMIT ?
            """, (user_id, min_importance, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'tags': json.loads(row['tags']),
                'importance': row['importance'],
            })
        
        conn.close()
        return results
    
    def get_user_memories(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent memories for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum results
            
        Returns:
            List of recent memories
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, content, timestamp, tags, importance
            FROM memories
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'tags': json.loads(row['tags']),
                'importance': row['importance'],
            })
        
        conn.close()
        return results
    
    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory.
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete from FTS
        cursor.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
        
        # Delete keywords
        cursor.execute("DELETE FROM keywords WHERE memory_id = ?", (memory_id,))
        
        # Delete embeddings
        cursor.execute("DELETE FROM embeddings WHERE memory_id = ?", (memory_id,))
        
        # Delete memory
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted
    
    def clear_user_memories(self, user_id: str) -> int:
        """Clear all memories for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of memories deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all memory IDs for user
        cursor.execute("SELECT id FROM memories WHERE user_id = ?", (user_id,))
        memory_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete each memory
        for memory_id in memory_ids:
            cursor.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
            cursor.execute("DELETE FROM keywords WHERE memory_id = ?", (memory_id,))
            cursor.execute("DELETE FROM embeddings WHERE memory_id = ?", (memory_id,))
        
        # Delete all memories for user
        cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        return len(memory_ids)
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text.
        
        Args:
            text: Text to extract from
            max_keywords: Maximum keywords to extract
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction (remove common words)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        words = text.lower().split()
        keywords = [w.strip('.,!?;:') for w in words if w.lower() not in stop_words and len(w) > 2]
        
        return list(set(keywords))[:max_keywords]
    
    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(importance), MAX(importance), MIN(importance)
            FROM memories WHERE user_id = ?
        """, (user_id,))
        avg_imp, max_imp, min_imp = cursor.fetchone()
        
        cursor.execute("""
            SELECT DATE(timestamp), COUNT(*) FROM memories
            WHERE user_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) DESC
            LIMIT 7
        """, (user_id,))
        recent = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_memories': total,
            'avg_importance': avg_imp or 0,
            'max_importance': max_imp or 0,
            'min_importance': min_imp or 0,
            'recent_7_days': recent,
        }
