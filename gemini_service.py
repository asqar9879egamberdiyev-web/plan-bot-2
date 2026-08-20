from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

PLAN_SYSTEM_PROMPT = (
    "Sen shaxsiy reja tuzuvchi yordamchisan. Foydalanuvchi bergan maqsad yoki vazifa "
    "asosida aniq, bajarilishi mumkin bo'lgan, kunlarga bo'lingan reja tuz. "
    "Har bir kun uchun 2-4 ta aniq, o'lchanadigan vazifa yoz. "
    "Javobni faqat o'zbek tilida, tushunarli va tartibli formatda yoz "
    "(masalan: '1-kun:', '2-kun:' kabi sarlavhalar bilan). Ortiqcha kirish so'zlarsiz, "
    "to'g'ridan to'g'ri reja matnini ber."
)

CHAT_SYSTEM_PROMPT = (
    "Sen do'stona, qo'llab-quvvatlovchi shaxsiy AI yordamchisisan. Foydalanuvchi bilan "
    "o'zbek tilida (agar u boshqa tilda yozmasa) samimiy va foydali suhbat qur. "
    "Javoblaring qisqa va aniq bo'lsin, lekin kerak bo'lsa batafsil tushuntir."
)


def generate_plan(goal_text: str, days: int = 7) -> str:
    prompt = f'Maqsad/vazifa: "{goal_text}"\nUshbu maqsad uchun {days} kunlik reja tuzib ber.'
    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=PLAN_SYSTEM_PROMPT),
    )
    return response.text.strip()


def chat_reply(history: list, user_message: str) -> str:
    """history: [{'role': 'user'|'model', 'content': str}, ...] eski xabarlar"""
    contents = []
    for h in history:
        contents.append(
            types.Content(role=h["role"], parts=[types.Part(text=h["content"])])
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT),
    )
    return response.text.strip()
