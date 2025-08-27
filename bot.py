# -*- coding: utf-8 -*-
import os, re
from datetime import datetime
from typing import Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

# ======================= Загрузка книги и справочников =======================

# Путь к книге (можно задать переменной окружения K2_PATH)
K2_PATH = os.getenv("K2_PATH", "KeytoFate_arbeiten.txt")

def _load_corpus() -> str:
    """Читает текст книги из K2_PATH или из /app/KeytoFate_arbeiten.txt (для Railway/Docker)."""
    try:
        if os.path.exists(K2_PATH):
            with open(K2_PATH, "r", encoding="utf-8") as f:
                return f.read()
        alt = "/app/KeytoFate_arbeiten.txt"
        if os.path.exists(alt):
            with open(alt, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"[WARN] corpus load error: {e}")
    return ""

CORPUS_TEXT = _load_corpus()

def _extract_numbered_sections(corpus: str, heading_regex: str) -> dict[int, str]:
    """
    Вытягивает блоки по заголовкам вида:
      Geisteszahl 1
      Handlungszahl 8
      Verwirklichungszahl 3
      Ergebniszahl 7
      Gemeinsame Geisteszahl 4
    """
    out: dict[int, str] = {}
    if not corpus:
        return out

    pat = re.compile(heading_regex, re.I | re.M)
    matches = list(pat.finditer(corpus))
    if not matches:
        return out

    for i, m in enumerate(matches):
        try:
            n = int(m.group(1))
        except Exception:
            continue
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(corpus)
        block = corpus[start:end].strip()
        # чистим лишние пустые строки и одиночные нумерации
        block = re.sub(r'\n{3,}', '\n\n', block)
        block = re.sub(r'\n\s*\d+\s*\n', '\n', block)
        out[n] = block
    return out

# Разделы из книги
GEISTES_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Geisteszahl\s+([1-9])\s*$')
HANDLUNGS_FULL = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Handlungszahl\s+([1-9])\s*$')
VERWIRK_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Verwirklichungszahl\s+([1-9])\s*$')
ERGEBNIS_FULL  = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Ergebniszahl\s+([1-9])\s*$')
PARTNER_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Gemeinsame\s+Geisteszahl\s+([1-9])\s*$')

def get_geistes(n: int) -> str:   return (GEISTES_FULL.get(n) or "").strip()
def get_handlungs(n: int) -> str: return (HANDLUNGS_FULL.get(n) or "").strip()
def get_verwirk(n: int) -> str:   return (VERWIRK_FULL.get(n) or "").strip()
def get_ergebnis(n: int) -> str:  return (ERGEBNIS_FULL.get(n) or "").strip()
def get_partner(n: int) -> str:   return (PARTNER_FULL.get(n) or "").strip()

# Короткие аннотации по Geisteszahl (1–9)
GEISTES_TXT: Dict[int, str] = {
    1: "(Menschen, geboren am 1., 10., 19., 28.) — Führung, starker Wille, Initiative.",
    2: "(2., 11., 20., 29.) — Harmonie, Diplomatie, empathisches Verstehen.",
    3: "(3., 12., 21., 30.) — Wissen, Ausdruck, Kreativität.",
    4: "(4., 13., 22., 31.) — Struktur, Ordnung, Ausdauer.",
    5: "(5., 14., 23.) — Bewegung, Kommunikation, Chancen.",
    6: "(6., 15., 24.) — Liebe, Fürsorge, Verantwortung.",
    7: "(7., 16., 25.) — Weisheit, Wahrheit, Disziplin.",
    8: "(8., 17., 26.) — Management, Erfolg, Gerechtigkeit.",
    9: "(9., 18., 27.) — Dienst, Mitgefühl, Vollendung.",
}

# Краткие подписи
HANDLUNG_SHORT = [
    'Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert',
    'Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll',
    'Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'
]
VERWIRK_SHORT = [
    'Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck',
    'Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit',
    'Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'
]
ERGEBNIS_SHORT = [
    'Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung',
    'Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe',
    'Gerechter Erfolg','Dienst & Großzügigkeit'
]

# Tagesenergie 1–9
TAG_TXT = {
    1: "Neuer Zyklus, klare Entscheidungen, erste Schritte.",
    2: "Dialog, Ausgleich, Partnerschaft, ehrliche Gespräche.",
    3: "Kommunikation, Lernen, Reisen, inspirierender Austausch.",
    4: "Struktur, Planung, praktische Arbeit, Ordnung schaffen.",
    5: "Chancen, Bewegung, Netzwerke, flexible Lösungen.",
    6: "Harmonie, Familie, Schönheit, reife Verantwortung.",
    7: "Analyse, Spiritualität, Hygiene des Geistes.",
    8: "Management, Finanzen, Ergebnisse, Leistung.",
    9: "Abschluss, Dienst, Großzügigkeit, Raum für Neues.",
}

# Краткие описания для Kollektivenergie
KOLLEKTIV_TXT = {
    1: "Initiativen, starke Persönlichkeiten, Führung. Vision bündeln, Rollen klären.",
    2: "Verbindend, ausgleichend, Wir-Gefühl. Verantwortung verankern, ehrlich sprechen.",
    3: "Austausch, Ideen, Lernen. Prioritäten & Prozesse halten Fokus.",
    4: "Strukturiert, ausdauernd, stabil. Innovation zulassen, nicht erstarren.",
    5: "Beweglich, chancenorientiert, Netzwerke. Innerer Kompass & Ziele.",
    6: "Sorgend, wertorientiert, ästhetisch. Faire Lasten, Balance Nähe/Freiheit.",
    7: "Forschend, diszipliniert, tief. Ergebnisse teilen, Wissen anwenden.",
    8: "Leistungsstark, zielorientiert, Management. Transparenz & Ethik.",
    9: "Sinnstiftend, humanitär, abschließend. Grenzen wahren, Erholung.",
}

# Полные тексты дней рождения (1–31)
DAY_BIRTH_TXT: Dict[int, str] = {
    1: """Bedeutung des Geburtstages 1 Sie besitzen ein absolut reines Bewusstsein, eine junge Seele...""",
    2: """Bedeutung des Geburtstages 2 Sie sind der beste Ratgeber und Helfer...""",
    3: """Bedeutung des Geburtstages 3 Ihnen steht die Energie des Wissens...""",
    4: """Bedeutung des Geburtstages 4 Ihre Energie besteht aus maximaler Kreativität...""",
    5: """Bedeutung des Geburtstages 5 Sie haben eine feine Wahrnehmung...""",
    6: """Bedeutung des Geburtstages 6 Das Bewusstsein ist darauf ausgerichtet...""",
    7: """Bedeutung des Geburtstages 7 Wahrscheinlich lieben Sie Sport...""",
    8: """Bedeutung des Geburtstages 8 Sie haben die produktivste Energie...""",
    9: """Bedeutung des Geburtstages 9 Ihre Hilfe kennt keine Grenzen...""",
    10: """Bedeutung des Geburtstages 10 Von Geburt an befindet sich...""",
    11: """Bedeutung des Geburtstages 11 Obwohl Sie ein guter Ratgeber...""",
    12: """Bedeutung des Geburtstages 12 Sie teilen die Welt...""",
    13: """Bedeutung des Geburtstages 13 Ihr häufigster Satz lautet...""",
    14: """Bedeutung des Geburtstages 14 Sie sind ein autonomer Mensch...""",
    15: """Bedeutung des Geburtstages 15 Sie erreichen Ihre Ziele...""",
    16: """Bedeutung des Geburtstages 16 Die wichtigste Aufgabe...""",
    17: """Bedeutung des Geburtstages 17 Der beste Weg zur Verwirklichung...""",
    18: """Bedeutung des Geburtstages 18 Obwohl Sie ein sehr fleißiger Mensch...""",
    19: """Bedeutung des Geburtstages 19 Sie sind ein feuriger Führer...""",
    20: """Bedeutung des Geburtstages 20 Nicht selten wird Ihnen...""",
    21: """Bedeutung des Geburtstages 21 Obwohl Sie ein Mensch des Wissens...""",
    22: """Bedeutung des Geburtstages 22 Ihr Bewusstsein strebt...""",
    23: """Bedeutung des Geburtstages 23 Sie verwirklichen sich hervorragend...""",
    24: """Bedeutung des Geburtstages 24 Durch ein tiefes Verständnis...""",
    25: """Bedeutung des Geburtstages 25 Ihre Stärken sind die Geschäftsentwicklung...""",
    26: """Bedeutung des Geburtstages 26 Obwohl Ihre Bestimmung Arbeit...""",
    27: """Bedeutung des Geburtstages 27 Ihre Stärke ist das tiefe Verständnis...""",
    28: """Bedeutung des Geburtstages 28 Ihr Bewusstsein verwirklicht sich...""",
    29: """Bedeutung des Geburtstages 29 Menschen, die an diesem Datum...""",
    30: """Bedeutung des Geburtstages 30 Sie sind ein "ziemlich" listiger Mensch...""",
    31: """Bedeutung des Geburtstages 31 Sie sind ein Mensch mit großem Verstand..."""
}

# ============================== Конфиг токена ===============================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise SystemExit("API_TOKEN is missing. Set it in env.")

# =============================== Утилиты ====================================
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def parse_date(text: str) -> Tuple[int,int,int]:
    m = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    if not m:
        raise ValueError("Bitte Datum im Format TT.MM.JJJJ, z. B. 25.11.1978.")
    d, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    datetime(year=yr, month=mth, day=d)  # validate
    return d, mth, yr

def parse_dates_multi(text: str) -> List[Tuple[int,int,int]]:
    found = re.findall(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    result = []
    for d, mth, yr in found:
        day, month, year = int(d), int(mth), int(yr)
        datetime(year=year, month=month, day=day)
        result.append((day, month, year))
    return result

def reduzieren(n: int, keep_master=True) -> int:
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

# Формулы
def geisteszahl(day: int) -> int: return reduzieren(day)
def handlungszahl(day: int, month: int, year: int) -> int: return reduzieren(sum(int(d) for d in f"{day:02d}{month:02d}{year}"))
def verwirklichungszahl(g: int, h: int) -> int: return reduzieren(g + h)
def ergebniszahl(g: int, h: int, v: int) -> int: return reduzieren(g + h + v)
def geldcode(day: int, month: int, year: int) -> str:
    d1, d2 = reduzieren(day), reduzieren(month)
    d3 = reduzieren(sum(int(d) for d in str(year)))
    d4 = reduzieren(d1 + d2 + d3)
    return f"{d1}{d2}{d3}{d4}"
def tagesenergie(bday_day: int, today_day: int) -> int:
    return reduzieren_1_9(sum(int(d) for d in f"{bday_day:02d}{today_day:02d}"))

# ===================== Кнопка «Назад» + длинные сообщения ====================
def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Zurück zum Menü", callback_data="open_menu")]])

async def send_long_html(update: Update, text: str, with_back: bool = True):
    """Безопасно шлём длинный HTML-текст: режем на части ≤4000 символов."""
    MAX = 4000
    parts = []
    while len(text) > MAX:
        cut = text.rfind("\n\n", 0, MAX)
        if cut == -1:
            cut = text.rfind("\n", 0, MAX)
        if cut == -1:
            cut = MAX
        parts.append(text[:cut])
        text = text[cut:]
    if text:
        parts.append(text)

    if parts:
        await update.message.reply_html(parts[0], reply_markup=back_kb() if with_back else None)
        for p in parts[1:]:
            await update.message.reply_html(p)

# =========================== Состояния и тексты UI ==========================
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

WELCOME = ("🌟 <b>Willkommen!</b>\n\n"
"Vor Ihnen liegt <b>KeyToFate</b> – Lehre über Zahlen und Wege.\n\n"
"✨ Lüften Sie den Schleier Ihres Schicksals – und lassen Sie KeyToFate Ihr Wegweiser sein. ✨")
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse", callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie", callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft", callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie", callback_data="calc_name")],
        [InlineKeyboardButton("👥 Kollektivenergie", callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad", callback_data="calc_path")],
    ])

# ================================ Handlers ==================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; data = q.data
    await q.answer()
    if data=="calc_full":
        await q.message.reply_html("🧮 Geben Sie Geburtsdatum ein (TT.MM.JJJJ):"); return ASK_FULL
    if data=="calc_day":
        await q.message.reply_html("Geben Sie Ihr Geburtsdatum ein (TT.MM.JJJJ):"); return ASK_DAY_BIRTH
    if data=="calc_compat":
        await q.message.reply_html("Geben Sie Geburtsdatum Person 1 ein (TT.MM.JJJJ):"); return ASK_COMPAT_1
    if data=="calc_name":
        await q.message.reply_html("Geben Sie den Namen ein (lateinische Schreibweise):"); return ASK_NAME
    if data=="calc_group":
        context.user_data["group_birthdays"] = []
        await q.message.reply_html("👥 Bis zu 5 Geburtstage eingeben. Schreiben Sie <b>fertig</b>, wenn bereit."); return ASK_GROUP
    if data=="calc_path":
        await q.message.reply_html("🧭 Bitte Geburtsdatum eingeben (TT.MM.JJJJ):"); return ASK_PATH
    return ConversationHandler.END

# ---- Vollanalyse ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip())
        g,h = geisteszahl(d), handlungszahl(d,m,y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d,m,y)

        geist_short = GEISTES_TXT.get(g,"")
        geist_full  = get_geistes(g)
        handl_full  = get_handlungs(h)
        verw_full   = get_verwirk(v)
        erg_full    = get_ergebnis(e)

        day_text = (DAY_BIRTH_TXT.get(d) or "").strip()
        day_block = f"\n\n📅 <b>Bedeutung des Geburtstagstages {d}</b>\n{html_escape(day_text)}" if day_text else ""

        parts = [
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>",
            f"🧠 <b>Geisteszahl {g}</b>\n{html_escape(geist_short)}",
        ]
        if geist_full: parts.append(html_escape(geist_full))
        parts.append(f"\n⚡ <b>Handlungszahl {h}</b>\n{HANDLUNG_SHORT[(h-1)%9]}")
        if handl_full: parts.append(html_escape(handl_full))
        parts.append(f"\n🎯 <b>Verwirklichungszahl {v}</b>\n{VERWIRK_SHORT[(v-1)%9]}")
        if verw_full: parts.append(html_escape(verw_full))
        parts.append(f"\n📘 <b>Ergebniszahl {e}</b>\n{ERGEBNIS_SHORT[(e-1)%9]}")
        if erg_full: parts.append(html_escape(erg_full))
        parts.append(f"\n💰 <b>Geldcode:</b> <code>{geld}</code>")
        if day_block: parts.append(day_block)

        await send_long_html(update, "\n\n".join(parts), with_back=True)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}", reply_markup=back_kb()); return ASK_FULL

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip()); today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        await send_long_html(
            update,
            f"📅 <b>Tagesenergie {today.day:02d}.{today.month:02d}.{today.year}</b>\n\n{html_escape(body)}",
            with_back=True
        )
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}", reply_markup=back_kb()); return ASK_DAY_BIRTH

# ---- Partnerschaft ----
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d1,m1,y1 = parse_date(update.message.text.strip())
    context.user_data["compat1"]=(d1,m1,y1,update.message.text.strip())
    await update.message.reply_html("Jetzt <b>Geburtsdatum Person 2</b> eingeben (TT.MM.JJJJ):", reply_markup=back_kb()); return ASK_COMPAT_2

async def ask_compat2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d2,m2,y2 = parse_date(update.message.text.strip())
    d1,m1,y1,s1 = context.user_data.get("compat1")
    g1,g2 = geisteszahl(d1), geisteszahl(d2)
    common = reduzieren_1_9(g1 + g2)
    long_txt = get_partner(common)
    header = (
        "💞 <b>Partnerschaft</b>\n\n"
        f"<b>Person 1:</b> {s1} → Geisteszahl {g1}\n"
        f"<b>Person 2:</b> {update.message.text.strip()} → Geisteszahl {g2}\n\n"
    )
    body = html_escape(long_txt) if long_txt else f"(Gemeinsame Geisteszahl {common})"
    await send_long_html(update, header + body, with_back=True)
    context.user_data.pop("compat1", None)
    return ConversationHandler.END

# ---- Namensenergie ----
NAME_MAP = {
    **{c:1 for c in "AIJQY"}, **{c:2 for c in "BKR"}, **{c:3 for c in "CLSG"},
    **{c:4 for c in "DMT"}, **{c:5 for c in "EHNX"}, **{c:6 for c in "UVW"},
    **{c:7 for c in "OZ"}, **{c:8 for c in "FP"},
}
def normalize_latin(s: str) -> str:
    return (s.replace("Ä","A").replace("Ö","O").replace("Ü","U")
              .replace("ä","a").replace("ö","o").replace("ü","u")
              .replace("ß","SS"))
def namensenergie(text: str) -> int:
    vals = [NAME_MAP[ch] for ch in normalize_latin(text).upper() if ch in NAME_MAP]
    return reduzieren(sum(vals)) if vals else 0

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name=update.message.text.strip(); val=namensenergie(name)
    await send_long_html(update, f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>", with_back=True)
    return ConversationHandler.END

# ---- Kollektivenergie ----
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=(update.message.text or "").strip()
    if text.lower()=="fertig":
        group=context.user_data.get("group_birthdays",[])
        if len(group)<2:
            await update.message.reply_html("❌ Mindestens 2 Personen.", reply_markup=back_kb()); return ASK_GROUP
        geistes_list=[geisteszahl(d) for d,_,_ in group]
        kollektiv = reduzieren_1_9(sum(geistes_list))
        personen="\n".join(f"• {d:02d}.{m:02d}.{y} → Geisteszahl {g}" for (d,m,y),g in zip(group,geistes_list))
        txt = KOLLEKTIV_TXT.get(kollektiv, "Dieses Kollektiv entfaltet eine besondere Dynamik und Lernaufgabe.")
        await send_long_html(update, f"👥 <b>Kollektivenergie</b>\n\n{personen}\n\n<b>Zahl:</b> {kollektiv}\n\n{html_escape(txt)}", with_back=True)
        return ConversationHandler.END
    parsed=parse_dates_multi(text)
    group=context.user_data.setdefault("group_birthdays",[])
    group.extend(parsed)
    await update.message.reply_html(f"✅ Hinzugefügt: {len(parsed)}. Tippen Sie <b>fertig</b>."); return ASK_GROUP

# ---- Entwicklungspfad ----
ENTWICKLUNGSPFAD = {
    1: "Die 1 reift zur 4 — über Beziehung (2) und Ausdruck (3): aus Impuls werden Disziplin und Struktur.",
    2: "Die 2 strebt zur 5 — über Wissen/Kommunikation (3) und Ordnung (4): Harmonie wird zu bewusster Freiheit.",
    3: "Die 3 entfaltet sich zur 6 — über Struktur (4) und Wandel (5): Kreativität wird zu reifer Verantwortung.",
    4: "Die 4 wächst zur 7 — über Freiheit (5) und Liebe/Verantwortung (6): Ordnung wird zu innerer Weisheit.",
    5: "Die 5 strebt zur 8 — über 6 und 7: Liebe/Verantwortung → Wahrheit/Disziplin → gerechter Erfolg.",
    6: "Die 6 geht zur 9 — über Tiefgang (7) und Macht/Erfolg (8): zur universellen Liebe und zum Dienst.",
    7: "Die 7 geht zur 1 — über 8 und 9: Disziplin & Macht, dann Abschluss & Dienst hin zur reifen Führung.",
    8: "Die 8 strebt zur 2 — über 9 und 1: von Macht zu Kooperation und Diplomatie.",
    9: "Die 9 findet zur 3 — über 1 und 2: Dienst & Vollendung führen zu schöpferischem Ausdruck.",
}
ZU_VERMEIDEN = {
    1: "Ego-Alleingänge, Ungeduld, Dominanz.",
    2: "Unentschlossenheit, konfliktscheues Schweigen, Selbstverleugnung.",
    3: "Zerstreuung, zu viele Projekte, Oberflächlichkeit.",
    4: "Überstrenge Routinen, Dogmatismus, Detailkontrolle.",
    5: "Reizjagd, Hektik, Flucht in Abwechslung, Bindungsangst.",
    6: "Überverantwortung, Einmischung, subtile Schuldgefühle.",
    7: "Isolation, endloses Zweifeln, Theorie ohne Praxis.",
    8: "Machtspiele, Mikromanagement, Erfolgsfixierung.",
    9: "Selbstaufopferung, diffuse Ziele, Grenzenlosigkeit.",
}

async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d,m,y=parse_date(update.message.text.strip()); g=geisteszahl(d)
    out=(f"🧭 <b>Entwicklungspfad (aus Geisteszahl {g})</b>\n\n"
         f"{ENTWICKLUNGSPFAD.get(g,'')}\n\n"
         f"⚠️ <b>Zu vermeiden:</b> {ZU_VERMEIDEN.get(g,'')}")
    await send_long_html(update, out, with_back=True); return ConversationHandler.END

# =============================== Bootstrap ==================================
def main():
    app = Application.builder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))
    conv=ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
          ASK_FULL:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full)],
          ASK_DAY_BIRTH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
          ASK_COMPAT_1:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1)],
          ASK_COMPAT_2:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2)],
          ASK_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
          ASK_GROUP:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group)],
          ASK_PATH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_path)],
        }, fallbacks=[CommandHandler("start", start)], allow_reentry=True
    )
    app.add_handler(conv)
    print("🤖 KeyToFate läuft. /start → Menü.")
    app.run_polling()

if __name__=="__main__":
    main()
