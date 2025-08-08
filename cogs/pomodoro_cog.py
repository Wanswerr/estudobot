import discord
from discord.ext import commands
from discord import app_commands
import asyncio

active_pomodoros = {}

class PomodoroView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Este controle de Pomodoro não é seu!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="❌ Encerrar Sessão", style=discord.ButtonStyle.danger, custom_id="end_pomodoro")
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        task = active_pomodoros.get(self.author_id)
        if task:
            task.cancel()
        
        button.disabled = True
        button.label = "Sessão Encerrada"
        
        try:
            await interaction.response.edit_message(content="Esta sessão de Pomodoro foi encerrada pelo usuário.", embed=None, view=self)
        except discord.NotFound:
            await interaction.response.send_message("Sessão de Pomodoro encerrada.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao editar mensagem no encerramento: {e}")

class PomodoroCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def run_pomodoro_cycle(self, user: discord.User, message: discord.Message, foco: int, pausa_curta: int, pausa_longa: int, ciclos: int):
        for i in range(ciclos):
            try:
                embed = discord.Embed(
                    title="🍅 Sessão de Foco",
                    description=f"**Foco total por `{foco}` minutos!**\nSilencie as notificações e mergulhe nos estudos.",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Ciclo {i + 1} de {ciclos}")
                await message.edit(embed=embed)

                await asyncio.sleep(foco * 60)

                is_long_break = (i + 1) % 4 == 0 and i + 1 >= 4

                if is_long_break:
                    break_time = pausa_longa
                    embed = discord.Embed(
                        title="🎉 Pausa Longa!",
                        description=f"Excelente! Você completou 4 ciclos. Agora, uma pausa merecida de `{break_time}` minutos.",
                        color=discord.Color.green()
                    )
                else:
                    break_time = pausa_curta
                    embed = discord.Embed(
                        title="☕ Pausa Curta",
                        description=f"Bom trabalho! Hora de uma pausa rápida de `{break_time}` minutos.",
                        color=discord.Color.blue()
                    )
                
                embed.set_footer(text=f"Após o ciclo {i + 1} de {ciclos}")
                await message.edit(embed=embed)
                await message.channel.send(f"⏰ {user.mention}, sua pausa de `{break_time}` minutos começou!")

                await asyncio.sleep(break_time * 60)

                if i + 1 < ciclos:
                    await message.channel.send(f"💪 {user.mention}, a pausa terminou! Preparando para o próximo ciclo de foco.")
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                print(f"Sessão de Pomodoro para {user.name} foi cancelada.")
                break
        
        if active_pomodoros.get(user.id):
            final_embed = discord.Embed(
                title="🏁 Sessão de Pomodoro Concluída!",
                description="Parabéns por completar todos os ciclos! Você mandou muito bem.",
                color=discord.Color.gold()
            )
            try:
                await message.edit(embed=final_embed, view=None)
            except discord.NotFound:
                pass
        
        if user.id in active_pomodoros:
            del active_pomodoros[user.id]

    @app_commands.command(name="pomodoro", description="Inicia uma sessão de estudo com a técnica Pomodoro.")
    @app_commands.describe(
        foco="Tempo de foco em minutos (padrão: 25).",
        pausa_curta="Tempo da pausa curta em minutos (padrão: 5).",
        pausa_longa="Tempo da pausa longa em minutos, após 4 ciclos (padrão: 15).",
        ciclos="Número de ciclos de foco que deseja completar (padrão: 4)."
    )
    async def pomodoro(self, interaction: discord.Interaction, foco: int = 25, pausa_curta: int = 5, pausa_longa: int = 15, ciclos: int = 4):
        user_id = interaction.user.id
        if user_id in active_pomodoros:
            await interaction.response.send_message("Você já tem uma sessão de Pomodoro ativa! Encerre-a antes de iniciar uma nova.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        view = PomodoroView(author_id=user_id)
        
        initial_embed = discord.Embed(title="🍅 Preparando seu Pomodoro...", color=discord.Color.orange())
        message = await interaction.followup.send(embed=initial_embed, view=view, wait=True)

        task = self.bot.loop.create_task(self.run_pomodoro_cycle(interaction.user, message, foco, pausa_curta, pausa_longa, ciclos))
        active_pomodoros[user_id] = task

async def setup(bot: commands.Bot):
    await bot.add_cog(PomodoroCog(bot))