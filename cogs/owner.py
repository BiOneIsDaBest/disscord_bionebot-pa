from discord.ext import commands

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def sync(self,ctx):
        try:
            if(ctx.author.id == 895604726454968320 or ctx.author.id == 1146990393167200276 or ctx.author.id == 1041226459689267211): 
                await self.bot.tree.sync()
                await ctx.reply("Synced!")
            else:
                await ctx.reply("You are not allowed to use this command!")
        except Exception as e:
            await ctx.reply(f"Error: {e}")
        
async def setup(bot):
    await bot.add_cog(Owner(bot))