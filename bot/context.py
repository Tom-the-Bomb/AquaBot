from typing import Any

import discord
from discord.ext import commands

class AquaContext(commands.Context):

    async def reply(self, content: Any = None, **kwargs) -> discord.Message:
        mention_author = kwargs.pop('mention_author', False)
        return await super().reply(content, mention_author=mention_author, **kwargs)

    async def send(self, content: Any = None, **kwargs) -> discord.Message:
        try:
            return await super().send(content, **kwargs)
        except discord.HTTPException as e:
            if (
                e.status == 400 and
                e.code == 50035 and
                e.text == 'invalid form body\nin content: must be 4000 or fewer in length.'
            ):
                return await super().send(await self.bot.post_mystbin(content), **kwargs)
            else:
                raise e