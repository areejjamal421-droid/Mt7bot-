import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ضع توكن البوت الخاص بك هنا
TOKEN = "9109483206:AAG60PTMWYKmkhtHFZJ5OdfShYAm9vD0D30"

# ضع آيدي الأدمن الخاص بك هنا (رقم التيليجرام الخاص بك)
ADMIN_ID = 8292471160  # استبدل الرقم برقمك الحقيقي

# قائمة المواد الافتراضية المطلوبة
INITIAL_SUBJECTS = [
    "Histology",
    "Physiology",
    "Microbiology",
    "Anatomy",
    "Biochemistry",
    "Dental material",
    "Pathology",
    "الإدارة الصحية",
    "الثقافة الوطنية",
    "علم النفس الطبي",
    "أخلاقيات المهنة",
]


# --- إعداد قاعدة البيانات ---
def init_db():
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()

  # جدول المواد
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

  # جدول الشيتات (الملفات)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            file_name TEXT,
            file_id TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    """)

  conn.commit()

  # إضافة المواد الافتراضية إذا لم تكن موجودة
  for sub in INITIAL_SUBJECTS:
    cursor.execute(
        "INSERT OR IGNORE INTO subjects (name) VALUES (?)", (sub,)
    )
  conn.commit()
  conn.close()


init_db()


# --- دوال مساعدة للبث والتفاعل ---
def get_subjects():
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT id, name FROM subjects")
  subs = cursor.fetchall()
  conn.close()
  return subs


def get_sheets(subject_id):
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, file_name, file_id FROM sheets WHERE subject_id = ?",
      (subject_id,),
  )
  sheets = cursor.fetchall()
  conn.close()
  return sheets


# --- أوامر البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  subs = get_subjects()

  keyboard = []
  # ترتيب المواد في أزرار تحت بعضها أو جنب بعضها (هنا كل مادة في زر منفصل تحت)
  for sub_id, sub_name in subs:
    keyboard.append(
        [InlineKeyboardButton(sub_name, callback_data=f"sub_{sub_id}")]
    )

  # لو كان المستخدم هو الأدمن، نضيف له أزرار لوحة التحكم
  if user_id == ADMIN_ID:
    keyboard.append(
        [InlineKeyboardButton("⚙️ لوحة التحكم (أدمن)", callback_data="admin_panel")]
    )

  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text(
      "مرحباً بك في بوت الشيتات والدراسة 📚\nاختر المادة لعرض الشيتات الخاصة بها:",
      reply_markup=reply_markup,
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  user_id = query.from_user.id
  await query.answer()

  data = query.data

  if data.startswith("sub_"):
    sub_id = int(data.split("_")[1])

    # جلب اسم المادة
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM subjects WHERE id = ?", (sub_id,))
    sub_name = cursor.fetchone()[0]
    conn.close()

    sheets = get_sheets(sub_id)

    keyboard = []
    if sheets:
      for sheet_id, file_name, file_id in sheets:
        # زر لكل شيت بحيث يقدر المستخدم يحمله مباشرة أو يفتحه
        # (بما أن تيليجرام ما يدعمش تحميل مباشر من زر Inline بملف، نقدروا نبعتوه لما يضغط أو نعرض اسمه ونخليه يطلب ملف)
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📄 {file_name}", callback_data=f"getsheet_{sheet_id}"
                )
            ]
        )

        # لو المستخدم هو الأدمن نعطيه خيار حذف الشيت هذا
        if user_id == ADMIN_ID:
          keyboard[-1].append(
              InlineKeyboardButton(
                  "❌ حذف", callback_data=f"del_sheet_{sheet_id}"
              )
          )

    # زر رجوع للقائمة الرئيسية
    keyboard.append(
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="home")]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=(
            f"📚 مادة: **{sub_name}**\nإليك الشيتات المتاحة لهذه المادة (اضغط على"
            " الشيت لفتحه):"
        ),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  elif data == "home":
    subs = get_subjects()
    keyboard = []
    for sub_id, sub_name in subs:
      keyboard.append(
          [InlineKeyboardButton(sub_name, callback_data=f"sub_{sub_id}")]
      )

    if user_id == ADMIN_ID:
      keyboard.append(
          [
              InlineKeyboardButton(
                  "⚙️ لوحة التحكم (أدمن)", callback_data="admin_panel"
              )
          ]
      )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="اختر المادة لعرض الشيتات الخاصة بها:", reply_markup=reply_markup
    )

  elif data == "admin_panel" and user_id == ADMIN_ID:
    keyboard = [
        [InlineKeyboardButton("➕ إضافة مادة جديدة", callback_data="add_sub")],
        [InlineKeyboardButton("➖ حذف مادة", callback_data="remove_sub_menu")],
        [InlineKeyboardButton("📤 إضافة شيت لمادة", callback_data="add_sheet_menu")],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="home")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="⚙️ **لوحة تحكم الأدمن**\nاختر العملية المطلوبة:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

  elif data == "add_sub" and user_id == ADMIN_ID:
    context.user_data["waiting_for"] = "add_sub"
    await query.message.reply_text(
        "أرسل الآن **اسم المادة الجديدة** التي تريد إضافتها:"
    )

  elif data == "remove_sub_menu" and user_id == ADMIN_ID:
    subs = get_subjects()
    keyboard = []
    for sub_id, sub_name in subs:
      keyboard.append(
          [
              InlineKeyboardButton(
                  f"حذف: {sub_name}", callback_data=f"delsub_{sub_id}"
              )
          ]
      )
    keyboard.append(
        [InlineKeyboardButton("🔙 رجوع لوحة التحكم", callback_data="admin_panel")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="اختر المادة التي تريد حذفها (سيتم حذف شيتاتها معها):",
        reply_markup=reply_markup,
    )

  elif data.startswith("delsub_") and user_id == ADMIN_ID:
    sub_id = int(data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sheets WHERE subject_id = ?", (sub_id,))
    cursor.execute("DELETE FROM subjects WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
    await query.edit_message_text(
        text="✅ تم حذف المادة بنجاح!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔙 رجوع لوحة التحكم", callback_data="admin_panel"
            )
        ]]),
    )

  elif data == "add_sheet_menu" and user_id == ADMIN_ID:
    subs = get_subjects()
    keyboard = []
    for sub_id, sub_name in subs:
      keyboard.append(
          [
              InlineKeyboardButton(
                  sub_name, callback_data=f"picksub_for_sheet_{sub_id}"
              )
          ]
      )
    keyboard.append(
        [InlineKeyboardButton("🔙 رجوع لوحة التحكم", callback_data="admin_panel")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="اختر المادة التي تريد إضافة شيت لها:", reply_markup=reply_markup
    )

  elif data.startswith("picksub_for_sheet_") and user_id == ADMIN_ID:
    sub_id = int(data.split("_")[3])
    context.user_data["target_sub_id"] = sub_id
    context.user_data["waiting_for"] = "upload_sheet"
    await query.message.reply_text(
        "أرسل الآن **ملف الشيت (PDF أو مستند)** مع كتابة اسم الشيت في الوصف (Caption) أو كرسالة تالية:"
    )

  elif data.startswith("getsheet_"):
    sheet_id = int(data.split("_")[1])
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, file_name FROM sheets WHERE id = ?", (sheet_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
      file_id, file_name = row
      await context.bot.send_document(
          chat_id=update.effective_chat.id,
          document=file_id,
          caption=f"📄 {file_name}",
      )

  elif data.startswith("del_sheet_") and user_id == ADMIN_ID:
    sheet_id = int(data.split("_")[2])
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))
    conn.commit()
    conn.close()
    await query.answer("تم حذف الشيت بنجاح!", show_alert=True)


# --- معالجة الرسائل النصية والملفاتی للآدمن ---
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_id = update.effective_user.id
  if user_id != ADMIN_ID:
    return

  waiting = context.user_data.get("waiting_for")

  if waiting == "add_sub":
    new_sub_name = update.message.text
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
      cursor.execute("INSERT INTO subjects (name) VALUES (?)", (new_sub_name,))
      conn.commit()
      await update.message.reply_text(
          f"✅ تمت إضافة المادة ({new_sub_name}) بنجاح!"
      )
    except sqlite3.IntegrityError:
      await update.message.reply_text("⚠️ هذه المادة موجودة مسبقاً!")
    conn.close()
    context.user_data["waiting_for"] = None

  elif waiting == "upload_sheet":
    if update.message.document:
      file_id = update.message.document.file_id
      file_name = (
          update.message.caption
          or update.message.document.file_name
          or "شيت جديد"
      )
      sub_id = context.user_data.get("target_sub_id")

      conn = sqlite3.connect("bot_database.db")
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO sheets (subject_id, file_name, file_id) VALUES (?, ?, ?)",
          (sub_id, file_name, file_id),
      )
      conn.commit()
      conn.close()

      await update.message.reply_text(
          f"✅ تم رفع وحفظ الشيت ({file_name}) بنجاح تحت المادة المختارة!"
      )
      context.user_data["waiting_for"] = None
      context.user_data["target_sub_id"] = None
    else:
      await update.message.reply_text(
          "⚠️ من فضلك أرسل ملف (Document / PDF) حقيقي وليس نصاً."
      )


def main():
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CallbackQueryHandler(button_handler))
  app.add_handler(
      MessageHandler(
          filters.TEXT & ~filters.COMMAND, handle_admin_input
      )
  )
  app.add_handler(filters.Document.ALL & ~filters.COMMAND)  # معالجة الملفات
  app.add_handler(
      MessageHandler(filters.Document.ALL, handle_admin_input)
  )  # استقبال الملفات من الأدمن

  print("البوت يعمل الآن...")
  app.run_polling()


if __name__ == "__main__":
  main()
        
