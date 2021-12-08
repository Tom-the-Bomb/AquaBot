from typing import Union, Optional
from urllib.parse import urljoin
import re

import discord
from discord.ext import commands

from bs4 import BeautifulSoup
from bs4.element import Tag

from tabulate import tabulate

from numpy import array_split

from ..bot import AquaBot
from ..context import AquaContext

from ..utils import *

class FBResultsSelect(discord.ui.Select):
    
    def __init__(self, bot: AquaBot, items: list[dict[str, Union[tuple[str, str], str]]]) -> None:

        self.items = items

        options = [
            discord.SelectOption(
                value=f"{i} {item['species'][1]}", # this is to make each value different so discord does not send us an error
                label=f"{item['species'][0]} ({item['country']})", 
                description=item['type'][0],
            ) for i, item in enumerate(self.items)
        ]

        super().__init__(
            placeholder='Select a species to view',
            min_values=1,
            max_values=1,
            options=options,
        )

        self.bot = bot
        self.reference_pat = re.compile(r'\(Ref\.? ?(([0-9]|,)+)\);?')

    @to_thread 
    def parse_species_html(self, url: str, html: str) -> discord.Embed:
        soup = BeautifulSoup(html, features='lxml')
    
        embed = discord.Embed(
            description='', 
            url=url,
            color=self.bot.color
        )

        main_div = soup.find('div', id='ss-container')
        name_div = main_div.find('div', id='ss-sciname')
        sci_name = ' '.join(
            word.contents[0].contents[0].contents[0]
            for word in name_div.find_all('span', class_='sciname')
        ).title()
        author_ref = ', '.join(
            word.contents[0].contents[0]
            for word in name_div.find_all('span', class_='sheader6 noLinkDesign')
        ).title()
        cm_name = name_div.find('span', class_='sheader2').contents[0]

        embed.title = f'{sci_name} | {author_ref}'
        embed.description += f'*{cm_name.strip()}*\n\n'

        images = main_div.find('div', id='ss-photomap-container')
        main_image = images.find('div', id='ss-photo') or images.find('div', id='ss-photo-full')

        if main_image:
            main_image = main_image.find('img')
            main_image = urljoin(url, main_image.get('src'))
            embed.set_image(url=main_image)

        map_image = images.find('div', id='ss-map')

        if map_image:
            map_image = map_image.find('img')
            map_image = urljoin(url, map_image.get('src'))
            embed.set_thumbnail(url=map_image)

        body_div = main_div.find('div', id='ss-main')
        contents = body_div.find_all('div', class_='smallSpace')

        classification = ''.join(tuple(contents[0].stripped_strings)[:5])
        embed.description += f'**Classification:**\n{classification}\n\n'

        env = ''.join(tuple(contents[1].stripped_strings)[0].removesuffix('(Ref.'))
        embed.description += f'**Environment:**\n{env}\n\n'

        location = ''.join(tuple(contents[2].strings))
        location = self.reference_pat.sub(' ', location)
        embed.description += f'**Location:**\n{location.strip()}\n\n'

        properties = ''.join(tuple(contents[3].stripped_strings))
        properties = properties.replace('&nbsp', ' ').replace('?', ' ')
        properties = self.reference_pat.sub(' ', properties)
        embed.description += f'**Description:**\n{properties}\n\n\n'

        all_headers = body_div.find_all('h1', class_='slabel bottomBorder')
    
        headers = []
        for header in all_headers:
            headers += tuple(header.stripped_strings)
        has_desc = 'short description' in ''.join(headers).lower()

        biology_idx = 5 if has_desc else 4

        biology = ''.join(tuple(contents[biology_idx].stripped_strings))
        biology = self.reference_pat.sub(' ', biology)
        embed.add_field(name='\u200b', value=biology)

        consv = list(body_div.find('span', class_='"black"').strings)[0]
        embed.add_field(name='\u200b', value=f'**Conservation Status**\n{consv}', inline=False)

        return embed
        
    async def scrape_species(self, url: str) -> Optional[discord.Embed]:
        async with self.bot.session.get(url) as response:
            if response.ok:
                html = await response.text(encoding='utf-8')
                return await self.parse_species_html(url, html)
            else:
                raise ApiError(f'{response.status}, Something went wrong while searching :(')

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        embed = await self.scrape_species(self.values[0].split()[-1])
        return await interaction.followup.send(embed=embed, ephemeral=True)

class FishBase(commands.Cog):
    FB_URL = 'https://fishbase.se'

    def __init__(self, bot: AquaBot) -> None:
        self.bot = bot

    def _parse_item(self, base_url: str, item: Tag) -> Union[str, tuple[str, str]]:
        contents = item.contents
        if len(contents) == 1:
            return contents[0]
        else:
            hl = contents[1].find('a') or contents[1]
            url = urljoin(base_url, hl.get('href'))
            name = hl.contents[0]
            return name, url

    @to_thread
    def _parse_result_html(self, url: str, html: str) -> Union[str, list[dict[str, str]]]:
        headers = ['common name', 'language', 'country', 'species', 'type']
        soup = BeautifulSoup(html, features='lxml')
        if data := soup.find('table'):
            data = data.find_all('tr')
            data = [
                {key: self._parse_item(url, item) for key, item in zip(headers, result.find_all('td'))}
                for result in data
            ]
            return data
        else:
            return 'No exact matches were found :('

    async def scrape_fb(self, type_: str, query: str):
        payload = {type_: query}
        ENDPOINT = (
            '/ComNames/CommonNameSearchList.php' if type_ == 'CommonName' else 
            '/Nomenclature/ScientificNameSearchList.php' if type_ == 'gs' else ''
        )

        URL = self.FB_URL + ENDPOINT
        async with self.bot.session.post(URL, data=payload) as response:
            if response.ok:
                html = await response.text(encoding='utf-8')
                return await self._parse_result_html(URL, html)
            else:
                raise ApiError(f'{response.status}, Something went wrong while searching :(')

    async def do_fishbase(self, ctx: AquaContext, query: str, type_: str) -> discord.Message:
        results = await self.scrape_fb(type_, query)

        if isinstance(results, str):
            return await ctx.send(results)
        else:
            fm_results = [
                f'**{num}.**\n\n' + '\n'.join([
                    (f'**{h.title()}**: {r}' if isinstance(r, str) else f'**{h.title()}**: [{r[0]}]({r[1]})') for h, r in r.items()
                ]) for num, r in enumerate(results[1:], 1)
            ]

            entries = [discord.Embed(description=desc, color=ctx.bot.color) for desc in fm_results]
                
            paginator = Paginator(ctx, entries)
            paginator.view.add_item(FBResultsSelect(self.bot, results[1:]))

            return await paginator.start(reply=True)

    @commands.group(name='fishbase', aliases=['fb'], invoke_without_command=True)
    async def fishbase_cmd(self, ctx: AquaContext, *, query: str) -> discord.Message:
        return await self.do_fishbase(ctx, query, 'CommonName')

    @fishbase_cmd.command(name='common', aliases=['cm', 'common_name', 'cname'])
    async def common_name(self, ctx: AquaContext, *, query: str) -> discord.Message:
        return await self.do_fishbase(ctx, query, 'CommonName')
    
    @fishbase_cmd.command(name='sci', aliases=['scientific', 'sciname', 'sn'])
    async def sci_name(self, ctx: AquaContext, *, query: str) -> discord.Message:
        return await self.do_fishbase(ctx, query, 'gs')

def setup(bot):
    bot.add_cog(FishBase(bot))