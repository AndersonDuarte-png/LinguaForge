# Empacotamento do LinguaForge — plano em quatro etapas

Estado inicial: V1 revisada e versionada no commit `c1472cb`; push informado pelo usuário. A árvore de trabalho estava limpa antes deste planejamento.

Vamos concluir uma etapa por vez. O planejamento definiu a entrega; a etapa 2 prepara uma prova executável, e o instalador definitivo pertence à etapa 4.

## 1. Definir a entrega

**Estado: definição inicial concluída; implementação e validação nas etapas seguintes.**

- Alvo inicial: o Pop!_OS 24.04 x86_64 já utilizado pelo usuário.
- Formato inicial: pacote `.deb`, com nome, ícone e entrada no menu de aplicativos.
- Experiência escolhida pelo usuário: janela própria de aplicativo, com as dependências adicionais necessárias, sem terminal no uso diário.
- Preservar Vue, FastAPI, SQLite e o backend/modelo já validados.
- Manter o arquivo GGUF separado das atualizações da aplicação. Reaproveitar o modelo existente mediante configuração/importação local, sem download automático.
- Direção técnica: `pywebview` com GTK/WebKitGTK para hospedar a interface Vue existente, e PyInstaller em modo de diretório para empacotar Python e suas dependências no `.deb`.
- Alternativas consideradas: Qt também é suportado por pywebview; Electron/Tauri exigiriam outra camada de empacotamento junto ao backend Python. A escolha inicial aproveita Python e os componentes GTK/WebKit do sistema alvo.
- A janela terá custo adicional de memória/renderização; a medição de RAM/VRAM e coexistência com CUDA fará parte da validação. Não há alteração planejada nos parâmetros do modelo.
- Inspeção inicial no sistema nativo confirmou `python3-gi`, GTK 3 e `libwebkit2gtk-4.1-0`; `gir1.2-webkit2-4.1` ainda não está instalado. A integração dessas bibliotecas com o ambiente Python e com o pacote precisa ser validada.
- Não haverá dependência de Node/uv no uso do pacote final. Bibliotecas gráficas de sistema continuarão sendo dependências declaradas do `.deb`.
- A configuração do WebView deverá preservar armazenamento local entre sessões para manter `Enable Reply`; o armazenamento do navegador atual não migra automaticamente para a nova janela.

**Concluída quando:** formato, experiência de abertura/encerramento e dependências necessárias estiverem definidos.

## 2. Preparar execução fora do repositório

**Estado: concluída e validada em 19/09/2026.**

Prova executável gerada com PyInstaller: Vue/API funcionaram fora do checkout com PATH vazio, histórico persistiu após reiniciar e a janela GTK preservou armazenamento local entre aberturas. Caminhos XDG e importação explícita com backup implementados. Validação: 128 testes Python, 12 testes da interface e smoke test nativo. Instruções e limites em [empacotamento-etapa2.md](empacotamento-etapa2.md).

- Validar primeiro as dependências gráficas e a viabilidade de build no sistema alvo, com uma prova mínima de janela.
- Compilar Vue durante a construção do pacote, eliminando a compilação a cada abertura.
- Executar a instalação sem depender de checkout, `.venv` de desenvolvimento, Node/npm, nvm ou uv no uso diário.
- Separar recursos da aplicação, banco de chats, configurações, logs, backend e modelo.
- Usar diretórios do usuário apropriados para dados graváveis; planejar transferência dos chats com backup e sem alterar o schema SQLite.
- Preservar o modo de desenvolvimento existente.

**Concluída quando:** aplicação de teste executar fora da pasta do projeto com recursos empacotados e testes cobrirem caminhos e preservação dos dados.

## 3. Integrar abertura e encerramento como aplicativo

**Estado: concluída e validada em 21/09/2026.**

O ponto de entrada `linguaforge-desktop` agora abre a janela GTK/WebKit, mostra uma tela de carregamento, inicia a API local e inicia ou reutiliza o `llama-server` saudável em `127.0.0.1:8080`. O servidor local recebe `LD_LIBRARY_PATH` somente no próprio processo, usa o modelo já configurado e nunca baixa arquivos. Uma trava de instância evita duas janelas usando o mesmo armazenamento. Falhas de porta, backend, modelo ou tempo de inicialização aparecem na própria janela. O encerramento libera a API e somente o processo do modelo iniciado pela sessão; um servidor externo reutilizado permanece ativo.

O modo `--no-model` continua disponível para diagnóstico e smoke test da interface; `--check`, `--serve-only` e `--import-chats` continuam sem iniciar inferência.

Validação da etapa: a suíte Python passou com 132 testes; o bundle foi reconstruído e executado fora do checkout com PATH vazio; a API, os assets, duas aberturas GTK/WebKit e a persistência do WebView passaram. Uma execução adicional iniciou o Qwen3-4B-Instruct-2507 local pelos caminhos absolutos configurados, aguardou o `llama-server` saudável e encerrou o processo próprio ao fechar a janela. A integração no menu e a medição final de RAM/VRAM ficam para o pacote da etapa 4.

- Abrir pelo ícone e iniciar automaticamente modelo/backend/interface na ordem correta.
- Exibir carregamento e falhas sem depender de um terminal.
- Tratar segunda abertura, instância já existente, porta ocupada e ausência do modelo.
- Encerrar os processos próprios e liberar recursos. Preservar serviços externos reutilizados.
- Fechar a janela encerra os processos próprios da sessão. A interface deve indicar operações ainda pendentes antes do encerramento.

**Concluída quando:** abrir, usar e encerrar pelo fluxo de desktop funcionar sem comandos manuais.

## 4. Gerar o pacote e validar instalação/atualização

**Estado: concluída e validada em 21/09/2026, com instalação real pendente de senha administrativa.**

O pacote `dist/linguaforge_0.1.0_amd64.deb` instala o bundle em `/opt/linguaforge`, o comando `linguaforge`, ícone SVG e entrada no menu. Declara `gir1.2-webkit2-4.1`; o modelo, backend, chats e configuração ficam fora do `.deb`. `scripts/build_deb.sh` produz o artefato e `scripts/test_deb_package.sh` valida extração, instalação isolada, atualização simulada e remoção, preservando dados de usuário. Instruções para a instalação nativa: [instalacao-desktop.md](instalacao-desktop.md).

O pacote executou o Qwen local com contexto de 4.096 e um slot, chegando a 3.263 MiB de VRAM; a tentativa anterior com os padrões do `llama-server` usou 6.774 MiB, então os limites agora são explícitos. O encerramento não deixou processo `llama-server` ativo.

- Criar uma receita reproduzível de build e gerar o instalador no formato definido.
- Verificar arquivos, dependências, permissões e integração no menu antes de instalar.
- Validar a instalação no sistema alvo e a execução sem ambiente de desenvolvimento.
- Verificar chat, Translate, inicialização do modelo, CPU/CUDA, logs e encerramento.
- Testar atualização e remoção preservando os chats e o modelo do usuário.
- Documentar instalação, uso, atualização e recuperação dos dados.

**Concluída quando:** houver um pacote instalável validado no alvo e instruções curtas para seu uso.

## Pontos identificados antes da implementação

- `get_config()` encontrava dados e modelos a partir da raiz do repositório; a etapa 2 adiciona caminhos XDG para execução instalada.
- `web.py` buscava o frontend relativo ao checkout; a etapa 2 permite recursos compilados no bundle.
- Os iniciadores de desenvolvimento dependem de `.venv`, uv, Node/npm e caminhos locais do backend/modelo; continuam disponíveis. O iniciador desktop da etapa 3 usa o bundle e os caminhos XDG, sem essas ferramentas no uso diário.
- `start_app.sh` compila o frontend a cada inicialização; a prova empacotada usa frontend pré-compilado.

## Referências técnicas

- [Formato e gerenciamento de pacotes Debian](https://www.debian.org/doc/manuals/debian-faq/pkg-basics.en.html).
- [Desktop Entry Specification: integração de lançadores no menu](https://specifications.freedesktop.org/desktop-entry/latest/).
- [XDG Base Directory Specification: dados, configurações e logs por usuário](https://specifications.freedesktop.org/basedir/latest/).

- [pywebview: instalação e dependências GTK no Linux](https://pywebview.flowrl.com/guide/installation.html).
- [pywebview: empacotamento de aplicações Python e Vue](https://pywebview.flowrl.com/guide/freezing.html).
- [pywebview: janela, eventos e persistência local](https://pywebview.flowrl.com/api/).
- [PyInstaller: execução de aplicações empacotadas](https://pyinstaller.org/en/stable/operating-mode.html).
