"""
Database configuration and connection management for Semantic Memory System
"""
import os
from typing import Optional
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


class DatabaseConfig:
 """Database configuration and connection pool management"""
 
 def __init__(
 self,
 host: str = None,
 port: int = None,
 database: str = None,
 user: str = None,
 password: str = None,
 min_conn: int = 1,
 max_conn: int = 10
 ):
 self.host = host or os.getenv('DB_HOST', 'localhost')
 self.port = port or int(os.getenv('DB_PORT', '5432'))
 self.database = database or os.getenv('DB_NAME', 'semantic_memory')
 self.user = user or os.getenv('DB_USER', 'postgres')
 self.password = password or os.getenv('DB_PASSWORD', '')
 
 self._pool: Optional[SimpleConnectionPool] = None
 self._min_conn = min_conn
 self._max_conn = max_conn
 
 def initialize_pool(self):
 """Initialize the connection pool"""
 if self._pool is None:
 self._pool = SimpleConnectionPool(
 self._min_conn,
 self._max_conn,
 host=self.host,
 port=self.port,
 database=self.database,
 user=self.user,
 password=self.password
 )
 
 @contextmanager
 def get_connection(self):
 """Get a connection from the pool"""
 if self._pool is None:
 self.initialize_pool()
 
 conn = self._pool.getconn()
 try:
 yield conn
 finally:
 self._pool.putconn(conn)
 
 @contextmanager
 def get_cursor(self, cursor_factory=RealDictCursor):
 """Get a cursor from a pooled connection"""
 with self.get_connection() as conn:
 cursor = conn.cursor(cursor_factory=cursor_factory)
 try:
 yield cursor
 conn.commit()
 except Exception as e:
 conn.rollback()
 raise e
 finally:
 cursor.close()
 
 def close_pool(self):
 """Close all connections in the pool"""
 if self._pool:
 self._pool.closeall()
 self._pool = None


# Global database instance
db_config = DatabaseConfig()
