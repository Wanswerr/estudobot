import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
from google.cloud import texttospeech
import asyncio
import os
import re
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

class SelecaoFormatoView(discord.ui.View):
    def __init__(self, author_id, topico, cog_ref):
        super().__init__(timeout=180.0)
        self.author_id = author_id
        self.topico = topico
        self.cog_ref = cog_ref

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Estes botões não são para você!", ephemeral=True)
            return False
        return True
    
    async def disable_and_confirm(self, interaction: discord.Interaction, message: str):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=message, view=self)

    @discord.ui.button(label="Texto 📄", style=discord.ButtonStyle.secondary)
    async def texto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_and_confirm(interaction, f"Ok! Gerando a explicação em texto sobre **{self.topico}**...")
        await self.cog_ref.gerar_explicacao_texto(interaction, self.topico)

    @discord.ui.button(label="Áudio 🎧", style=discord.ButtonStyle.secondary)
    async def audio_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice:
            await interaction.response.send_message("Você precisa estar em um canal de voz para que eu possa explicar em áudio!", ephemeral=True)
            return
        
        await self.disable_and_confirm(interaction, f"Ok! Vou entrar no seu canal de voz. Gerando e sintetizando o áudio sobre **{self.topico}**...")
        await self.cog_ref.gerar_explicacao_audio(interaction, self.topico)

class ExplicacaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        try:
            self.tts_client = texttospeech.TextToSpeechClient.from_service_account_json('google_credentials.json')
            print("Cliente Google Cloud TTS inicializado com sucesso.")
        except FileNotFoundError:
            print("ERRO: O arquivo 'google_credentials.json' não foi encontrado. A função de áudio não funcionará.")
            self.tts_client = None
        except Exception as e:
            print(f"ERRO ao inicializar o cliente Google Cloud TTS: {e}")
            self.tts_client = None

    async def obter_texto_explicativo(self, topico: str):
        prompt = f"""
        Aja como um narrador profissional e especialista no assunto.
        Explique de forma clara, didática e conversacional o seguinte tópico: "{topico}".
        Sua explicação deve ser fluida e agradável de ouvir. Para isso, você DEVE usar a linguagem SSML para adicionar pausas e naturalidade.
        - Use a tag <break time="700ms"/> para pausas mais longas entre parágrafos ou ideias principais.
        - Use a tag <break time="300ms"/> para pausas curtas, como após uma vírgula.
        - Envolva TODA a sua resposta final dentro de uma única tag <speak>.
        
        Exemplo:
        <speak>
        Claro! <break time="300ms"/> O Regulamento de Voo por Instrumentos, ou IFR, <break time="300ms"/> é um conjunto de regras que permite aos pilotos voar sem a necessidade de referências visuais externas. <break time="700ms"/> Isso é fundamental para operações noturnas ou em condições de baixa visibilidade.
        </speak>
        """
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"Erro ao gerar conteúdo com Gemini: {e}")
            return None

    def converter_texto_para_audio_google(self, texto_ssml: str):
        if not self.tts_client:
            return None

        texto_ssml = texto_ssml.strip()
        if not texto_ssml.startswith('<speak>'):
            texto_ssml = '<speak>' + texto_ssml
        if not texto_ssml.endswith('</speak>'):
            texto_ssml = texto_ssml + '</speak>'

        voice = texttospeech.VoiceSelectionParams(
            language_code="pt-BR", name="pt-BR-Wavenet-A"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            effects_profile_id=['headphone-class-device']
        )
        
        response = None
        try:
            print("Tentando sintetizar com SSML...")
            synthesis_input = texttospeech.SynthesisInput(ssml=texto_ssml)
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
        except Exception as e:
            print(f"AVISO: Falha ao sintetizar com SSML ({e}). Tentando novamente com texto puro.")
            try:
                print("Executando Plano B: Sintetizando com texto puro.")
                texto_puro = re.sub('<[^<]+?>', '', texto_ssml)
                
                synthesis_input = texttospeech.SynthesisInput(text=texto_puro)
                response = self.tts_client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
            except Exception as e_text:
                print(f"ERRO: Falha ao sintetizar até mesmo com texto puro: {e_text}")
                return None
        
        if response:
            filepath = "temp_audio.mp3"
            with open(filepath, "wb") as out:
                out.write(response.audio_content)
            print(f"Áudio salvo em: {filepath}")
            return filepath
        return None

    async def gerar_explicacao_texto(self, interaction: discord.Interaction, topico: str):
        texto_ssml = await self.obter_texto_explicativo(topico)
        if not texto_ssml:
            await interaction.followup.send("Desculpe, não consegui gerar o conteúdo da explicação.", ephemeral=True)
            return
            
        texto_limpo = re.sub('<[^<]+?>', '', texto_ssml)
        
        if len(texto_limpo) > 1900:
            texto_limpo = texto_limpo[:1900] + "\n\n... (explicação truncada)"

        embed = discord.Embed(title=f"Explicação sobre: {topico}", description=texto_limpo, color=discord.Color.blue())
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def gerar_explicacao_audio(self, interaction: discord.Interaction, topico: str):
        if not self.tts_client:
            await interaction.followup.send("Desculpe, a função de áudio não está configurada corretamente.", ephemeral=True)
            return

        texto_ssml = await self.obter_texto_explicativo(topico)
        if not texto_ssml:
            await interaction.followup.send("Desculpe, não consegui gerar o conteúdo da explicação.", ephemeral=True)
            return

        loop = asyncio.get_running_loop()
        audio_filepath = await loop.run_in_executor(None, self.converter_texto_para_audio_google, texto_ssml)

        if not audio_filepath:
            await interaction.followup.send("Desculpe, falhei ao tentar converter a explicação para áudio.", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        try:
            vc = await voice_channel.connect()
        except discord.ClientException:
            vc = interaction.guild.voice_client
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        except Exception as e:
            await interaction.followup.send(f"Não consegui me conectar ao canal de voz: {e}", ephemeral=True)
            if os.path.exists(audio_filepath): os.remove(audio_filepath)
            return

        await interaction.followup.send(f"Iniciando a explicação em áudio no canal `{voice_channel.name}`.", ephemeral=True)
        
        def after_playing(error):
            if error:
                print(f"Erro ao tocar o áudio: {error}")
            coro = vc.disconnect()
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Erro ao tentar desconectar: {e}")
            
            if os.path.exists(audio_filepath):
                os.remove(audio_filepath)
                print(f"Arquivo temporário '{audio_filepath}' deletado.")

        vc.play(discord.FFmpegPCMAudio(audio_filepath), after=after_playing)

    @app_commands.command(name="explique", description="Pede ao bot uma explicação sobre qualquer tópico.")
    @app_commands.describe(topico="O assunto que você quer que o bot explique.")
    async def explique(self, interaction: discord.Interaction, topico: str):
        view = SelecaoFormatoView(author_id=interaction.user.id, topico=topico, cog_ref=self)
        await interaction.response.send_message(
            f"Entendido! Você pediu uma explicação sobre **{topico}**. Como você prefere recebê-la?",
            view=view,
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ExplicacaoCog(bot))