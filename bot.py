# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re
from datetime import datetime
from typing import Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

# ========================= API TOKEN =========================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
# =============================================================

# ========================= ПУТЬ К КНИГЕ ======================
# На Railway положи файл рядом с bot.py и используй тот же путь.
# Можно переопределить через переменную окружения K2_PATH.
CORPUS_PATH = os.getenv("K2_PATH", "/app/KeytoFate_arbeiten.txt")
# =============================================================

# ----------------------------- Utils -----------------------------
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def parse_date(text: str) -> Tuple[int,int,int]:
    m = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    if not m:
        raise ValueError("Bitte Datum im Format TT.MM.JJJJ angeben, z. B. 25.11.1978.")
    d, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # Валидация
    datetime(year=yr, month=mth, day=d)
    return d, mth, yr

def parse_dates_multi(text: str) -> List[Tuple[int,int,int]]:
    pattern = r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})'
    found = re.findall(pattern, text)
    out: List[Tuple[int,int,int]] = []
    for d, mth, yr in found:
        day, month, year = int(d), int(mth), int(yr)
        datetime(year=year, month=month, day=day)  # validate
        out.append((day, month, year))
    return out

def reduzieren(n: int, keep_master: bool = True) -> int:
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
    return reduzieren(g + h + v)

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

# ---------------------- Краткие тексты ----------------------
GEISTES_TXT_SHORT = {
    1: "Führung, Wille, Initiative.",
    2: "Harmonie, Diplomatie, Empathie.",
    3: "Wissen, Ausdruck, Kreativität.",
    4: "Struktur, Ordnung, Ausdauer.",
    5: "Bewegung, Kommunikation, Chancen.",
    6: "Liebe, Fürsorge, Verantwortung.",
    7: "Weisheit, Wahrheit, Disziplin.",
    8: "Management, Erfolg, Gerechtigkeit.",
    9: "Dienst, Mitgefühl, Vollendung.",
}
HANDLUNG_SHORT = ['Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert','Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll','Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend']
VERWIRK_SHORT = ['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit']
ERGEBNIS_SHORT = ['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit']

# ---------------------- Загрузка корпуса (книга) ----------------------
CORPUS_TEXT: str = ""
PARTNERSCHAFT_FULL: Dict[int, str] = {}

def _load_corpus(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] corpus not loaded: {e}")
        return ""

def _clean_block(t: str) -> str:
    # немножко почистим абзацы
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def _extract_numbered_sections(corpus: str, heading_regex: str) -> Dict[int, str]:
    out: Dict[int, str] = {}
    if not corpus:
        return out
    pat = re.compile(heading_regex, re.I | re.M)
    matches = list(pat.finditer(corpus))
    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(corpus)
        out[n] = _clean_block(corpus[start:end])
    return out

def _init_knowledge():
    global CORPUS_TEXT, PARTNERSCHAFT_FULL
    CORPUS_TEXT = _load_corpus(CORPUS_PATH)
    if not CORPUS_TEXT:
        print("[WARN] empty corpus")
        PARTNERSCHAFT_FULL = {}
        return
    # В книге должны быть заголовки вида:
    #   Gemeinsame Geisteszahl 1
    #   ...
    #   Gemeinsame Geisteszahl 9
    PARTNERSCHAFT_FULL = _extract_numbered_sections(
        CORPUS_TEXT, r'^\s*(?:##\s*)?Gemeinsame\s+Geisteszahl\s+([1-9])\s*$'
    )
    print(f"[INFO] corpus loaded: {len(CORPUS_TEXT)} chars; partnerschaft:{len(PARTNERSCHAFT_FULL)}")

_init_knowledge()

# ----------------------------- Меню/состояния ------------------------------
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

WELCOME = (
    "🌟 <b>Willkommen!</b>\n\n"
    "Vor Ihnen liegt eine systematische Lehre über Zahlen, Bewusstsein und Lebenspfade. "
    "Sie hilft, das eigene Potenzial zu entfalten und Harmonie mit sich und der Welt zu finden.\n\n"
    "✨ Lüften Sie den Schleier Ihres Weges – und lassen Sie diese Lehre Ihr Wegweiser sein. ✨"
)
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

# ---- Кнопки (донат только кнопкой, без приписок в текстах) ----
PAYPAL_URL = "https://www.paypal.com/donate?business=manzera%40mail.ru"
def donate_keyboard(extra_rows: List[List[InlineKeyboardButton]] | None = None) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    if extra_rows:
        rows.extend(extra_rows)
    rows.append([InlineKeyboardButton("💖 Spende (PayPal)", url=PAYPAL_URL)])
    rows.append([InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")])
    return InlineKeyboardMarkup(rows)

def back_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück zum Menü", callback_data="back_menu")]])

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse",   callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie",  callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft", callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie", callback_data="calc_name")],
        [InlineKeyboardButton("👥 Gruppenenergie",callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad",callback_data="calc_path")],
    ])

# ---------------------------- Команды/меню ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(MENU_HEADER, reply_markup=main_menu())

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
            "👥 Bis zu 5 Geburtstage eingeben. Wenn fertig — tippen Sie <b>fertig</b>.",
            reply_markup=back_menu_kb()
        )
        return ASK_GROUP
    if data == "calc_path":
        await q.message.reply_html("🧭 Entwicklungspfad: Geburtsdatum eingeben (TT.MM.JJJJ):",
                                   reply_markup=back_menu_kb())
        return ASK_PATH
    return ConversationHandler.END

# ========================= Handlers =========================
# ---- Vollanalyse (оставил классическую логику) ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h)
        e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        parts = [
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>",
            f"🧠 <b>Geisteszahl:</b> {g}\n{GEISTES_TXT_SHORT.get(g,'')}",
            f"⚡ <b>Handlungszahl:</b> {h}\n{HANDLUNG_SHORT[(h-1)%9]}",
            f"🎯 <b>Verwirklichungszahl:</b> {v}\n{VERWIRK_SHORT[(v-1)%9]}",
            f"📘 <b>Ergebniszahl:</b> {e}\n{ERGEBNIS_SHORT[(e-1)%9]}",
            f"💰 <b>Geldcode:</b> <code>{geld}</code>",
        ]
        await update.message.reply_html("\n\n".join(parts), reply_markup=donate_keyboard())
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBeispiel: <code>25.11.1978</code>",
                                        reply_markup=back_menu_kb())
        return ASK_FULL

# ---- Tagesenergie ----
TAG_TXT = {
    1: "📅 Tagesenergie 1 — neue Zyklen, klare Entscheidungen.",
    2: "📅 Tagesenergie 2 — Dialog, Ausgleich, Partnerschaft.",
    3: "📅 Tagesenergie 3 — Kommunikation, Expansion, Lernen.",
    4: "📅 Tagesenergie 4 — Ordnung, Planung, praktische Arbeit.",
    5: "📅 Tagesenergie 5 — Chancen, Bewegung, Netzwerke.",
    6: "📅 Tagesenergie 6 — Harmonie, Familie, Verantwortung.",
    7: "📅 Tagesenergie 7 — Analyse, Spiritualität, Hygiene des Geistes.",
    8: "📅 Tagesenergie 8 — Management, Finanzen, Ergebnisse.",
    9: "📅 Tagesenergie 9 — Abschluss, Dienst, Großzügigkeit.",
}
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        today = datetime.now()
        val = tagesenergie(d, today.day)
        out = f"📅 <b>Tagesenergie für {today.day:02d}.{today.month:02d}.{today.year}:</b>\n\n{TAG_TXT.get(val,'Energie im Fluss.')}"
        await update.message.reply_html(out, reply_markup=donate_keyboard())
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}",
                                        reply_markup=back_menu_kb())
        return ASK_DAY_BIRTH

# ---- Partnerschaft (ДЛИННЫЕ тексты из книги) ----
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
            await update.message.reply_html("Bitte zuerst Person 1 eingeben.", reply_markup=back_menu_kb())
            return ASK_COMPAT_1

        d2, m2, y2 = parse_date(update.message.text.strip())
        d1, m1, y1, s1 = context.user_data.get("compat1")
        g1 = geisteszahl(d1)
        g2 = geisteszahl(d2)
        common = reduzieren_1_9(g1 + g2)

        # Берём из книги: раздел «Gemeinsame Geisteszahl N»
        long_txt = PARTNERSCHAFT_FULL.get(common, "").strip()

        header = (
            "💞 <b>Partnerschaft</b>\n\n"
            f"<b>Person 1:</b> {html_escape(s1)} → Geisteszahl {g1}\n"
            f"<b>Person 2:</b> {html_escape(update.message.text.strip())} → Geisteszahl {g2}\n\n"
            f"🧮 <b>Gemeinsame Geisteszahl:</b> {common}\n\n"
        )
        body = html_escape(long_txt) if long_txt else "Für diese Kombination wurde im Korpus kein Abschnitt gefunden."
        await update.message.reply_html(header + body, reply_markup=donate_keyboard())
        context.user_data.pop("compat1", None)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}\nBitte erneut Person 2 (TT.MM.JJJJ):",
                                        reply_markup=back_menu_kb())
        return ASK_COMPAT_2

# ---- Namensenergie ----
NAMENS_TXT = {
    1: "Die Namensenergie 1: Wille, Initiative, Führung.",
    2: "Die Namensenergie 2: Harmonie, Diplomatie, Ausgleich.",
    3: "Die Namensenergie 3: Kreativität, Wissen, Ausdruck.",
    4: "Die Namensenergie 4: Struktur, Ordnung, Ausdauer.",
    5: "Die Namensenergie 5: Freiheit, Bewegung, Wandel.",
    6: "Die Namensenergie 6: Liebe, Fürsorge, Verantwortung.",
    7: "Die Namensenergie 7: Weisheit, Analyse, Wahrheit.",
    8: "Die Namensenergie 8: Erfolg, Autorität, Management.",
    9: "Die Namensenergie 9: Dienst, Humanität, Vollendung.",
}
def namensenergie_text(val: int) -> str:
    return NAMENS_TXT.get(val, "Keine Beschreibung gefunden.")

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    val = namensenergie(name)
    await update.message.reply_html(
        f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>\n\n{namensenergie_text(val)}",
        reply_markup=donate_keyboard()
    )
    return ConversationHandler.END

# ---- Gruppenenergie (краткий вывод) ----
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.lower() == "fertig":
        group = context.user_data.get("group_birthdays", [])
        if len(group) < 2:
            await update.message.reply_html("❌ Mindestens 2 Personen eingeben.", reply_markup=back_menu_kb())
            return ASK_GROUP
        geistes_list = [geisteszahl(d) for d,_,_ in group]
        kollektiv = reduzieren_1_9(sum(geistes_list))
        personen_txt = "\n".join(
            f"• Person {i+1}: {d:02d}.{m:02d}.{y} → Geisteszahl {g}"
            for i, ((d,m,y), g) in enumerate(zip(group, geistes_list))
        )
        out = f"👥 <b>Gruppenenergie</b>\n\n{personen_txt}\n\nGesamtzahl: {kollektiv}"
        await update.message.reply_html(out, reply_markup=donate_keyboard())
        return ConversationHandler.END
    try:
        parsed = parse_dates_multi(text)
        group = context.user_data.setdefault("group_birthdays", [])
        group.extend(parsed)
        await update.message.reply_html(
            f"✅ Hinzugefügt: {len(parsed)}. Schreiben Sie <b>fertig</b>, wenn bereit.",
            reply_markup=back_menu_kb()
        )
        return ASK_GROUP
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}", reply_markup=back_menu_kb())
        return ASK_GROUP

# ---- Entwicklungspfad (кратко) ----
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
async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        out = f"🧭 <b>Entwicklungspfad</b> (aus Geisteszahl {g})\n\n{ENTWICKLUNGSPFAD.get(g,'')}"
        await update.message.reply_html(out, reply_markup=donate_keyboard())
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}", reply_markup=back_menu_kb())
        return ASK_PATH

# ---------------------------- Bootstrap ----------------------------
def main():
    if not API_TOKEN:
        raise RuntimeError("API_TOKEN fehlt. Lege es in .env oder Railway-Variablen.")
    app = Application.builder().token(API_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))

    # Кнопки открытия/назад
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))

    # Диалоговое меню
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
            ASK_FULL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_DAY_BIRTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_COMPAT_1:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_COMPAT_2:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_GROUP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
            ASK_PATH:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_path),
                            CallbackQueryHandler(back_to_menu, pattern="^back_menu$")],
        },
        fallbacks=[CommandHandler("menu", menu_cmd)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # Гарантируем, что «Zurück» поймается даже вне состояний
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_menu$"), group=1)

    print("🤖 KeyToFate läuft. /start → Begrüßung, dann «Zum Menü». Partnerschaft nutzt Texte aus der Datei.")
    app.run_polling()

if __name__ == "__main__":
    main()
