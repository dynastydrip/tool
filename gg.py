import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import sqlite3
import random
import time
import asyncio

# ================= TOKEN =================
with open("token.txt", "r", encoding="utf-8") as f:
    TOKEN = f.read().strip()

# ================= BOT =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="p!",
    intents=intents,
    help_command=None
)

# ================= DATABASE =================
conn = sqlite3.connect("owo_public.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
id TEXT PRIMARY KEY,
cash INTEGER,
xp INTEGER,
level INTEGER,
pet TEXT,
last_daily REAL,
last_hunt REAL
)
""")
conn.commit()

# ================= PETS =================
pets = {
    "none": 1,
    "fox": 1.2,
    "wolf": 1.5,
    "dragon": 2.5
}

# ================= UTILS =================
def get_user(uid):
    c.execute("SELECT * FROM users WHERE id=?", (str(uid),))
    u = c.fetchone()

    if not u:
        c.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uid), 1000, 0, 1, "none", 0, 0))
        conn.commit()
        return get_user(uid)

    return u


def save(uid, cash, xp, lvl, pet, ld, lh):
    c.execute("""
    UPDATE users
    SET cash=?, xp=?, level=?, pet=?, last_daily=?, last_hunt=?
    WHERE id=?
    """, (cash, xp, lvl, pet, ld, lh, str(uid)))
    conn.commit()


def cd(last, sec):
    now = time.time()

    if now - last < sec:
        return False, int(sec - (now - last))

    return True, now


def add_xp(xp, lvl):
    xp += 10

    if xp >= lvl * 100:
        return 0, lvl + 1, True

    return xp, lvl, False


def draw():
    return random.randint(2, 11)


def emb(title, desc, color=0x2f3136):
    return discord.Embed(
        title=title,
        description=desc,
        color=color
    )

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🔥 Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(e)

# ================= HELP =================
@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="📖 P! HELP MENU",
        description="List of commands",
        color=0x00ffcc
    )

    embed.add_field(
        name="💰 Economy",
        value="""
`p!daily`
`p!hunt`
`p!profile`
`p!leaderboard`
""",
        inline=False
    )

    embed.add_field(
        name="🎮 Games",
        value="""
`p!coinflip <amount> <heads/tails>`
`p!spin <amount>`
`p!blackjack <amount>`
""",
        inline=False
    )

    embed.add_field(
        name="🛒 Other",
        value="""
`p!shop`
`p!help`
""",
        inline=False
    )

    await ctx.send(embed=embed)

# ================= PROFILE =================
@bot.command()
async def profile(ctx):
    u = get_user(ctx.author.id)

    embed = discord.Embed(
        title=f"👤 {ctx.author.name}",
        color=0x00ffcc
    )

    embed.add_field(name="💰 Cash", value=u[1])
    embed.add_field(name="⭐ XP", value=u[2])
    embed.add_field(name="🏆 Level", value=u[3])
    embed.add_field(name="🐾 Pet", value=u[4])

    await ctx.send(embed=embed)

# ================= DAILY =================
@bot.command()
async def daily(ctx):
    u = get_user(ctx.author.id)

    ok, val = cd(u[5], 86400)

    if not ok:
        return await ctx.send(
            embed=emb("⏳ Cooldown", f"Wait {val}s")
        )

    reward = random.randint(1500, 4000)

    xp, lvl, up = add_xp(u[2], u[3])

    save(
        ctx.author.id,
        u[1] + reward,
        xp,
        lvl,
        u[4],
        val,
        u[6]
    )

    msg = f"🎁 You got `{reward}` coins"

    if up:
        msg += "\n⬆️ LEVEL UP"

    await ctx.send(embed=emb("💰 Daily Reward", msg))

# ================= HUNT =================
@bot.command()
async def hunt(ctx):
    u = get_user(ctx.author.id)

    ok, val = cd(u[6], 10)

    if not ok:
        return await ctx.send(
            embed=emb("⏳ Cooldown", f"Wait {val}s")
        )

    animal = random.choice([
        "🐶 dog",
        "🐱 cat",
        "🦊 fox",
        "🐻 bear",
        "🐼 panda"
    ])

    base = random.randint(100, 500)

    mult = pets.get(u[4], 1)

    reward = int(base * mult)

    xp, lvl, up = add_xp(u[2], u[3])

    save(
        ctx.author.id,
        u[1] + reward,
        xp,
        lvl,
        u[4],
        u[5],
        val
    )

    msg = f"🏹 Hunted {animal}\n💰 +{reward}"

    if up:
        msg += "\n⬆️ LEVEL UP"

    await ctx.send(embed=emb("🎯 Hunt", msg))

# ================= COINFLIP =================
@bot.command()
async def coinflip(ctx, amount: int, side: str):

    u = get_user(ctx.author.id)

    if amount > u[1]:
        return await ctx.send("❌ Not enough money")

    if side.lower() not in ["heads", "tails"]:
        return await ctx.send("❌ choose heads/tails")

    msg = await ctx.send("🪙 Flipping coin...")

    flips = [
        "🪙 heads...",
        "🪙 tails...",
        "🪙 spinning..."
    ]

    for i in range(3):
        await asyncio.sleep(0.7)
        await msg.edit(content=flips[i])

    result = random.choice(["heads", "tails"])

    cash = u[1]

    if result == side.lower():
        cash += amount
        text = f"✅ WON +{amount}"
    else:
        cash -= amount
        text = f"❌ LOST -{amount}"

    save(ctx.author.id, cash, u[2], u[3], u[4], u[5], u[6])

    embed = emb(
        "🪙 Coinflip",
        f"Result: **{result.upper()}**\n{text}"
    )

    await msg.edit(content="", embed=embed)

# ================= SPIN =================
@bot.command()
async def spin(ctx, amount: int):

    u = get_user(ctx.author.id)

    if amount > u[1]:
        return await ctx.send("❌ Not enough money")

    slots = ["🍒", "🍋", "🍇", "💎", "7️⃣"]

    msg = await ctx.send("🎰 Spinning...")

    for _ in range(4):

        r = [
            random.choice(slots),
            random.choice(slots),
            random.choice(slots)
        ]

        await asyncio.sleep(0.5)

        await msg.edit(
            content=f"🎰 {' | '.join(r)}"
        )

    final = [
        random.choice(slots),
        random.choice(slots),
        random.choice(slots)
    ]

    text = " | ".join(final)

    cash = u[1]

    if len(set(final)) == 1:
        reward = amount * 3
        cash += reward
        result = f"🔥 JACKPOT +{reward}"
    else:
        cash -= amount
        result = f"❌ LOST -{amount}"

    save(ctx.author.id, cash, u[2], u[3], u[4], u[5], u[6])

    embed = emb(
        "🎰 Slot Machine",
        f"{text}\n\n{result}"
    )

    await msg.edit(content="", embed=embed)

# ================= SHOP =================
@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="🛒 SHOP",
        description="""
🦊 fox — 1000
🐺 wolf — 3000
🐉 dragon — 10000
""",
        color=0xffcc00
    )

    await ctx.send(embed=embed)

# ================= BLACKJACK =================
class BJ(View):

    def __init__(self, uid, amount):
        super().__init__(timeout=30)

        self.uid = uid
        self.amount = amount

        self.p = [draw(), draw()]
        self.d = [draw(), draw()]

    def t(self, x):
        return sum(x)

    async def end(self, interaction, result):

        u = get_user(self.uid)

        cash = u[1]

        if result == "win":
            cash += self.amount
        elif result == "lose":
            cash -= self.amount

        save(
            self.uid,
            cash,
            u[2],
            u[3],
            u[4],
            u[5],
            u[6]
        )

        embed = emb(
            "🃏 Blackjack Result",
            f"""
Your Total: `{self.t(self.p)}`
Dealer Total: `{self.t(self.d)}`

Result: **{result.upper()}**
"""
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @discord.ui.button(
        label="HIT",
        style=discord.ButtonStyle.green
    )
    async def hit(self, interaction, button):

        if interaction.user.id != self.uid:
            return await interaction.response.send_message(
                "❌ not your game",
                ephemeral=True
            )

        self.p.append(draw())

        if self.t(self.p) > 21:
            return await self.end(interaction, "lose")

        embed = emb(
            "🃏 Blackjack",
            f"""
Your Total: `{self.t(self.p)}`
Dealer: `{self.d[0]} + ?`
"""
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="STAND",
        style=discord.ButtonStyle.red
    )
    async def stand(self, interaction, button):

        while self.t(self.d) < 17:
            self.d.append(draw())

        p = self.t(self.p)
        d = self.t(self.d)

        if p > d or d > 21:
            res = "win"
        elif p < d:
            res = "lose"
        else:
            res = "draw"

        await self.end(interaction, res)

@bot.command()
async def blackjack(ctx, amount: int):

    u = get_user(ctx.author.id)

    if amount > u[1]:
        return await ctx.send("❌ Not enough money")

    embed = emb(
        "🃏 Blackjack",
        """
Click buttons below

🟩 HIT
🟥 STAND
"""
    )

    await ctx.send(
        embed=embed,
        view=BJ(ctx.author.id, amount)
    )

# ================= LEADERBOARD =================
@bot.command()
async def leaderboard(ctx):

    c.execute("""
    SELECT id, cash
    FROM users
    ORDER BY cash DESC
    LIMIT 10
    """)

    rows = c.fetchall()

    text = ""

    for i, r in enumerate(rows):
        text += f"**{i+1}.** {r[0]} — `{r[1]}`💰\n"

    embed = emb(
        "🏆 Leaderboard",
        text
    )

    await ctx.send(embed=embed)

# ================= ADD CASH =================
@bot.command()
async def addcash(ctx, member: discord.Member, amount: int):

    OWNER_ID = 1141054252433821876

    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ owner only")

    if amount <= 0:
        return await ctx.send("❌ amount phải lớn hơn 0")

    u = get_user(member.id)

    new_cash = u[1] + amount

    save(
        member.id,
        new_cash,
        u[2],
        u[3],
        u[4],
        u[5],
        u[6]
    )

    embed = emb(
        "💸 ADD CASH",
        f"""
✅ Added `{amount}` coins

👤 User: {member.mention}
💰 New Balance: `{new_cash}`
""",
        0x00ff99
    )

    await ctx.send(embed=embed)

# ================= RUN =================
print("🔥 OW0 REAL PUBLIC BOT STARTING...")
bot.run(TOKEN)
