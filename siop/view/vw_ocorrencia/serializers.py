from .common import display_user, format_datetime


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": format_datetime(anexo.criado_em),
        "download_url": f"/anexos/{anexo.id}/download/",
    }


def _serialize_ocorrencia_base_fields(ocorrencia):
    return {
        "id": ocorrencia.id,
        "natureza": ocorrencia.natureza,
        "tipo": ocorrencia.tipo,
        "area": ocorrencia.area,
        "local": ocorrencia.local,
        "pessoa": ocorrencia.tipo_pessoa,
        "data": format_datetime(ocorrencia.data_ocorrencia),
        "status": ocorrencia.status,
    }


def _serialize_ocorrencia_audit_fields(ocorrencia):
    return {
        "criado_em": format_datetime(ocorrencia.criado_em),
        "criado_por": display_user(ocorrencia.criado_por),
        "modificado_em": format_datetime(ocorrencia.modificado_em),
        "modificado_por": display_user(ocorrencia.modificado_por),
    }


def serialize_ocorrencia_list_item(ocorrencia):
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "tem_anexo": ocorrencia.total_anexos > 0,
        "total_anexos": ocorrencia.total_anexos,
    }


def serialize_ocorrencia_detail(ocorrencia):
    anexos = [serialize_anexo(anexo) for anexo in ocorrencia.anexos.all()]
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "descricao": ocorrencia.descricao,
        "cftv": ocorrencia.cftv,
        "bombeiro_civil": ocorrencia.bombeiro_civil,
        "anexos": anexos,
        "anexos_total": len(anexos),
        **_serialize_ocorrencia_audit_fields(ocorrencia),
    }
