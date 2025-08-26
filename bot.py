# -*- coding: utf-8 -*-
from __future__ import annotations

import os, re
from datetime import datetime
from typing import Tuple, List, Dict

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

# ========================= API TOKEN =========================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
# =============================================================

# ----------------------------- Utils -----------------------------
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

def idx_1_9(n: int) -> int:
    return n if 1 <= n <= 9 else reduzieren_1_9(n)

# ------------------------- Формулы -----------------------
def geisteszahl(day: int) -> int: return reduzieren(day)
def handlungszahl(day: int, month: int, year: int) -> int: return reduzieren(sum(int(d) for d in f"{day:02d}{month:02d}{year}"))
def verwirklichungszahl(g: int, h: int) -> int: return reduzieren(g + h)
def ergebniszahl(g: int, h: int, v: int) -> int: return reduzieren(g + h + v)
def geldcode(day: int, month: int, year: int) -> str:
    d1, d2 = reduzieren(day), reduzieren(month)
    d3 = reduzieren(sum(int(d) for d in str(year)))
    d4 = reduzieren(d1 + d2 + d3)
    return f"{d1}{d2}{d3}{d4}"
def tagesenergie(bday_day: int, today_day: int) -> int: return reduzieren_1_9(sum(int(d) for d in f"{bday_day:02d}{today_day:02d}"))

# ---------------------- Namensenergie ---------------------
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

# ---------------------- Тексты ----------------------
GEISTES_TXT = {
    1: """(Menschen, geboren am 1., 10., 19., 28. eines Monats):
 
Sie sind ein geborener Anführer, eine sehr starke Person mit großem Willen. Sie handeln schnell, lieben es, Verantwortung zu übernehmen und neue Wege zu eröffnen.""",
    2: """(Menschen, geboren am 2., 11., 20., 29. eines Monats):

Sie sind in diese Welt gekommen, um sich durch Verständnis und Beziehungen zu verwirklichen. Ihre Stärke liegt in Harmonie, Diplomatie und der Fähigkeit, andere zu fühlen.""",
    3: """(Menschen, geboren am 3., 12., 21., 30. eines Monats):

Sie sind Träger von Wissen und natürlicher Kreativität. Sie lernen schnell, vermitteln Inhalte leicht und inspirieren andere durch Wort und Ausdruck.""",
    4: """(Menschen, geboren am 4., 13., 22., 31. eines Monats):

Sie sind der/die Erbauer:in — Struktur, Ordnung und Ausdauer prägen Ihren Weg. Sie schaffen stabile Systeme und bringen Projekte konsequent zu Ende.""",
    5: """(Menschen, geboren am 5., 14. oder 23. eines Monats):

Sie sind ein pragmatischer Mensch, lieben konsequentes Handeln, Bewegung und Kommunikation. Ihre Natur bringt Chancen, Netzwerke und Expansion.""",
    6: """(Menschen, geboren am 6., 15. oder 24. eines Monats):

Sie sind in diese Welt gekommen, um Liebe, Schönheit und Verantwortung zu leben. Familie, Fürsorge und reife Entscheidungen bilden Ihr Zentrum.""",
    7: """(Menschen, geboren am 7., 16. oder 25. eines Monats):

Sie verkörpern Analyse, Weisheit und innere Tiefe. Ihnen ist das Streben nach Wahrheit und geistiger Unabhängigkeit gegeben.""",
    8: """(Menschen, geboren am 8., 17. oder 26. eines Monats):

Sie sind in diese Welt gekommen, um alles zu kontrollieren — Management, Erfolg und gerechte Führung sind Ihr Terrain. Sie materialisieren Ziele und tragen Verantwortung.""",
    9: """(Menschen, geboren am 9., 18. oder 27. eines Monats):

In Ihnen ist die Energie des Dienens und der Vollendung angelegt. Mitgefühl, Gerechtigkeit und Blick aufs Ganze leiten Ihre Schritte.""",
}

# Полные тексты Geisteszahl 1–9 (сейчас — заглушки; можно заменить на «книжные» 1:1)
GEISTES_FULL_TXT = {
    1: """(Menschen, geboren am 1., 10., 19., 28. eines Monats):

Sie sind ein geborener Anführer, eine sehr starke Person mit großem Willen. ...""",
    2: """(Menschen, geboren am 2., 11., 20., 29. eines Monats):

Sie sind in diese Welt gekommen, um sich durch Verständnis und Beziehungen zu verwirklichen. ...""",
    3: """(Menschen, geboren am 3., 12., 21., 30. eines Monats):

Sie sind Träger von Wissen, das Ihnen von Geburt an gegeben wurde. ...""",
    4: """(Menschen, geboren am 4., 13., 22., 31. eines Monats):

Viele Menschen nehmen die Energie 4 negativ wahr, doch sie ist die Kraft der Struktur und Vollendung. ...""",
    5: """(Menschen, geboren am 5., 14. oder 23. eines Monats):

Sie sind ein pragmatischer Mensch, lieben konsequentes Handeln, ...""",
    6: """(Menschen, geboren am 6., 15. oder 24. eines Monats):

Weisheit, Erfolg und Liebe – die Qualitäten Ihrer Seele. ...""",
    7: """(Menschen, geboren am 7., 16. oder 25. eines Monats):

Sie sind ein genialer Mensch – aber nur mit Disziplin. ...""",
    8: """(Menschen, geboren am 8., 17. oder 26. eines Monats):

Sie sind in diese Welt gekommen, um alles zu kontrollieren. ...""",
    9: """(Menschen, geboren am 9., 18. oder 27. eines Monats):

Dienst, Hilfe für andere und das Erlangen maximaler Weisheit. ...""",
}

# Полные тексты остальных разделов (минимальные рабочие; можно заменить на «книжные»)
HANDLUNGS_FULL_TXT = {
    1: "Direkt, initiativ, Verantwortung übernehmen; lernt, zu Ende zu bringen.",
    2: "Diplomatisch, verbindend, hört zu; lernt, klare Grenzen und Entscheidungen.",
    3: "Kommunikativ, wissensorientiert; lernt, Fokus und Prioritäten.",
    4: "Strukturiert, ausdauernd; lernt, flexibel zu bleiben.",
    5: "Beweglich, chancenorientiert; lernt, Tiefe statt Hektik.",
    6: "Fürsorglich, verantwortungsvoll; lernt, nicht zu überladen.",
    7: "Diszipliniert, analytisch; lernt, in die Praxis zu gehen.",
    8: "Zielorientiert, Management, Ergebnisse; lernt Fairness und Delegation.",
    9: "Dienend, abschließend; lernt, Grenzen zu wahren.",
}
VERWIRK_FULL_TXT = {
    1: "Strategie, Selbstbestimmung, reife Entscheidungen entfalten den Weg.",
    2: "Beziehungen, Kooperation, Empathie bilden das Fundament.",
    3: "Wissen, Lehre, Ausdruck führen zur Entfaltung.",
    4: "Strukturen und Systeme geben Stabilität.",
    5: "Expansion, Kommunikation, Beweglichkeit öffnen Türen.",
    6: "Liebe, Verantwortung, Schönheit als Reifegrad.",
    7: "Exzellenz durch Disziplin, Forschung, innere Tiefe.",
    8: "Materieller Erfolg, gerechtes Management, Ergebnisfokus.",
    9: "Dienst, Großzügigkeit, Abschlusszyklen als Ernte.",
}
ERGEBNIS_FULL_TXT = {
    1: "Reife Führung; klare Ziele und eigenständige Umsetzung.",
    2: "Echte Kooperation; Balance zwischen Nähe und Grenzen.",
    3: "Ausdruck & Wissen; Lehren, Inspirieren, Vermitteln.",
    4: "Struktur & Vollendung; Aufbau stabiler Resultate.",
    5: "Freiheit in Bewusstheit; Wandel mit Fokus.",
    6: "Liebe mit Weisheit; Verantwortung ohne Überlastung.",
    7: "Transformation & Tiefe; Disziplinierte Exzellenz.",
    8: "Gerechter Erfolg; fair, transparent, effizient.",
    9: "Dienst & Großzügigkeit; runder Abschluss und Sinn.",
}

# --- Точечные описания по дню рождения (1..31) — твои тексты ---
DAY_BIRTH_TXT: Dict[int, str] = {
    1: """Bedeutung des Geburtstages 1 ...""",
    2: """Bedeutung des Geburtstages 2 ...""",
    3: """Bedeutung des Geburtstages 3 ...""",
    4: """Bedeutung des Geburtstages 4 ...""",
    5: """Bedeutung des Geburtstages 5 ...""",
    6: """Bedeutung des Geburtstages 6 ...""",
    7: """Bedeutung des Geburtstages 7 ...""",
    8: """Bedeutung des Geburtstages 8 ...""",
    9: """Bedeutung des Geburtstages 9 ...""",
    10: """Bedeutung des Geburtstages 10 ...""",
    11: """Bedeutung des Geburtstages 11 ...""",
    12: """Bedeutung des Geburtstages 12 ...""",
    13: """Bedeutung des Geburtstages 13 ...""",
    14: """Bedeutung des Geburtstages 14 ...""",
    15: """Bedeutung des Geburtstages 15 ...""",
    16: """Bedeutung des Geburtstages 16 ...""",
    17: """Bedeutung des Geburtstages 17 ...""",
    18: """Bedeutung des Geburtstages 18 ...""",
    19: """Bedeutung des Geburtstages 19 ...""",
    20: """Bedeutung des Geburtstages 20 ...""",
    21: """Bedeutung des Geburtstages 21 ...""",
    22: """Bedeutung des Geburtstages 22 ...""",
    23: """Bedeutung des Geburtstages 23 ...""",
    24: """Bedeutung des Geburtstages 24 ...""",
    25: """Bedeutung des Geburtstages 25 ...""",
    26: """Bedeutung des Geburtstages 26 ...""",
    27: """Bedeutung des Geburtstages 27 ...""",
    28: """Bedeutung des Geburtstages 28 ...""",
    29: """Bedeutung des Geburtstages 29 ...""",
    30: """Bedeutung des Geburtstages 30 ...""",
    31: """Bedeutung des Geburtstages 31 ...""",
}

# Tagesenergie 1-9
TAG_TXT = {
    1: "📅 Tagesenergie 1 — neuer Zyklus, klare Entscheidungen.",
    2: "📅 Tagesenergie 2 — Dialog, Ausgleich, Partnerschaft.",
    3: "📅 Tagesenergie 3 — Kommunikation, Expansion, Lernen.",
    4: "📅 Tagesenergie 4 — Ordnung, Planung, praktische Arbeit.",
    5: "📅 Tagesenergie 5 — Chancen, Bewegung, Netzwerke.",
    6: "📅 Tagesenergie 6 — Harmonie, Familie, Verantwortung.",
    7: "📅 Tagesenergie 7 — Analyse, Spiritualität, Hygiene des Geistes.",
    8: "📅 Tagesenergie 8 — Management, Finanzen, Ergebnisse.",
    9: "📅 Tagesenergie 9 — Abschluss, Dienst, Großzügigkeit.",
}

# Kollektivenergie 1–9
KOLLEKTIV_TXT = {
    1: ("👥 Kollektivenergie 1\n\nInitiativen, starke Persönlichkeiten, Führung. "
        "Gemeinsame Vision bündeln, Rollen klären."),
    2: ("👥 Kollektivenergie 2\n\nVerbindend, ausgleichend, Wir-Gefühl. "
        "Verantwortlichkeiten verankern, ehrlich sprechen."),
    3: ("👥 Kollektivenergie 3\n\nAustausch, Ideen, Lernen. "
        "Prioritäten und Prozesse vermeiden Überladung."),
    4: ("👥 Kollektivenergie 4\n\nStrukturiert, ausdauernd, stabil. "
        "Innovation zulassen, nicht erstarren."),
    5: ("👥 Kollektivenergie 5\n\nBeweglich, chancenorientiert, Netzwerke. "
        "Inneren Kompass und Ziele definieren."),
    6: ("👥 Kollektivenergie 6\n\nSorgend, wertorientiert, ästhetisch. "
        "Faire Lastenverteilung, Balance Nähe/Freiheit."),
    7: ("👥 Kollektivenergie 7\n\nForschend, diszipliniert, tief. "
        "Ergebnisse teilen, Wissen praktisch anwenden."),
    8: ("👥 Kollektivenergie 8\n\nLeistungsstark, zielorientiert, Management. "
        "Transparenz und Ethik für Vertrauen."),
    9: ("👥 Kollektivenergie 9\n\nSinnstiftend, humanitär, abschließend. "
        "Grenzen wahren, Erholung kultivieren."),
}

# Экран приветствия / меню
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

# ---------------------------- Книга: Partnerschaft из файла ----------------------------
CORPUS_PATH = os.getenv("K2_PATH", "KeytoFate_arbeiten.txt")
CORPUS_TEXT = ""
if os.path.exists(CORPUS_PATH):
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        CORPUS_TEXT = f.read()

def _extract_numbered_sections(corpus: str, heading_regex: str) -> Dict[int, str]:
    out: Dict[int, str] = {}
    if not corpus:
        return out
    pat = re.compile(heading_regex, re.M)
    matches = list(pat.finditer(corpus))
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(corpus)
        block = corpus[start:end].strip()
        out[num] = block
    return out

_PS = _extract_numbered_sections(
    CORPUS_TEXT,
    r'^\s*(?:##\s*)?Gemeinsame\s+Geisteszahl\s+([1-9])\s*$'
)

def extract_partnerschaft(n: int) -> str:
    return _PS.get(n, "")

# ---------------------------- Handlers ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
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
        await q.message.reply_html("👥 Bis zu 5 Geburtstage eingeben. Schreiben Sie <b>fertig</b>, wenn bereit.")
        return ASK_GROUP
    if data=="calc_path":
        await q.message.reply_html("🧭 Bitte Geburtsdatum für Entwicklungspfad (TT.MM.JJJJ):"); return ASK_PATH
    return ConversationHandler.END

# ---- Vollanalyse ---- (с устойчивой поддержкой 11/22)
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g, h = geisteszahl(d), handlungszahl(d, m, y)
        v, e = verwirklichungszahl(g, h), ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)
        g9, h9, v9, e9 = idx_1_9(g), idx_1_9(h), idx_1_9(v), idx_1_9(e)

        day_text = (DAY_BIRTH_TXT.get(d, "") or "").strip()
        day_block = f"\n\n📅 <b>Bedeutung des Geburtstagstages {d}</b>\n{html_escape(day_text)}" if day_text else ""

        out = (
            f"<b>Vollanalyse {d:02d}.{m:02d}.{y}</b>\n\n"
            f"🧠 Geisteszahl <b>{g}</b>:\n"
            f"{html_escape(GEISTES_TXT.get(g9, ''))}\n"
            f"{html_escape(GEISTES_FULL_TXT.get(g9, ''))}"
            f"{day_block}\n\n"
            f"⚡ Handlungszahl <b>{h}</b>:\n"
            f"{html_escape(HANDLUNGS_FULL_TXT.get(h9, ''))}\n\n"
            f"🎯 Verwirklichungszahl <b>{v}</b>:\n"
            f"{html_escape(VERWIRK_FULL_TXT.get(v9, ''))}\n\n"
            f"📘 Ergebniszahl <b>{e}</b>:\n"
            f"{html_escape(ERGEBNIS_FULL_TXT.get(e9, ''))}\n\n"
            f"💰 Geldcode: <code>{geld}</code>"
        )
        await update.message.reply_html(out)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}")
        return ASK_FULL

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip()); today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        await update.message.reply_html(f"📅 <b>Tagesenergie {today.day:02d}.{today.month:02d}.{today.year}</b>\n\n{html_escape(body)}")
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}")
        return ASK_DAY_BIRTH

# ---- Partnerschaft (из книги) ----
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d1, m1, y1 = parse_date(update.message.text.strip())
        context.user_data["compat1"] = (d1, m1, y1, update.message.text.strip())
        await update.message.reply_html("Jetzt <b>Geburtsdatum Person 2</b> eingeben (TT.MM.JJJJ):")
        return ASK_COMPAT_2
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}")
        return ASK_COMPAT_1

async def ask_compat2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if "compat1" not in context.user_data:
            await update.message.reply_html("Bitte zuerst Person 1 eingeben (TT.MM.JJJJ).")
            return ASK_COMPAT_1
        d2, m2, y2 = parse_date(update.message.text.strip())
        d1, m1, y1, s1 = context.user_data.get("compat1")
        g1, g2 = geisteszahl(d1), geisteszahl(d2)
        common = reduzieren_1_9(g1 + g2)
        long_txt = extract_partnerschaft(common) or f"(Gemeinsame Geisteszahl {common})"
        header = (
            "💞 <b>Partnerschaft</b>\n\n"
            f"<b>Person 1:</b> {s1} → Geisteszahl {g1}\n"
            f"<b>Person 2:</b> {update.message.text.strip()} → Geisteszahl {g2}\n\n"
        )
        await update.message.reply_html(header + html_escape(long_txt))
        context.user_data.pop("compat1", None)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}")
        return ASK_COMPAT_2

# ---- Namensenergie ----
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    val = namensenergie(name)
    await update.message.reply_html(f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>")
    return ConversationHandler.END

# ---- Kollektivenergie ---- (без Entwicklungspfad, по твоему запросу)
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.lower() == "fertig":
        group = context.user_data.get("group_birthdays", [])
        if len(group) < 2:
            await update.message.reply_html("❌ Mindestens 2 Personen eingeben.")
            return ASK_GROUP
        geistes_list = [geisteszahl(d) for d,_,_ in group]
        kollektiv = reduzieren_1_9(sum(geistes_list))
        personen_txt = "\n".join(
            f"• {d:02d}.{m:02d}.{y} → Geisteszahl {g}"
            for (d,m,y), g in zip(group, geistes_list)
        )
        out = f"👥 <b>Kollektivenergie</b>\n\n{personen_txt}\n\n{KOLLEKTIV_TXT.get(kollektiv,'')}"
        await update.message.reply_html(out)
        context.user_data.pop("group_birthdays", None)
        return ConversationHandler.END
    try:
        parsed = parse_dates_multi(text)
        group = context.user_data.setdefault("group_birthdays", [])
        group.extend(parsed)
        await update.message.reply_html(f"✅ Hinzugefügt: {len(parsed)}. Tippen Sie <b>fertig</b>.")
        return ASK_GROUP
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}")
        return ASK_GROUP

# ---- Entwicklungspfad (кратко; можно расширить позже) ----
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
    5: "Reizjagd, Hektik, Flucht in Abwechslung.",
    6: "Überverantwortung, subtile Schuldgefühle.",
    7: "Isolation, Theorie ohne Praxis.",
    8: "Machtspiele, Erfolgsfixierung.",
    9: "Selbstaufopferung, diffuse Ziele.",
}
async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        out = (
            f"🧭 <b>Entwicklungspfad (aus Geisteszahl {g})</b>\n\n"
            f"{ENTWICKLUNGSPFAD.get(idx_1_9(g), '')}\n\n"
            f"⚠️ Zu vermeiden: {ZU_VERMEIDEN.get(idx_1_9(g), '')}"
        )
        await update.message.reply_html(out)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}")
        return ASK_PATH

# ---------------------------- Bootstrap ----------------------------
def main():
    app = Application.builder().token(API_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))

    # Глобальные callback'и
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))

    # Диалог-меню
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
            ASK_FULL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full)],
            ASK_DAY_BIRTH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
            ASK_COMPAT_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1)],
            ASK_COMPAT_2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2)],
            ASK_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_GROUP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group)],
            ASK_PATH:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_path)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    print("🤖 KeyToFate läuft. /start → Menü.")
    app.run_polling()

if __name__=="__main__":
    main()
