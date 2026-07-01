# Sistema de Dados FCA — Fundação Campeões do Amanhã

Sistema de tratamento de dados e BI para a FCA (João Pessoa/PB): natação,
futebol, basquete, ginástica, voleibol, jiu-jitsu, tênis e triathlon.

Fonte dos dados: 9 planilhas Google Sheets (1 mestre + 8 de matrícula, uma
por modalidade), lidas ao vivo via Google Sheets API.

## Status atual

**Camada 1 (ETL) construída e testada** com dados sintéticos no mesmo
formato dos exemplos reais levantados (parser de turma, de-para de locais,
deduplicação por CPF). Ainda **não foi rodada contra as planilhas reais** —
falta configurar as credenciais (veja abaixo). Camadas 2 (dashboard) e 3
(relatórios) ainda não foram construídas: a ideia é validar os números da
Camada 1 com dados reais antes de avançar, conforme combinado.

## Estrutura de pastas

```
sports-data/
├── config/
│   ├── modalidades.yaml       # cadastro das 8 modalidades + variável de ambiente do Sheet ID de cada uma
│   └── locais_mapping.yaml    # de-para "nome do local na matrícula" -> "nome oficial na planilha mestre"
├── src/fca/
│   ├── config.py               # carrega .env + YAMLs em um objeto Settings
│   ├── db/
│   │   ├── models.py           # schema do banco (SQLAlchemy)
│   │   └── session.py          # engine/sessão SQLite
│   ├── etl/
│   │   ├── cpf.py              # normalização/validação de CPF
│   │   ├── turma_parser.py     # extrai local/dias/turno/faixa etária/horário do campo de turma
│   │   ├── locais_mapping.py   # resolve o de-para de locais
│   │   ├── dedup.py            # deduplicação por CPF (reenvio de formulário)
│   │   ├── sheets_client.py    # conector Google Sheets (gspread)
│   │   └── pipeline.py         # orquestra tudo acima em um sync completo
│   ├── dashboard/              # Camada 2 — ainda não implementada
│   └── reports/                # Camada 3 — ainda não implementada
├── scripts/sync.py             # CLI: init-db / sync
├── tests/                      # testes automatizados (pytest)
└── data/fca.db                 # banco SQLite local (gerado, não versionado)
```

## Schema do banco (SQLite)

| Tabela | O que guarda |
|---|---|
| `modalidades` | As 8 modalidades. |
| `locais` | Locais oficiais por modalidade (aba "Locais - Contatos"). |
| `locais_aliases` | De-para carregado de `config/locais_mapping.yaml`. |
| `vagas` | Vagas ofertadas/preenchidas por modalidade (aba "Vagas 2026"). |
| `atletas` | Uma linha por CPF normalizado (pessoa única). |
| `matriculas` | Matrícula **ativa** (já deduplicada) de um atleta em uma modalidade. |
| `matriculas_descartadas` | Log de auditoria: todo registro superado por reenvio de formulário. Nada é apagado, só deixa de contar como ativo. |
| `log_erros_parsing` | Avisos de dado que o pipeline não conseguiu tratar sozinho (local não mapeado, CPF ausente/inválido, campo de turma não reconhecido) — é a base dos indicadores de qualidade de dados da Camada 2. |

Detalhes de cada coluna estão comentados diretamente em `src/fca/db/models.py`.

## Como as regras de tratamento foram implementadas

- **Parser de turma** (`etl/turma_parser.py`): um motor de extração por
  regex compartilhado entre modalidades (porque os "tokens" — local, dias,
  turno, faixa etária, horário — são os mesmos, só a ordem/pontuação muda),
  mas registrado como configuração por modalidade (`MODALIDADE_PARSERS`),
  para que uma modalidade com formato realmente diferente possa ganhar uma
  função própria sem afetar as outras. Testado com os 6 exemplos reais do
  levantamento (Futebol, Voleibol, Jiu-jitsu, Natação, Tênis, Triathlon).
- **De-para de locais** (`etl/locais_mapping.py` + `config/locais_mapping.yaml`):
  editável por você, sem precisar mexer em código. Já vem com os dois
  exemplos reais mapeados (Arena Funcionários, Ginásio Ronaldão). Quando o
  pipeline encontra um local que não bate nem com o nome oficial nem com um
  alias cadastrado, ele **não descarta o registro** — grava a matrícula sem
  local e cria um aviso em `log_erros_parsing` (tipo `local_nao_mapeado`)
  para você mapear manualmente.
- **Deduplicação por CPF** (`etl/dedup.py`): agrupa por CPF normalizado
  dentro da mesma modalidade, mantém o registro de `Carimbo de data/hora`
  mais recente como ativo, e grava os demais em `matriculas_descartadas`
  com o motivo `duplicata_cpf_superada`. Testado com o caso real do
  Lindemberg (mesmo CPF, dois envios, nomes com grafia diferente).

## Configuração

### 1. Ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Credenciais do Google Sheets (necessário para rodar `sync`)

O sistema lê as planilhas via **Service Account** do Google Cloud:

1. Crie (ou peça para criar) um projeto no Google Cloud Console, habilite
   a **Google Sheets API** e a **Google Drive API**.
2. Crie uma Service Account e gere uma chave JSON.
3. **Compartilhe cada uma das 9 planilhas** (a mestre + as 8 de matrícula)
   com o e-mail da Service Account (algo como
   `nome@projeto.iam.gserviceaccount.com`), como leitor.
4. Salve o JSON localmente, por exemplo em `credentials/service_account.json`
   (essa pasta já está no `.gitignore` — nunca commite esse arquivo).
5. Copie `.env.example` para `.env` e preencha:
   - `FCA_GOOGLE_SERVICE_ACCOUNT_FILE`: caminho para o JSON.
   - `FCA_SHEET_ID_MESTRE` e um `FCA_SHEET_ID_<MODALIDADE>` para cada uma
     das 8 planilhas de matrícula. O Sheet ID é o trecho da URL entre
     `/d/` e `/edit` (ex: `docs.google.com/spreadsheets/d/ESTE_TRECHO/edit`).

Não tenho como validar isso sem esses IDs — me passe as credenciais e os
9 IDs (pode ser um por vez, o sistema roda com o que estiver configurado
e avisa quais modalidades ficaram de fora).

### 3. Inicializar e sincronizar

```bash
python scripts/sync.py init-db   # cria as tabelas em data/fca.db
python scripts/sync.py sync      # lê as planilhas e atualiza o banco
```

O comando `sync` imprime um resumo (atletas, matrículas ativas,
duplicatas resolvidas, avisos de parsing) ao final.

### 4. Rodar os testes

```bash
python -m pytest
```

Os testes não acessam o Google Sheets real — usam dados de exemplo no
mesmo formato dos dados reais para validar parser, de-para, deduplicação
e o pipeline completo.

## Como adicionar/editar o de-para de locais

Abra `config/locais_mapping.yaml` e adicione uma entrada na modalidade
correspondente:

```yaml
modalidades:
  futebol:
    aliases:
      - alias: "NOME COMO APARECE NA MATRÍCULA"
        oficial: "Nome oficial exatamente como está na aba Locais - Contatos"
```

Não precisa reiniciar nada — o arquivo é recarregado a cada `sync`.

## Próximos passos

1. Você fornece as credenciais e os 9 Sheet IDs.
2. Rodamos `sync` contra os dados reais e validamos os números batendo
   com o que você já sabe da planilha mestre (ex: Futebol = 174 vagas
   preenchidas).
3. Ajustamos `config/locais_mapping.yaml` para os locais que aparecerem
   como não mapeados.
4. Construímos a Camada 2 (dashboard) e a Camada 3 (relatórios em
   Excel/PDF) em cima do banco já validado.
