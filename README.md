# Quick start

## Get token from Gemini for free use with limit.
https://aistudio.google.com/

## Click the link below to create your Telegram bot and get token.
https://telegram.me/BotFather

## Create file .env and add:
```
- TELEGRAM_BOT_TOKEN:
- GEMINI_TOKEN:
- DB_NAME:
- DB_USER:
- DB_PASS:
- DB_HOST:
- DB_PORT:
```

## Add prompt.yaml
```
content: |
  You are ...
  .
  .
  .
  ## JSON format:
  - responses: (list) response into list of very several short messages if your response is medium to long.

  ## Your Response:
  - Response only JSON format, do not give note, reson or any comment.
  - You may split your response into very several short messages to response in JSON responses for examples responses: 
  -- responses: ['the man who stand toward you','you walking to him','then he say','"you're not running but walking to me?"'] ,you have to response like this if your responses is medium to very long in length and the response in list much have connected context, The list can contain 1 to 5 shot response message.
  -- responses: ['you are so funny'], if your responses is short.
  - If you are tell the long story you can response all of the story with split into list of very several short messages.
  - Respond at the same language as your users.
```

## Docker compose
```docker compose up -d```
