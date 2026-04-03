# Spec-Driven Development (SDD) - Fogueira do Fim

## Objetivo

Este documento estabelece as especificações técnicas e funcionais que devem guiar todas as tasks de desenvolvimento do projeto Fogueira do Fim. Toda implementação deve ser rastreável a este documento.

---

## 1. Especificações Arquiteturais

### 1.1 Estrutura de Diretórios

```
game/
├── main.py                    # Entry point
├── session.py                 # Coordenacao geral do jogo
├── world.py                   # Regras, procedural e simulacao
├── actors.py                  # Jogador, moradores e zumbis
├── rendering.py               # Renderizacao principal
├── audio.py                   # Audio procedural
├── input.py                   # Sistema de entrada
├── models.py                  # Dataclasses e modelos de dados
├── dialogue_helpers.py        # Helpers de dialogo
├── hud_rendering_helpers.py   # Helpers de HUD
├── audio_runtime.py           # Runtime de audio
├── audio_synthesis.py         # Sintese de audio
├── entity_rendering.py        # Renderizacao de entidades
├── domain/                    # Logica de dominio
│   └── camp_social.py         # Sistema social do acampamento
├── infrastructure/            # Infraestrutura tecnica
└── application/               # Casos de uso
```

### 1.2 Padrões Arquiteturais

- **Separação de Responsabilidades**: Cada modulo deve ter responsabilidade unica
- **Dependency Injection**: Evitar acoplamento forte entre modulos
- **Event-Driven**: Sistemas se comunicam via eventos quando possivel
- **Data-Oriented**: Preferir composicao sobre heranca

### 1.3 Convenções de Código

- **Nomes**: snake_case para variaveis/funcoes, PascalCase para classes
- **Idioma**: Comentarios e documentacao em portugues sem acentos
- **Tipagem**: Usar type hints em todas as funcoes publicas
- **Imports**: Ordem: stdlib, terceiros, modulos locais
- **Docstrings**: Usar docstrings para classes e funcoes complexas

---

## 2. Especificações Funcionais

### 2.1 Sistema de Jogo

#### 2.1.1 Ciclo Dia/Noite

```python
# Especificacao tecnica
class CicloDiaNoite:
    """
    Gerencia transicao suave entre dia e noite.
    
    Regras:
    - Fator de luz continua entre 0.0 (noite) e 1.0 (dia)
    - Transicao gradual sem saltos bruscos
    - Influencia gameplay: visao, spawn de zumbis, comportamentos
    """
    fator_luz: float  # 0.0 a 1.0
    periodo: str      # "madrugada", "manha", "tarde", "noite"
    
    def atualizar(self, delta_time: float) -> None:
        """Atualiza iluminacao de forma continua."""
        pass
```

#### 2.1.2 Sistema de Clima

```python
# Especificacao tecnica
class SistemaClima:
    """
    Gerencia estados climaticos dinamicos.
    
    Estados suportados:
    - ceu_limpo: visibilidade normal
    - nublado: penumbra leve
    - vento: efeito visual nas arvores
    - chuva: penalidades de movimento e visao
    
    Efeitos:
    - Altera iluminacao global
    - Modifica neblina e atmosfera
    - Afeta audio ambiente
    """
    estado_atual: str
    intensidade: float  # 0.0 a 1.0
    duracao_restante: float
```

### 2.2 Sistema de Recursos

#### 2.2.1 Cadeia Produtiva

```
ARVORE → toras → [OFICINA/SERRARIA] → tabuas
INSUMOS + combustivel → [COZINHA] → refeicoes
ERVAS + sucata → [ENFERMARIA] → remedios
HORTA → (tempo) → comida + ervas
```

#### 2.2.2 Armazenamento

```python
# Especificacao tecnica
class Estoque:
    """
    Gerencia recursos do acampamento.
    
    Recursos validos:
    - toras: recurso bruto de madeira
    - tabuas: recurso processado
    - insumos: materia-prima para comida
    - ervas: materia-prima para remedios
    - sucata: componente de remedios
    - refeicoes: consumo de sobreviventes
    - remedios: tratamento de feridos
    
    Regras:
    - Capacidade maxima: 999 por recurso
    - Sempre verificar antes de adicionar
    - Logar transacoes significativas
    """
    recursos: Dict[str, int]
    capacidade_maxima: int = 999
    
    def adicionar(self, recurso: str, quantidade: int) -> bool:
        """Adiciona recurso se houver capacidade."""
        pass
    
    def consumir(self, recurso: str, quantidade: int) -> bool:
        """Consome recurso se houver disponibilidade."""
        pass
```

### 2.3 Sistema de Construcao

#### 2.3.1 Estruturas Disponiveis

| Estrutura     | Custo                   | Funcao                          | Operavel por Lider |
|---------------|-------------------------|---------------------------------|-------------------|
| Barraca       | 8 tabuas                | +1 cama                         | Nao               |
| Torre         | 15 tabuas + 5 sucata    | Vigia especializado             | Sim (dispara)     |
| Horta         | 5 tabuas + 3 insumos    | Produz comida/ervas             | Sim (colhe)       |
| Anexo         | 12 tabuas               | Acelera reparos                 | Sim (repara)      |
| Serraria      | 20 tabuas + 10 sucata   | Processa toras → tabuas         | Sim (opera)       |
| Cozinha       | 15 tabuas + 5 sucata    | Processa refeicoes              | Sim (cozinha)     |
| Enfermaria    | 20 tabuas + 10 ervas    | Trata + produz remedios         | Sim (trata)       |

#### 2.3.2 Regras de Posicionamento

```python
# Especificacao tecnica
class SistemaConstrucao:
    """
    Gerencia construcao de estruturas.
    
    Regras de posicionamento:
    - Dentro dos limites do acampamento
    - Nao sobrepor estruturas existentes
    - Respeitar espaco minimo entre construcoes
    - Verificar recursos disponiveis antes de confirmar
    
    Fluxo:
    1. Jogador abre menu (B)
    2. Seleciona estrutura (1-7)
    3. Posiciona em local valido
    4. Confirma com clique
    5. Recursos sao deduzidos
    6. Estrutura aparece no mapa
    """
    estrutura_selecionada: Optional[str]
    modo_construcao: bool
    
    def pode_construir(self, x: int, y: int, estrutura: str) -> bool:
        """Verifica se posicao e valida para construcao."""
        pass
```

### 2.4 Sistema de Combate

#### 2.4.1 Tipos de Inimigos

| Tipo     | Vida | Velocidade | Dano | Comportamento Especial      |
|----------|------|------------|------|----------------------------|
| Walker   | 30   | Lenta      | 10   | Persegue lentamente        |
| Runner   | 20   | Rapida     | 15   | Persegue agressivamente    |
| Brute    | 100  | Muito Lenta| 30   | Carga devastadora          |
| Howler   | 15   | Media      | 5    | Chama reforcos             |
| Raider   | 40   | Rapida     | 20   | Ataca estruturas           |
| Boss     | 200+ | Variavel   | 40+  | Padroes complexos          |

#### 2.4.2 Mecanicas de Combate

```python
# Especificacao tecnica
class SistemaCombate:
    """
    Gerencia combate jogador vs zumbis.
    
    Mecanicas:
    - Jogador ataca em curto alcance
    - Diferentes tipos de inimigo reagem diferente:
      * Walker: knockback leve
      * Runner: stagger rapido
      * Brute: resistente a stagger
      * Howler: foge ao ser atingido
    - Feedback visual de dano obrigatorio
    - Moradores defendem automaticamente
    
    Regras de equilibrio:
    - Dano basico do jogador: 20
    - Cooldown entre ataques: 0.5s
    - Alcance de ataque: 40 pixels
    """
    dano_base: int = 20
    cooldown_ataque: float = 0.5
    alcance_ataque: int = 40
    
    def processar_ataque(self, atacante, alvo) -> ResultadoAtaque:
        """Processa um ataque e retorna resultado."""
        pass
```

### 2.5 Sistema Social

#### 2.5.1 Atributos de Morador

```python
# Especificacao tecnica
@dataclass
class Morador:
    """
    Representa um morador do acampamento.
    
    Atributos obrigatorios:
    - nome: identificador unico
    - role: papel funcional (Lenhador, Vigia, Batedora, Artesa, Cozinheiro, Mensageiro)
    - vida: 0-100
    - energia: 0-100
    - fome: 0-100 (aumenta com tempo)
    - moral: 0-100
    - exaustao: 0-100
    - insanidade: 0-100
    - confianca_lider: 0-100
    - relacoes: Dict[str, int]  # nome -> nivel de relacao
    - memorias: List[MemoriaSocial]
    - cama_atribuida: Optional[str]
    - edificio_atribuido: Optional[str]
    
    Tracos disponiveis:
    - "bravo": bônus em combate
    - "calmo": resistencia a insanidade
    - "trabalhador": bônus em coleta
    - "lider": influencia outros
    - "fragil": penalidade de vida maxima
    - "genio": bônus em craft
    """
    nome: str
    role: str
    tracos: List[str]
    vida: int
    energia: int
    fome: int
    moral: int
    exaustao: int
    insanidade: int
    confianca_lider: int
    relacoes: Dict[str, int]
    memorias: List['MemoriaSocial']
    cama_atribuida: Optional[str]
    edificio_atribuido: Optional[str]
```

#### 2.5.2 Sistema de Confianca

```python
# Especificacao tecnica
class SistemaConfianca:
    """
    Gerencia nivel de confianca dos moradores no lider.
    
    Aumenta com:
    - Presenca ativa do jogador (+1 por ciclo)
    - Boas decisoes em eventos (+5 a +10)
    - Cuidado com a base (+2)
    - Resposta humanitaria a crises (+5)
    
    Diminui com:
    - Fome prolongada (-2 por ciclo)
    - Crises mal resolvidas (-10)
    - Escolhas duras demais (-5 a -15)
    - Ausencia do lider (-1 por ciclo)
    
    Consequencias:
    - Confianca < 30: morador pode desobedecer
    - Confianca < 15: morador pode desertar
    - Confianca < 5: morador tenta fugir
    """
    def calcular_mudanca_confianca(self, morador: Morador, evento: str) -> int:
        """Calcula mudanca de confianca baseada em evento."""
        pass
```

### 2.6 Sistema de Eventos

#### 2.6.1 Tipos de Eventos

```python
# Especificacao tecnica
class TipoEvento(Enum):
    DOENCA = "doenca"              # Morador adoece
    INCENDIO = "incendio"          # Estrutura pega fogo
    FUGA = "fuga"                  # Morador tenta fugir
    DESERCAO = "desercao"          # Morador abandona acampamento
    PEDIDO_ABRIGO = "pedido_abrigo" # Pedido de abrigo
    ALARME = "alarme"              # Alarme de zumbis
    EVENTO_FACCAO = "evento_faccao" # Evento de faccao
    SOCORRO_EXPEDICAO = "socorro_expedicao"  # Pedido de socorro

@dataclass
class Evento:
    """
    Representa um evento dinamico no jogo.
    
    Atributos obrigatorios:
    - tipo: TipoEvento
    - timer: tempo restante em segundos
    - urgencia: 1-10 (afeta consequencias)
    - posicao: (x, y) no mapa
    - alvo: entidade afetada
    - consequencia_sucesso: Dict
    - consequencia_falha: Dict
    
    Regras:
    - Eventos com urgencia >= 8 devem ter feedback visual imediato
    - Eventos de faccao e abrigo geram visitante fisico no mapa
    - Timer = 0 dispara consequencia de falha automaticamente
    """
    tipo: TipoEvento
    timer: float
    urgencia: int
    posicao: Tuple[int, int]
    alvo: Optional[str]
    consequencia_sucesso: Dict
    consequencia_falha: Dict
```

### 2.7 Sistema de Faccoes

#### 2.7.1 Faccoes Disponiveis

| Faccao            | Caracteristica              | Recursos Oferecidos |
|-------------------|----------------------------|---------------------|
| Andarilhos        | Nomades, neutros           | Informacao, mapa    |
| Ferro-Velho       | Tecnicos, pragmaticos      | Sucata, tecnologia  |
| Vigias da Estrada | Organizados, defensivos    | Armas, protecao     |

#### 2.7.2 Sistema de Reputacao

```python
# Especificacao tecnica
class SistemaReputacao:
    """
    Gerencia relacoes com faccoes.
    
    Niveis de reputacao:
    - Hostil: < -50 (atacam ao ver)
    - Desconfiado: -50 a -10 (evitam contato)
    - Neutro: -10 a 10 (relacao normal)
    - Amigavel: 10 a 50 (comercio possivel)
    - Aliado: > 50 (apoio ativo)
    
    Acoes do jogador afetam reputacao:
    - E (humanitario): +5 com todos, -2 com pragmaticos
    - Q (pragmatico): +5 com pragmaticos, -5 com humanitarios
    
    Visitantes:
    - Aparecem fisicamente no mapa
    - Possuem animacao de espera
    - Falam ao jogador se aproximar
    - Espera decisao (E ou Q) por tempo limitado
    """
    reputacoes: Dict[str, int]  # faccao -> valor
```

### 2.8 Sistema de Exploracao

#### 2.8.1 Geração Procedural

```python
# Especificacao tecnica
class GeradorMundo:
    """
    Gera chunks procedurais sob demanda.
    
    Estrutura:
    - Tamanho do chunk: 512x512 pixels
    - Biomas: floresta, campos, pantano, ruinas, cinzas_frias, bosque_gigante, pedreira_morta
    - Features: arvores, rochas, recursos, pontos de interesse
    - Regioes nomeadas com bosses territoriais
    
    Regras de geracao:
    - Chunks sao gerados quando jogador se aproxima
    - Chunks sao persistidos no save
    - Bosses derrotados permanecem derrotados
    - Recursos coletados nao respawname (exceto horta)
    """
    tamanho_chunk: int = 512
    biomas: List[str]
    
    def gerar_chunk(self, x: int, y: int) -> Chunk:
        """Gera chunk na posicao especificada."""
        pass
```

#### 2.8.2 Sistema de Neblina

```python
# Especificacao tecnica
class SistemaNeblina:
    """
    Gerencia neblina de guerra do mapa.
    
    Regras:
    - Areas nao exploradas sao escuras
    - Areas ja exploradas ficam visiveis
    - Moradores revelam neblina ao explorar
    - Cache de renderizacao para performance
    
    Performance:
    - Manter cache de areas reveladas
    - Atualizar cache apenas quando necessario
    - Evitar recalculo desnecessario
    """
    areas_reveladas: Set[Tuple[int, int]]
    cache_render: Dict[Tuple[int, int], Surface]
```

### 2.9 Sistema de Audio

#### 2.9.1 Audio Procedural

```python
# Especificacao tecnica
class SistemaAudio:
    """
    Gerencia audio procedural em tempo real.
    
    Tipos de som:
    - Efeitos: ataque, impacto, passos
    - Ambiente: clima, fogueira, natureza
    - Musica: trilha procedural com camadas
    - Terror: camadas noturnas de tensao
    
    Regras:
    - Nenhum arquivo externo obrigatorio
    - Sintese em runtime
    - Responde ao clima e horario
    - Camadas de terror aumentam a noite
    """
    def reproduzir_efeito(self, tipo: str, volume: float = 1.0) -> None:
        """Reproduz efeito sonoro sintetizado."""
        pass
    
    def atualizar_ambiente(self, clima: str, horario: float) -> None:
        """Atualiza sons ambiente baseado em contexto."""
        pass
```

### 2.10 Sistema de Interface

#### 2.10.1 HUD Principal

```python
# Especificacao tecnica
class HUD:
    """
    Gerencia interface heads-up display.
    
    Elementos obrigatorios:
    - Clima e tensao (topo)
    - Recursos principais (topo direito)
    - Estado da fogueira (topo direito)
    - Objetivos do chefe (lateral)
    - Painel de sociedade (lateral direita)
    - Historico social/chat (inferior)
    - Painel do chefe com vida/folego (inferior esquerdo)
    
    Modos:
    - Compacto: durante exploracao e combate
    - Completo: durante gestao do acampamento
    
    Interacao:
    - Tab: alterna entre modos
    - Clique em morador: expande detalhes
    - Scroll no painel de sociedade
    """
    modo_compacto: bool
    
    def renderizar(self, tela: Surface) -> None:
        """Renderiza HUD no modo atual."""
        pass
```

#### 2.10.2 Sistema de Prompts

```python
# Especificacao tecnica
class SistemaPrompts:
    """
    Gerencia prompts contextuais de interacao.
    
    Regras:
    - Priorizar alvo sob o mouse
    - Mostrar prompt quando alvo esta ao alcance
    - Indicar teclas disponiveis (E, Q, etc)
    - Feedback visual de alcance
    
    Exemplos:
    - "E - Cozinhar" ao passar perto da cozinha
    - "E - Tratar / Q - Remedios" na enfermaria
    - "E - Aceitar / Q - Recusar" em eventos de faccao
    """
    alcance_interacao: int = 50
    
    def calcular_prompt(self, jogador_pos: Tuple[int, int], 
                        entidades: List[Entidade]) -> Optional[str]:
        """Calcula prompt contextual baseado em posicoes."""
        pass
```

---

## 3. Especificações Tecnicas de Implementacao

### 3.1 Performance

#### 3.1.1 Targets de Performance

```python
# Especificacao tecnica
"""
Targets de performance:
- FPS alvo: 60 FPS estaveis
- Uso de memoria: < 500 MB em condicoes normais
- Tempo de carregamento: < 3 segundos
- Latencia de input: < 16ms

Otimizacoes obrigatorias:
- Cache de renderizacao para neblina
- Pool de objetos para projeteis e efeitos
- Culling de entidades fora da tela
- Batch rendering quando possivel
- Evitar alocacoes em loop principal
"""
```

#### 3.1.2 Profile de Performance

```python
# Especificacao tecnica
"""
Pontos de atencao para profiling:
1. Renderizacao de neblina
2. Atualizacao de pathfinding
3. Processamento de eventos sociais
4. Geracao procedural de chunks
5. Sintese de audio

Ferramentas recomendadas:
- cProfile para profiling de CPU
- memory_profiler para memoria
- pygame.time.get_ticks() para medir tempo de frames
"""
```

### 3.2 Persistencia

#### 3.2.1 Sistema de Save/Load

```python
# Especificacao tecnica
class SistemaSave:
    """
    Gerencia salvamento e carregamento de partidas.
    
    Formato: JSON com compressao opcional
    
    Dados salvos:
    - Estado do mundo (chunks, biomas, regioes)
    - Estado do acampamento (estruturas, recursos)
    - Estado dos moradores (todos os atributos)
    - Estado do jogador (posicao, atributos)
    - Historico de eventos e decisoes
    - Reputacao com faccoes
    - Configuracoes de usuario
    
    Regras:
    - F5: salva rapido
    - F9: carrega rapido
    - Validar dados ao carregar
    - Backup automatico a cada 5 minutos
    """
    def salvar(self, slot: int = 0) -> bool:
        """Salva estado atual do jogo."""
        pass
    
    def carregar(self, slot: int = 0) -> bool:
        """Carrega estado salvo."""
        pass
```

### 3.3 Testes

#### 3.3.1 Cobertura de Testes

```python
# Especificacao tecnica
"""
Cobertura minima exigida:
- Logica de recursos: 80%
- Sistema de combate: 80%
- Sistema social: 70%
- Geracao procedural: 70%
- Sistema de eventos: 75%

Tipos de teste:
- Unitarios: funcoes puras e logica de negocio
- Integracao: interacao entre sistemas
- Regressao: bugs corrigidos devem ter teste

Frameworks:
- pytest para testes unitarios
- mocks para isolar sistemas
"""
```

### 3.4 Seguranca

#### 3.4.1 Validação de Dados

```python
# Especificacao tecnica
"""
Pontos de validacao obrigatorios:
1. Input do usuario (teclas, cliques)
2. Dados de save files (JSON malformado, valores invalidos)
3. Parametros de construcao (posicao, recursos)
4. Acoes de moradores (IA deve validar antes de executar)

Regras:
- Nunca confiar em dados externos
- Validar ranges de valores numericos
- Sanitizar strings antes de usar
- Logar erros de validacao
"""
```

---

## 4. Especificações de Qualidade

### 4.1 Legibilidade de Codigo

```python
# Especificacao tecnica
"""
Padroes de legibilidade:
- Funcoes com no maximo 30 linhas
- Arquivos com no maximo 500 linhas
- Comentar logica complexa
- Nomes auto-explicativos
- Evitar numeros magicos (usar constantes)

Exemplo bom:
MAX_RECURSOS = 999
CAPACIDADE_BARRACA = 1

def pode_adicionar_recurso(estoque: Estoque, recurso: str) -> bool:
    return estoque.recursos.get(recurso, 0) < MAX_RECURSOS

Exemplo ruim:
def pode_add(e, r):
    return e[r] < 999
"""
```

### 4.2 Documentacao

```python
# Especificacao tecnica
"""
Regras de documentacao:
1. Toda classe publica deve ter docstring
2. Toda funcao publica deve ter docstring
3. Complexidade alta deve ser explicada em comentarios
4. Atualizar docs/GDD.md quando mudar mecanicas
5. Atualizar este SDD quando mudar especificacoes

Formato de docstring:
'''
Descricao curta da funcao.

Descricao mais detalhada se necessario.

Args:
    parametro1: Descricao do parametro.
    parametro2: Descricao do parametro.

Returns:
    Descricao do retorno.

Raises:
    ExcecaoQueLanca: Quando lanca.
'''
"""
```

### 4.3 Controle de Versao

```python
# Especificacao tecnica
"""
Regras de commit:
1. Commits atomicos (uma feature/fix por commit)
2. Mensagens claras e em portugues
3. Referenciar issue/feature quando aplicavel
4. Nao commitar arquivos de log ou cache
5. Manter .gitignore atualizado

Formato de mensagem:
tipo: descricao curta

Tipos validos:
- feat: nova feature
- fix: correcao de bug
- refactor: refatoracao
- docs: documentacao
- test: testes
- chore: tarefas de manutencao

Exemplo:
feat: implementa sistema de confianca dos moradores

Adiciona SistemaConfianca que gerencia relacao entre moradores
e lider. Implementa calculo de mudancas baseado em eventos e
consequencias para niveis baixos de confianca.
"""
```

---

## 5. Especificações de Gameplay

### 5.1 Balanceamento

#### 5.1.1 Economia de Recursos

```python
# Especificacao tecnica
"""
Valores de referencia para balanceamento:

Producao:
- 1 arvore = 3-5 toras
- 1 tora = 2 tabuas (oficina) ou 4 tabuas (serraria)
- 1 refeicao = 2 insumos + 1 combustivel
- 1 remedio = 2 ervas + 1 sucata

Consumo:
- Cada morador come 1 refeicao/dia
- Fogueira consome 1 tora/hora ou 2 tabuas/hora
- Estruturas precisam de reparo a cada 3 dias

Custos de construcao ver tabela em 2.3.1.
"""
```

#### 5.1.2 Curva de Dificuldade

```python
# Especificacao tecnica
"""
Curva de dificuldade almejada:

Dias 1-3:
- Tutorial implicito
- Poucos zumbis
- Recursos abundantes
- Eventos simples

Dias 4-7:
- Introducao de runners
- Eventos de faccao
- Escassez comeca
- Primeiras escolhas morais

Dias 8-14:
- Hordas organizadas
- Bosses de zona
- Gestao social critica
- Recursos escassos

Dias 15+:
- Endgame
- Desafios de supervivencia
- Progressao de base avancada
- Narrativa emergente
"""
```

### 5.2 Experiencia do Usuario

#### 5.2.1 Feedback ao Jogador

```python
# Especificacao tecnica
"""
Tipos de feedback obrigatorio:

Visual:
- Dano: flash vermelho + screen shake
- Sucesso: animacao de confirmacao
- Perigo: indicador de direcao
- Progresso: barras e numeros claros

Sonoro:
- Acoes: efeitos para cada interacao
- Ambiente: clima e tensao
- Alertas: eventos urgentes

Textual:
- Prompts contextuais
- Historico de eventos
- Dialogos de moradores
- Mensagens de sistema
"""
```

#### 5.2.2 Acessibilidade

```python
# Especificacao tecnica
"""
Features de acessibilidade obrigatórias:
- Tamanho de fonte ajustavel
- Contraste suficiente (WCAG AA minimo)
- Opcao de desativar screen shake
- Configuracao de volume separado (efeitos, musica, ambiente)
- Rebind de teclas (futuro)

Features desejaveis:
- Modo daltonico
- Indicadores de audio visuais
- Velocidade de jogo ajustavel
"""
```

---

## 6. Especificações de Task

### 6.1 Formato de Task

```markdown
## [ID] Titulo da Task

### Tipo
- Feature / Bugfix / Refactor / Docs / Test / Chore

### Prioridade
- Critica / Alta / Media / Baixa

### Estimativa
- Pontos de historia (1, 2, 3, 5, 8, 13)

### Descricao
Descricao clara do que deve ser feito.

### Criterios de Aceitacao
- [ ] Criterio 1
- [ ] Criterio 2
- [ ] Criterio 3

### Especificacoes Relacionadas
- SDD Secao X.Y.Z

### Dependencias
- Task ABC (se aplicavel)

### Notas Tecnicas
Detalhes de implementacao relevantes.
```

### 6.2 Workflow de Task

```
1. Backlog → Task criada com especificacoes
2. Ready → Task bem definida, sem bloqueios
3. In Progress → Desenvolvedor trabalha na task
4. Review → Código pronto, aguardando revisao
5. Done → Task completa e mergeada
```

### 6.3 Checklist de Task

```markdown
Antes de mover para Done:
- [ ] Codigo implementado
- [ ] Testes escritos e passando
- [ ] Documentacao atualizada
- [ ] Code review aprovado
- [ ] Sem regressoes conhecidas
- [ ] Especificacoes do SDD respeitadas
```

---

## 7. Especificações de Release

### 7.1 Versionamento

```
Seguindo Semantic Versioning (MAJOR.MINOR.PATCH):

MAJOR: Mudancas incompativeis
MINOR: Novas features compativeis
PATCH: Bugfixes compativeis

Exemplos:
- 1.0.0: Release inicial
- 1.1.0: Nova mecanica de faccoes
- 1.1.1: Correcao de bug de save
- 2.0.0: Reescrita do sistema de combate
```

### 7.2 Checklist de Release

```markdown
Pre-release:
- [ ] Todos os tests passando
- [ ] Documentacao atualizada
- [ ] docs/GDD.md atualizado
- [ ] docs/SDD.md atualizado
- [ ] Changelog preparado
- [ ] Versao incrementada

Post-release:
- [ ] Tag criada no git
- [ ] Binarios compilados
- [ ] Release notes publicadas
```

---

## 8. Referencias

### 8.1 Documentos Relacionados

- `docs/GDD.md`: Game Design Document completo
- `README.md`: Instrucoes de setup e execucao
- `docs/OPTIMIZATION_REPORT.md`: Relatorio de otimizacoes

### 8.2 Tecnologias

- **Python 3.x**: Linguagem principal
- **pygame**: Framework de jogo
- **pytest**: Framework de testes

### 8.3 Inspiracoes

- RimWorld: Sistema social e gestao de colonia
- Project Zomboid: Sobrevivencia e crafting
- State of Decay: Base building e recursos
- The Long Dark: Atmosfera e sobrevivencia

---

## 9. Apêndices

### 9.1 Glossario

- **Chunk**: Unidade de mapa gerada proceduralmente
- **Neblina de Guerra**: Mecanica de mapa nao explorado
- **Faccoes**: Grupos de sobreviventes externos ao acampamento
- **Boss de Zona**: Inimigo forte que guarda uma regiao
- **Stack**: Efeito que se acumula (ex: dano, status)
- **Cooldown**: Tempo de espera entre acoes

### 9.2 Constantes do Jogo

```python
# Dimensoes
TAMANHO_TILE = 32
TAMANHO_CHUNK = 512
LARGURA_TELA = 1280
ALTURA_TELA = 720
FPS_ALVO = 60

# Gameplay
DURACAO_DIA = 300  # segundos
MAX_MORADORES = 20
MAX_RECURSOS = 999
ALCANCE_INTERACAO = 50

# Combate
DANO_BASE_JOGADOR = 20
COOLDOWN_ATAQUE = 0.5
ALCANCE_ATAQUE = 40
```

---

## 10. Controle de Mudancas

| Versao | Data       | Autor           | Mudancas                        |
|--------|------------|-----------------|--------------------------------|
| 1.0.0  | 2024-XX-XX | Leonardo Paes   | Criacao inicial do documento   |

---

**Este documento e a fonte unica de verdade para especificacoes tecnicas. Toda task deve ser rastreavel a este documento.**

