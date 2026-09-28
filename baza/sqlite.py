import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path_to_db: str = "main.db", debug: bool = False):
        self.path_to_db = path_to_db
        self.debug = debug
        self._init_db()

    def _init_db(self) -> None:
        """Initsizatsiya qilish va jadvallarni yaratish"""
        try:
            connection = sqlite3.connect(self.path_to_db)
            connection.execute("PRAGMA foreign_keys = ON")
            connection.close()
            logger.info(f"Database {self.path_to_db} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        """Bazaga ulanish yaratish"""
        conn = sqlite3.connect(self.path_to_db)
        conn.execute("PRAGMA foreign_keys = ON")
        if self.debug:
            conn.set_trace_callback(self._log_sql)
        return conn

    @staticmethod
    def _log_sql(statement: str) -> None:
        """SQL so'rovlarini logga yozish"""
        logger.debug(f"SQL: {statement}")

    def execute(
        self, 
        sql: str, 
        parameters: Tuple = None, 
        fetchone: bool = False, 
        fetchall: bool = False, 
        commit: bool = False
    ) -> Optional[Any]:
        """SQL so'rovni bajaritsh"""
        if parameters is None:
            parameters = ()
        
        connection = self.connection
        cursor = connection.cursor()
        data = None
        
        try:
            cursor.execute(sql, parameters)
            
            if commit:
                connection.commit()
                logger.debug(f"Query committed: {sql}")
            
            if fetchall:
                data = cursor.fetchall()
            elif fetchone:
                data = cursor.fetchone()
                
            return data
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}\nSQL: {sql}\nParams: {parameters}")
            connection.rollback()
            raise
        finally:
            connection.close()

    def execute_script(self, sql: str) -> None:
        """Bir nechta SQL buyruqlarini ketma-ket bajarish"""
        connection = self.connection
        try:
            connection.executescript(sql)
            connection.commit()
            logger.debug("SQL script committed successfully")
        except sqlite3.Error as e:
            logger.error(f"Database script error: {e}\nSQL: {sql}")
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_table_users(self) -> None:
        """Foydalanuvchilar jadvalini yaratish"""
        sql = """
        CREATE TABLE IF NOT EXISTS Users (
            full_name TEXT,
            telegram_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_telegram_id ON Users(telegram_id);
        """
        try:
            self.execute_script(sql)
            logger.info("Users table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create users table: {e}")
    
    def create_table_channels(self) -> None:
        """Kanallar jadvalini yaratish"""
        sql = """
        CREATE TABLE IF NOT EXISTS Channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_channel_id ON Channels(channel_id);
        """
        try:
            self.execute_script(sql)
            logger.info("Channels table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create channels table: {e}")

    def create_table_appeals(self) -> None:
        """Murojaatlar jadvalini yaratish"""
        sql = """
        CREATE TABLE IF NOT EXISTS Appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            organization TEXT,
            is_anonymous INTEGER DEFAULT 0,
            message_text TEXT NOT NULL,
            category TEXT DEFAULT 'Boshqa',
            risk_level TEXT DEFAULT 'Past',
            priority TEXT DEFAULT 'Rejalashtirilgan',
            status TEXT DEFAULT 'Yangi',
            route_to TEXT DEFAULT 'Operator ko''rib chiqishi',
            ai_summary TEXT,
            ai_keywords TEXT,
            ai_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES Users(telegram_id)
        );
        CREATE INDEX IF NOT EXISTS idx_appeals_user_id ON Appeals(user_id);
        CREATE INDEX IF NOT EXISTS idx_appeals_status ON Appeals(status);
        CREATE INDEX IF NOT EXISTS idx_appeals_risk_level ON Appeals(risk_level);
        """
        try:
            self.execute_script(sql)
            self.ensure_column(
                table_name="Appeals",
                column_name="is_anonymous",
                column_definition="INTEGER DEFAULT 0",
            )
            logger.info("Appeals table created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create appeals table: {e}")

    def ensure_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Jadvalda ustun mavjudligini tekshirish va kerak bo'lsa qo'shish"""
        sql = f"PRAGMA table_info({table_name});"
        columns = self.execute(sql, fetchall=True) or []
        column_names = {column[1] for column in columns}
        if column_name in column_names:
            return

        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};"
        self.execute(alter_sql, commit=True)
        logger.info("Added missing column %s to %s", column_name, table_name)

    @staticmethod
    def format_args(sql: str, parameters: dict) -> Tuple[str, Tuple]:
        """SQL so'rovni parametrlarni sozlashtirish"""
        sql += " AND ".join([f"{item} = ?" for item in parameters])
        return sql, tuple(parameters.values())

    def add_user(self, telegram_id: int, full_name: str) -> None:
        """Yangi foydalanuvchini qo'shish"""
        sql = """
        INSERT INTO Users (telegram_id, full_name) VALUES(?, ?);
        """
        try:
            self.execute(sql, parameters=(telegram_id, full_name), commit=True)
            logger.info(f"User added: {telegram_id}")
        except sqlite3.IntegrityError:
            logger.warning(f"User {telegram_id} already exists")
        except sqlite3.Error as e:
            logger.error(f"Failed to add user: {e}")
            raise

    def add_channel(self, channel_id: int, channel_name: str, channel_link: str) -> None:
        """Yangi kanalni qo'shish"""
        sql = "INSERT INTO Channels (channel_id, channel_name, channel_link) VALUES(?, ?, ?);"
        try:
            self.execute(sql, parameters=(channel_id, channel_name, channel_link), commit=True)
            logger.info(f"Channel added: {channel_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to add channel: {e}")
            raise

    def add_appeal(
        self,
        user_id: int,
        full_name: str,
        phone: str,
        organization: str,
        is_anonymous: bool,
        message_text: str,
        analysis: Dict[str, str],
    ) -> int:
        """Yangi murojaatni saqlash"""
        sql = """
        INSERT INTO Appeals (
            user_id, full_name, phone, organization, is_anonymous, message_text,
            category, risk_level, priority, status, route_to,
            ai_summary, ai_keywords, ai_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        connection = self.connection
        try:
            cursor = connection.cursor()
            cursor.execute(
                sql,
                (
                    user_id,
                    full_name,
                    phone,
                    organization,
                    int(is_anonymous),
                    message_text,
                    analysis.get("category", "Boshqa"),
                    analysis.get("risk_level", "Past"),
                    analysis.get("priority", "Rejalashtirilgan"),
                    "Yangi",
                    analysis.get("route_to", "Operator ko'rib chiqishi"),
                    analysis.get("summary", ""),
                    analysis.get("keywords", ""),
                    analysis.get("analysis_notes", ""),
                ),
            )
            connection.commit()
            appeal_id = cursor.lastrowid
            logger.info("Appeal added: %s", appeal_id)
            return int(appeal_id)
        except sqlite3.Error as e:
            connection.rollback()
            logger.error(f"Failed to add appeal: {e}")
            raise
        finally:
            connection.close()
    
    def select_all_channels(self) -> List[Tuple]:
        """
        Barcha kanallarni olib olish.

        Ustunlar aniq sanab o'tilgan: "SELECT *" created_at ni ham qaytarardi va
        chaqiruvchi kod uni uch qiymatga ochgani uchun ValueError chiqardi.
        """
        sql = "SELECT channel_id, channel_name, channel_link FROM Channels ORDER BY created_at DESC"
        try:
            result = self.execute(sql, fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to select channels: {e}")
            return []

    def delete_channel(self, channel_id: int) -> None:
        """Kanalni o'chirish"""
        try:
            self.execute(
                "DELETE FROM Channels WHERE channel_id = ?", 
                parameters=(channel_id,), 
                commit=True
            )
            logger.info(f"Channel deleted: {channel_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete channel: {e}")
            raise

    def select_all_users(self) -> List[Tuple]:
        """Barcha foydalanuvchilarni olib olish"""
        sql = "SELECT * FROM Users ORDER BY created_at DESC"
        try:
            result = self.execute(sql, fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to select users: {e}")
            return []

    def select_user(self, **kwargs) -> Optional[Tuple]:
        """Foydalanuvchini qidirish"""
        base_sql = "SELECT * FROM Users WHERE "
        sql, parameters = self.format_args(base_sql, kwargs)
        try:
            return self.execute(sql, parameters=parameters, fetchone=True)
        except sqlite3.Error as e:
            logger.error(f"Failed to select user: {e}")
            return None

    def count_users(self) -> int:
        """Foydalanuvchilar sonini hisoblash"""
        try:
            result = self.execute("SELECT COUNT(*) FROM Users;", fetchone=True)
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count users: {e}")
            return 0

    def delete_users(self) -> None:
        """Barcha foydalanuvchilarni o'chirish"""
        try:
            self.execute("DELETE FROM Users;", commit=True)
            logger.warning("All users deleted from database")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete users: {e}")
            raise
    
    def all_users_id(self) -> List[Tuple]:
        """Barcha foydalanuvchilarning ID larini olib olish"""
        try:
            result = self.execute("SELECT telegram_id FROM Users;", fetchall=True)
            return result or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get user IDs: {e}")
            return []

    def get_user_appeals(self, user_id: int, limit: int = 5) -> List[Tuple]:
        """Foydalanuvchi murojaatlarini olish"""
        sql = """
        SELECT id, category, risk_level, status, created_at, is_anonymous
        FROM Appeals
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?;
        """
        try:
            return self.execute(sql, parameters=(user_id, limit), fetchall=True) or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get user appeals: {e}")
            return []

    def get_recent_appeals(self, limit: int = 10) -> List[Tuple]:
        """So'nggi murojaatlarni olish"""
        sql = """
        SELECT id, user_id, full_name, phone, organization, category, risk_level, priority, status, created_at, message_text, is_anonymous
        FROM Appeals
        ORDER BY created_at DESC
        LIMIT ?;
        """
        try:
            return self.execute(sql, parameters=(limit,), fetchall=True) or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent appeals: {e}")
            return []

    def get_appeal_statistics(self) -> Dict[str, int]:
        """Asosiy murojaatlar statistikasini olish"""
        queries = {
            "total": "SELECT COUNT(*) FROM Appeals;",
            "today": "SELECT COUNT(*) FROM Appeals WHERE DATE(created_at) = DATE('now', 'localtime');",
            "high_risk": "SELECT COUNT(*) FROM Appeals WHERE risk_level = 'Yuqori';",
            "in_review": "SELECT COUNT(*) FROM Appeals WHERE status IN ('Yangi', 'Ko''rib chiqilmoqda');",
            "resolved": "SELECT COUNT(*) FROM Appeals WHERE status = 'Yakunlangan';",
        }
        stats = {}
        for key, sql in queries.items():
            result = self.execute(sql, fetchone=True)
            stats[key] = result[0] if result else 0
        return stats

    def get_category_statistics(self) -> List[Tuple[str, int]]:
        """Toifalar kesimidagi statistika"""
        sql = """
        SELECT category, COUNT(*) AS total
        FROM Appeals
        GROUP BY category
        ORDER BY total DESC, category ASC;
        """
        try:
            return self.execute(sql, fetchall=True) or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get category statistics: {e}")
            return []

    def get_risk_statistics(self) -> List[Tuple[str, int]]:
        """Xavf darajalari kesimidagi statistika"""
        sql = """
        SELECT risk_level, COUNT(*) AS total
        FROM Appeals
        GROUP BY risk_level
        ORDER BY total DESC, risk_level ASC;
        """
        try:
            return self.execute(sql, fetchall=True) or []
        except sqlite3.Error as e:
            logger.error(f"Failed to get risk statistics: {e}")
            return []
