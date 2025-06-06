import sqlite3
from discord.ext import commands
from datetime import datetime, timedelta
from discord import Embed, Color
import discord

class SubTime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data.sqlite", timeout=5)
        self.cursor = self.db.cursor()
        self.log_channel_id = 1378056650799186022

    def seconds_to_string(self, seconds: int) -> str:
        td = timedelta(seconds=seconds)
        return f"{round(td.total_seconds() // 3600, 2)} giờ, {round((td.total_seconds() % 3600) // 60, 2)} phút, {round(td.total_seconds() % 60, 2)} giây"

    def day_to_timestamp(self, date_str: str) -> float:
        dt_obj = datetime.strptime(date_str + " 12:00:00", "%d/%m/%Y %H:%M:%S")
        return datetime.timestamp(dt_obj)

    @commands.has_role("Phòng Nhân Sự")
    @commands.hybrid_command(description="Thêm thời gian làm việc thủ công")
    async def addtime(self, ctx, seconds: int, date: str, member: discord.Member):
        try:
            time_str = self.seconds_to_string(seconds)
            timestamp = self.day_to_timestamp(date)

            self.cursor.execute(
                "INSERT INTO OFFDUTY (user_id, day, user_total, license) VALUES (?, ?, ?, ?)",
                (member.id, timestamp, time_str, "MANUAL_ADD")
            )
            self.db.commit()

            em = Embed(title="✅ Thêm thời gian thành công",
                       description=f"👤 {member.mention} đã được thêm `{time_str}` vào ngày `{date}`",
                       color=Color.green())
            await ctx.reply(embed=em)

            # gửi log
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                await log_channel.send(content=f"{ctx.author.mention}, đã cập nhật thời gian cho nhân viên:", embed=em)

        except Exception as e:
            await ctx.reply(f"❌ Lỗi: {e}")

    @commands.has_role("Phòng Nhân Sự")
    @commands.hybrid_command(description="Xóa thời gian làm việc thủ công")
    async def removetime(self, ctx, seconds: int, date: str, member: discord.Member):
        try:
            start_ts = datetime.strptime(date + " 00:00:00", "%d/%m/%Y %H:%M:%S").timestamp()
            end_ts = datetime.strptime(date + " 23:59:59", "%d/%m/%Y %H:%M:%S").timestamp()

            self.cursor.execute(
                "SELECT rowid, user_total FROM OFFDUTY WHERE user_id = ? AND day BETWEEN ? AND ?",
                (member.id, start_ts, end_ts))
            rows = self.cursor.fetchall()

            if not rows:
                await ctx.reply("❌ Không tìm thấy bản ghi thời gian nào để xóa.")
                return

            # Tổng thời gian trong ngày
            total_seconds = 0
            for _, time_str in rows:
                h, m, s = [float(part.split()[0]) for part in time_str.split(",")]
                total_seconds += int(h * 3600 + m * 60 + s)

            # Trừ thời gian
            new_total = max(0, total_seconds - seconds)
            new_time_str = self.seconds_to_string(new_total)
            removed_str = self.seconds_to_string(min(total_seconds, seconds))

            if new_total == 0:
                # Xoá tất cả bản ghi
                for rowid, _ in rows:
                    self.cursor.execute("DELETE FROM OFFDUTY WHERE rowid = ?", (rowid,))
                action = "❌ Đã xoá toàn bộ thời gian trong ngày"
            else:
                # Xóa các bản ghi trừ cái cuối cùng
                for rowid, _ in rows[:-1]:
                    self.cursor.execute("DELETE FROM OFFDUTY WHERE rowid = ?", (rowid,))    
                # Cập nhật bản ghi cuối với thời gian còn lại
                last_rowid = rows[-1][0]
                self.cursor.execute("UPDATE OFFDUTY SET user_total = ? WHERE rowid = ?", (new_time_str, last_rowid))
                action = f"✅ Đã cập nhật còn lại `{new_time_str}`"

            self.db.commit()
            em = Embed(title="🧮 Xử lý giảm thời gian",
                    description=f"{action} cho 👤 {member.mention} vào ngày `{date}`\nĐã trừ: `{removed_str}`",
                    color=Color.red())
            await ctx.reply(embed=em)

            # gửi log
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                await log_channel.send(content=f"{ctx.author.mention}, đã cập nhật thời gian cho nhân viên:", embed=em)

        except Exception as e:
            await ctx.reply(f"❌ Lỗi: {e}")

async def setup(bot):
    await bot.add_cog(SubTime(bot))
