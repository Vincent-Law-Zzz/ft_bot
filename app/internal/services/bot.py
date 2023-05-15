import asyncio
import logging
import textwrap
import uuid
from typing import Callable, Optional, List

import pydantic
from aiogram import Bot, Dispatcher, types, utils
from aiogram.utils import executor, exceptions
from aiogram.utils.callback_data import CallbackData
from pydantic import SecretStr, PositiveInt

from app.internal.services.game import Game
from app.internal.services.map import Map
from app.pkg.settings import get_settings


class TelegramBot:
	game: Game

	def __init__(self):
		self.game = Game(
			Map(
				x=7,
				y=11,
				conf=[
					['200', '120', '80', '50', '30', '20', '10', '5', '0', '0', '0'],
					['180', '150', '100', '70', '50', '40', '30', '15', '10', '5', '0'],
					['190', '210', '150', '120', '100', '80', '50', '30', '20', '10', '5']
				]
			)
		)
		logging.basicConfig(level=logging.INFO)
		self.settings = get_settings()
		self.bot: Bot = Bot(token=self.settings.TELEGRAM_TOKEN.get_secret_value())
		self.dp: Dispatcher = Dispatcher(self.bot)
		self.callback = CallbackData('codes', 'action', 'tg_id')

	async def cmd_start(self, message: types.Message) -> None:
		"""
		Conversation's entry point
		"""
		start_text = textwrap.dedent(
			"""
			<b>▪️Здравствуйте!</b> 
			<i>Правила игры:
			Каждый человек представляет предприятие реального сектора, расположенного на берегу одного и того же озера. Для осуществления своей деятельности команды используют воду из озера. Вода загрязняется в результате их технологической деятельности. Компании устанавливают технологию, которая может полностью очищать, частично очищать или вообще не очищать воду. В зависимости о того, насколько они очищают воду, у них увеличивается доход. Всего игра продолжается 5 лет. Каждый год разделен на кварталы – 20 кварталов в течение всей игры. В течение каждого квартала компания выбирает свою стратегию.
			Стратегий всего 5, имеют условные названия цветов:
			Красная – Я полностью выполняю все экологические нормы, я инвестирую в развитие экологических мероприятий, развитие очистных сооружений, берегу природу
			Зеленая – Я очищаю воду, но не всю, оптимизирую затраты. Я зарабатываю чуть больше чем тот, кто полностью очищает воду и чуть меньше, чем тот, кто не очищает воду вообще
			Желтая – Гори все огнем, хочу денег как можно больше здесь и сейчас, поэтому я воду вообще не очищаю
			Синий – Есть возможность поехать в политический центр и сообщить, что на озере творится безобразие. Тогда все, кто выбрал в этом квартале Желтую стратегию будут оштрафованы на 20.
			Белый – Можно поехать в политический центр и поощрить тех, кто бережно относится к экологии. Им выделят субсидию. Все, кто выбрал в этом квартале Красную стратегию будут поощрены на 20.
			*Если два игрока выбрало С или Б стратегию, то К или Ж игроки будут поощрены или оштрафованы на 40.
			* Игрок, который выбирает либо синюю либо белую стратегию зарабатывает в этом квартале 0.
			* Маркер двигается только от Желтой или Красной Стратегии
			
			Правила: Вы в течение каждого квартала выбираете стратегию, и ваша цель – заработать для себя как можно больше денег в течение 5 лет. То есть максимизировать заработанные деньги для себя любимого.
			Эти заработки компании рассчитываются по таблице в зависимости от выбранной стратегии.
			Красный маркер движется по определенным законам.
			В положительное направление маркер идет налево и вверх
			В отрицательное направление маркер идет направо и вниз
			</i>
			"""
		)
		await self.bot.send_message(text=start_text, chat_id=message.chat.id, parse_mode='HTML')

	async def start_game(self, message: types.Message) -> None:
		await self.game.start_game()
		game_id = uuid.uuid4()
		logging.info(f"Game started: {game_id}")
		await self.send_message(user_id=message.chat.id, text=f"Игра запущена {game_id}")
		await self.game_processing(game_id)

	async def stop_game(self, message: types.Message) -> None:
		await self.game.stop_game()
		await self.send_message(user_id=message.chat.id, text="Игра остановлена")

	async def notif_player_name(self):
		for p in self.game.players:
			name = await self.game.get_player_name(p.chat_id)
			await self.send_message(user_id=p.chat_id, text=name)

	async def iteration_qrtl_year(self, qrtl, year):
		if qrtl == 0:
			year += 1
		qrtl += 1
		if qrtl == 5:
			qrtl = 1
			year += 1
			await asyncio.sleep(self.settings.YEARS_TIME_SLEEP)
		return qrtl, year

	async def game_processing(self, game_id: uuid.UUID):
		year = 0
		qrtl = 0
		await self.notif_player_name()
		while self.game.is_game_stared and (year < 5 or qrtl < 4):
			qrtl, year = await self.iteration_qrtl_year(qrtl, year)
			for p in self.game.players:
				kb = await self.get_keyboard(chat_id=p.chat_id)
				await self.bot.send_message(
					chat_id=p.chat_id,
					text=f"Выбери стратегию на {qrtl} квартал {year} года",
					reply_markup=kb
				)
			await asyncio.sleep(self.settings.QRTL_TIME_SLEEP - 10)
			for p in self.game.players:
				await self.bot.send_message(
					chat_id=p.chat_id,
					text=f"Осталось 10 секунд на принятие решения. "
				)
			await asyncio.sleep(10)
			await self.game.finish_round()
			for p in self.game.players:
				await self.send_message(user_id=p.chat_id, text=str(self.game.map))
			logging.info(f"map:\n{self.game.map}")
			top = await self.game.get_players_top()
			logging.info(f"Топ игроков:\n{top}")
			for p in self.game.players:
				await self.send_message(user_id=p.chat_id, text=f"Квартал: {qrtl} Год: {year}\n{top}")
		logging.info(f"Игра окончена {game_id}")

	async def play(self, message: types.Message):
		await self.game.add_player(message.chat.id)
		await self.send_message(user_id=message.chat.id, text="Вы были зарегистрированы. Дождитесь начала игры.")

	async def set_strategy(self, query: types.CallbackQuery, callback_data: dict):
		await self.game.set_player_strategy(chat_id=callback_data['tg_id'], st=callback_data['action'])
		await self.bot.edit_message_text(
			f'Ответ принят.',
			query.from_user.id,
			query.message.message_id
		)
		logging.info(f"Player:{query.from_user} {callback_data['action']}")

	async def send_message(self, user_id: int, text: str, disable_notification: bool = False, *args, **kwargs) -> bool:
		"""
		Safe messages sender

		:param user_id:
		:param text:
		:param disable_notification:
		:return:
		"""
		try:
			await self.bot.send_message(user_id, text, disable_notification=disable_notification, *args, **kwargs)
		except exceptions.BotBlocked:
			logging.error(f"Target [ID:{user_id}]: blocked by user")
		except exceptions.ChatNotFound:
			logging.error(f"Target [ID:{user_id}]: invalid user ID")
		except exceptions.RetryAfter as e:
			logging.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
			await asyncio.sleep(e.timeout)
			return await self.send_message(user_id, text, *args, **kwargs)  # Recursive call
		except exceptions.UserDeactivated:
			logging.error(f"Target [ID:{user_id}]: user is deactivated")
		except exceptions.TelegramAPIError:
			logging.exception(f"Target [ID:{user_id}]: failed")
		else:
			logging.info(f"Target [ID:{user_id}]: success")
			return True
		return False

	async def get_keyboard(self, chat_id: int):
		print(chat_id)
		return types.InlineKeyboardMarkup().row(
			types.InlineKeyboardButton(
				'🔴',
				callback_data=self.callback.new(action='🔴', tg_id=chat_id)
			),
			types.InlineKeyboardButton(
				'🟢',
				callback_data=self.callback.new(action='🟢', tg_id=chat_id)
			),
			types.InlineKeyboardButton(
				'🟡',
				callback_data=self.callback.new(action='🟡', tg_id=chat_id)
			),
			types.InlineKeyboardButton(
				'🔵',
				callback_data=self.callback.new(action='🔵', tg_id=chat_id)
			),
			types.InlineKeyboardButton(
				'⚪',
				callback_data=self.callback.new(action='⚪', tg_id=chat_id)
			),
		)

	def register_handlers(self):
		self.dp.register_message_handler(self.cmd_start, commands="start")
		self.dp.register_message_handler(self.play, commands="play")
		self.dp.register_message_handler(self.start_game, commands="admin_start_game")
		self.dp.register_message_handler(self.stop_game, commands="admin_stop_game")

		self.dp.register_callback_query_handler(self.set_strategy, self.callback.filter(action='🔴'))
		self.dp.register_callback_query_handler(self.set_strategy, self.callback.filter(action='🟢'))
		self.dp.register_callback_query_handler(self.set_strategy, self.callback.filter(action='🟡'))
		self.dp.register_callback_query_handler(self.set_strategy, self.callback.filter(action='🔵'))
		self.dp.register_callback_query_handler(self.set_strategy, self.callback.filter(action='⚪'))

	# self.dp.register_message_handler(self.gen_admin_token, commands="gen_admin_token")
	# self.dp.register_message_handler(self.get_users, commands="all")
	# self.dp.register_message_handler(self.delete_user, commands="delete")
	# self.dp.register_message_handler(self.set_phone, commands="phone")

	# self.dp.register_callback_query_handler(self.get_recommendations, self.callback.filter(action='-6'))
	# self.dp.register_callback_query_handler(self.get_full_description, self.callback.filter(action='-7'))
	# self.dp.register_message_handler(
	# 	self.validate_token,
	# 	regexp=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
	# )
	# self.dp.register_message_handler(self.get_code_description)

	def run(self):
		loop = asyncio.get_event_loop_policy()
		loop = loop.get_event_loop()
		self.register_handlers()
		executor.start_polling(self.dp, skip_updates=True, loop=loop)
