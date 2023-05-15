import numpy as np
from typing import List, Dict

__all__ = ['Map']


class Map:
	empty_field: str = "◽️"
	border: str = "◼️"
	cursor: str = "🚩"
	position: Dict[str, int] = {}

	def __init__(self, x: int, y: int, conf: List[List[str]]):
		self.conf = conf
		self.x = x
		self.y = y
		self.position['x'] = self.x // 2
		self.position['y'] = self.y // 2
		self.map = None

	async def __read(self):
		x = 0
		y = 0
		for i in self.conf:
			for j in i:
				if not int(j) // 10:
					self.conf[x][y] += """   """
				elif not int(j) // 100:
					self.conf[x][y] += """  """
				elif not int(j) // 1000:
					self.conf[x][y] += """ """
				y += 1
			y = 0
			x += 1
		self.conf = list(np.array(self.conf))

	async def __create_header(self):
		res = []
		for i in range(self.x):
			res.append(self.border)
		res.append(" ")
		for i in ["🔴  ", "🟢  ", "🟡"]:
			res.append(i)
		return res
	
	async def reset(self):
		self.position['x'] = self.x // 2
		self.position['y'] = self.y // 2
		await self.build()

	async def build(self):
		matrix = []
		for i in range(self.x):
			matrix.append([])

		for i in range(self.y):
			for j in range(self.x):
				matrix[j].append(self.empty_field)

		matrix[self.position['x']][self.position['y']] = self.cursor
		await self.__read()

		matrix = matrix + self.conf

		header = await self.__create_header()
		matrix = np.array(matrix).transpose()
		self.map = [header] + list(matrix)

	async def __yellow_move(self, y_count: int):
		if y_count == 0:
			return
		level_delta = (y_count + self.position['x']) // self.x
		row_delta = (y_count + self.position['x']) % self.x
		new_y = self.position['y'] + level_delta
		if new_y < self.y:
			self.position['x'] = row_delta
			self.position['y'] = new_y
		else:
			self.position['x'] = self.x - 1
			self.position['y'] = self.y - 1

	async def __red_move(self, r_count: int):
		if r_count == 0:
			return
		new_x = self.position['x']
		new_y = self.position['y']
		while r_count > 0:
			r_count -= 1
			new_x -= 1
			if new_x < 0:
				new_y -= 1
				new_x = self.x - 1

		if new_y >= 0:
			self.position['x'] = new_x
			self.position['y'] = new_y
		else:
			self.position['x'] = 0
			self.position['y'] = 0

	async def get_current_payment(self):
		return [int(i) for i in self.map[self.position['y'] + 1][-3:]]

	async def move(self, r_count: int, y_count: int):
		if y_count > 0:
			await self.__yellow_move(y_count)
		else:
			await self.__red_move(r_count)
		await self.build()

	def __str__(self):
		res = ""
		for i in self.map:
			for j in i:
				res += f"{j}"
			res += f"\n"
		for i in range(self.x):
			res += self.border
		return res

