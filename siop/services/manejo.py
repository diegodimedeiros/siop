from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from core.services import ServiceError, parse_local_datetime, to_bool
from siop.models import Foto, Geolocalizacao, Manejo


def _normalize_text(value):
    return (value or "").strip()


def _normalize_optional_text(value):
    text = _normalize_text(value)
    return text or None


def _parse_lat_lon(value, field_name):
    raw = _normalize_text(value)
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={field_name: "Coordenada inválida."},
        )


def _create_geolocalizacao(*, instance, tipo, latitude, longitude, user):
    if latitude is None and longitude is None:
        return

    details = {}
    if latitude is None:
        details["latitude"] = "Latitude obrigatória."
    if longitude is None:
        details["longitude"] = "Longitude obrigatória."
    if details:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details=details,
        )

    Geolocalizacao.objects.create(
        content_type=ContentType.objects.get_for_model(Manejo),
        object_id=instance.id,
        tipo=tipo,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _create_fotos(*, instance, tipo, files, user):
    if not files:
        return

    content_type = ContentType.objects.get_for_model(Manejo)
    for file_obj in files:
        if not file_obj:
            continue
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=instance.id,
            tipo=tipo,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_{tipo}_{instance.id}",
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


@transaction.atomic
def create_manejo(*, data, files, user):
    data_hora = parse_local_datetime(
        data.get("data_hora"),
        field_name="data_hora",
        required=True,
    )

    try:
        manejo = Manejo.objects.create(
            data_hora=data_hora,
            classe=_normalize_text(data.get("classe")),
            nome_cientifico=_normalize_optional_text(data.get("nome_cientifico")),
            nome_popular=_normalize_optional_text(data.get("nome_popular")),
            estagio_desenvolvimento=_normalize_optional_text(data.get("estagio_desenvolvimento")),
            area_captura=_normalize_text(data.get("area_captura")),
            local_captura=_normalize_text(data.get("local_captura")),
            descricao_local=_normalize_text(data.get("descricao_local")),
            importancia_medica=to_bool(data.get("importancia_medica")),
            realizado_manejo=to_bool(data.get("realizado_manejo")),
            responsavel_manejo=_normalize_optional_text(data.get("responsavel_manejo")),
            area_soltura=_normalize_optional_text(data.get("area_soltura")),
            local_soltura=_normalize_optional_text(data.get("local_soltura")),
            descricao_local_soltura=_normalize_text(data.get("descricao_local_soltura")),
            acionado_orgao_publico=to_bool(data.get("acionado_orgao_publico")),
            orgao_publico=_normalize_optional_text(data.get("orgao_publico")),
            numero_boletim_ocorrencia=_normalize_optional_text(data.get("numero_boletim_ocorrencia")),
            motivo_acionamento=_normalize_text(data.get("motivo_acionamento")),
            observacoes=_normalize_text(data.get("observacoes")),
            criado_por=user,
            modificado_por=user,
        )

        _create_fotos(
            instance=manejo,
            tipo=Foto.TIPO_CAPTURA,
            files=files.getlist("foto_captura"),
            user=user,
        )
        _create_fotos(
            instance=manejo,
            tipo=Foto.TIPO_SOLTURA,
            files=files.getlist("foto_soltura"),
            user=user,
        )

        _create_geolocalizacao(
            instance=manejo,
            tipo="captura",
            latitude=_parse_lat_lon(data.get("latitude_captura"), "latitude_captura"),
            longitude=_parse_lat_lon(data.get("longitude_captura"), "longitude_captura"),
            user=user,
        )
        _create_geolocalizacao(
            instance=manejo,
            tipo="soltura",
            latitude=_parse_lat_lon(data.get("latitude_soltura"), "latitude_soltura"),
            longitude=_parse_lat_lon(data.get("longitude_soltura"), "longitude_soltura"),
            user=user,
        )
    except ValidationError as exc:
        _raise_service_validation(exc)

    return manejo
