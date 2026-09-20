from pathlib import Path

output = Path(__file__).resolve().parents[1] / 'docs' / 'roteiro-testes-manuais-v1.pdf'

sections = [
    ('BATERIA DE TESTES MANUAIS - LINGUAFORGE V1', [
        'Objetivo: validar a aplicacao completa com o modelo local, antes da entrega da V1.',
        'Data da execucao: ____________________    Responsavel: ____________________',
        'Resultado geral: [ ] aprovado  [ ] aprovado com observacoes  [ ] reprovado',
    ]),
    ('PREPARACAO', [
        '1. Em um terminal nativo, entre na pasta do projeto LinguaForge.',
        '2. Execute ./scripts/start_linguaforge.sh e aguarde LinguaForge disponivel.',
        '3. Abra http://127.0.0.1:8000 no navegador.',
        '4. Confirme que a pagina inicial abre e que nao ha aviso de indisponibilidade.',
        '5. Registre GPU e memoria livre opcionalmente com: nvidia-smi.',
        'Regra: cada caso abaixo deve ser marcado como PASSOU, FALHOU ou NAO APLICAVEL.',
    ]),
    ('CASOS DE CHAT', [
        'C01 - Criar chat',
        'Acao: clique em + New Chat.',
        'Esperado: um chat New Chat aparece na sidebar e fica selecionado.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C02 - Turno basico do tutor',
        'Acao: envie: Yesterday I go to school and meet my friends.',
        'Esperado: aparece uma bolha do aluno e uma resposta da IA com Corrected text, Explanation e Reply.',
        'Esperado: a correcao usa went e met; a explicacao fica em portugues; a resposta continua em ingles.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C03 - Quebra de linha',
        'Acao: escreva duas linhas usando Shift+Enter entre elas e envie com Enter.',
        'Esperado: Shift+Enter cria uma nova linha; Enter envia; o conteudo chega inteiro ao chat.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C04 - Contexto da conversa',
        'Acao: em um novo chat, envie: I started a new job yesterday. Em seguida envie: It was very stressful.',
        'Esperado: a segunda resposta reconhece o contexto do trabalho novo, sem trocar de assunto ou inventar fatos.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('CASOS DE CHATS INDEPENDENTES', [
        'C05 - Separacao de historicos',
        'Acao: no Chat A, converse sobre cooking. Crie o Chat B e converse sobre travel. Volte ao Chat A.',
        'Esperado: cada chat mostra somente suas mensagens; o tutor no Chat A usa o contexto de cooking.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C06 - Persistencia apos reinicio',
        'Acao: encerre scripts/start_linguaforge.sh com Ctrl+C, inicie-o novamente e atualize o navegador.',
        'Esperado: chats e mensagens anteriores continuam presentes e o chat mais recentemente criado e selecionado.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C07 - Exclusao com confirmacao',
        'Acao: clique no X de um chat. Primeiro escolha Cancel; depois repita e escolha Delete.',
        'Esperado: Cancel preserva o chat; Delete remove o chat e todas as mensagens dele.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'C08 - Rolagem de conversa',
        'Acao: envie mensagens suficientes para ultrapassar a altura da tela.',
        'Esperado: a lista possui rolagem vertical e o chat acompanha a mensagem mais recente apos uma resposta.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('CASOS DE TRADUCAO', [
        'T01 - Ingles para portugues',
        'Acao: abra Translate, escolha English para Portuguese e envie: I am tied up this afternoon.',
        'Esperado: a traducao preserva o sentido de estar ocupado; Meaning explica a expressao se necessario.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'T02 - Portugues para ingles',
        'Acao: troque a direcao e envie: Estou ansioso para a reuniao de amanha.',
        'Esperado: a traducao fica em ingles natural e Meaning, quando houver, fica em portugues.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'T03 - Sem historico',
        'Acao: faca uma traducao, retorne a Chats e crie ou abra um chat.',
        'Esperado: a traducao nao cria chat, nao aparece no historico e nao afeta o contexto do tutor.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('INDISPONIBILIDADE E RECUPERACAO', [
        'I01 - Modelo indisponivel',
        'Acao: para este diagnostico, inicie start_app.sh e start_llama_server.sh em terminais separados; pare somente o modelo e envie uma mensagem.',
        'Esperado: o aviso Tutor is unavailable aparece abaixo da barra de digitacao.',
        'Esperado: o texto permanece na caixa; nenhuma bolha e salva no historico.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'I02 - Recuperacao automatica',
        'Acao: com o aviso visivel, inicie novamente scripts/start_llama_server.sh.',
        'Esperado: em ate 10 segundos, o aviso some automaticamente quando o modelo estiver pronto.',
        'Esperado: envie o texto que permaneceu na caixa e confirme a resposta normal.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'I03 - Tradutor indisponivel',
        'Acao: repita I01 dentro da secao Translate.',
        'Esperado: aparece aviso do tradutor; o texto de traducao continua preservado.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('INTERFACE E RESPONSIVIDADE', [
        'U01 - Layout de desktop',
        'Acao: use a janela em largura normal.',
        'Esperado: sidebar a esquerda; aluno a direita; IA a esquerda; barra de digitacao visivel no rodape.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'U02 - Tela estreita',
        'Acao: reduza o navegador para 320, 640 e 900 px ou use a emulacao de celular.',
        'Esperado: controles continuam acessiveis, sem rolagem horizontal da pagina; ate 640 px a navegacao fica no topo. Textos longos quebram linha e o compositor fica visivel.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'U03 - Idioma da interface',
        'Acao: revise botoes, rotulos, placeholders e mensagens de erro.',
        'Esperado: a interface fica em ingles; somente as explicacoes pedagogicas e Meaning podem ficar em portugues.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('CONFIGURACOES E TITULOS', [
        'U04 - Desabilitar e reabilitar Reply',
        'Acao: abra Settings e desmarque Enable Reply; envie uma frase. Recarregue a pagina e confira a preferencia; depois reative e envie outra frase.',
        'Esperado: correcao e explicacao permanecem; desativado nao gera Reply. Ao reativar, respostas antigas existentes reaparecem, sem inventar Replies para turnos que nao os geraram.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'U05 - Renomear chat',
        'Acao: abra Edit title, salve outro nome e recarregue. Tente salvar somente espacos e teste Cancel e Escape.',
        'Esperado: titulo persistido na lateral e cabecalho, limite de 80 caracteres, nenhum titulo vazio; cancelamento preserva o nome.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'U06 - Navegacao por teclado',
        'Acao: abra Settings, Edit title e a confirmacao de exclusao usando teclado. Navegue com Tab e feche com Escape.',
        'Esperado: foco visivel e contido no dialogo; ao fechar retorna ao controle de origem; campos e botoes acessiveis.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('REGRESSOES DA REVISAO FINAL', [
        'R01 - Trocar de chat durante resposta',
        'Acao: envie no chat A e, durante a geracao, selecione B e digite um rascunho. Volte a A depois da resposta.',
        'Esperado: resposta permanece em A; historico e rascunho de B nao sao alterados. Nenhuma duplicacao ao voltar a A.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'R02 - Contexto preserva pronomes e fatos',
        "Acao: envie My dog is named Kira. e depois What is my dog\'s name?",
        'Esperado: pergunta permanece com my; Reply recupera Kira, sem alterar o ponto de vista do aluno.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'R03 - Traducao e direcao',
        'Acao: selecione cada sentido, use Swap e traduza; edite depois o texto original.',
        'Esperado: idiomas sao sempre distintos, edicao limpa resultado antigo, controles ficam protegidos durante geracao.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'R04 - Inicializacao e encerramento',
        'Acao: com portas livres, use start_linguaforge.sh e depois Ctrl+C. Repita com o modelo ja iniciado separadamente.',
        'Esperado: so anuncia disponibilidade depois de modelo e API prontos; encerra processos que iniciou e preserva o modelo externo.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
        '',
        'R05 - Duas abas no mesmo chat',
        'Acao: envie simultaneamente duas mensagens em duas abas do mesmo chat.',
        'Esperado: se o contexto mudou durante geracao, a segunda operacao orienta recarregar; nenhuma metade de turno ou historico sobrescrito.',
        'Resultado: [ ] passou [ ] falhou  Observacao: _______________________________',
    ]),
    ('CRITERIO DE ACEITACAO', [
        'A V1 pode seguir para entrega quando todos os casos aplicaveis passarem.',
        'Falhas que bloqueiam a entrega: perda de historico, mistura entre chats, ausencia de resposta do tutor com servidor saudavel, traducao salva como chat, exclusao sem confirmacao, ou interface inutilizavel em tela estreita.',
        'Observacoes finais:',
        '______________________________________________________________________________',
        '______________________________________________________________________________',
        '______________________________________________________________________________',
        'Assinatura: _______________________________    Data: _________________________',
    ]),
]

output.parent.mkdir(parents=True, exist_ok=True)
markdown = []
for title, entries in sections:
    markdown.extend([f"## {title}", ""])
    markdown.extend(f"- {entry}" if entry else "" for entry in entries)
    markdown.append("")
output.with_suffix('.md').write_text('\n'.join(markdown) + '\n')

lines = []
for title, entries in sections:
    lines.append(('title', title))
    for entry in entries:
        lines.append(('body', entry))
    lines.append(('body', ''))

# Quebra linhas para gerar PDF simples sem dependências externas.
def wrap(text, width=96):
    if not text:
        return ['']
    words = text.split(' ')
    result, current = [], ''
    for word in words:
        candidate = word if not current else f'{current} {word}'
        if len(candidate) <= width:
            current = candidate
        else:
            result.append(current)
            current = word
    if current:
        result.append(current)
    return result

pages = []
page = []
for style, text in lines:
    wrapped = wrap(text, 88 if style == 'title' else 100)
    required = len(wrapped) + (1 if style == 'title' else 0)
    if len(page) + required > 59:
        pages.append(page)
        page = []
    for item in wrapped:
        page.append((style, item))
    if style == 'title':
        page.append(('body', ''))
if page:
    pages.append(page)

def escape_pdf(text):
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

def stream_for_page(page, number, total):
    commands = ['BT', '/F1 9 Tf', '44 800 Td', '12 TL']
    for style, text in page:
        if style == 'title':
            commands.append('/F2 13 Tf')
        else:
            commands.append('/F1 9 Tf')
        encoded = escape_pdf(text).encode('latin-1', 'replace').decode('latin-1')
        commands.append(f'({encoded}) Tj')
        commands.append('T*')
    commands.extend(['/F1 8 Tf', '0 -8 Td', f'(Pagina {number} de {total}) Tj', 'ET'])
    return '\n'.join(commands).encode('latin-1', 'replace')

objects = []
def add_object(data):
    objects.append(data)
    return len(objects)

catalog_id = add_object(None)
pages_id = add_object(None)
font_regular_id = add_object(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
font_bold_id = add_object(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
page_ids = []
for index, page in enumerate(pages, start=1):
    content = stream_for_page(page, index, len(pages))
    content_id = add_object(b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream')
    page_id = add_object(
        f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] '
        f'/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> '
        f'/Contents {content_id} 0 R >>'.encode('ascii')
    )
    page_ids.append(page_id)
objects[catalog_id - 1] = f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode('ascii')
objects[pages_id - 1] = ('<< /Type /Pages /Kids [' + ' '.join(f'{pid} 0 R' for pid in page_ids) + f'] /Count {len(page_ids)} >>').encode('ascii')

pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
offsets = [0]
for number, obj in enumerate(objects, start=1):
    offsets.append(len(pdf))
    pdf.extend(f'{number} 0 obj\n'.encode('ascii'))
    pdf.extend(obj)
    pdf.extend(b'\nendobj\n')
xref = len(pdf)
pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
pdf.extend(b'0000000000 65535 f \n')
for offset in offsets[1:]:
    pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
pdf.extend(f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('ascii'))
output.write_bytes(pdf)
print(f'{output} ({len(pages)} pages, {len(pdf)} bytes)')
