from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from core.api import ApiStatus, api_error, api_success, is_json_request, parse_limit_offset
from core.services import ServiceError

from ...models import Anexo, Ocorrencia
from ...services import create_ocorrencia, edit_ocorrencia
from .common import extract_request_payload, unexpected_error_response, service_error_response
from .exportacao import ocorrencia_export, ocorrencia_export_view_pdf
from .query import build_ocorrencia_filtered_qs, render_ocorrencia_page
from .serializers import serialize_ocorrencia_detail, serialize_ocorrencia_list_item


@login_required
def ocorrencia(request):
    return render_ocorrencia_page(request)


@require_GET
@login_required
def ocorrencia_list(request):
    ocorrencias, _, _, _, _ = build_ocorrencia_filtered_qs(request)

    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )

    total = ocorrencias.count()
    if limit is not None:
        ocorrencias = ocorrencias[offset : offset + limit]

    data = [serialize_ocorrencia_list_item(ocorrencia_item) for ocorrencia_item in ocorrencias]
    meta = {
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(data),
        }
    }

    return api_success(
        data={"ocorrencias": data},
        message="Ocorrências carregadas com sucesso.",
        meta=meta,
    )


@require_GET
@login_required
def ocorrencia_list_partial(request):
    return render_ocorrencia_page(request, template_name="ocorrencias/list.html")


@login_required
def ocorrencia_view(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia, pk=pk)
    return api_success(
        data=serialize_ocorrencia_detail(ocorrencia_obj),
        message="Ocorrência carregada com sucesso.",
    )


@login_required
def ocorrencia_new(request):
    if request.method == "POST":
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error

            ocorrencia_obj = create_ocorrencia(
                data=data,
                files=files,
                user=request.user,
            )
            return api_success(
                data={"id": ocorrencia_obj.id},
                message="Ocorrência cadastrada com sucesso.",
                status=ApiStatus.CREATED,
            )
        except ServiceError as exc:
            return service_error_response(exc)
        except Exception:
            return unexpected_error_response(
                "Erro inesperado ao criar ocorrência",
                user_id=getattr(request.user, "id", None),
            )

    return render_ocorrencia_page(request)


@login_required
def ocorrencia_edit(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia, pk=pk)

    if request.method not in {"POST", "PATCH"}:
        return api_error(
            code="method_not_allowed",
            message="Método não permitido.",
            status=405,
        )

    try:
        data, files, payload_error = extract_request_payload(request)
        if payload_error:
            return payload_error

        edit_ocorrencia(
            ocorrencia=ocorrencia_obj,
            data=data,
            files=files,
            user=request.user,
            strict_required=is_json_request(request),
        )

        return api_success(
            data={"id": ocorrencia_obj.id},
            message="Ocorrência alterada com sucesso.",
        )
    except ServiceError as exc:
        return service_error_response(exc)
    except Exception:
        return unexpected_error_response(
            "Erro inesperado ao editar ocorrência",
            ocorrencia_id=pk,
        )


@login_required
def anexo_download(request, pk):
    anexo = get_object_or_404(Anexo, pk=pk)
    response = HttpResponse(
        anexo.arquivo,
        content_type=anexo.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{anexo.nome_arquivo}"'
    return response
