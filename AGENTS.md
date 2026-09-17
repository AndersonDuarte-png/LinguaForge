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
- o tutor continua a conversa em inglês.

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
- respostas do modelo passam por validação determinística: os três campos devem estar preenchidos e o texto corrigido deve permanecer relacionado à mensagem do aluno;
- a validação é uma proteção adicional contra respostas desviadas por instruções na entrada e não substitui a avaliação de qualidade gramatical e pedagógica.

Próximos marcos devem seguir esta ordem geral:

1. definir e testar o contrato funcional do tutor textual;
2. manter esse contrato independente de um LLM específico;
3. somente depois considerar interface mais elaborada.

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
