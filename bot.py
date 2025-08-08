import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID_STR = os.getenv("GUILD_ID")

if not DISCORD_TOKEN:
    print("ERRO CRÍTICO: A variável de ambiente 'DISCORD_TOKEN' não foi encontrada.")
    print("Verifique se você criou o arquivo .env e o preencheu corretamente.")
    exit()

GUILD_ID = None
if GUILD_ID_STR:
    try:
        GUILD_ID = int(GUILD_ID_STR)
    except ValueError:
        print(f"AVISO: O GUILD_ID '{GUILD_ID_STR}' no arquivo .env não é um número válido. A sincronização de comandos será global.")
else:
    print("AVISO: A variável de ambiente 'GUILD_ID' não foi definida no arquivo .env. A sincronização de comandos será global.")

class CNUGeminiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True

        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        print("Carregando cogs...")

        cogs_a_carregar = [
            "cogs.simulado_cog",
            "cogs.explicacao_cog",
            "cogs.pomodoro_cog",
            "cogs.flashcards_cog",
        ]

        for cog in cogs_a_carregar:
            try:
                await self.load_extension(cog)
                print(f"-> Cog '{cog}' carregado com sucesso.")
            except Exception as e:
                print(f"!!! Falha ao carregar o cog '{cog}': {e}")

        print("Sincronizando comandos de barra...")
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            print(f"Sincronizados {len(synced)} comandos para o servidor {GUILD_ID}.")
        else:
            print("AVISO: Sincronizando globalmente.")
            synced = await self.tree.sync()
            print(f"Sincronizados {len(synced)} comandos globalmente.")

    async def on_ready(self):
        print("-" * 50)
        print(f'Bot conectado como {self.user.name} (ID: {self.user.id})')
        print(f'Pronto para ajudar em {len(self.guilds)} servidores.')
        print("-" * 50)
        await self.change_presence(activity=discord.Game(name="com os estudos | /pomodoro"))

if __name__ == "__main__":
    bot = CNUGeminiBot()
    bot.run(DISCORD_TOKEN)
