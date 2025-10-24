import sqlite3
import discord
from discord.ext import commands, tasks
from discord import Embed, Color, Interaction
from discord.ui import View, button, Button
from datetime import datetime, timedelta
from pytz import timezone

TZ = timezone("Asia/Ho_Chi_Minh")

CONFIRM_CHANNEL_ID = 1429695494124208169  # room to post confirmation prompts
PROMPT_INTERVAL = timedelta(hours=1)       # ask every 1 hours
CONFIRM_TIMEOUT = 300                      # 5 minutes (seconds)

def fmt_timedelta(td: timedelta) -> str:
    total_minutes = int(td.total_seconds() // 60)
    return f"{total_minutes // 60}h {total_minutes % 60} phút"

class ConfirmView(View):
    def __init__(self, cog: "ConfirmDuty", user_id: int):
        super().__init__(timeout=CONFIRM_TIMEOUT)
        self.cog = cog
        self.user_id = user_id
        self.message = None  # filled after send
        self._confirmed = False

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Đây không phải yêu cầu của bạn.", ephemeral=True)
            return False
        return True

    @button(label="✅ Xác Nhận On-Duty", style=discord.ButtonStyle.success, custom_id="confirm_onduty_btn")
    async def confirm(self, interaction: Interaction, _: Button):
        self._confirmed = True
        await self.cog.mark_confirmed(self.user_id)
        em = Embed(
            title="✅ Đã xác nhận trạng thái ON-DUTY",
            description=f"{interaction.user.mention} đã xác nhận tiếp tục làm việc.",
            color=Color.green()
        )
        em.set_footer(text="BiOneBot • Hệ thống chấm công Tự Động")
        em.timestamp = datetime.now(TZ)
        await interaction.response.edit_message(embed=em, view=None)
        # clear pending
        self.cog.pending.pop(self.user_id, None)

    async def on_timeout(self) -> None:
        # If not confirmed -> auto offduty
        if not self._confirmed:
            try:
                await self.cog.auto_offduty(self.user_id, origin="⏰ Hết thời gian xác nhận (5 phút)")
            finally:
                # clear pending and disable buttons
                if self.message:
                    try:
                        em = self.message.embeds[0] if self.message.embeds else Embed()
                        em.title = "⏳ Hết thời gian xác nhận"
                        em.color = Color.red()
                        await self.message.edit(embed=em, view=None)
                    except Exception:
                        pass
                self.cog.pending.pop(self.user_id, None)

class ConfirmDuty(commands.Cog):
    """Tự động yêu cầu xác nhận ON-DUTY mỗi 2 giờ. Không xác nhận trong 3 phút sẽ OFF-DUTY."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect("data.sqlite", timeout=5)
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS CONFIRMLOG (
                user_id INTEGER PRIMARY KEY,
                last_confirm REAL
            )
        """)
        self.db.commit()
        # track prompts already sent (avoid spam)
        self.pending: dict[int, int] = {}  # user_id -> message_id
        self.loop_check.start()

    def cog_unload(self):
        try:
            self.loop_check.cancel()
        except Exception:
            pass
        self.db.close()

    def get_last_confirm(self, user_id: int, fallback_ts: float) -> float:
        row = self.cursor.execute("SELECT last_confirm FROM CONFIRMLOG WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            self.cursor.execute("INSERT INTO CONFIRMLOG(user_id, last_confirm) VALUES (?, ?)", (user_id, fallback_ts))
            self.db.commit()
            return fallback_ts
        return float(row[0] or fallback_ts)

    async def mark_confirmed(self, user_id: int):
        now_ts = datetime.now(TZ).timestamp()
        self.cursor.execute("INSERT INTO CONFIRMLOG(user_id, last_confirm) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET last_confirm=excluded.last_confirm", (user_id, now_ts))
        self.db.commit()

    @tasks.loop(seconds=60)
    async def loop_check(self):
        """Every minute: find ONDUTY users that hit the 2h threshold; ask them to confirm."""
        try:
            now = datetime.now(TZ)
            self.cursor.execute("SELECT user_id, user_onduty, license FROM ONDUTY WHERE user_onduty != 0")
            rows = self.cursor.fetchall()

            channel = self.bot.get_channel(CONFIRM_CHANNEL_ID)

            for user_id, start_ts, license in rows:
                # last confirm defaults to start time
                last_confirm_ts = self.get_last_confirm(user_id, start_ts)
                last_confirm_dt = datetime.fromtimestamp(last_confirm_ts, tz=TZ)

                if now - last_confirm_dt >= PROMPT_INTERVAL:
                    if user_id in self.pending:
                        continue  # already awaiting confirmation

                    # Build prompt embed
                    member = None
                    for g in self.bot.guilds:
                        m = g.get_member(int(user_id))
                        if m:
                            member = m
                            break

                    started_dt = datetime.fromtimestamp(start_ts, tz=TZ)
                    duration = now - started_dt

                    em = Embed(
                        title="🔔 Xác Nhận Trạng Thái On-Duty",
                        description=(
                            f"**Bạn đang ON-DUTY được {fmt_timedelta(duration)}**\n\n"
                            "⚠️ Vui lòng xác nhận bạn vẫn còn đang làm việc!\n"
                            f"**Nếu không xác nhận trong 5 phút, hệ thống sẽ tự động OFF-DUTY.**"
                        ),
                        color=Color.orange()
                    )
                    em.add_field(name="🕒 Thời gian bắt đầu", value=started_dt.strftime("%H:%M:%S  %d/%m/%Y"), inline=False)
                    if license:
                        em.add_field(name="🚓 Phương tiện", value=f"`{license}`", inline=True)
                    if member:
                        em.set_author(name=member.display_name, icon_url=(member.avatar.url if member.avatar else member.default_avatar.url))
                    em.set_footer(text="BiOneBot • Hệ Thống Chấm Công Tự Động")
                    em.timestamp = now

                    if channel is None:
                        continue  # channel not found

                    view = ConfirmView(self, int(user_id))
                    msg = await channel.send(content=(member.mention if member else None), embed=em, view=view)
                    view.message = msg
                    self.pending[int(user_id)] = msg.id
        except Exception as e:
            print(f"[ConfirmDuty loop error] {e}")

    @loop_check.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def auto_offduty(self, user_id: int, origin: str = "Auto OFF-DUTY (No confirm)"):
        """
        Chỉ dùng cho trường hợp KHÔNG xác nhận trong 5 phút.
        - Reset ONDUTY về 0
        - XÓA toàn bộ OFFDUTY của NGÀY HÔM NAY (theo TZ) để hủy công trong ngày
        - Gửi thông báo vào kênh xác nhận
        LƯU Ý: offduty thủ công (lệnh trong duty.py) vẫn ghi OFFDUTY như bình thường.
        """
        try:
            # Lấy thông tin phiên đang ON
            row = self.cursor.execute(
                "SELECT user_onduty, license FROM ONDUTY WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if not row:
                return
            start_ts, license = row
            if start_ts == 0:
                return

            now = datetime.now(TZ)
            start_dt = datetime.fromtimestamp(start_ts, tz=TZ)

            # Xác định NGÀY HÔM NAY theo TZ
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_day_start = day_start + timedelta(days=1)

            day_start_ts = day_start.timestamp()
            next_day_start_ts = next_day_start.timestamp()

            # 1) Reset ONDUTY về 0
            self.cursor.execute(
                "UPDATE ONDUTY SET user_onduty = 0 WHERE user_id = ?",
                (user_id,)
            )

            # 2) XÓA toàn bộ công của NGÀY HÔM NAY
            self.cursor.execute(
                "DELETE FROM OFFDUTY WHERE user_id = ? AND day >= ? AND day < ?",
                (user_id, day_start_ts, next_day_start_ts)
            )

            self.db.commit()

            # 3) Gửi thông báo
            channel = self.bot.get_channel(CONFIRM_CHANNEL_ID)
            member = None
            for g in self.bot.guilds:
                m = g.get_member(int(user_id))
                if m:
                    member = m
                    break

            em = Embed(
                title="⛔ Tự động OFF-DUTY & Hủy công trong ngày",
                description=(
                    f"{member.mention if member else f'<@{user_id}>'} đã bị OFF-DUTY: **{origin}**\n"
                    " *Tất cả giờ công trong NGÀY HÔM NAY đã bị xóa.* "
                ),
                color=Color.red()
            )
            em.add_field(
                name="Thời gian bắt đầu ca",
                value=start_dt.strftime("%d/%m/%Y, %H:%M:%S"),
                inline=False
            )
            em.add_field(
                name="Khoảng ngày bị xóa",
                value=f"{day_start.strftime('%d/%m/%Y')} (00:00) → {next_day_start.strftime('%d/%m/%Y')} (00:00)",
                inline=False
            )
            if license:
                em.add_field(name="Phương tiện", value=f"`{license}`", inline=True)
            em.timestamp = now

            if channel:
                await channel.send(embed=em)
        except Exception as e:
            print(f"[ConfirmDuty auto_offduty (wipe day) error] {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfirmDuty(bot))
