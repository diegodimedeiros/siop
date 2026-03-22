import base64
import binascii
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from core.services import ServiceError, parse_local_datetime, to_bool
from siop.models import (
    Assinatura,
    Contato,
    ControleAtendimento,
    Foto,
    Geolocalizacao,
    Pessoa,
    Testemunha,
)


TESTEMUNHA_KEY_RE = re.compile(
    r"^testemunhas\[(\d+)\]\[(nome|documento|telefone|data_nascimento|sexo|nacionalidade|endereco|cidade|pais)\]$"
)


def _normalize_text(value):
    return (value or "").strip()


def _normalize_optional_text(value):
    text = _normalize_text(value)
    return text or None


def _parse_date(value, *, field_name, required=False):
    if value in (None, ""):
        if required:
            raise ServiceError(
                code="validation_error",
                message="Campos inválidos.",
                details={field_name: "Campo obrigatório."},
            )
        return None

    raw = str(value).strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={field_name: "Use o formato YYYY-MM-DD."},
        )


def _parse_decimal_7(value, *, field_name):
    raw = _normalize_text(value)
    if not raw:
        return None

    try:
        return Decimal(raw).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={field_name: "Coordenada inválida."},
        )


def _parse_signature_data_url(data_url):
    value = _normalize_text(data_url)
    if not value:
        return None, None
    if not value.startswith("data:") or "," not in value:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_atendido": "Formato de assinatura inválido."},
        )

    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_atendido": "Assinatura deve estar em base64."},
        )

    mime_type = header[5:].split(";")[0].strip().lower() or "image/png"
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_atendido": "Assinatura inválida."},
        )

    if not payload:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_atendido": "Assinatura vazia."},
        )

    return mime_type, payload


def _create_geolocalizacao(*, atendimento, latitude, longitude, user):
    if latitude is None and longitude is None:
        return

    details = {}
    if latitude is None:
        details["geo_latitude"] = "Latitude obrigatória."
    if longitude is None:
        details["geo_longitude"] = "Longitude obrigatória."
    if details:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details=details,
        )

    Geolocalizacao.objects.create(
        content_type=ContentType.objects.get_for_model(ControleAtendimento),
        object_id=atendimento.id,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _create_signature(*, atendimento, data_url, user):
    mime_type, payload = _parse_signature_data_url(data_url)
    if not payload:
        return

    ext = "png"
    if mime_type == "image/jpeg":
        ext = "jpg"
    elif mime_type == "image/webp":
        ext = "webp"

    Assinatura.objects.create(
        content_type=ContentType.objects.get_for_model(ControleAtendimento),
        object_id=atendimento.id,
        nome_arquivo=f"assinatura_atendido_{atendimento.id}.{ext}",
        mime_type=mime_type,
        arquivo=payload,
        criado_por=user,
        modificado_por=user,
    )


def _create_fotos(*, atendimento, files, user):
    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    for file_obj in files:
        if not file_obj:
            continue

        content = file_obj.read()
        if not content:
            continue

        Foto.objects.create(
            content_type=content_type,
            object_id=atendimento.id,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_{atendimento.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _raise_service_validation(exc):
    if hasattr(exc, "message_dict"):
        details = exc.message_dict
    elif hasattr(exc, "messages"):
        details = {"__all__": exc.messages}
    else:
        details = {"__all__": [str(exc)]}

    raise ServiceError(
        code="validation_error",
        message="Campos inválidos.",
        details=details,
    )


def _has_any_contact_value(data):
    return any(
        _normalize_text(data.get(field))
        for field in (
            "contato_endereco",
            "contato_bairro",
            "contato_cidade",
            "contato_estado",
            "contato_pais",
            "contato_telefone",
            "contato_email",
        )
    )


def _get_or_create_pessoa(*, nome, documento, orgao_emissor, sexo, data_nascimento, nacionalidade):
    pessoa = Pessoa.objects.filter(documento=documento).order_by("id").first()
    if pessoa is None:
        return Pessoa.objects.create(
            nome=nome,
            documento=documento,
            orgao_emissor=orgao_emissor,
            sexo=sexo,
            data_nascimento=data_nascimento,
            nacionalidade=nacionalidade,
        )

    pessoa.nome = nome
    pessoa.orgao_emissor = orgao_emissor
    pessoa.sexo = sexo
    pessoa.data_nascimento = data_nascimento
    pessoa.nacionalidade = nacionalidade
    pessoa.save(
        update_fields=[
            "nome",
            "orgao_emissor",
            "sexo",
            "data_nascimento",
            "nacionalidade",
        ]
    )
    return pessoa


def _build_contato_from_request(data):
    if not _has_any_contact_value(data):
        return None

    return Contato.objects.create(
        endereco=_normalize_optional_text(data.get("contato_endereco")),
        bairro=_normalize_optional_text(data.get("contato_bairro")),
        cidade=_normalize_optional_text(data.get("contato_cidade")),
        estado=_normalize_optional_text(data.get("contato_estado")),
        pais=_normalize_optional_text(data.get("contato_pais")),
        telefone=_normalize_optional_text(data.get("contato_telefone")),
        email=_normalize_optional_text(data.get("contato_email")),
    )


def _parse_testemunhas(data):
    grouped = {}
    for key, value in data.items():
        match = TESTEMUNHA_KEY_RE.match(key)
        if not match:
            continue
        idx, field = match.groups()
        grouped.setdefault(idx, {})[field] = _normalize_text(value)

    testemunhas = []
    for idx in sorted(grouped.keys(), key=int):
        item = grouped[idx]
        has_any_value = any(item.values())
        if not has_any_value:
            continue

        nome = item.get("nome", "")
        documento = item.get("documento", "")
        if not nome or not documento:
            raise ServiceError(
                code="validation_error",
                message="Campos inválidos.",
                details={"testemunhas": f"Testemunha {int(idx) + 1}: nome e documento são obrigatórios."},
            )

        testemunhas.append(
            {
                "nome": nome,
                "documento": documento,
                "telefone": item.get("telefone") or None,
                "data_nascimento": _parse_date(
                    item.get("data_nascimento"),
                    field_name=f"testemunhas[{idx}][data_nascimento]",
                    required=False,
                ),
                "sexo": item.get("sexo") or None,
                "nacionalidade": item.get("nacionalidade") or None,
                "endereco": item.get("endereco") or None,
                "cidade": item.get("cidade") or None,
                "pais": item.get("pais") or None,
            }
        )

    return testemunhas


def _create_testemunhas(*, atendimento, data):
    testemunhas_payload = _parse_testemunhas(data)
    if not testemunhas_payload:
        return

    testemunha_ids = []
    for item in testemunhas_payload:
        contato = Contato.objects.create(
            telefone=item["telefone"],
            endereco=item["endereco"],
            cidade=item["cidade"],
            pais=item["pais"],
        )
        testemunha = Testemunha.objects.create(
            nome=item["nome"],
            documento=item["documento"],
            sexo=item["sexo"],
            data_nascimento=item["data_nascimento"],
            nacionalidade=item["nacionalidade"],
            contato=contato,
        )
        testemunha_ids.append(testemunha.id)

    atendimento.testemunhas.set(testemunha_ids)


def _build_payload(data):
    details = {}

    pessoa_nome = _normalize_text(data.get("pessoa_nome"))
    pessoa_documento = _normalize_text(data.get("pessoa_documento"))
    pessoa_sexo = _normalize_text(data.get("pessoa_sexo"))
    responsavel_atendimento = _normalize_text(data.get("responsavel_atendimento"))

    if not pessoa_nome:
        details["pessoa_nome"] = "Campo obrigatório."
    if not pessoa_documento:
        details["pessoa_documento"] = "Campo obrigatório."
    if not _normalize_text(data.get("tipo_pessoa")):
        details["tipo_pessoa"] = "Campo obrigatório."
    if not pessoa_sexo:
        details["pessoa_sexo"] = "Campo obrigatório."
    if not _normalize_text(data.get("area_atendimento")):
        details["area_atendimento"] = "Campo obrigatório."
    if not _normalize_text(data.get("local")):
        details["local"] = "Campo obrigatório."
    if not _normalize_text(data.get("tipo_ocorrencia")):
        details["tipo_ocorrencia"] = "Campo obrigatório."
    if not responsavel_atendimento:
        details["responsavel_atendimento"] = "Campo obrigatório."
    if not _normalize_text(data.get("descricao")):
        details["descricao"] = "Campo obrigatório."

    possui_acompanhante = to_bool(data.get("possui_acompanhante"))
    acompanhante_nome = _normalize_text(data.get("acompanhante_nome"))
    acompanhante_documento = _normalize_text(data.get("acompanhante_documento"))
    if possui_acompanhante:
        if not acompanhante_nome:
            details["acompanhante_nome"] = "Campo obrigatório."
        if not acompanhante_documento:
            details["acompanhante_documento"] = "Campo obrigatório."

    if details:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details=details,
        )

    return {
        "tipo_pessoa": _normalize_text(data.get("tipo_pessoa")),
        "pessoa_nome": pessoa_nome,
        "pessoa_documento": pessoa_documento,
        "pessoa_orgao_emissor": _normalize_optional_text(data.get("pessoa_orgao_emissor")),
        "pessoa_sexo": pessoa_sexo,
        "pessoa_data_nascimento": _parse_date(
            data.get("pessoa_data_nascimento"),
            field_name="pessoa_data_nascimento",
            required=False,
        ),
        "pessoa_nacionalidade": _normalize_optional_text(data.get("pessoa_nacionalidade")),
        "data_atendimento": parse_local_datetime(
            data.get("data_atendimento"),
            field_name="data_atendimento",
            required=True,
        ),
        "area_atendimento": _normalize_text(data.get("area_atendimento")),
        "local": _normalize_text(data.get("local")),
        "tipo_ocorrencia": _normalize_text(data.get("tipo_ocorrencia")),
        "responsavel_atendimento": responsavel_atendimento,
        "atendimentos": to_bool(data.get("atendimentos")),
        "primeiros_socorros": _normalize_optional_text(data.get("primeiros_socorros")),
        "descricao": _normalize_text(data.get("descricao")),
        "doenca_preexistente": to_bool(data.get("doenca_preexistente")),
        "descricao_doenca": _normalize_optional_text(data.get("descricao_doenca")),
        "alergia": to_bool(data.get("alergia")),
        "descricao_alergia": _normalize_optional_text(data.get("descricao_alergia")),
        "plano_saude": to_bool(data.get("plano_saude")),
        "nome_plano_saude": _normalize_optional_text(data.get("nome_plano_saude")),
        "numero_carteirinha": _normalize_optional_text(data.get("numero_carteirinha")),
        "seguiu_passeio": to_bool(data.get("seguiu_passeio")),
        "houve_remocao": to_bool(data.get("houve_remocao")),
        "transporte": _normalize_optional_text(data.get("transporte")),
        "encaminhamento": _normalize_optional_text(data.get("encaminhamento")),
        "hospital": _normalize_optional_text(data.get("hospital")),
        "medico_responsavel": _normalize_optional_text(data.get("medico_responsavel")),
        "crm": _normalize_optional_text(data.get("crm")),
        "possui_acompanhante": possui_acompanhante,
        "acompanhante_nome": acompanhante_nome or None,
        "acompanhante_documento": acompanhante_documento or None,
        "acompanhante_orgao_emissor": _normalize_optional_text(data.get("acompanhante_orgao_emissor")),
        "acompanhante_sexo": _normalize_optional_text(data.get("acompanhante_sexo")),
        "acompanhante_data_nascimento": _parse_date(
            data.get("acompanhante_data_nascimento"),
            field_name="acompanhante_data_nascimento",
            required=False,
        ),
        "acompanhante_nacionalidade": _normalize_optional_text(data.get("acompanhante_nacionalidade")),
        "grau_parentesco": _normalize_optional_text(data.get("grau_parentesco")),
        "geo_latitude": _parse_decimal_7(data.get("geo_latitude"), field_name="geo_latitude"),
        "geo_longitude": _parse_decimal_7(data.get("geo_longitude"), field_name="geo_longitude"),
    }


@transaction.atomic
def create_atendimento(*, data, files, user):
    payload = _build_payload(data)

    pessoa = _get_or_create_pessoa(
        nome=payload["pessoa_nome"],
        documento=payload["pessoa_documento"],
        orgao_emissor=payload["pessoa_orgao_emissor"],
        sexo=payload["pessoa_sexo"],
        data_nascimento=payload["pessoa_data_nascimento"],
        nacionalidade=payload["pessoa_nacionalidade"],
    )
    contato = _build_contato_from_request(data)

    acompanhante = None
    if payload["possui_acompanhante"]:
        acompanhante = _get_or_create_pessoa(
            nome=payload["acompanhante_nome"],
            documento=payload["acompanhante_documento"],
            orgao_emissor=payload["acompanhante_orgao_emissor"],
            sexo=payload["acompanhante_sexo"],
            data_nascimento=payload["acompanhante_data_nascimento"],
            nacionalidade=payload["acompanhante_nacionalidade"],
        )

    try:
        atendimento = ControleAtendimento.objects.create(
            tipo_pessoa=payload["tipo_pessoa"],
            pessoa=pessoa,
            contato=contato,
            area_atendimento=payload["area_atendimento"],
            local=payload["local"],
            data_atendimento=payload["data_atendimento"],
            tipo_ocorrencia=payload["tipo_ocorrencia"],
            possui_acompanhante=payload["possui_acompanhante"],
            acompanhante_pessoa=acompanhante,
            grau_parentesco=payload["grau_parentesco"],
            doenca_preexistente=payload["doenca_preexistente"],
            descricao_doenca=payload["descricao_doenca"],
            alergia=payload["alergia"],
            descricao_alergia=payload["descricao_alergia"],
            plano_saude=payload["plano_saude"],
            nome_plano_saude=payload["nome_plano_saude"],
            numero_carteirinha=payload["numero_carteirinha"],
            primeiros_socorros=payload["primeiros_socorros"],
            atendimentos=payload["atendimentos"],
            responsavel_atendimento=payload["responsavel_atendimento"],
            seguiu_passeio=payload["seguiu_passeio"],
            houve_remocao=payload["houve_remocao"],
            transporte=payload["transporte"],
            encaminhamento=payload["encaminhamento"],
            hospital=payload["hospital"],
            medico_responsavel=payload["medico_responsavel"],
            crm=payload["crm"],
            descricao=payload["descricao"],
            criado_por=user,
            modificado_por=user,
        )

        _create_testemunhas(atendimento=atendimento, data=data)
        _create_signature(atendimento=atendimento, data_url=data.get("assinatura_atendido"), user=user)
        _create_geolocalizacao(
            atendimento=atendimento,
            latitude=payload["geo_latitude"],
            longitude=payload["geo_longitude"],
            user=user,
        )
        _create_fotos(
            atendimento=atendimento,
            files=files.getlist("fotos"),
            user=user,
        )
    except ValidationError as exc:
        _raise_service_validation(exc)

    return atendimento
