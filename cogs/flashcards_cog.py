import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import json
import re
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
active_flashcards = {}

class FlashcardView(discord.ui.View):
    def __init__(self, bot: commands.Bot, interaction: discord.Interaction, cards: list):
        super().__init__(timeout=600.0)
        self.bot = bot
        self.interaction = interaction
        self.cards = cards
        self.author_id = interaction.user.id
        
        self.current_card = 0
        self.acertos = 0
        self.erros = 0
        self.nao_sabia_topicos = []
        self.is_flipped = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Estes flashcards não são seus!", ephemeral=True)
            return False
        return True

    async def start(self):
        """Inicia a sessão de flashcards, mostrando o primeiro card."""
        await self.show_card()

    def create_embed(self):
        """Cria o embed com base no estado atual do card (virado ou não)."""
        card_data = self.cards[self.current_card]
        
        if not self.is_flipped:
            embed = discord.Embed(
                title=f"Flashcard {self.current_card + 1}/{len(self.cards)}",
                description=f"**FRENTE:**\n\n# {card_data['frente']}",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title=f"Flashcard {self.current_card + 1}/{len(self.cards)}",
                description=f"**FRENTE:**\n\n# {card_data['frente']}\n\n---\n\n**VERSO:**\n\n## {card_data['verso']}",
                color=discord.Color.purple()
            )
        
        embed.set_footer(text=f"Acertos: {self.acertos} | Erros: {self.erros}")
        return embed

    def update_buttons(self):
        """Atualiza os botões visíveis com base no estado do card."""
        self.clear_items()
        if not self.is_flipped:
            flip_button = discord.ui.Button(label="Virar Card 🔄", style=discord.ButtonStyle.primary, custom_id="flip_card")
            flip_button.callback = self.flip_card_callback
            self.add_item(flip_button)
        else:
            correct_button = discord.ui.Button(label="Acertei ✅", style=discord.ButtonStyle.success, custom_id="assess_correct")
            correct_button.callback = self.assess_callback
            
            incorrect_button = discord.ui.Button(label="Errei ❌", style=discord.ButtonStyle.danger, custom_id="assess_incorrect")
            incorrect_button.callback = self.assess_callback

            unknown_button = discord.ui.Button(label="Não Sei 🤔", style=discord.ButtonStyle.secondary, custom_id="assess_unknown")
            unknown_button.callback = self.assess_callback

            self.add_item(correct_button)
            self.add_item(incorrect_button)
            self.add_item(unknown_button)

    async def show_card(self):
        """Função principal que monta e envia/edita a mensagem do card."""
        embed = self.create_embed()
        self.update_buttons()
        await self.interaction.edit_original_response(embed=embed, view=self)

    async def flip_card_callback(self, interaction: discord.Interaction):
        """Callback para o botão 'Virar Card'."""
        await interaction.response.defer()
        self.is_flipped = True
        await self.show_card()

    async def assess_callback(self, interaction: discord.Interaction):
        """Callback para os botões 'Acertei', 'Errei' e 'Não Sei'."""
        await interaction.response.defer()
        

        custom_id = interaction.data['custom_id']
        
        if custom_id == "assess_correct":
            self.acertos += 1
        elif custom_id == "assess_incorrect":
            self.erros += 1
        elif custom_id == "assess_unknown":
            self.erros += 1
            card_data = self.cards[self.current_card]
            review_topic = card_data.get('topico_para_revisao', 'Tópico não especificado.')
            if review_topic not in self.nao_sabia_topicos:
                self.nao_sabia_topicos.append(review_topic)

        self.current_card += 1
        self.is_flipped = False

        if self.current_card < len(self.cards):
            await self.show_card()
        else:
            await self.end_session()
            
    async def end_session(self):
        """Encerra a sessão e mostra o resultado final, incluindo os tópicos de revisão."""
        total = len(self.cards)
        percentual_acertos = (self.acertos / total) * 100 if total > 0 else 0
        
        final_embed = discord.Embed(
            title="🏁 Sessão de Flashcards Finalizada!",
            description=f"Ótimo trabalho! Você revisou **{total}** cards.",
            color=discord.Color.gold()
        )
        final_embed.add_field(name="Acertos ✅", value=f"**{self.acertos}**", inline=True)
        final_embed.add_field(name="Erros/Não Sabia ❌", value=f"**{self.erros}**", inline=True)
        final_embed.add_field(name="Aproveitamento", value=f"**{percentual_acertos:.2f}%**", inline=True)

        if self.nao_sabia_topicos:
            review_text = "\n".join(f"- {topic}" for topic in self.nao_sabia_topicos)
            final_embed.add_field(
                name="📚 Tópicos para reforçar o estudo:",
                value=review_text,
                inline=False
            )

        await self.interaction.edit_original_response(embed=final_embed, view=None)
        self.stop()

class FlashcardsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def generate_flashcards_with_gemini(self, tema, num_cards):
        prompt = f"""
        Aja como um especialista em memorização e criação de material de estudo para concursos.
        Crie {num_cards} flashcards sobre o tema: "{tema}".

        Para cada flashcard, forneça OBRIGATORIAMENTE os seguintes campos:
        - "frente": Deve ser uma pergunta direta ou um conceito a ser definido.
        - "verso": Deve ser a resposta direta e concisa para a "frente".
        - "topico_para_revisao": Um tópico de estudo específico e direcionado relacionado ao card.

        Retorne a resposta estritamente no seguinte formato JSON, dentro de um bloco de código JSON. Não inclua texto fora do bloco.
        
        Exemplo de formato:
        ```json
        [
          {{
            "frente": "Quais são os 5 princípios expressos da Administração Pública (LIMPE)?",
            "verso": "Legalidade, Impessoalidade, Moralidade, Publicidade e Eficiência.",
            "topico_para_revisao": "Princípios Expressos da Administração Pública (Art. 37 da CF/88)"
          }}
        ]
        ```
        """
        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text.strip()
            
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])', raw_text)
            if not json_match:
                print(f"ERRO: Nenhum JSON encontrado na resposta para flashcards sobre '{tema}'.")
                return None
            
            cleaned_response = next((group for group in json_match.groups() if group is not None), None)
            if not cleaned_response:
                print(f"ERRO: Bloco JSON vazio para flashcards sobre '{tema}'.")
                return None
            
            cards = json.loads(cleaned_response)
            return cards
        except Exception as e:
            print(f"Erro ao gerar flashcards: {e}")
            return None

    @app_commands.command(name="flashcards", description="Inicia uma sessão de revisão com flashcards gerados por IA.")
    @app_commands.describe(
        tema="O tema para os flashcards.",
        quantidade="O número de flashcards que deseja gerar (entre 3 e 20)."
    )
    async def flashcards(self, interaction: discord.Interaction, tema: str, quantidade: int):
        
        if not (3 <= quantidade <= 20):
            await interaction.response.send_message("Por favor, escolha uma quantidade de flashcards entre 3 e 20.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        cards = await self.generate_flashcards_with_gemini(tema, quantidade)
        
        if not cards or len(cards) < quantidade:
            await interaction.followup.send("Desculpe, não consegui gerar os flashcards no momento. A IA pode estar ocupada ou o tema é muito específico. Tente novamente.", ephemeral=True)
            return
            
        view = FlashcardView(self.bot, interaction, cards)
        await interaction.followup.send("Iniciando flashcards...", ephemeral=True)
        await view.start()


async def setup(bot: commands.Bot):
    await bot.add_cog(FlashcardsCog(bot))