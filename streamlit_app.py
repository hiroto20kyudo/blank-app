import sqlite3
from datetime import date, datetime
import calendar
import streamlit as st
from streamlit_calendar import calendar as st_calendar

DB_PATH = "app.db"

# ---------- DB ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ev_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            place TEXT
        );
        """
    )
    conn.commit()
    conn.close()

def add_event(ev_date: str, start_time: str | None, end_time: str | None,
              category: str, title: str, place: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (ev_date, start_time, end_time, category, title, place) VALUES (?, ?, ?, ?, ?, ?)",
        (ev_date, start_time, end_time, category, title, place),
    )
    conn.commit()
    conn.close()

def delete_event(event_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def fetch_events_in_month(year: int, month: int):
    start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{last_day:02d}"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, ev_date, start_time, end_time, category, title, place FROM events WHERE ev_date BETWEEN ? AND ? ORDER BY ev_date ASC, start_time ASC", (start, end))
    rows = cur.fetchall()
    conn.close()
    by_date = {}
    for r in rows:
        ev = {"id": r[0], "date": r[1], "start": r[2], "end": r[3], "category": r[4], "title": r[5], "place": r[6]}
        by_date.setdefault(ev["date"], []).append(ev)
    return by_date

def format_event_label(ev):
    t = f'{ev["start"]}-{ev["end"]} ' if ev["start"] and ev["end"] else ""
    p = f'{ev["place"]} ' if ev["place"] else ""
    return f"{p}{t}{ev['title']}"

# ---------- ポップアップ (Dialog) ----------
@st.dialog("予定を追加")
def show_add_event_dialog(selected_date):
    st.write(f"📅 **{selected_date}** の予定を入力してください")
    
    category_ui = st.selectbox("種別", ["class（授業）", "job（就活）", "private（遊び）", "work（確定バイト）", "proposal（提案シフト）"])
    cat_map = {"class（授業）": "class", "job（就活）": "job", "private（遊び）": "private", "work（確定バイト）": "work", "proposal（提案シフト）": "proposal"}
    
    all_day = st.checkbox("終日（時間なし）", value=True)
    start_time = end_time = None
    if not all_day:
        col1, col2 = st.columns(2)
        start_time = col1.time_input("開始", value=datetime.strptime("10:00", "%H:%M").time()).strftime("%H:%M")
        end_time = col2.time_input("終了", value=datetime.strptime("12:00", "%H:%M").time()).strftime("%H:%M")

    title = st.text_input("タイトル", placeholder="例：サンマルク")
    place = st.text_input("場所・店名（任意）")

    if st.button("保存する", use_container_width=True):
        if not title.strip():
            st.error("タイトルを入力してください")
        else:
            add_event(selected_date, start_time, end_time, cat_map[category_ui], title.strip(), place.strip() or None)
            st.rerun()

# ---------- main ----------
st.set_page_config(page_title="バイトシフト作成", layout="wide")
init_db()

st.title("📅 バイトシフト作成アプリ")

# 年月選択
today = date.today()
c1, c2 = st.columns(2)
year = c1.number_input("年", 2020, 2035, today.year, 1)
month = c2.selectbox("月", list(range(1, 13)), index=today.month - 1)

# イベント取得
events_by_date = fetch_events_in_month(year, month)

# FullCalendar用のデータ変換
fc_events = []
# カテゴリごとの色設定
colors = {
    "class": "#E8F5E9", "job": "#E3F2FD", "private": "#FCE4EC", 
    "work": "#E0F7FA", "proposal": "#FFF3E0"
}
text_colors = {
    "class": "#1B5E20", "job": "#0D47A1", "private": "#880E4F", 
    "work": "#006064", "proposal": "#E65100"
}

for day_key, evs in events_by_date.items():
    for ev in evs:
        fc_events.append({
            "title": format_event_label(ev),
            "start": f"{day_key}T{ev['start']}:00" if ev["start"] else day_key,
            "end": f"{day_key}T{ev['end']}:00" if ev["end"] else day_key,
            "allDay": not bool(ev["start"]),
            "backgroundColor": colors.get(ev["category"], "#EEEEEE"),
            "textColor": text_colors.get(ev["category"], "#212121"),
            "borderColor": text_colors.get(ev["category"], "#212121"),
        })

# カレンダーの表示オプション
calendar_options = {
    "initialView": "dayGridMonth",
    "locale": "ja",
    "height": 650,
    "headerToolbar": {"left": "", "center": "title", "right": ""},
    "initialDate": f"{year}-{month:02d}-01",
    "selectable": True,
}

# カレンダー描画
state = st_calendar(events=fc_events, options=calendar_options, key="calendar")

# --- クリック判定 (重要) ---
if state and "dateClick" in state:
    clicked_date = state["dateClick"]["date"].split("T")[0]
    show_add_event_dialog(clicked_date)

# ---------- サイドバー (既存機能) ----------
st.sidebar.header("➕ クイック追加")
with st.sidebar.form("side_add"):
    ev_date = st.date_input("日付", value=today)
    category = st.selectbox("種別", ["class", "job", "private", "work", "proposal"])
    title = st.text_input("タイトル")
    submitted = st.form_submit_button("追加")
    if submitted and title:
        add_event(ev_date.strftime("%Y-%m-%d"), None, None, category, title)
        st.rerun()

st.sidebar.divider()
if st.sidebar.button("今週のシフトを1件提案"):
    add_event(today.strftime("%Y-%m-%d"), "18:00", "22:00", "proposal", "提案シフト", "サンマルク")
    st.rerun()

# ---------- 下部：予定一覧 ----------
st.divider()
st.subheader("🗂 予定一覧（削除）")
flat = [ev for evs in events_by_date.values() for ev in evs]
if not flat:
    st.info("予定はありません。カレンダーをクリックして追加してください。")
else:
    for ev in flat:
        cols = st.columns([5, 1])
        cols[0].write(f"**{ev['date']}** | {format_event_label(ev)} | `{ev['category']}`")
        if cols[1].button("削除", key=f"del_{ev['id']}"):
            delete_event(ev["id"])
            st.rerun()
    

