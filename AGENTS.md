# LinguaForge - Instruções para Codex

## Objetivo

LinguaForge é um assistente local de aprendizado de inglês com IA.

O projeto deve priorizar:

- execução local;
- privacidade;
- arquitetura modular;
- uso eficiente de GPU;
- baixo acoplamento entre núcleo, IA, áudio e interface;
- código simples e testável;
- validação incremental da utilidade pedagógica antes de aumentar a complexidade.

## Ambiente atual

Sistema:

- Pop!_OS 24.04 LTS
- Python 3.12
- `uv` para gerenciamento do projeto
- Git
- NVIDIA RTX 4060 Laptop
- aproximadamente 8 GB de VRAM

Diretório do projeto:

`~/Repo/LinguaForge`

## Gerenciamento Python

Use `uv`.

Preferir:

`uv add <pacote>`

para dependências normais.

Preferir:

`uv add --dev <pacote>`

para dependências de desenvolvimento.

Para executar testes:

`uv run --no-sync pytest`

Não usar `pip install` diretamente sem necessidade explícita.

## Estrutura atual

Código principal:

`src/linguaforge/`

Testes:

`tests/`

Dados locais:

`data/`

Modelos locais:

`models/`

O projeto já possui um executável:

`uv run linguaforge`

## Estado arquitetural atual

Já existem:

- `main.py`;
- configuração central;
- modelo de runtime;
- testes automatizados.

A configuração existente usa a classe `Config`.

O dispositivo configurado pode ser:

- `auto`;
- `cpu`;
- `cuda`.

O runtime efetivo deve usar apenas:

- `cpu`;
- `cuda`.

A resolução entre configuração e runtime deve permanecer separada da detecção real de hardware.

## Escopo de versões

### V1 - Tutor por texto

A primeira versão do LinguaForge será exclusivamente textual.

Fluxo principal:

- o usuário escreve em inglês;
- o tutor identifica e corrige erros;
- o tutor fornece uma versão corrigida;
- o tutor explica os erros em português;
- o tutor pode continuar a conversa em inglês; `Enable Reply` controla essa continuação.

Objetivo da V1:

Validar a utilidade pedagógica do tutor antes de adicionar voz.

Não implementar na V1:

- captura de microfone;
- STT;
- TTS;
- `faster-whisper`;
- pipeline de áudio;
- streaming de áudio.

### V2 - Voz

Somente após validação da V1 serão avaliados:

- captura de microfone;
- `faster-whisper` como backend preferencial de STT;
- transcrição;
- síntese de voz;
- conversação por voz.

## Regras arquiteturais

Não acoplar o núcleo do LinguaForge a uma interface específica.

O núcleo deve poder funcionar futuramente com:

- CLI;
- interface desktop;
- API;
- outras interfaces.

Manter separadas sempre que possível:

1. configuração;
2. runtime;
3. IA / LLM;
4. reconhecimento de voz;
5. síntese de voz;
6. lógica pedagógica;
7. interface.

Evitar abstrações prematuras.

Preferir código pequeno, explícito e testável.

## Tutor textual - contrato inicial

A V1 deve suportar conceitualmente este fluxo:

Entrada:

- uma mensagem escrita pelo aluno em inglês.

Saída:

1. texto corrigido;
2. explicação curta em português;
3. resposta do tutor em inglês para continuar a conversa.

O contrato do tutor deve ser independente de um LLM específico.

Não acoplar a lógica pedagógica diretamente a um modelo ou backend de inferência.

## Modelos locais e recursos

Priorizar execução local.

Meta para o modelo principal:

- aproximadamente 6 GB de VRAM ou menos;
- preservar margem da RTX 4060 de 8 GB;
- manter fallback para CPU quando for viável;
- não baixar modelos automaticamente sem avisar o usuário.

Antes de escolher ou instalar um modelo local, avaliar:

- qualidade em inglês;
- qualidade das explicações em português;
- aderência a instruções;
- velocidade;
- uso real de VRAM;
- compatibilidade com o hardware atual.

## Dependências pesadas

Antes de adicionar algo como:

- PyTorch;
- CUDA toolkit;
- transformers;
- `faster-whisper`;
- llama.cpp;
- engines de inferência;
- frameworks de interface;

pare e explique brevemente:

1. por que a dependência é necessária;
2. alternativas relevantes;
3. impacto em GPU/VRAM;
4. impacto no projeto.

Espere aprovação antes de continuar.

## Git

Pode:

- editar arquivos;
- criar testes;
- executar testes;
- revisar diffs.

Não fazer automaticamente:

- `git commit`;
- `git push`;
- reset destrutivo;
- force push.

Somente fazer commit/push quando solicitado.

## Testes

Toda funcionalidade nova deve ter testes quando fizer sentido.

Antes de concluir uma tarefa, executar a suíte relevante.

Preferência:

`uv run --no-sync pytest`

Durante o desenvolvimento, prefira testes específicos quando isso reduzir tempo e consumo de contexto.

Rode a suíte completa quando fizer sentido para validar o marco.

Não remover ou alterar testes apenas para fazer a suíte passar sem explicar o problema real.

## Uso de tokens e contexto

Economizar contexto e cota do Codex.

Não:

- reler todo o repositório sem necessidade;
- reproduzir arquivos completos na resposta;
- explicar raciocínio interno detalhado;
- produzir relatórios longos para tarefas simples;
- transformar tarefas simples em várias microetapas;
- reanalisar arquivos que já estão suficientemente compreendidos.

Preferir:

- analisar apenas arquivos relacionados à tarefa atual;
- trabalhar em blocos razoáveis;
- concluir em um único bloco quando for seguro;
- reutilizar contexto já disponível no repositório e neste `AGENTS.md`;
- usar testes específicos durante a implementação quando apropriado.

## Política de uso de modelos do Codex

Modelo padrão: **Automático**, quando essa opção estiver disponível.

Objetivo: usar o menor nível de capacidade suficiente para concluir a tarefa com qualidade e economizar cota.

### GPT-5.6 Luna

Usar para tarefas mecânicas e bem especificadas, como:

- criar ou mover arquivos simples;
- renomear símbolos;
- pequenos ajustes de testes;
- documentação;
- formatação;
- alterações repetitivas;
- mudanças locais e facilmente reversíveis.

### GPT-5.6 Terra

Usar como referência para desenvolvimento cotidiano quando o modo Automático não estiver disponível ou quando for necessário selecionar manualmente.

Adequado para:

- implementação normal de features;
- módulos pequenos ou médios;
- refatorações moderadas;
- testes;
- integração entre poucos componentes;
- correção de bugs comuns.

### GPT-5.6 Sol

Usar somente quando houver justificativa clara, como:

- bug difícil;
- integração complexa;
- problema envolvendo vários módulos;
- concorrência;
- CUDA/GPU;
- performance crítica;
- refatoração ampla;
- decisão técnica difícil;
- tentativa anterior com Terra que não resolveu satisfatoriamente.

Se a seleção de modelo for manual, avise brevemente antes de recomendar Sol quando Terra provavelmente não for suficiente.

### GPT-6 Astra

Reservar para casos excepcionais:

- problema muito difícil ou ambíguo;
- investigação profunda;
- falha persistente após tentativa com Sol;
- arquitetura altamente complexa;
- debugging excepcionalmente difícil.

Não recomendar Astra para tarefas normais.

## Regra de escalonamento de modelo

Preferir sempre o menor modelo capaz de executar a tarefa com qualidade.

Escalonamento conceitual:

`Luna -> Terra -> Sol -> Astra`

Quando o modo Automático estiver selecionado, deixe o Codex gerenciar a escolha do modelo, mas siga esta política de eficiência.

Se a tarefa claramente exigir Sol ou Astra e a seleção for manual:

- pare antes de implementar;
- diga qual modelo recomenda;
- explique em no máximo 2 frases o motivo;
- aguarde confirmação.

## Regra de eficiência

Se uma tarefa puder ser concluída com segurança em um único bloco, faça isso.

Evite transformar trabalho simples em várias microetapas que exigem novas rodadas de contexto.

Não use Sol ou Astra apenas por conveniência.

Não aumente o nível de raciocínio sem necessidade clara.

## Quando parar e pedir decisão

Pare antes de:

- mudar arquitetura principal;
- escolher modelo LLM definitivo;
- escolher stack de áudio definitiva;
- alterar estratégia CUDA/GPU;
- adicionar dependência pesada;
- mudar formato persistente de dados;
- introduzir banco de dados;
- escolher framework principal de interface.

## Regra para decisões arquiteturais

Pode implementar sem consultar quando a mudança for:

- local;
- pequena;
- facilmente reversível;
- sem dependência pesada;
- sem alterar contratos entre módulos.

Pare e peça decisão antes de mudanças que:

- afetem vários módulos;
- introduzam dependências pesadas;
- definam interfaces permanentes;
- alterem persistência de dados;
- mudem estratégia de GPU/CUDA;
- escolham LLM, STT, TTS ou framework principal;
- sejam caras de desfazer posteriormente.

Na dúvida, apresente:

1. decisão necessária;
2. opções;
3. impacto;
4. recomendação.

## Estado da V1 e próximo marco

A prioridade atual é concluir a V1 textual.

Decisões e validações já realizadas:

- o contrato textual usa `TutorRequest` e `TutorResponse`, sem acoplamento a LLM;
- os controles, rótulos e mensagens da interface da V1 serão em inglês; a explicação pedagógica do tutor permanece em português brasileiro (`explanation_pt`), conforme o contrato textual;
- o modelo selecionado para a V1 é `Qwen3-4B-Instruct-2507` em `Q4_K_M`, executado com `llama.cpp`;
- avaliações locais iniciais confirmaram a viabilidade do modelo para a V1, inclusive em CPU;
- uma avaliação em CPU com 10 cenários casuais originais obteve 10 contratos válidos e 10 correções esperadas; ela cobriu apresentações, trabalho, convites, combinações, viagem, pedidos de esclarecimento, sentimentos e hobbies;
- o backend oficial CUDA 12.8 do `llama.cpp` (b10978) foi baixado e o binário foi verificado por SHA-256;
- o runtime local do backend está em `data/llama.cpp/b10978/cuda12.8/runtime`; ao iniciar o `llama-server` manualmente, expô-lo por `LD_LIBRARY_PATH` em vez de instalar um CUDA toolkit global;
- o paliativo de inicialização é `scripts/start_llama_server.sh`: ele limita `LD_LIBRARY_PATH` ao processo do `llama-server`, usa o modelo local já existente e solicita `--gpu-layers 999`; não altera variáveis globais, instala dependências ou baixa modelos;
- após reiniciar, o carregamento persistente de `nvidia_uvm` foi confirmado pelo `systemd-modules-load`; o `llama-server --list-devices` no terminal nativo detectou a CUDA0. O ambiente integrado pode não expor CUDA ao processo que ele inicia, portanto a execução do servidor deve ocorrer pelo terminal nativo;
- em 17/09/2026, `nvidia-smi`, `libcuda` e NVML foram confirmados no ambiente (RTX 4060 Laptop, 8188 MiB). A primeira tentativa CUDA falhou porque `nvidia_uvm` não estava carregado; após `sudo modprobe nvidia_uvm`, `cuInit`, o runtime CUDA 12.8 e `llama-server --list-devices` passaram a detectar a GPU;
- a validação CUDA do backend oficial `llama.cpp` b10978, com o runtime CUDA 12.8 fornecido no pacote e `--gpu-layers 999`, foi bem-sucedida: 37/37 camadas foram offloaded para a GPU, sem fallback para CPU. A VRAM foi de 1 MiB inicialmente a 3153 MiB de pico; o modelo usou 2375,91 MiB, o KV cache 576 MiB e o buffer de cálculo 79,01 MiB;
- uma chamada real via `LlamaCppTutor` foi válida na GPU: prompt a 1601,81 tokens/s e geração a 66,78 tokens/s (86 tokens). A resposta corrigiu "Yesterday I go to school and meet my friends." para "Yesterday I went to school and met my friends.";
- `LlamaCppTutor` usa a API HTTP de um `llama-server` local já iniciado, sem gerenciar downloads ou o processo do servidor;
- se a resposta não passa na validação, o tutor faz uma única nova tentativa com instrução reforçada e então retorna uma falha controlada;
- respostas do modelo passam por validação determinística: correção e explicação devem estar preenchidas, `reply_en` deve estar preenchido quando habilitado e vazio quando desabilitado; o texto corrigido deve permanecer relacionado à mensagem do aluno;
- a validação é uma proteção adicional contra respostas desviadas por instruções na entrada e não substitui a avaliação de qualidade gramatical e pedagógica.

Interface de chat da V1 implementada e validada, nos seguintes marcos:

1. definir o contrato local de chats e mensagens, incluindo persistência, sem acoplar o núcleo à interface (concluído: `Chat`, `UserMessage`, `AssistantMessage` e `ChatStore`);
2. implementar a persistência local de chats independentes e seus testes (concluído com `SqliteChatStore`, sem dependências externas);
3. criar a estrutura visual responsiva com Vue 3 e FastAPI local: sidebar, criação, seleção e exclusão com confirmação (concluído);
4. exibir o histórico em ordem cronológica e o formato estruturado da resposta do tutor (concluído);
5. adicionar o campo de envio, `Enter` para enviar e `Shift+Enter` para nova linha (concluído);
6. integrar o envio com `LlamaCppTutor`, estados de carregamento, indisponibilidade do servidor e nova tentativa (concluído);
7. validar manualmente o fluxo completo: criar chat, conversar, trocar, manter histórico e excluir (concluído pelo usuário).

O tutor recebe uma janela das 12 mensagens mais recentes do chat antes da nova mensagem. A consulta SQLite já limita essa leitura; o histórico completo permanece salvo. Esse limite é de mensagens, não uma garantia de tamanho em tokens.

A V1 inclui a seção `Translate`, independente dos chats:

- recebe um texto isolado, sem criar ou consultar histórico;
- retorna uma tradução direta e uma interpretação breve de tom, intenção ou expressão relevante quando necessário;
- usa contrato e chamada ao modelo próprios, sem correção pedagógica, resposta de continuidade ou validação do tutor;
- aparece como entrada principal ao lado de `Chats`;
- suporta inglês para português e português para inglês;
- já possui contrato, adaptador local, API e interface próprios, sem criar chat ou persistir conteúdo.

Decisão de interface: a V1 usará Vue 3 para a camada visual, servido por uma API local em FastAPI. A adoção deve permanecer limitada ao necessário para a interface de chat, sem biblioteca adicional de componentes ou gerenciamento de estado nesta fase. O `nvm` do usuário já fornece Node.js 26.3.0 e npm 11.16.0, adequados ao fluxo atual do Vue; o Node.js 18.19.1 visto fora do `nvm` é apenas a versão do sistema.

Base do frontend criada em `frontend/`: Vue 3.5.43, Vite 8.3.0 e `@vitejs/plugin-vue` 6.0.9. Nenhuma biblioteca de componentes, roteamento ou gerenciamento de estado foi instalada.

Os títulos dos chats podem ser editados pelo cabeçalho da conversa selecionada; a alteração é persistida em SQLite e atualiza imediatamente a barra lateral.

FastAPI 0.141.1 e Uvicorn 0.53.0 foram instalados como dependências da aplicação. `httpx2` 2.13.0 foi adicionado somente ao grupo de desenvolvimento, pois o `TestClient` do Starlette atual o exige para testar a API. O Vite usa proxy local de `/api` para `127.0.0.1:8000` durante o desenvolvimento.

Para uso normal, `scripts/start_linguaforge.sh` inicia o `llama-server`, aguarda o modelo ficar disponível, compila o frontend Vue e inicia FastAPI em `http://127.0.0.1:8000`. Ele encerra o servidor do modelo que iniciou quando recebe `Ctrl+C`; se já houver um `llama-server` saudável, apenas o reutiliza. `scripts/start_app.sh` e `scripts/start_llama_server.sh` permanecem disponíveis para diagnóstico separado.

Em `Settings`, o usuário pode desabilitar `Enable Reply`. A escolha fica salva no navegador, oculta Replies já existentes e pede ao modelo uma resposta sem continuação nas próximas mensagens, reduzindo os tokens de saída.


Revisão final de 19/09/2026:

- respostas assíncronas e rascunhos ficam isolados por chat; a interface ignora leituras antigas após trocar de conversa;
- aluno e tutor são salvos em uma única transação; exclusão concorrente retorna 404 e contexto alterado por outra aba retorna 409;
- respostas malformadas, vazias ou truncadas do modelo são rejeitadas com erro 502; indisponibilidade mantém 503; a consulta de saúde tem timeout de 3 segundos;
- `Reply` desabilitado exige string vazia no schema e na validação; o prompt preserva o ponto de vista do aluno e usa fatos do histórico para responder;
- diálogos usam foco nativo, Escape e bloqueio de ações durante salvamento; tradução mantém idiomas distintos; o layout foi verificado em 320, 360, 640 e 900 px;
- o iniciador verifica pré-requisitos, limita espera de saúde, encerra somente processos próprios e não sincroniza/baixa dependências; log em `data/llama-server.log`;
- `README.md` documenta uso e limites; o roteiro manual em Markdown/PDF pode ser regenerado com `scripts/generate_manual_test_pdf.py`;
- resultados e limitações desta revisão estão em `docs/revisao-final-v1.md`.

V1 revisada versionada no commit `c1472cb`; push informado como concluído pelo usuário. Próximo marco: empacotamento, seguindo uma etapa por vez conforme `docs/plano-empacotamento.md`: (1) definir entrega; (2) preparar execução fora do repositório; (3) integrar abertura/encerramento desktop; (4) gerar e validar instalador. A etapa 1 definiu alvo Pop!_OS 24.04 amd64 e pacote `.deb`; o usuário escolheu janela própria. A direção técnica é pywebview com GTK/WebKitGTK e PyInstaller, preservando Vue/FastAPI e mantendo o GGUF separado. A etapa 2 foi concluída em 19/09/2026: `config.py` separa recursos empacotados e dados XDG, `web.py` recebe essa configuração, e `storage_import.py` oferece importação explícita de chats com backup e recusa de sobrescrita. O desenvolvimento conserva os caminhos anteriores. A prova `desktop_preview.py` abre Vue em GTK/WebKit, mantém armazenamento local e encerra sua própria API. `scripts/build_desktop_preview.sh` usa `.venv-desktop` com Python nativo e gera `dist/linguaforge-preview` (diretório completo, cerca de 489 MiB, sem modelo). Foram adicionados pywebview 6.2.1 no grupo `desktop` e PyInstaller 6.22.3 no grupo `packaging`; o usuário instalou os componentes GTK faltantes. O bundle foi validado fora do checkout, com PATH vazio, duas aberturas da janela, persistência SQLite e armazenamento do WebView. Passaram 128 testes Python e 12 testes da interface. Nenhum chat real foi migrado; CUDA e modelo permaneceram inalterados. Detalhes e reprodução: `docs/empacotamento-etapa2.md`.

A etapa 3 foi concluída em 21/09/2026: `desktop_app.py` exibe carregamento e falhas na própria janela, inicia a API local e inicia ou reutiliza o `llama-server` configurado; `desktop_runtime.py` valida modelo/backend, limita `LD_LIBRARY_PATH` ao processo filho, aguarda saúde, impede segunda instância e encerra somente processos próprios. O executável não baixa modelos, não altera CUDA e mantém o servidor externo reutilizado. Foram adicionados testes de trava, reutilização, ausência de modelo, inicialização e encerramento; a suíte Python passou com 132 testes. O bundle relocado passou pelo smoke test com duas aberturas, persistência do WebView e integração real com o modelo local.

A etapa 4 foi concluída em 21/09/2026: `scripts/build_deb.sh` gera `dist/linguaforge_0.1.0_amd64.deb` para Pop!_OS 24.04 amd64, com bundle em `/opt/linguaforge`, comando, ícone e entrada no menu. O pacote declara `gir1.2-webkit2-4.1` e não inclui GGUF, backend, chats ou configuração. `scripts/test_deb_package.sh` validou extração, instalação isolada, atualização e remoção sem tocar no sistema real nem nos dados do usuário; a instalação nativa exige `sudo apt install` e permanece uma ação manual. `--configure-resources` grava, por escolha explícita do usuário, os caminhos de modelo/backend/runtime em `~/.config/linguaforge/runtime-paths.json`, sem cópia ou download. A suíte Python passou com 135 testes. Na validação real do pacote, o Qwen carregou e usou 3263 MiB de VRAM; para manter a margem de aproximadamente 6 GB, os iniciadores usam por padrão `--ctx-size 4096` e `--parallel 1`, configuráveis por `LLAMA_CONTEXT_SIZE` e `LLAMA_PARALLEL_SLOTS`. O encerramento não deixou `llama-server` ativo. A V1 de empacotamento está pronta para instalação nativa e uso manual.

Após a primeira instalação, a janela desktop identifica a ausência do modelo ou backend e mostra `Initial setup`. Ela permite selecionar os recursos locais já existentes, valida os caminhos e continua a inicialização sem abrir um terminal nem reiniciar a aplicação. O fluxo não procura, baixa, copia ou move arquivos; o comando `--configure-resources` permanece disponível apenas como alternativa de diagnóstico.

Áudio permanece fora do escopo da V1.

## Resposta ao terminar uma tarefa

Responder de forma curta:

### Resultado

- o que foi implementado;
- arquivos principais alterados;
- testes executados e resultado;
- dependências adicionadas, se houver;
- decisões pendentes.

Não reproduzir arquivos completos salvo quando solicitado.
