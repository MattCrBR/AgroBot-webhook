# AgroBot — Webhook do WhatsApp

Assistente de WhatsApp que recebe a foto de uma praga do milho enviada pelo produtor e devolve, em linguagem simples, a identificação e o manejo recomendado.

Este repositório é a **API do projeto**: recebe as mensagens do WhatsApp (através da Evolution API), aplica filtros, chama o pipeline de análise e responde ao produtor.

> **Estado atual:** o pipeline de análise (qualidade da foto, classificador, base de conhecimento e LLM) está com **funções de teste (mocks)** em `pipeline.py`. O diagnóstico devolvido é fixo e controlado pelo arquivo `.env`. Os módulos reais vão substituir essas funções, sem mudar o resto do fluxo.

---

## Como funciona

```
Produtor (WhatsApp)
      │
      ▼
Evolution API (Docker) ──► ngrok ──► Webhook FastAPI (este projeto)
      ▲                                       │
      │                                       ▼
      └────────── resposta ◄────────── pipeline de análise
```

1. O produtor manda texto ou foto para o número conectado.
2. A Evolution API avisa o webhook (`POST /webhook`).
3. O webhook descarta o que não interessa (grupos, números fora da lista, mensagens antigas, repetidas ou do próprio bot) e responde `200` na hora.
4. O processamento roda em segundo plano: se for foto, ela é baixada e analisada; se for texto ou outro tipo de mensagem, o bot pede uma foto.
5. A resposta volta pela Evolution API, com um pequeno atraso para parecer natural.

### Arquivos

| Arquivo | Para que serve |
|---|---|
| `main.py` | FastAPI e o endpoint `/webhook` |
| `handlers.py` | Filtros dos eventos, tratamento das mensagens e feedback |
| `evolution.py` | Chamadas à Evolution API (enviar texto, baixar imagem) |
| `pipeline.py` | Pipeline de análise: mocks das etapas + roteador de confiança |
| `config.py` | Leitura do `.env` e constantes |
| `docker-compose.yml` | Evolution API + Postgres + Redis |
| `.env.example` | Modelo do arquivo de configuração |

---

## Pré-requisitos

- **Python 3.10 ou superior**
- **Docker Desktop** (no Windows usa o WSL2; a virtualização precisa estar habilitada na BIOS)
- **Git**
- **Conta gratuita no ngrok** (ngrok.com), com o *authtoken* em mãos
- **Um WhatsApp para conectar** (veja "Observações para a demonstração")

---

## Passo a passo

### 1. Baixar o projeto e configurar o `.env`

```powershell
git clone https://github.com/MattCrBR/agrobot-webhook.git
cd agrobot-webhook
copy .env.example .env
```

(Linux/macOS: `cp .env.example .env`)

Abra o `.env` e ajuste:

- `EVOLUTION_API_KEY`: qualquer texto longo e aleatório (no PowerShell, `[guid]::NewGuid()` gera um). É a "senha" da Evolution API.
- `ALLOWED_NUMBERS`: o número do WhatsApp que vai conversar com o bot, no formato `55` + DDD + número, sem `+`, espaços ou traços (ex.: `5511999999999`). Para mais de um, separe por vírgula.

O mesmo `.env` é lido pelo webhook e pelo Docker, então a chave só precisa ser escrita uma vez.

### 2. Subir a Evolution API

Abra o **Docker Desktop** e espere ele terminar de iniciar. Depois, na pasta do projeto:

```powershell
docker compose up -d
docker compose ps
```

Os três serviços (`agrobot-evolution`, `agrobot-postgres`, `agrobot-redis`) devem aparecer como rodando. Na primeira vez, o download das imagens demora um pouco.

### 3. Criar a instância e conectar o WhatsApp

Troque `SUA_CHAVE` pela `EVOLUTION_API_KEY` do seu `.env`:

```powershell
$headers = @{ "Content-Type" = "application/json"; "apikey" = "SUA_CHAVE" }
$body = @{ instanceName = "agrobot"; qrcode = $true; integration = "WHATSAPP-BAILEYS" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/instance/create" -Method Post -Headers $headers -Body $body
```

Depois abra **http://localhost:8080/manager** no navegador (ele pode pedir a URL `http://localhost:8080` e a chave), clique na instância `agrobot` e escaneie o QR Code:

> No celular: WhatsApp → **Aparelhos conectados** → **Conectar um aparelho**.

O QR Code vale por cerca de 1 minuto. Se a instância ficar em *connecting* (laranja), gere um QR novo e escaneie na hora. Quando ficar **connected**, está pronto.

### 4. Preparar o ambiente Python

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

(Linux/macOS: `source venv/bin/activate`. Se o PowerShell reclamar de permissão para rodar scripts, use antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.)

### 5. Subir o webhook

```powershell
uvicorn main:app --reload --port 8001
```

Abra **http://localhost:8001**: deve aparecer `{"status": "AgroBot webhook online"}`. Deixe esse terminal aberto.

### 6. Expor o webhook com o ngrok

Em **outro terminal**:

```powershell
ngrok config add-authtoken SEU_TOKEN
ngrok http 8001
```

(O `add-authtoken` só é necessário na primeira vez.) Copie o endereço que aparece em *Forwarding*, algo como `https://xxxx.ngrok-free.dev`. Deixe esse terminal aberto também.

### 7. Apontar a Evolution API para o webhook

Troque `SUA_CHAVE` e a URL do ngrok. **A URL precisa terminar em `/webhook`:**

```powershell
$headers = @{ "Content-Type" = "application/json"; "apikey" = "SUA_CHAVE" }
$body = @{
  webhook = @{
    enabled = $true
    url = "https://SEU-ENDERECO.ngrok-free.dev/webhook"
    webhookByEvents = $false
    events = @("MESSAGES_UPSERT")
  }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8080/webhook/set/agrobot" -Method Post -Headers $headers -Body $body
```

Para conferir o que ficou salvo:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/webhook/find/agrobot" -Method Get -Headers @{ "apikey" = "SUA_CHAVE" }
```

Se o endereço do ngrok mudar (acontece quando se usa um endereço temporário), repita este passo com o novo.

### 8. Testar

No WhatsApp, abra a conversa com **você mesmo** (o chat "Você") e envie:

1. Um texto, como "oi": o bot responde pedindo uma foto.
2. Uma foto qualquer: o bot responde com o diagnóstico de teste, o aviso e a pergunta "Acertei?".
3. Responda 👍 ou 👎: o bot agradece e o retorno é gravado em `feedback.jsonl`.

No terminal do `uvicorn` aparecem linhas curtas como `mensagem recebida | tipo=imageMessage | de=***9999`. O texto das mensagens e o número completo **não** são registrados no log.

---

## Testando os caminhos do pipeline

Enquanto o pipeline é de teste, o resultado é decidido por estas variáveis do `.env`:

| `MOCK_CONFIANCA` | `MOCK_FOTO_OK` | O que o bot responde |
|---|---|---|
| `0.85` | `true` | Diagnóstico direto, com aviso e pergunta de feedback |
| `0.65` | `true` | "Pode ser..., mas não tenho certeza" e pede outra foto |
| `0.30` | `true` | Encaminha o produtor à Casa da Agricultura |
| `0.85` | `false` | Pede outra foto (qualidade ruim) |

`MOCK_PRAGA` aceita `lagarta-do-cartucho`, `lagarta-da-espiga`, `vaquinha` ou `milho-saudavel`.

**Depois de mudar o `.env`, pare o `uvicorn` (`Ctrl+C`) e suba de novo.** O reinício automático só observa os arquivos `.py`.

---

## Rotina do dia a dia

1. Abrir o Docker Desktop e rodar `docker compose up -d`.
2. Terminal 1: `venv\Scripts\activate` e `uvicorn main:app --reload --port 8001`.
3. Terminal 2: `ngrok http 8001`.
4. Se o endereço do ngrok mudou, refazer o passo 7.

Para desligar: `Ctrl+C` nos dois terminais e `docker compose down`. Os dados da instância ficam guardados, então o WhatsApp continua conectado na próxima vez.

---

## Problemas comuns

| Sintoma | Causa provável e solução |
|---|---|
| Docker Desktop: "Virtualization support not detected" | Virtualização desligada. Veja em Gerenciador de Tarefas → Desempenho → CPU. Se estiver desabilitada, ative Intel VT-x / SVM na BIOS. |
| `401 Unauthorized` ao chamar a Evolution | A chave do comando não é a mesma do `EVOLUTION_API_KEY` do `.env`. Se mudou a chave depois de subir os containers, rode `docker compose up -d` de novo. |
| No `curl` do PowerShell dá erro com `-X` e `-H` | No PowerShell, `curl` é um apelido de outro comando. Use `Invoke-RestMethod` (como neste README) ou `curl.exe`. |
| Instância presa em *connecting* | O QR Code expirou. Gere outro no `/manager` e escaneie na hora. |
| `405 Method Not Allowed` no terminal do `uvicorn` | A URL salva na Evolution não termina em `/webhook`. Refaça o passo 7. |
| Chegam mensagens, mas o bot não responde nada | O número da conversa não está em `ALLOWED_NUMBERS`, ou o `.env` foi editado sem reiniciar o `uvicorn`. |
| O bot ignora mensagens novas | O relógio do computador está adiantado mais de 2 minutos (as mensagens parecem "antigas"). Sincronize a hora do Windows. |
| Logo ao reconectar, o terminal enche de eventos | É o acúmulo de mensagens de quando a instância ficou desligada. O webhook descarta o que é antigo. Se demorar, rode `docker compose restart evolution-api`. |
| `ImportError` ao subir o `uvicorn` | O ambiente virtual não está ativo, ou faltou `pip install -r requirements.txt`. |

Para ver mais detalhes no terminal, coloque `LOG_LEVEL=DEBUG` no `.env` e reinicie o `uvicorn`.

---

## Observações para a demonstração

- **Uma instância por número.** Se duas instâncias da Evolution (a sua e a do colega) estiverem conectadas ao mesmo número ao mesmo tempo, as duas respondem e o usuário recebe a mensagem em dobro. Deixe só uma ligada.
- **Cada computador precisa da própria instância.** Quem rodar no notebook precisa criar a instância (passo 3) e escanear o QR Code com o WhatsApp que vai usar, além de ter a própria conta no ngrok.
- **Outras pessoas conversarem com o bot:** coloque o número delas em `ALLOWED_NUMBERS` (separado por vírgula).
- A Evolution API é uma solução **não oficial** (conecta como um aparelho vinculado ao WhatsApp). Use um número que possa correr o pequeno risco de bloqueio.

---

## Limitações conhecidas

- A Meta Cloud API (oficial) foi testada e descartada: a conta de teste recebeu o erro 130497 (envio para o Brasil restrito).
- A lista de mensagens já processadas, o último diagnóstico de cada número e as mensagens enviadas pelo bot ficam **só em memória**: somem quando o servidor reinicia.
- O feedback 👍/👎 vale para o último diagnóstico enviado a cada número.
- Reações do WhatsApp (emoji em cima de uma mensagem) são ignoradas; o feedback precisa ser digitado como mensagem.
- Enquanto o número do bot for um número pessoal, o bot também reage às mensagens que você digita manualmente em conversas de números que estão em `ALLOWED_NUMBERS`.
- Quando o bot ficar offline, as mensagens recebidas nesse período não são respondidas (o que tem mais de 2 minutos é descartado).