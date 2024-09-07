from __future__ import annotations

from typing import Awaitable, Optional, Callable, TypeVar, Union
from typing_extensions import ParamSpec
from io import BytesIO
import functools
import asyncio
import secrets

import discord
import aiohttp

from .context import AquaContext
from .bot import AquaBot as bot

__all__: tuple[str] = (
    'Number',
    'num',
    'post_cdn',
    'to_thread',
    'truncate',
    'ApiError',
    'AuthorOnlyView',
    'PaginatorView',
    'Paginator',
)

P = ParamSpec('P')
T = TypeVar('T')

Number = Union[int, float]

async def post_cdn(session: aiohttp.ClientSession, fp: BytesIO) -> Optional[str]:
    data = aiohttp.FormData()
    data.add_field('file', fp, filename=f'{secrets.token_urlsafe()}.png')
    base = 'https://cdn.lambdabot.cf'

    async with session.post(
        base + '/upload',
        headers={'Authorization': 'Bearer aaa'},
        data=data,
        params={'directory': 'bomb_uploads'},
    ) as r:
        r.raise_for_status()
        data = await r.json()
        return base + '/uploads' + data.get('path')

def num(n: str) -> Number:
    n = float(n)
    if n.is_integer():
        n = int(n)
    return n

def to_thread(func: Callable[P, T]) -> Callable[P, Awaitable[T]]:

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
        return asyncio.to_thread(func, *args, **kwargs)

    return wrapper

def truncate(content: str, limit: int = 2000) -> str:
    if len(content) > limit:
        return content[:1997] + '...'
    else:
        return content

class ApiError(Exception):
    pass

class AuthorOnlyView(discord.ui.View):

    def __init__(self, author: discord.User, *, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message(f'This interaction can only be used by {self.author.mention}', ephemeral=True)
            return False
        else:
            return True

class PaginatorView(AuthorOnlyView):

    def __init__(self, author: discord.User, paginator: Paginator, *, timeout: float = None) -> None:
        super().__init__(author, timeout=timeout)

        self.paginator = paginator
        self.counter: int = 0

    def _update_sign(self) -> None:
        self.children[2].label = f'Page {self.counter + 1}'

    @discord.ui.button(
        emoji=bot.emojis['REWIND'],
        style=discord.ButtonStyle.gray,
    )
    async def rewind(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.counter = 0
        self._update_sign()
        return await interaction.message.edit(embed=self.paginator.entries[0], view=self)

    @discord.ui.button(
        label=bot.emojis['ARROW_LEFT'],
        style=discord.ButtonStyle.gray,
    )
    async def arrow_left(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        try:
            if self.counter == 0:
                return
            self.counter -= 1
            self._update_sign()
            return await interaction.message.edit(embed=self.paginator.entries[self.counter], view=self)
        except IndexError:
            return

    @discord.ui.button(
        label='Page 1',
        disabled=True,
        style=discord.ButtonStyle.blurple,
    )
    async def page_sign(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        return

    @discord.ui.button(
        label=bot.emojis['ARROW_RIGHT'],
        style=discord.ButtonStyle.gray,
    )
    async def arrow_right(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        try:
            if self.counter == len(self.paginator.entries):
                return
            self.counter += 1
            self._update_sign()
            return await interaction.message.edit(embed=self.paginator.entries[self.counter], view=self)
        except IndexError:
            return

    @discord.ui.button(
        emoji=bot.emojis['FAST_FW'],
        style=discord.ButtonStyle.gray,
    )
    async def fast_forward(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.counter = len(self.paginator.entries) - 1
        self._update_sign()
        return await interaction.message.edit(embed=self.paginator.entries[-1], view=self)

    @discord.ui.button(
        label=bot.emojis['STOP'] + ' stop',
        style=discord.ButtonStyle.red,
    )
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.message.edit(embed=self.paginator.entries[self.counter], view=self)
        return self.stop()

class Paginator:

    def __init__(self, ctx: AquaContext, entries: list[discord.Embed]) -> None:
        self.ctx = ctx
        self.entries = entries

        self.view = PaginatorView(self.ctx.author, self)

    async def start(self, *, reply: bool = False, **send_kwargs) -> discord.Message:
        method = self.ctx.reply if reply else self.ctx.send
        return await method(embed=self.entries[self.view.counter], view=self.view, **send_kwargs)