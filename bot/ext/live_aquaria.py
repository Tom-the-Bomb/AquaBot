from typing import Any, ClassVar, Optional
from urllib.parse import quote
import json

import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from bs4.element import Tag

from ..bot import AquaBot
from ..context import AquaContext

from ..utils import *

class LAResultsSelect(discord.ui.Select):
    
    def __init__(self, bot: AquaBot, items: list[dict[str, str]]) -> None:

        self.items = items

        options = [
            discord.SelectOption(
                value=item['url'], 
                label=item['name'], 
                description=item['price']
            ) for item in self.items
        ]
        super().__init__(
            placeholder='Select a product to view',
            min_values=1,
            max_values=1,
            options=options,
        )
        self.bot = bot

    @to_thread
    def _parse_product_html(self, html: str) -> dict[str, Any]:
        BASE_URL = 'https://www.liveaquaria.com'

        soup = BeautifulSoup(html, features='lxml')
        data = soup.find('script', type='application/ld+json').contents[0]
        data = json.loads(data)

        if not (img := data.get('image')) or img == BASE_URL:
            image_div = soup.find('div', class_='product-image')
            image = BASE_URL + image_div.find('img').get('src')
            data['image'] = image

        return data

    async def scrape_la_product(self, product_url: str) -> tuple[str, dict[str, Any]]:
        async with self.bot.session.get(product_url) as response:
            if response.ok:
                html = await response.text(encoding='utf-8')
                return (product_url, await self._parse_product_html(html))
            else:
                raise ApiError(f'{response.status}, Something went wrong while searching :(')

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        url, data = await self.scrape_la_product(self.values[0])
        description = truncate(data.get('description') or '-')

        embed = discord.Embed(
            title=data.get('name') or '-',
            url=url,
            description=description,
            color=self.bot.color,
        )

        if image := data.get('image'):
            embed.set_image(url=image)

        return await interaction.followup.send(embed=embed, ephemeral=True)

class LiveAquaria(commands.Cog):
    LA_URL: ClassVar[str] = 'https://aquarium-fish.liveaquaria.com/api/Search/'
    
    def __init__(self, bot: AquaBot) -> None:
        self.bot = bot

    def _format_item(self, item: Tag) -> dict[str, str]:
        url = item.find('a').get('href')
        img = item.find('div', class_='product_image')
        img = img.find('img', class_='image').get('src')

        details = item.find('div', class_='product_details')
        price = details.find('div', class_='price').contents[0]
        name = details.find('h3', class_='title').contents[0]

        return {
            'name': name, 'url': url, 
            'img': img, 'price': price,
        }

    @to_thread
    def _parse_results_html(self, html: str, *, limit: Optional[int] = None) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, features='lxml')
        results = soup.find_all('div', class_='product')
        results = [self._format_item(item) for item in results[:limit]]
        return results
    
    async def scrape_la(self, query: str, *, limit: Optional[int] = None) -> list[dict[str, str]]:
        async with self.bot.session.get(self.LA_URL + quote(query)) as response:
            if response.ok:
                html = await response.text(encoding='utf-8')
                return await self._parse_results_html(html, limit=limit)
            else:
                raise ApiError(f'{response.status}, Something went wrong while searching :(')

    def _format_item_embed(self, item: dict[str, str]) -> discord.Embed:
        embed = discord.Embed(
            title=item['name'],
            url=item['url'],
            description=f'Price : `{item["price"]}`',
            color=self.bot.color,
        )
        embed.set_thumbnail(url=item['img'])
        return embed

    @commands.command(name='liveaquaria', aliases=['la'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def live_aquaria(self, ctx: AquaContext, *, query: str) -> discord.Message:
        results = await self.scrape_la(query, limit=10)

        if not results:
            return await ctx.reply(f'No results were found for the query : {query}')

        entries = [discord.Embed(
            title='Results',
            description='\n\n'.join(
                f'**{i}. [{item["name"]}]({item["url"]})**\nPrice : `{item["price"]}`' for i, item in enumerate(results, 1)
            ),
            color=self.bot.color,
        )]

        entries += [self._format_item_embed(item) for item in results]

        paginator = Paginator(ctx, entries)
        paginator.view.add_item(LAResultsSelect(self.bot, results))
        return await paginator.start(reply=True)
        
def setup(bot: AquaBot) -> None:
    bot.add_cog(LiveAquaria(bot))