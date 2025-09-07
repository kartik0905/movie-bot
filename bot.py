import os
import requests
import json
import random
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv  
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, InlineQueryHandler
from telegram.helpers import escape_markdown
from urllib.parse import quote_plus


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
OMDB_API_KEY = os.getenv("OMDB_API_KEY") 


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
        overview = details_response.get('overview', 'No overview available.')
        poster_path = details_response.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750.png?text=No+Poster"
        

        escaped_title = escape_markdown(title, version=2)
        escaped_overview = escape_markdown(overview[:150] + '...', version=2)

        message = (
            f"🎬 *{escaped_title}*\n\n"
            f"📝 *Overview:*\n{escaped_overview}"
        )

        callback_data = f"moreinfo_{media_type}_{item_id}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Show More Info ➕", callback_data=callback_data)]
        ])
        
        await update.message.reply_photo(
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
        "Hello! I'm your movie bot. 🍿\n"
        "Send a movie name for details, or try /popular, /suggest, or /actor."
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, media_type, item_id_str = data.split('_')
    item_id = int(item_id_str)

    if action == "moreinfo":
        try:
            details_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}?api_key={TMDB_API_KEY}&append_to_response=videos"
            details_response = requests.get(details_url, timeout=10).json()

            imdb_id = details_response.get('imdb_id')
            title = details_response.get('title') or details_response.get('name')
            overview = details_response.get('overview', 'No overview available.')
            genres = ', '.join([genre['name'] for genre in details_response.get('genres', [])])
            status = details_response.get('status', 'N/A')
            
            trailer_key = next((video['key'] for video in details_response.get('videos', {}).get('results', []) if video['type'].lower() == 'trailer'), None)
            trailer_url = f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None
            

            imdb_rating, rt_rating = "N/A", "N/A"
            if imdb_id and OMDB_API_KEY:
                omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
                omdb_data = requests.get(omdb_url, timeout=10).json()
                if omdb_data.get("Response") == "True":
                    imdb_rating = omdb_data.get("imdbRating", "N/A")
                    rt_rating = next((r['Value'] for r in omdb_data.get("Ratings", []) if r["Source"] == "Rotten Tomatoes"), "N/A")


            escaped_title = escape_markdown(title, version=2)
            escaped_overview = escape_markdown(overview, version=2)
            escaped_genres = escape_markdown(genres, version=2)
            escaped_status = escape_markdown(status, version=2)
            escaped_imdb = escape_markdown(imdb_rating, version=2)
            escaped_rt = escape_markdown(rt_rating, version=2)
            
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else "https://www.imdb.com"
            rt_search_url = f"https://www.rottentomatoes.com/search?search={quote_plus(title)}"

            full_message = (
                f"🎬 *{escaped_title}*\n\n"
                f"⭐ [IMDb: {escaped_imdb}/10]({imdb_url})\n"
                f"🍅 [Rotten Tomatoes: {escaped_rt}]({rt_search_url})\n\n"
                f"🎭 *Genre:* {escaped_genres}\n"
                f"📊 *Status:* {escaped_status}\n\n"
                f"📝 *Overview:*\n{escaped_overview}"
            )
            

            keyboard_buttons = []
            if trailer_url:
                keyboard_buttons.append(InlineKeyboardButton("▶️ Watch Trailer", url=trailer_url))
            

            if media_type == 'movie':
                release_date_str = details_response.get('release_date')
                if release_date_str:
                    release_date = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    if today - timedelta(days=60) <= release_date <= today:
                        keyboard_buttons.append(InlineKeyboardButton("🎟️ Book Tickets", url="https://in.bookmyshow.com/explore/movies"))
            
            reply_markup = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None
            
            await query.edit_message_caption(caption=full_message, parse_mode='MarkdownV2', reply_markup=reply_markup)

        except Exception as e:
            print(f"Error in button_handler: {e}")
            await query.edit_message_caption(caption="Sorry, an error occurred while fetching more details.")

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
        await update.message.reply_text("Sorry, an error occurred while fetching popular movies.")

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
        await update.message.reply_text("Sorry, an error occurred while finding a suggestion.")

async def actor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actor_name = ' '.join(context.args)
    if not actor_name:
        await update.message.reply_text("Please provide an actor's name. Example: /actor Tom Hanks")
        return
    await update.message.reply_text(f"Searching for {actor_name}...")
    try:
        search_url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={actor_name}"
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
        await update.message.reply_text("Sorry, an error occurred while searching for the actor.")
        
async def usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Sorry, this command is for the bot admin only.")
        return

    await update.message.reply_text("Usage stats would be displayed here.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query: return
    results = []
    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}"
        response = requests.get(search_url, timeout=5).json()
        for item in response.get('results', [])[:5]:
            if item.get('media_type') not in ['movie', 'tv']: continue
            title = item.get('title') or item.get('name')
            overview = item.get('overview', 'No overview available.')
            poster_path = item.get('poster_path')
            thumb_url = f"https://image.tmdb.org/t/p/w92{poster_path}" if poster_path else ""
            rating = item.get('vote_average', 0)
            message_content = (f"🎬 {title}\n⭐ Rating: {rating:.1f}/10\n📝 Overview:\n{overview}")
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=overview[:100] + '...' if overview else 'Click for details',
                    thumb_url=thumb_url,
                    input_message_content=InputTextMessageContent(message_content)
                )
            )
    except Exception as e:
        print(f"Error in inline_query: {e}")
    await update.inline_query.answer(results, cache_time=5)

def main():
    """Starts the bot."""
    print("Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()


    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", usage))
    application.add_handler(CommandHandler("popular", popular_command))
    application.add_handler(CommandHandler("suggest", suggest_command))
    application.add_handler(CommandHandler("actor", actor_command))
    

    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(InlineQueryHandler(inline_query))


    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_info))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()