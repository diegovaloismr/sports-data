from fca.etl.cpf import is_cpf_valido, normalize_cpf


def test_normalize_removes_pontuacao():
    assert normalize_cpf("101.671.714-88") == "10167171488"


def test_normalize_ja_normalizado_fica_igual():
    assert normalize_cpf("10167171488") == "10167171488"


def test_normalize_outro_formato_real_do_documento():
    assert normalize_cpf("139.963.024-52") == "13996302452"


def test_normalize_vazio():
    assert normalize_cpf("") == ""
    assert normalize_cpf(None) == ""


def test_normalize_mesmo_cpf_formatos_diferentes_ficam_iguais():
    assert normalize_cpf("101.671.714-88") == normalize_cpf("10167171488")


def test_is_cpf_valido_rejeita_tamanho_errado():
    assert is_cpf_valido("123") is False


def test_is_cpf_valido_rejeita_digitos_repetidos():
    assert is_cpf_valido("11111111111") is False


def test_is_cpf_valido_aceita_cpf_com_digitos_verificadores_corretos():
    # CPF de teste com DV calculado corretamente (não corresponde a pessoa real).
    assert is_cpf_valido("11144477735") is True
