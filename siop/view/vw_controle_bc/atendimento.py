import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.api import ApiStatus, api_error, api_success
from core.services import ServiceError
from core.utils.catalogos import (
    carregar_catalogo_json,
    catalogo_areas_data,
    catalogo_encaminhamentos_data,
    catalogo_locais_por_area_data,
    catalogo_primeiros_socorros_data,
    catalogo_responsaveis_atendimento_data,
    catalogo_sexos_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
    catalogo_transportes_data,
    catalogo_ufs_data,
)
from siop.services import create_atendimento

logger = logging.getLogger(__name__)


def _format_form_error(exc):
    details = exc.details or {}
    if not details:
        return exc.message

    messages = []
    for field_messages in details.values():
        if isinstance(field_messages, (list, tuple)):
            messages.extend(str(message) for message in field_messages if str(message).strip())
        elif str(field_messages).strip():
            messages.append(str(field_messages))

    return messages[0] if messages else exc.message


def _ufs_for_atendimento():
    data = carregar_catalogo_json("catalogo_uf.json")

    if isinstance(data, dict):
        return [
            {"sigla": str(sigla).strip().upper(), "nome": str(nome).strip() or str(sigla).strip().upper()}
            for sigla, nome in sorted(data.items(), key=lambda item: str(item[0]).upper())
            if str(sigla).strip()
        ]

    return catalogo_ufs_data()


def _atendimento_context():
    areas = catalogo_areas_data()
    locais_por_area = {area: catalogo_locais_por_area_data(area) for area in areas}
    return {
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "tipos_ocorrencia": catalogo_tipos_ocorrencia_data(),
        "sexos": catalogo_sexos_data(),
        "transportes": catalogo_transportes_data(),
        "primeiros_socorros": catalogo_primeiros_socorros_data(),
        "responsaveis_atendimento": catalogo_responsaveis_atendimento_data(),
        "encaminhamentos": catalogo_encaminhamentos_data(),
        "ufs": _ufs_for_atendimento(),
        "areas": areas,
        "locais_por_area": locais_por_area,
    }


@login_required
def atendimento(request):
    if request.method == "POST":
        try:
            atendimento_obj = create_atendimento(
                data=request.POST,
                files=request.FILES,
                user=request.user,
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return api_success(
                    data={"id": atendimento_obj.id},
                    message="Atendimento cadastrado com sucesso.",
                    status=ApiStatus.CREATED,
                )
            messages.success(request, "Atendimento cadastrado com sucesso.")
            return redirect("atendimento")
        except ServiceError as exc:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return api_error(
                    code=exc.code,
                    message=exc.message,
                    status=exc.status,
                    details=exc.details,
                )

            ctx = _atendimento_context()
            ctx["form_error"] = _format_form_error(exc)
            ctx["form_error_details"] = exc.details or {}
            return render(request, "controle_bc/atendimento/atendimento.html", ctx, status=400)
        except Exception:
            logger.exception("Erro inesperado ao criar atendimento")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return api_error(
                    code="internal_error",
                    message="Erro interno ao processar a solicitação.",
                    status=500,
                )

            ctx = _atendimento_context()
            ctx["form_error"] = "Erro interno ao processar a solicitação."
            return render(request, "controle_bc/atendimento/atendimento.html", ctx, status=500)

    return render(request, "controle_bc/atendimento/atendimento.html", _atendimento_context())
