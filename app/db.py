import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_pool: pool.ThreadedConnectionPool | None = None
_ph = PasswordHasher()


def run_migrations() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE registrations
                ADD COLUMN IF NOT EXISTS payment_confirmed BOOLEAN NOT NULL DEFAULT FALSE
            """)


def init_pool() -> None:
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=8,
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_settings() -> dict[str, str]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cur.fetchall()}


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE settings SET value = %s WHERE key = %s", (value, key))


def get_table_bookings() -> dict[int, int]:
    """Returns {table_nr: total_tickets_wished} for all tables that have registrations."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT desired_table, SUM(total_tickets)
                FROM registrations
                WHERE desired_table IS NOT NULL
                GROUP BY desired_table
                """
            )
            return {int(row[0]): int(row[1]) for row in cur.fetchall()}


def get_ticket_counts() -> tuple[int, int, int]:
    """Returns (total_available, tickets_sold, remaining)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = 'total_tickets'")
            total = int(cur.fetchone()[0])
            cur.execute("SELECT COALESCE(SUM(total_tickets), 0) FROM registrations")
            sold = int(cur.fetchone()[0])
            return total, sold, total - sold


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

def ensure_admin_user(username: str, password: str) -> None:
    hashed = _ph.hash(password)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_users (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """,
                (username, hashed),
            )


def verify_admin(username: str, password: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash FROM admin_users WHERE username = %s", (username,)
            )
            row = cur.fetchone()
            if not row:
                return False
            try:
                _ph.verify(row[0], password)
                return True
            except VerifyMismatchError:
                return False


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

def create_registration(
    registrant_name: str,
    email: str,
    desired_table: int | None,
    persons: list[dict],
    ip_address: str | None,
) -> int:
    """
    Inserts a registration and all persons atomically.
    When fcfs_block_enabled is true, blocks if all tickets are sold.
    Returns the new registration id.
    Raises ValueError('no_tickets') when blocked due to sold-out.
    """
    total_tickets = len(persons)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = 'fcfs_block_enabled'")
            fcfs = cur.fetchone()[0].lower() == "true"

            if fcfs:
                cur.execute("LOCK TABLE registrations IN SHARE ROW EXCLUSIVE MODE")
                cur.execute("SELECT COALESCE(SUM(total_tickets), 0) FROM registrations")
                sold = int(cur.fetchone()[0])
                cur.execute("SELECT value FROM settings WHERE key = 'total_tickets'")
                total = int(cur.fetchone()[0])
                if sold >= total:
                    raise ValueError("no_tickets")

            cur.execute(
                """
                INSERT INTO registrations
                    (registrant_name, email, desired_table, total_tickets, ip_address)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (registrant_name, email, desired_table, total_tickets, ip_address),
            )
            reg_id = cur.fetchone()[0]

            for person in persons:
                cur.execute(
                    """
                    INSERT INTO persons
                        (registration_id, name, is_over_18, food_preference, is_registrant)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        reg_id,
                        person["name"],
                        person["is_over_18"],
                        person["food_preference"],
                        person["is_registrant"],
                    ),
                )
            return reg_id


def get_all_registrations() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    r.id,
                    r.registrant_name,
                    r.email,
                    r.desired_table,
                    r.total_tickets,
                    r.payment_confirmed,
                    r.created_at,
                    r.ip_address,
                    COALESCE(json_agg(
                        json_build_object(
                            'name',            p.name,
                            'is_over_18',      p.is_over_18,
                            'food_preference', p.food_preference,
                            'is_registrant',   p.is_registrant
                        ) ORDER BY p.is_registrant DESC, p.id
                    ), '[]'::json) AS persons
                FROM registrations r
                JOIN persons p ON p.registration_id = r.id
                GROUP BY r.id
                ORDER BY r.created_at ASC
                """
            )
            return cur.fetchall()
