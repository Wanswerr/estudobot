# CNU-Bot: Seu Assistente de Estudos para o Concurso Nacional Unificado

![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![Google Cloud](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)

## 📖 Sobre o Projeto

O **CNU-Bot** é um assistente de estudos multifuncional para o Discord, projetado especificamente para auxiliar candidatos do **Concurso Nacional Unificado (CNU)**. Utilizando o poder da IA generativa do Google Gemini, o bot oferece uma suíte de ferramentas interativas para otimizar a preparação, desde a teoria até a prática.

Este projeto foi criado para ser um companheiro de estudos 360°, que planeja, ensina, testa e motiva.

## ✨ Funcionalidades Principais

O bot opera com comandos de barra (`/`) для uma experiência de usuário moderna e intuitiva.

| Comando | Parâmetros | Descrição |
| :--- | :--- | :--- |
| **`/simulado`** | `tema`, `quantidade` | Inicia um simulado interativo com questões de múltipla escolha geradas em tempo real pela IA. Ao final, apresenta um gabarito paginado com justificativas, fontes e tópicos para revisão. |
| **`/flashcards`** | `tema`, `quantidade` | Inicia uma sessão de memorização ativa com flashcards. O bot apresenta a "frente" e o usuário vira o card para se autoavaliar com "Acertei", "Errei" ou "Não Sei", recebendo um relatório de tópicos a reforçar. |
| **`/explique`** | `topico` | Solicita uma explicação aprofundada sobre qualquer assunto. O bot oferece a explicação em formato de **Texto** no chat ou em **Áudio**, narrando o conteúdo diretamente no canal de voz do usuário com uma voz natural. |
| **`/pomodoro`** | `foco`, `pausa_curta`, `pausa_longa`, `ciclos` | Inicia uma sessão de estudo com a técnica Pomodoro. O bot gerencia os tempos de foco e pausa, notificando o usuário a cada etapa através de uma mensagem interativa com um botão para encerrar a sessão. |

## 🚀 Começando

Siga os passos abaixo para configurar e rodar o bot no seu próprio servidor.

### Pré-requisitos

Antes de começar, você precisará de:

1.  **Python 3.10 ou superior.**
2.  **FFmpeg:** Essencial para a funcionalidade de áudio do comando `/explique`.
    * **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`
    * **Windows:** Baixe em [ffmpeg.org](https://ffmpeg.org/download.html) e adicione o `bin` da pasta ao seu PATH do sistema.
3.  **Chaves de API:**
    * **Token do Bot do Discord:** Crie uma aplicação no [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications).
    * **Chave de API do Gemini:** Obtenha no [Google AI Studio](https://aistudio.google.com/).
    * **Credenciais do Google Cloud:** Um arquivo `google_credentials.json` de uma Conta de Serviço com a API "Cloud Text-to-Speech" ativada. Obtenha no [Google Cloud Console](https://console.cloud.google.com/).

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-seu-repositorio>
    cd CNU-Gemini-Bot
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Para Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure suas chaves:**
    * Renomeie o arquivo de credenciais do Google Cloud para `google_credentials.json` e coloque-o na pasta raiz do projeto.
    * Preencha o arquivo `.env` com suas chaves:
        ```python
        # .env
        DISCORD_TOKEN = "SEU_TOKEN_DO_DISCORD_AQUI"
        GEMINI_API_KEY = "SUA_CHAVE_DE_API_DO_GEMINI_AQUI"
        ```

5.  **Configure o Servidor de Testes:**
    * No arquivo `bot.py`, altere a variável `GUILD_ID` para o ID do seu servidor do Discord. Isso fará com que os comandos sejam atualizados instantaneamente durante o desenvolvimento.
        ```python
        # bot.py
        GUILD_ID = 123456789012345678 # <--- COLOQUE O ID DO SEU SERVIDOR AQUI
        ```

### Executando o Bot

Com o ambiente virtual ativado, inicie o bot:
```bash
python bot.py