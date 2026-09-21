# Etapa 2 — execução independente do repositório

A prova desktop preserva Vue/FastAPI e incorpora Python com PyInstaller. O GGUF e o backend de inferência permanecem separados. Este artefato ainda não é o instalador `.deb`; a integração do iniciador desktop foi concluída na etapa 3 e o pacote instalável pertence à etapa 4.

## Preparar o build no terminal nativo

Alvo: Pop!_OS 24.04 amd64, Python 3.12 do sistema. A distribuição fornece GTK, Cairo e WebKitGTK. Os componentes que faltavam foram instalados pelo usuário:

```sh
sudo apt install --no-install-recommends python3-gi-cairo gir1.2-webkit2-4.1
```

A instalação inclui `gir1.2-javascriptcoregtk-4.1`. Não instala CUDA, modelo ou framework de IA. Em uma máquina nova, verificar também `python3-gi`, `python3-cairo`, `gir1.2-gtk-3.0` e `libwebkit2gtk-4.1-0`; estavam presentes nesta máquina.

Preparar um ambiente separado para acessar os bindings gráficos do Python nativo:

```sh
cd ~/Repo/LinguaForge
uv venv --python /usr/bin/python3 --system-site-packages .venv-desktop
VIRTUAL_ENV="$PWD/.venv-desktop" uv sync --active --group desktop --group packaging --no-default-groups --locked
./scripts/build_desktop_preview.sh
```

O grupo `desktop` contém pywebview; `packaging` contém PyInstaller. O build exige Node/npm compatíveis e as dependências Vue já instaladas, compila o frontend e inclui seus arquivos no bundle. O script pode carregar o nvm existente; não instala Node nem baixa modelos. A receita exclui `pkg_resources` legado da distribuição, incompatível com o setuptools atual; as dependências usadas funcionam com `importlib.metadata`.

## Executar a prova

```sh
./dist/linguaforge-preview/linguaforge-preview --check
./dist/linguaforge-preview/linguaforge-preview
```

É necessário manter **todo** o diretório `dist/linguaforge-preview`, incluindo `_internal`. Pode-se copiar esse diretório para outro lugar. Não depende da `.venv`, de uv, Python ou Node no PATH para executar, mas requer ambiente gráfico e bibliotecas compatíveis com o sistema alvo.

A janela usa a API local na porta 18765. `--port` permite selecionar outra; mudar a porta muda a origem do armazenamento local do WebView e, portanto, a preferência `Enable Reply`. O iniciador da etapa 3 preserva uma porta padrão, trata instância/porta ocupada e inicia o modelo configurado.

No modo `--no-model`, o servidor pode permanecer separado para testar apenas a interface. No uso normal, o iniciador inicia ou reutiliza o servidor em `127.0.0.1:8080`; ao fechar, encerra apenas o processo que iniciou e preserva um servidor externo reutilizado.

## Recursos e dados

| Item | Desenvolvimento | Execução empacotada (padrão) |
|---|---|---|
| Frontend | `frontend/dist` | `_internal/frontend` do bundle |
| Chats | `data/chats.sqlite3` | `~/.local/share/linguaforge/chats.sqlite3` |
| WebView | Navegador externo | `~/.local/share/linguaforge/webview` |
| Configuração | `data/config` | `~/.config/linguaforge` |
| Estado/logs futuros | `data/state` | `~/.local/state/linguaforge` |
| Modelos | `models` | `~/.local/share/linguaforge/models` |
| Backend | `data/llama.cpp/b10978/cuda12.8` | `~/.local/share/linguaforge/backends/llama.cpp` |

São respeitados `XDG_DATA_HOME`, `XDG_CONFIG_HOME` e `XDG_STATE_HOME` absolutos. A resolução de caminhos não cria diretórios nem depende da pasta atual. Configurações e estado possuem diretórios preparados, sem formato novo de configuração/log nesta etapa.

`LINGUAFORGE_MODEL_PATH`, `LINGUAFORGE_LLAMA_SERVER` e `LINGUAFORGE_CUDA_RUNTIME_DIR` permitem apontar para recursos locais existentes por caminhos absolutos. O iniciador usa esses caminhos para iniciar inferência, sem copiar ou baixar modelos automaticamente.

## Importar chats de forma explícita

Antes de abrir a prova pela primeira vez com o diretório de dados definitivo:

```sh
./dist/linguaforge-preview/linguaforge-preview --import-chats "$HOME/Repo/LinguaForge/data/chats.sqlite3"
```

A importação lê a origem sem alterá-la, cria um snapshot SQLite consistente (incluindo transações confirmadas em WAL) e salva uma cópia independente em `backups` junto ao destino. Recusa sobrescrever qualquer banco existente. Se a janela já criou um banco de destino, não o exclua às cegas: use outro `XDG_DATA_HOME` para testar ou preserve os dados antes de decidir como migrar.

Os testes usam bancos temporários; os chats reais do usuário não foram migrados. Preferências do navegador anterior não são importadas para o WebView.

## Validação reproduzível

```sh
uv run --no-sync pytest -q
python3 scripts/smoke_desktop_preview.py dist/linguaforge-preview --window
```

O segundo comando deve rodar no terminal nativo. Copia o bundle para um diretório temporário fora do checkout, remove Python/Node/uv do PATH do processo testado, isola os diretórios XDG e verifica recursos, API e persistência de chats após reiniciar. `--window` também abre uma janela temporária, verifica o Vue renderizado, fecha automaticamente e reabre na mesma porta para confirmar o armazenamento local persistente. Não usa os chats reais nem inicia o modelo.

## Resultado em 19/09/2026

- 128 testes Python passaram; 1 aviso de depreciação externo (`anyio`/Starlette), sem falhas.
- 12 testes da interface passaram; build Vue concluído.
- Bundle copiado para `/tmp`, fora do checkout, executou com PATH vazio e sem ambiente virtual.
- Recursos compilados, API, criação/renomeação/exclusão e histórico após reiniciar: aprovados.
- Duas aberturas nativas GTK/WebKit renderizaram Vue; armazenamento local recuperado na segunda abertura.
- Testes unitários cobrem importação com backup independente, preservação da origem, recusa de sobrescrita, fontes inválidas e snapshot de WAL.
- Artefato local: `dist/linguaforge-preview`, aproximadamente **489 MiB** em disco, sem GGUF. É tamanho do diretório, não consumo de RAM/VRAM nem tamanho final do `.deb`.
- Versões: pywebview 6.2.1; PyInstaller 6.22.3; WebKit/JavaScriptCore GTK 2.52.6; python3-gi-cairo 3.48.2.
- Nenhum chat real migrado, modelo baixado ou configuração CUDA alterada. Não houve commit/push.
- Permanecem nas próximas etapas: iniciador completo, integração no menu, medição de recursos com modelo ativo, pacote `.deb` e testes de instalação/atualização/remoção.

O iniciador completo foi entregue na etapa 3 e está descrito em `docs/plano-empacotamento.md`. O bundle continua sendo um artefato de build; a instalação, o ícone e a medição com o modelo ativo ficam para a etapa 4.

## Referências

- [Dependências Linux do pywebview](https://pywebview.flowrl.com/guide/installation.html).
- [API e armazenamento persistente do pywebview](https://pywebview.flowrl.com/api/).
- [Recursos em aplicações PyInstaller](https://pyinstaller.org/en/stable/runtime-information.html).
