import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv  
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID") 


USAGE_LOG_FILE = 'usage_log.json'

def log_usage(user_id: int, query: str):
    """Logs a user's request to a JSON file."""
    try:
        logs = []
        if os.path.exists(USAGE_LOG_FILE):
            with open(USAGE_LOG_FILE, 'r') as f:
                logs = json.load(f)
        
        logs.append({
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'query': query
        })

        with open(USAGE_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging usage: {e}")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hello! I'm your movie bot. 🍿\n"
        "Send me any movie or series name for details."
    )

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and sends movie/series info and logs the request."""
    query = update.message.text
    user_id = update.effective_user.id
    
    processing_message = await update.message.reply_text(f"Searching for '{query}'...")

    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}"
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

        if not data.get('results'):
            await update.message.reply_text("Sorry, I couldn't find that title.")
            return


        log_usage(user_id, query)

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
        
        await update.message.reply_text(message)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await update.message.reply_text("An error occurred while fetching details.")


async def usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends usage statistics, restricted to the admin."""
    user_id = str(update.effective_user.id)
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Sorry, this command is for the bot admin only.")
        return

    try:
        if not os.path.exists(USAGE_LOG_FILE):
            await update.message.reply_text("No usage data has been recorded yet.")
            return

        with open(USAGE_LOG_FILE, 'r') as f:
            logs = json.load(f)

        total_requests = len(logs)
        unique_users = len(set(log['user_id'] for log in logs))
        

        last_24_hours_requests = 0
        one_day_ago = datetime.now() - timedelta(days=1)
        for log in logs:
            log_time = datetime.fromisoformat(log['timestamp'])
            if log_time > one_day_ago:
                last_24_hours_requests += 1

        stats_message = (
            "📊 **Bot Usage Statistics**\n\n"
            f"- **Total Requests:** {total_requests}\n"
            f"- **Unique Users:** {unique_users}\n"
            f"- **Requests in Last 24h:** {last_24_hours_requests}"
        )
        await update.message.reply_text(stats_message, parse_mode='Markdown')

    except Exception as e:
        print(f"Error in /usage command: {e}")
        await update.message.reply_text("An error occurred while fetching usage stats.")


def main():
    """Starts the bot."""
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("usage", usage))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_info))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()