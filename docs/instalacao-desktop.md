# LinguaForge desktop para Pop!_OS 24.04 amd64

O pacote atual é `dist/linguaforge_0.1.0_amd64.deb`. Ele contém a janela desktop, API e frontend pré-compilado. Não contém o modelo Qwen, o backend llama.cpp, chats nem credenciais.

## Instalar

No terminal nativo, na raiz do repositório que contém o pacote:

```sh
sudo apt install ./dist/linguaforge_0.1.0_amd64.deb
```

O `apt` instala a dependência gráfica `gir1.2-webkit2-4.1` e suas dependências. Não instala CUDA, baixa modelo ou move chats.

## Preparar os recursos locais na primeira abertura

Na primeira abertura, a janela **Initial setup** pede o arquivo GGUF e o executável `llama-server` já existentes. O diretório do runtime CUDA é recomendado para uso da GPU, mas pode ficar vazio para permitir o fallback de CPU. Escolha os caminhos e use **Save and start**: a aplicação valida, grava a configuração e inicia na mesma janela.

Esse fluxo não baixa, copia nem move modelo ou backend. Os caminhos ficam em `~/.config/linguaforge/runtime-paths.json`, com permissão de usuário.

Como alternativa de diagnóstico, os mesmos caminhos podem ser configurados pelo terminal. Os caminhos abaixo são os validados neste computador; ajuste apenas se eles estiverem em outro local.

```sh
linguaforge --configure-resources \
  --model "$HOME/Repo/LinguaForge/models/Qwen3-4B-Instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf" \
  --server "$HOME/Repo/LinguaForge/data/llama.cpp/b10978/cuda12.8/bin/llama-b10978/llama-server" \
  --cuda-runtime "$HOME/Repo/LinguaForge/data/llama.cpp/b10978/cuda12.8/runtime"
```

O comando também só valida e grava os caminhos. Variáveis de ambiente `LINGUAFORGE_MODEL_PATH`, `LINGUAFORGE_LLAMA_SERVER` e `LINGUAFORGE_CUDA_RUNTIME_DIR` continuam tendo prioridade para diagnóstico.

Se houver chats no checkout antigo, importe-os antes de criar novos chats no aplicativo instalado:

```sh
linguaforge --import-chats "$HOME/Repo/LinguaForge/data/chats.sqlite3"
```

A importação cria um backup e recusa sobrescrever um banco já existente.

## Usar, atualizar e remover

Abra **LinguaForge** pelo menu de aplicativos ou execute `linguaforge`. A janela inicia a API e o modelo local, e os encerra ao fechar quando forem processos próprios. Um `llama-server` saudável já aberto em `127.0.0.1:8080` é reutilizado e preservado.

Chats ficam em `~/.local/share/linguaforge/chats.sqlite3`; logs do backend ficam em `~/.local/state/linguaforge/llama-server.log`. Para atualizar, instale o próximo `.deb` com `sudo apt install ./novo-pacote.deb`. Para remover o aplicativo, use `sudo apt remove linguaforge`; chats, configuração e modelo permanecem no computador.

Para uma execução de diagnóstico sem GPU, use `LLAMA_GPU_LAYERS=0 linguaforge`. A configuração padrão usa todas as camadas compatíveis com GPU, contexto de 4.096 tokens e um slot. Na validação do pacote com o Qwen carregado, a RTX 4060 usou 3.263 MiB de VRAM, abaixo da meta aproximada de 6 GB.

## Construir e validar

```sh
./scripts/build_deb.sh
./scripts/test_deb_package.sh dist/linguaforge_0.1.0_amd64.deb
```

O segundo comando instala, atualiza e remove o pacote em uma raiz temporária, sem modificar o sistema real. A instalação real requer o primeiro comando desta página e senha de administrador.
