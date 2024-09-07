import discord
from discord.ext import commands
import asyncio
import re

import matplotlib
matplotlib.use("agg")

from matplotlib import pyplot as plt
import numpy as np

from io import BytesIO
from Equation import Expression

from ..utils import to_thread

@to_thread
def data_check(data):
    data = [a.isdigit() for a in data]
    return all(data)

@to_thread
def bar(*args):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    buffer = BytesIO()
    args1 = [int(i) for i in args]
    plt.bar(args, args1)
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def pie(*args):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("Solarize_Light2")
    buffer = BytesIO()
    args1 = [int(i) for i in args]
    plt.pie(args1, labels=args, autopct = '%1.1f%%', shadow = True)
    plt.savefig(buffer, transparent=True)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def scatter(*args):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")
    buffer = BytesIO()
    args1 = [int(i) for i in args]
    plt.scatter(args, args1, color='r')
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def line(*args):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")
    buffer = BytesIO()

    x_ = args
    y = [int(i) for i in args]

    plt.plot(x_, y, 'o-g')
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def linear(m: float, b: float):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")

    plt.xlim((-40, 40))
    plt.ylim((-40, 40))
    buffer = BytesIO()

    x_ = np.linspace(-100, 100, 50000)
    y  = [(m * i + b) for i in x_]

    plt.plot(x_, y)
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def quadratic(a: float, b: float, c: float):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")

    plt.xlim((-40, 40))
    plt.ylim((-40, 40))
    buffer = BytesIO()

    x_ = np.linspace(-100, 100, 50000)
    y  = [(a * (i**2) + (b * i) + c) for i in x_]

    plt.plot(x_, y)
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def equation_(equation: str):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")

    def _mul(val):
        val = list(val.group())
        val.insert(-1, "*")
        return "".join(val)

    equation = equation.replace(' ', '')
    equation = re.sub(r"(?<=[0-9x)])x", _mul, equation)
    equation = equation.replace(")(", ")*(")

    x = np.linspace(-100, 100, 50000)

    fn = Expression(equation, ["x"])
    y = [fn(i) for i in x]

    plt.xlim((-40, 40))
    plt.ylim((-40, 40))
    buffer = BytesIO()

    plt.plot(x, y)
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

@to_thread
def exponent(*args):
    plt.style.use(["fast", "fivethirtyeight", "ggplot"])
    plt.style.use("bmh")
    buffer = BytesIO()
    x = np.array([int(i) for i in args])
    y = np.exp(x)
    plt.plot(x, y)
    plt.savefig(buffer)
    plt.close()
    buffer.seek(0)
    image = discord.File(buffer, "graph.png")
    return image

class Graphing(commands.Cog):

    def __init__(self, bot):
        self._cog_name = "Graphing commands ..."
        self.bot    = bot
        self.loop   = asyncio.get_running_loop()

    @commands.command(name="bar")
    async def bar(self, ctx, *args):
        if not data_check(args):
            return await ctx.send("data points must be numerical values!")

        image = await bar(*args)
        return await ctx.send(file=image)

    @commands.command(name="pie")
    async def pie(self, ctx, *args):
        if not data_check(args):
            return await ctx.send("data points must be numerical values!")

        image = await pie(*args)
        return await ctx.send(file=image)

    @commands.command(name="scatterplot")
    async def scatterplot(self, ctx, *args):
        if not data_check(args):
            return await ctx.send("data points must be numerical values!")

        image = await scatter(*args)
        return await ctx.send(file=image)

    @commands.command(name="linegraph", aliases=["line"])
    async def linegraph(self, ctx, *args):
        if not data_check(args):
            return await ctx.send("data points must be numerical values!")

        image = await line(*args)
        return await ctx.send(file=image)

    @commands.command(name="quadratic",  aliases=["quad"])
    async def quadratic(self, ctx, a: float, b: float, c: float):
        image = await quadratic(a, b, c)
        return await ctx.send(file=image)

    @commands.command(name="linear")
    async def linear(self, ctx, m: float, b: float):
        image = await linear(m, b)
        return await ctx.send(file=image)

    @commands.command(name="equation", aliases=["eq", "graph"])
    async def equation(self, ctx, equation: str):
        try:
            image = await equation_(equation)
            return await ctx.send(file=image)
        except TypeError:
            return await ctx.send("Invalid equation\nMake sure the only variable present is `x`!")

    @commands.command(name="exponential", aliases=["exp"])
    async def exponential(self, ctx, *args):
        if not data_check(args):
            return await ctx.send("data points must be numerical values!")

        image = await exponent(*args)
        return await ctx.send(file=image)

def setup(client):
    client.add_cog(Graphing(client))