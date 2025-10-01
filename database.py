
"""
Database Connection Manager
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and queries"""
    
    def __init__(self):
        self.db_type = os.getenv('DATABASE_TYPE', 'sqlite')  # 'sqlite' or 'postgres'
        self.db_path = os.getenv('DATABASE_PATH', './data/phone_system.db')
        self.postgres_url = os.getenv('DATABASE_URL')
        self._connection = None
        
        if self.db_type == 'sqlite':
            self._init_sqlite()
        else:
            self._init_postgres()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create connection
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            logger.info(f"SQLite database initialized: {self.db_path}")
            
            # Run migrations
            self._run_sqlite_migrations()
            
        except Exception as e:
            logger.error(f"SQLite initialization failed: {str(e)}")
            raise
    
    def _init_postgres(self):
        """Initialize PostgreSQL database"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self._connection = psycopg2.connect(
                self.postgres_url,
                cursor_factory=RealDictCursor
            )
            self._connection.autocommit = True
            logger.info("PostgreSQL database initialized")
            
            # Run migrations
            self._run_postgres_migrations()
            
        except Exception as e:
            logger.error(f"PostgreSQL initialization failed: {str(e)}")
            # Fallback to SQLite
            logger.warning("Falling back to SQLite")
            self.db_type = 'sqlite'
            self._init_sqlite()
    
    def _run_sqlite_migrations(self):
        """Run SQLite migrations (convert from PostgreSQL schema)"""
        cursor = self._connection.cursor()
        
        migrations = [
            # Recurring Bookings
            """
            CREATE TABLE IF NOT EXISTS recurring_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                customer_name TEXT,
                facility_type TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                time_slot TEXT NOT NULL,
                duration_hours REAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                next_booking_date TEXT,
                is_active INTEGER DEFAULT 1,
                calcom_event_type_id INTEGER,
                price_per_booking REAL,
                total_bookings_created INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Waitlist
            """
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                customer_name TEXT,
                facility_type TEXT NOT NULL,
                requested_date TEXT NOT NULL,
                requested_time TEXT NOT NULL,
                duration_hours REAL NOT NULL,
                priority INTEGER DEFAULT 0,
                notified_at TEXT,
                expires_at TEXT,
                status TEXT DEFAULT 'waiting',
                notification_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Customers
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                name TEXT,
                tier TEXT DEFAULT 'standard',
                total_bookings INTEGER DEFAULT 0,
                total_spent_dollars REAL DEFAULT 0,
                loyalty_points INTEGER DEFAULT 0,
                preferences TEXT DEFAULT '{}',
                voice_print TEXT,
                communication_preference TEXT DEFAULT 'sms',
                favorite_facility TEXT,
                preferred_time_slot TEXT,
                average_duration_hours REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_booking_at TEXT,
                vip_since TEXT
            )
            """,
            
            # Loyalty Transactions
            """
            CREATE TABLE IF NOT EXISTS loyalty_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_phone TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                points INTEGER NOT NULL,
                description TEXT,
                booking_id TEXT,
                balance_after INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
            """,
            
            # Booking Analytics
            """
            CREATE TABLE IF NOT EXISTS booking_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility_type TEXT NOT NULL,
                day_of_week INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                booking_count INTEGER DEFAULT 0,
                revenue_dollars REAL DEFAULT 0,
                average_duration_hours REAL DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(facility_type, day_of_week, hour)
            )
            """,
            
            # Emergency Bookings
            """
            CREATE TABLE IF NOT EXISTS emergency_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_uuid TEXT UNIQUE,
                customer_phone TEXT NOT NULL,
                customer_name TEXT,
                facility_type TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                urgency_level TEXT DEFAULT 'high',
                reason TEXT,
                staff_notified INTEGER DEFAULT 0,
                staff_notification_sent_at TEXT,
                status TEXT DEFAULT 'pending',
                calcom_booking_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            )
            """,
            
            # Rebooking Campaigns
            """
            CREATE TABLE IF NOT EXISTS rebooking_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                customer_name TEXT,
                last_booking_id TEXT,
                last_booking_date TEXT,
                last_facility_type TEXT,
                campaign_type TEXT DEFAULT 'standard',
                outbound_call_scheduled_at TEXT,
                outbound_call_made_at TEXT,
                call_status TEXT DEFAULT 'pending',
                rebooked INTEGER DEFAULT 0,
                new_booking_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Email Log
            """
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_email TEXT NOT NULL,
                recipient_phone TEXT,
                email_type TEXT NOT NULL,
                subject TEXT,
                booking_id TEXT,
                sendgrid_message_id TEXT,
                status TEXT DEFAULT 'sent',
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Group Bookings
            """
            CREATE TABLE IF NOT EXISTS group_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calcom_booking_id TEXT UNIQUE NOT NULL,
                conversation_uuid TEXT,
                customer_phone TEXT NOT NULL,
                coordinator_name TEXT,
                coordinator_email TEXT,
                facility_type TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                group_size INTEGER NOT NULL,
                base_price REAL,
                group_multiplier REAL,
                total_price REAL,
                special_requirements TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for migration in migrations:
            try:
                cursor.execute(migration)
            except Exception as e:
                logger.error(f"Migration failed: {str(e)}")
        
        self._connection.commit()
        logger.info("SQLite migrations completed")
    
    def _run_postgres_migrations(self):
        """Run PostgreSQL migrations from schema file"""
        try:
            # Run Phase 6 migrations
            schema_path_6 = os.path.join(os.path.dirname(__file__), 'migrations', 'phase6_schema.sql')
            
            if os.path.exists(schema_path_6):
                with open(schema_path_6, 'r') as f:
                    schema = f.read()
                
                cursor = self._connection.cursor()
                cursor.execute(schema)
                logger.info("PostgreSQL Phase 6 migrations completed")
            else:
                logger.warning("PostgreSQL Phase 6 schema file not found")
            
            # Run Phase 7 migrations
            schema_path_7 = os.path.join(os.path.dirname(__file__), 'migrations', 'phase7_schema.sql')
            
            if os.path.exists(schema_path_7):
                with open(schema_path_7, 'r') as f:
                    schema = f.read()
                
                cursor = self._connection.cursor()
                cursor.execute(schema)
                logger.info("PostgreSQL Phase 7 migrations completed")
            
            # Run Phase 8 migrations
            schema_path_8 = os.path.join(os.path.dirname(__file__), 'migrations', 'phase8_schema.sql')
            
            if os.path.exists(schema_path_8):
                with open(schema_path_8, 'r') as f:
                    schema = f.read()
                
                cursor = self._connection.cursor()
                cursor.execute(schema)
                logger.info("PostgreSQL Phase 8 migrations completed")
                
        except Exception as e:
            logger.error(f"PostgreSQL migration failed: {str(e)}")
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor (context manager)"""
        cursor = self._connection.cursor()
        try:
            yield cursor
            if self.db_type == 'sqlite':
                self._connection.commit()
        except Exception as e:
            if self.db_type == 'sqlite':
                self._connection.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if self.db_type == 'postgres':
                cursor.close()
    
    def execute(self, query, params=None):
        """Execute a query and return cursor"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor
    
    def fetchone(self, query, params=None):
        """Execute query and fetch one result"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()
    
    def fetchall(self, query, params=None):
        """Execute query and fetch all results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    def insert(self, table, data):
        """Insert a row and return the new ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' if self.db_type == 'sqlite' else '%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()))
            
            if self.db_type == 'sqlite':
                return cursor.lastrowid
            else:
                return cursor.fetchone()['id']
    
    def update(self, table, data, where_clause, where_params=None):
        """Update rows"""
        set_clause = ', '.join([f"{k} = ?" if self.db_type == 'sqlite' else f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        params = list(data.values())
        if where_params:
            params.extend(where_params)
        
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            logger.info("Database connection closed")


# Global database instance
db = DatabaseManager()
