import os
import requests
import json
import random
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


async def send_media_details(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type: str, item_id: int):
    """Fetches details for a given ID and sends the formatted message."""
    try:
        details_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}?api_key={TMDB_API_KEY}"
        details_response = requests.get(details_url, timeout=10).json()

        title = details_response.get('title') or details_response.get('name')
        overview = details_response.get('overview', 'No overview available.')
        rating = details_response.get('vote_average', 0)
        
        videos_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}/videos?api_key={TMDB_API_KEY}"
        videos_response = requests.get(videos_url, timeout=10).json()
        trailer_key = next((video['key'] for video in videos_response.get('results', []) if video['type'].lower() == 'trailer'), None)
        trailer_link = f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else "No trailer found."

        message = (
            f"🎬 {title}\n\n"
            f"⭐ Rating: {rating:.1f}/10\n\n"
            f"📝 Overview:\n{overview}\n\n"
            f"▶️ Trailer: {trailer_link}"
        )
        
        if media_type == 'movie':
            release_date_str = details_response.get('release_date')
            if release_date_str:
                release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                today = datetime.now().date()
                if today - timedelta(days=60) <= release_date <= today:
                    bms_url = "https://in.bookmyshow.com/explore/movies"
                    message += f"\n\n🎟️ Book Tickets: {bms_url}"
        
        await update.message.reply_text(message)

    except Exception as e:
        print(f"Error in send_media_details: {e}")
        await update.message.reply_text("An error occurred while fetching the details.")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hello! I'm your movie bot. 🍿\n"
        "Send a movie name for details, or try /popular or /suggest."
    )

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text search, finds the media ID, and calls the sender function."""
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
        await send_media_details(update, context, result.get('media_type'), result.get('id'))
        
    except Exception as e:
        print(f"An unexpected error in get_info: {e}")
        await update.message.reply_text("An error occurred while searching.")

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

async def popular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays the top 5 currently popular movies."""
    await update.message.reply_text("Fetching the most popular movies right now...")
    
    try:
        popular_url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
        response = requests.get(popular_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('results'):
            await update.message.reply_text("Sorry, couldn't fetch the popular movies list right now.")
            return
            
        message = "🔥 **Top 5 Popular Movies Today**\n\n"
        for i, movie in enumerate(data['results'][:5]):
            title = movie.get('title')
            rating = movie.get('vote_average', 0)
            message += f"{i+1}. {title} (⭐ {rating:.1f}/10)\n"
            
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error in /popular command: {e}")
        await update.message.reply_text("Sorry, an error occurred while fetching popular movies.")

async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches a random, well-regarded movie and displays its details."""
    await update.message.reply_text("Finding a great movie for you...")
    
    try:
        random_page = random.randint(1, 50)
        discover_url = (
            f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
            f"&language=en-US&sort_by=popularity.desc&include_adult=false"
            f"&vote_count.gte=500&page={random_page}"
        )
        
        response = requests.get(discover_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('results'):
            await update.message.reply_text("Couldn't find a suggestion right now, please try again!")
            return
            
        random_movie = random.choice(data['results'])
        await send_media_details(update, context, 'movie', random_movie['id'])
        
    except Exception as e:
        print(f"Error in /suggest command: {e}")
        await update.message.reply_text("Sorry, an error occurred while finding a suggestion.")

def main():
    """Starts the bot."""
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", usage))
    application.add_handler(CommandHandler("popular", popular_command))
    application.add_handler(CommandHandler("suggest", suggest_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_info))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()