# Fogueira do Fim

Protótipo top-down em `pygame` sobre liderança, sobrevivência e gestão social em um acampamento cercado por floresta, clima hostil e mortos-vivos.

O jogo mistura exploração procedural, construção de base, rotina autônoma dos moradores, crises emergentes, expedições e defesa noturna. Tudo é desenhado em runtime, sem depender de assets externos.

## Destaques

- Mundo procedural com clareiras, ruínas, pântanos, bosques, pedreiras e regiões nomeadas.
- Acampamento vivo com moradores que dormem, vigiam, coletam, conversam, brigam, criam laços e lembram eventos importantes.
- Cadeia produtiva com toras, tábuas, comida, ervas, sucata, refeições e remédios.
- Construções com função estratégica: barraca, torre, horta, anexo, serraria, cozinha, enfermaria e estoque.
- Estoque com capacidade real, limites visíveis no HUD e perda de suprimentos quando incêndios atingem áreas de armazenamento.
- Fogueira em duas camadas, `chama` e `brasa`, afetando moral, segurança e rotina da base.
- Clima dinâmico com chuva, vento, neblina, efeitos visuais na câmera e impacto na atmosfera.
- Expedições com rota física no mapa, risco de morte, retorno com recompensas e chance de trazer ameaças até a base.
- Zumbis com comportamento agressivo, hordas, variantes e pressão crescente durante a noite.
- Tarefas do chefe, eventos morais, facções humanas, pedidos de abrigo, doenças, deserções, incêndios e crises sociais.
- Áudio procedural com ambiente, vento, chuva, passos, ataques, interface e tela escondida para testar sons.

## Requisitos

- Python 3.12 ou compatível
- `pygame`

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Executar

```bash
python main.py
```

No Windows, também funciona:

```powershell
py .\main.py
```

## Controles

- `WASD`: mover o chefe
- `Shift`: correr
- `Clique esquerdo` ou `Espaço`: atacar
- `E`: interagir com o alvo atual
- `Botão direito`: interagir diretamente com o alvo sob o mouse
- `Q`: resposta dura/pragmática em eventos morais
- `B`: abrir ou fechar o menu de construção
- `1-8` com o menu aberto: selecionar estrutura
- `Clique esquerdo` com o menu aberto: posicionar construção
- `1`: foco equilibrado
- `2`: foco em suprimentos
- `3`: foco em fortificação
- `4`: foco em moral
- `Tab`: alternar HUD compacta
- `M`: abrir painel de volume durante a partida
- `F10`: abrir tela escondida de teste de áudio
- `F5`: salvar
- `F9`: carregar
- `Enter`: confirmar, avançar dicas ou reiniciar
- `Esc`: cancelar, pular dicas ou abrir confirmação de saída

## Loop do Jogo

Durante o dia, organize a base, colete recursos, converse com moradores, aprove construções, mande expedições e prepare a defesa. À noite, mantenha a fogueira acesa, segure a moral e impeça que zumbis atravessem as barricadas.

Prioridades importantes:

- Alimente a fogueira antes da noite.
- Transforme toras em tábuas na oficina ou na serraria.
- Use a cozinha para preparar refeições.
- Use a enfermaria para tratar ferimentos e preparar remédios.
- Construa estoques para aumentar os limites de suprimentos.
- Reforce barricadas e use torres quando houver ameaça próxima.
- Fale com moradores para manter confiança e descobrir tensões.
- Reaja rápido a incêndios, doenças, fugas, deserções e pedidos de socorro.
- Leia o painel de tarefas do chefe para entender o próximo objetivo prático.

## Construções

- `Barraca`: aumenta a quantidade de camas.
- `Torre`: ajuda na defesa e reduz risco de ataques.
- `Horta`: gera comida e ervas com o tempo.
- `Anexo`: melhora manutenção e reforço de barricadas.
- `Serraria`: transforma toras em tábuas com mais eficiência.
- `Cozinha`: converte insumos em refeições e ajuda a moral.
- `Enfermaria`: trata ferimentos, doenças e prepara remédios.
- `Estoque`: aumenta a capacidade de toras, tábuas, sucata, comida, refeições, ervas e remédios.

## Smoke Test

Útil para validar inicialização sem abrir janela real:

```powershell
$env:SDL_VIDEODRIVER="dummy"
py .\main.py --smoke-test
```

## Configuração

O arquivo `game_settings.json` concentra ajustes principais:

- tela, resolução, fullscreen e FPS
- tamanho do mundo e posição do acampamento
- duração do dia e horários de amanhecer/anoitecer
- recursos iniciais e fogo inicial
- volumes e opções de apresentação
- intensidade e duração dos climas
- paleta de cores e cores de papéis
- modo de teste com `testing.unlimited_resources`

Se o arquivo estiver ausente ou incompleto, o jogo usa os fallbacks internos de [game/core/config.py](game/core/config.py).

## Estrutura do Projeto

- [main.py](main.py): ponto de entrada.
- [game/app/session.py](game/app/session.py): estado principal da sessão e loop do jogo.
- [game/application](game/application): fluxo de gameplay, título, carregamento e ciclo da sessão.
- [game/core](game/core): configuração, modelos, input, câmera e cenas.
- [game/domain](game/domain): regras de acampamento, combate, eventos, recursos e mundo.
- [game/entities](game/entities): chefe, moradores e zumbis.
- [game/rendering](game/rendering): mundo, HUD, telas, construções, clima e entidades.
- [game/audio](game/audio): síntese, runtime e sistema de áudio.
- [game/infrastructure](game/infrastructure): save/load.
- [game/ui](game/ui): layouts e helpers de interface.

## Save

O save manual usa `savegame.json` na raiz do projeto. Use `F5` para salvar e `F9` para carregar durante a partida.
