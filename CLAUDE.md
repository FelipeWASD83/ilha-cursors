# CLAUDE.md: ilha-cursors

Esquemas de ponteiro do Windows inspirados na `ilha` (pedido do Felipe em 02/11/2026: "cursor moderno, tema preto e
branco, outline da cor inversa, inspirado na ilha"). Dois esquemas, preto com contorno branco e branco com contorno
preto. O README explica o uso; aqui ficam as decisões e as armadilhas. Código em inglês, docs e changelog em
português. **Repositório público** (`FelipeWASD83/ilha-cursors`, MIT), escolha dele ao criar.

## Como é feito

- Python puro (numpy + Pillow). Cada ponteiro é uma lista de camadas de campos de distância (`ilhacursors/sdf.py`,
  `shapes.py`) em unidades de uma tela de 32 x 32; `render.py` desenha com 3 x 3 de superamostragem, contorno de
  1,9 unidade na cor inversa (era 1,5 na 1.0.0; ele pediu mais grosso) e sombra desfocada. Uma camada "body" posterior corta com o contorno dela as de baixo:
  é o que separa a bolha da seta.
- Linguagem da ilha: pílulas, cantos arredondados, bolha ao lado da seta (estado dividido com bolha) e o cometa em
  órbita 3D inclinada (o que fica atrás é menor e mais apagado) com a pílula inchando por uma mola periódica (no "Ocupado").
- **Pedidos dele na 1.0.1** (02/11/2026): seta mais arredondada (polígono menor inflado por 1,95 e o canto de dentro
  com filete; a 1ª tentativa, com 2,2 e filete 2,2, virou uma gota e foi descartada), mão sem os traços entre os
  dedos e "Trabalhando" só com bolinhas girando, sem a pílula de fundo (cada bolinha é um "body" com contorno).
- **Bolsões mais estreitos que o contorno viram furinhos:** no "mover", com contorno 1,9, sobravam pontinhos do
  fundo entre as cabeças vizinhas. Uma camada "ink" em losango (`POCKET`) por baixo pinta esses bolsões na cor do
  contorno. Engrossou o contorno de novo: conferir o "mover" em 48 e 128 px.
- **Transições de entrada (1.1.0)**, pedido dele ("clique, transição entre várias animações"): clique não existe em
  esquema de ponteiro (o Windows não avisa o cursor). Cada cursor menos a seta toca uma entrada de 16 quadros
  (24 no ocupado) e depois segura o último quadro por um dia (`HOLD`), ou entra no loop repetido até ~60 mil
  passos (`MAX_STEPS`). Os quadros não se repetem no arquivo: `seq ` e `rate` do `.ani` apontam e cronometram.
  `morph_intro` mistura o campo da seta (com a ponta no hotspot do destino, encolhida só o necessário para caber)
  com o do destino; `pop_intro` faz a parte nova crescer de um ponto; a mola é `ease`.
- **Misturar dois campos de distância cria retalhos**: o contorno engorda onde o campo muda devagar e aparece
  contorno vazio onde uma parte fina está nascendo. Por isso o campo é renormalizado pelo gradiente e a camada
  é "morph", cujo contorno só existe a até 1,9 + 0,3 de algum preenchimento (`render._morph_outline`).
- **Não verificado:** que o Windows recomeça a animação do quadro 0 a cada troca de cursor. Se não recomeçar, a
  entrada toca só na primeira vez e o cursor fica parado na forma final (não quebra nada). Conferir na tela exige
  mexer o mouse dele: só com a permissão dele.
- Arquivos escritos à mão em `fileformats.py`: `.cur` com BMP 32 bits e máscara AND, `.ani` RIFF ACON com um `.cur`
  por quadro, 96 quadros a 1 jiffy (60 fps, 1,6 s por volta; na 1.0.0 eram 48 a 30 fps).
- Saída em `build/` (fora do git, ~30 MB). `install.py` gera se faltar.

## Armadilhas (medidas)

- **O `.ani` aceita até 65.535 passos** (65.524 carrega, 65.536 não, 02/11/2026) e tempo por passo de até
  0xFFFFFFFF jiffies (o `GetCursorFrameInfo` devolve o valor certo); o `HOLD` usa um dia para não estourar
  conta de milissegundos.
- **60 fps é o teto do cursor animado no Windows.** O tempo de quadro do `.ani` é um inteiro em jiffies (1/60 s):
  com 1 carrega (o `GetCursorFrameInfo` devolve 1), com 0 o Windows recusa o arquivo (26300, 02/11/2026). Ele
  pediu 250 e depois 144: não existem nesse formato. O `.ani` de 96 quadros e 4 tamanhos tem 9,4 MB e carrega.
- **O Windows recusa `.ani` com mais de 4 tamanhos por quadro** (26300, 02/11/2026: 4 carrega, 5 não, sem erro,
  `LoadCursorFromFile` só devolve nulo). Por isso os animados levam 32, 48, 64 e 128. O `.cur` estático aceita os 6
  (32 a 256).
- **Instalador em Python, não em PowerShell:** o `SystemParametersInfo` precisaria de `Add-Type`, que compila DLL, e
  o Smart App Control barra DLL compilada aqui.
- **Rodar o `install.py` num terminal normal**, não pelo shell do app do Claude (MSIX): registro e pastas podem ser
  virtualizados. Os arquivos vão para `%USERPROFILE%\.ilha-cursors` pelo mesmo motivo da `ilha` (fora do AppData).
- Aplicar o esquema mexe no registro do usuário (`HKCU\Control Panel\Cursors`): agente não roda o `install.py` sem
  ele pedir. O primeiro install guarda os valores de antes em `backup.json`, que o `--uninstall` devolve; installs
  seguintes não sobrescrevem esse backup.

## Release (formato igual ao do `clave`, `relogio-mond` e `ilha`)

- `versao.json` (`versao`, `repositorio`) anda junto com `VERSION` do `generate.py` e o topo do `CHANGELOG.md`;
  o `ferramentas\publicar-versao.ps1` recusa se os três e o `build\manifest.json` não baterem.
- O pacote é `ilha-cursors-<versão>.zip` (pasta `ilha-cursors/` dentro): `build\black`, `build\white`,
  `build\manifest.json`, `install.py`, `install.bat`, README, LICENSE, CHANGELOG e `versao.json`. Instalar a partir
  dele só pede Python (sem numpy nem Pillow), porque o `build` já vem pronto. É a mesma pasta que o
  `desktop-glow` embute. Sem `-SoGerar` o script faz a release no GitHub (**decisão do Felipe**).
- Ramo principal aqui é `master` (os outros projetos usam `main`).

## Conferir

- `python preview.py`: carrega cada arquivo pela API do Windows em todos os tamanhos, confere o hotspot, o número
  de passos e os tempos (`GetCursorFrameInfo`) e desenha as
  folhas de prévia com o que o próprio Windows pinta. Sai com código 1 se algo falhar.
- `python -m unittest discover -s tests`: lógica do instalador contra um registro falso.
