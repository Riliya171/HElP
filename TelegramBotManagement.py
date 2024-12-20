from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests

# آدرس API
API_URL = "http://130.185.73.93:4999/api/air-quality"

# آیدی عددی ادمین
ADMIN_ID = 7501482979  # آیدی عددی ادمین را اینجا وارد کنید

# شمارنده آمار استفاده
stats = {"group": 0, "private": 0}

# لیست کاربران محدود شده
banned_users = set()

# حالت‌ها برای کنترل وضعیت‌های محدود کردن/رفع محدودیت
admin_states = {
    "awaiting_user_id_for_ban": False,
    "awaiting_user_id_for_unban": False
}


# تابعی برای چک کردن محدودیت کاربر (برای همه دستورات)
async def is_user_banned(update: Update):
    user_id = update.effective_user.id
    if user_id in banned_users:
        await update.message.reply_text("⛔️ شما محدود شده‌اید و اجازه دسترسی به ربات را ندارید.")
        return True
    return False


# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # چک محدودیت کاربر
    if await is_user_banned(update):
        return

    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    # شمارنده آمار استفاده
    if chat_type == "private":
        stats["private"] += 1
    else:
        stats["group"] += 1

    # ساختن دکمه
    keyboard = [
        [InlineKeyboardButton("📊 دریافت شاخص تهران", callback_data="get_aqi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! من بات شاخص هوای تهران هستم.\n"
        "برای دریافت شاخص کیفیت هوای تهران روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )


# دستور جدید /statsth
async def statsthdef(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # چک محدودیت کاربر
    if await is_user_banned(update):
        return

    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            current_index = data["current_index"]
            await update.message.reply_text(f"شاخص کنونی تهران: {current_index}")
        else:
            await update.message.reply_text(f"خطا در دریافت اطلاعات: کد وضعیت {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"خطا در ارتباط با سرور: {e}")


# دستور /panel برای مدیریت ربات
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # بررسی اینکه فقط ادمین و فقط در پیوی از این دستور استفاده کنند
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔️ شما مجاز به دسترسی به این بخش نیستید.")
        return

    if update.message.chat.type != "private":
        await update.message.reply_text("⛔️ این دستور فقط در چت خصوصی با ربات قابل استفاده است.")
        return

    # ساختن دکمه‌های پنل مدیریت
    keyboard = [
        [InlineKeyboardButton("⛔️ خاموش کردن بات", callback_data="shutdown")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="stats")],
        [InlineKeyboardButton("🚫 محدود کردن کاربر", callback_data="ban_user")],
        [InlineKeyboardButton("✅ رفع محدودیت کاربر", callback_data="unban_user")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("👮‍♂️ پنل مدیریت:", reply_markup=reply_markup)


# تابع دریافت آیدی کاربران و اعمال محدودیت یا رفع محدودیت
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.message.chat.type

    # فقط ادمین قادر به انجام این عملیات است
    if user_id != ADMIN_ID:
        return

    # بررسی اینکه فقط در چت خصوصی این عملیات انجام شود
    if chat_type != "private":
        await update.message.reply_text("⛔️ این عملیات فقط در چت خصوصی انجام می‌شود.")
        return

    # دریافت متن پیام و اطمینان از اینکه آیدی عددی است
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⛔️ لطفاً فقط آیدی عددی معتبر وارد کنید.")
        return

    user_id_to_process = int(text)

    # محدود کردن کاربر
    if admin_states["awaiting_user_id_for_ban"]:
        banned_users.add(user_id_to_process)
        admin_states["awaiting_user_id_for_ban"] = False
        await update.message.reply_text(f"⛔️ کاربر با آیدی {user_id_to_process} محدود شد.")

    # رفع محدودیت کاربر
    elif admin_states["awaiting_user_id_for_unban"]:
        if user_id_to_process in banned_users:
            banned_users.remove(user_id_to_process)
            admin_states["awaiting_user_id_for_unban"] = False
            await update.message.reply_text(f"✅ کاربر با آیدی {user_id_to_process} از محدودیت خارج شد.")
        else:
            await update.message.reply_text(f"⛔️ کاربر با آیدی {user_id_to_process} در لیست محدودیت نیست.")
    else:
        await update.message.reply_text("⛔️ عملیاتی انتخاب نشده است.")

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # پاسخ به کلیک کاربر

    # بررسی callback_data
    if query.data == "get_aqi":
        await query.edit_message_text("لطفاً صبر کنید، در حال دریافت اطلاعات...")
        aqi_info = await get_tehran_aqi()
        await query.edit_message_text(aqi_info)



# تابع اصلی
def main():
    # توکن ربات خود را اینجا وارد کنید
    TELEGRAM_TOKEN = "7890720418:AAG5aXtLagc5iAFswRkjBDnYjvCkHwwO2kE"

    # ساختن یک برنامه با ApplicationBuilder
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # اضافه کردن هندلر برای دستور /start
    app.add_handler(CommandHandler("start", start))

    # اضافه کردن هندلر برای دستور /statsth
    app.add_handler(CommandHandler("statsth", statsthdef))

    # اضافه کردن هندلر برای دستور /panel
    app.add_handler(CommandHandler("panel", panel))

    # اضافه کردن هندلر برای کلیک روی دکمه
    app.add_handler(CallbackQueryHandler(handle_button_click))

    # اضافه کردن هندلر برای پردازش پیام‌های متنی (برای آیدی کاربران)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # اجرا
    app.run_polling()


if __name__ == '__main__':
    main()
