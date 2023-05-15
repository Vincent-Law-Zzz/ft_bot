from typing import Literal, Optional

import pydantic

__all__ = ['Player']


class BasePlayer(pydantic.BaseModel):
	...


class Player(BasePlayer):
	chat_id: int
	balance: int
	current_strategy: Optional[str] = None
	name: Optional[str] = None

