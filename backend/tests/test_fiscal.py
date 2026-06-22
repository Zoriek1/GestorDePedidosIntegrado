from app.utils.fiscal import is_valid_cpf_cnpj, normalize_cpf_cnpj, normalize_uf


def test_normalize_and_validate_cpf_cnpj():
    assert normalize_cpf_cnpj("529.982.247-25") == "52998224725"
    assert normalize_cpf_cnpj("04.252.011/0001-10") == "04252011000110"
    assert normalize_cpf_cnpj("") is None
    assert is_valid_cpf_cnpj("529.982.247-25") is True
    assert is_valid_cpf_cnpj("04.252.011/0001-10") is True
    assert is_valid_cpf_cnpj("111.111.111-11") is False
    assert is_valid_cpf_cnpj("123") is False


def test_normalize_uf():
    assert normalize_uf(" go ") == "GO"
    assert normalize_uf("SP") == "SP"
    assert normalize_uf("") is None
    assert normalize_uf("XX") is None
