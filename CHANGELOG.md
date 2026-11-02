# Changelog

## 1.0.2 (02/11/2026)

**Mudou**
- "Ocupado" e "Trabalhando" agora animam a 60 quadros por segundo (eram 30), o máximo que o Windows aceita
  em cursor animado. A volta continua levando 1,6 s.

## 1.0.1 (02/11/2026)

**Mudou**
- Contorno mais grosso em todos os ponteiros.
- A seta está mais arredondada, nas pontas e no canto de dentro (vale também para ajuda, trabalhando, local e pessoa).
- A mão do link não tem mais os traços entre os dedos.
- "Trabalhando em segundo plano" agora são só bolinhas girando ao lado da seta, sem a pílula de fundo.

## 1.0.0 (02/11/2026)

**Novo**
- Dois esquemas de ponteiro inspirados na Ilha: "Ilha preto" (preto com contorno branco) e "Ilha branco" (branco com
  contorno preto), com os 17 ponteiros do Windows e sombra macia.
- "Ocupado" e "Trabalhando" animados: a pílula incha com mola e um cometa orbita dentro dela em 3D, como nas animações
  de carregamento da ilha.
- Cada ponteiro em vários tamanhos (32 a 256 px; os animados até 128), para o controle de tamanho do Windows.
- Instalador que registra os dois esquemas, aplica um e desfaz tudo com `--uninstall`.
