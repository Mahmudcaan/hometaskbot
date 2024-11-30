import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
from datetime import datetime, timedelta

# Replace this with your bot's token (from BotFather)
BOT_TOKEN = '7861407130:AAFg8219urCsrrrRNQXTrnUbe9104kpHXeI'

# Replace this with the chat ID of the admin
ADMIN_CHAT_ID = '1028664534'  # Ensure this is correct

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
HOMEWORK, NAME = range(2)

# Global variable to track the student number (based on the order they submit homework)
submission_counter = 1

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    # Check if the user already submitted homework within the last 24 hours
    last_submission_time = context.user_data.get('last_submission_time')

    if last_submission_time:
        # Calculate the time difference from the last submission
        time_diff = datetime.now() - last_submission_time

        # If less than 24 hours, notify the user they can't submit homework
        if time_diff < timedelta(hours=24):
            remaining_time = timedelta(hours=24) - time_diff
            await update.message.reply_text(
                f"You can only submit homework once every 24 hours. Please try again in {remaining_time}.")
            return ConversationHandler.END

    # If no recent submission or it's been more than 24 hours, allow submission
    await update.message.reply_text(
        "Welcome! Please send your homework (this can be any text, photo, or file)."
    )
    return HOMEWORK


# Homework handler (collects homework and asks for the name)
async def homework(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    # If the user hasn't already started a homework list, initialize it
    if 'homework' not in context.user_data:
        context.user_data['homework'] = []

    # Append the received media/message to the list
    homework_message = update.message

    context.user_data['homework'].append(homework_message)

    # Ask for more homework or proceed with the name
    await update.message.reply_text(
        "Homework received! You can send more or click 'Done' to proceed.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Done", callback_data='done')]
        ])
    )

    return HOMEWORK


# Inline button callback handler to mark "Done"
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    # Ask for the user's name
    await query.message.reply_text("You've finished sending homework. Now, please provide your name.")
    return NAME


# Name handler (handles the user's name and forwards homework + name)
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global submission_counter  # Use the global counter for student number

    # Save the user's name
    context.user_data['name'] = update.message.text

    # Get all homework messages and the user's name
    homework_messages = context.user_data['homework']
    user_name = context.user_data['name']

    # Get the current date and time
    submission_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Send the first message with 11 checkmarks
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="✅✅✅✅✅✅✅✅✅✅✅✅✅"
        )

        # Send the homework (media and text)
        for homework_message in homework_messages:
            if homework_message.text:
                # Forward text
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=homework_message.text
                )
            elif homework_message.photo:
                # Forward photo
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=homework_message.photo[-1].file_id  # Get the highest resolution photo
                )
            elif homework_message.video:
                # Forward video
                await context.bot.send_video(
                    chat_id=ADMIN_CHAT_ID,
                    video=homework_message.video.file_id
                )
            elif homework_message.audio:
                # Forward audio
                await context.bot.send_audio(
                    chat_id=ADMIN_CHAT_ID,
                    audio=homework_message.audio.file_id
                )
            elif homework_message.voice:
                # Forward voice message
                await context.bot.send_voice(
                    chat_id=ADMIN_CHAT_ID,
                    voice=homework_message.voice.file_id
                )

        # Send the student's name and submission details (markdown format)
        message_to_admin = f"-----------------------------\n"
        message_to_admin += f"**Student's Name**: {user_name}\n"
        message_to_admin += f"**Date and Time**: {submission_time}\n"
        message_to_admin += f"**Student Number**: {submission_counter}\n"
        message_to_admin += f"-----------------------------"

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message_to_admin,
            parse_mode="Markdown"
        )

        # Acknowledge to the user
        await update.message.reply_text("Your homework and name have been forwarded to the admin.")

        # Increment the submission counter for the next student
        submission_counter += 1

        # Update the last submission time to prevent multiple submissions within 24 hours
        context.user_data['last_submission_time'] = datetime.now()

    except Exception as e:
        logger.error(f"Failed to forward content to admin: {e}")
        await update.message.reply_text("There was an error forwarding your content. Please try again later.")

    return ConversationHandler.END


# Main bot setup
async def main():
    # Create and configure the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Create the ConversationHandler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],  # When /start is triggered
        states={
            HOMEWORK: [MessageHandler(
                filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
                homework
            )],  # All types of media and text
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],  # Name state, handle text (user's name)
        },
        fallbacks=[CallbackQueryHandler(done, pattern='done')],  # Handle 'done' button press
    )

    # Register handlers
    application.add_handler(conversation_handler)

    # Initialize and start the bot
    await application.initialize()
    await application.start()
    try:
        # Start polling updates and keep the bot running
        await application.updater.start_polling()
        logger.info("Bot is running... Press Ctrl+C to stop.")
        # Keep the bot alive
        await asyncio.Future()  # Run forever
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        # Proper cleanup
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot has stopped.")


# Entry point
if __name__ == "__main__":
    # Ensure Windows compatibility
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user.")
    except RuntimeError as e:
        logger.error(f"A RuntimeError occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
