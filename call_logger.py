
"""
Call Logging System
Tracks all phone calls with detailed information and links to user accounts
"""

import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CallLogger:
    """Manages call logging and history"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_call_logs_table()
    
    def _ensure_call_logs_table(self):
        """Create call_logs table if it doesn't exist"""
        if self.db.db_type == 'sqlite':
            schema = """
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                conversation_uuid TEXT UNIQUE NOT NULL,
                caller_id TEXT NOT NULL,
                caller_name TEXT,
                duration INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                intent TEXT,
                outcome TEXT DEFAULT 'in_progress',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                recording_url TEXT,
                transcription TEXT,
                notes TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        else:
            schema = """
            CREATE TABLE IF NOT EXISTS call_logs (
                id SERIAL PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                conversation_uuid TEXT UNIQUE NOT NULL,
                caller_id TEXT NOT NULL,
                caller_name TEXT,
                duration INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                intent TEXT,
                outcome TEXT DEFAULT 'in_progress',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                recording_url TEXT,
                transcription TEXT,
                notes TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        
        try:
            cursor = self.db._connection.cursor()
            cursor.execute(schema)
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_call_logs_user_id ON call_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_call_logs_intent ON call_logs(intent)",
                "CREATE INDEX IF NOT EXISTS idx_call_logs_outcome ON call_logs(outcome)",
                "CREATE INDEX IF NOT EXISTS idx_call_logs_conversation_uuid ON call_logs(conversation_uuid)",
            ]
            
            for index in indexes:
                try:
                    cursor.execute(index)
                except Exception:
                    pass  # Index might already exist
            
            self.db._connection.commit()
            logger.info("Call logs table ready")
        except Exception as e:
            logger.error(f"Error creating call_logs table: {str(e)}")
    
    def start_call(self, conversation_uuid, caller_id, user_id=None, caller_name=None, metadata=None):
        """Log the start of a call"""
        try:
            metadata_str = json.dumps(metadata) if metadata else None
            
            cursor = self.db._connection.cursor()
            cursor.execute("""
                INSERT INTO call_logs (user_id, conversation_uuid, caller_id, caller_name, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, conversation_uuid, caller_id, caller_name, metadata_str))
            self.db._connection.commit()
            
            logger.info(f"Call started: {conversation_uuid}")
            return self.get_call(conversation_uuid)
        except Exception as e:
            logger.error(f"Error logging call start: {str(e)}")
            return None
    
    def update_call(self, conversation_uuid, **kwargs):
        """Update call information"""
        try:
            updates = []
            values = []
            
            allowed_fields = ['duration', 'cost', 'intent', 'outcome', 'recording_url', 
                            'transcription', 'notes', 'caller_name', 'user_id', 'metadata']
            
            for field in allowed_fields:
                if field in kwargs:
                    if field == 'metadata' and kwargs[field]:
                        updates.append(f"{field} = ?")
                        values.append(json.dumps(kwargs[field]))
                    else:
                        updates.append(f"{field} = ?")
                        values.append(kwargs[field])
            
            if not updates:
                return self.get_call(conversation_uuid)
            
            # Add updated_at
            if self.db.db_type == 'sqlite':
                updates.append("updated_at = CURRENT_TIMESTAMP")
            else:
                updates.append("updated_at = NOW()")
            
            values.append(conversation_uuid)
            
            cursor = self.db._connection.cursor()
            cursor.execute(f"""
                UPDATE call_logs 
                SET {', '.join(updates)}
                WHERE conversation_uuid = ?
            """, values)
            self.db._connection.commit()
            
            return self.get_call(conversation_uuid)
        except Exception as e:
            logger.error(f"Error updating call: {str(e)}")
            return None
    
    def end_call(self, conversation_uuid, duration, outcome='completed', cost=0.0):
        """Log the end of a call"""
        return self.update_call(
            conversation_uuid,
            duration=duration,
            outcome=outcome,
            cost=cost
        )
    
    def get_call(self, conversation_uuid):
        """Get call by conversation UUID"""
        try:
            cursor = self.db._connection.cursor()
            cursor.execute("SELECT * FROM call_logs WHERE conversation_uuid = ?", (conversation_uuid,))
            result = cursor.fetchone()
            
            if result:
                if self.db.db_type == 'sqlite':
                    columns = [desc[0] for desc in cursor.description]
                    call = dict(zip(columns, result))
                else:
                    call = dict(result)
                
                # Parse metadata
                if call.get('metadata'):
                    try:
                        call['metadata'] = json.loads(call['metadata'])
                    except:
                        pass
                
                return call
            
            return None
        except Exception as e:
            logger.error(f"Error getting call: {str(e)}")
            return None
    
    def list_calls(self, user_id=None, limit=50, offset=0, intent=None, outcome=None):
        """List calls with optional filtering"""
        try:
            conditions = []
            values = []
            
            if user_id:
                conditions.append("user_id = ?")
                values.append(user_id)
            
            if intent:
                conditions.append("intent = ?")
                values.append(intent)
            
            if outcome:
                conditions.append("outcome = ?")
                values.append(outcome)
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            cursor = self.db._connection.cursor()
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM call_logs {where_clause}", values)
            total = cursor.fetchone()[0]
            
            # Get calls with pagination
            values.extend([limit, offset])
            cursor.execute(f"""
                SELECT * FROM call_logs 
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, values)
            results = cursor.fetchall()
            
            if self.db.db_type == 'sqlite':
                columns = [desc[0] for desc in cursor.description]
                calls = [dict(zip(columns, row)) for row in results]
            else:
                calls = [dict(row) for row in results]
            
            # Parse metadata for each call
            for call in calls:
                if call.get('metadata'):
                    try:
                        call['metadata'] = json.loads(call['metadata'])
                    except:
                        pass
            
            return {
                'calls': calls,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        except Exception as e:
            logger.error(f"Error listing calls: {str(e)}")
            return {'calls': [], 'total': 0, 'limit': limit, 'offset': offset}
    
    def get_call_stats(self, user_id=None, days=30):
        """Get call statistics"""
        try:
            conditions = []
            values = []
            
            if user_id:
                conditions.append("user_id = ?")
                values.append(user_id)
            
            # Add date filter
            if self.db.db_type == 'sqlite':
                conditions.append("datetime(timestamp) >= datetime('now', '-' || ? || ' days')")
            else:
                conditions.append("timestamp >= NOW() - INTERVAL '%s days'")
            values.append(days)
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            cursor = self.db._connection.cursor()
            
            # Total calls
            cursor.execute(f"SELECT COUNT(*) FROM call_logs {where_clause}", values)
            total_calls = cursor.fetchone()[0]
            
            # Total cost
            cursor.execute(f"SELECT COALESCE(SUM(cost), 0) FROM call_logs {where_clause}", values)
            total_cost = cursor.fetchone()[0]
            
            # Average duration
            cursor.execute(f"SELECT COALESCE(AVG(duration), 0) FROM call_logs {where_clause}", values)
            avg_duration = cursor.fetchone()[0]
            
            # Calls by intent
            cursor.execute(f"""
                SELECT intent, COUNT(*) as count 
                FROM call_logs 
                {where_clause}
                GROUP BY intent
                ORDER BY count DESC
            """, values)
            calls_by_intent = cursor.fetchall()
            
            # Calls by outcome
            cursor.execute(f"""
                SELECT outcome, COUNT(*) as count 
                FROM call_logs 
                {where_clause}
                GROUP BY outcome
                ORDER BY count DESC
            """, values)
            calls_by_outcome = cursor.fetchall()
            
            return {
                'total_calls': total_calls,
                'total_cost': float(total_cost),
                'avg_duration': float(avg_duration),
                'calls_by_intent': [{'intent': r[0], 'count': r[1]} for r in calls_by_intent],
                'calls_by_outcome': [{'outcome': r[0], 'count': r[1]} for r in calls_by_outcome]
            }
        except Exception as e:
            logger.error(f"Error getting call stats: {str(e)}")
            return {
                'total_calls': 0,
                'total_cost': 0.0,
                'avg_duration': 0.0,
                'calls_by_intent': [],
                'calls_by_outcome': []
            }
