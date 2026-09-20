# LinguaForge

Tutor local de inglês por texto com Vue 3, FastAPI, SQLite e Qwen3-4B-Instruct-2507 Q4_K_M executado por llama.cpp.

## Uso diário

Com o ambiente já preparado, execute em um terminal nativo do sistema:

```bash
cd ~/Repo/LinguaForge
./scripts/start_linguaforge.sh
```

Aguarde `LinguaForge disponível` e abra <http://127.0.0.1:8000>. O iniciador verifica os componentes locais, carrega o modelo, compila a interface e inicia a API. Não é necessário iniciar o Vite para uso normal. O navegador não é aberto automaticamente.

`Ctrl+C` encerra os processos iniciados pelo script. Serviços que já estavam em execução são preservados. Se a API já estiver aberta e o modelo estiver parado, o script inicia o modelo que falta. O log do modelo fica em `data/llama-server.log`.

A aplicação usa apenas `127.0.0.1:8000` (interface/API) e `127.0.0.1:8080` (modelo). O iniciador não instala dependências, não baixa modelos nem altera configuração global de GPU. O paliativo de `LD_LIBRARY_PATH` se aplica apenas ao processo do llama.cpp.

## Funcionalidades da V1

- Chats independentes com histórico local; criação, título editável e exclusão com confirmação.
- Correção em inglês, explicação em português e continuação opcional em inglês.
- `Settings → Enable Reply` controla a continuação. A preferência fica no navegador; desativar oculta Replies anteriores e impede a geração nos próximos turnos.
- `Translate` traduz entre inglês e português sem salvar conteúdo nos chats.
- `Enter` envia; `Shift+Enter` insere uma nova linha. Rascunhos ficam separados por chat enquanto a página está aberta.
- O tutor recebe as últimas 12 mensagens do chat. O restante do histórico permanece salvo, mas não é enviado ao modelo.

Os chats ficam em `data/chats.sqlite3`. Para backup, encerre a aplicação e copie esse arquivo. O modelo fica em `models/`; dados, modelos e dependências locais não são versionados.

## Ambiente de desenvolvimento

Pré-requisitos: Linux, Bash, `curl`, `setsid`, Python 3.12, `uv` e Node compatível com o Vite instalado (20.19+ ou 22.12+). O iniciador aceita Node no `PATH` e usa o `nvm` local como alternativa. As dependências e o modelo precisam estar preparados previamente.

Para preparar explicitamente as dependências de um checkout:

```bash
uv sync --dev
cd frontend
npm ci
```

Esses comandos podem baixar pacotes. Eles não baixam o modelo nem o backend llama.cpp. A instalação atual espera:

- `models/Qwen3-4B-Instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf`;
- `data/llama.cpp/b10978/cuda12.8/bin/llama-b10978/llama-server`;
- bibliotecas em `data/llama.cpp/b10978/cuda12.8/runtime/`.

Para diagnóstico separado, use `scripts/start_app.sh` (API + build Vue) e `scripts/start_llama_server.sh` (modelo). Para verificar pré-requisitos sem iniciar serviços: `scripts/start_app.sh --check`. O Vite de desenvolvimento pode ser iniciado em `frontend/` com `npm run dev`, usando proxy para a API em 8000.

## Validação

Na raiz do projeto:

```bash
uv run --no-sync pytest
```

No diretório `frontend/`:

```bash
npm test
npm run build
```

A suíte automatizada usa modelos simulados e bancos temporários. Os testes do iniciador também usam processos simulados e não carregam a GPU. Testes de resposta real do Qwen são separados dos testes determinísticos.

O [roteiro manual](docs/roteiro-testes-manuais-v1.md) também está disponível em [PDF](docs/roteiro-testes-manuais-v1.pdf). Para regenerar ambos:

```bash
uv run --no-sync python scripts/generate_manual_test_pdf.py
```

## Limites atuais

O modelo pode errar uma correção, interpretação ou informação mesmo quando o formato da resposta é válido. A validação determinística verifica estrutura e semelhança do texto; ela não comprova precisão pedagógica. Textos ou conversas que excedam a capacidade do modelo podem gerar erro controlado; respostas truncadas não são salvas como completas.

A V1 atual é executada a partir do repositório. Empacotamento em aplicativo/instalador e áudio ficam para etapas posteriores. A detecção de GPU dentro de ambientes integrados pode diferir do terminal nativo; execute o iniciador pelo terminal nativo já validado.
