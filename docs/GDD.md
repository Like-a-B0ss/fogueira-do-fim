# GDD - Fogueira do Fim

## 1. Visao Geral

- `Titulo`: Fogueira do Fim
- `Genero`: survival top-down com gestao de acampamento, simulacao social e defesa contra zumbis
- `Plataforma atual`: PC
- `Tecnologia`: Python + `pygame`
- `Estado do projeto`: vertical slice jogavel com loop completo, mundo procedural, IA de moradores, clima dinamico, audio procedural, combate funcional e progressao de base

## 2. High Concept

O jogador assume o papel de chefe de um acampamento erguido no meio da floresta, tentando manter uma pequena sociedade viva em um mundo procedural hostil. Durante o dia, a comunidade coleta recursos, cozinha, trata feridos, ergue estruturas e se reorganiza. Durante a noite, zumbis rondam a mata, testam a defesa e pressionam a moral do grupo.

O diferencial do jogo esta na mistura de:

- lideranca social
- defesa do acampamento
- progressao estrutural
- exploracao procedural
- clima atmosferico dinamico
- eventos morais e faccoes humanas

## 3. Fantasia do Jogador

O jogo quer entregar a fantasia de:

- liderar uma sociedade fragil no limite
- segurar um acampamento que cresce aos poucos
- improvisar sob pressao
- decidir quem proteger, onde investir e quando arriscar
- equilibrar humanidade e pragmatismo

## 4. Pilares de Design

### 4.1 Sociedade Viva

Cada morador tem:

- papel funcional
- tracos
- cansaco
- insanidade
- confianca no lider
- relacoes com outros moradores
- memoria social de eventos, ordens e conflitos

O objetivo e fazer o acampamento parecer um grupo real, e nao apenas unidades de coleta.

### 4.2 Pressao Diaria

O jogo se estrutura em um ciclo claro:

- `dia`: expansao, producao, coleta, exploracao
- `noite`: defesa, fogo, vigia, resposta a crises

Cada turno do jogador envolve decidir onde gastar tempo e recurso escasso.

### 4.3 Base que Cresce

O acampamento comeca pequeno e se expande em niveis. A base ganha:

- mais espaco
- edificios especializados
- mais area util para circular, construir e respirar melhor dentro da clareira
- melhor leitura visual do chao da base, com terra batida e trilhas internas

### 4.4 Mundo Hostil e Procedural

O mundo gera chunks sob demanda, com biomas, regioes nomeadas, recursos, pontos de interesse, zonas de risco e bosses.

### 4.5 Atmosfera e Clima

O mundo tambem precisa se comunicar pelo ceu, pela luz e pelo som:

- amanhecer e entardecer suaves, sem troca brusca entre dia e noite
- dias nublados, vento e chuva fina alterando a leitura da floresta
- fogueira ganhando mais presenca quando a escuridao e o mau tempo apertam
- neblina, penumbra e audio respondendo ao clima
- trilha procedural com camadas de terror e presenca de zumbis na mata

### 4.6 Escolha com Consequencia

Eventos dinamicos e faccoes colocam o jogador em decisoes morais e praticas:

- salvar ou negar abrigo
- ceder ou impor
- defender a base ou acompanhar uma expedicao

### 4.7 Leitura e Feedback

O jogo precisa comunicar perigo, progresso e estado emocional com clareza:

- feedback visual de dano no combate
- prompts contextuais consistentes
- leitura de prontidao de estruturas
- resposta visivel da sociedade e do mundo as decisoes do lider

## 5. Publico-Alvo

- jogadores que gostam de survival com tomada de decisao
- jogadores que gostam de colony sim simplificado
- jogadores atraidos por atmosfera, tensao e progressao emergente

Referencias de sensacao:

- sobrevivencia em tempo real
- colony management leve
- defesa de base
- narrativa sistemica

## 6. Estrutura da Partida

### 6.1 Inicio

O jogo comeca com:

- acampamento central
- poucos moradores
- oficina, fogao, radio e fogueira
- estoque inicial limitado, mas suficiente para o primeiro ciclo

### 6.2 Meio

O jogador expande:

- barracas construidas manualmente, se quiser abrir mais leitos
- serraria
- cozinha
- enfermaria
- horta
- anexo
- torres

Nesse ponto a sociedade fica mais complexa e as rotinas dos moradores passam a importar muito mais.

### 6.3 Fase Avancada

O jogo abre para:

- expedicoes
- faccoes
- regioes nomeadas
- bosses de zona
- hordas com chefe

## 7. Core Loop

### 7.1 Loop Principal

1. observar o estado da base
2. definir foco do grupo
3. ler o clima, a hora e a janela de risco do momento
4. coletar ou processar recursos
5. construir ou melhorar estruturas
6. resolver crises e eventos
7. segurar a noite e os zumbis
8. amanhecer, consumir recursos e repetir

### 7.2 Loop de Curto Prazo

- cortar arvores
- transformar toras em tabuas
- cozinhar
- tratar feridos
- reparar defesa
- alimentar a fogueira

### 7.3 Loop de Medio Prazo

- ampliar base
- abrir camas
- atrair novos moradores
- desbloquear producao mais eficiente
- estabilizar a sociedade

### 7.4 Loop de Longo Prazo

- explorar regioes distantes
- derrotar bosses
- lidar com faccoes
- consolidar um acampamento maior e mais complexo

## 8. Controles

- `WASD`: mover lider
- `Shift`: correr
- `Mouse`: orientar ataque e interagir com a interface
- `Clique esquerdo` / `Espaco`: atacar
- `E`: interagir
- `Botao direito`: interacao contextual no acampamento, quando o alvo esta ao alcance
- `Q`: acao alternativa ou decisao dura
- `B`: abrir menu de construcao
- `1-7`: selecionar estrutura no menu de build
- `1-4`: definir foco da comunidade fora do menu de build
- `Tab`: alternar entre HUD compacta e HUD completa
- `F5`: salvar
- `F9`: carregar
- `Esc`: sair / voltar / abrir confirmacao

O jogo prioriza o alvo sob o mouse para a interacao quando ele estiver ao alcance, evitando confusao em areas apertadas da base.

## 9. Focos da Comunidade

Os focos alteram a prioridade da IA dos moradores:

- `1 Equilibrio`: comportamento natural do momento
- `2 Suprimentos`: coleta, corte, serraria, estoque
- `3 Fortificar`: reparo, vigia, linha defensiva
- `4 Moral`: fogo, cozinha, clima social e estabilidade

Os focos funcionam como prioridade, nao como ordem absoluta. Necessidades criticas ainda podem sobrepor o foco.

## 10. Sistema de Recursos

### 10.1 Recursos Atuais

- `toras`
- `tabuas`
- `insumos`
- `ervas`
- `sucata`
- `refeicoes`
- `remedios`

### 10.2 Cadeia Produtiva Atual

- arvore -> `toras`
- oficina -> `tabuas` lentas no early game
- serraria -> `tabuas` em escala
- insumos + combustivel -> `refeicoes`
- ervas + sucata -> `remedios`
- horta -> lote pequeno de comida e ervas, seguido de tempo de crescimento

O lider tambem pode operar estruturas chave manualmente para acelerar a base quando a IA nao da conta.

### 10.3 Filosofia

O jogo separa:

- recurso bruto
- recurso processado
- recurso de manutencao

Isso ajuda a criar gargalo, planejamento e progressao.

## 11. Construcoes

### 11.1 Estruturas Atuais

- `Barraca`
- `Torre`
- `Horta`
- `Anexo`
- `Serraria`
- `Cozinha`
- `Enfermaria`

### 11.2 Funcoes

- `Barraca`: camas extras
- `Torre`: vigia especializado
- `Horta`: gera comida e ervas quando madura; entra em regrowth apos colheita
- `Anexo`: reforca manutencao e reparo
- `Serraria`: transforma toras em tabuas
- `Cozinha`: produz refeicoes
- `Enfermaria`: trata e fabrica remedios

### 11.3 Uso Direto pelo Lider

Estruturas que o lider pode usar manualmente:

- `Oficina`: corta algumas tabuas antes da serraria
- `Serraria`: processa toras em tabuas
- `Cozinha`: monta refeicoes
- `Horta`: colhe um pequeno lote quando pronta
- `Anexo`: vira reparo rapido na linha defensiva
- `Torre`: dispara contra zumbis proximos
- `Enfermaria`: trata ferimentos ou prepara remedios

### 11.4 Fluxo de Build

- jogador abre menu com `B`
- escolhe estrutura
- posiciona no espaco valido da base

### 11.5 Pedidos de Obra dos Moradores

Moradores agora podem:

- detectar necessidade da base
- comentar essa necessidade no historico social/chat
- sugerir prioridades para o lider sem posicionar obra no chao
- justificar melhor o pedido conforme o contexto da base

## 12. Acampamento

O acampamento e:

- quadrado
- expansivel em niveis
- cercado por barricadas
- centrado na fogueira
- sensivel ao clima e ao horario

Elementos estruturais:

- oficina
- fogao
- radio
- fogueira
- barracas
- estoque
- palicada e barricadas

Regras importantes atuais:

- as barracas predefinidas ficam fixas e nao se movem com a expansao
- expandir a base nao gera barracas automaticamente
- a linha defensiva preserva upgrades de spikes quando a base cresce
- a expansao reposiciona a defesa para o novo tamanho sem resetar o progresso
- a base possui chao batido mais legivel no centro, com trilhas internas entre estruturas

## 13. Fogueira

A fogueira possui duas camadas:

- `chama`
- `brasa`

Ela influencia:

- moral
- seguranca percebida
- rotina dos moradores
- atmosfera visual e sonora
- leitura da base em dias nublados e noites profundas

O fogo pode ser alimentado com:

- toras
- tabuas

Toras sustentam melhor a brasa; tabuas servem como reforco rapido.

## 14. Moradores

### 14.1 Papeis

- `Lenhador`
- `Vigia`
- `Batedora`
- `Artesa`
- `Cozinheiro`
- `Mensageiro`

### 14.2 Dados por Morador

- nome
- role
- tracos
- vida
- energia
- fome
- moral
- exaustao
- insanidade
- confianca no lider
- relacoes sociais
- memorias sociais recentes
- atribuicao de cama
- atribuicao de edificio

### 14.3 Comportamentos

Os moradores podem:

- coletar recursos
- cortar arvores
- cozinhar
- operar serraria
- tratar
- vigiar
- dormir
- socializar
- defender o acampamento
- sugerir necessidades da base pelo chat
- revelar neblina do mapa quando exploram ou se deslocam vivos pela base e arredores

## 15. Sistema Social

### 15.1 Confianca no Lider

A confianca sobe com:

- presenca do jogador
- boas decisoes
- cuidado com a base
- resposta humana a crises e pedidos

A confianca cai com:

- fome
- crises mal resolvidas
- pressao
- escolhas duras demais
- ordens recusadas ou clima social ruim

### 15.2 Relacoes Internas

Moradores acumulam:

- amizade
- rivalidade
- feudos
- conflitos
- reconciliacoes ocasionais

### 15.3 Memoria Social

Os moradores registram lembrancas sociais de:

- eventos de crise
- pedidos de abrigo
- interacoes com faccoes
- ordens aceitas ou recusadas
- amizades e desentendimentos

Essas memorias afetam falas, obediencia, clima do grupo e a forma como respondem ao lider.

### 15.4 Consequencias Sistêmicas

O sistema social influencia:

- falas contextuais
- resumo emocional nos dialogos
- chance de aceitar melhor uma diretriz
- formacao de pares que trabalham melhor juntos
- desgaste quando rivais convivem perto demais

### 15.5 Insanidade e Exaustao

Esses sistemas empurram a sociedade para estados mais instaveis, como:

- rondar a base
- dormir em horarios criticos
- quebrar moral
- entrar em fuga ou desercao

## 16. Eventos Dinamicos

Eventos atuais:

- `doenca`
- `incendio`
- `fuga`
- `desercao`
- `pedido de abrigo`
- `alarme`
- `evento de faccao`
- `socorro de expedicao`

Cada evento tem:

- timer
- urgencia
- posicao
- alvo
- consequencia de sucesso ou falha

Eventos de `abrigo` e `faccao` tambem colocam um visitante fisico no mapa, surgindo em um ponto aleatorio nas laterais do acampamento.

## 17. Faccoes

Faccoes atuais:

- `Andarilhos`
- `Ferro-Velho`
- `Vigias da Estrada`

O sistema de faccao controla:

- reputacao
- rotulo da relacao
- eventos de encontro
- recompensas e perdas sociais

O jogador responde com:

- `E`: linha mais humana
- `Q`: linha mais dura

Visitantes de faccao e abrigo possuem:

- presenca visual no mundo
- animacao leve de espera
- fala curta em balao quando o lider se aproxima

## 18. Combate

### 18.1 Jogador

O lider:

- ataca em curto alcance
- corta arvores com o mesmo golpe base
- reage a zumbis perto da base e da exploracao
- aplica stagger e knockback diferentes conforme o tipo de inimigo
- recebe feedback visual de dano para reforcar leitura de perigo

### 18.2 Moradores

A defesa e automatica e depende de:

- papel
- condicao fisica
- foco da base
- contexto de invasao

### 18.3 Zumbis

Tipos atuais:

- walker
- runner
- brute
- howler
- raider
- bosses

Comportamentos atuais:

- rondar acampamento
- atacar barricada quando realmente proximos da base
- perseguir alvo na floresta e no entorno
- chamar reforcos
- surgir na floresta
- liderar hordas
- executar comportamentos mais fortes por variante, como charge, slam, grito e furia de boss

### 18.4 Bosses de Zona

Chefes territoriais:

- defendem sua regiao
- engajam o jogador quando encontrados na selva
- ficam mais perigosos conforme perdem vida
- servem como marco de progressao e risco regional

## 19. Mundo Procedural

### 19.1 Estrutura

O mundo usa:

- chunks
- biomas
- regioes nomeadas
- features ambientais
- pontos de interesse
- clima dinamico
- luz continua ao longo do dia

### 19.2 Biomas Atuais

- floresta
- campos
- pantano
- ruinas
- cinzas frias
- bosque gigante
- pedreira morta

### 19.3 Bosses de Zona

Cada regiao pode ter:

- nome proprio
- bioma dominante
- boss territorial
- status persistente de derrota

### 19.4 Clima e Luz

Estados climaticos atuais:

- ceu limpo
- ceu nublado
- vento nas copas
- chuva fina

Efeitos atuais:

- altera a penumbra geral do mapa
- muda neblina e atmosfera visual
- interfere na presenca da fogueira
- afeta audio e leitura do ambiente
- adiciona peso em expedicoes e riscos secundarios

A passagem entre dia e noite usa um fator continuo de luminosidade, deixando amanhecer e entardecer mais suaves.

## 20. Expedicoes

O sistema atual permite:

- enviar equipe pelo radio
- acompanhar a caravana
- lidar com combate na trilha
- responder a pedido de socorro
- perder membros no caminho
- trazer loot raro por regiao

## 21. Interface

### 21.1 HUD

Mostra:

- clima
- tensao
- recursos
- estado da fogueira
- leitura atmosferica do momento pela luz e neblina
- objetivos do chefe
- sociedade
- historico social e chat
- modo compacto e modo completo para aliviar a tela durante exploracao e combate

Tambem ha:

- prompts contextuais que priorizam o alvo sob o mouse
- painel do chefe com vida, folego e contexto de descanso
- feedback de dano no combate
- confirmacao de saida com salvar, sair sem salvar ou cancelar

### 21.2 Tela Inicial

Possui:

- tela cheia
- simulacao viva ao fundo
- novo jogo
- continuar
- configuracoes em aba separada quando o jogador clica no botao
- saida
- sequencia de dicas

### 21.3 HUD de Sociedade

O painel dos moradores agora tem:

- scroll
- cards compactos
- clique para expandir detalhes
- leitura melhor do estado emocional e social

### 21.4 Apresentacao dos Eventos

Eventos humanos importantes aparecem no mundo com:

- visitante visivel
- anel de destaque
- texto contextual ao aproximar
- escolha `E` ou `Q` quando aplicavel

## 22. Audio

O audio atual e procedural, sem depender de arquivos externos. Ja existem:

- efeitos de ataque
- impactos
- clima
- passos
- trilha procedural
- ambiencia de fogueira
- clima de horda
- resposta sonora para nublado, vento e chuva
- camadas de terror mais presentes a noite
- zumbis distantes e presenca hostil na mata

## 23. Arte e Direcao Visual

Direcao atual:

- top-down estilizado
- sem assets externos
- atmosfera de floresta sombria
- contraste entre calor do acampamento e frieza do exterior
- neblina e iluminacao dinamicas
- clima visual com nuvens, chuva e variacao gradual de luminosidade
- base com centro de terra batida e leitura mais marcada dos caminhos internos

## 24. Cenas e Fluxo

Fluxo atual:

1. `Title`
2. `Tips`
3. `Gameplay`
4. `Game Over`

## 25. Condicoes de Falha

O jogo entra em derrota quando:

- o lider morre
- nao restam sobreviventes
- a moral media da sociedade despenca demais

## 26. Estado Tecnico Atual

Arquitetura principal:

- `main.py`: entrada
- `game/session.py`: coordenacao geral
- `game/world.py`: regras, procedural e simulacao
- `game/actors.py`: jogador, moradores e zumbis
- `game/rendering.py`: mundo, HUD e telas
- `game/audio.py`: audio procedural
- `game/input.py`: entrada
- `game/models.py`: dataclasses

Detalhes tecnicos atuais:

- Python 3 + `pygame`
- renderizacao top-down sem assets externos obrigatorios
- audio sintetizado em runtime
- save e load manual por arquivo
- neblina do mapa com cache para aliviar custo de render
- estrutura modular com helpers de HUD, UI, dialogo e sistema social

Modulos auxiliares:

- `game/dialogue_helpers.py`
- `game/ui_helpers.py`
- `game/hud_rendering_helpers.py`

Sistema social movido para camada de dominio:

- `game/domain/camp_social.py` - Relacoes, conflitos e dinamica social do acampamento

## 27. Riscos Atuais

- `Game` ainda centraliza muitas responsabilidades
- `world.py` ainda esta grande
- varias mecanicas profundas dependem mais de tuning do que de implementacao nova
- falta playtest manual prolongado para curva de dificuldade e progressao
- balanceamento de combate, economia e crescimento social ainda precisa de iteracao longa

## 28. Oportunidades de Evolucao

- comercio entre faccoes
- ataques humanos
- memoria longa de decisoes morais em escala de campanha
- mais tipos de chefe e mutacoes
- craft mais profundo
- agricultura e doencas mais sistemicas
- narrativa emergente por temporadas
- sistema de campanha

## 29. Resumo do Estado Atual

`Fogueira do Fim` ja funciona como um survival top-down sistemico com:

- base expansivel
- moradores com IA
- cadeia produtiva
- eventos dinamicos
- faccoes
- expedicoes
- bosses de zona
- hordas
- exploracao procedural
- clima dinamico
- clima social
- audio procedural atmosferico
- combate com variantes mais legiveis

O projeto ja passou da fase de prototipo visual simples e hoje se posiciona como uma simulacao de acampamento survival com combate, lideranca, tensao atmosferica e mundo procedural.
