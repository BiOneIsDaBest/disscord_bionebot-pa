import sqlite3
import discord
import re
from datetime import datetime
from datetime import timedelta
from discord.ext import commands
from typing import Union
import sys
from discord import Embed, Color
from pytz import timezone
from asyncio import sleep
from discord import Member
from discord import Role
from discord.ext.commands import Context

tz = timezone("Asia/Ho_Chi_Minh")

def format_timedelta(td: timedelta) -> str:
    """Formats a timedelta object into 'HHh MM phút' string."""
    total_seconds = td.total_seconds()
    # Use integer division for whole hours and minutes
    total_minutes_int = int(total_seconds // 60)
    total_hours_int = total_minutes_int // 60
    remaining_minutes_int = total_minutes_int % 60
    return f"{total_hours_int}h {remaining_minutes_int} phút"

def parse_to_timedelta(time_str: str) -> timedelta:
    if not isinstance(time_str, str):
        return timedelta()

    # Try format "Xh Y phút" (new output format)
    match_hm_new = re.match(r"(\d+)\s*h\s*(\d+)\s*phút", time_str, re.IGNORECASE)
    if match_hm_new:
        hours = int(match_hm_new.group(1))
        minutes = int(match_hm_new.group(2))
        return timedelta(hours=hours, minutes=minutes)
        
    # Try format "X.Yh/Z.Wm" (old output format)
    match_hm_old = re.match(r"(\d+(\.\d+)?)\s*h\s*/\s*(\d+(\.\d+)?)\s*m", time_str, re.IGNORECASE)
    if match_hm_old:
        hours = float(match_hm_old.group(1))
        minutes = float(match_hm_old.group(3))
        return timedelta(hours=hours, minutes=minutes)

    # Try format "X giờ, Y phút, Z giây" (database format)
    match_hms_vi = re.match(r"(\d+(\.\d+)?)\s*giờ\s*,\s*(\d+(\.\d+)?)\s*phút\s*,\s*(\d+(\.\d+)?)\s*giây", time_str, re.IGNORECASE)
    if match_hms_vi:
        hours = float(match_hms_vi.group(1))
        minutes = float(match_hms_vi.group(3))
        seconds = float(match_hms_vi.group(5))
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    return timedelta()

def add_time_strings(time_string1, time_string2):
    """Adds two time strings, handling multiple formats, and returns a formatted string 'HHh MM phút'."""
    td1 = parse_to_timedelta(time_string1)
    td2 = parse_to_timedelta(time_string2)
    total_timedelta = td1 + td2
    # Format the result using the helper function
    return format_timedelta(total_timedelta)

class Duty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect("data.sqlite",timeout=5)
        self.cursor = self.db.cursor()

    @commands.hybrid_command(description='Cập nhật biển số mới')
    async def update(self, ctx: Context, license: str):
        try:
            if len(ctx.message.attachments) == 0:
                await ctx.reply("Đồng chí cần gửi thêm ảnh minh chứng!")
                return
            
            self.cursor.execute("SELECT user_onduty FROM ONDUTY WHERE user_id = ?",(ctx.author.id,))
            if(self.cursor.fetchone() == None):
                pass
            else:
                self.cursor.execute("SELECT user_onduty FROM ONDUTY WHERE user_id = ?",(ctx.author.id,))
                if(self.cursor.fetchone()[0] == 0):
                    await ctx.reply("Bạn chưa bắt đầu phiên làm việc nào cả!")
                else:
                    em = Embed(title="✅ Cập nhật biển số thành công",description=f'**{ctx.author.display_name}** đã tiếp phiên làm việc ⌚ với xe 🚓 ┇ **{license}** ┇',color=Color.purple())
                    await ctx.reply(embed=em)
                    self.cursor.execute("UPDATE ONDUTY SET license = ? WHERE user_id = ?",(license,ctx.author.id))
                    self.db.commit()
                
        except Exception as e:
            print(e)
    
    @commands.hybrid_command(description="Bắt đầu phiên làm việc")
    async def onduty(self,ctx: Context,license: str):
        try:
            if len(ctx.message.attachments) == 0:
                await ctx.reply("Đồng chí cần gửi thêm ảnh minh chứng!")
                return
            
            self.cursor.execute("SELECT user_onduty FROM ONDUTY WHERE user_id = ?",(ctx.author.id,))
            if(self.cursor.fetchone() == None):
                self.cursor.execute("INSERT INTO ONDUTY VALUES(?,?,?,?)",(ctx.author.id,0,0,license))
                self.db.commit()
                em = Embed(title="✅ OnDuty thành công",description=f'**{ctx.author.display_name}** đã bắt đầu phiên làm việc ⌚ với xe 🚓 ┇ **{license}** ┇',color=Color.purple())
                await ctx.reply(embed=em)
                now = datetime.now(tz=tz)
                timestamp = datetime.timestamp(now)
                self.cursor.execute("UPDATE ONDUTY SET user_onduty = ? WHERE user_id = ?",(timestamp,ctx.author.id))
                self.db.commit()
            else:
                self.cursor.execute("SELECT user_onduty FROM ONDUTY WHERE user_id = ?",(ctx.author.id,))
                if(self.cursor.fetchone()[0] != 0):
                    await ctx.reply("Bạn đã bắt đầu phiên làm việc!")
                else:
                    em = Embed(title="✅ OnDuty thành công",description=f'**{ctx.author.display_name}** đã bắt đầu phiên làm việc ⌚ với xe 🚓 ┇ **{license}** ┇',color=Color.purple())
                    await ctx.reply(embed=em)
                    now = datetime.now(tz=tz)
                    timestamp = datetime.timestamp(now)
                    self.cursor.execute("UPDATE ONDUTY SET user_onduty = ?,license = ? WHERE user_id = ?",(timestamp,license,ctx.author.id))
                    self.db.commit()
        except Exception as e:
            print(e)

    @commands.hybrid_command(description="Kết thúc phiên làm việc")
    async def offduty(self,ctx):
        try:
            onduty = self.cursor.execute("SELECT user_onduty FROM ONDUTY WHERE user_id = ?",(ctx.author.id,)).fetchone()[0]
            license = self.cursor.execute("SELECT license FROM ONDUTY WHERE user_id = ?",(ctx.author.id,)).fetchone()[0]
            if(onduty != 0):
                now = datetime.now()

                diff = now - datetime.fromtimestamp(onduty)

                total_time = f"{round(diff.total_seconds() // 3600,3)} giờ, {round(diff.total_seconds() % 3600 // 60,2)} phút, {round(diff.total_seconds() % 60,2)} giây"
                self.cursor.execute("INSERT INTO OFFDUTY VALUES(?,?,?,?)",(ctx.author.id,datetime.timestamp(datetime.now(tz=tz)),total_time,license))
                self.cursor.execute("UPDATE ONDUTY SET user_onduty = ? WHERE user_id = ?",(0,ctx.author.id))
                self.db.commit()    

                
                em = Embed(title="✅ OffDuty thành công",description=f'{ctx.author.display_name} đã kết thúc phiên làm việc vào ⌚ {datetime.now(tz=tz).strftime("%d/%m/%Y, %H:%M:%S")}',color=Color.purple())
                em.add_field(name="Thời gian bắt đầu - kết thúc",value=f"{datetime.fromtimestamp(onduty,tz=tz).strftime('%d/%m/%Y, %H:%M:%S')} - {datetime.now(tz=tz).strftime('%d/%m/%Y, %H:%M:%S')}",inline=False)
                em.add_field(name="Phương tiện",value=f"xe 🚓 ┇ {license} ┇")
                em.add_field(name="Thời gian làm việc",value=f"{total_time}",inline=False) 
                await ctx.reply(embed=em)
            else:
                await ctx.reply("Bạn chưa bắt đầu phiên làm việc!")
        except Exception as e:
            print(e)
            print(sys.exc_info())

    @commands.has_role("Phòng Nhân Sự")
    @commands.hybrid_command(description="Kiểm tra thời gian làm việc")
    async def checktime(self,ctx,start:str,end:str=None,member: Union[Member, Role, None] = None):
        try:
            if(type(member) is None):
                start=start+" 0:0:0"
                datetime_object = datetime.strptime(start, "%d/%m/%Y %H:%M:%S")
                timestamp1 = datetime.timestamp(datetime_object)
                end=end+" 23:59:59"
                datetime_object = datetime.strptime(end, "%d/%m/%Y %H:%M:%S")
                timestamp2 = datetime.timestamp(datetime_object)
                des = ""
                stt = 0 # Initialize counter
                self.cursor.execute("SELECT day,user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(ctx.author.id,timestamp1,timestamp2))
                for _day,_total in self.cursor.fetchall():
                    stt += 1 # Increment counter
                    datetime_object = datetime.fromtimestamp(_day)
                    date_string = datetime_object.strftime("%d/%m/%Y")
                    # Parse and format the time from DB
                    db_time_str = _total if _total is not None else "0 giờ, 0 phút, 0 giây"
                    td = parse_to_timedelta(db_time_str)
                    formatted_total = format_timedelta(td)
                    des = des + f"{stt}. **{date_string}** đã làm việc `{formatted_total}`\n"

                week_total = "0 giờ 0 phút 0 giây"
                date_now = datetime.now(tz=tz)
                weekday = date_now.weekday()

                start_date = date_now - timedelta(days=weekday)
                end_date = start_date + timedelta(days=6)

                start_date = datetime.timestamp(start_date)
                end_date = datetime.timestamp(end_date)

                week_des = "0h 0m"

                self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(ctx.author.id,start_date,end_date))
                for _total in self.cursor.fetchall():
                    db_time_str = _total[0] if _total[0] is not None else "0 giờ, 0 phút, 0 giây"
                    week_des = add_time_strings(week_des, db_time_str)

                if(week_des == ""):
                    week_des = "⚠ Không tìm thấy dữ liệu"


                start_month = date_now.replace(day=1)
                next_month = start_month + timedelta(days=32)
                end_month = next_month.replace(day=1) - timedelta(days=1)
                
                start_month = datetime.timestamp(start_month)
                end_month = datetime.timestamp(end_month)

                month_des = "0h 0m"

                self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(ctx.author.id,start_month,end_month))
                for _total in self.cursor.fetchall():
                    db_time_str = _total[0] if _total[0] is not None else "0 giờ, 0 phút, 0 giây"
                    month_des = add_time_strings(month_des, db_time_str)


                em = Embed(title=f"📋 Thống kê thời gian làm việc của {ctx.author.display_name} (**PA**)",description=des,color=Color.purple())
                em.add_field(name="Thống kê tuần này",value=f"```{week_des}```",inline=False)
                em.add_field(name="Thống kê tháng này",value=f"```{month_des}```",inline=False)


                await ctx.reply(embed=em)
            if(type(member) is Member):
                start=start+" 0:0:0"
                datetime_object = datetime.strptime(start, "%d/%m/%Y %H:%M:%S")
                timestamp1 = datetime.timestamp(datetime_object)
                end=end+" 23:59:59"
                datetime_object = datetime.strptime(end, "%d/%m/%Y %H:%M:%S")
                timestamp2 = datetime.timestamp(datetime_object)
                des = ""
                stt = 0 # Initialize counter
                self.cursor.execute("SELECT day,user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(member.id,timestamp1,timestamp2))
                for _day,_total in self.cursor.fetchall():
                    stt += 1 # Increment counter
                    datetime_object = datetime.fromtimestamp(_day)
                    date_string = datetime_object.strftime("%d/%m/%Y")
                    # Parse and format the time from DB
                    db_time_str = _total if _total is not None else "0 giờ, 0 phút, 0 giây"
                    td = parse_to_timedelta(db_time_str)
                    formatted_total = format_timedelta(td)
                    des = des + f"{stt}. **{date_string}** đã làm việc `{formatted_total}`\n"

                week_total = "0 giờ 0 phút 0 giây"
                date_now = datetime.now(tz=tz)
                weekday = date_now.weekday()

                start_date = date_now - timedelta(days=weekday)
                end_date = start_date + timedelta(days=6)

                start_date = datetime.timestamp(start_date)
                end_date = datetime.timestamp(end_date)

                week_des = "0h 0m"

                self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(member.id,start_date,end_date))
                for _total in self.cursor.fetchall():
                    db_time_str = _total[0] if _total[0] is not None else "0 giờ, 0 phút, 0 giây"
                    week_des = add_time_strings(week_des, db_time_str)

                if(week_des == ""):
                    week_des = "⚠ Không tìm thấy dữ liệu"


                start_month = date_now.replace(day=1)
                next_month = start_month + timedelta(days=32)
                end_month = next_month.replace(day=1) - timedelta(days=1)
                
                start_month = datetime.timestamp(start_month)
                end_month = datetime.timestamp(end_month)

                month_des = "0h 0m"

                self.cursor.execute("SELECT user_total FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day <= ?",(member.id,start_month,end_month))
                for _total in self.cursor.fetchall():   
                    db_time_str = _total[0] if _total[0] is not None else "0 giờ, 0 phút, 0 giây"
                    month_des = add_time_strings(month_des, db_time_str)


                em = Embed(title=f"📋 Thống kê thời gian làm việc của {member.display_name} (**PA**)",description=des,color=Color.purple())
                em.add_field(name="Thống kê tuần này",value=f"```{week_des}```",inline=False)
                em.add_field(name="Thống kê tháng này",value=f"```{month_des}```",inline=False)

                await ctx.reply(embed=em)
                
            if(type(member) is Role):
                user_ids = []
                des = ""
                for member_servers in ctx.guild.members:
                    if member in member_servers.roles:
                        user_ids.append(member_servers.id)
                start=start+" 0:0:0"
                datetime_object = datetime.strptime(start, "%d/%m/%Y %H:%M:%S")
                timestamp1 = datetime.timestamp(datetime_object)
                end=end+" 23:59:59"
                datetime_object = datetime.strptime(end, "%d/%m/%Y %H:%M:%S")
                timestamp2 = datetime.timestamp(datetime_object)
                placeholders = ', '.join(['?'] * len(user_ids))
                query = f"SELECT user_id, user_total FROM OFFDUTY WHERE user_id IN ({placeholders}) AND day >= ?"
                params = (*user_ids, timestamp1)
                user_sum = {}
                self.cursor.execute(query, params)
                for _user_id,_total in self.cursor.fetchall():
                    db_time_str = _total if _total is not None else "0 giờ, 0 phút, 0 giây"
                    current_sum = user_sum.get(_user_id, "0h 0m")
                    user_sum[_user_id] = add_time_strings(current_sum, db_time_str)

                stt = 0 # Initialize counter
                for _user_id,_total in list(user_sum.items()):
                    stt += 1 # Increment counter
                    # Parse and format the time from DB
                    db_time_str = _total if _total is not None else "0 giờ, 0 phút, 0 giây"
                    td = parse_to_timedelta(db_time_str)
                    formatted_total = format_timedelta(td)
                    des = des + f"{stt}. *<@{_user_id}>* đã làm việc `{formatted_total}`\n"
                    
                if(des == ""):
                    des = "⚠ Không tìm thấy dữ liệu"

                em = Embed(title=f"📋 Thống kê thời gian làm việc của mọi thành viên thuộc {member.name}",description=des,color=Color.purple())
                await ctx.reply(embed=em)
        except Exception as e:
            print(e)

    @commands.has_role("Phòng Nhân Sự")
    @commands.hybrid_command()
    async def checkduty(self,ctx):
        try:
            des = ""
            user_check = []
            for user in ctx.guild.members:
                user_check.append(user.id)
    
            self.cursor.execute("SELECT user_id,user_onduty,license FROM ONDUTY WHERE user_onduty != 0")
            for _user,_time,_license in self.cursor.fetchall():
                if _user in user_check:
                    des += f"<@{_user}> đang làm việc bắt đầu từ {datetime.fromtimestamp(_time)} - {_license}\n"
    
            em = Embed(title="Danh sách sĩ quan đang thực hiện nhiệm vụ",description=des)
            await ctx.reply(embed=em)
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Duty(bot))

