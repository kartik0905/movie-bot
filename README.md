<div align="center">

# 🎬 Movie Info Fetcher Bot  
### Get Movie & Web Series Info Instantly on Telegram  

[👉 Try it Live](https://t.me/MyMovieInfoFetcherbot)

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Telegram%20Bot-0088cc?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot"/>
  <img src="https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white" alt="Railway"/>
  <img src="https://img.shields.io/badge/BookMyShow-E40046?style=for-the-badge&logoColor=white" alt="BookMyShow"/>
</p>

---

## 📌 Overview  

**Movie Info Fetcher Bot** is a **Telegram bot** that lets you quickly search for **movies and web series info** right inside Telegram.  

If the movie is currently running in **theatres**, it even provides a **BookMyShow link** to book tickets instantly.  

The bot is live and hosted on **Railway** 🚂.  

---

## ✨ Features  

- 🔍 **Search Movies & Web Series** — Get detailed info in seconds  
- 🎟️ **Theatre Movies** — Direct **BookMyShow link** to book tickets  
- ⚡ **Instant & Lightweight** — Works directly in Telegram  
- ☁️ **Hosted on Railway** — Always online & fast  

---

## 🛠️ Tech Stack  

| Layer | Technologies | Purpose |
|-------|--------------|---------|
| **Bot Framework** | [Telegram Bot API](https://core.telegram.org/bots) | Telegram integration |
| **Backend** | Python | Core logic |
| **Hosting** | Railway | Deployment & uptime |
| **Integration** | BookMyShow | Theatre ticket booking link |

---

## 📁 Folder Structure  

```
movie-info-bot/
├── main.py               # Entry point for the bot
├── handlers/             # Telegram command & message handlers
├── services/             # APIs to fetch movie/web series info
├── utils/                # Helper functions
├── requirements.txt      # Dependencies
└── README.md             # Project documentation
```

---

## 🧪 Local Development  

### 🔧 Requirements  

- Python **3.9+**  
- Telegram Bot Token (from [BotFather](https://t.me/BotFather))  

---

## 🏁 Getting Started  

### 1. Clone the Repo  

```bash
git clone https://github.com/your-username/movie-info-bot.git
cd movie-info-bot
```

### 2. Install Dependencies  

```bash
pip install -r requirements.txt
```

### 3. Add Environment Variables  

Create a `.env` file:  

```bash
BOT_TOKEN=your_telegram_bot_token
```

### 4. Run the Bot  

```bash
python main.py
```

Your bot will now be live 🚀.  

---

## 🚦 Deployment  

This bot is hosted on **Railway** for continuous uptime.  
For deployment:  

```bash
railway init
railway up
```

---

## 📦 Dependencies  

- `python-telegram-bot`  
- `requests`  
- `python-dotenv`  

---

## 🙌 Acknowledgments  

- [Telegram Bot API](https://core.telegram.org/bots)  
- [BookMyShow](https://in.bookmyshow.com/)  
- [Railway](https://railway.app/)  

---

<div align="center">
  Built with ❤️ by <a href="https://github.com/kartik0905">Kartik Garg</a>
</div>  
