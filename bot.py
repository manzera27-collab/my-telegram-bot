# -*- coding: utf-8 -*-
from __future__ import annotations
import re
import os
from datetime import datetime, timedelta, date
from typing import Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
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
        raise ValueError("Bitte Datum im Format TT.MM.JJJJ angeben, z. B. 25.11.1978.")
    d, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    datetime(year=yr, month=mth, day=d)  # верификация
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
VERWIRK_SHORT   = ['Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck','Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit','Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit']
ERGEBNIS_SHORT  = ['Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung','Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe','Gerechter Erfolg','Dienst & Großzügigkeit']

# ---------------------- Загрузка корпуса ----------------------
CORPUS_PATH = os.getenv("K2_PATH", "/app/KeytoFate_arbeiten.txt")
CORPUS_TEXT: str = ""
PARTNERSCHAFT_FULL: Dict[int, str] = {}
GEISTES_FULL:      Dict[int, str] = {}
HANDLUNGS_FULL:    Dict[int, str] = {}
VERWIRK_FULL:      Dict[int, str] = {}

def _load_corpus(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] corpus not loaded: {e}")
        return ""

def _clean_block(t: str) -> str:
    t = re.sub(r'\n\s*\d+\s*\n', '\n', t)
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
    global CORPUS_TEXT, PARTNERSCHAFT_FULL, GEISTES_FULL, HANDLUNGS_FULL, VERWIRK_FULL
    CORPUS_TEXT = _load_corpus(CORPUS_PATH)
    if not CORPUS_TEXT:
        print("[WARN] empty corpus"); return
    PARTNERSCHAFT_FULL = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Gemeinsame Geisteszahl\s+([1-9])\s*$')
    GEISTES_FULL       = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Geisteszahl\s+([1-9])\s*$')
    HANDLUNGS_FULL     = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Handlungszahl\s+([1-9])\s*$')
    VERWIRK_FULL       = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Verwirklichungszahl\s+([1-9])\s*$')
    print(f"[INFO] corpus loaded: {len(CORPUS_TEXT)} chars; partnerschaft:{len(PARTNERSCHAFT_FULL)} geist:{len(GEISTES_FULL)} handlung:{len(HANDLUNGS_FULL)} verwirk:{len(VERWIRK_FULL)}")

_init_knowledge()

# ---- helper: отправка длинного текста ----
async def send_long_html(message, text: str, reply_markup=None, chunk: int = 4000):
    if not text:
        return
    for i in range(0, len(text), chunk):
        tail = (i + chunk) >= len(text)
        await message.reply_html(text[i:i+chunk], reply_markup=reply_markup if tail else None)

# ----------------------------- Меню/состояния ------------------------------
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH, ASK_AI = range(8)

WELCOME = (
    "🌟 <b>Willkommen!</b>\n\n"
    "Vor Ihnen liegt eine systematische Lehre über Zahlen, Bewusstsein und Lebenspfade. "
    "Sie hilft, das eigene Potenzial zu entfalten und Harmonie mit sich und der Welt zu finden.\n\n"
    "✨ Lüften Sie den Schleier Ihres Weges – und lassen Sie diese Lehre Ihr Wegweiser sein. ✨"
)
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

# ---------------------------- KI helpers ----------------------------
def _split_paragraphs(corpus: str) -> List[str]:
    return [p.strip() for p in corpus.split("\n\n") if p.strip()]

def _score(q: str, para: str) -> int:
    q_terms = [t for t in re.findall(r"[\wÄÖÜäöüß]+", q.lower()) if len(t) > 2]
    pl = para.lower()
    return sum(pl.count(t) for t in q_terms)

def ai_answer_from_corpus(query: str) -> str:
    if not CORPUS_TEXT:
        return "Das Wissensarchiv ist derzeit nicht verfügbar. Bitte versuchen Sie es später erneut."
    paras = _split_paragraphs(CORPUS_TEXT)
    scored = sorted(paras, key=lambda p: _score(query, p), reverse=True)
    top = [p for p in scored[:3] if _score(query, p) > 0]
    if not top:
        return "Ich konnte dazu keinen spezifischen Abschnitt finden. Formulieren Sie die Frage präziser."
    return "\n\n".join(top)

# ---------------------------- Меню/кнопки ----------------------------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse", callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie", callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft", callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie", callback_data="calc_name")],
        [InlineKeyboardButton("👥 Gruppenenergie", callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad", callback_data="calc_path")],
        [InlineKeyboardButton("🤖 KI-Modus", callback_data="ai_mode")],
        [InlineKeyboardButton("💖 Spende (PayPal)", url="https://www.paypal.com/donate?business=manzera%40mail.ru")],
    ])

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    await q.answer()

    if data == "calc_full":
        await q.message.reply_html("🧮 Geben Sie das <b>Geburtsdatum</b> für die Vollanalyse ein (TT.MM.JJJJ):")
        return ASK_FULL
    if data == "calc_day":
        await q.message.reply_html("Geben Sie Ihr <b>Geburtsdatum</b> ein (TT.MM.JJJJ):")
        return ASK_DAY_BIRTH
    if data == "calc_compat":
        await q.message.reply_html("Geben Sie <b>Geburtsdatum Person 1</b> ein (TT.MM.JJJJ):")
        return ASK_COMPAT_1
    if data == "calc_name":
        await q.message.reply_html("Geben Sie den <b>Namens</b> ein (lateinische Schreibweise):")
        return ASK_NAME
    if data == "calc_group":
        context.user_data["group_birthdays"] = []
        await q.message.reply_html("👥 Bis zu 5 Geburtstage eingeben. Schreiben Sie <b>fertig</b>, wenn bereit.")
        return ASK_GROUP
    if data == "calc_path":
        await q.message.reply_html("🧭 <b>Entwicklungspfad</b>\nBitte Geburtsdatum eingeben (TT.MM.JJJJ):")
        return ASK_PATH
    if data == "ai_mode":
        await q.message.reply_html("🤖 KI-Modus: Stellen Sie Ihre Frage zur Lehre.")
        return ASK_AI
    return ConversationHandler.END

# ---------------------------- Handlers ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG] /start received")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG] back_to_menu clicked")
    q = update.callback_query
    await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

# ---- Vollanalyse ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        g = geisteszahl(d); h = handlungszahl(d, m, y)
        v = verwirklichungszahl(g, h); e = ergebniszahl(g, h, v)
        geld = geldcode(d, m, y)

        geist_full = GEISTES_FULL.get(g, ""); handl_full = HANDLUNGS_FULL.get(h, "")
        verw_full  = VERWIRK_FULL.get(v, "")

        parts = [
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>",
            f"🧠 Geisteszahl {g}: {html_escape(GEISTES_TXT_SHORT.get(g,'').strip())}",
        ]
        if geist_full: parts.append(html_escape(geist_full))
        parts.append(f"⚡ Handlungszahl {h}: {HANDLUNG_SHORT[(h-1)%9]}")
        if handl_full: parts.append(html_escape(handl_full))
        parts.append(f"🎯 Verwirklichungszahl {v}: {VERWIRK_SHORT[(v-1)%9]}")
        if verw_full: parts.append(html_escape(verw_full))
        parts.append(f"📘 Ergebniszahl {e}: {ERGEBNIS_SHORT[(e-1)%9]}")
        parts.append(f"💰 Geldcode: <code>{geld}</code>")

        await send_long_html(update.message, "\n\n".join(parts))
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}\nBeispiel: <code>25.11.1978</code>")
        return ASK_FULL

# ---- Tagesenergie ----
TAG_TXT = {
    1: "Neuer Zyklus, Entscheidungen.",
    2: "Dialog, Ausgleich, Partnerschaft.",
    3: "Kommunikation, Expansion, Lernen.",
    4: "Ordnung, Planung, Arbeit.",
    5: "Chancen, Bewegung, Netzwerke.",
    6: "Harmonie, Familie, Verantwortung.",
    7: "Analyse, Spiritualität, Innere Ruhe.",
    8: "Management, Finanzen, Ergebnisse.",
    9: "Abschluss, Dienst, Großzügigkeit.",
}
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d, m, y = parse_date(update.message.text.strip())
        today = datetime.now()
        val = tagesenergie(d, today.day)
        out = f"📅 <b>Tagesenergie {today.day:02d}.{today.month:02d}.{today.year}:</b>\n\n{TAG_TXT.get(val,'Energie im Fluss.')}"
        await update.message.reply_html(out)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}")
        return ASK_DAY_BIRTH

# ---- Partnerschaft ----
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d1, m1, y1 = parse_date(update.message.text.strip())
        context.user_data["compat1"] = (d1, m1, y1, update.message.text.strip())
        await update.message.reply_html("Jetzt Geburtsdatum Person 2 eingeben (TT.MM.JJJJ):")
        return ASK_COMPAT_2
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}")
        return ASK_COMPAT_1

async def ask_compat2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if "compat1" not in context.user_data:
            await update.message.reply_html("Bitte zuerst Person 1 eingeben.")
            return ASK_COMPAT_1

        d2, m2, y2 = parse_date(update.message.text.strip())
        d1, m1, y1, s1 = context.user_data.get("compat1")
        g1, g2 = geisteszahl(d1), geisteszahl(d2)
        common = reduzieren_1_9(g1 + g2)

        long_txt = PARTNERSCHAFT_FULL.get(common, "")
        header = (
            "💞 <b>Partnerschaft</b>\n\n"
            f"<b>Person 1:</b> {s1} → Geisteszahl {g1}\n"
            f"<b>Person 2:</b> {update.message.text.strip()} → Geisteszahl {g2}\n\n"
        )
        body = html_escape(long_txt) if long_txt else f"(Gemeinsame Geisteszahl {common})"
        await send_long_html(update.message, header + body)
        context.user_data.pop("compat1", None)
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex)))}")
        return ASK_COMPAT_2

# ---- Namensenergie ----
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    val = namensenergie(name)
    await update.message.reply_html(f"🔤 Namensenergie „{html_escape(name)}“: <b>{val}</b>")
    return ConversationHandler.END

# ---- Gruppenenergie ----
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.lower() == "fertig":
        group = context.user_data.get("group_birthdays", [])
        if len(group) < 2:
            await update.message.reply_html("❌ Mindestens 2 Personen eingeben.")
            return ASK_GROUP
        geistes_list = [geisteszahl(d) for d,_,_ in group]
        summe = sum(geistes_list); kollektiv = reduzieren_1_9(summe)
        personen_txt = "\n".join(
            f"• {d:02d}.{m:02d}.{y} → {g}" for (d,m,y), g in zip(group, geistes_list)
        )
        out = f"👥 <b>Gruppenenergie</b>\n\n{personen_txt}\n\nZahl: {kollektiv}"
        await update.message.reply_html(out)
        return ConversationHandler.END
    try:
        parsed = parse_dates_multi(text)
        group = context.user_data.setdefault("group_birthdays", [])
        group.extend(parsed[: max(0, 5 - len(group))])
        await update.message.reply_html(f"✅ Hinzugefügt: {len(parsed)}. Schreiben Sie <b>fertig</b> für Berechnung.")
        return ASK_GROUP
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}")
        return ASK_GROUP

# ---- KI-Modus ----
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q:
        await update.message.reply_html("Bitte Frage eingeben.")
        return ASK_AI
    ans = ai_answer_from_corpus(q)
    await send_long_html(update.message, "🧾 Antwort:\n\n" + ans)
    return ConversationHandler.END

# ---- Общий error-handler (видно падения в логах) ----
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    who = "?"
    try:
        if update and isinstance(update, Update) and update.effective_user:
            who = str(update.effective_user.id)
    except Exception:
        pass
    print(f"[ERROR] user={who}: {context.error}")

# ---------------------------- Bootstrap ----------------------------
def main():
    app = Application.builder().token(API_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))

    # Кнопка «в меню»
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))

    # Диалоговое меню
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^(calc_|ai_mode)")],
        states={
            ASK_FULL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full)],
            ASK_DAY_BIRTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
            ASK_COMPAT_1:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1)],
            ASK_COMPAT_2:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2)],
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_GROUP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group)],
            ASK_PATH:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
            ASK_AI:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ai)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # Общий ловец ошибок
    app.add_error_handler(error_handler)

    print("🤖 KeyToFate läuft. /start → Menü öffnen.")
    app.run_polling()

if __name__ == "__main__":
    main()
