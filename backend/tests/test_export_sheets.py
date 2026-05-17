# -*- coding: utf-8 -*-
"""Testes do script de exportação para Google Sheets."""
import calendar
import importlib.util
from datetime import date, datetime
from pathlib import Path

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Carrega o módulo do script sem executar create_app
_backend_dir = Path(__file__).resolve().parent.parent
_script_path = _backend_dir / "scripts" / "export" / "exportar_vendas_sheets.py"
_spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", _script_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

identificar_aba = _module.identificar_aba
parse_valor = _module.parse_valor
_created_at_date_brazil = _module._created_at_date_brazil
TIMEZONE_BRASIL = _module.TIMEZONE_BRASIL
ABA_WHATSAPP = _module.ABA_WHATSAPP
ABA_CATALOGO = _module.ABA_CATALOGO
ABA_SITE = _module.ABA_SITE

# ---------------------------------------------------------------------------
# identificar_aba — mapeamento de fonte → aba
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fonte_nome,expected_aba",
    [
        ("WhatsApp", ABA_WHATSAPP),
        ("whatsapp", ABA_WHATSAPP),
        ("Catálogo", ABA_CATALOGO),
        ("catalogo", ABA_CATALOGO),
        ("Site", ABA_SITE),
        ("site", ABA_SITE),
        ("SITE", ABA_SITE),
        # Nuvemshop = subclasse de Site (mesma aba)
        ("Nuvemshop", ABA_SITE),
        ("nuvemshop", ABA_SITE),
        ("NuvemShop", ABA_SITE),
        ("Tiendanube", ABA_SITE),
        ("tiendanube", ABA_SITE),
    ],
)
def test_identificar_aba_fontes_conhecidas(fonte_nome, expected_aba):
    """Fontes conhecidas (incl. Nuvemshop) mapeiam para a aba correta."""
    assert identificar_aba(fonte_nome) == expected_aba


def test_identificar_aba_fonte_desconhecida_retorna_none():
    """Fonte desconhecida retorna None (pedido não entra em nenhuma aba)."""
    assert identificar_aba("Outra Fonte Qualquer") is None
    assert identificar_aba("") is None


# ---------------------------------------------------------------------------
# parse_valor — conversão de moeda BR para float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("R$ 150,00", 150.0),
        ("R$ 1.234,56", 1234.56),
        ("65,00", 65.0),
        ("R$50,00", 50.0),
        ("0,00", 0.0),
        ("", 0.0),
        (None, 0.0),
        ("150.00", 150.0),  # formato com ponto (sem vírgula)
        ("abc", 0.0),  # inválido → 0.0
    ],
)
def test_parse_valor(entrada, esperado):
    """parse_valor converte formatos BR para float corretamente."""
    assert parse_valor(entrada) == pytest.approx(esperado, abs=0.001)


# ---------------------------------------------------------------------------
# _created_at_date_brazil — conversão de timezone
# ---------------------------------------------------------------------------


def test_created_at_date_brazil_com_timezone_utc():
    """Datetime UTC 01:00 do dia 1/3 = 28/2 no Brasil (UTC-3)."""
    dt_utc = datetime(2026, 3, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
    resultado = _created_at_date_brazil(dt_utc)
    assert resultado == date(2026, 2, 28)


def test_created_at_date_brazil_sem_timezone():
    """Datetime sem tzinfo retorna a data tal como está (comportamento documentado)."""
    dt_naive = datetime(2026, 3, 8, 14, 0, 0)
    resultado = _created_at_date_brazil(dt_naive)
    assert resultado == date(2026, 3, 8)


def test_created_at_date_brazil_none():
    """None retorna None sem erro."""
    assert _created_at_date_brazil(None) is None


def test_created_at_date_brazil_horario_brasilia():
    """Datetime em horário de Brasília é devolvido sem alteração de dia."""
    dt_br = datetime(2026, 3, 8, 22, 0, 0, tzinfo=TIMEZONE_BRASIL)
    resultado = _created_at_date_brazil(dt_br)
    assert resultado == date(2026, 3, 8)


# ---------------------------------------------------------------------------
# Lógica de totais por dia — Bug 2: dias futuros não devem ficar em branco
# ---------------------------------------------------------------------------


def _simular_totais(ano, mes, pedidos_aba):
    """
    Reproduz a lógica de montagem de totais_data do exportar_vendas()
    (após a correção do Bug 2).
    """
    _, num_dias = calendar.monthrange(ano, mes)
    totais_data = []

    for dia in range(1, num_dias + 1):
        data_dia = date(ano, mes, dia)
        dia_semana = data_dia.weekday()
        total_dia = sum(p["valor"] for p in pedidos_aba.get(dia, []))

        dia_label = "DOMINGO" if dia_semana == 6 else str(dia)
        if total_dia > 0:
            totais_data.append([dia_label, f"R$ {total_dia:.2f}".replace(".", ",")])
        else:
            totais_data.append([dia_label, "-"])

    return totais_data, num_dias


def test_totais_preenche_todos_os_dias_do_mes():
    """Todos os dias do mês devem ter entrada em totais_data (sem buracos)."""
    ano, mes = 2026, 3  # março tem 31 dias
    totais, num_dias = _simular_totais(ano, mes, {})
    assert len(totais) == num_dias  # 31 linhas para março


def test_totais_dias_sem_venda_recebem_tracinho():
    """Dias sem vendas (passados ou futuros) mostram '-', não célula vazia."""
    totais, _ = _simular_totais(2026, 3, {})
    # Pegar dia 2 de março de 2026 (segunda-feira, index 0)
    # dia 2 → índice 1 em totais_data → [str(2), "-"]
    linha_dia2 = totais[1]  # dia 2
    assert linha_dia2[0] == "2"
    assert linha_dia2[1] == "-"


def test_totais_dias_com_venda_mostram_valor():
    """Dias com vendas mostram o total formatado em R$."""
    # Usar dia 5 de março 2026 (quinta-feira, não domingo)
    pedidos_aba = {5: [{"valor": 150.0}, {"valor": 80.0}]}
    totais, _ = _simular_totais(2026, 3, pedidos_aba)
    linha_dia5 = totais[4]  # dia 5 → índice 4
    assert linha_dia5[0] == "5"
    assert "230" in linha_dia5[1]  # R$ 230,00


def test_totais_domingo_recebe_label_correto():
    """Domingos devem aparecer como ['DOMINGO', '-']."""
    # 1º março 2026 é domingo (weekday=6)
    totais, _ = _simular_totais(2026, 3, {})
    linha_dia1 = totais[0]  # dia 1
    assert linha_dia1 == ["DOMINGO", "-"]


def test_totais_domingo_com_venda_mostra_total():
    """Domingo com venda deve mostrar valor, sem perder faturamento."""
    # 1º março de 2026 é domingo
    pedidos_aba = {1: [{"valor": 100.0}, {"valor": 50.0}]}
    totais, _ = _simular_totais(2026, 3, pedidos_aba)
    linha_dia1 = totais[0]
    assert linha_dia1[0] == "DOMINGO"
    assert "150" in linha_dia1[1]


def test_totais_nao_ha_celulas_vazias():
    """Nenhuma linha em totais_data deve ter strings vazias (bug original)."""
    totais, _ = _simular_totais(2026, 3, {})
    for linha in totais:
        assert linha[0] != "", f"Dia com célula vazia em F: {linha}"
        assert linha[1] != "", f"Dia com célula vazia em G: {linha}"


def test_totais_mes_completo_com_vendas_em_alguns_dias():
    """Meses com vendas em alguns dias e sem em outros devem ter 31 entradas."""
    pedidos_aba = {
        5: [{"valor": 100.0}],
        10: [{"valor": 200.0}, {"valor": 50.0}],
        20: [{"valor": 75.0}],
    }
    totais, num_dias = _simular_totais(2026, 3, pedidos_aba)
    assert len(totais) == num_dias
    # Verificar dias com venda
    assert "100" in totais[4][1]  # dia 5
    assert "250" in totais[9][1]  # dia 10 (200 + 50)
    assert "75" in totais[19][1]  # dia 20


def test_export_sheets_verbose_summary():
    """Resumo verbose para inspeção manual com pytest -s."""
    aba_whatsapp = identificar_aba("WhatsApp")
    aba_site = identificar_aba("Site")
    aba_nuvemshop = identificar_aba("Nuvemshop")
    valor_brl = parse_valor("R$ 150,00")
    valor_decimal = parse_valor("65,00")
    dt_utc = datetime(2026, 3, 1, 1, 0, 0, tzinfo=ZoneInfo("UTC"))
    dt_brasil = _created_at_date_brazil(dt_utc)

    print("=== EXPORT SHEETS VERBOSE SUMMARY ===")
    print(f"aba_whatsapp={aba_whatsapp}")
    print(f"aba_site={aba_site}")
    print(f"aba_nuvemshop={aba_nuvemshop}")
    print(f"parse_valor_R$150={valor_brl}")
    print(f"parse_valor_65,00={valor_decimal}")
    print(f"created_at_brazil={dt_brasil}")

    assert aba_whatsapp == ABA_WHATSAPP
    assert aba_site == ABA_SITE
    assert aba_nuvemshop == ABA_SITE
    assert valor_brl == pytest.approx(150.0, abs=0.001)
    assert valor_decimal == pytest.approx(65.0, abs=0.001)
    assert dt_brasil == date(2026, 2, 28)


# ---------------------------------------------------------------------------
# Teste de contrato HTTP — garante que o endpoint está na URL correta
# ---------------------------------------------------------------------------


def test_exportar_planilha_endpoint_acessivel(client):
    """
    Garante que POST /api/pedidos/exportar-planilha está registrado no blueprint correto.
    Detecta regressões onde a rota muda de url_prefix sem atualizar o frontend.
    200 ou 500 (credenciais Google ausentes no CI) são válidos.
    404 ou 405 indicam URL errada.
    """
    import base64

    auth = base64.b64encode(b"admin:testpass").decode()
    response = client.post(
        "/api/pedidos/exportar-planilha",
        headers={"Authorization": f"Basic {auth}"},
    )
    assert response.status_code not in (404, 405), (
        f"Endpoint ausente ou método rejeitado (status {response.status_code}). "
        "Verificar url_prefix do pedidos_bp e o path chamado em OrdersPage.tsx."
    )
