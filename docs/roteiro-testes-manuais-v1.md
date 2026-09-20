## BATERIA DE TESTES MANUAIS - LINGUAFORGE V1

- Objetivo: validar a aplicacao completa com o modelo local, antes da entrega da V1.
- Data da execucao: ____________________    Responsavel: ____________________
- Resultado geral: [ ] aprovado  [ ] aprovado com observacoes  [ ] reprovado

## PREPARACAO

- 1. Em um terminal nativo, entre na pasta do projeto LinguaForge.
- 2. Execute ./scripts/start_linguaforge.sh e aguarde LinguaForge disponivel.
- 3. Abra http://127.0.0.1:8000 no navegador.
- 4. Confirme que a pagina inicial abre e que nao ha aviso de indisponibilidade.
- 5. Registre GPU e memoria livre opcionalmente com: nvidia-smi.
- Regra: cada caso abaixo deve ser marcado como PASSOU, FALHOU ou NAO APLICAVEL.

## CASOS DE CHAT

- C01 - Criar chat
- Acao: clique em + New Chat.
- Esperado: um chat New Chat aparece na sidebar e fica selecionado.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C02 - Turno basico do tutor
- Acao: envie: Yesterday I go to school and meet my friends.
- Esperado: aparece uma bolha do aluno e uma resposta da IA com Corrected text, Explanation e Reply.
- Esperado: a correcao usa went e met; a explicacao fica em portugues; a resposta continua em ingles.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C03 - Quebra de linha
- Acao: escreva duas linhas usando Shift+Enter entre elas e envie com Enter.
- Esperado: Shift+Enter cria uma nova linha; Enter envia; o conteudo chega inteiro ao chat.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C04 - Contexto da conversa
- Acao: em um novo chat, envie: I started a new job yesterday. Em seguida envie: It was very stressful.
- Esperado: a segunda resposta reconhece o contexto do trabalho novo, sem trocar de assunto ou inventar fatos.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## CASOS DE CHATS INDEPENDENTES

- C05 - Separacao de historicos
- Acao: no Chat A, converse sobre cooking. Crie o Chat B e converse sobre travel. Volte ao Chat A.
- Esperado: cada chat mostra somente suas mensagens; o tutor no Chat A usa o contexto de cooking.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C06 - Persistencia apos reinicio
- Acao: encerre scripts/start_linguaforge.sh com Ctrl+C, inicie-o novamente e atualize o navegador.
- Esperado: chats e mensagens anteriores continuam presentes e o chat mais recentemente criado e selecionado.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C07 - Exclusao com confirmacao
- Acao: clique no X de um chat. Primeiro escolha Cancel; depois repita e escolha Delete.
- Esperado: Cancel preserva o chat; Delete remove o chat e todas as mensagens dele.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- C08 - Rolagem de conversa
- Acao: envie mensagens suficientes para ultrapassar a altura da tela.
- Esperado: a lista possui rolagem vertical e o chat acompanha a mensagem mais recente apos uma resposta.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## CASOS DE TRADUCAO

- T01 - Ingles para portugues
- Acao: abra Translate, escolha English para Portuguese e envie: I am tied up this afternoon.
- Esperado: a traducao preserva o sentido de estar ocupado; Meaning explica a expressao se necessario.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- T02 - Portugues para ingles
- Acao: troque a direcao e envie: Estou ansioso para a reuniao de amanha.
- Esperado: a traducao fica em ingles natural e Meaning, quando houver, fica em portugues.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- T03 - Sem historico
- Acao: faca uma traducao, retorne a Chats e crie ou abra um chat.
- Esperado: a traducao nao cria chat, nao aparece no historico e nao afeta o contexto do tutor.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## INDISPONIBILIDADE E RECUPERACAO

- I01 - Modelo indisponivel
- Acao: para este diagnostico, inicie start_app.sh e start_llama_server.sh em terminais separados; pare somente o modelo e envie uma mensagem.
- Esperado: o aviso Tutor is unavailable aparece abaixo da barra de digitacao.
- Esperado: o texto permanece na caixa; nenhuma bolha e salva no historico.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- I02 - Recuperacao automatica
- Acao: com o aviso visivel, inicie novamente scripts/start_llama_server.sh.
- Esperado: em ate 10 segundos, o aviso some automaticamente quando o modelo estiver pronto.
- Esperado: envie o texto que permaneceu na caixa e confirme a resposta normal.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- I03 - Tradutor indisponivel
- Acao: repita I01 dentro da secao Translate.
- Esperado: aparece aviso do tradutor; o texto de traducao continua preservado.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## INTERFACE E RESPONSIVIDADE

- U01 - Layout de desktop
- Acao: use a janela em largura normal.
- Esperado: sidebar a esquerda; aluno a direita; IA a esquerda; barra de digitacao visivel no rodape.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- U02 - Tela estreita
- Acao: reduza o navegador para 320, 640 e 900 px ou use a emulacao de celular.
- Esperado: controles continuam acessiveis, sem rolagem horizontal da pagina; ate 640 px a navegacao fica no topo. Textos longos quebram linha e o compositor fica visivel.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- U03 - Idioma da interface
- Acao: revise botoes, rotulos, placeholders e mensagens de erro.
- Esperado: a interface fica em ingles; somente as explicacoes pedagogicas e Meaning podem ficar em portugues.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## CONFIGURACOES E TITULOS

- U04 - Desabilitar e reabilitar Reply
- Acao: abra Settings e desmarque Enable Reply; envie uma frase. Recarregue a pagina e confira a preferencia; depois reative e envie outra frase.
- Esperado: correcao e explicacao permanecem; desativado nao gera Reply. Ao reativar, respostas antigas existentes reaparecem, sem inventar Replies para turnos que nao os geraram.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- U05 - Renomear chat
- Acao: abra Edit title, salve outro nome e recarregue. Tente salvar somente espacos e teste Cancel e Escape.
- Esperado: titulo persistido na lateral e cabecalho, limite de 80 caracteres, nenhum titulo vazio; cancelamento preserva o nome.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- U06 - Navegacao por teclado
- Acao: abra Settings, Edit title e a confirmacao de exclusao usando teclado. Navegue com Tab e feche com Escape.
- Esperado: foco visivel e contido no dialogo; ao fechar retorna ao controle de origem; campos e botoes acessiveis.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## REGRESSOES DA REVISAO FINAL

- R01 - Trocar de chat durante resposta
- Acao: envie no chat A e, durante a geracao, selecione B e digite um rascunho. Volte a A depois da resposta.
- Esperado: resposta permanece em A; historico e rascunho de B nao sao alterados. Nenhuma duplicacao ao voltar a A.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- R02 - Contexto preserva pronomes e fatos
- Acao: envie My dog is named Kira. e depois What is my dog's name?
- Esperado: pergunta permanece com my; Reply recupera Kira, sem alterar o ponto de vista do aluno.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- R03 - Traducao e direcao
- Acao: selecione cada sentido, use Swap e traduza; edite depois o texto original.
- Esperado: idiomas sao sempre distintos, edicao limpa resultado antigo, controles ficam protegidos durante geracao.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- R04 - Inicializacao e encerramento
- Acao: com portas livres, use start_linguaforge.sh e depois Ctrl+C. Repita com o modelo ja iniciado separadamente.
- Esperado: so anuncia disponibilidade depois de modelo e API prontos; encerra processos que iniciou e preserva o modelo externo.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

- R05 - Duas abas no mesmo chat
- Acao: envie simultaneamente duas mensagens em duas abas do mesmo chat.
- Esperado: se o contexto mudou durante geracao, a segunda operacao orienta recarregar; nenhuma metade de turno ou historico sobrescrito.
- Resultado: [ ] passou [ ] falhou  Observacao: _______________________________

## CRITERIO DE ACEITACAO

- A V1 pode seguir para entrega quando todos os casos aplicaveis passarem.
- Falhas que bloqueiam a entrega: perda de historico, mistura entre chats, ausencia de resposta do tutor com servidor saudavel, traducao salva como chat, exclusao sem confirmacao, ou interface inutilizavel em tela estreita.
- Observacoes finais:
- ______________________________________________________________________________
- ______________________________________________________________________________
- ______________________________________________________________________________
- Assinatura: _______________________________    Data: _________________________

