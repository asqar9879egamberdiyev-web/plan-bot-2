import logging
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import db
import gemini_service
from config import TELEGRAM_BOT_TOKEN
from keyboards import (
    BTN_RESULTS, BTN_AI_PLAN, BTN_AI_CHAT, BTN_MONTHLY, BTN_MY_PLANS, BTN_BACK,
    main_menu_keyboard, back_keyboard, tasks_inline_keyboard,
    month_nav_keyboard, month_days_keyboard, day_entries_keyboard,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


# ---------------------------------------------------------------------------
# Yordamchi funksiya: foydalanuvchi rejimini tozalash (asosiy menyuga qaytish)
# ---------------------------------------------------------------------------
def clear_mode(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("mode", None)
    context.user_data.pop("mode_data", None)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.first_name or "")
    clear_mode(context)
    await update.message.reply_text(
        f"Salom, {user.first_name}! 👋\n\n"
        "Men sizning shaxsiy reja tuzuvchi yordamchingizman.\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=main_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# 1) Natijalarim
# ---------------------------------------------------------------------------
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    stats = db.get_stats(update.effective_user.id)
    total = stats["total_tasks"]
    done = stats["done_tasks"]
    percent = round((done / total) * 100) if total else 0
    text = (
        "📊 <b>Natijalarim</b>\n\n"
        f"📝 Jami vazifalar: {total}\n"
        f"✅ Bajarilgan: {done} ({percent}%)\n"
        f"🤖 AI orqali tuzilgan rejalar: {stats['ai_plans_count']}\n\n"
        f"🗓 Shu oy: {stats['month_done']}/{stats['month_total']} yozuv bajarildi\n"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


# ---------------------------------------------------------------------------
# 2) AI bilan reja tuzish
# ---------------------------------------------------------------------------
async def start_ai_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "ai_plan_goal"
    await update.message.reply_text(
        "🤖 Qanday maqsad yoki vazifa uchun reja tuzib beray?\n"
        "Masalan: \"2 hafta ichida IELTS Reading bo'limini yaxshilash\"",
        reply_markup=back_keyboard(),
    )


async def handle_ai_plan_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal = update.message.text.strip()
    context.user_data["mode_data"] = {"goal": goal}
    context.user_data["mode"] = "ai_plan_days"
    await update.message.reply_text(
        "Nechi kunlik reja kerak? (Raqam kiriting, masalan: 7)",
        reply_markup=back_keyboard(),
    )


async def handle_ai_plan_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    days = int(text) if text.isdigit() else 7
    goal = context.user_data.get("mode_data", {}).get("goal", "")
    await update.message.reply_text("⏳ Reja tuzilmoqda, biroz kuting...")
    try:
        plan_text = gemini_service.generate_plan(goal, days)
    except Exception as e:
        logger.exception("Gemini xatosi (reja)")
        await update.message.reply_text(
            f"❌ Reja tuzishda xatolik yuz berdi: {e}", reply_markup=main_menu_keyboard()
        )
        clear_mode(context)
        return
    db.save_ai_plan(update.effective_user.id, goal, plan_text)
    clear_mode(context)
    # Telegram xabar uzunligi cheklangan (4096), shuning uchun bo'lib yuboramiz
    for chunk_start in range(0, len(plan_text), 3500):
        await update.message.reply_text(plan_text[chunk_start:chunk_start + 3500])
    await update.message.reply_text("✅ Reja saqlandi!", reply_markup=main_menu_keyboard())


# ---------------------------------------------------------------------------
# 3) AI bilan suhbat
# ---------------------------------------------------------------------------
async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "ai_chat"
    await update.message.reply_text(
        "💬 AI bilan suhbat boshlandi. Xohlagan narsangizni yozing.\n"
        "Chiqish uchun \"⬅️ Bosh menyu\" tugmasini bosing.",
        reply_markup=back_keyboard(),
    )


async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    history_rows = db.get_chat_history(user_id, limit=20)
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows]
    await update.message.chat.send_action("typing")
    try:
        reply = gemini_service.chat_reply(history, user_message)
    except Exception as e:
        logger.exception("Gemini xatosi (chat)")
        await update.message.reply_text(f"❌ Xatolik: {e}")
        return
    db.add_chat_message(user_id, "user", user_message)
    db.add_chat_message(user_id, "model", reply)
    await update.message.reply_text(reply, reply_markup=back_keyboard())


# ---------------------------------------------------------------------------
# 4) Oylik rejalar (Notion uslubida)
# ---------------------------------------------------------------------------
async def show_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    now = datetime.now()
    await send_month_view(update.effective_chat.id, context, update.effective_user.id, now.year, now.month, update)


async def send_month_view(chat_id, context, user_id, year, month, update=None):
    entries = db.get_month_entries(user_id, year, month)
    days_with_entries = {e["day"] for e in entries}
    text = f"🗓 <b>{year}-yil, oy: {month}</b>\nKunni tanlang yoki yangi yozuv qo'shing:"
    kb = month_days_keyboard(year, month, days_with_entries)
    if update and update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await context.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)


async def monthly_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "noop":
        return

    if data.startswith("month_nav:"):
        year, month = map(int, data.split(":")[1].split("-"))
        entries = db.get_month_entries(user_id, year, month)
        days_with_entries = {e["day"] for e in entries}
        await query.edit_message_text(
            f"🗓 <b>{year}-yil, oy: {month}</b>\nKunni tanlang yoki yangi yozuv qo'shing:",
            parse_mode="HTML",
            reply_markup=month_days_keyboard(year, month, days_with_entries),
        )

    elif data.startswith("day_view:"):
        year, month, day = map(int, data.split(":")[1].split("-"))
        entries = db.get_day_entries(user_id, year, month, day)
        header = f"🗓 {year}-{month:02d}-{day:02d} kuni uchun yozuvlar:"
        if not entries:
            header += "\n\n(Hali yozuv yo'q)"
        await query.edit_message_text(
            header, reply_markup=day_entries_keyboard(year, month, day, entries)
        )

    elif data.startswith("day_add:"):
        year, month = map(int, data.split(":")[1].split("-"))
        context.user_data["mode"] = "monthly_add_pick_day"
        context.user_data["mode_data"] = {"year": year, "month": month}
        await query.message.reply_text(
            f"Qaysi kun uchun? (1 dan {31} gacha raqam kiriting)",
            reply_markup=back_keyboard(),
        )

    elif data.startswith("day_add_one:"):
        year, month, day = map(int, data.split(":")[1].split("-"))
        context.user_data["mode"] = "monthly_add_text"
        context.user_data["mode_data"] = {"year": year, "month": month, "day": day}
        await query.message.reply_text(
            f"{year}-{month:02d}-{day:02d} uchun matn kiriting:",
            reply_markup=back_keyboard(),
        )

    elif data.startswith("entry_toggle:"):
        entry_id = int(data.split(":")[1])
        db.toggle_monthly_entry(entry_id, user_id)
        # ekranni yangilash uchun entry orqali kun/oyni topamiz
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT year, month, day FROM monthly_entries WHERE id=?", (entry_id,)
            ).fetchone()
        if row:
            entries = db.get_day_entries(user_id, row["year"], row["month"], row["day"])
            await query.edit_message_reply_markup(
                reply_markup=day_entries_keyboard(row["year"], row["month"], row["day"], entries)
            )

    elif data.startswith("entry_del:"):
        entry_id = int(data.split(":")[1])
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT year, month, day FROM monthly_entries WHERE id=?", (entry_id,)
            ).fetchone()
        db.delete_monthly_entry(entry_id, user_id)
        if row:
            entries = db.get_day_entries(user_id, row["year"], row["month"], row["day"])
            await query.edit_message_reply_markup(
                reply_markup=day_entries_keyboard(row["year"], row["month"], row["day"], entries)
            )

    elif data.startswith("task_toggle:"):
        task_id = int(data.split(":")[1])
        with db.get_conn() as conn:
            row = conn.execute(
                "SELECT status FROM tasks WHERE id=? AND user_id=?", (task_id, user_id)
            ).fetchone()
        if row:
            new_status = "pending" if row["status"] == "done" else "done"
            db.set_task_status(task_id, user_id, new_status)
        tasks = db.get_tasks(user_id)
        kb = tasks_inline_keyboard(tasks)
        await query.edit_message_reply_markup(reply_markup=kb)

    elif data.startswith("task_del:"):
        task_id = int(data.split(":")[1])
        db.delete_task(task_id, user_id)
        tasks = db.get_tasks(user_id)
        kb = tasks_inline_keyboard(tasks)
        if kb:
            await query.edit_message_reply_markup(reply_markup=kb)
        else:
            await query.edit_message_text("📝 Hozircha rejalar yo'q.")


async def handle_monthly_add_pick_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 31):
        await update.message.reply_text("Iltimos, 1 dan 31 gacha to'g'ri raqam kiriting.")
        return
    day = int(text)
    md = context.user_data.get("mode_data", {})
    md["day"] = day
    context.user_data["mode_data"] = md
    context.user_data["mode"] = "monthly_add_text"
    await update.message.reply_text(f"Endi {day}-kun uchun matn kiriting:", reply_markup=back_keyboard())


async def handle_monthly_add_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    md = context.user_data.get("mode_data", {})
    year, month, day = md.get("year"), md.get("month"), md.get("day")
    db.add_monthly_entry(update.effective_user.id, year, month, day, text)
    clear_mode(context)
    await update.message.reply_text(
        f"✅ {year}-{month:02d}-{day:02d} kuniga yozuv qo'shildi!", reply_markup=main_menu_keyboard()
    )


# ---------------------------------------------------------------------------
# 5) Rejalarim (umumiy vazifalar ro'yxati)
# ---------------------------------------------------------------------------
async def show_my_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    tasks = db.get_tasks(update.effective_user.id)
    kb = tasks_inline_keyboard(tasks)
    text = "📝 <b>Rejalarim</b>\n\nYangi reja qo'shish uchun matn yozing." if not tasks else \
        "📝 <b>Rejalarim</b>\n\nBajarilganini belgilash uchun ustiga bosing.\nYangisini qo'shish uchun shunchaki matn yozing."
    context.user_data["mode"] = "add_task"
    if kb:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        await update.message.reply_text("Yangi reja qo'shish uchun matn kiriting:", reply_markup=back_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=back_keyboard())


async def handle_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    db.add_task(update.effective_user.id, title)
    await update.message.reply_text(f"✅ Qo'shildi: {title}")
    tasks = db.get_tasks(update.effective_user.id)
    kb = tasks_inline_keyboard(tasks)
    if kb:
        await update.message.reply_text("📝 Joriy rejalar:", reply_markup=kb)


# ---------------------------------------------------------------------------
# Markazlashgan matn xabarlar routeri (rejim asosida)
# ---------------------------------------------------------------------------
async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == BTN_BACK:
        clear_mode(context)
        await update.message.reply_text("Bosh menyu:", reply_markup=main_menu_keyboard())
        return

    if text == BTN_RESULTS:
        await show_results(update, context)
        return
    if text == BTN_AI_PLAN:
        await start_ai_plan(update, context)
        return
    if text == BTN_AI_CHAT:
        await start_ai_chat(update, context)
        return
    if text == BTN_MONTHLY:
        await show_monthly(update, context)
        return
    if text == BTN_MY_PLANS:
        await show_my_plans(update, context)
        return

    mode = context.user_data.get("mode")
    if mode == "ai_plan_goal":
        await handle_ai_plan_goal(update, context)
    elif mode == "ai_plan_days":
        await handle_ai_plan_days(update, context)
    elif mode == "ai_chat":
        await handle_ai_chat(update, context)
    elif mode == "add_task":
        await handle_add_task(update, context)
    elif mode == "monthly_add_pick_day":
        await handle_monthly_add_pick_day(update, context)
    elif mode == "monthly_add_text":
        await handle_monthly_add_text(update, context)
    else:
        await update.message.reply_text(
            "Iltimos, quyidagi menyudan tanlang:", reply_markup=main_menu_keyboard()
        )


# ---------------------------------------------------------------------------
# Kunlik avtomatik xabarlar (08:00 / 12:00 / 18:00, Toshkent vaqti)
# ---------------------------------------------------------------------------
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    period = context.job.data["period"]
    now = datetime.now(TASHKENT_TZ)

    for user_id in db.get_all_user_ids():
        try:
            if period == "morning":
                entries = db.get_day_entries(user_id, now.year, now.month, now.day)
                if entries:
                    lines = "\n".join(f"• {e['text']}" for e in entries)
                    text = f"🌅 Xayrli tong!\n\nBugungi rejalaringiz:\n{lines}"
                else:
                    text = (
                        "🌅 Xayrli tong!\n\n"
                        "Bugun uchun hali yozuv qo'shilmagan. \"🗓 Oylik rejalar\" "
                        "bo'limidan bugungi kunga reja qo'shib qo'ying."
                    )
            elif period == "noon":
                pending = db.get_tasks(user_id, status="pending")
                text = (
                    f"🕛 Kun yarmiga keldi!\n\n"
                    f"Bajarilmagan vazifalar: {len(pending)} ta.\n"
                    f"Davom eting, hali vaqt bor! 💪"
                )
            else:  # evening
                stats = db.get_stats(user_id)
                text = (
                    "🌆 Kun yakunlanmoqda.\n\n"
                    f"✅ Bugungi holat: {stats['month_done']}/{stats['month_total']} "
                    f"oylik yozuv, {stats['done_tasks']}/{stats['total_tasks']} umumiy vazifa bajarilgan.\n"
                    "Ertangi kun uchun ham reja tuzib qo'yishni unutmang!"
                )
            await context.bot.send_message(user_id, text, reply_markup=main_menu_keyboard())
        except Exception:
            # Foydalanuvchi botni bloklagan yoki boshqa xato — davom etamiz
            logger.warning("Foydalanuvchi %s ga eslatma yuborib bo'lmadi", user_id)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    db.init_db()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(monthly_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))

    job_queue = app.job_queue
    job_queue.run_daily(
        send_daily_reminder, time=dtime(hour=8, minute=0, tzinfo=TASHKENT_TZ),
        data={"period": "morning"}, name="morning_reminder",
    )
    job_queue.run_daily(
        send_daily_reminder, time=dtime(hour=12, minute=0, tzinfo=TASHKENT_TZ),
        data={"period": "noon"}, name="noon_reminder",
    )
    job_queue.run_daily(
        send_daily_reminder, time=dtime(hour=18, minute=0, tzinfo=TASHKENT_TZ),
        data={"period": "evening"}, name="evening_reminder",
    )

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
