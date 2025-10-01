
"""
User Management System
Syncs users between dashboard (Prisma/PostgreSQL) and backend (SQLite/PostgreSQL)
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user accounts and syncing between systems"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self._ensure_users_table()
    
    def _ensure_users_table(self):
        """Create users table if it doesn't exist"""
        if self.db.db_type == 'sqlite':
            schema = """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'admin',
                phone_number TEXT,
                company_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:
            schema = """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'admin',
                phone_number TEXT,
                company_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        
        try:
            cursor = self.db._connection.cursor()
            cursor.execute(schema)
            self.db._connection.commit()
            logger.info("Users table ready")
        except Exception as e:
            logger.error(f"Error creating users table: {str(e)}")
    
    def get_or_create_user(self, user_id, email, name=None, **kwargs):
        """Get existing user or create new one"""
        user = self.get_user(user_id)
        
        if user:
            return user
        
        # Create new user
        return self.create_user(user_id, email, name, **kwargs)
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            cursor = self.db._connection.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                if self.db.db_type == 'sqlite':
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                else:
                    return dict(result)
            
            return None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            cursor = self.db._connection.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            
            if result:
                if self.db.db_type == 'sqlite':
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                else:
                    return dict(result)
            
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    def create_user(self, user_id, email, name=None, **kwargs):
        """Create new user"""
        try:
            # Parse name
            first_name = kwargs.get('first_name', '')
            last_name = kwargs.get('last_name', '')
            
            if name and not (first_name or last_name):
                parts = name.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
            
            cursor = self.db._connection.cursor()
            cursor.execute("""
                INSERT INTO users (id, email, first_name, last_name, role, phone_number, company_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                email,
                first_name,
                last_name,
                kwargs.get('role', 'admin'),
                kwargs.get('phone_number'),
                kwargs.get('company_name')
            ))
            self.db._connection.commit()
            
            logger.info(f"Created user: {email}")
            return self.get_user(user_id)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    def update_user(self, user_id, **kwargs):
        """Update user information"""
        try:
            updates = []
            values = []
            
            allowed_fields = ['first_name', 'last_name', 'phone_number', 'company_name', 'role']
            
            for field in allowed_fields:
                if field in kwargs:
                    updates.append(f"{field} = ?")
                    values.append(kwargs[field])
            
            if not updates:
                return self.get_user(user_id)
            
            # Add updated_at
            if self.db.db_type == 'sqlite':
                updates.append("updated_at = CURRENT_TIMESTAMP")
            else:
                updates.append("updated_at = NOW()")
            
            values.append(user_id)
            
            cursor = self.db._connection.cursor()
            cursor.execute(f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            self.db._connection.commit()
            
            return self.get_user(user_id)
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return None
    
    def list_users(self):
        """Get all users"""
        try:
            cursor = self.db._connection.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            results = cursor.fetchall()
            
            if self.db.db_type == 'sqlite':
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
            else:
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []
