# Fogueira do Fim

Prototipo top-down em `pygame` focado em atmosfera, direcao visual e gestao de uma pequena sociedade em um acampamento no meio da floresta enquanto hordas de zumbis pressionam a defesa.

## Conceito

- Voce e o chefe do acampamento.
- Cada partida monta trilhas, ruinas, pantanos, clareiras e bosques de forma procedural.
- Cada sobrevivente tem papel proprio, necessidades e rotina diaria.
- De dia a comunidade coleta, cozinha, reforca barricadas e organiza o campo.
- A noite os zumbis saem da mata, testam a palicada e obrigam o lider a reagir.
- O visual e procedural, sem assets externos: fogueira animada, neblina, paleta quente/fria e HUD cinematografica.
- A interface agora tem tela inicial completa, menu principal navegavel e painel de configuracoes para audio, neblina, tremor e contraste da HUD.
- O mapa agora inclui nevoa de exploracao e pontos de interesse ligados aos biomas.
- O mundo agora continua gerando para alem da clareira, com chunks procedurais conforme voce avanca.
- O audio agora gera efeitos, passos por terreno, clima, gemidos de horda e trilha procedural em runtime.
- O acampamento agora tem formato quadrado, pode crescer pela oficina e abre novas camas, barracas e linhas de barricada.
- Moradores seguem ciclos de sono, revezam vigia e novos sobreviventes podem chegar quando houver espaco e estabilidade.
- Barracas e barracas extras agora contam como leitos fisicos com colisao, e o chefe tambem pode dormir para acelerar as horas enquanto o campo tenta se manter sozinho.
- As barracas agora foram redesenhadas como abrigos mais completos, com leitura visual melhor no acampamento e uso claro como ponto de descanso.
- O jogo agora mostra prompts contextuais perto do alvo interagivel mais proximo, indicando exatamente o que `E` ou `Q` vao fazer.
- O jogo agora tem menu de construcao com barracas extras, torres, hortas e anexos de oficina.
- Vigias, cozinheiros e artesas podem se especializar automaticamente em predios do acampamento.
- Madeira agora vem de arvores reais do mapa: cortar perto do acampamento desmata a regiao e empurra a coleta cada vez mais para longe.
- Novos biomas e variantes de recursos aparecem longe do campo, incluindo cinzas frias, bosque gigante e pedreira morta.
- A Fase 1 da cadeia produtiva agora esta ativa: toras entram na serraria, insumos passam pela cozinha e ervas abastecem a enfermaria.
- O estoque central virou parte real da simulacao, com recursos brutos e processados separados no HUD e no acampamento.
- A fogueira agora trabalha em duas camadas, `chama` e `brasa`, com combustivel pesado sustentando melhor a noite e os moradores ajudando quando o fogo cai.
- A Fase 2 agora entrou na sociedade: cada morador tem traços, nivel de confianca no lider, exaustao acumulada e relacoes de amizade ou rivalidade.
- Brigas podem surgir quando a pressao sobe, e laços fortes ajudam a segurar a moral ao redor da fogueira.
- A Fase 3 agora traz crises dinamicas no proprio acampamento, incluindo fuga, doenca, incendio, desercao e pedido de abrigo.
- A Fase 4 agora introduz faccoes humanas com reputacao persistente e encontros morais de resposta humana ou pragmatica.
- A Fase 5 agora abre o mundo em regioes nomeadas persistentes, com bosses de zona ligados ao bioma e exploracao realmente sem borda pratica.
- Zumbis agora ficaram mais agressivos e variados: podem surgir na floresta durante o dia, rondar a base, chamar reforcos, formar hordas com boss e aparecer com perfis mais perigosos.
- A sociedade agora tambem pode quebrar por dentro: moradores acumulam insanidade, rondam a base sob pressao e exigem mais presenca, fogo e estabilidade para nao desandar.

## Controles

- `WASD`: mover
- `Shift`: correr
- `Clique esquerdo` ou `Espaco`: atacar
- `Clique esquerdo` perto de arvores: cortar e recolher madeira
- `E`: interagir com recursos, barricadas, fogueira ou sobreviventes
- `E` perto de uma barraca: dormir e acelerar o tempo; qualquer comando acorda o chefe
- `E` perto de uma crise ativa: responder ao evento antes que o tempo acabe
- `Q` perto de uma faccao: escolher a resposta dura ou pragmatica na decisao moral
- `E` na oficina: ampliar o acampamento quando houver toras e sucata
- `E` perto da enfermaria: tratar o chefe usando remedios ou ervas do estoque
- `B`: abrir ou fechar o menu de construcao
- `1-7` com o menu aberto: selecionar o tipo de estrutura
- `Clique esquerdo` com o menu aberto: posicionar a estrutura
- `1`: foco equilibrado
- `2`: foco em suprimentos
- `3`: foco em fortificacao
- `4`: foco em moral
- `F5`: salvar o estado atual do acampamento
- `F9`: carregar o ultimo save manual
- `Enter`: iniciar ou reiniciar
- `Setas` ou `WASD` na tela inicial: navegar pelo menu e pelas configuracoes
- `Mouse` na tela inicial: clicar em `Continuar`, `Novo Jogo`, `Sair` e ajustar configuracoes
- `Esc`: voltar para a tela inicial

## Loop do jogo

- Mantenha a fogueira acesa para sustentar a moral.
- Use toras para sustentar a brasa e tabuas so para reacender rapido quando o fogo estiver fraco.
- Observe a confianca no lider, a exaustao e os feudos do grupo na HUD social.
- Reaja rapido a crises do campo: febre, fogo, fuga e abrigo agora competem pela sua atencao.
- Acompanhe o humor das faccoes e use `E` ou `Q` para decidir como sua lideranca vai ser lembrada.
- Colete toras, insumos, ervas e sucata nas redondezas.
- Derrube arvores para obter toras e aceite que a clareira vai ficando mais vazia com o tempo.
- Passe as toras pela serraria para transformar volume bruto em tabuas de construcao.
- Monte cozinhas para converter insumos em refeicoes e enfermarias para transformar ervas em cura.
- Repare barricadas danificadas antes do anoitecer.
- Abra o menu de construcao para erguer barracas, torres, hortas, anexos, serrarias, cozinhas e enfermarias.
- Use as barracas como leitos reais: moradores dormem nelas, voce tambem pode deitar e deixar a sociedade se virar por algumas horas.
- Use o foco comunitario para orientar a prioridade diaria da IA.
- Explore sinais do mapa para ativar eventos de bioma e descobrir recursos raros.
- Atravesse regioes nomeadas, leia a HUD de zona e prepare o grupo antes de despertar um boss territorial.
- Elimine zumbis que cruzarem o anel defensivo.
- Leia as barras de vida dos zumbis, identifique variantes mais pesadas e trate noites de horda como um evento de defesa total.

## Requisitos

```bash
pip install pygame
```

## Executar

```bash
python main.py
```

## Estrutura

- `main.py`: ponto de entrada do jogo
- `game/config.py`: constantes, paleta e helpers
- `game/models.py`: dataclasses do mundo
- `game/input.py`: leitura e mapeamento de controles
- `game/camera.py`: camera 2D do mundo
- `game/audio.py`: facade de audio do jogo
- `game/scenes.py`: estados/cenas da sessao
- `game/actors.py`: player, sobreviventes e zumbis
- `game/world.py`: geracao procedural e regras do mapa
- `game/rendering.py`: desenho do mundo, HUD e telas
- `game/session.py`: loop principal, estado e eventos

## Smoke test

Util para validar inicializacao sem jogar manualmente:

```bash
$env:SDL_VIDEODRIVER="dummy"
python main.py --smoke-test
```
