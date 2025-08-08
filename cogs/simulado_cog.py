import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import demjson3 as demjson
import re
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
active_simulados = {}

class ResultadosPaginadosView(discord.ui.View):
    def __init__(self, author_id, state):
        super().__init__(timeout=300.0)
        self.author_id = author_id
        self.state = state
        self.current_page = 0
        self.total_pages = len(state['questoes'])
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Este gabarito não é seu!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == self.total_pages - 1

    def create_page_embed(self):
        q = self.state['questoes'][self.current_page]
        score = self.state['score']
        
        resposta_correta_letra = q['resposta']
        resposta_dada_letra = self.state['respostas_usuario'][self.current_page]

        texto_resposta_dada = q['opcoes'].get(resposta_dada_letra, "N/A")
        texto_resposta_correta = q['opcoes'].get(resposta_correta_letra)

        if resposta_dada_letra == resposta_correta_letra:
            cor_embed = discord.Color.green()
            resultado_texto = (
                f"✅ **Sua resposta:**\n> {resposta_dada_letra}) {texto_resposta_dada}\n\n"
                f"**Resultado:** Correto!\n\n"
                f"**Fonte:**\n> *{q.get('fonte', 'Fonte não informada pela IA.')}*"
            )
        else:
            cor_embed = discord.Color.red()
            resultado_texto = (
                f"❌ **Sua resposta:**\n> {resposta_dada_letra}) {texto_resposta_dada}\n\n"
                f"✔️ **Resposta correta:**\n> {resposta_correta_letra}) {texto_resposta_correta}\n\n"
                f"💡 **Justificativa:**\n> *{q.get('justificativa', 'Justificativa não fornecida.')}*\n\n"
                f"📚 **Para revisar:**\n> *{q.get('topico_para_revisao', 'Tópico de revisão não informado.')}*"
            )

        embed = discord.Embed(
            title=f"Questão {self.current_page + 1}: {q['materia']}",
            description=f"**Enunciado:**\n> {q['pergunta']}\n\n{resultado_texto}",
            color=cor_embed
        )
        embed.set_footer(text=f"Questão {self.current_page + 1}/{self.total_pages}  |  Pontuação Final: {score}/{self.total_pages}")
        return embed

    @discord.ui.button(label="<< Anterior", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        embed = self.create_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Próxima >>", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        embed = self.create_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Fechar", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        self.stop()
        await interaction.response.edit_message(content="Gabarito interativo fechado.", embed=None, view=self)

class SimuladoView(discord.ui.View):
    def __init__(self, author_id, on_finish_callback):
        super().__init__(timeout=300.0)
        self.author_id = author_id
        self.on_finish_callback = on_finish_callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Este simulado não é seu!", ephemeral=True)
            return False
        return True
    
    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def button_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "A")
    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def button_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "B")
    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def button_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "C")
    @discord.ui.button(label="D", style=discord.ButtonStyle.secondary)
    async def button_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_answer(interaction, "D")

    async def process_answer(self, interaction: discord.Interaction, answer: str):
        user_id = interaction.user.id
        simulado_state = active_simulados.get(user_id)
        if not simulado_state:
            await interaction.response.edit_message(content="Este simulado parece ter expirado ou foi encerrado.", view=None)
            return

        simulado_state["respostas_usuario"].append(answer)
        simulado_state["questao_atual"] += 1

        if simulado_state["questao_atual"] < len(simulado_state["questoes"]):
            next_question = simulado_state["questoes"][simulado_state["questao_atual"]]
            embed = self.create_question_embed(next_question, simulado_state["questao_atual"], len(simulado_state["questoes"]))
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            self.disable_all_buttons()
            await interaction.response.edit_message(content="🎉 **Simulado Finalizado!**\nGerando seu gabarito interativo...", embed=None, view=self)
            await self.on_finish_callback(interaction)
    
    def create_question_embed(self, question_data, current_index, total_questions):
        opcoes_texto = "\n".join([f"**{letra})** {texto}" for letra, texto in question_data['opcoes'].items()])
        embed = discord.Embed(title=f"Questão {current_index + 1}/{total_questions} | {question_data['materia']}", description=f"**{question_data['pergunta']}**\n\n{opcoes_texto}", color=discord.Color.purple())
        embed.set_footer(text=f"Eixo: {question_data['eixo']}")
        return embed

class SimuladoAICog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def generate_questions_with_gemini(self, tema, num_questoes):
        prompt = f"""
        Aja como um especialista na criação de questões para o Concurso Nacional Unificado (CNU) do Brasil. Crie {num_questoes} questões de múltipla escolha (A, B, C, D) sobre o seguinte tema: "{tema}".
        As questões devem ser desafiadoras e no estilo de bancas como Cesgranrio.

        Para cada questão, forneça OBRIGATORIAMENTE os seguintes campos:
        - "justificativa": Explicação concisa do porquê a alternativa correta é a certa.
        - "fonte": A base legal ou teórica para a questão (ex: "Art. 37 da Constituição Federal de 1988").
        - "topico_para_revisao": Um tópico de estudo específico para o usuário que errar a questão (ex: "Princípios Expressos da Administração Pública").

        Retorne a resposta estritamente no seguinte formato JSON, dentro de um bloco de código JSON.
        
        Exemplo de formato:
        ```json
        [
          {{
            "eixo": "Eixo Temático", "materia": "Matéria", "pergunta": "Pergunta.",
            "opcoes": {{"A": "Opção A.", "B": "Opção B.", "C": "Opção C.", "D": "Opção D."}},
            "resposta": "A", "justificativa": "Justificativa.", "fonte": "Fonte.", "topico_para_revisao": "Tópico."
          }}
        ]
        ```
        """
        raw_text = ""
        try:
            response = await self.model.generate_content_async(prompt)
            raw_text = response.text

            json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\])', raw_text)
            
            if not json_match:
                print("ERRO: Nenhum bloco JSON válido foi encontrado na resposta da IA.")
                print("--- Resposta Recebida ---\n", raw_text, "\n-------------------------")
                return None

            cleaned_response = next((group for group in json_match.groups() if group is not None), None)

            if not cleaned_response:
                print("ERRO: Bloco JSON encontrado, mas estava vazio.")
                return None
            questions = demjson.decode(cleaned_response)
            return questions
        except demjson.JSONDecodeError as e:
            print(f"Erro ao parsear o JSON (demjson) da Gemini: {e}")
            print("--- Resposta que causou o erro ---\n", raw_text, "\n---------------------------------")
            return None
        except Exception as e:
            print(f"Um erro inesperado ocorreu: {type(e).__name__} - {e}")
            return None

    async def show_final_results_paginated(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        state = active_simulados.pop(user_id, None)
        if not state:
            await interaction.followup.send("Não foi possível encontrar os dados do seu simulado.", ephemeral=True)
            return
        score = 0
        for i, q in enumerate(state['questoes']):
            if i < len(state['respostas_usuario']) and state['respostas_usuario'][i] == q['resposta']:
                score += 1
        state['score'] = score
        view = ResultadosPaginadosView(author_id=user_id, state=state)
        view.update_buttons()
        embed = view.create_page_embed()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message
    @app_commands.command(name="simulado", description="Inicia um simulado gerado por IA sobre um tema do CNU.")
    @app_commands.describe(tema="O tema para o simulado.", quantidade="O número de questões (entre 3 e 10).")
    async def simulado(self, interaction: discord.Interaction, tema: str, quantidade: int):
        user_id = interaction.user.id
        if user_id in active_simulados:
            await interaction.response.send_message("Você já tem um simulado em andamento!", ephemeral=True)
            return
        if not (3 <= quantidade <= 10):
            await interaction.response.send_message("Por favor, escolha uma quantidade de questões entre 3 e 10.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        questoes = await self.generate_questions_with_gemini(tema, quantidade)
        if not questoes or len(questoes) != quantidade:
            await interaction.followup.send("Desculpe, não consegui gerar as questões no momento. Verifique o console para mais detalhes.", ephemeral=True)
            return
        active_simulados[user_id] = {"questoes": questoes, "respostas_usuario": [], "questao_atual": 0, "tema": tema}
        view = SimuladoView(author_id=user_id, on_finish_callback=self.show_final_results_paginated)
        primeira_questao = active_simulados[user_id]["questoes"][0]
        embed = view.create_question_embed(primeira_questao, 0, quantidade)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(SimuladoAICog(bot))