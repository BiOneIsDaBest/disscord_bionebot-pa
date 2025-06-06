import sqlite3
import traceback
from discord.ext import commands
from discord import Embed, ButtonStyle, Interaction
from discord.ui import View, button, Button, Modal, TextInput
from datetime import datetime, timedelta

GDDT_ROLE_ID = 1087276659327119367  # ID role Phòng Giáo Dục & Đào Tạo

class RoleSelectView(View):
    def __init__(self, bot, role: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.role = role

    @button(label="Phòng GD & ĐT", style=ButtonStyle.primary, custom_id="gd_dt")
    async def gd_dt(self, interaction: Interaction, button: Button):
        if not any(r.id == GDDT_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Bạn không có quyền thuộc Phòng GD & ĐT.", ephemeral=True)
            return
        await self.record_teach(interaction, self.role, "Phòng GD & ĐT")

    @button(label="Phòng Ban Khác", style=ButtonStyle.primary, custom_id="other")
    async def other(self, interaction: Interaction, button: Button):
        await self.record_teach(interaction, self.role, "Phòng Ban Khác")

    async def record_teach(self, interaction: Interaction, role: str, department: str):
        conn = sqlite3.connect("data.sqlite")
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TEACHLOG (
                user_id INTEGER,
                timestamp REAL,
                role TEXT,
                department TEXT,
                tiet INTEGER
            )
        """)
        cursor.execute("INSERT INTO TEACHLOG VALUES (?, ?, ?, ?, ?)",
                       (interaction.user.id, now.timestamp(), role, department, 1))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Bắt đầu ghi nhận **1 tiết** dạy cho **{role} - {department}**.", ephemeral=True)

class TeachView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Giảng Viên", style=ButtonStyle.secondary, custom_id="giang_vien")
    async def giang_vien(self, interaction: Interaction, button: Button):
        await interaction.response.send_message(view=RoleSelectView(self.bot, "Giảng Viên"), ephemeral=True)

    @button(label="Trợ Giảng", style=ButtonStyle.secondary, custom_id="tro_giang")
    async def tro_giang(self, interaction: Interaction, button: Button):
        await interaction.response.send_message(view=RoleSelectView(self.bot, "Trợ Giảng"), ephemeral=True)

    @button(label="📊 Tracking lịch sử", style=ButtonStyle.success, custom_id="tracking")
    async def tracking(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(TrackModal(self.bot))

class TrackModal(Modal, title="Tracking số tiết dạy học"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.start_date = TextInput(label="Từ ngày (dd/mm/yyyy)", required=True)
        self.end_date = TextInput(label="Đến ngày (dd/mm/yyyy)", required=True)
        self.add_item(self.start_date)
        self.add_item(self.end_date)

    async def on_submit(self, interaction: Interaction):
        try:
            print("[DEBUG] on_submit triggered")
            start = datetime.strptime(self.start_date.value, "%d/%m/%Y")
            end = datetime.strptime(self.end_date.value + " 23:59:59", "%d/%m/%Y %H:%M:%S")

            conn = sqlite3.connect("data.sqlite")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, role, department, COUNT(*) FROM TEACHLOG
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY user_id, role, department
            """, (start.timestamp(), end.timestamp()))

            data = {}
            for user_id, role, dept, count in cursor.fetchall():
                if user_id not in data:
                    data[user_id] = {
                        "Phòng GD & ĐT": {"Giảng Viên": 0, "Trợ Giảng": 0},
                        "Phòng Ban Khác": {"Giảng Viên": 0, "Trợ Giảng": 0}
                    }
                if dept not in data[user_id]:
                    data[user_id][dept] = {"Giảng Viên": 0, "Trợ Giảng": 0}
                data[user_id][dept][role] = count

            conn.close()

            description = f"📆 Từ `{self.start_date.value}` đến `{self.end_date.value}`\n\n"
            for uid, by_dept in data.items():
                member = interaction.guild.get_member(uid)
                member_name = f"**{member.display_name}** - `{uid}`" if member else f"**(Unknown)** - `{uid}`"
                total_salary = 0
                desc = f"> 🧑‍🏫 {member_name}\n"
                for dept in ["Phòng GD & ĐT", "Phòng Ban Khác"]:
                    gv = by_dept.get(dept, {}).get("Giảng Viên", 0)
                    tg = by_dept.get(dept, {}).get("Trợ Giảng", 0)
                    if gv == 0 and tg == 0:
                        continue
                    if dept == "Phòng GD & ĐT":
                        salary = gv * 100000 + tg * 50000
                    else:
                        salary = gv * 70000 + tg * 30000
                    total_salary += salary
                    desc += f"{gv} tiết **giảng viên**, {tg} tiết **trợ giảng** tại **{dept}**\n"
                desc += f"<a:money_bioneshop:1145256811176407070> Tổng lương: `{total_salary:,}$`\n\n"
                description += desc

            em = Embed(title="📊 Báo cáo lịch sử dạy học", description=description, color=0x00FFCC)
            await interaction.response.send_message(embed=em, ephemeral=True)

        except Exception as e:
            print(f"[TRACKING ERROR] {e}")
            traceback.print_exc()
            await interaction.response.send_message("❌ Đã xảy ra lỗi. Vui lòng thử lại sau.", ephemeral=True)

class TeachEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="teachpanel")
    async def send_teach_panel(self, ctx):
        em = Embed(
            title="📋 Chấm công Giáo Dục",
            description="Vui lòng chọn vai trò giảng dạy phù hợp.",
            color=0x9900FF
        )
        em.add_field(name="Chọn vai trò", value="➤ Giảng Viên\n➤ Trợ Giảng", inline=False)
        em.add_field(name="Tracking", value="➤ Xem lịch sử tiết dạy", inline=False)
        em.set_footer(text="BiOneIsDaBest/BiOneBot • Hệ Thống Chấm Công Tự Động")
        await ctx.send(embed=em, view=TeachView(self.bot))

async def setup(bot):
    await bot.add_cog(TeachEmbed(bot))
