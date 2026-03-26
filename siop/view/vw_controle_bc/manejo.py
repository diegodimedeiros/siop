import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.api import ApiStatus, api_error, api_success
from core.services import ServiceError
from core.utils import (
    catalogo_areas_data,
    catalogo_especies_por_classe_data,
    catalogo_fauna_data,
    catalogo_responsaveis_atendimento_data,
)
from siop.services import create_manejo

logger = logging.getLogger(__name__)


@login_required
def manejo(request):
    if request.method == "POST":
        try:
            manejo_obj = create_manejo(
                data=request.POST,
                files=request.FILES,
                user=request.user,
            )
            return api_success(
                data={"id": manejo_obj.id},
                message="Manejo cadastrado com sucesso.",
                status=ApiStatus.CREATED,
            )
        except ServiceError as exc:
            return api_error(
                code=exc.code,
                message=exc.message,
                status=exc.status,
                details=exc.details,
            )
        except Exception:
            logger.exception("Erro inesperado ao criar manejo")
            return api_error(
                code="internal_error",
                message="Erro interno ao processar a solicitação.",
                status=500,
            )

    return render(
        request,
        "controle_bc/manejo/manejo.html",
        {
            "classes_fauna": catalogo_fauna_data(),
            "areas_captura": catalogo_areas_data(),
            "responsaveis_manejo": catalogo_responsaveis_atendimento_data(),
        },
    )


@require_GET
@login_required
def catalogo_especies_por_classe(request):
    classe = (request.GET.get("classe") or "").strip()
    return api_success(
        data={"especies": catalogo_especies_por_classe_data(classe)},
        message="Espécies carregadas com sucesso.",
    )
