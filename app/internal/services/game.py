import logging
from typing import List, Dict

from app.pkg.models import Player
from app.internal.services.map import Map


class Game:
	players: List[Player]
	is_game_stared: bool
	map: Map

	def __init__(self, q_map: Map):
		self.map = q_map
		self.players = []
		self.is_game_stared = False
		self.strategy = None

	async def add_player(self, tg_id: int) -> None:
		player = Player(
			chat_id=tg_id,
			balance=0
		)
		if player not in self.players:
			self.players.append(
				player
			)

	async def start_game(self) -> None:
		await self.map.build()
		await self.set_player_name()
		self.is_game_stared = True

	async def stop_game(self) -> None:
		self.is_game_stared = False
		self.players = []
		await self.map.reset()

	async def set_player_strategy(self, chat_id: int, st: str) -> None:
		player_num = 0
		for p in self.players:
			if int(p.chat_id) == int(chat_id):
				self.players[player_num].current_strategy = st
			player_num += 1

	async def reset_players_strategy(self) -> None:
		for p in self.players:
			p.current_strategy = None

	async def summary_strategy(self) -> Dict[str, int]:
		w_st_count = 0
		b_st_count = 0
		r_st_count = 0
		g_st_count = 0
		y_st_count = 0

		for p in self.players:
			if p.current_strategy == "🟢":
				g_st_count += 1
			elif p.current_strategy == "🔴":
				r_st_count += 1
			elif p.current_strategy == "🟡":
				y_st_count += 1
			elif p.current_strategy == "🔵":
				b_st_count += 1
			elif p.current_strategy == "⚪":
				w_st_count += 1
			else:
				continue

		return {
			"y": y_st_count,
			"b": b_st_count,
			"w": w_st_count,
			"g": g_st_count,
			"r": r_st_count
		}

	async def update_players(self, payment: List[int]):
		player_num = 0
		for p in self.players:
			if p.current_strategy == "🟢":
				self.players[player_num].balance += payment[1]
			elif p.current_strategy == "🔴":
				self.players[player_num].balance += payment[0]
			elif p.current_strategy == "🟡":
				self.players[player_num].balance += payment[2]
			player_num += 1

		await self.reset_players_strategy()

	async def finish_round(self) -> None:
		st_count = await self.summary_strategy()
		self.strategy = st_count
		await self.map.move(r_count=st_count['r'], y_count=st_count['y'])
		payment = await self.map.get_current_payment()
		summary_payment = [
			payment[0] + 20 * st_count['w'],
			payment[1],
			payment[2] - 20 * st_count['b']
		]
		await self.update_players(payment=summary_payment)

	async def set_player_name(self) -> None:
		player_num = 0
		for p in self.players:
			logging.info(f"{p}")
			self.players[player_num].name = f"player_{player_num + 1}"
			player_num += 1

	async def get_player_name(self, chat_id: int) -> str:
		res = "Ваш номер:\n"
		for p in self.players:
			if p.chat_id == chat_id:
				res += p.name

		return res

	async def get_players_top(self) -> str:
		player_position = 1
		top_of_players = sorted(self.players, key=lambda x: x.balance, reverse=True)
		top_text = "Итоги:\n"
		for p in top_of_players:
			top_text += f"{player_position} {p.name} {p.balance}\n"
			player_position += 1
		top_text += f"\n🔴{self.strategy['r']} 🟢{self.strategy['g']} 🟡{self.strategy['y']} " \
					f"🔵{self.strategy['b']} ⚪{self.strategy['w']}"
		return top_text

