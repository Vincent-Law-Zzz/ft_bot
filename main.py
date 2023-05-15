import asyncio
from app.internal.services.bot import TelegramBot


if __name__ == "__main__":
	client = TelegramBot()
	asyncio.run(client.run())
