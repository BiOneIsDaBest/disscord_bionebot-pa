import sqlite3
import traceback
import csv
import os
from discord.ext import commands
from discord import Embed, ButtonStyle, Interaction, File
from discord.ui import View, button, Button, Modal, TextInput
from datetime import datetime, timedelta

GDDT_ROLE_ID = 1087276659327119367  # ID role Phòng Giáo Dục & Đào Tạo

class ExportButtonView(View):
    def __init__(self, filename, start_date_str):
        super().__init__(timeout=300)
        self.filename = filename
        self.start_date_str = start_date_str

    @button(label="🛠 Điều chỉnh", style=ButtonStyle.secondary)
    async def edit_teaching(self, interaction: Interaction, button: Button):
        if not any(r.id == 1087276659327119368 for r in interaction.user.roles):
            await interaction.response.send_message("❌ Bạn không có quyền sử dụng tính năng điều chỉnh này.", ephemeral=True)
            return
        await interaction.response.send_modal(AdjustTeachModal(self.start_date_str))

    @button(label="📥 Tải file Excel", style=ButtonStyle.primary)
    async def export_csv(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.send_message("📁 Dưới đây là file Excel của bạn:", file=File(self.filename), ephemeral=True)

            # gửi log tới kênh LOG TIME GD
            log_channel = interaction.guild.get_channel(1378078053929844908)
            if log_channel:
                await log_channel.send(
                    f"📤 {interaction.user.mention} đã trích xuất bảng time từ ngày **{self.filename[12:22].replace('-', '/')}** đến **{self.filename[24:34].replace('-', '/')}**",
                    file=File(self.filename)
                )
            os.remove(self.filename)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi gửi file: {e}", ephemeral=True)

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

        log_channel = interaction.guild.get_channel(1380979632777465986)
        if log_channel:
            await log_channel.send(f"📚 {interaction.user.mention} đã bắt đầu tiết học với vai trò: **{role}** ( **{department}** ).")



class TeachView(View):
    
    async def dot_menu(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(DeleteModal(self.bot))
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

class DeleteModal(Modal, title="🗑 Điều chỉnh tiết học theo thời gian"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.start_date = TextInput(label="Từ ngày (dd/mm/yyyy)", required=True)
        self.end_date = TextInput(label="Đến ngày (dd/mm/yyyy)", required=True)
        self.add_item(self.start_date)
        self.add_item(self.end_date)

    async def on_submit(self, interaction: Interaction):
        # Kiểm tra quyền hạn role Trưởng Phòng
        if not any(r.id == 1087276659327119368 for r in interaction.user.roles):
            await interaction.response.send_message("❌ Bạn không có quyền sử dụng tính năng điều chỉnh này.", ephemeral=True)
            return
        # Kiểm tra quyền hạn role Trưởng Phòng
        if not any(r.id == 1087276659327119368 for r in interaction.user.roles):
            await interaction.response.send_message("❌ Bạn không có quyền sử dụng tính năng điều chỉnh này.", ephemeral=True)
            return
        try:
            start = datetime.strptime(self.start_date.value, "%d/%m/%Y")
            end = datetime.strptime(self.end_date.value + " 23:59:59", "%d/%m/%Y %H:%M:%S")

            conn = sqlite3.connect("data.sqlite")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, role, department, COUNT(*) FROM TEACHLOG
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY user_id, role, department
            """, (start.timestamp(), end.timestamp()))

            entries = cursor.fetchall()
            if not entries:
                await interaction.response.send_message("⚠️ Không có dữ liệu trong khoảng thời gian.", ephemeral=True)
                return

            display_list = []
            user_map = {}
            for i, (user_id, role, dept, count) in enumerate(entries, 1):
                key = (user_id, dept)
                if key not in user_map:
                    user_map[key] = {"Giảng Viên": 0, "Trợ Giảng": 0}
                user_map[key][role] = count

            message = f"📆 Dữ liệu từ `{self.start_date.value}` đến `{self.end_date.value}`"
            numbered = []
            index = 1
            for (user_id, dept), roles in user_map.items():
                member = interaction.guild.get_member(user_id)
                name = member.mention if member else f"(Unknown {user_id})"
                gv = roles.get("Giảng Viên", 0)
                tg = roles.get("Trợ Giảng", 0)
                message += f"{index}. {name} - {gv} tiết giảng viên, {tg} tiết trợ giảng tại {dept}"
                numbered.append((index, user_id, dept, gv, tg))
                index += 1

            message += "👉 Hãy chọn số thứ tự bên dưới để điều chỉnh."

            # tạo view chọn người xoá
            class SelectUserToDelete(Modal, title="Chọn người và số tiết cần xoá"):
                def __init__(self, bot):
                    super().__init__()
                    self.bot = bot
                    self.stt = TextInput(label="Số thứ tự người cần xoá", required=True)
                    self.role = TextInput(label="Vai trò cần xoá (Giảng Viên / Trợ Giảng)", required=True)
                    self.sotiethoc = TextInput(label="Số tiết cần xoá", required=True)
                    self.start = start
                    self.end = end
                    self.entries = numbered
                    self.add_item(self.stt)
                    self.add_item(self.sotiethoc)

                async def on_submit(self, interaction: Interaction):
                    try:
                        stt = int(self.stt.value.strip())
                        amount = int(self.sotiethoc.value.strip())
                        entry = next((e for e in self.entries if e[0] == stt), None)
                        role = self.role.value.strip().title()
                        if role not in ["Giảng Viên", "Trợ Giảng"]:
                            await interaction.response.send_message("❌ Vai trò không hợp lệ. Vui lòng nhập Giảng Viên hoặc Trợ Giảng.", ephemeral=True)
                            return
                        if not entry:
                            await interaction.response.send_message("❌ Không tìm thấy người phù hợp.", ephemeral=True)
                            return

                        user_id, dept, _, _ = entry[1:]

                        conn = sqlite3.connect("data.sqlite")
                        cursor = conn.cursor()
                        cursor.execute("""
                            DELETE FROM TEACHLOG
                            WHERE rowid IN (
                                SELECT rowid FROM TEACHLOG
                                WHERE user_id = ? AND department = ? AND role = ? AND timestamp BETWEEN ? AND ?
                                ORDER BY timestamp DESC
                                LIMIT ?
                            )
                        """, (user_id, dept, self.start.timestamp(), self.end.timestamp(), role, amount))
                        conn.commit()
                        conn.close()

                        await interaction.response.send_message(f"✅ Đã xoá `{amount}` tiết **{role}** của <@{user_id}> tại **{dept}**.", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"❌ Lỗi khi xoá: {e}", ephemeral=True)

            await interaction.followup.send("⬇️ Nhập STT và số tiết cần xoá:", ephemeral=True)
            await interaction.followup.send_modal(SelectUserToDelete(self.bot))
            await interaction.response.send_message(message, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

class AdjustTeachModal(Modal, title="🛠 Điều chỉnh tiết học"):
    def __init__(self, start_date_str):
        super().__init__()
        self.start_date_str = start_date_str
        self.user_id = TextInput(label="ID người dùng", required=True)
        self.role = TextInput(label="Vai trò (Giảng Viên / Trợ Giảng)", required=True)
        self.tiet_moi = TextInput(label="Số tiết muốn đặt lại", required=True)
        self.add_item(self.user_id)
        self.add_item(self.role)
        self.add_item(self.tiet_moi)

    async def on_submit(self, interaction: Interaction):
        try:
            uid = int(self.user_id.value.strip())
            role = self.role.value.strip().title()
            new_count = int(self.tiet_moi.value.strip())

            if role not in ["Giảng Viên", "Trợ Giảng"]:
                await interaction.response.send_message("❌ Vai trò không hợp lệ. Nhập Giảng Viên hoặc Trợ Giảng.", ephemeral=True)
                return

            conn = sqlite3.connect("data.sqlite")
            cursor = conn.cursor()

            # Xác định phòng ban người đó đang dạy gần nhất
            cursor.execute("""
                SELECT department FROM TEACHLOG
                WHERE user_id = ? AND role = ?
                GROUP BY department
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, (uid, role))
            result = cursor.fetchone()
            if not result:
                await interaction.response.send_message("❌ Không tìm thấy dữ liệu tiết học phù hợp.", ephemeral=True)
                return

            department = result[0]

            # Truy vấn số tiết cũ trước khi xoá
            cursor.execute("SELECT COUNT(*) FROM TEACHLOG WHERE user_id = ? AND role = ? AND department = ?", (uid, role, department))
            old_count = cursor.fetchone()[0]

            # Xoá toàn bộ tiết cũ theo user + role + department
            cursor.execute("DELETE FROM TEACHLOG WHERE user_id = ? AND role = ? AND department = ?", (uid, role, department))

            # Xác định timestamp từ khoảng thời gian được chọn khi tracking
            start_ts = datetime.strptime(self.start_date_str, "%d/%m/%Y").timestamp()
            for i in range(new_count):
                ts = start_ts + i
                cursor.execute("INSERT INTO TEACHLOG VALUES (?, ?, ?, ?, 1)", (uid, ts, role, department))

            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ Đã cập nhật thành công: <@{uid}> giờ có `{new_count}` tiết **{role}** tại **{department}**.", ephemeral=True)

            log_channel = interaction.guild.get_channel(1378078053929844908)
            if log_channel:
                await log_channel.send(f"🛠 {interaction.user.mention} đã điều chỉnh tiết học cho <@{uid}>: từ `{old_count}` tiết {role} thành `{new_count}` tiết {role} ( {department} ).")

            
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi điều chỉnh: {e}", ephemeral=True)

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
            export_data = []
            for user_id, role, dept, count in cursor.fetchall():
                if user_id not in data:
                    data[user_id] = {
                        "Phòng GD & ĐT": {"Giảng Viên": 0, "Trợ Giảng": 0},
                        "Phòng Ban Khác": {"Giảng Viên": 0, "Trợ Giảng": 0}
                    }
                if dept not in data[user_id]:
                    data[user_id][dept] = {"Giảng Viên": 0, "Trợ Giảng": 0}
                data[user_id][dept][role] = count

                member = interaction.guild.get_member(user_id)
                display_name = member.display_name if member else f"(Unknown {user_id})"

                if dept == "Phòng GD & ĐT":
                    salary = count * 100000 if role == "Giảng Viên" else count * 50000
                else:
                    salary = count * 70000 if role == "Giảng Viên" else count * 30000

                export_data.append([display_name, role, dept, count, salary])

            conn.close()

            filename = f"BangLuongGD_{self.start_date.value.replace('/', '-')}to{self.end_date.value.replace('/', '-')}_{interaction.user.id}.csv"
            with open(filename, "w", newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Tên hiển thị", "Vai trò", "Phòng ban", "Số tiết", "Tổng tiền ($)"])
                writer.writerows(export_data)

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
            await interaction.response.send_message(embed=em, view=ExportButtonView(filename, self.start_date.value), ephemeral=True)

        except Exception as e:
            print(f"[TRACKING ERROR] {e}")
            traceback.print_exc()
            await interaction.response.send_message("❌ Đã xảy ra lỗi. Vui lòng thử lại sau.", ephemeral=True)

class TeachEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gdmenu")
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
