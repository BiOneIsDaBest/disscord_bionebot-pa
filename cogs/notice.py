import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from pytz import timezone
import sqlite3

tz = timezone("Asia/Ho_Chi_Minh")

class Notice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data.sqlite", timeout=5)
        self.cursor = self.db.cursor()
        self.first_notice.start()
        self.second_notice.start()
        self.check_overtime.start()
        self.log_channel_id = 1378078238646997123 # noitice_log
        self.overtime_channel_id = 1378078238646997123 # 4h remind log
        self.overtime_notified = {}  # Đếm số lần nhắc theo user_id

    @tasks.loop(minutes=1)
    async def first_notice(self):
        now = datetime.now(tz).time()
        if now.hour == 23 and now.minute == 0:
            await self.notify_onduty_users(
                "**[NHẮC NHỞ OFFDUTY]**\nVui lòng kết thúc ca làm trước **23:58 hôm nay**.\nNếu không bạn sẽ **bị trừ hết ngày công** nếu vẫn còn ONDUTY sau **00:00**.")

    @tasks.loop(minutes=1)
    async def second_notice(self):
        now = datetime.now(tz).time()
        if now.hour == 23 and now.minute == 45:
            await self.notify_onduty_users(
                "**[NHẮC NHỞ OFFDUTY]**\nVui lòng kết thúc ca làm trước **23:58 hôm nay**.\nNếu bạn vẫn còn ONDUTY, hãy nghỉ ngơi **10–15 phút** rồi bắt đầu lại vào **sau 00:03** để tính công cho ngày mới.")

    @tasks.loop(minutes=10)
    async def check_overtime(self):
        now = datetime.now(tz)
        try:
            self.cursor.execute("SELECT user_id, user_onduty FROM ONDUTY WHERE user_onduty != 0")
            results = self.cursor.fetchall()
            overtime_channel = self.bot.get_channel(self.overtime_channel_id)

            for user_id, start_ts in results:
                start_time = datetime.fromtimestamp(start_ts, tz=tz)
                duration = now - start_time
                if duration >= timedelta(hours=4):
                    # Đếm số lần nhắc
                    count = self.overtime_notified.get(user_id, 0)
                    if count < 2:
                        self.overtime_notified[user_id] = count + 1
                        for guild in self.bot.guilds:
                            member = guild.get_member(user_id)
                            if member:
                                msg = f"🔔 {member.mention} Bạn đã đạt chỉ tiêu trong ngày, nếu muốn tiếp tục hãy thử sức với công việc khác nhé!"
                                if overtime_channel:
                                    await overtime_channel.send(msg)
        except Exception as e:
            print(f"[Overtime Check Error] {e}")

    async def notify_onduty_users(self, message_text):
        embed = discord.Embed(
            title="📣 Thông báo nhắc nhở ONDUTY",
            description=message_text,
            color=discord.Color.orange()
        )
        embed.set_footer(text="BiOneIsDaBest/BiOneBot • Hệ Thông Chấm Công Tự Động")
        embed.timestamp = datetime.now(tz)

        log_channel = self.bot.get_channel(self.log_channel_id)

        try:
            self.cursor.execute("SELECT user_id FROM ONDUTY WHERE user_onduty != 0")
            users = [row[0] for row in self.cursor.fetchall()]

            for guild in self.bot.guilds:
                for user_id in users:
                    member = guild.get_member(user_id)
                    if member and not member.bot:
                        try:
                            await member.send(embed=embed)
                            if log_channel:
                                await log_channel.send(f"📤 Đã gửi nhắc nhở tới {member.mention}")
                        except Exception as e:
                            if log_channel:
                                await log_channel.send(f"⚠ Không thể gửi DM cho {member.mention} — Lỗi: `{str(e)}`")
        except Exception as e:
            print(f"[Notice Error] {e}")

    @first_notice.before_loop
    @second_notice.before_loop
    @check_overtime.before_loop
    async def before_start(self):
        await self.bot.wait_until_ready()

    @commands.command(name="test_notice")
    async def test_notice(self, ctx):
        """Gửi thử thông báo đến người đang ONDUTY"""
        await self.notify_onduty_users(
            "**[THỬ NGHIỆM THÔNG BÁO]**\nĐây là tin nhắn test dành cho những người đang ONDUTY.")
        await ctx.reply("✅ Đã gửi thử thông báo đến các user đang ONDUTY.")

async def setup(bot):
    await bot.add_cog(Notice(bot))