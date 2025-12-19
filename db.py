import psycopg2
from psycopg2.extras import RealDictCursor
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "starwars_game",
    "user": "postgres",
    "password": "123",
}

def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn

def load_all_characters():
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM characters ORDER BY character_id")
        return cur.fetchall()

def load_character(cid):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM characters WHERE character_id=%s",(cid,))
        return cur.fetchone()

def load_player_progress(cid):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM player_progress WHERE character_id=%s",(cid,))
        r = cur.fetchone()
        return r or {"character_id":cid,"current_chapter":1,"unlocked_chapters":1}

def save_player_progress(cid, current_chapter, unlocked_chapters):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("""
        INSERT INTO player_progress(character_id,current_chapter,unlocked_chapters)
        VALUES(%s,%s,%s)
        ON CONFLICT (character_id)
        DO UPDATE SET current_chapter=%s, unlocked_chapters=%s
        """,(cid,current_chapter,unlocked_chapters,current_chapter,unlocked_chapters))

def load_chapter(chid):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM chapters WHERE chapter_id=%s",(chid,))
        return cur.fetchone()

def load_chapters_upto(maxc):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM chapters WHERE chapter_id<=%s",(maxc,))
        return cur.fetchall()

def load_chapter_bots(chid):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
        SELECT b.*, cb.spawn_count
        FROM chapter_bots cb
        JOIN bots b ON b.bot_id=cb.bot_id
        WHERE cb.chapter_id=%s
        """,(chid,))
        return cur.fetchall()

def load_boss_for_chapter(chid):
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM bosses WHERE chapter_id=%s",(chid,))
        return cur.fetchone()

def add_character_stats(cid: int, hp_add: int = 0, attack_add: int = 0):
    """+hp и +attack к персонажу (characters.hp / characters.attack)."""
    with get_conn() as c, c.cursor() as cur:
        cur.execute("""
            UPDATE characters
            SET hp = COALESCE(hp, 0) + %s,
                attack = COALESCE(attack, 0) + %s
            WHERE character_id = %s
        """, (int(hp_add), int(attack_add), int(cid)))


def load_character_stats(cid: int):
    """Вернет текущие hp/attack персонажа."""
    with get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT hp, attack
            FROM characters
            WHERE character_id = %s
        """, (cid,))
        row = cur.fetchone()
        return row or {"hp": 0, "attack": 0}


def apply_chapter_reward_once(cid, chapter_id, hp_add=0, dmg_add=0):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("""
        INSERT INTO chapter_rewards_applied(character_id, chapter_id)
        VALUES (%s, %s)
        ON CONFLICT (character_id, chapter_id) DO NOTHING
        """, (int(cid), int(chapter_id)))
        applied_now = (cur.rowcount == 1)

    if applied_now:
        add_character_stats(cid, hp_add=hp_add, attack_add=dmg_add)

    return applied_now
