from __future__ import annotations

import re
from datetime import datetime
from typing import Tuple, List

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# ========================= ПРОБНАЯ ВЕРСИЯ =========================
API_TOKEN = '8307912076:AAG6neSMpuFIVFmTY0Pi-rHco66Tqn94uwo'
# ================================================================

MEISTER_ERHALTEN = True          # для базовых чисел (1/11/22/33) где уместно
DATE_REGEX = r'^\s*(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})\s*$'

# ----------------------------- Utils -----------------------------
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

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
    """Редукция с возможным сохранением мастер-чисел (11/22/33)."""
    while n > 9:
        s = sum(int(d) for d in str(n))
        if keep_master and s in (11, 22, 33):
            return s
        n = s
    return n

def reduzieren_1_9(n: int) -> int:
    """Жёсткая редукция 1–9 (без мастер-чисел) — для Tagesenergie/Partnerschaft/Kollektiv."""
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
    # День рождения (например 25) + сегодняшний день (например 23) => 2+5+2+3 => редукция до 1–9
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

# ---------------------- Тексты: из книги и расширенные ----------------------

# КОРОТКИЕ аннотации Geisteszahl 1–9 — из первых предложений книги.
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

# ПОЛНЫЕ тексты Geisteszahl 1–9 — буквально из книги (кнопка «Mehr lesen»)
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

# Tagesenergie 1–9 — буквально из книги
TAG_TXT = {
    1: """📅 Tagesenergie 1

** – heute können Sie mit klaren Entscheidungen und ersten Schritten einen neuen Zyklus öffnen. ...""",
    2: """📅 Tagesenergie 2

** – heute ist Dialog, Ausgleich und Partnerschaft begünstigt. ...""",
    3: """📅 Tagesenergie 3

** – der Wunsch nach Kommunikation und Expansion wird Ihr Erschaffen beschleunigen. ...""",
    4: """📅 Tagesenergie 4

** – Struktur, Ordnung, praktische Arbeit und Planung sind heute auf Ihrer Seite. ...""",
    5: """📅 Tagesenergie 5

** – Freiheit, Reisen, Netzwerke und Chancen bringen Bewegung in Ihre Vorhaben. ...""",
    6: """📅 Tagesenergie 6

** – Harmonie, Familie, Schönheit und reife Entscheidungen prägen diesen Tag. ...""",
    7: """📅 Tagesenergie 7

** – Analyse, Forschung, Spiritualität und geistige Hygiene stehen im Vordergrund. ...""",
    8: """📅 Tagesenergie 8

** – Management, Finanzen, Ergebnisse. Heute ist ein Tag der Zielklarheit. ...""",
    9: """📅 Tagesenergie 9

** – Abschluss, Dienst und Großzügigkeit: bringen Sie Dinge zu Ende und schaffen Sie Raum für Neues. ...""",
}

# Partnerschaft (общая цифра пары 1–9) — расширенный текст (в книге отдельного явного раздела нет)
PARTNERSCHAFT_TXT = {
    1: ("💞 Partnerschaft 1\n\n"
        "Zwei Führungsenergien bringen Funken, Tempo und große Schaffenskraft. "
        "Mit gemeinsamen Zielen entsteht ein starkes Team; ohne sie drohen Machtspiele."),
    2: ("💞 Partnerschaft 2\n\n"
        "Zart, empathisch, harmonieorientiert. Diese Verbindung heiligt das Gespräch und liebt Ausgleich. "
        "Ehrlichkeit und Grenzen schützen Nähe."),
    3: ("💞 Partnerschaft 3\n\n"
        "Lebendig, inspirierend, voller Kommunikation, Reisen, Lernen. "
        "Struktur und klare Prioritäten verhindern Zerstreuung."),
    4: ("💞 Partnerschaft 4\n\n"
        "Praktisch und stabil. Ordnung, Disziplin und Beständigkeit prägen das Zusammensein. "
        "Raum für Spontaneität einplanen."),
    5: ("💞 Partnerschaft 5\n\n"
        "Kommunikativ, beweglich, abenteuerlustig. Offen für neue Erfahrungen. "
        "Innerer Anker und gemeinsame Werte halten Fokus."),
    6: ("💞 Partnerschaft 6\n\n"
        "Liebe, Fürsorge, Verantwortung. Wärme, Harmonie und Wunsch nach Familie. "
        "Balance zwischen Nähe und Freiheit pflegen."),
    7: ("💞 Partnerschaft 7\n\n"
        "Tiefe, Transformation, innere Arbeit. Disziplin, Austausch und Rituale beugen Rückzug vor."),
    8: ("💞 Partnerschaft 8\n\n"
        "Machtvoll, zielorientiert, ergebnisstark. Transparenz, Ethik und Fairness sind Schlüssel."),
    9: ("💞 Partnerschaft 9\n\n"
        "Reif, sinnstiftend, überpersönlich. Klare Grenzen, Balance Geben/Empfangen."),
}

# Kollektivenergie (общая цифра группы 1–9) — расширенный текст
KOLLEKTIV_TXT = {
    1: ("👥 Kollektivenergie 1\n\n"
        "Initiativen, starke Persönlichkeiten, Führung. Gemeinsame Vision bündeln, Rollen klären."),
    2: ("👥 Kollektivenergie 2\n\n"
        "Verbindend, ausgleichend, Wir-Gefühl. Verantwortlichkeiten verankern, ehrlich sprechen."),
    3: ("👥 Kollektivenergie 3\n\n"
        "Austausch, Ideen, Lernen. Prioritäten und Prozesse vermeiden Überladung."),
    4: ("👥 Kollektivenergie 4\n\n"
        "Strukturiert, ausdauernd, stabil. Innovation zulassen, nicht erstarren."),
    5: ("👥 Kollektivenergie 5\n\n"
        "Beweglich, chancenorientiert, Netzwerke. Inneren Kompass und Ziele definieren."),
    6: ("👥 Kollektivenergie 6\n\n"
        "Sorgend, wertorientiert, ästhetisch. Faire Lastenverteilung, Balance Nähe/Freiheit."),
    7: ("👥 Kollektivenergie 7\n\n"
        "Forschend, diszipliniert, tief. Ergebnisse teilen, Wissen praktisch anwenden."),
    8: ("👥 Kollektivenergie 8\n\n"
        "Leistungsstark, zielorientiert, Management. Transparenz und Ethik für Vertrauen."),
    9: ("👥 Kollektivenergie 9\n\n"
        "Sinnstiftend, humanitär, abschließend. Grenzen wahren, Erholung kultivieren."),
}

# Entwicklungspfad (из книги — логика пути «через что к чему», без формул) + Zu vermeiden
ENTWICKLUNGSPFAD = {
    1: "Die 1 reift zur 4 — über Beziehung (2) und Ausdruck (3): aus Impuls werden Disziplin und Struktur.",
    2: "Die 2 strebt zur 5 — über Wissen/Kommunikation (3) und Ordnung (4): Harmonie wird zu bewusster Freiheit.",
    3: "Die 3 entfaltet sich zur 6 — über Struktur (4) und Wandel (5): Kreativität wird zu reifer Verantwortung.",
    4: "Die 4 wächst zur 7 — über Freiheit (5) und Liebe/Verantwortung (6): Ordnung wird zu innerer Weisheit.",
    5: "Die 5 strebt zur 8 — über 6 und 7: zuerst Liebe/Verantwortung (6), dann Wahrheit/Disziplin (7), und erst dann gerechter Erfolg (8).",
    6: "Die 6 geht zur 9 — über Tiefgang (7) und Macht/Erfolg (8): zur universellen Liebe und zum Dienst.",
    7: "Die 7 geht zur 1 — über 8 und 9: Disziplin & Macht (8), Abschluss & Dienst (9) hin zur reifen Führung (1).",
    8: "Die 8 strebt zur 2 — über 9 und 1: von Macht zu Kooperation und Diplomatie.",
    9: "Die 9 findet zur 3 — über 1 und 2: Dienst & Vollendung führen zu leichtem, schöpferischem Ausdruck.",
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

# ----------------------------- Меню ------------------------------
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse",     callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie",    callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft",   callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie",   callback_data="calc_name")],
        [InlineKeyboardButton("👥 Kollektivenergie",callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad",callback_data="calc_path")],
    ])

def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")]])

WELCOME = (
    "🌟 <b>Liebe Freunde!</b>\n\n"
    "Vor Ihnen liegt ein einzigartiges Wissen: <b>KeyToFate</b> – der Schlüssel zu sich selbst und zu allem.\n"
    "Es hilft, Ihr wahres Potenzial zu entfalten und Harmonie mit sich und der Welt zu finden.\n\n"
    "Ihr Geburtsdatum birgt erstaunliche Erkenntnisse über Persönlichkeit und Bestimmung. "
    "Wer diese Gesetze versteht, entfaltet Talente und findet den eigenen Weg.\n\n"
    "✨ Lüften Sie den Schleier Ihres Schicksals – und lassen Sie KeyToFate Ihr Wegweiser zum Glück sein. ✨\n\n"
    "➡️ Wählen Sie unten, um Ihre Reise zu beginnen:"
)

MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

# ---------------------------- Handlers ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(WELCOME, reply_markup=main_menu())

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(MENU_HEADER, reply_markup=main_menu())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()
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
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        # кнопка «Mehr lesen» по Geisteszahl
        more_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"📖 Mehr lesen über {g}", callback_data=f"more_g{g}")
        ], [
            InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")
        ]])

        out = (
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>\n\n"
            f"🧠 <b>Geisteszahl:</b> {g}\n{html_escape(GEISTES_TXT.get(g,'').strip())}\n\n"
            f"⚡ <b>Handlungszahl:</b> {h}\n"
            f"{['Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert','Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll','Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'][(h-1)%9]}\n\n"
            f"🎯 <b>Verwirklichungszahl:</b> {v}\n"
            f"{['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'][(v-1)%9]}\n\n"
            f"📘 <b>Ergebniszahl:</b> {e}\n"
            f"{['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit'][(e-1)%9]}\n\n"
            f"💰 <b>Geldcode:</b> <code>{geld}</code>"
        )
        await update.message.reply_html(out, reply_markup=more_kb)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBeispiel: <code>25.11.1978</code>",
                                        reply_markup=back_menu_kb())
        return ASK_FULL

# ---- Callback: Mehr lesen über Geisteszahl X ----
async def read_more_geist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        data = q.data  # e.g. "more_g5"
        g = int(data.replace("more_g", ""))
        full = GEISTES_FULL_TXT.get(g)
        if not full:
            await q.message.reply_html("Für diese Zahl liegt kein erweiterter Text vor.",
                                       reply_markup=back_menu_kb())
            return
        await q.message.reply_html(f"📖 <b>Geisteszahl {g}</b>\n\n{html_escape(full.strip())}",
                                   reply_markup=back_menu_kb())
    except Exception as e:
        await q.message.reply_html(f"❌ {html_escape(str(e))}", reply_markup=back_menu_kb())

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        out = (
            f"📅 <b>Tagesenergie für {today.day:02d}.{today.month:02d}.{today.year}:</b>\n\n"
            f"{html_escape(body.strip())}"
        )
        await update.message.reply_html(out, reply_markup=main_menu())
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nVersuchen Sie erneut (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_DAY_BIRTH

# ---- Partnerschaft ----
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        )
        await update.message.reply_html(text, reply_markup=main_menu())
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
    name = update.message.text.strip()
    val = namensenergie(name)
    beschreibung = NAMENS_TXT.get(val, "Keine Beschreibung gefunden.")
    await update.message.reply_html(
        f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>\n\n"
        f"{beschreibung}",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

# ---- Kollektivenergie ----
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        )
        await update.message.reply_html(out, reply_markup=main_menu())
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

# ---- Entwicklungspfad (по Geisteszahl) ----
async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        pfad = ENTWICKLUNGSPFAD.get(g, "")
        avoid = ZU_VERMEIDEN.get(g, "")
        out = (
            f"🧭 <b>Entwicklungspfad (aus Geisteszahl {g})</b>\n\n"
            f"{pfad}\n\n"
            + (f"⚠️ <b>Zu vermeiden:</b> {avoid}" if avoid else "")
        )
        await update.message.reply_html(out, reply_markup=main_menu())
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
    try:
        d, m, y = parse_date(text)
        g = geisteszahl(d)
        h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        more_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"📖 Mehr lesen über {g}", callback_data=f"more_g{g}")
        ], [
            InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")
        ]])

        out = (
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>\n\n"
            f"🧠 <b>Geisteszahl:</b> {g}\n{html_escape(GEISTES_TXT.get(g,'').strip())}\n\n"
            f"⚡ <b>Handlungszahl:</b> {h}\n"
            f"{['Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert','Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll','Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'][(h-1)%9]}\n\n"
            f"🎯 <b>Verwirklichungszahl:</b> {v}\n"
            f"{['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'][(v-1)%9]}\n\n"
            f"📘 <b>Ergebniszahl:</b> {e}\n"
            f"{['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit'][(e-1)%9]}\n\n"
            f"💰 <b>Geldcode:</b> <code>{geld}</code>"
        )
        await update.message.reply_html(out, reply_markup=more_kb)
    except Exception:
        pass

# ---------------------------- Bootstrap ----------------------------
def main():
    app = Application.builder().token(API_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))

    # Кнопка "Zurück zum Menü"
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_menu$"))

    # Callback "Mehr lesen"
    app.add_handler(CallbackQueryHandler(read_more_geist, pattern=r"^more_g[1-9]$"))

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

    # Фоллбек: если просто прислали дату — Vollanalyse
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, full_analysis_fallback))

    print("🤖 KeyToFate läuft. /start oder /menu → Hauptmenü. Geisteszahl & Tagesenergie — wörtlich aus dem Buch.")
    app.run_polling()

if __name__ == "__main__":
    main()

