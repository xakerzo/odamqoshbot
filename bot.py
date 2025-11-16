import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import asyncio
from dotenv import load_dotenv

# .env faylidan o'qish
load_dotenv()

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ma'lumotlarni saqlash uchun fayl
DATA_FILE = 'group_data.json'

# Environment variables dan o'qish
OWNER_ID = int(os.getenv('OWNER_ID', '1373647'))
TOKEN = os.getenv('TOKEN', '7383197624:AAEXFEhfjeLnmMFVkwG6m00Wttga7gF0S7w')

# PORT ni o'qish (Railway uchun)
PORT = int(os.environ.get('PORT', 8443))

def load_data():
    """Ma'lumotlarni yuklash"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ma'lumotlarni yuklashda xato: {e}")
    return {}

def save_data(data):
    """Ma'lumotlarni saqlash"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ma'lumotlarni saqlashda xato: {e}")

def is_owner(user_id):
    """Foydalanuvchi owner ekanligini tekshirish"""
    return user_id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user_id = update.message.from_user.id
    chat_type = update.message.chat.type
    
    # Agar shaxsiy chatda va owner bo'lsa
    if chat_type == 'private' and is_owner(user_id):
        await show_admin_panel(update, context)
    # Agar guruhda bo'lsa
    elif chat_type in ['group', 'supergroup']:
        await show_group_commands(update, context)
    else:
        await update.message.reply_text("Bot faqat guruhlarda ishlaydi!")

async def show_group_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhda komandalarni ko'rsatish"""
    group_commands = (
        "👋 **Guruh boshqaruvi**\n\n"
        "🔧 **Quyidagi komandalardan foydalaning:**\n"
        "• /setlimit - Odam qo'shish sonini belgilash\n"
        "• /freemode - Taqiqni olib tashlash\n"
        "• /status - Joriy holatni ko'rish\n\n"
        "Bot yangi a'zolar ma'lum sonida odam qo'shmaguncha chatda yozishni bloklaydi."
    )
    await update.message.reply_text(group_commands, parse_mode='Markdown')

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner uchun admin panelni ko'rsatish (faqat shaxsiy chatda)"""
    data = load_data()
    total_groups = len(data)
    
    # Faol guruhlarni hisoblash
    active_groups = 0
    total_members = 0
    
    for chat_id, group_data in data.items():
        if group_data.get('active', False):
            active_groups += 1
        total_members += group_data.get('initial_member_count', 0)
    
    admin_text = (
        "👑 **Owner Admin Panel**\n\n"
        f"📊 **Statistika:**\n"
        f"• Jami guruhlar: {total_groups}\n"
        f"• Faol guruhlar: {active_groups}\n"
        f"• Taxminiy a'zolar: {total_members}\n\n"
        "🛠 **Buyruqlar:**\n"
        "• /stats - Batafsil statistika\n"
        "• /broadcast - Xabar yuborish\n"
        "• /groups - Guruhlar ro'yxati\n"
        "• /admin - Admin panel"
    )
    
    await update.message.reply_text(admin_text)

async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh uchun limitni o'rnatish"""
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Bu komanda faqat guruhlarda ishlaydi!")
        return

    # Administratorlikni tekshirish
    try:
        chat_member = await update.message.chat.get_member(update.message.from_user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Faqat administratorlar bu komandadan foydalanishlari mumkin!")
            return
    except Exception as e:
        logger.error(f"Admin tekshirishda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi!")
        return

    if not context.args:
        await update.message.reply_text(
            "🔢 **Limit o'rnatish:**\n\n"
            "Ishlatish: /setlimit <son>\n\n"
            "Misol: /setlimit 5\n"
            "Bu yangi a'zolar 5 ta yangi a'zo qo'shguncha chatda yozolmaydi."
        )
        return

    try:
        limit = int(context.args[0])
        if limit < 1:
            await update.message.reply_text("❌ Limit 1 dan katta bo'lishi kerak!")
            return

        chat_id = str(update.message.chat.id)
        data = load_data()
        
        if chat_id not in data:
            data[chat_id] = {}
        
        data[chat_id]['limit'] = limit
        data[chat_id]['title'] = update.message.chat.title
        data[chat_id]['initial_member_count'] = await update.message.chat.get_member_count()
        data[chat_id]['active'] = True  # Taqiq faol
        save_data(data)

        await update.message.reply_text(
            f"✅ **Limit {limit} a'zoga o'rnatildi!**\n\n"
            f"Endi har bir yangi a'zo {limit} ta yangi a'zo qo'shguncha chatda yozolmaydi.\n\n"
            f"Taqiqni olib tashlash uchun: /freemode"
        )

    except ValueError:
        await update.message.reply_text("❌ Iltimos, raqam kiriting!\nMisol: /setlimit 5")
    except Exception as e:
        logger.error(f"Limit o'rnatishda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi!")

async def freemode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taqiqni olib tashlash"""
    if update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Bu komanda faqat guruhlarda ishlaydi!")
        return

    # Administratorlikni tekshirish
    try:
        chat_member = await update.message.chat.get_member(update.message.from_user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Faqat administratorlar bu komandadan foydalanishlari mumkin!")
            return
    except Exception as e:
        logger.error(f"Admin tekshirishda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi!")
        return

    chat_id = str(update.message.chat.id)
    data = load_data()
    
    if chat_id not in data or 'limit' not in data[chat_id]:
        await update.message.reply_text("❌ Hali limit o'rnatilmagan! Avval /setlimit bilan limit o'rnating.")
        return

    # Taqiqni o'chirish
    data[chat_id]['active'] = False
    save_data(data)

    await update.message.reply_text(
        "✅ **Taqiq olib tashlandi!**\n\n"
        "Endi barcha a'zolar cheklovsiz chatda yozishlari mumkin.\n\n"
        "Taqiqni qayta yoqish uchun: /setlimit <son>"
    )

async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh holatini ko'rsatish"""
    if update.message.chat.type not in ['group', 'supergroup']:
        return

    chat = update.message.chat
    chat_id = str(chat.id)
    
    data = load_data()
    
    if chat_id not in data or 'limit' not in data[chat_id]:
        await update.message.reply_text(
            "❌ **Limit o'rnatilmagan!**\n\n"
            "Yangi a'zolarni cheklash uchun:\n/setlimit <son>\n\n"
            "Misol: /setlimit 3"
        )
        return

    try:
        limit = data[chat_id]['limit']
        initial_count = data[chat_id].get('initial_member_count', await chat.get_member_count())
        current_count = await chat.get_member_count()
        new_members = current_count - initial_count
        is_active = data[chat_id].get('active', True)
        
        if not is_active:
            status_text = "✅ **Taqiq o'chirilgan** - Barcha a'zolar chatda yozishlari mumkin."
        else:
            status_text = (
                f"📊 **Guruh statistikasi:**\n"
                f"• Joriy limit: {limit} a'zo\n"
                f"• Yangi a'zolar: {new_members}/{limit}\n"
                f"• Guruh hajmi: {current_count} a'zo"
            )
            
            if new_members >= limit:
                status_text += "\n\n✅ **Limit bajarildi!** Yangi a'zolar chatda yozishlari mumkin."
            else:
                status_text += f"\n\n❌ **Limit bajarilmadi!** Yangi {limit - new_members} a'zo kerak."
        
        status_text += f"\n\n🔧 Sozlamalar: /setlimit | /freemode"
        
        await update.message.reply_text(status_text)
    except Exception as e:
        logger.error(f"Status ko'rsatishda xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi!")

async def check_user_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi xabar yozish huquqini tekshirish"""
    try:
        chat = update.message.chat
        user = update.message.from_user
        chat_id = str(chat.id)

        # Faqat guruhlar uchun
        if chat.type not in ['group', 'supergroup']:
            return

        data = load_data()
        
        # Agar guruh sozlanmagan bo'lsa yoki taqiq o'chirilgan bo'lsa
        if chat_id not in data or 'limit' not in data[chat_id] or not data[chat_id].get('active', True):
            return

        limit = data[chat_id]['limit']

        # Administratorlarni cheklamaymiz
        chat_member = await chat.get_member(user.id)
        if chat_member.status in ['administrator', 'creator']:
            return

        # Guruhdagi a'zolar sonini olish
        member_count = await chat.get_member_count()

        # Agar guruhda hali ma'lumot saqlanmagan bo'lsa
        if 'initial_member_count' not in data[chat_id]:
            data[chat_id]['initial_member_count'] = member_count
            data[chat_id]['allowed_users'] = []
            save_data(data)
            return

        initial_count = data[chat_id]['initial_member_count']
        allowed_users = data[chat_id].get('allowed_users', [])

        # Agar foydalanuvchi allaqachon ruxsat berilgan bo'lsa
        if str(user.id) in allowed_users:
            return

        # Yangi a'zolar sonini hisoblash
        new_members_count = member_count - initial_count

        # Agar yangi a'zolar soni limitdan kam bo'lsa
        if new_members_count < limit:
            # Xabarni o'chirish
            try:
                await update.message.delete()
            except Exception as e:
                logger.error(f"Xabarni o'chirishda xato: {e}")
            
            # Foydalanuvchiga ogohlantirish yuborish
            try:
                warning_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {user.mention_html()}, siz hali chatda yozishingiz mumkin emas!\n\n"
                         f"📊 **Siz {new_members_count}/{limit} ta yangi a'zo qo'shgansiz.**\n"
                         f"Yana {limit - new_members_count} ta yangi a'zo qo'shishingiz kerak.\n\n"
                         f"🔓 Taqiqni olib tashlash: /freemode",
                    parse_mode='HTML'
                )
                # 15 soniyadan so'ng ogohlantirishni o'chirish
                asyncio.create_task(delete_after_delay(context, chat_id, warning_msg.message_id, 15))
            except Exception as e:
                logger.error(f"Ogohlantirish yuborishda xato: {e}")
    except Exception as e:
        logger.error(f"Foydalanuvchi tekshirishda xato: {e}")

async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    """Xabarni kechiktirilgan vaqtdan so'ng o'chirish"""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Xabarni o'chirishda xato: {e}")

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi a'zolar qo'shilganda"""
    try:
        chat = update.message.chat
        chat_id = str(chat.id)

        data = load_data()
        
        if chat_id in data and data[chat_id].get('active', True):
            # Guruhdagi jami a'zolar sonini yangilash
            data[chat_id]['initial_member_count'] = await chat.get_member_count()
            data[chat_id]['title'] = chat.title
            save_data(data)
    except Exception as e:
        logger.error(f"Yangi a'zolar qo'shilganda xato: {e}")

# ==================== OWNER COMMANDS (faqat shaxsiy chatda) ====================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batafsil statistika (faqat owner)"""
    if update.message.chat.type != 'private' or not is_owner(update.message.from_user.id):
        return
    
    data = load_data()
    total_groups = len(data)
    
    stats_text = "📈 **Batafsil Statistika**\n\n"
    
    if total_groups == 0:
        stats_text += "Hali hech qanday guruh yo'q."
    else:
        active_count = 0
        total_members = 0
        
        for chat_id, group_data in data.items():
            if group_data.get('active', False):
                active_count += 1
            total_members += group_data.get('initial_member_count', 0)
            
            # Guruh ma'lumotlari
            group_name = group_data.get('title', f"Guruh {chat_id}")
            limit = group_data.get('limit', 'Noma\'lum')
            members = group_data.get('initial_member_count', 'Noma\'lum')
            status = "🟢 Faol" if group_data.get('active', False) else "🔴 O'chirilgan"
            
            stats_text += f"**{group_name}**\n"
            stats_text += f"  👥 {members} a'zo | Limit: {limit} | {status}\n"
            stats_text += f"  🆔 {chat_id}\n\n"
        
        stats_text += f"**Umumiy:** {total_groups} guruh, {total_members} a'zo, {active_count} faol"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast xabar yuborish (faqat owner)"""
    if update.message.chat.type != 'private' or not is_owner(update.message.from_user.id):
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **Broadcast qilish:**\n\n"
            "Ishlatish: /broadcast <xabar>\n\n"
            "Misol: /broadcast Salom! Bu test xabari."
        )
        return
    
    message_text = ' '.join(context.args)
    data = load_data()
    groups = list(data.keys())
    
    if not groups:
        await update.message.reply_text("❌ Hali hech qanday guruh yo'q.")
        return
    
    await update.message.reply_text(f"📤 {len(groups)} ta guruhga xabar yuborilmoqda...")
    
    success_count = 0
    failed_count = 0
    
    for chat_id in groups:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 **Bot yangiligi:**\n\n{message_text}"
            )
            success_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"Broadcast xatosi {chat_id}: {e}")
    
    result_text = (
        f"✅ **Broadcast natijasi:**\n\n"
        f"• Muvaffaqiyatli: {success_count}\n"
        f"• Xatolik: {failed_count}\n"
        f"• Jami: {len(groups)}"
    )
    
    await update.message.reply_text(result_text)

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhlar ro'yxati (faqat owner)"""
    if update.message.chat.type != 'private' or not is_owner(update.message.from_user.id):
        return
    
    data = load_data()
    
    if not data:
        await update.message.reply_text("📭 Hali hech qanday guruh yo'q.")
        return
    
    groups_text = "📋 **Bot qo'shilgan guruhlar:**\n\n"
    
    for i, (chat_id, group_data) in enumerate(data.items(), 1):
        group_name = group_data.get('title', f"Guruh {chat_id}")
        members = group_data.get('initial_member_count', 'Noma\'lum')
        limit = group_data.get('limit', 'Sozlanmagan')
        status = "🟢" if group_data.get('active', False) else "🔴"
        
        groups_text += f"{i}. **{group_name}** {status}\n"
        groups_text += f"   👥 {members} a'zo | ⚙️ {limit}\n"
        groups_text += f"   🆔 `{chat_id}`\n\n"
    
    await update.message.reply_text(groups_text, parse_mode='Markdown')

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel (faqat owner)"""
    if update.message.chat.type != 'private' or not is_owner(update.message.from_user.id):
        return
    await show_admin_panel(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni qayta ishlash"""
    logger.error(f"Xato yuz berdi: {context.error}")

def main():
    """Asosiy funksiya"""
    # Application yaratish
    application = Application.builder().token(TOKEN).build()

    # Handlerlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setlimit", set_limit))
    application.add_handler(CommandHandler("freemode", freemode))
    application.add_handler(CommandHandler("status", get_status))
    
    # Owner handlerlari (faqat shaxsiy chatda ishlaydi)
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("groups", list_groups))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_user_permission))
    
    # Xatolar handleri
    application.add_error_handler(error_handler)

    # Botni ishga tushirish
    logger.info("Bot ishga tushdi...")
    application.run_polling()

if __name__ == '__main__':
    main()
