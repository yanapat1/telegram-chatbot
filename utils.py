from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, UUID, Boolean, text, DECIMAL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps
import uuid
import os
load_dotenv()

def get_engine():
    dbname = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_async_engine(DATABASE_URL, echo=False)

    return engine

Base = declarative_base()
class ChatHistory(Base):
    __tablename__ = 'chat_history'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    telegram_id = Column(Text, nullable=False)
    session_id = Column(Integer, nullable=False)
    human_message = Column(Text, nullable=False)
    ai_message = Column(Text, nullable=False)
    ai_assistant = Column(Text, nullable=True)
    raws = Column(Text, nullable=False)
    avg_logprobs = Column(DECIMAL, nullable=False)
    model_version = Column(Text, nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    deleted = Column(Boolean, nullable=False)

class Person(Base):
    __tablename__ = 'siam_user'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username = Column(UUID, nullable=False)
    password = Column(UUID, nullable=False)
    email = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    telegram_id = Column(Text, nullable=True)

class UserSession(Base):
    __tablename__ = 'user_session'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username = Column(UUID, nullable=False)
    telegram_id = Column(Text, nullable=True)
    session_id = Column(Integer, nullable=False)


def ASQLEexcute(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result_box = []
        engine = get_engine()
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        command_box = await func(*args, **kwargs)
        async with async_session() as session:
            for command, command_type in command_box:
                result = None
                match command_type:
                    case 'save_':
                        session.add(command)
                        await session.commit()
                    case 'read_':
                        result = await session.execute(command)
                        result = result.fetchall()
                    case 'update_':
                        await session.execute(command)
                        await session.commit()
                result_box.append(result)
            return result_box
    return wrapper

@ASQLEexcute
async def user_register(username: str,
                        password: str,
                        email:str ,
                        name:str,
                        telegram_id: str = None,
                        ) -> None:
    username = uuid.uuid3(uuid.NAMESPACE_DNS, username).__str__()
    password = uuid.uuid3(uuid.NAMESPACE_DNS, password).__str__()
    
    command1 = Person(
        username=username,
        password=password,
        email=email,
        name=name,
        telegram_id=telegram_id
    )

    command2 = UserSession(
        username=username,
        telegram_id=telegram_id,
        session_id=0
    )

    command_box = [
        [command1, 'save_'],
        [command2, 'save_']
        ]
    return command_box

@ASQLEexcute
async def grant_permission(username: str):
    username = uuid.uuid3(uuid.NAMESPACE_DNS, username).__str__()
    command = text(f"""
    UPDATE user_session
    SET permission = TRUE
    WHERE username = '{username}'
    """)
    command_box = [
        [command, 'update_']
    ]
    return command_box

@ASQLEexcute
async def user_permission_check(telegram_id: str):
    command = text(f"""
    SELECT permission, session_id FROM user_session
    WHERE telegram_id = '{telegram_id}'
    AND permission = TRUE
    """)

    command_box = [
        [command, 'read_']
    ]
    return command_box

@ASQLEexcute
async def update_session(username: str, telegram_id: str, session_id: int):
    command = UserSession(
        username=username,
        telegram_id=telegram_id,
        session_id=session_id
    )
    return command

@ASQLEexcute
async def change_session(telegram_id: str, session_id: int):
    command1 = text(f"""
    UPDATE chat_history
    SET deleted = TRUE
    WHERE telegram_id = '{telegram_id}'
    AND session_id = '{session_id}'
    """)

    command2 = text(f"""
    UPDATE user_session
    SET session_id = session_id + 1
    WHERE telegram_id = '{telegram_id}'
    """)

    command_box = [
        [command1, 'update_'],
        [command2, 'update_']
    ]
    return command_box

@ASQLEexcute
async def get_chat_history(telegram_id: int):
    command = text(f"""
    SELECT raws FROM chat_history
    WHERE session_id = (SELECT session_id FROM user_session WHERE telegram_id = '{telegram_id}') 
    AND telegram_id = '{telegram_id}'
    ORDER BY timestamp
    """)

    command_box = [
        [command, 'read_']
    ]
    return command_box

@ASQLEexcute
async def save_message(telegram_id: str, 
                       session_id: int, 
                       human_message: str,
                       ai_message: str,
                       ai_assistant: str,
                       raws: str,
                       input_tokens: int,
                       output_tokens: int,
                       total_tokens: int,
                       avg_logprobs: float = None,
                       model_version: str = None
                       ):
    command = ChatHistory(
        telegram_id=telegram_id,
        session_id=session_id,
        human_message=human_message,
        ai_message=ai_message,
        ai_assistant=ai_assistant,
        raws=raws,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        avg_logprobs=avg_logprobs,
        model_version=model_version,
        deleted=False
    )

    command_box = [
        [command, 'save_']
    ]

    return command_box
    
@ASQLEexcute
async def get_llm_price():
    command = text(f"""
    SELECT input_tokens, output_tokens FROM chat_history
    """)

    command_box = [
        [command, 'read_']
    ]
    return command_box