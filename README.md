# PlanBot — AI reja tuzuvchi Telegram bot

5 ta menyuli Telegram bot: Natijalarim, AI bilan reja tuzish, AI bilan suhbat,
Oylik rejalar (Notion uslubida), Rejalarim.

## ⚠️ MUHIM — Xavfsizlik

**Kalitlaringizni (token/API key) hech qachon kodga yozib GitHub'ga yubormang.**
Bu loyihada barcha maxfiy kalitlar `.env` faylidan o'qiladi, kod ichida emas.

Agar avval kalitingiz kodga yozilgan holda GitHub'ga tushgan bo'lsa (yoki
chatda ochiq yuborilgan bo'lsa), uni **kompromisga uchragan** deb hisoblang va
zudlik bilan bekor qiling:

- Telegram token: BotFather → `/mybots` → botingiz → **API Token** → **Revoke current token**
- Gemini key: [Google AI Studio](https://aistudio.google.com/apikey) → eskisini o'chirib, yangi key yarating

## Tuzilma

```
planbot/
├── bot.py              # Asosiy bot fayli, barcha handlerlar
├── config.py            # .env dan sozlamalarni o'qiydi
├── db.py                 # SQLite baza (users, tasks, ai_plans, monthly_entries, chat_history)
├── gemini_service.py     # Gemini AI bilan ishlash (reja tuzish, suhbat)
├── keyboards.py          # Telegram tugmalar/menyular
├── requirements.txt
├── .env.example          # Namuna, haqiqiy kalitlar EMAS
└── .gitignore             # .env va *.db GitHub'ga tushmasligi uchun
```

## 5 ta menyu

1. **📊 Natijalarim** — jami/vajarilgan vazifalar soni, AI orqali tuzilgan rejalar soni, shu oy statistikasi.
2. **🤖 AI bilan reja tuzish** — maqsadingizni yozasiz, necha kunlik reja kerakligini aytasiz, Gemini kunlarga bo'lingan reja tuzib beradi, baza ga saqlanadi.
3. **💬 AI bilan suhbat** — Gemini bilan erkin suhbat, oxirgi xabarlar konteksti saqlanadi.
4. **🗓 Oylik rejalar** — Notion uslubidagi oylik ko'rinish: oy tugmalari bilan navigatsiya, kunni tanlab yozuv qo'shish/belgilash/o'chirish.
5. **📝 Rejalarim** — umumiy vazifalar ro'yxati: qo'shish, bajarildi deb belgilash, o'chirish.

## Kunlik avtomatik xabarlar

Bot har kuni **Toshkent vaqti bilan 08:00, 12:00 va 18:00** da barcha
`/start` bosgan foydalanuvchilarga avtomatik xabar yuboradi:

- **08:00** — bugungi kun uchun "Oylik rejalar"dagi yozuvlar ro'yxati
- **12:00** — bajarilmagan vazifalar soni bo'yicha eslatma
- **18:00** — kunlik natija xulosasi + ertaga uchun reja tuzishni eslatish

Bu `bot.py` ichidagi `send_daily_reminder` funksiyasi va `job_queue.run_daily(...)`
orqali ishlaydi (`python-telegram-bot[job-queue]` kutubxonasi kerak, u
`requirements.txt`ga qo'shilgan). Vaqtni o'zgartirish uchun `main()` funksiyasidagi
`dtime(hour=..., minute=...)` qiymatlarini tahrirlang.

**Eslatma**: bot doim ishlab turishi kerak (polling rejimida), aks holda
belgilangan vaqtda xabar yuborilmaydi — shuning uchun PythonAnywhere'da
uni doimiy jarayon (always-on task yoki `screen`/`tmux` ichida) sifatida
ishga tushiring.

## Mahalliy ishga tushirish

```bash
cd planbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env faylini ochib haqiqiy TELEGRAM_BOT_TOKEN va GEMINI_API_KEY ni yozing
python bot.py
```

## PythonAnywhere'ga joylash

1. **Fayllarni yuklash**: GitHub repo'ingizni Pythonanywhere konsolida clone qiling:
   ```bash
   git clone https://github.com/SIZNING_USERNAME/SIZNING_REPO.git
   cd SIZNING_REPO
   ```
2. **Virtual muhit yarating va kutubxonalarni o'rnating**:
   ```bash
   mkvirtualenv --python=python3.11 planbot-env
   pip install -r requirements.txt
   ```
3. **`.env` faylini qo'lda yarating** (PythonAnywhere Files bo'limida yoki konsolda `nano .env`):
   ```
   TELEGRAM_BOT_TOKEN=yangi_tokeningiz
   GEMINI_API_KEY=yangi_keyingiz
   GEMINI_MODEL=gemini-2.0-flash
   DB_PATH=/home/SIZNING_USERNAME/SIZNING_REPO/planbot.db
   ```
   Bu faylni hech qachon `git add` qilmang — `.gitignore` allaqachon uni chetlab o'tadi.
4. **"Always-on task" yarating** (PythonAnywhere'ning pullik rejasida mavjud;
   bepul rejada `Tasks` bo'limidan vaqti-vaqti bilan ishga tushirish yoki
   konsolni `screen`/`tmux` bilan ochiq qoldirish kerak bo'ladi):
   ```bash
   workon planbot-env
   python bot.py
   ```
5. Bot polling rejimida ishlaydi (`run_polling`), shuning uchun alohida webhook
   yoki Flask web app sozlashning hojati yo'q — jarayon doim ishlab tursa bas.

## Kengaytirish g'oyalari

- "Rejalarim"ga muddat (deadline) va eslatma (reminder) qo'shish
- "Natijalarim"da haftalik/oylik grafik (masalan, matplotlib bilan rasm yuborish)
- AI tuzgan rejani to'g'ridan-to'g'ri "Oylik rejalar"ga avtomatik taqsimlab qo'yish
