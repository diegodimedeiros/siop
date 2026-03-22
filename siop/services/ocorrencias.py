from core.api import ApiStatus
from core.services import (
    ServiceError,
    create_attachments_for_instance,
    ensure_required_fields,
    parse_local_datetime,
    to_bool,
)
from siop.models import Anexo, Ocorrencia


def create_ocorrencia(*, data, files, user):
    ensure_required_fields(
        data,
        ["data", "natureza", "tipo", "area", "local", "pessoa", "descricao"],
    )
    data_evento = parse_local_datetime(
        data.get("data"),
        field_name="data",
        required=True,
    )

    ocorrencia = Ocorrencia.objects.create(
        tipo_pessoa=data.get("pessoa"),
        data_ocorrencia=data_evento,
        natureza=data.get("natureza"),
        tipo=data.get("tipo"),
        area=data.get("area"),
        local=data.get("local"),
        descricao=data.get("descricao"),
        cftv=to_bool(data.get("cftv")),
        bombeiro_civil=to_bool(data.get("bombeiro_civil")),
        status=to_bool(data.get("status")),
        criado_por=user,
        modificado_por=user,
    )
    create_attachments_for_instance(
        instance=ocorrencia,
        model_class=Ocorrencia,
        anexo_model=Anexo,
        files=files,
    )
    return ocorrencia


def edit_ocorrencia(*, ocorrencia, data, files, user, strict_required=False):
    if ocorrencia.status:
        raise ServiceError(
            code="business_rule_violation",
            message="Ocorrência finalizada não pode ser editada.",
            status=ApiStatus.CONFLICT,
        )

    if strict_required:
        ensure_required_fields(
            data,
            ["descricao", "cftv", "bombeiro_civil", "status"],
        )

    ocorrencia.descricao = data.get("descricao", ocorrencia.descricao)
    ocorrencia.cftv = to_bool(data.get("cftv"))
    ocorrencia.bombeiro_civil = to_bool(data.get("bombeiro_civil"))
    ocorrencia.status = to_bool(data.get("status"))
    ocorrencia.modificado_por = user
    ocorrencia.save()

    create_attachments_for_instance(
        instance=ocorrencia,
        model_class=Ocorrencia,
        anexo_model=Anexo,
        files=files,
    )
    return ocorrencia
