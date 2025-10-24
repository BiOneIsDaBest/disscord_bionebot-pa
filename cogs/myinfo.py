import sqlite3
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Embed, Color
from pytz import timezone

tz = timezone("Asia/Ho_Chi_Minh")

def parse_to_timedelta(time_str: str) -> timedelta:
    import re
    if not isinstance(time_str, str):
        return timedelta()

    match_hm_new = re.match(r"(\d+)\s*h\s*(\d+)\s*phút", time_str, re.IGNORECASE)
    if match_hm_new:
        return timedelta(hours=int(match_hm_new.group(1)), minutes=int(match_hm_new.group(2)))

    match_hms_vi = re.match(r"(\d+(\.\d+)?)\s*giờ\s*,\s*(\d+(\.\d+)?)\s*phút\s*,\s*(\d+(\.\d+)?)\s*giây", time_str, re.IGNORECASE)
    if match_hms_vi:
        return timedelta(hours=float(match_hms_vi.group(1)), minutes=float(match_hms_vi.group(3)), seconds=float(match_hms_vi.group(5)))

    return timedelta()

def format_timedelta(td: timedelta) -> str:
    total_seconds = td.total_seconds()
    total_minutes = int(total_seconds // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}h {minutes} phút"

def add_time_strings(t1: str, t2: str) -> str:
    td1 = parse_to_timedelta(t1)
    td2 = parse_to_timedelta(t2)
    return format_timedelta(td1 + td2)

class MyInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data.sqlite", timeout=5)
        self.cursor = self.db.cursor()

    @commands.hybrid_command(description="Kiểm tra thời gian làm việc (chỉ của bạn)")
    async def myinfo(self, ctx, start: str = None, end: str = None):
        try:
            member = ctx.author

            # Lấy thời gian tuần và tháng
            now = datetime.now(tz=tz)
            weekday = now.weekday()
            start_week = datetime.timestamp(now - timedelta(days=weekday))
            end_week = datetime.timestamp(now + timedelta(days=6 - weekday))

            start_month = now.replace(day=1)
            next_month = start_month + timedelta(days=32)
            end_month = next_month.replace(day=1) - timedelta(days=1)
            start_month_ts = datetime.timestamp(start_month)
            end_month_ts = datetime.timestamp(end_month)

            # Tính tổng tuần
            week_total = "0h 0 phút"
            self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day BETWEEN ? AND ?", (member.id, start_week, end_week))
            for (total,) in self.cursor.fetchall():
                week_total = add_time_strings(week_total, total or "0 giờ, 0 phút, 0 giây")

            # Tính tổng tháng
            month_total = "0h 0 phút"
            self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day BETWEEN ? AND ?", (member.id, start_month_ts, end_month_ts))
            for (total,) in self.cursor.fetchall():
                month_total = add_time_strings(month_total, total or "0 giờ, 0 phút, 0 giây")

            # Thống kê chi tiết nếu có start & end
            des = ""
            if start and end:
                start += " 0:0:0"
                end += " 23:59:59"
                timestamp1 = datetime.timestamp(datetime.strptime(start, "%d/%m/%Y %H:%M:%S"))
                timestamp2 = datetime.timestamp(datetime.strptime(end, "%d/%m/%Y %H:%M:%S"))

                self.cursor.execute(
                    "SELECT day, user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",
                    (member.id, timestamp1, timestamp2)
                )
                for _day, _total in self.cursor.fetchall():
                    date_string = datetime.fromtimestamp(_day).strftime("%d/%m/%Y")
                    td = parse_to_timedelta(_total or "0 giờ, 0 phút, 0 giây")
                    formatted_total = format_timedelta(td)
                    des += f"*{date_string}* đã làm việc **{formatted_total}**\n"

                if not des:
                    des = "⚠ Không tìm thấy dữ liệu"
            else:
                des = None  # Không có phần chi tiết ngày

            # Xác định bộ phận
            roles_to_check = ["Phòng Giáo Dục & Đào Tạo", "Phòng Nhân Sự", "Phòng An Ninh"]
            roles_found = [role.name for role in member.roles if role.name in roles_to_check]
            department = ", ".join(roles_found) if roles_found else "Chưa được phân bố"

            # Thông tin thời gian vào
            joined_timestamp = int(member.joined_at.timestamp())
            joined_date = member.joined_at.strftime("%d/%m/%Y")
            days_since_join = (now - member.joined_at.replace(tzinfo=tz)).days

            # Embed
            em = Embed(
                title=f"📋 Thống kê thời gian làm việc của {member.display_name}",
                color=Color.purple()
            )
            em.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            em.add_field(name="👤 Tên người dùng", value=f"{member} ({member.id})", inline=False)
            em.add_field(name="🏢 Bộ phận", value=department, inline=False)
            em.add_field(name="📅 Tham gia server", value=f"{joined_date} (<t:{joined_timestamp}:R> — {days_since_join} ngày)", inline=False)
            em.add_field(name="📊 Thống kê tuần này", value=f"```{week_total}```", inline=False)
            em.add_field(name="📈 Thống kê tháng này", value=f"```{month_total}```", inline=False)

            if des:
                em.add_field(name="🗓️ Chi tiết từ ngày", value=des, inline=False)

            await ctx.reply(embed=em)

        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(MyInfo(bot))
