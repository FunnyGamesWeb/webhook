import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# =============================================
# EINSTELLUNGEN - HIER ANPASSEN
# =============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 123456789  # Deine Channel ID (nur Zahlen, keine Anführungszeichen!)
# =============================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Speichert aktive UI-Bau Sessions
# { user_id: { "remotes": [...], "elements": [...] } }
sessions = {}

# =============================================
# HILFSFUNKTIONEN - WindUI Code Generator
# =============================================

def generate_windui_element(element_type, name, remote_code):
    """Generiert WindUI Code für ein Element"""
    
    if element_type == "toggle":
        return f"""Tab:Toggle({{
    Title = "{name}",
    Value = false,
    Callback = function(v)
        if v then
            {remote_code}
        end
    end,
}})"""

    elif element_type == "button":
        return f"""Tab:Button({{
    Title = "{name}",
    Justify = "Center",
    Callback = function()
        {remote_code}
    end,
}})"""

    elif element_type == "slider":
        return f"""Tab:Slider({{
    Title = "{name}",
    Value = {{
        Min = 0,
        Max = 100,
        Default = 50,
    }},
    Callback = function(value)
        -- Passe den Remote Call an!
        {remote_code}
    end,
}})"""

    elif element_type == "dropdown":
        return f"""Tab:Dropdown({{
    Title = "{name}",
    Values = {{"Option 1", "Option 2", "Option 3"}},
    Callback = function(value)
        -- Passe den Remote Call an!
        {remote_code}
    end,
}})"""

    elif element_type == "textbox":
        return f"""Tab:Input({{
    Title = "{name}",
    Placeholder = "Eingabe hier...",
    Callback = function(text)
        -- Passe den Remote Call an!
        {remote_code}
    end,
}})"""

    return ""


def generate_full_menu(elements):
    """Generiert ein komplettes WindUI Menü Script"""
    
    elements_code = "\n\n".join([
        f"-- {el['name']} ({el['type']})\n{el['code']}"
        for el in elements
    ])
    
    return f"""-- Komplettes WindUI Menü
-- Generiert von SimpleSpy Bot
-- ⚠️ Vergiss nicht WindUI zu laden!

local WindUI = loadstring(game:HttpGet(
    "https://raw.githubusercontent.com/Footagesus/WindUI/main/dist/main.lua"
))()

local Window = WindUI:CreateWindow({{
    Title = "Mein Menü",
    Author = "by Me",
    Icon = "solar:compass-big-bold",
    Theme = "Dark",
    Transparent = true,
    ToggleKey = Enum.KeyCode.RightShift,
}})

local Tab = Window:Tab({{
    Title = "Main",
    Icon = "solar:home-bold",
}})

{elements_code}
"""


# =============================================
# DISCORD VIEWS (Buttons)
# =============================================

class StartView(discord.ui.View):
    """Erste Buttons: Create a UI?"""
    def __init__(self, remote_name, script_code):
        super().__init__(timeout=300)
        self.remote_name = remote_name
        self.script_code = script_code

    @discord.ui.button(label="✅ Create a UI!", style=discord.ButtonStyle.green)
    async def create_ui(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HowManyView(self.remote_name, self.script_code, interaction.user.id)
        await interaction.response.edit_message(
            content="",
            embed=discord.Embed(
                title="📐 Wie viele Elemente?",
                description="Willst du **ein einzelnes Element** oder ein **komplettes Menü** mit mehreren Elementen bauen?",
                color=0x5865F2
            ),
            view=view
        )

    @discord.ui.button(label="❌ Nein danke", style=discord.ButtonStyle.red)
    async def no_ui(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Okay! Script wurde nur gespeichert.",
            embed=None,
            view=None
        )


class HowManyView(discord.ui.View):
    """Ein Element oder Mehrere?"""
    def __init__(self, remote_name, script_code, user_id):
        super().__init__(timeout=300)
        self.remote_name = remote_name
        self.script_code = script_code
        self.user_id = user_id

    @discord.ui.button(label="1️⃣ Ein Element", style=discord.ButtonStyle.blurple)
    async def one_element(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ElementTypeView(self.remote_name, self.script_code, self.user_id, multi=False)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎛️ Welches Element?",
                description=f"Was soll **{self.remote_name}** werden?",
                color=0x5865F2
            ),
            view=view
        )

    @discord.ui.button(label="📋 Komplettes Menü", style=discord.ButtonStyle.green)
    async def multi_element(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Session starten
        sessions[self.user_id] = {
            "remotes": [{"name": self.remote_name, "code": self.script_code}],
            "elements": []
        }
        view = MultiElementView(self.remote_name, self.script_code, self.user_id)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="📋 Menü Builder",
                description=f"**Remote hinzugefügt:** `{self.remote_name}`\n\nWas soll dieses Element werden?",
                color=0x5865F2
            ),
            view=view
        )


class ElementTypeView(discord.ui.View):
    """Auswahl: Toggle / Button / Slider / Dropdown / Textbox"""
    def __init__(self, remote_name, script_code, user_id, multi=False, session_key=None):
        super().__init__(timeout=300)
        self.remote_name = remote_name
        self.script_code = script_code
        self.user_id = user_id
        self.multi = multi
        self.session_key = session_key

    async def handle_choice(self, interaction, element_type):
        code = generate_windui_element(element_type, self.remote_name, self.script_code)
        
        if self.multi and self.user_id in sessions:
            # Zum Menü hinzufügen
            sessions[self.user_id]["elements"].append({
                "name": self.remote_name,
                "type": element_type,
                "code": code
            })
            
            count = len(sessions[self.user_id]["elements"])
            view = AddMoreView(self.user_id)
            
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="✅ Element hinzugefügt!",
                    description=f"**{self.remote_name}** wurde als `{element_type.upper()}` hinzugefügt!\n\n**Elemente im Menü:** {count}\nMöchtest du noch ein Element hinzufügen?",
                    color=0x57F287
                ),
                view=view
            )
        else:
            # Einzelnes Element direkt ausgeben
            embed = discord.Embed(
                title=f"✅ WindUI {element_type.upper()} Code",
                description=f"**Remote:** `{self.remote_name}`\n**Typ:** `{element_type}`",
                color=0x57F287
            )
            
            # Code aufteilen falls zu lang
            if len(code) > 950:
                embed.add_field(name="📜 Code (Teil 1)", value=f"```lua\n{code[:950]}\n```", inline=False)
                embed.add_field(name="📜 Code (Teil 2)", value=f"```lua\n{code[950:]}\n```", inline=False)
            else:
                embed.add_field(name="📜 Code", value=f"```lua\n{code}\n```", inline=False)
            
            embed.set_footer(text="Kopiere den Code und füge ihn in dein Script ein!")
            
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🔘 Toggle", style=discord.ButtonStyle.blurple)
    async def toggle(self, interaction, button):
        await self.handle_choice(interaction, "toggle")

    @discord.ui.button(label="⚡ Button", style=discord.ButtonStyle.green)
    async def button_el(self, interaction, button):
        await self.handle_choice(interaction, "button")

    @discord.ui.button(label="🎚️ Slider", style=discord.ButtonStyle.grey)
    async def slider(self, interaction, button):
        await self.handle_choice(interaction, "slider")

    @discord.ui.button(label="📋 Dropdown", style=discord.ButtonStyle.grey)
    async def dropdown(self, interaction, button):
        await self.handle_choice(interaction, "dropdown")

    @discord.ui.button(label="✏️ Textbox", style=discord.ButtonStyle.grey)
    async def textbox(self, interaction, button):
        await self.handle_choice(interaction, "textbox")


class MultiElementView(discord.ui.View):
    """Beim Menü Builder - Element Typ wählen"""
    def __init__(self, remote_name, script_code, user_id):
        super().__init__(timeout=300)
        self.remote_name = remote_name
        self.script_code = script_code
        self.user_id = user_id

    async def handle_choice(self, interaction, element_type):
        code = generate_windui_element(element_type, self.remote_name, self.script_code)
        
        if self.user_id in sessions:
            sessions[self.user_id]["elements"].append({
                "name": self.remote_name,
                "type": element_type,
                "code": code
            })
        
        count = len(sessions[self.user_id]["elements"]) if self.user_id in sessions else 1
        view = AddMoreView(self.user_id)
        
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Element hinzugefügt!",
                description=f"**{self.remote_name}** → `{element_type.upper()}`\n\n**Elemente im Menü:** {count}\nMöchtest du noch ein Remote hinzufügen?",
                color=0x57F287
            ),
            view=view
        )

    @discord.ui.button(label="🔘 Toggle", style=discord.ButtonStyle.blurple)
    async def toggle(self, interaction, button):
        await self.handle_choice(interaction, "toggle")

    @discord.ui.button(label="⚡ Button", style=discord.ButtonStyle.green)
    async def button_el(self, interaction, button):
        await self.handle_choice(interaction, "button")

    @discord.ui.button(label="🎚️ Slider", style=discord.ButtonStyle.grey)
    async def slider(self, interaction, button):
        await self.handle_choice(interaction, "slider")

    @discord.ui.button(label="📋 Dropdown", style=discord.ButtonStyle.grey)
    async def dropdown(self, interaction, button):
        await self.handle_choice(interaction, "dropdown")

    @discord.ui.button(label="✏️ Textbox", style=discord.ButtonStyle.grey)
    async def textbox(self, interaction, button):
        await self.handle_choice(interaction, "textbox")


class AddMoreView(discord.ui.View):
    """Noch ein Remote hinzufügen oder Menü fertigstellen?"""
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="➕ Weiteres Remote hinzufügen", style=discord.ButtonStyle.blurple)
    async def add_more(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="➕ Remote hinzufügen",
                description="Gehe in SimpleSpy, klicke auf ein Remote und dann auf **'Send to Menu'**!\n\nDas Remote wird dann automatisch hier hinzugefügt.",
                color=0x5865F2
            ),
            view=WaitingView(self.user_id)
        )

    @discord.ui.button(label="✅ Menü fertigstellen", style=discord.ButtonStyle.green)
    async def finish_menu(self, interaction, button):
        if self.user_id not in sessions or not sessions[self.user_id]["elements"]:
            await interaction.response.edit_message(
                content="❌ Keine Elemente gefunden!",
                embed=None, view=None
            )
            return
        
        full_code = generate_full_menu(sessions[self.user_id]["elements"])
        element_list = "\n".join([
            f"• `{el['name']}` → {el['type'].upper()}"
            for el in sessions[self.user_id]["elements"]
        ])
        
        embed = discord.Embed(
            title="🎉 Komplettes WindUI Menü",
            description=f"**Elemente:**\n{element_list}",
            color=0x57F287
        )
        
        # Code in Chunks aufteilen (Discord Limit 1024 pro Field)
        chunk_size = 950
        chunks = [full_code[i:i+chunk_size] for i in range(0, len(full_code), chunk_size)]
        
        for idx, chunk in enumerate(chunks):
            embed.add_field(
                name=f"📜 Code {'(Teil ' + str(idx+1) + ')' if len(chunks) > 1 else ''}",
                value=f"```lua\n{chunk}\n```",
                inline=False
            )
        
        embed.set_footer(text="Kopiere den kompletten Code und führe ihn im Spiel aus!")
        
        # Session aufräumen
        del sessions[self.user_id]
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Abbrechen", style=discord.ButtonStyle.red)
    async def cancel(self, interaction, button):
        if self.user_id in sessions:
            del sessions[self.user_id]
        await interaction.response.edit_message(
            content="❌ Menü Builder abgebrochen.",
            embed=None, view=None
        )


class WaitingView(discord.ui.View):
    """Warte auf nächstes Remote aus SimpleSpy"""
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="✅ Menü fertigstellen", style=discord.ButtonStyle.green)
    async def finish(self, interaction, button):
        if self.user_id not in sessions or not sessions[self.user_id]["elements"]:
            await interaction.response.edit_message(content="❌ Keine Elemente!", embed=None, view=None)
            return
        
        full_code = generate_full_menu(sessions[self.user_id]["elements"])
        element_list = "\n".join([f"• `{el['name']}` → {el['type'].upper()}" for el in sessions[self.user_id]["elements"]])
        
        embed = discord.Embed(title="🎉 Komplettes WindUI Menü", description=f"**Elemente:**\n{element_list}", color=0x57F287)
        chunks = [full_code[i:i+950] for i in range(0, len(full_code), 950)]
        for idx, chunk in enumerate(chunks):
            embed.add_field(name=f"📜 Code {'(Teil ' + str(idx+1) + ')' if len(chunks) > 1 else ''}", value=f"```lua\n{chunk}\n```", inline=False)
        embed.set_footer(text="Kopiere den kompletten Code und führe ihn im Spiel aus!")
        
        del sessions[self.user_id]
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🗑️ Abbrechen", style=discord.ButtonStyle.red)
    async def cancel(self, interaction, button):
        if self.user_id in sessions:
            del sessions[self.user_id]
        await interaction.response.edit_message(content="❌ Abgebrochen.", embed=None, view=None)


# =============================================
# BOT EVENTS & WEBHOOK EMPFANG
# =============================================

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} Slash Commands synchronisiert")
    except Exception as e:
        print(f"❌ Sync Fehler: {e}")


@bot.event
async def on_message(message):
    """Empfängt SimpleSpy Nachrichten vom Webhook"""
    if message.author.bot and message.channel.id == CHANNEL_ID:
        # Prüft ob es eine SimpleSpy Webhook Nachricht ist
        if message.embeds:
            embed = message.embeds[0]
            if embed.title and embed.title.startswith("📡"):
                remote_name = embed.title.replace("📡 ", "").strip()
                
                # Script aus dem Embed holen
                script_code = ""
                remote_type = "event"
                for field in embed.fields:
                    if field.name == "📜 Script":
                        # Code Block entfernen
                        script_code = field.value.replace("```lua\n", "").replace("\n```", "").strip()
                    if field.name == "📦 Remote Typ":
                        if "Function" in field.value:
                            remote_type = "function"

                # UI Erstell-Frage schicken
                ui_embed = discord.Embed(
                    title="🎮 UI erstellen?",
                    description=f"Remote **{remote_name}** wurde empfangen!\nMöchtest du daraus ein **WindUI Element** erstellen?",
                    color=0x5865F2
                )
                ui_embed.add_field(
                    name="📜 Script Preview",
                    value=f"```lua\n{script_code[:200]}{'...' if len(script_code) > 200 else ''}\n```",
                    inline=False
                )
                
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(
                        embed=ui_embed,
                        view=StartView(remote_name, script_code)
                    )

    await bot.process_commands(message)


# =============================================
# SLASH COMMANDS
# =============================================

@bot.tree.command(name="add_to_menu", description="Fügt ein Remote manuell zum Menü Builder hinzu")
@app_commands.describe(
    remote_name="Name des Remotes",
    script_code="Der Script Code"
)
async def add_to_menu(interaction: discord.Interaction, remote_name: str, script_code: str):
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message("❌ Dieser Command funktioniert nur im SimpleSpy Channel!", ephemeral=True)
        return
    
    user_id = interaction.user.id
    
    if user_id not in sessions:
        sessions[user_id] = {"remotes": [], "elements": []}
    
    sessions[user_id]["remotes"].append({"name": remote_name, "code": script_code})
    
    view = MultiElementView(remote_name, script_code, user_id)
    await interaction.response.send_message(
        embed=discord.Embed(
            title="➕ Remote zum Menü hinzugefügt",
            description=f"**Remote:** `{remote_name}`\nWas soll dieses Element werden?",
            color=0x5865F2
        ),
        view=view
    )


@bot.tree.command(name="clear_session", description="Löscht deine aktuelle Menü Builder Session")
async def clear_session(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in sessions:
        del sessions[user_id]
        await interaction.response.send_message("✅ Session gelöscht!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Keine aktive Session!", ephemeral=True)


@bot.tree.command(name="show_menu", description="Zeigt dein aktuelles Menü")
async def show_menu(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in sessions or not sessions[user_id]["elements"]:
        await interaction.response.send_message("❌ Kein aktives Menü!", ephemeral=True)
        return
    
    element_list = "\n".join([f"• `{el['name']}` → {el['type'].upper()}" for el in sessions[user_id]["elements"]])
    await interaction.response.send_message(
        embed=discord.Embed(
            title="📋 Dein aktuelles Menü",
            description=element_list,
            color=0x5865F2
        ),
        view=AddMoreView(user_id),
        ephemeral=True
    )


# =============================================
# START
# =============================================
bot.run(BOT_TOKEN)
