
from urllib.parse import quote

import discord
from discord.ext import commands

from bs4 import BeautifulSoup
from bs4.element import Tag

from tabulate import tabulate

from ..bot import AquaBot
from ..context import AquaContext

from ..utils import *

class FishBase(commands.Cog):
    FB_URL = 'https://fishbase.se'

    def __init__(self, bot: AquaBot) -> None:
        self.bot = bot

    def _parse_item(self, item: Tag) -> str:
        contents = item.contents
        if len(contents) == 1:
            return contents[0]
        else:
            hl = contents[1].find('a') or contents[1]
            url = self.FB_URL + hl.get('href').strip('.')
            name = hl.contents[0]
            return f'[{name}]({url})'

    @to_thread
    def _parse_result_html(self, html: str):
        soup = BeautifulSoup(html, features='lxml')
        if data := soup.find('table'):
            data = data.find_all('tr')
            data = [
                [self._parse_item(item) for item in result.find_all('td')] 
                for result in data
            ]
            return data
        else:
            return 'No exact matches were found :('

    async def scrape_fb(self, type_: str, query: str):
        payload = {type_: quote(query)}
        ENDPOINT = '/ComNames/CommonNameSearchList.php' if type_ == 'CommonName' else 'gs'
        async with self.bot.session.post(self.FB_URL + ENDPOINT, data=payload) as response:
            if response.ok:
                html = await response.text(encoding='utf-8')
                return await self._parse_result_html(html)
            else:
                raise ApiError(f'{response.status}, Something went wrong while searching :(')

    @commands.command(name='fishbase', aliases=['fb'])
    async def fishbase(self, ctx, query: str):
        results = await self.scrape_fb('CommonName', query)
        if isinstance(results, str):
            return await ctx.send(results)
        else:
            results = [discord.Embed(description='\n'.join(f)) for f in results[1:]]
            paginator = Paginator(ctx, results)
            await paginator.start(reply=True)

def setup(bot):
    bot.add_cog(FishBase(bot))