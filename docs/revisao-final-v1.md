# Revisão final da V1 — 19/09/2026

A revisão encontrou problemas funcionais que não estavam cobertos pelos 51 testes iniciais. As correções abaixo foram implementadas e verificadas. Não foram identificados bloqueadores para o commit nas verificações realizadas. Nenhum commit ou push foi feito nesta revisão.

## Problemas corrigidos

| Área | Problema reproduzido ou identificado no código | Correção |
| --- | --- | --- |
| Troca de chat | Uma leitura atrasada de A podia sobrescrever B; uma resposta em geração podia ser anexada ao chat selecionado depois do envio. | Cada operação mantém o chat de origem; leituras antigas são ignoradas e respostas não vazam entre conversas. |
| Rascunhos e exclusão | O rascunho era global; excluir um chat não selecionado recarregava a conversa atual. | Rascunhos separados por chat durante a sessão; exclusão de outra conversa preserva a atual. |
| SQLite | Aluno e tutor eram gravados em transações distintas; uma falha podia salvar somente metade do turno. | Uma transação salva o par completo ou desfaz tudo. Sem alteração de schema. |
| Concorrência | Duas abas podiam salvar respostas baseadas no mesmo histórico já desatualizado; exclusão durante geração gerava falha não tratada. | Conferência atômica da última mensagem, erro 409 para conflito e 404 para exclusão concorrente. |
| Histórico | Todo o histórico era lido do banco antes de limitar o contexto. | A consulta de contexto lê apenas as últimas 12 mensagens; a interface mantém o histórico completo. |
| Saída do modelo | `choices` vazio e formatos inesperados escapavam do tratamento; tradução vazia era aceita; corte por limite de tokens podia passar despercebido. | Validação explícita de envelope, tipos, campos, conteúdo obrigatório e conclusão. Saída truncada é rejeitada. |
| Mensagens de erro | Resposta inválida era tratada como servidor parado. | 502 identifica falha de resposta e 503 identifica indisponibilidade; o rascunho permanece para recuperação. |
| Reply | Desligar dependia somente da instrução textual para não gerar continuação. | Schema exige string vazia e validação confirma; instruções do modo ligado e desligado são separadas. |
| Contexto pedagógico | No teste real, o modelo trocou indevidamente “my” por “your” e deixou de responder um fato do histórico. | Prompt reforça a preservação do ponto de vista e a resposta com fatos explícitos do histórico; caso repetido com outro nome passou. |
| Similaridade | A heurística padrão de `SequenceMatcher` rejeitava uma correção legítima com frases repetidas. | Comparação desativa a heurística de descarte de caracteres frequentes; regressão cobre o caso. |
| Translate | Era possível selecionar idiomas iguais ou mudar a direção durante uma resposta. | Direções complementares, controles protegidos durante a geração e remoção de resultado antigo quando a entrada muda. Orçamento de saída ampliado para 2048 tokens. |
| Interface | Títulos/textos longos, foco de modais e falta de espaço na digitação exigiam proteção. | Quebra de linhas, largura mínima flexível, rolagem, diálogos nativos, foco visível, mensagens de erro junto da ação e ícone da aba. |
| Inicialização | Disponibilidade era anunciada antes da API, chamadas de saúde não tinham limite curto e o encerramento não cobria todos os filhos. | Pré-requisitos antes do modelo, readiness com timeout, grupos de processos e encerramento limitado aos processos criados pelo script. |
| Reuso da aplicação | Uma API já aberta com o modelo parado não iniciava o componente que faltava. | O iniciador reutiliza a API e inicia o modelo ausente. Instâncias externas são preservadas. |
| Dependências ao iniciar | `uv run` podia sincronizar implicitamente o ambiente. | Inicialização usa `--no-sync --offline --no-python-downloads`; não baixa pacotes ou modelos. |

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| `uv run --no-sync pytest -q` | **114 passaram**, aproximadamente 15 segundos; 1 aviso de depreciação já existente no Starlette/AnyIO. |
| `npm test` em `frontend/` | **12 passaram**, incluindo corridas de seleção/envio, rascunhos, falhas, envio duplo, histórico atrasado e renomeação. |
| `npm run build` | Concluído; nenhum pacote instalado. |
| Firefox headless com API simulada e perfis temporários | Passou em viewports efetivos de **320, 360, 640 e 900 × 800 px**. Conferidos overflow horizontal, compositor, textos/títulos longos, foco do diálogo, renomeação, Reply, envio e tradução. |
| API atual + modelo local existente, com SQLite temporário | **4 turnos de tutor + 2 traduções passaram**. Nenhuma mensagem foi adicionada aos chats do usuário. |
| Scripts de inicialização | 15 testes de processos simulados incluídos na suíte Python; cobrem falhas, sinais, timeout, processos filhos, reutilização e pré-requisitos. |
| `bash -n` nos três iniciadores | Passou. |
| `scripts/start_app.sh --check` | Passou com os componentes locais. |
| Roteiro manual regenerado | PDF válido, 4 páginas A4; versão Markdown e gerador disponíveis. |
| `git diff --check` e inspeção de arquivos novos | Sem erros de whitespace. |

### Amostra de modelo real com o prompt final

| Entrada | Resultado verificado |
| --- | --- |
| `Yesterday I go to school and meet my friends.` | `Yesterday I went to school and met my friends.`; explicação em português e Reply presente. |
| `My sister don't like coffee, but she love tea.` com Reply desligado | `My sister doesn't like coffee, but she loves tea.`; explicação presente e `reply_en` vazio. |
| `My dog is named Kira.` | Frase preservada e fato disponível no histórico. |
| `What is my dog's name?` | Pergunta preservada e Reply recuperou Kira. |
| `I am tied up this afternoon.` | `Estou ocupado esta tarde.` |
| `A reunião foi adiada para amanhã.` | `The meeting has been postponed to tomorrow.` |

A validação manual anterior foi informada como concluída pelo usuário. Os novos casos de concorrência, configuração e inicialização constam no roteiro atualizado para futuras regressões.

## Limites e próximos passos

- A amostra real confirma os cenários executados, não garante todas as respostas futuras. O LLM ainda pode introduzir inferências ou erros pedagógicos; a validação de formato/similaridade não prova precisão semântica.
- O contexto contém no máximo 12 mensagens, mas não possui orçamento exato de tokens. Entradas muito grandes podem exceder a capacidade do modelo e gerar erro controlado. Não há truncamento silencioso de respostas aceitas.
- Preferência de Reply é local ao navegador/origem; rascunhos são apenas da sessão. Chats e mensagens concluídas persistem no SQLite.
- Os testes novos de inicialização não desligaram o modelo ou a API reais do usuário. O ciclo de sinais/cleanup foi verificado com processos isolados; o uso manual do iniciador anterior já havia sido confirmado na conversa.
- Nenhuma dependência foi adicionada nesta revisão e nenhuma configuração de GPU foi modificada. As dependências de Vue/FastAPI já estavam presentes no trabalho anterior ainda não commitado.
- A aplicação continua executada pelo repositório. Instalador/executável, distribuição do backend/modelo e integração com o menu do sistema são etapas posteriores.

Para usar o código revisado, encerre o iniciador antigo com `Ctrl+C`, execute `./scripts/start_linguaforge.sh` novamente e recarregue o navegador. Uma API já em execução mantém o código Python que carregou até ser reiniciada.
