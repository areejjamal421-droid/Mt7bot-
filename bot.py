import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ضع توكن البوت الخاص بك هنا
TOKEN = "9109483206:AAG60PTMWYKmkhtHFZJ5OdfShYAm9vD0D30"

# معرف الأدمن الخاص بك على تيليجرام (رقم الـ ID)
ADMIN_ID = 8292471160  # استبدله بـ ID الخاص بك

DATA_FILE = "database.json"

# تحميل أو إنشاء قاعدة البيانات
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"subjects": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

# دالة لتحديث لوحة المفاتيح التحتية للمواد
def get_main_keyboard():
    subjects = list(data["subjects"].keys())
    keyboard = [[subj] for subj in subjects]
    # أزرار إضافية للأدمن إذا كان في القائمة الرئيسية (يمكن تنظيمها حسب الرغبة)
    keyboard.append(["📚 الرئيسية"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    welcome_text = "أهلاً بك في بوت الشيتات والمواد الدراسية! اختر المادة من الأزرار بالأسفل:"
    
    if user_id == ADMIN_ID:
        welcome_text += "\n\nأهلاً بك يا أدمن. يمكنك استخدام الأوامر التالية لإدارة المحتوى:\n" \
                        "➕ لإضافة مادة: `/add_subject <اسم المادة>`\n" \
                        "❌ لحذف مادة: `/del_subject <اسم المادة>`\n" \
                        "📄 لإضافة شيت لمادة: `/add_sheet <اسم المادة> | <رابط أو وصف الشيت>`\n" \
                        "🗑️ لحذف شيت: `/del_sheet <اسم المادة> <رقم الشيت>`"

    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# --- أوامر الأدمن ---

async def add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء كتابة اسم المادة. مثال: `/add_subject الرياضيات`", parse_mode="Markdown")
        return

    subject_name = " ".join(context.args)
    if subject_name not in data["subjects"]:
        data["subjects"][subject_name] = []
        save_data(data)
        await update.message.reply_text(f"تم إضافة المادة '{subject_name}' بنجاح!", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("هذه المادة موجودة مسبقاً.")

async def del_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("الرجاء كتابة اسم المادة المراد حذفها.")
        return

    subject_name = " ".join(context.args)
    if subject_name in data["subjects"]:
        del data["subjects"][subject_name]
        save_data(data)
        await update.message.reply_text(f"تم حذف المادة '{subject_name}' بنجاح.", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("المادة غير موجودة.")

async def add_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("الصيغة خاطئة. استخدم:\n`/add_sheet اسم المادة | رابط الشيت أو وصفه`", parse_mode="Markdown")
        return

    subject_name, sheet_info = text.split("|", 1)
    subject_name = subject_name.strip()
    sheet_info = sheet_info.strip()

    if subject_name in data["subjects"]:
        data["subjects"][subject_name].append(sheet_info)
        save_data(data)
        await update.message.reply_text(f"تم إضافة الشيت بنجاح إلى مادة '{subject_name}'!")
    else:
        await update.message.reply_text("المادة غير موجودة. تأكد من الاسم أو قم بإضافتها أولاً.")

# --- التعامل مع اختيار المواد من الأزرار السفلى ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📚 الرئيسية":
        await update.message.reply_text("القائمة الرئيسية:", reply_markup=get_main_keyboard())
        return

    # إذا الضغطة تطابق إحدى المواد، نعرض كل الشيتات دفعة واحدة
    if text in data["subjects"]:
        sheets = data["subjects"][text]
        if not sheets:
            await update.message.reply_text(f"لا توجد شيتات مضافة حالياً لمادة **{text}**.", parse_mode="Markdown")
            return

        response = f"📂 **شيتات مادة {text}:**\n\n"
        for i, sheet in enumerate(sheets, 1):
            response += f"{i}. {sheet}\n"
        
        await update.message.reply_text(response, parse_mode="Markdown")
    else:
        await update.message.reply_text("الرجاء اختيار مادة من الأزرار الموجودة أسفل الشات.", reply_markup=get_main_keyboard())

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_subject", add_subject))
    app.add_handler(CommandHandler("del_subject", del_subject))
    app.add_handler(CommandHandler("add_sheet", add_sheet))

    # الرد على الأزرار النصية السفلية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
          
