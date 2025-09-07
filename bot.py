import os
import requests
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv  
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.helpers import escape_markdown
from urllib.parse import quote_plus
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")


DATABASE_URL = os.getenv("DATABASE_URL") 


if not DATABASE_URL:
    PGHOST = os.getenv("PGHOST")
    PGUSER = os.getenv("PGUSER")
    PGPASSWORD = os.getenv("PGPASSWORD")
    PGDATABASE = os.getenv("PGDATABASE")
    PGPORT = os.getenv("PGPORT")
   
    if all([PGHOST, PGUSER, PGPASSWORD, PGDATABASE, PGPORT]):
        DATABASE_URL = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"


engine = create_engine(DATABASE_URL)
Base = declarative_base()

class WatchlistItem(Base):
    __tablename__ = 'watchlist'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    media_type = Column(String, nullable=False)
    media_id = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'media_type', 'media_id', name='_user_media_uc'),)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


USAGE_LOG_FILE = 'usage_log.json'

def log_usage(user_id: int, query: str):
    """Logs a user's request to a JSON file."""
    try:
        logs = []
        if os.path.exists(USAGE_LOG_FILE):
            with open(USAGE_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        logs.append({
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'query': query
        })

        with open(USAGE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging usage: {e}")


async def send_media_details(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type: str, item_id: int):
    """Fetches initial details and sends a message with a 'More Info' button."""
    try:
        details_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}?api_key={TMDB_API_KEY}"
        details_response = requests.get(details_url, timeout=10).json()

        title = details_response.get('title') or details_response.get('name')
        poster_path = details_response.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750.png?text=No+Poster"
        
        escaped_title = escape_markdown(title, version=2)
        message = f"🎬 *{escaped_title}*"

        callback_data = f"details_{media_type}_{item_id}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Show Details & Options ➕", callback_data=callback_data)]])
        

        message_to_send = update.message or update.callback_query.message
        
        await message_to_send.reply_photo(
            photo=poster_url,
            caption=message,
            parse_mode='MarkdownV2',
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"Error in send_media_details: {e}")
        await update.message.reply_text("An error occurred while fetching details.")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hello\! I'm your movie bot\. 🍿\n"
        "Send a movie name for details, or try /popular, /suggest, or /actor\."
    )

async def get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text search, finds the media ID, and calls the sender function."""
    query = update.message.text
    user_id = update.effective_user.id
    processing_message = await update.message.reply_text(f"Searching for '{query}'...")

    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={quote_plus(query)}"
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text with full details."""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, media_type, item_id_str = data.split('_')
    item_id = int(item_id_str)
    user_id = query.from_user.id

    if action == "details":
        try:
            details_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}?api_key={TMDB_API_KEY}&append_to_response=videos"
            details_response = requests.get(details_url, timeout=10).json()

            title = details_response.get('title') or details_response.get('name')
            overview = details_response.get('overview', 'No overview available.')
            genres = ', '.join([genre['name'] for genre in details_response.get('genres', [])])
            status = details_response.get('status', 'N/A')
            rating = details_response.get('vote_average', 0)
            
            escaped_title = escape_markdown(title, version=2)
            escaped_overview = escape_markdown(overview, version=2)
            escaped_genres = escape_markdown(genres, version=2)
            escaped_status = escape_markdown(status, version=2)
            escaped_rating = escape_markdown(f"{rating:.1f}/10", version=2)

            full_message = (
                f"🎬 *{escaped_title}*\n\n"
                f"⭐ *Rating:* {escaped_rating} \\(TMDb\\)\n\n"
                f"🎭 *Genre:* {escaped_genres}\n"
                f"📊 *Status:* {escaped_status}\n\n"
            )
            
            if media_type == 'tv':
                seasons = details_response.get('number_of_seasons')
                episodes = details_response.get('number_of_episodes')
                full_message += f"📺 *Seasons:* {seasons}  |  *Episodes:* {episodes}\n\n"

            full_message += f"📝 *Overview:*\n{escaped_overview}"
            
            keyboard_buttons = []
            trailer_key = next((v['key'] for v in details_response.get('videos', {}).get('results', []) if v['type'].lower() == 'trailer'), None)
            if trailer_key:
                keyboard_buttons.append(InlineKeyboardButton("▶️ Watch Trailer", url=f"https://www.youtube.com/watch?v={trailer_key}"))
            
            if media_type == 'movie':
                release_date_str = details_response.get('release_date')
                if release_date_str:
                    release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                    if datetime.now().date() - timedelta(days=60) <= release_date:
                        keyboard_buttons.append(InlineKeyboardButton("🎟️ Book Tickets", url="https://in.bookmyshow.com/explore/movies"))

            keyboard_buttons.append(InlineKeyboardButton("Add to Watchlist ➕", callback_data=f"add_{media_type}_{item_id}"))
            
            reply_markup = InlineKeyboardMarkup([keyboard_buttons])
            await query.edit_message_caption(caption=full_message, parse_mode='MarkdownV2', reply_markup=reply_markup)

        except Exception as e:
            print(f"Error in button_handler (details): {e}")

    elif action == "add":
        try:
            session = Session()
            exists = session.query(WatchlistItem).filter_by(user_id=user_id, media_type=media_type, media_id=item_id).first()
            
            if exists:
                await query.answer("This item is already on your watchlist!", show_alert=True)
            else:
                new_item = WatchlistItem(user_id=user_id, media_type=media_type, media_id=item_id)
                session.add(new_item)
                session.commit()
                await query.answer("✅ Added to your watchlist!", show_alert=True)
            
            session.close()

        except Exception as e:
            print(f"Error in button_handler (add): {e}")
            await query.answer("Error: Could not add to watchlist.", show_alert=True)

async def popular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching the most popular movies right now...")
    try:
        popular_url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
        response = requests.get(popular_url, timeout=10).json()
        message = "*🔥 Top 5 Popular Movies Today*\n\n"
        for i, movie in enumerate(response.get('results', [])[:5]):
            title = escape_markdown(movie.get('title'), version=2)
            rating = escape_markdown(str(movie.get('vote_average', 0)), version=2)
            message += f"{i+1}\\. {title} \\(⭐ {rating}/10\\)\n"
        await update.message.reply_text(message, parse_mode='MarkdownV2')
    except Exception as e:
        print(f"Error in /popular command: {e}")

async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Finding a great movie for you...")
    try:
        random_page = random.randint(1, 50)
        discover_url = (f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
                        f"&language=en-US&sort_by=popularity.desc&include_adult=false"
                        f"&vote_count.gte=500&page={random_page}")
        response = requests.get(discover_url, timeout=10).json()
        if not response.get('results'):
            await update.message.reply_text("Couldn't find a suggestion right now, please try again!")
            return
        random_movie = random.choice(response['results'])
        await update.message.reply_text("I suggest you watch:")
        await send_media_details(update, context, 'movie', random_movie['id'])
    except Exception as e:
        print(f"Error in /suggest command: {e}")

async def actor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actor_name = ' '.join(context.args)
    if not actor_name:
        await update.message.reply_text("Please provide an actor's name. Example: /actor Tom Hanks")
        return
    await update.message.reply_text(f"Searching for {actor_name}...")
    try:
        search_url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={quote_plus(actor_name)}"
        search_response = requests.get(search_url, timeout=10).json()
        if not search_response.get('results'):
            await update.message.reply_text(f"Sorry, I couldn't find an actor named {actor_name}.")
            return
        person_id = search_response['results'][0]['id']
        details_url = f"https://api.themoviedb.org/3/person/{person_id}?api_key={TMDB_API_KEY}"
        details_response = requests.get(details_url, timeout=10).json()
        credits_url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_API_KEY}"
        credits_response = requests.get(credits_url, timeout=10).json()
        
        actor_name_official = details_response.get('name')
        profile_path = details_response.get('profile_path')
        photo_url = f"https://image.tmdb.org/t/p/w500{profile_path}" if profile_path else "https://via.placeholder.com/500x750.png?text=No+Photo"
        sorted_movies = sorted(credits_response['cast'], key=lambda k: k.get('popularity', 0), reverse=True)
        
        escaped_name = escape_markdown(actor_name_official, version=2)
        message = f"🎬 *{escaped_name}*\n\n*Most Popular Movies:*\n"
        if not sorted_movies:
            message += "No popular movie credits found."
        else:
            for i, movie in enumerate(sorted_movies[:5]):
                title = escape_markdown(movie.get('title'), version=2)
                message += f"{i+1}\\. {title}\n"
        await update.message.reply_photo(photo=photo_url, caption=message, parse_mode='MarkdownV2')
    except Exception as e:
        print(f"Error in /actor command: {e}")

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's personal watchlist."""
    user_id = update.effective_user.id
    session = Session()
    user_watchlist = session.query(WatchlistItem).filter_by(user_id=user_id).all()
    session.close()

    if not user_watchlist:
        await update.message.reply_text("Your watchlist is empty. Find a movie and use the 'Add to Watchlist' button to save it!")
        return

    message = "*📝 Your Watchlist*\n\n"
    for i, item in enumerate(user_watchlist):
        details_url = f"https://api.themoviedb.org/3/{item.media_type}/{item.media_id}?api_key={TMDB_API_KEY}"
        details_response = requests.get(details_url, timeout=10).json()
        title = details_response.get('title') or details_response.get('name')
        escaped_title = escape_markdown(title, version=2)
        message += f"{i+1}\\. {escaped_title}\n"
        
    await update.message.reply_text(message, parse_mode='MarkdownV2')
        
async def usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Sorry, this command is for the bot admin only.")
        return
    try:
        if not os.path.exists(USAGE_LOG_FILE):
            await update.message.reply_text("No usage data has been recorded yet.")
            return
        with open(USAGE_LOG_FILE, 'r', encoding='utf-8') as f:
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
            f"*📊 Bot Usage Statistics*\n\n"
            f"\\- *Total Requests:* {total_requests}\n"
            f"\\- *Unique Users:* {unique_users}\n"
            f"\\- *Requests in Last 24h:* {last_24_hours_requests}"
        )
        await update.message.reply_text(stats_message, parse_mode='MarkdownV2')
    except Exception as e:
        print(f"Error in /usage command: {e}")
        
async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    policy_text = (
        "*Privacy Policy for CineFile Bot*\n\n"
        "*Data We Receive:*\nWe only process the movie title you send and your Telegram User/Chat ID to reply to you\.\n\n"
        "*How We Use It:*\nYour search is sent to TMDb to fetch movie details\. Your ID is used only to send the message back\.\n\n"
        "*Data Storage:*\n**We do not store your personal data**\. Your searches and watchlist are processed in real\-time\. Your watchlist is stored in a secure database, linked only to your anonymous User ID\.\n\n"
        "*Contact:*\nFor questions, contact @YourTelegramUsername\."
    )
    await update.message.reply_text(policy_text, parse_mode='MarkdownV2')

def main():
    """Starts the bot."""
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()


    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", usage))
    application.add_handler(CommandHandler("popular", popular_command))
    application.add_handler(CommandHandler("suggest", suggest_command))
    application.add_handler(CommandHandler("actor", actor_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("privacy", privacy))
    

    application.add_handler(CallbackQueryHandler(button_handler))


    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_info))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()