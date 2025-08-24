from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, date
from typing import Tuple, List, Dict

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# ========================= ПРОБНАЯ ВЕРСИЯ =========================
API_TOKEN = '8307912076:AAG6neSMpuFIVFmTY0Pi-rHco66Tqn94uwo'
# ================================================================

# ---------- DONATE & ANALYTICS ----------
DONATE_EMAIL = "manzera@mail.ru"
PAYPAL_URL = "https://www.paypal.com/donate?business=manzera%40mail.ru"

# Включатели функций (если что-то не работает на хостинге — просто выключи)
SHOW_DONATE = True           # показать/скрыть кнопку и текст доната
ANALYTICS_ENABLED = True     # включить/выключить запись статистики в файл

ANALYTICS_PATH = "analytics.json"
RETAIN_DAYS = 90
ADMIN_IDS = {6480688287}     # твой Telegram ID

MEISTER_ERHALTEN = True
DATE_REGEX = r'^\s*(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})\s*$'

# ----------------------------- Utils -----------------------------
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def is_admin(update: Update) -> bool:
    u = update.effective_user
    return bool(u and (u.id in ADMIN_IDS))

def parse_date(text: str) -> Tuple[int,int,int]:
    m = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    if not m:
        raise ValueError("Bitte Datum im Format TT.MM.JJJJ angeben, z. B. 25.11.1978.")
    d, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    datetime(year=yr, month=mth, day=d)  # validate
    return d, mth, yr

def parse_dates_multi(text: str) -> List[Tuple[int,int,int]]:
    pattern = r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})'
    found = re.findall(pattern, text)
    result = []
    for d, mth, yr in found:
        day, month, year = int(d), int(mth), int(yr)
        datetime(year=year, month=month, day=day)
        result.append((day, month, year))
    return result

def reduzieren(n: int, keep_master: bool = MEISTER_ERHALTEN) -> int:
    while n > 9:
        s = sum(int(d) for d in str(n))
        if keep_master and s in (11, 22, 33):
            return s
        n = s
    return n

def reduzieren_1_9(n: int) -> int:
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n

# ------------------------- Формулы -----------------------
def geisteszahl(day: int) -> int:
    return reduzieren(day)

def handlungszahl(day: int, month: int, year: int) -> int:
    total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
    return reduzieren(total)

def verwirklichungszahl(g: int, h: int) -> int:
    return reduzieren(g + h)

def ergebniszahl(g: int, h: int, v: int) -> int:
    s = g + h + v
    return reduzieren(s)

def geldcode(day: int, month: int, year: int) -> str:
    d1 = reduzieren(day)
    d2 = reduzieren(month)
    d3 = reduzieren(sum(int(d) for d in str(year)))
    d4 = reduzieren(d1 + d2 + d3)
    return f"{d1}{d2}{d3}{d4}"

def tagesenergie(bday_day: int, today_day: int) -> int:
    return reduzieren_1_9(sum(int(d) for d in f"{bday_day:02d}{today_day:02d}"))

# ---------------------- Namensenergie ---------------------
NAME_MAP = {
    **{c:1 for c in "AIJQY"},
    **{c:2 for c in "BKR"},
    **{c:3 for c in "CLSG"},
    **{c:4 for c in "DMT"},
    **{c:5 for c in "EHNX"},
    **{c:6 for c in "UVW"},
    **{c:7 for c in "OZ"},
    **{c:8 for c in "FP"},
}
def normalize_latin(s: str) -> str:
    return (s.replace("Ä","A").replace("Ö","O").replace("Ü","U")
              .replace("ä","a").replace("ö","o").replace("ü","u")
              .replace("ß","SS"))

def namensenergie(text: str) -> int:
    t = normalize_latin(text)
    vals = [NAME_MAP[ch] for ch in t.upper() if ch in NAME_MAP]
    return reduzieren(sum(vals)) if vals else 0

# ---------------------- Тексты (коротко; длинные вставишь сам) ----------------------
GEISTES_TXT = {
    1: """(Menschen, geboren am 1., 10., 19., 28. eines Monats):

Sie sind ein geborener Anführer, eine sehr starke Person mit großem Willen. Sie handeln schnell, lieben es, Verantwortung zu übernehmen und neue Wege zu eröffnen.""",
    2: """(Menschen, geboren am 2., 11., 20., 29. eines Monats):

Sie sind in diese Welt gekommen, um sich durch Verständnis und Beziehungen zu verwirklichen. Ihre Stärke liegt in Harmonie, Diplomatie und der Fähigkeit, andere zu fühlen.""",
    3: """(Menschen, geboren am 3., 12., 21., 30. eines Monats):

Sie sind Träger von Wissen und natürlicher Kreativität. Sie lernen schnell, vermitteln Inhalte leicht und inspirieren andere durch Wort und Ausdruck.""",
    4: """(Menschen, geboren am 4., 13., 22., 31. eines Monats):

Sie sind der/die Erbauer:in — Struktur, Ordnung und Ausdauer prägen Ihren Weg.""",
    5: """(Menschen, geboren am 5., 14. oder 23. eines Monats):

Sie sind ein pragmatischer Mensch, lieben konsequentes Handeln, Bewegung und Kommunikation.""",
    6: """(Menschen, geboren am 6., 15. oder 24. eines Monats):

Sie sind in diese Welt gekommen, um Liebe, Schönheit und Verantwortung zu leben.""",
    7: """(Menschen, geboren am 7., 16. oder 25. eines Monats):

Sie verkörpern Analyse, Weisheit und innere Tiefe.""",
    8: """(Menschen, geboren am 8., 17. oder 26. eines Monats):

Sie sind in diese Welt gekommen, um alles zu kontrollieren — Management, Erfolg und gerechte Führung.""",
    9: """(Menschen, geboren am 9., 18. oder 27. eines Monats):

In Ihnen ist die Energie des Dienens und der Vollendung angelegt.""",
}

# Полные тексты — вставишь сам
GEISTES_FULL_TXT: Dict[int, str] = {i: "" for i in range(1,10)}

# День рождения 1..31 — вставишь сам (сейчас примерные заглушки)
DAY_BIRTH_TXT: Dict[int, str] = {1: "Bedeutung des Geburtstages 1 ...", 2: "Bedeutung des Geburtstages 2 ..."}
for k in range(3, 32):
    DAY_BIRTH_TXT.setdefault(k, f"Bedeutung des Geburtstages {k} ...")

# Tagesenergie 1..9 — вставишь сам
TAG_TXT: Dict[int, str] = {i: f"📅 Tagesenergie {i}\n\n** – ..." for i in range(1,10)}

# Partnerschaft
PARTNERSCHAFT_TXT = {
    1: ("💞 Partnerschaft 1\n\nZwei Führungsenergien bringen Funken, Tempo und Schaffenskraft."),
    2: ("💞 Partnerschaft 2\n\nZart, empathisch, harmonieorientiert."),
    3: ("💞 Partnerschaft 3\n\nLebendig, inspirierend, voller Kommunikation."),
    4: ("💞 Partnerschaft 4\n\nPraktisch und stabil."),
    5: ("💞 Partnerschaft 5\n\nKommunikativ, beweglich, abenteuerlustig."),
    6: ("💞 Partnerschaft 6\n\nLiebe, Fürsorge, Verantwortung."),
    7: ("💞 Partnerschaft 7\n\nTiefe, Transformation, innere Arbeit."),
    8: ("💞 Partnerschaft 8\n\nMachtvoll, zielorientiert, ergebnisstark."),
    9: ("💞 Partnerschaft 9\n\nReif, sinnstiftend, überpersönlich."),
}

# Kollektiv & Pfad
KOLLEKTIV_TXT = {i: f"👥 Kollektivenergie {i}\n\n..." for i in range(1,10)}
ENTWICKLUNGSPFAD = {
    1: "Die 1 reift zur 4 — über 2 und 3.",
    2: "Die 2 strebt zur 5 — über 3 und 4.",
    3: "Die 3 entfaltet sich zur 6 — über 4 und 5.",
    4: "Die 4 wächst zur 7 — über 5 und 6.",
    5: "Die 5 strebt zur 8 — über 6 und 7.",
    6: "Die 6 geht zur 9 — über 7 und 8.",
    7: "Die 7 geht zur 1 — über 8 und 9.",
    8: "Die 8 strebt zur 2 — über 9 und 1.",
    9: "Die 9 findet zur 3 — über 1 und 2.",
}
ZU_VERMEIDEN = {
    1: "Ego-Alleingänge, Ungeduld.",
    2: "Unentschlossenheit, konfliktscheues Schweigen.",
    3: "Zerstreuung, zu viele Projekte.",
    4: "Überstrenge Routinen, Dogmatismus.",
    5: "Reizjagd, Hektik, Bindungsangst.",
    6: "Überverantwortung, Einmischung.",
    7: "Isolation, endloses Zweifeln.",
    8: "Machtspiele, Erfolgsfixierung.",
    9: "Selbstaufopferung, diffuse Ziele.",
}

# ----------------------------- DONATE UI ------------------------------
DONATE_TEXT = (
    ("\n\n🙏 <b>Unterstützen Sie KeyToFate</b>\n"
     "Wenn Ihnen dieses Projekt gefällt, können Sie es mit einer Spende unterstützen.\n"
     f"PayPal: <b>{html_escape(DONATE_EMAIL)}</b>\n"
     "<i>Vielen Dank für Ihre Hilfe!</i>") if SHOW_DONATE else ""
)

def donate_keyboard(extra_rows: List[List[InlineKeyboardButton]] | None = None,
                   show_stats_button: bool = False,
                   is_admin_user: bool = False) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    if extra_rows:
        rows.extend(extra_rows)
    if SHOW_DONATE:
        rows.append([InlineKeyboardButton("💖 Spende (PayPal)", url=PAYPAL_URL)])
    if show_stats_button and ANALYTICS_ENABLED and is_admin_user:
        rows.append([InlineKeyboardButton("📊 Statistik", callback_data="show_stats")])
    rows.append([InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)

def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")]])

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse",     callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie",    callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft",   callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie",   callback_data="calc_name")],
        [InlineKeyboardButton("👥 Kollektivenergie",callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad",callback_data="calc_path")],
    ])

def menu_with_donate_keyboard(is_admin_user: bool) -> InlineKeyboardMarkup:
    base = [row[:] for row in main_menu().inline_keyboard]
    extra: List[List[InlineKeyboardButton]] = []
    if SHOW_DONATE:
        extra.append([InlineKeyboardButton("💖 Spende (PayPal)", url=PAYPAL_URL)])
    if ANALYTICS_ENABLED and is_admin_user:
        extra.append([InlineKeyboardButton("📊 Statistik", callback_data="show_stats")])
    return InlineKeyboardMarkup(base + extra)

# ----------------------------- ANALYTICS ------------------------------
def _now_iso() -> str: return datetime.now().isoformat(timespec="seconds")
def _today_str() -> str: return datetime.now().date().isoformat()

def load_analytics() -> dict:
    try:
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_events": 0, "users": {}, "by_date": {}}

def _rotate_analytics(data: dict) -> dict:
    try:
        cutoff = date.today() - timedelta(days=RETAIN_DAYS)
        by_date = data.get("by_date", {})
        data["by_date"] = {d:rec for d,rec in by_date.items()
                           if (re.match(r"\d{4}-\d{2}-\d{2}", d) and date.fromisoformat(d) >= cutoff)}
    except Exception:
        pass
    return data

def save_analytics(data: dict) -> None:
    try:
        data = _rotate_analytics(data)
        with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] analytics save failed: {e}")

def track_event(update: Update, kind: str) -> None:
    if not ANALYTICS_ENABLED:
        return
    try:
        user = update.effective_user
        if not user:
            return
        uid = str(user.id)
        uname = (user.username or "")[:64]
        data = load_analytics()
        data["total_events"] = int(data.get("total_events", 0)) + 1

        users = data.setdefault("users", {})
        urec = users.get(uid, {"username": uname, "first_seen": _now_iso(),
                               "last_seen": _now_iso(), "events": 0})
        urec["username"] = uname or urec.get("username","")
        urec["last_seen"] = _now_iso()
        urec["events"] = int(urec.get("events", 0)) + 1
        users[uid] = urec

        day = _today_str()
        by_date = data.setdefault("by_date", {})
        drec = by_date.get(day, {"events": 0, "unique_users": []})
        drec["events"] = int(drec.get("events", 0)) + 1
        if uid not in drec.get("unique_users", []):
            drec["unique_users"].append(uid)
        by_date[day] = drec

        data["users"] = users
        data["by_date"] = by_date
        save_analytics(data)
    except Exception as e:
        print(f"[WARN] track_event failed: {e}")

def format_stats() -> str:
    data = load_analytics()
    total_events = int(data.get("total_events", 0))
    users = data.get("users", {})
    total_users = len(users)
    by_date = data.get("by_date", {})
    today = _today_str()
    today_rec = by_date.get(today, {"events": 0, "unique_users": []})
    today_events = int(today_rec.get("events", 0))
    today_unique = len(today_rec.get("unique_users", []))

    last7_events = 0
    uniq7 = set()
    t = datetime.now().date()
    for i in range(7):
        d = (t - timedelta(days=i)).isoformat()
        rec = by_date.get(d, {})
        last7_events += int(rec.get("events", 0))
        uniq7.update(rec.get("unique_users", []))

    text = (
        "📊 <b>KeyToFate – Statistik</b>\n\n"
        f"👥 Benutzer gesamt: <b>{total_users}</b>\n"
        f"🧮 Ereignisse gesamt: <b>{total_events}</b>\n\n"
        f"📅 Heute ({today}):\n"
        f"   • Ereignisse: <b>{today_events}</b>\n"
        f"   • Einzigartige Benutzer: <b>{today_unique}</b>\n\n"
        f"🗓️ Letzte 7 Tage (inkl. heute):\n"
        f"   • Ereignisse: <b>{last7_events}</b>\n"
        f"   • Einzigartige Benutzer: <b>{len(uniq7)}</b>\n"
    )
    return text

def export_csv_files() -> List[tuple[str, bytes]]:
    data = load_analytics()
    by_date = data.get("by_date", {})
    users = data.get("users", {})

    buf1 = io.StringIO()
    w1 = csv.writer(buf1)
    w1.writerow(["date", "events", "unique_users_count", "unique_users_ids"])
    for dstr in sorted(by_date.keys()):
        rec = by_date[dstr]
        events = int(rec.get("events", 0))
        uu = rec.get("unique_users", [])
        w1.writerow([dstr, events, len(uu), " ".join(uu)])
    f1 = ("analytics_by_date.csv", buf1.getvalue().encode("utf-8"))

    buf2 = io.StringIO()
    w2 = csv.writer(buf2)
    w2.writerow(["user_id", "username", "first_seen", "last_seen", "events"])
    for uid, urec in users.items():
        w2.writerow([
            uid,
            urec.get("username",""),
            urec.get("first_seen",""),
            urec.get("last_seen",""),
            int(urec.get("events",0))
        ])
    f2 = ("analytics_users.csv", buf2.getvalue().encode("utf-8"))
    return [f1, f2]

# ----------------------------- Меню/состояния ------------------------------
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

WELCOME = (
    "🌟 <b>Liebe Freunde!</b>\n\n"
    "Vor Ihnen liegt ein einzigartiges Wissen: <b>KeyToFate</b> – der Schlüssel zu sich selbst und zu allem.\n"
    "Es hilft, Ihr wahres Potenzial zu entfalten und Harmonie mit sich und der Welt zu finden.\n\n"
    "Ihr Geburtsdatum birgt erstaunliche Erkenntnisse über Persönlichkeit und Bestimmung. "
    "Wer diese Gesetze versteht, entfaltet Talente und findet den eigenen Weg.\n\n"
    "✨ Lüften Sie den Schleier Ihres Schicksals – und lassen Sie KeyToFate Ihr Wegweiser zum Glück sein. ✨"
)
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

# ---------------------------- Handlers ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "start")
    # ТОЛЬКО приветствие и кнопка «Zum Menü»
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]
    ])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    track_event(update, "back_menu")
    kb = menu_with_donate_keyboard(is_admin(update))
    await q.message.reply_html(MENU_HEADER, reply_markup=kb)
    return ConversationHandler.END

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "menu")
    kb = menu_with_donate_keyboard(is_admin(update))
    await update.message.reply_html(MENU_HEADER, reply_markup=kb)

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()
    track_event(update, data)
    if data == "calc_full":
        await q.message.reply_html("🧮 Geben Sie das <b>Geburtsdatum</b> für die Vollanalyse ein (TT.MM.JJJJ):",
                                   reply_markup=back_menu_kb())
        return ASK_FULL
    if data == "calc_day":
        await q.message.reply_html("Geben Sie Ihr <b>Geburtsdatum</b> ein (TT.MM.JJJJ):",
                                   reply_markup=back_menu_kb())
        return ASK_DAY_BIRTH
    if data == "calc_compat":
        await q.message.reply_html("Geben Sie <b>Geburtsdatum Person 1</b> ein (TT.MM.JJJJ):",
                                   reply_markup=back_menu_kb())
        return ASK_COMPAT_1
    if data == "calc_name":
        await q.message.reply_html("Geben Sie den <b>Namen</b> ein (lateinische Schreibweise):",
                                   reply_markup=back_menu_kb())
        return ASK_NAME
    if data == "calc_group":
        context.user_data["group_birthdays"] = []
        await q.message.reply_html(
            "👥 Bitte bis zu 5 Geburtstage eingeben.\n"
            "• Sie können <b>mehrere</b> in <u>einer</u> Nachricht senden.\n"
            "• Formate: <code>12.12.1999 13.12.1999</code> oder <code>12 12 1999, 13 12 1999</code> oder pro Zeile.\n"
            "Wenn fertig, tippen Sie <b>fertig</b>.",
            reply_markup=back_menu_kb()
        )
        return ASK_GROUP
    if data == "calc_path":
        await q.message.reply_html(
            "🧭 <b>Entwicklungspfad</b>\n"
            "Bitte geben Sie Ihr <b>Geburtsdatum</b> ein (TT.MM.JJJJ). "
            "Der Pfad wird aus Ihrer <b>Geisteszahl</b> berechnet.",
            reply_markup=back_menu_kb()
        )
        return ASK_PATH

# ---- Vollanalyse ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "ask_full")
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        extra = [[InlineKeyboardButton(f"📖 Mehr lesen über {g}", callback_data=f"more_g{g}")]]
        kb = donate_keyboard(extra_rows=extra,
                             show_stats_button=True,
                             is_admin_user=is_admin(update))

        day_text = DAY_BIRTH_TXT.get(d, "").strip()
        day_block = f"📅 <b>Bedeutung des Geburtstagstages {d}</b>\n{html_escape(day_text)}\n\n" if day_text else ""

        out = (
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>\n\n"
            f"🧠 <b>Geisteszahl:</b> {g}\n{html_escape(GEISTES_TXT.get(g,'').strip())}\n\n"
            + day_block +
            f"⚡ <b>Handlungszahl:</b> {h}\n"
            f"{['Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert','Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll','Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'][(h-1)%9]}\n\n"
            f"🎯 <b>Verwirklichungszahl:</b> {v}\n"
            f"{['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'][(v-1)%9]}\n\n"
            f"📘 <b>Ergebniszahl:</b> {e}\n"
            f"{['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit'][(e-1)%9]}\n\n"
            f"💰 <b>Geldcode:</b> <code>{geld}</code>"
            + DONATE_TEXT
        )
        await update.message.reply_html(out, reply_markup=kb)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBeispiel: <code>25.11.1978</code>",
                                        reply_markup=back_menu_kb())
        return ASK_FULL

# ---- Callback: Mehr lesen über Geisteszahl X ----
async def read_more_geist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    track_event(update, "more_geist")
    try:
        data = q.data
        g = int(data.replace("more_g", ""))
        full = (GEISTES_FULL_TXT.get(g) or "").strip()
        if not full:
            await q.message.reply_html("Für diese Zahl liegt kein erweiterter Text vor.",
                                       reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
            return
        await q.message.reply_html(f"📖 <b>Geisteszahl {g}</b>\n\n{html_escape(full)}" + DONATE_TEXT,
                                   reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
    except Exception as e:
        await q.message.reply_html(f"❌ {html_escape(str(e))}",
                                   reply_markup=donate_keyboard(is_admin_user=is_admin(update)))

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "ask_day")
    try:
        d, m, y = parse_date(update.message.text.strip())
        today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        out = (
            f"📅 <b>Tagesenergie für {today.day:02d}.{today.month:02d}.{today.year}:</b>\n\n"
            f"{html_escape(body.strip())}"
            + DONATE_TEXT
        )
        await update.message.reply_html(out, reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nVersuchen Sie erneut (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_DAY_BIRTH

# ---- Partnerschaft ----
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "compat_1")
    try:
        d1, m1, y1 = parse_date(update.message.text.strip())
        context.user_data["compat1"] = (d1, m1, y1, update.message.text.strip())
        await update.message.reply_html("Jetzt <b>Geburtsdatum Person 2</b> eingeben (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_COMPAT_2
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBitte erneut Person 1 (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_COMPAT_1

async def ask_compat2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "compat_2")
    try:
        if "compat1" not in context.user_data:
            await update.message.reply_html(
                "Die erste Eingabe fehlt. Bitte neu starten: <b>Geburtsdatum Person 1</b> (TT.MM.JJJJ).",
                reply_markup=back_menu_kb()
            )
            return ASK_COMPAT_1

        d2, m2, y2 = parse_date(update.message.text.strip())
        d1, m1, y1, s1 = context.user_data.get("compat1")
        g1 = geisteszahl(d1)
        g2 = geisteszahl(d2)
        common = reduzieren_1_9(g1 + g2)

        text = (
            "💞 <b>Partnerschaft</b>\n\n"
            f"<b>Person 1:</b> {html_escape(s1)} → Geisteszahl {g1}\n"
            f"<b>Person 2:</b> {html_escape(update.message.text.strip())} → Geisteszahl {g2}\n\n"
            f"{PARTNERSCHAFT_TXT.get(common,'Eine interessante Verbindung mit Entwicklungspotenzial.')}"
            + DONATE_TEXT
        )
        await update.message.reply_html(text, reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
        context.user_data.pop("compat1", None)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBitte erneut Person 2 (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_COMPAT_2

# ---- Namensenergie ----
NAMENS_TXT = {
    1: ("Die Namensenergie 1: Wille, Initiative, Führung."),
    2: ("Die Namensenergie 2: Harmonie, Diplomatie, Ausgleich."),
    3: ("Die Namensenergie 3: Kreativität, Wissen, Ausdruck."),
    4: ("Die Namensenergie 4: Struktur, Ordnung, Ausdauer."),
    5: ("Die Namensenergie 5: Freiheit, Bewegung, Wandel."),
    6: ("Die Namensenergie 6: Liebe, Fürsorge, Verantwortung."),
    7: ("Die Namensenergie 7: Weisheit, Analyse, Wahrheit."),
    8: ("Die Namensenergie 8: Erfolg, Autorität, Management."),
    9: ("Die Namensenergie 9: Dienst, Humanität, Vollendung."),
}
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "ask_name")
    name = update.message.text.strip()
    val = namensenergie(name)
    beschreibung = NAMENS_TXT.get(val, "Keine Beschreibung gefunden.")
    await update.message.reply_html(
        f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>\n\n"
        f"{beschreibung}"
        + DONATE_TEXT,
        reply_markup=donate_keyboard(is_admin_user=is_admin(update))
    )
    return ConversationHandler.END

# ---- Kollektivenergie ----
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "group")
    text = (update.message.text or "").strip()

    if text.lower() == "fertig":
        group = context.user_data.get("group_birthdays", [])
        if len(group) < 2:
            await update.message.reply_html("❌ Mindestens 2 Personen eingeben.",
                                            reply_markup=back_menu_kb())
            return ASK_GROUP

        geistes_list = [geisteszahl(d) for d,_,_ in group]
        summe = sum(geistes_list)
        kollektiv = reduzieren_1_9(summe)

        personen_txt = "\n".join(
            f"• Person {i+1}: {d:02d}.{m:02d}.{y} → Geisteszahl {g}"
            for i, ((d,m,y), g) in enumerate(zip(group, geistes_list))
        )

        pfad_txt = ENTWICKLUNGSPFAD.get(kollektiv, "")
        avoid_txt = ZU_VERMEIDEN.get(kollektiv, "")

        out = (
            "👥 <b>Kollektivenergie</b>\n\n"
            f"{personen_txt}\n\n"
            f"{KOLLEKTIV_TXT.get(kollektiv,'Dieses Kollektiv entfaltet eine besondere Dynamik und Lernaufgabe.')}\n\n"
            + (f"🧭 <b>Entwicklungspfad (Kollektiv):</b> {pfad_txt}\n" if pfad_txt else "") +
            (f"⚠️ <b>Zu vermeiden:</b> {avoid_txt}\n" if avoid_txt else "")
            + DONATE_TEXT
        )
        await update.message.reply_html(out, reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
        return ConversationHandler.END

    try:
        parsed = parse_dates_multi(text)
        if not parsed:
            raise ValueError("Bitte Datum im Format TT.MM.JJJJ angeben, z. B. 25.11.1978.")

        group = context.user_data.setdefault("group_birthdays", [])
        rest = 5 - len(group)
        if rest <= 0:
            await update.message.reply_html("⚠️ Es sind schon 5 Personen gespeichert. Tippen Sie <b>fertig</b>.",
                                            reply_markup=back_menu_kb())
            return ASK_GROUP

        to_add = parsed[:rest]
        group.extend(to_add)

        added_msg = "\n".join(f"• {d:02d}.{m:02d}.{y}" for d,m,y in to_add)
        left = 5 - len(group)

        if left == 0:
            await update.message.reply_html(
                f"✅ Hinzugefügt:\n{added_msg}\n\n"
                "Maximal 5 Personen erreicht. Tippen Sie <b>fertig</b> für die Berechnung.",
                reply_markup=back_menu_kb()
            )
            return ASK_GROUP

        await update.message.reply_html(
            f"✅ Hinzugefügt:\n{added_msg}\n\n"
            f"Gesamt: {len(group)} Person(en). "
            f"Noch {left} möglich. Geben Sie weitere Geburtstage ein oder tippen Sie <b>fertig</b>.",
            reply_markup=back_menu_kb()
        )
        return ASK_GROUP

    except Exception as ex:
        await update.message.reply_html(
            f"❌ {html_escape(str(ex))}\n"
            "Beispiele: <code>12.12.1999 13.12.1999</code> oder <code>12 12 1999, 13 12 1999</code>.",
            reply_markup=back_menu_kb()
        )
        return ASK_GROUP

# ---- Entwicklungspfad ----
async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_event(update, "ask_path")
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        pfad = ENTWICKLUNGSPFAD.get(g, "")
        avoid = ZU_VERMEIDEN.get(g, "")
        out = (
            f"🧭 <b>Entwicklungspfad (aus Geisteszahl {g})</b>\n\n"
            f"{pfad}\n\n"
            + (f"⚠️ <b>Zu vermeiden:</b> {avoid}" if avoid else "")
            + DONATE_TEXT
        )
        await update.message.reply_html(out, reply_markup=donate_keyboard(is_admin_user=is_admin(update)))
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(
            f"❌ {html_escape(str(ex))}\nBitte erneut Datum im Format <code>TT.MM.JJJJ</code> eingeben.",
            reply_markup=back_menu_kb()
        )
        return ASK_PATH

# ---- Vollanalyse при простом вводе даты (фоллбек) ----
async def full_analysis_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.startswith("/"):
        return
    track_event(update, "fallback")
    try:
        d, m, y = parse_date(text)
        g = geisteszahl(d)
        h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        day_text = DAY_BIRTH_TXT.get(d, "").strip()
        day_block = f"📅 <b>Bedeutung des Geburtstagstages {d}</b>\n{html_escape(day_text)}\n\n" if day_text else ""

        extra = [[InlineKeyboardButton(f"📖 Mehr lesen über {g}", callback_data=f"more_g{g}")]]
        kb = donate_keyboard(extra_rows=extra,
                             show_stats_button=True,
                             is_admin_user=is_admin(update))

        out = (
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>\n\n"
            f"🧠 <b>Geisteszahl:</b> {g}\n{html_escape(GEISTES_TXT.get(g,'').strip())}\n\n"
            + day_block +
            f"⚡ <b>Handlungszahl:</b> {h}\n"
            f"{['Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert','Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll','Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'][(h-1)%9]}\n\n"
            f"🎯 <b>Verwirklichungszahl:</b> {v}\n"
            f"{['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'][(v-1)%9]}\n\n"
            f"📘 <b>Ergebniszahl:</b> {e}\n"
            f"{['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit'][(e-1)%9]}\n\n"
            f"💰 <b>Geldcode:</b> <code>{geld}</code>"
            + DONATE_TEXT
        )
        await update.message.reply_html(out, reply_markup=kb)
    except Exception:
        pass

# ---- СТАТИСТИКА: команды ----
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_html("⛔ Sie haben keine Berechtigung für /stats.",
                                        reply_markup=back_menu_kb())
        return
    text = format_stats()
    await update.message.reply_html(text, reply_markup=donate_keyboard(is_admin_user=True))

async def export_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_html("⛔ Sie haben keine Berechtigung für /export_stats.",
                                        reply_markup=back_menu_kb())
        return
    for fname, content in export_csv_files():
        bio = io.BytesIO(content); bio.name = fname
        await update.message.reply_document(InputFile(bio), caption=fname)

# ---- Callback “📊 Statistik” ----
async def show_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        await q.message.reply_html("⛔ Sie haben keine Berechtigung.", reply_markup=back_menu_kb())
        return
    text = format_stats()
    await q.message.reply_html(text, reply_markup=donate_keyboard(is_admin_user=True))

# ---------------------------- Bootstrap ----------------------------
def main():
    app = Application.builder().token(API_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("export_stats", export_stats_cmd))

    # ВАЖНО: кнопки открытия/назад — регистрируем ГЛОБАЛЬНО
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))

    # Диалоговое меню
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
            ASK_FULL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_DAY_BIRTH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_COMPAT_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_COMPAT_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_GROUP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_PATH:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_path),
                           CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
        },
        fallbacks=[CommandHandler("menu", menu_cmd)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # Гарантируем, что «Zurück» поймается даже вне состояний
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_menu$"), group=1)

    # Callback «Mehr lesen»
    app.add_handler(CallbackQueryHandler(read_more_geist, pattern=r"^more_g[1-9]$"))
    # Статистика (кнопка)
    app.add_handler(CallbackQueryHandler(show_stats_callback, pattern=r"^show_stats$"))

    # Фоллбек: если просто прислали дату — Vollanalyse
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, full_analysis_fallback))

    print("🤖 KeyToFate läuft. /start → приветствие, затем «Zum Menü». Меню содержит донат-кнопку внизу. /stats и /export_stats — только для админа.")
    app.run_polling()

if __name__ == "__main__":
    main()
