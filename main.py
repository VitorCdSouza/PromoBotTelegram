from telethon import TelegramClient, events
import requests
from dotenv import load_dotenv
import os
import time
import asyncio
import json

# ---- VARIÁVEIS GLOBAIS ----
api_id = None
api_hash = None
bot_token = None
user_id = None
filtros = []
PROMO_CHATS = []
me = None
ultimo_reload = time.time()
ENV_FILE_PATH = '.env'
FILTROS_FILE_PATH = 'filtros.json'

# ---- FUNÇÕES DE CONFIGURAÇÃO E AJUDA ----
def carregar_env():
    """Carrega ou recarrega as variáveis de ambiente do arquivo .env."""
    global api_id, api_hash, bot_token, user_id, PROMO_CHATS
    load_dotenv(ENV_FILE_PATH)
    
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    user_id = int(os.getenv("USER_ID"))

    promo_chats_str = os.getenv("PROMO_CHATS", "")
    PROMO_CHATS = [int(chat_id.strip()) for chat_id in promo_chats_str.split(",") if chat_id.strip()]

    print("Variáveis de ambiente carregadas/recarregadas.")
    print(f"Chats monitorados: {PROMO_CHATS}")


def carregar_filtros():
    """Carrega filtros do arquivo JSON (ou cria vazio se não existir)."""
    global filtros
    if not os.path.exists(FILTROS_FILE_PATH):
        # cria arquivo vazio
        with open(FILTROS_FILE_PATH, "w") as f:
            json.dump([], f)
        filtros = []
        print("Arquivo de filtros não encontrado, criado novo vazio.")
        return

    try:
        with open(FILTROS_FILE_PATH, "r") as f:
            filtros = json.load(f)
            if not isinstance(filtros, list):
                raise ValueError("Formato inválido no filtros.json")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Erro ao ler {FILTROS_FILE_PATH}: {e}")
        filtros = []
        salvar_filtros()
    print(f"Filtros carregados: {filtros}")


def salvar_filtros():
    """Salva a lista de filtros no arquivo JSON."""
    try:
        with open(FILTROS_FILE_PATH, "w") as f:
            json.dump(filtros, f)
        print(f"Filtros salvos no arquivo {FILTROS_FILE_PATH}: {filtros}")
    except Exception as e:
        print(f"Erro ao salvar filtros: {e}")


def enviar_bot(msg: str):
    """Envia uma mensagem para o seu bot pessoal."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": user_id, "text": msg}
        )
    except Exception as e:
        print(f"Erro ao enviar mensagem via bot: {e}")

# ---- INICIALIZAÇÃO DO CLIENTE ----
carregar_env()
carregar_filtros()
client = TelegramClient('sessao', api_id, api_hash)

# ---- HANDLER PRINCIPAL DE MENSAGENS ----
@client.on(events.NewMessage)
async def main_handler(event):
    global filtros, ultimo_reload
    
    if time.time() - ultimo_reload > 30:
        carregar_env()
        carregar_filtros()
        ultimo_reload = time.time()

    if event.is_private:
        msg = event.raw_text.strip().lower()

        if msg.startswith("/add "):
            novo_filtro = msg[5:].strip()
            if novo_filtro and novo_filtro not in filtros:
                filtros.append(novo_filtro)
                salvar_filtros()
                enviar_bot(f"✅ Filtro '{novo_filtro}' adicionado.\nFiltros atuais: {', '.join(filtros)}")
            else:
                enviar_bot(f"⚠️ Filtro inválido ou já existe.\nFiltros atuais: {', '.join(filtros)}")
            return

        elif msg.startswith("/remove "):
            filtro_a_remover = msg[8:].strip()
            if filtro_a_remover in filtros:
                filtros.remove(filtro_a_remover)
                salvar_filtros()
                enviar_bot(f"✅ Filtro '{filtro_a_remover}' removido.\nFiltros atuais: {', '.join(filtros)}")
            else:
                enviar_bot(f"⚠️ Filtro '{filtro_a_remover}' não encontrado.\nFiltros atuais: {', '.join(filtros)}")
            return

        elif msg == "/list":
            if filtros:
                enviar_bot(f"📋 Filtros atuais: {', '.join(filtros)}")
            else:
                enviar_bot("📋 Nenhum filtro configurado.")
            return
        
    # --- LÓGICA PARA MONITORAR GRUPOS DE PROMOÇÃO ---
    if event.chat_id in PROMO_CHATS:
        if event.sender_id == me.id:
            return

        texto = event.raw_text.lower()
        if any(f in texto for f in filtros):
            chat = await event.get_chat()
            titulo_chat = chat.title if hasattr(chat, 'title') else 'Desconhecido'
            
            enviar_bot(
                f"📌 Promo encontrada!\n\n"
                f"{event.raw_text}\n\n"
                f"👉 De: {titulo_chat}"
            )

async def main():
    """Função principal para iniciar o bot."""
    global me
    
    await client.start(bot_token=bot_token if os.getenv("IS_BOT", "false").lower() == "true" else None)
    me = await client.get_me()
    print(f"Conectado como: {me.first_name}")
    
    enviar_bot("📌 Bot iniciado e rodando!")
    print("✅ Bot rodando... (CTRL+C pra parar)")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
