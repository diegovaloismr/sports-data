"""Nomes de coluna das planilhas do Google Sheets - fonte única da verdade.

As 8 planilhas de matrícula (geradas por Google Forms) têm a coluna do
nome do atleta e a do nome do responsável com o MESMO texto de cabeçalho
("NOME COMPLETO" duplicado), o que quebra qualquer leitura por nome de
coluna. Por isso a leitura de matrícula é feita por POSIÇÃO (ver
etl/sheets_client.py), usando `COLUNAS_MATRICULA_EM_ORDEM` como as chaves
canônicas - a ordem foi confirmada nos dados reais das 8 planilhas.
"""

COL_CARIMBO = "Carimbo de data/hora"
COL_NOME = "NOME COMPLETO"
COL_NASCIMENTO = "DATA DE NASCIMENTO"
COL_CPF = "CPF"
COL_SEXO = "SEXO"
COL_BAIRRO = "BAIRRO"
COL_CIDADE = "CIDADE"
COL_ESTADO = "ESTADO"
COL_TELEFONE = "TELEFONE / WHATSAPP PARA CONTATO"
COL_NOME_RESPONSAVEL = "NOME COMPLETO (RESPONSÁVEL)"
COL_TELEFONE_RESPONSAVEL = "TELEFONE (RESPONSÁVEL)"
COL_EMAIL = "E-MAIL"
COL_BENEFICIO = "A FAMÍLIA RECEBE ALGUM BENEFÍCIO SOCIAL?"
COL_ESCOLARIDADE = "ESCOLARIDADE"
COL_MODELO_ENSINO = "MODELO DE ENSINO ESCOLAR DO ATLETA"
COL_TURNO_ESTUDO = "TURNO QUE ESTUDA"
COL_TURMA = "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO"
COL_TERMO_AUTORIZACAO = "Termo de autorização"

# Ordem confirmada nos dados reais (18 colunas). Usada para montar os dicts
# de cada linha de matrícula por posição, ignorando o cabeçalho real da
# planilha (que tem nomes duplicados).
COLUNAS_MATRICULA_EM_ORDEM = [
    COL_CARIMBO,
    COL_NOME,
    COL_NASCIMENTO,
    COL_CPF,
    COL_SEXO,
    COL_BAIRRO,
    COL_CIDADE,
    COL_ESTADO,
    COL_TELEFONE,
    COL_NOME_RESPONSAVEL,
    COL_TELEFONE_RESPONSAVEL,
    COL_EMAIL,
    COL_BENEFICIO,
    COL_ESCOLARIDADE,
    COL_MODELO_ENSINO,
    COL_TURNO_ESTUDO,
    COL_TURMA,
    COL_TERMO_AUTORIZACAO,
]

# Planilha de Vagas: também tem colunas extras com cabeçalho vazio, então é
# lida por posição também (só as 4 primeiras colunas importam).
MASTER_VAGAS_MODALIDADE = "Modalidade Esportiva"
MASTER_VAGAS_OFERTADAS = "Vagas Ofertadas"
MASTER_VAGAS_PREENCHIDAS = "Vagas Preenchidas"
MASTER_VAGAS_OCUPACAO = "Ocupação (%)"

COLUNAS_VAGAS_EM_ORDEM = [
    MASTER_VAGAS_MODALIDADE,
    MASTER_VAGAS_OFERTADAS,
    MASTER_VAGAS_PREENCHIDAS,
    MASTER_VAGAS_OCUPACAO,
]

# Planilha de Locais: título mesclado na linha 1, cabeçalho real na linha 2
# (sem duplicidade) - essa é lida por nome de coluna normalmente.
MASTER_LOCAIS_MODALIDADE = "Modalidade"
MASTER_LOCAIS_LOCAL = "Local"
MASTER_LOCAIS_ENDERECO = "Endereço"
MASTER_LOCAIS_HORARIOS = "Horários de Atendimentos"
MASTER_LOCAIS_PROFESSORES = "Professores Responsáveis / Contato"
