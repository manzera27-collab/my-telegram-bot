# -*- coding: utf-8 -*-
# KeyToFate — единый файл бота (упрощённая Vollanalyse + улучшенная Namensenergie)
# Требуется python-telegram-bot v20+

import os, re
from datetime import datetime
from typing import Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

# ========================= НАСТРОЙКА =========================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise SystemExit("API_TOKEN is missing. Set it in env.")

# ---- утилиты ----
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Zurück ins Menü", callback_data="open_menu")]])

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

# ========================= ТЕКСТЫ =========================
GEISTES_TXT = {
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

# Короткий «общий» блок для Geisteszahl (1–9) — как у тебя был в книге (сокращённая версия для Vollanalyse)
GEISTES_BLOCK = {
    7: """(Menschen, geboren am 7., 16. oder 25. eines Monats):

Sie sind ein genialer Mensch, aber nur, wenn Sie für sich selbst Disziplin für Geist und Körper schaffen. Ohne Plan, Sport und Disziplin entsteht Chaos. Hauptaufgabe: bewusst Disziplin kultivieren (z. B. Sport, Yoga), damit das Leben keine Krisen für Sie schafft. Sie haben viel vitale/sexuelle Energie — её нужно направлять и контролировать. Избегать веществ, меняющих сознание — трезвость даёт больше радости и результата.""",
    # при желании добавишь остальные 1–6,8–9 по тому же шаблону
}

# Полные тексты дней рождения 1–31 (сокр. фрагменты — использую твои блоки)
DAY_BIRTH_TXT: Dict[int, str] = {
    25: """Wenn Sie am 25. geboren sind:
Ihre Stärken sind die Geschäftsentwicklung und Kommunikation durch das Verständnis von Menschen. Sie streben danach, andere zu verstehen, und verwirklichen sich hervorragend in der Kommunikation. Täglicher Sport und klare Zielsetzung bringen überragende Ergebnisse.
Achten Sie auf innere Ehrlichkeit; übernehmen Sie Verpflichtungen und Verantwortung. Dann werden Sie ein Führer, der Menschen versteht. Hervorragende Verhandlungsfähigkeiten — richten Sie Aufmerksamkeit auf das Ergebnis.""",
    7: """Wenn Sie am 7. geboren sind:
Wahrscheinlich lieben Sie Sport seit Kindheit und besitzen eine große Energiereserve. Wichtig: Ziele setzen, энергию направлять на достижение, а не на хаос. Развивайте лидерство, действуйте самостоятельно, медитация и спорт — против сомнений.""",
    16: """Wenn Sie am 16. geboren sind:
Главная задача — дисциплина и контроль времени. Жизнь даст любовь/деньги/успех, если вы держите порядок. Практикуйте аскезы, планируйте дни, ставьте долгие цели, доводите дела до конца — это делает вас сильнее."""
    # По желанию добавь сюда 1..31 целиком из твоей версии
}

# Zusatz: планеты / профессии по Geisteszahl (минималистично и по делу)
ZUSATZ_INFO = {
    1: "🔭 Planet: Sonne. 💼 Passend: Führung, Entrepreneurship, Product-Owner, Sales.",
    2: "🔭 Planet: Mond. 💼 Passend: HR/Diplomatie, Psychologie, Coaching, Service/Support.",
    3: "🔭 Planet: Jupiter. 💼 Passend: Lehre, Schreiben, Marketing, Reisen/Studium.",
    4: "🔭 Planet: Uranus/Saturn. 💼 Passend: Operations, Engineering, Bau/Architektur.",
    5: "🔭 Planet: Merkur. 💼 Passend: Vertrieb, PR, Medien, SMM, Reisen/Logistik.",
    6: "🔭 Planet: Venus. 💼 Passend: Design, Beauty, Pflege/Medizin, People-Management.",
    7: "🔭 Planet: Neptun/Mars. 💼 Passend: Research, Analytics, Coaching, Kampf-спорт/тренер.",
    8: "🔭 Planet: Saturn/Pluto. 💼 Passend: Management, Finanzen, Recht, Big-Corp/Executive.",
    9: "🔭 Planet: Mars/Neptun. 💼 Passend: Благотворительность, Art, Healing, НКО/социальные проекты.",
}

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

# Namensenergie (Pythagorean) — карта и описания
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
    vals = [NAME_MAP.get(ch) for ch in normalize_latin(text).upper() if ch in NAME_MAP]
    vals = [v for v in vals if v is not None]
    return reduzieren(sum(vals)) if vals else 0

NAME_NUMBER_DESC = {
    1: "Инициатива, лидерство, самостоятельность. Имя даёт тягу начинать и вести.",
    2: "Дипломатия, мягкая сила, чуткость. Имя про отношения и баланс.",
    3: "Коммуникация, креатив, обучение. Имя усиливает слово и самовыражение.",
    4: "Системность, порядок, надёжность. Имя про дисциплину и практичность.",
    5: "Свобода, скорость, продажи/PR. Имя даёт гибкость и харизму.",
    6: "Красота, забота, ответственность. Имя про семью/людей/эстетику.",
    7: "Глубина, анализ, духовность. Имя про исследование и дисциплину ума.",
    8: "Статус, финансы, управление. Имя про результат и власть.",
    9: "Служение, смысл, щедрость. Имя про гуманизм и завершение.",
}

# ========================= UI/STATE =========================
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

WELCOME = ("🌟 <b>Willkommen!</b>\n\n"
"Vor Ihnen liegt <b>KeyToFate</b> – Lehre über Zahlen und Wege.\n\n"
"✨ Lüften Sie den Schleier Ihres Schicksals – und lassen Sie KeyToFate Ihr Wegweiser sein. ✨")
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse", callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie", callback_data="calc_day")],
        [InlineKeyboardButton("🔤 Namensenergie", callback_data="calc_name")],
        # Если нужно, включи и остальные:
        # [InlineKeyboardButton("💞 Partnerschaft", callback_data="calc_compat")],
        # [InlineKeyboardButton("👥 Kollektivenergie", callback_data="calc_group")],
        # [InlineKeyboardButton("🧭 Entwicklungspfad", callback_data="calc_path")],
    ])

# ========================= HANDLERS =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; data = q.data; await q.answer()
    if data=="calc_full":
        await q.message.reply_html("🧮 Geben Sie Geburtsdatum ein (TT.MM.JJJJ):")
        return ASK_FULL
    if data=="calc_day":
        await q.message.reply_html("Geben Sie Ihr Geburtsdatum ein (TT.MM.JJJJ):")
        return ASK_DAY_BIRTH
    if data=="calc_name":
        await q.message.reply_html("Geben Sie den Namen ein (lateinische Schreibweise):")
        return ASK_NAME
    # ниже можно вернуть остальные пункты, если включишь их в меню
    return ConversationHandler.END

# ---- Vollanalyse (ТОЛЬКО Geisteszahl + День рождения + Zusatz + Geldcode) ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip())
        g = geisteszahl(d)
        geld = geldcode(d,m,y)

        parts = [f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>"]
        # Сжатый общий блок по Geisteszahl
        geist_short = GEISTES_TXT.get(g,"")
        parts.append(f"🧠 <b>Geisteszahl {g}</b>\n{html_escape(geist_short)}")
        if g in GEISTES_BLOCK:
            parts.append(html_escape(GEISTES_BLOCK[g]))

        # Описание конкретного дня рождения
        day_text = (DAY_BIRTH_TXT.get(d) or "").strip()
        if day_text:
            parts.append(f"📅 <b>Wenn Sie am {d} geboren sind</b>\n{html_escape(day_text)}")

        # Zusatz (планеты/профессии) — ПОСЛЕ описания дня
        zusatz = ZUSATZ_INFO.get(g)
        if zusatz:
            parts.append(f"➕ <b>Zusätzliche Info</b>\n{html_escape(zusatz)}")

        # Деньги-код
        parts.append(f"💰 <b>Geldcode:</b> <code>{geld}</code>")

        await update.message.reply_html("\n\n".join(parts), reply_markup=back_kb())
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}", reply_markup=back_kb())
        return ASK_FULL

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip()); today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        await update.message.reply_html(
            f"📅 <b>Tagesenergie {today.day:02d}.{today.month:02d}.{today.year}</b>\n\n{html_escape(body)}",
            reply_markup=back_kb()
        )
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}", reply_markup=back_kb())
        return ASK_DAY_BIRTH

# ---- Namensenergie (число + краткое описание) ----
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    val = namensenergie(name)
    desc = NAME_NUMBER_DESC.get(val, "Нет интерпретации.")
    await update.message.reply_html(
        f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>\n\n{html_escape(desc)}",
        reply_markup=back_kb()
    )
    return ConversationHandler.END

# ========================= BOOTSTRAP =========================
def main():
    app = Application.builder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
          ASK_FULL:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full)],
          ASK_DAY_BIRTH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
          ASK_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    print("🤖 KeyToFate läuft. /start → Menü.")
    app.run_polling()

if __name__=="__main__":
    main()
