# CLAUDE.md: ilha-cursors

Esquemas de ponteiro do Windows inspirados na `ilha` (pedido do Felipe em 02/11/2026: "cursor moderno, tema preto e
branco, outline da cor inversa, inspirado na ilha"). Dois esquemas, preto com contorno branco e branco com contorno
preto. O README explica o uso; aqui ficam as decisões e as armadilhas. Código em inglês, docs e changelog em
português.

## Como é feito

- Python puro (numpy + Pillow). Cada ponteiro é uma lista de camadas de campos de distância (`ilhacursors/sdf.py`,
  `shapes.py`) em unidades de uma tela de 32 x 32; `render.py` desenha com 3 x 3 de superamostragem, contorno de
  1,5 unidade na cor inversa e sombra desfocada. Uma camada "body" posterior corta com o contorno dela as de baixo:
  é o que separa a bolha da seta.
- Linguagem da ilha: pílulas, cantos arredondados, bolha ao lado da seta (estado dividido com bolha) e o cometa em
  órbita 3D inclinada (o que fica atrás é menor e mais apagado) com a pílula inchando por uma mola periódica.
- Arquivos escritos à mão em `fileformats.py`: `.cur` com BMP 32 bits e máscara AND, `.ani` RIFF ACON com um `.cur`
  por quadro, 48 quadros a 2 jiffies (30 fps, 1,6 s).
- Saída em `build/` (fora do git, ~30 MB). `install.py` gera se faltar.

## Armadilhas (medidas)

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

## Conferir

- `python preview.py`: carrega cada arquivo pela API do Windows em todos os tamanhos, confere o hotspot e desenha as
  folhas de prévia com o que o próprio Windows pinta. Sai com código 1 se algo falhar.
- `python -m unittest discover -s tests`: lógica do instalador contra um registro falso.
