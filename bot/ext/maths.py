from __future__ import annotations

from io import BytesIO
import re

import discord
from discord.ext import commands

import matplotlib
matplotlib.use('agg')

from matplotlib import pyplot as plt
import numpy as np

from ..bot import AquaBot
from ..context import AquaContext
from ..utils import *

X = '\U0001d465'
DEL = 'DEL'
WS = '\u200b'

class InvalidEquation(Exception):
    pass

class CalcButton(discord.ui.Button):

    view: LinearUI
    
    def __init__(self, label: str, *, style: discord.ButtonStyle = discord.ButtonStyle.grey, row: int, custom_id: str = None):
        super().__init__(style=style, label=str(label), row=row, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):

        process_embed = discord.Embed(
            title='Linear Equation Calculator', 
            description='Use the following buttons to input an equation in the format of: `y = mx + b`\nExample: `8 = 5x + 3`\nI will solve for `x`', 
            color=self.view.ctx.bot.color,
        )

        if self.label == 'Enter':
            try:
                m, x, b, y, steps = self.view.solve_lineareq_2(self.view.equation)
                fp = await self.view.linear_graph(m, b, x, y)
                embed = discord.Embed(title='Solution:', description=f'```py\n{steps}\n```', color=self.view.ctx.bot.color)
                url = await post_cdn(self.view.ctx.bot.session, fp)
                embed.set_image(url=url)
                return await interaction.message.edit(embed=embed, view=None)
            except InvalidEquation:
                return await interaction.message.edit(content=f'`{self.view.equation}` is an invalid einear equation, please try again.', embed=None, view=None)
        elif self.label == DEL:
            self.view.equation = self.view.equation[:-1]
            process_embed.description += f"\n\n```py\n{self.view.equation.replace('x', X) or WS}\n```"
            await interaction.message.edit(embed=process_embed)
        else:
            term = 'x' if self.label == X else self.label
            self.view.equation += term
            process_embed.description += f"\n\n```py\n{self.view.equation.replace('x', X)}\n```"
            await interaction.message.edit(embed=process_embed)

class CalcUI(AuthorOnlyView):

    def __init__(self, ctx: AquaContext, author: discord.User, *, timeout: float = None) -> None:
        super().__init__(author, timeout=timeout)

        self.ctx = ctx
        self.equation: str = ''

        for i in (1, 2, 3):
            self.add_item(CalcButton(i, row=0))
        for i in (4, 5, 6):
            self.add_item(CalcButton(i, row=1))
        for i in (7, 8, 9):
            self.add_item(CalcButton(i, row=2))

        self.add_item(CalcButton(".", row=3))
        self.add_item(CalcButton(0, row=3))
        self.add_item(CalcButton("=", row=3, style=discord.ButtonStyle.blurple))
        
        self.add_item(CalcButton('+', style=discord.ButtonStyle.red, row=0))
        self.add_item(CalcButton('-', style=discord.ButtonStyle.red, row=1))

    def multiply(self, a: Number, b: Number) -> Number:
        """multiplies 2 numbers"""
        return a * b

    def divide(self, a: Number, b: Number) -> Number:
        """divides 2 numbers; handles ZeroDivisionError"""
        if b == 0:
            return float('NaN')
        return a / b

    def solve_formula(self, a: Number, b: Number, c: Number, d: Number) -> Number:
        """Solves the formula (a + b * c) / d"""
        if d == 0:
            return float('NaN')
        return (a + b * c) / d

class LinearUI(AuthorOnlyView):

    def __init__(self, ctx: AquaContext, author: discord.User, *, timeout: float = None) -> None:
        super().__init__(author, timeout=timeout)

        self.ctx = ctx
        self.equation: str = ''

        for i in (1, 2, 3):
            self.add_item(CalcButton(i, row=0))
        for i in (4, 5, 6):
            self.add_item(CalcButton(i, row=1))
        for i in (7, 8, 9):
            self.add_item(CalcButton(i, row=2))

        self.add_item(CalcButton(".", row=3))
        self.add_item(CalcButton(0, row=3))
        self.add_item(CalcButton("=", row=3, style=discord.ButtonStyle.blurple))
        
        self.add_item(CalcButton('+', style=discord.ButtonStyle.red, row=0))
        self.add_item(CalcButton('-', style=discord.ButtonStyle.red, row=1))
        self.add_item(CalcButton(X, style=discord.ButtonStyle.blurple, row=2))
        self.add_item(CalcButton('Enter', style=discord.ButtonStyle.green, row=3))

        self.add_item(CalcButton(DEL, style=discord.ButtonStyle.red, row=0))
        
        for i in range(1, 4):
            self.add_item(CalcButton(WS, style=discord.ButtonStyle.grey, row=i))

    def solve_lineareq_2(self, equation: str) -> tuple[Number, str]:
        """
        parses a  2-step linear equation: (y = mx + b) as a string
        converts select terms to a float and evaluates it
        """

        eq = re.sub(r'\s+', '', equation)
        num_pat = r'[-+]?\d+\.?\d*'

        if terms := re.match(fr'({num_pat})(=)({num_pat})(x)(\+|-)({num_pat})', eq):
            y = num(terms.group(1))
            m = num(terms.group(3))
            operator = terms.group(5)
            b = num(terms.group(6))
            b = -1 * b if operator == '-' else b

            mx = y - b
            x = mx / m
            steps = (
                f'{equation}\n'+
                (
                    f'{m}{X} = {y} - {b}\n' if b > 0 else 
                    f'{m}{X} = {y} + {abs(b)}\n' if b < 0 else 
                    f'{m}{X} = {y}\n'
                ) +
                f'{X} = {mx} / {m}\n'+
                f'{X} = {x}'
            )
            return m, x, b, y, steps
        else:
            raise InvalidEquation('That is not a valid Equation!')

    @to_thread
    def linear_graph(self, m: Number, b: Number, x: Number, y: Number) -> BytesIO:
        """Plots a linear equation graph"""

        plt.style.use(["fast", "fivethirtyeight", "ggplot"])
        plt.style.use("bmh")
        buffer = BytesIO()
        
        lim = abs(x) * 3
        x_ = np.linspace(-lim, lim, 100)
        y_  = [(m * i + b) for i in x_]

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.spines['left'].set_position('center')
        ax.spines['bottom'].set_position('zero')
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')
        ax.xaxis.set_ticks_position('bottom')
        ax.yaxis.set_ticks_position('left')

        plt.plot(x,y, 'r')
        plt.plot(x_, y_)
        plt.plot(x, y, marker='o')
        plt.savefig(buffer)
        plt.close()

        buffer.seek(0)
        return buffer

class MathCog(commands.Cog):

    def __init__(self, bot: AquaBot) -> None:
        self.bot = bot

    @commands.command(name='linears')
    async def linear(self, ctx: AquaContext) -> discord.Message:
        
        embed = discord.Embed(
            title='Linear Equation Calculator', 
            description='Use the following buttons to input an equation in the format of: `y = mx + b`\nExample: `8 = 5x + 3`\nI will solve for `x`', 
            color=self.bot.color,
        )

        return await ctx.send(embed=embed, view=LinearUI(ctx, ctx.author, timeout=300))

def setup(bot: AquaBot) -> None:
    bot.add_cog(MathCog(bot))