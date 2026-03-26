from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from core.api import ApiStatus, api_error, api_success
from core.services import ServiceError

from ...models import AcessoTerceiros
from ...services import create_acesso_terceiros, edit_acesso_terceiros
from .common import extract_request_payload, service_error_response, unexpected_error_response
from .exportacao import acesso_terceiros_export, acesso_terceiros_export_view_pdf
from .query import build_acesso_filtered_qs, render_acesso_page
from .serializers import serialize_acesso_detail, serialize_acesso_list_item


@login_required
def acesso_terceiro(request):
    return render_acesso_page(request)


@require_GET
@login_required
def acesso_terceiros_list(request):
    queryset, _, _, _, _ = build_acesso_filtered_qs(request)

    from core.api import parse_limit_offset

    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )

    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]

    data = [serialize_acesso_list_item(item) for item in queryset]
    return api_success(
        data={"acessos_terceiros": data},
        message="Acessos de terceiros carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@require_GET
@login_required
def acesso_terceiros_list_partial(request):
    return render_acesso_page(request, template_name="acesso_terceiros/list.html")


@require_GET
@login_required
def acesso_terceiros_view(request, pk):
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    return api_success(
        data=serialize_acesso_detail(acesso),
        message="Acesso de terceiros carregado com sucesso.",
    )


@login_required
def acesso_terceiros_new(request):
    if request.method == "POST":
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error

            acesso = create_acesso_terceiros(data=data, files=files, user=request.user)
            return api_success(
                data={"id": acesso.id},
                message="Acesso de terceiros cadastrado com sucesso.",
                status=ApiStatus.CREATED,
            )
        except ServiceError as exc:
            return service_error_response(exc)
        except Exception:
            return unexpected_error_response(
                "Erro inesperado ao criar acesso de terceiros",
                user_id=getattr(request.user, "id", None),
            )

    return acesso_terceiro(request)


@login_required
def acesso_terceiros_edit(request, pk):
    acesso = get_object_or_404(AcessoTerceiros, pk=pk)

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

        edit_acesso_terceiros(acesso=acesso, data=data, files=files, user=request.user)
        return api_success(
            data={"id": acesso.id},
            message="Acesso de terceiros alterado com sucesso.",
        )
    except ServiceError as exc:
        return service_error_response(exc)
    except Exception:
        return unexpected_error_response(
            "Erro inesperado ao editar acesso de terceiros",
            acesso_id=pk,
            user_id=getattr(request.user, "id", None),
        )
