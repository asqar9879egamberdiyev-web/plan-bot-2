from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import calendar

BTN_RESULTS = "📊 Natijalarim"
BTN_AI_PLAN = "🤖 AI bilan reja tuzish"
BTN_AI_CHAT = "💬 AI bilan suhbat"
BTN_MONTHLY = "🗓 Oylik rejalar"
BTN_MY_PLANS = "📝 Rejalarim"
BTN_BACK = "⬅️ Bosh menyu"

MONTH_NAMES_UZ = [
    "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            [BTN_RESULTS, BTN_AI_PLAN],
            [BTN_AI_CHAT, BTN_MONTHLY],
            [BTN_MY_PLANS],
        ],
        resize_keyboard=True,
    )


def back_keyboard():
    return ReplyKeyboardMarkup([[BTN_BACK]], resize_keyboard=True)


def tasks_inline_keyboard(tasks):
    rows = []
    for t in tasks:
        mark = "✅" if t["status"] == "done" else "⬜️"
        label = f'{mark} {t["title"][:35]}'
        rows.append([
            InlineKeyboardButton(label, callback_data=f"task_toggle:{t['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"task_del:{t['id']}"),
        ])
    return InlineKeyboardMarkup(rows) if rows else None


def month_nav_keyboard(year: int, month: int):
    prev_month = month - 1 or 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️", callback_data=f"month_nav:{prev_year}-{prev_month}"),
            InlineKeyboardButton(f"{MONTH_NAMES_UZ[month]} {year}", callback_data="noop"),
            InlineKeyboardButton("▶️", callback_data=f"month_nav:{next_year}-{next_month}"),
        ]
    ])


def month_days_keyboard(year: int, month: int, days_with_entries: set):
    _, num_days = calendar.monthrange(year, month)
    rows = []
    row = []
    for day in range(1, num_days + 1):
        label = f"{day}•" if day in days_with_entries else str(day)
        row.append(InlineKeyboardButton(label, callback_data=f"day_view:{year}-{month}-{day}"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("➕ Yangi kun yozuvi", callback_data=f"day_add:{year}-{month}")])
    return InlineKeyboardMarkup(rows)


def day_entries_keyboard(year: int, month: int, day: int, entries):
    rows = []
    for e in entries:
        mark = "✅" if e["done"] else "⬜️"
        rows.append([
            InlineKeyboardButton(f'{mark} {e["text"][:30]}', callback_data=f"entry_toggle:{e['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"entry_del:{e['id']}"),
        ])
    rows.append([InlineKeyboardButton("➕ Qo'shish", callback_data=f"day_add_one:{year}-{month}-{day}")])
    rows.append([InlineKeyboardButton("⬅️ Oyga qaytish", callback_data=f"month_nav:{year}-{month}")])
    return InlineKeyboardMarkup(rows)
