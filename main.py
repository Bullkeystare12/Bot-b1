import discord
from discord.ext import commands
from discord import app_commands
import time, asyncio, os, requests
from mcstatus import JavaServer, BedrockServer

# ---------- ENV ----------
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
BOT_ID = os.getenv("BOT_ID")

TOPGG_API = os.getenv("TOPGG_API")
DBL_API = os.getenv("DBL_API")
INFINITY_API = os.getenv("INFINITY_API")

# ---------- BOT ----------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

start_time = time.time()
uptime_tasks = {}

# ---------- READY ----------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ======================================================
# 🕒 UPTIME AUTO POST
# ======================================================
@bot.tree.command(name="uptime", description="Auto send uptime in a channel")
@app_commands.describe(
    channel="Target channel",
    unit="seconds / minutes / hours",
    value="Time value",
    user="Optional user mention"
)
async def uptime(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    unit: str,
    value: int,
    user: discord.User | None = None
):
    seconds = value
    if unit.lower() == "minutes":
        seconds *= 60
    elif unit.lower() == "hours":
        seconds *= 3600

    async def task():
        while True:
            t = int(time.time() - start_time)
            h, m, s = t // 3600, (t % 3600) // 60, t % 60
            msg = f"🟢 **Bot Uptime:** `{h}h {m}m {s}s`"
            if user:
                msg = f"{user.mention}\n" + msg
            await channel.send(msg)
            await asyncio.sleep(seconds)

    uptime_tasks[channel.id] = bot.loop.create_task(task())
    await interaction.response.send_message(
        "✅ Uptime auto-message started.", ephemeral=True
    )

# ======================================================
# 🗳️ VOTE COMMAND (BUTTON CONFIRM)
# ======================================================
class VoteConfirm(discord.ui.View):
    def __init__(self, link, channel):
        super().__init__(timeout=30)
        self.link = link
        self.channel = channel

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, _):
        await self.channel.send(
            f"❤️ **Support the bot by voting!**\n👉 {self.link}"
        )
        await interaction.response.send_message(
            "✅ Vote message sent.", ephemeral=True
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, _):
        await interaction.response.send_message(
            "❌ Vote cancelled.", ephemeral=True
        )
        self.stop()

@bot.tree.command(name="vote", description="Send vote link with confirmation")
@app_commands.describe(
    website="topgg / dbl / infinity / void",
    app_id="Bot App ID",
    channel="Target channel"
)
async def vote(
    interaction: discord.Interaction,
    website: str,
    app_id: str,
    channel: discord.TextChannel
):
    links = {
        "topgg": f"https://top.gg/bot/{app_id}/vote",
        "dbl": f"https://discordbotlist.com/bots/{app_id}/upvote",
        "infinity": f"https://infinitybots.gg/bots/{app_id}/vote",
        "void": f"https://voidbots.net/bot/{app_id}/vote"
    }

    link = links.get(website.lower())
    if not link:
        return await interaction.response.send_message(
            "❌ Invalid website.", ephemeral=True
        )

    await interaction.response.send_message(
        f"⚠️ **Confirm Vote Message**\n\n"
        f"🌐 Website: **{website}**\n"
        f"📢 Channel: {channel.mention}\n"
        f"🔗 Link:\n{link}",
        view=VoteConfirm(link, channel),
        ephemeral=True
    )

# ======================================================
# 🏆 VOTE LEADERBOARD
# ======================================================
@bot.tree.command(name="voteleaderboard", description="Show vote leaderboard")
async def voteleaderboard(interaction: discord.Interaction):
    data = []

    try:
        r = requests.get(
            f"https://top.gg/api/bots/{BOT_ID}",
            headers={"Authorization": TOPGG_API}
        )
        if r.status_code == 200:
            data.append(("Top.gg", r.json()["points"]))
    except:
        pass

    try:
        r = requests.get(
            f"https://discordbotlist.com/api/v1/bots/{BOT_ID}",
            headers={"Authorization": DBL_API}
        )
        if r.status_code == 200:
            data.append(("DiscordBotList", r.json()["upvotes"]))
    except:
        pass

    try:
        r = requests.get(
            f"https://infinitybots.gg/api/bots/{BOT_ID}",
            headers={"Authorization": INFINITY_API}
        )
        if r.status_code == 200:
            data.append(("InfinityBots", r.json()["votes"]))
    except:
        pass

    if not data:
        return await interaction.response.send_message("❌ No data found.")

    data.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Vote Leaderboard",
        color=discord.Color.gold()
    )

    for i, (site, votes) in enumerate(data, 1):
        embed.add_field(
            name=f"#{i} {site}",
            value=f"⭐ Votes: `{votes}`",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ======================================================
# 🎮 MINECRAFT STATUS
# ======================================================
@bot.tree.command(name="mcstatus", description="Check Minecraft server status")
@app_commands.describe(
    ip="Server IP",
    edition="java or bedrock",
    port="Optional port"
)
async def mcstatus(
    interaction: discord.Interaction,
    ip: str,
    edition: str = "java",
    port: int | None = None
):
    try:
        if edition.lower() == "bedrock":
            server = BedrockServer(ip, port or 19132)
            status = server.status()
            msg = (
                "🟩 **Bedrock Server Online**\n"
                f"👥 Players: `{status.players_online}/{status.players_max}`\n"
                f"📶 Ping: `{int(status.latency)}ms`"
            )
        else:
            server = JavaServer(ip, port or 25565)
            status = server.status()
            msg = (
                "🟢 **Java Server Online**\n"
                f"👥 Players: `{status.players.online}/{status.players.max}`\n"
                f"📶 Ping: `{int(status.latency)}ms`"
            )

        await interaction.response.send_message(msg)
    except:
        await interaction.response.send_message(
            "❌ Server offline or invalid details."
        )

# ======================================================
# 🔒 OWNER SHUTDOWN
# ======================================================
@bot.tree.command(name="shutdown", description="Owner only")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "❌ Owner only.", ephemeral=True
        )
    await interaction.response.send_message("🛑 Shutting down...")
    await bot.close()

# ---------- RUN ----------
bot.run(TOKEN)
