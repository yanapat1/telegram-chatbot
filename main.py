from telegram.ext import ConversationHandler, ApplicationBuilder, CommandHandler, ContextTypes
# from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from telegram import Update
from typing import Dict
import random
import asyncio
import json
import yaml
import os

from google.generativeai.types import HarmCategory, HarmBlockThreshold
import google.generativeai as genai


from utils import (
    user_register,
    grant_permission,
    user_permission_check,
    update_session,
    change_session,
    get_chat_history,
    save_message
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

################ /START ################
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your bot\nPlease /register to using bot.")

########################################

################ /REGISTER ################
NAME, CONFIRM = range(2)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    await update.message.reply_text("Hello! What is your name? 😊")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text

    summary = (
        f"Please confirm your info:\n"
        f"👤 Name: {context.user_data['name']}\n"
        f"Is this correct?"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data='yes'), InlineKeyboardButton("❌ No", callback_data='no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(summary, reply_markup=reply_markup)
    return CONFIRM

import uuid
async def reister_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await user_register(
        username=query.from_user.username,
        password=uuid.uuid4().__str__(),
        email='test@test.com',
        name=context.user_data['name'],
        telegram_id=str(query.from_user.id)
    )
    await grant_permission(query.from_user.username)
    await query.edit_message_text(text="✅ You're successfully registered!")
    return ConversationHandler.END

async def reister_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="❌ Let's try again.")
    return NAME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❎ Registration cancelled.")
    return ConversationHandler.END
########################################

def clean_json_response(raw_ai_message: str) -> str:
    repl = [
        ['```json',''],
        ['```','']
    ]
    for old, new in repl:
        raw_ai_message = raw_ai_message.replace(old, new)
    try:
        ai_message = json.loads(raw_ai_message)
    except Exception as e:
        print(e)
        ai_message = raw_ai_message

    return ai_message

async def normal_chatbot(teleram_id: str, message: str):
    
    ai_message = f'bot: {message} -> {teleram_id}'
    
    return ai_message


async def ai_chatbot(teleram_id: str, message: str, session: int, teleram_username: str):
    new_history = list()
    with open('prompt.yaml', 'r', encoding='utf-8') as f:
        prompt = yaml.safe_load(f)
        chat.set_system_prompt(prompt['content'].format(username=teleram_username))
    
    history = await get_chat_history(teleram_id)
    if history[0]:
        history = [j for i in history[0] for j in json.loads(i[0])]
        history.append({'role':'user', 'parts': [message]})
    else:
        history = message
    
    new_history.append({'role':'user', 'parts': [message]})
    response = await chat.ainvoke(history)
    raw_ai_message = response.content

    ## ADD ASSISTANT HERE ##
    ai_assistant = None

    #########################
    ## CLEAN CONTENT AND CHECK RESPONSE ##
    ai_message = clean_json_response(raw_ai_message)        
    
    ######################################

    new_history.append({'role':'model', 'parts': [raw_ai_message]})
    await save_message(
        telegram_id=teleram_id,
        session_id=session,
        human_message=message,
        ai_message=raw_ai_message,
        ai_assistant=ai_assistant,
        raws=json.dumps(new_history),
        input_tokens=response.usage_metadata['input_tokens'],
        output_tokens=response.usage_metadata['output_tokens'],
        total_tokens=response.usage_metadata['total_tokens'],
        avg_logprobs=response.avg_logprobs,
        model_version=response.model_version
    )
    if 'bye' in message.lower():
        await change_session(teleram_id, session)
    print(ai_message)
    return ai_message


#### MAIN REPLY MESSAGE 
async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teleram_id = update.message.chat.id
    teleram_username = update.message.chat.username
    str_teleram_id = str(teleram_id)
    message = update.message.text
    message_id = update.message.id

    check = await user_permission_check(str_teleram_id)
    if not check[0]:
        response = await normal_chatbot(str_teleram_id, message)
    else: 
        session = check[0][0][1]
        response = await ai_chatbot(str_teleram_id, message, session, teleram_username)
    
    if isinstance(response, dict):
        await context.bot.set_message_reaction(teleram_id, message_id, '👀', is_big=False)
        messages = [j for i in response['responses'] for j in i.split('  ')]
        for ai_message in messages:
            ai_message = ai_message.replace('  ',' ')
            timer = len(ai_message)*3

            await asyncio.sleep( random.randint( timer, timer+50) / 100 )
            await update.message.reply_text(ai_message)
        await context.bot.set_message_reaction(teleram_id, message_id, [], is_big=False)
    else:
        await update.message.reply_text(response)

def main():
    TOKEN = telegram_token
    app = ApplicationBuilder().token(TOKEN).build()


    app.add_handler(CommandHandler("start", start))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CONFIRM: [
                CallbackQueryHandler(reister_yes, pattern="yes"),
                CallbackQueryHandler(reister_no, pattern="no")
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, entry_point))
    
    print('start...')
    app.run_polling()

class ModelResponse(BaseModel):
    content: str
    usage_metadata: dict
    model_version: str = None
    avg_logprobs: float = None

class ModelGemini:
    def __init__(self, token: str, model_name: str = "gemini-1.5-flash-8b"):
        genai.configure(api_key=token)

        self.model_name = model_name

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.generation_config = genai.types.GenerationConfig(
            temperature = 1
            # candidate_count=1,
            # stop_sequences=['x'],
            # max_output_tokens=2048,
            # top_p=1
            # top_k=1
        )

        self.model = genai.GenerativeModel(
            model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
            )
        
    def set_system_prompt(self, system_instruction):
        self.system_instruction = system_instruction
        self.model = genai.GenerativeModel(
            self.model_name,
            generation_config = self.generation_config,
            safety_settings = self.safety_settings,
            system_instruction = self.system_instruction
            )

    async def ainvoke(self, content: str | List[Dict]):
        if isinstance(content, str):
            chat = self.model.start_chat()
        if isinstance(content, list):
            chat = self.model.start_chat(history=content[:-1])
            content = content[-1]['parts'][0]
        response = await chat.send_message_async(content)
        info_response = ModelResponse(
            content = response.candidates[0].content.parts[0].text,
            usage_metadata={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            },
            model_version = response.model_version,
            avg_logprobs = response.candidates[0].avg_logprobs
        )
        return info_response

if __name__ == "__main__":
    load_dotenv()
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    gemini_token = os.getenv('GEMINI_TOKEN')

    # os.environ["GOOGLE_API_KEY"] = gemini_token
    # chat = ChatGoogleGenerativeAI(model="gemini-1.5-flash-8b", temperature=1)

    chat = ModelGemini(token=gemini_token, model_name='gemini-1.5-flash')

    main()