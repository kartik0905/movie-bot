import os
import requests
from dotenv import load_dotenv  
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! I'm your movie bot. 🍿\n\n"
        "Just send me the name of any movie or web series, and I'll find the details for you!"
    )

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and sends movie/series info based on user's message."""
    query = update.message.text
    processing_message = await update.message.reply_text(f"Searching for '{query}'...")

    search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}"
    
    try:

        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

        if not data.get('results'):
            await update.message.reply_text("Sorry, I couldn't find anything for that title. Please check the spelling.")
            return

        result = data['results'][0]
        media_type = result.get('media_type')

        item_id = result.get('id')
        title = result.get('title') or result.get('name')
        overview = result.get('overview', 'No overview available.')
        rating = result.get('vote_average', 0)
        poster_path = result.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750.png?text=No+Poster"
        
        videos_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}/videos?api_key={TMDB_API_KEY}"

        videos_response = requests.get(videos_url, timeout=10).json()
        trailer_key = None
        for video in videos_response.get('results', []):
            if video['type'].lower() == 'trailer':
                trailer_key = video['key']
                break
        
        trailer_link = f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else "No trailer found."

        message = (
            f"🎬 {title}\n\n"
            f"⭐ Rating: {rating:.1f}/10\n\n"
            f"📝 Overview:\n{overview}\n\n"
            f"▶️ Trailer: {trailer_link}"
        )

        if media_type == 'movie':
            details_url = f"https://api.themoviedb.org/3/movie/{item_id}?api_key={TMDB_API_KEY}"

            details_response = requests.get(details_url, timeout=10).json()
            release_date_str = details_response.get('release_date')

            if release_date_str:
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                today = datetime.now().date()
                if today - timedelta(days=60) <= release_date <= today:
                    bms_url = "https://in.bookmyshow.com/explore/movies"
                    message += f"\n\n🎟️ Book Tickets: {bms_url}"

        await update.message.reply_photo(photo=poster_url, caption=message)

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        await update.message.reply_text("Sorry, I'm having trouble connecting to the movie database. Please try again in a moment.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await update.message.reply_text("An unexpected error occurred. The developer has been notified.")


def main():
    """Start the bot."""
    print("Bot is starting...")
    
    if not TELEGRAM_TOKEN or not TMDB_API_KEY:
        print("ERROR: Environment variables for API keys are not set correctly.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_info))

    print("Bot is running and polling for messages...")
    application.run_polling()

if __name__ == '__main__':
    main()