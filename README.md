# Cursores da Ilha

Um conjunto de ponteiros do mouse para o Windows inspirado na [Ilha](https://github.com/FelipeWASD83/ilha): formas de pílula, cantos macios,
uma bolha ao lado da seta (como a ilha dividida com bolha) e o cometa orbitando em 3D das animações de carregamento
dela. Preto e branco, com o contorno sempre na cor inversa, em dois esquemas:

- **Ilha preto**: preto com contorno branco (o visual da pílula da ilha).
- **Ilha branco**: branco com contorno preto.

São os 17 ponteiros que o Windows usa (seleção normal, ajuda, trabalhando, ocupado, precisão, texto, manuscrito, não
disponível, os quatro de redimensionar, mover, seleção alternativa, link, local e pessoa). "Ocupado" e "Trabalhando"
são animados: no "Ocupado" a pílula incha com mola e um cometa dá a volta dentro dela; no "Trabalhando", bolinhas
giram ao lado da seta, cada uma com o próprio contorno.

Cada ponteiro vem em vários tamanhos dentro do mesmo arquivo (32 até 256 px; os animados até 128), então o controle
de tamanho do ponteiro do Windows continua funcionando sem ficar borrado.

## Como instalar

Num terminal normal (fora do app do Claude), dentro desta pasta:

```powershell
python install.py
```

ou dois cliques em `install.bat`. Ele copia os cursores para `%USERPROFILE%\.ilha-cursors`, registra os dois esquemas
e aplica o preto na hora. Outras opções:

| Comando | O que faz |
|---|---|
| `python install.py --variant white` | aplica o branco |
| `python install.py --register-only` | só deixa os dois esquemas na lista, sem trocar o ponteiro atual |
| `python install.py --uninstall` | devolve os ponteiros que estavam antes da primeira instalação |

Depois de instalado, dá para trocar entre os dois pelo Windows: **Configurações > Bluetooth e dispositivos > Mouse >
Configurações adicionais do mouse > Ponteiros**, campo **Esquema**.

## Mudar o desenho

O desenho é todo vetorial, em `ilhacursors/shapes.py` (uma função por ponteiro). Depois de mexer:

```powershell
python generate.py
python preview.py
```

O `generate.py` monta os arquivos em `build/black` e `build/white` (fora do git; `--png` também solta as imagens
cruas em `build/png`). O `preview.py` abre cada arquivo pela API do próprio Windows, confere o ponto de clique de cada
tamanho e desenha `build/preview-black.png`, `build/preview-white.png` e as tiras das animações
(`build/preview-anim-*.png`) sobre fundo claro, escuro e colorido. Ele não muda nada no sistema. Rodar o
`install.py` de novo depois aplica o desenho novo.

Valores fáceis de ajustar, em `ilhacursors/render.py`: `OUTLINE` (espessura do contorno, 1.9 = 1,9 px no tamanho
32), `SHADOW_ALPHA` (força da sombra, 0 tira) e `SHADOW_SIGMA` (quanto a sombra espalha).

Testes do instalador (com registro falso, não mexem no sistema): `python -m unittest discover -s tests`.
