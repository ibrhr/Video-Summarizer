from db import save_user, update_user_tier, add_request, get_user_tier, get_requests_today
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from .logic import is_valid_youtube_url, summarize_takeaways_youtube_video, summarize_youtube_video


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name or "there"
    save_user(user)  # Save user data to the database
    await update.message.reply_text(
        f"👋 Hey {name}! Just send me a YouTube link and I’ll help you break it down."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_valid_youtube_url(text):
        context.user_data["video_url"] = text

        keyboard = [
            [InlineKeyboardButton("📝 Summarize", callback_data="option_summarize")],
            [InlineKeyboardButton("📌 Main Takeaways", callback_data="option_takeaways")],
            [InlineKeyboardButton("❓ Ask a Question (5)", callback_data="option_ask")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("✅ Link looks good! What would you like to do?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("⚠️ That doesn't look like a valid YouTube link. Please send a correct one.")


async def handle_option_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
         
    # check how many requests the user has made today, if free max is 3, pro is 10, plus is 100
    user_id = query.from_user.id
    tier = get_user_tier(user_id)
    requests_today = get_requests_today(user_id)
    if tier == 'free' and requests_today >= 3:
        await query.edit_message_text("❌ You have reached your daily limit of 3 requests. Upgrade to Pro or Plus for more!")
        return
    elif tier == 'pro' and requests_today >= 10:
        await query.edit_message_text("❌ You have reached your daily limit of 10 requests. Upgrade to Plus for unlimited access!")
        return
    elif tier == 'plus' and requests_today >= 100:  # Arbitrary high limit for Plus
        await query.edit_message_text("❌ You have reached your daily limit of 100 requests. Please try again tomorrow!")

    video_url = context.user_data.get("video_url")
    if not video_url:
        await query.edit_message_text("❌ No video URL found. Please send me a YouTube link first.")
        return

    option = query.data
    if option == "option_summarize":
        
        context.user_data["pending_action"] = "summarize"
        await query.edit_message_text("🌐 Choose the language for your summary:", reply_markup=get_language_keyboard())
        return
        
    elif option == "option_takeaways":
        if tier == 'free':
            await query.edit_message_text("❌ The 'Main Takeaways' feature is only available for Pro and Plus subscribers. Upgrade to access this feature!")
            return
        
        context.user_data["pending_action"] = "takeaways"
        await query.edit_message_text("🌐 Choose the language for your takeaways:", reply_markup=get_language_keyboard())
        return
        
        
    elif option == "option_ask":
        await query.edit_message_text("🚧 The 'Ask a Question' feature is not available yet. Coming soon!")

    else:
        await query.edit_message_text("❌ Unknown option.")

async def handle_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split("_")[1]  # 'en', 'ar', 'es'
    # convert language code to full name for to pass to the summarization functions
    if lang_code == "en":
        lang_code = "english"
    elif lang_code == "ar":
        lang_code = "arabic"
    elif lang_code == "es":
        lang_code = "spanish"
    else:
        await query.edit_message_text("❌ Unsupported language. Please choose English, Arabic, or Spanish.")
        return
    action = context.user_data.get("pending_action")
    video_url = context.user_data.get("video_url")

    if not action or not video_url:
        await query.edit_message_text("❌ Missing data. Please send a new YouTube link.")
        return

    await query.edit_message_text("⏳ Working on it...")

    try:
        if action == "summarize":
            try:
                summary = summarize_youtube_video(video_url, language=lang_code)
                await query.edit_message_text("⏳ Summarizing...")                
                await query.message.reply_text(f"✅ Summary:\n\n{summary}")
                add_request(query.from_user.id, "Summarize")  # Log the request
                return 
            except Exception as e:
                print("Summarize error:", e)
                await query.message.reply_text("❌ Could not generate a summary. Try another video.")


        elif action == "takeaways":
            try:
                takeaways = summarize_takeaways_youtube_video(video_url, language=lang_code)
                await query.edit_message_text("⏳ Generating Takeaways...")            
                await query.message.reply_text(f"✅ Main Takeaways:\n\n{takeaways}")
                add_request(query.from_user.id, "Takeaways")  # Log the request
                return
            except Exception as e:
                print("Takeaways error:", e)
                await query.message.reply_text("❌ Could not generate takeaways. Try another video.")


    except Exception as e:
        print(f"{action} error:", e)
        await query.message.reply_text("❌ Could not process your request. Please try again.")


async def subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Free", callback_data="tier_free"),
            InlineKeyboardButton("Pro", callback_data="tier_pro"),
            InlineKeyboardButton("Plus", callback_data="tier_plus"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose your subscription tier:", reply_markup=reply_markup)

# Callback handler for button clicks
async def subscription_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    user_id = query.from_user.id
    data = query.data

    if data.startswith("tier_"):
        new_tier = data.split("_")[1]  # 'free', 'pro', or 'plus'
        update_user_tier(user_id, new_tier)
        await query.edit_message_text(f"Subscription tier updated to *{new_tier.capitalize()}* ✅", parse_mode="Markdown")
        
def setup_handlers(app) -> None:
    print("Registering handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'^/'), handle_message))

    # Handle buttons related to video options (callback_data starting with "option_")
    app.add_handler(CallbackQueryHandler(handle_option_click, pattern=r"^option_"))

    # Handle buttons related to subscription tiers (callback_data starting with "tier_")
    app.add_handler(CallbackQueryHandler(subscription_button_callback, pattern=r"^tier_"))

    app.add_handler(CommandHandler("subscription", subscription))
    
    app.add_handler(CallbackQueryHandler(handle_language_choice, pattern=r"^lang_"))

    
    
def get_language_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇸🇦 Arabic", callback_data="lang_ar"),
            InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_es"),
        ]
    ])