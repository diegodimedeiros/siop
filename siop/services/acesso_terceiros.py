from core.services import (
    ServiceError,
    create_attachments_for_instance,
    parse_local_datetime,
)
from siop.models import AcessoTerceiros, Anexo, Pessoa


def _normalize_payload(*, data, original=None):
    original = original or {}
    entrada = parse_local_datetime(
        data.get("entrada") or data.get("data"),
        field_name="entrada",
        required=True,
    )
    saida = parse_local_datetime(
        data.get("saida"),
        field_name="saida",
        required=False,
    )
    nome = (data.get("nome", original.get("nome")) or "").strip()
    documento = (data.get("documento", original.get("documento")) or "").strip()
    p1 = (data.get("p1") or data.get("pessoa") or original.get("p1") or "").strip()

    details = {}
    if not nome:
        details["nome"] = "Nome completo é obrigatório."
    if not documento:
        details["documento"] = "Documento é obrigatório."
    if not p1:
        details["p1"] = "P1 é obrigatório."

    if entrada and saida and saida < entrada:
        details["saida"] = "Data/Hora de saída não pode ser anterior à entrada."

    if details:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details=details,
        )

    return {
        "entrada": entrada,
        "saida": saida,
        "nome": nome,
        "documento": documento,
        "p1": p1,
        "empresa": (data.get("empresa") or "").strip(),
        "placa_veiculo": (data.get("placa_veiculo") or "").strip(),
        "descricao_acesso": (data.get("descricao") or "").strip(),
    }


def _get_or_create_pessoa(*, nome, documento):
    pessoa = Pessoa.objects.filter(documento=documento).order_by("id").first()
    if pessoa is None:
        return Pessoa.objects.create(nome=nome, documento=documento)

    updates = []
    if pessoa.nome != nome:
        pessoa.nome = nome
        updates.append("nome")

    if updates:
        pessoa.save(update_fields=updates)

    return pessoa


def create_acesso_terceiros(*, data, files, user):
    payload = _normalize_payload(data=data)
    pessoa = _get_or_create_pessoa(
        nome=payload["nome"],
        documento=payload["documento"],
    )

    acesso = AcessoTerceiros.objects.create(
        entrada=payload["entrada"],
        saida=payload["saida"],
        pessoa=pessoa,
        empresa=payload["empresa"],
        placa_veiculo=payload["placa_veiculo"],
        p1=payload["p1"],
        descricao_acesso=payload["descricao_acesso"],
        criado_por=user,
        modificado_por=user,
    )

    create_attachments_for_instance(
        instance=acesso,
        model_class=AcessoTerceiros,
        anexo_model=Anexo,
        files=files,
    )
    return acesso


def edit_acesso_terceiros(*, acesso, data, files, user):
    payload = _normalize_payload(
        data=data,
        original={
            "nome": acesso.nome,
            "documento": acesso.documento,
            "p1": acesso.p1,
        },
    )
    pessoa = _get_or_create_pessoa(
        nome=payload["nome"],
        documento=payload["documento"],
    )

    acesso.entrada = payload["entrada"]
    acesso.saida = payload["saida"]
    acesso.pessoa = pessoa
    acesso.empresa = payload["empresa"]
    acesso.placa_veiculo = payload["placa_veiculo"]
    acesso.p1 = payload["p1"]
    acesso.descricao_acesso = payload["descricao_acesso"]
    acesso.modificado_por = user
    acesso.save()

    create_attachments_for_instance(
        instance=acesso,
        model_class=AcessoTerceiros,
        anexo_model=Anexo,
        files=files,
    )
    return acesso
