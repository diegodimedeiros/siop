from datetime import datetime
import io
import logging
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.api import ApiStatus, api_error, api_success, parse_json_body, parse_limit_offset
from core.services import ServiceError
from ..models import AcessoTerceiros, Anexo
from ..services import create_acesso_terceiros, edit_acesso_terceiros
from siop.utils import (
    _anexos_total,
    _export_generic_csv,
    _export_generic_excel,
    _export_generic_pdf,
    _fmt_dt,
    _user_display,
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)

logger = logging.getLogger(__name__)


def _format_datetime(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else ""


def _display_user(user):
    if not user:
        return "Não registrado"
    return user.get_full_name() if user.get_full_name() else user.username


def _parse_dt_local(value):
    if not value:
        return None
    tz = timezone.get_current_timezone()
    try:
        return timezone.make_aware(datetime.strptime(value, "%Y-%m-%dT%H:%M"), tz)
    except ValueError:
        return None


def _parse_date_term(term):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(term, fmt).date()
        except ValueError:
            continue
    return None


def export_acessos_terceiros_pdf(request, queryset):
    headers = [
        "Entrada", "Empresa", "Nome", "Documento", "P1", "Saida", "Descricao",
        "Anexos", "Placa", "Criado em", "Criado por", "Modificado em", "Modificado por", "ID",
    ]
    row_getters = [
        lambda o: _fmt_dt(o.entrada),
        lambda o: o.empresa or "",
        lambda o: o.nome or "",
        lambda o: o.documento or "",
        lambda o: o.p1 or "",
        lambda o: _fmt_dt(o.saida),
        lambda o: o.descricao or "",
        _anexos_total,
        lambda o: o.placa_veiculo or "",
        lambda o: _fmt_dt(o.criado_em),
        lambda o: _user_display(getattr(o, "criado_por", None)),
        lambda o: _fmt_dt(o.modificado_em),
        lambda o: _user_display(getattr(o, "modificado_por", None)),
        lambda o: o.id,
    ]
    base_col_widths = [
        1.0 * 72, 1.15 * 72, 1.2 * 72, 1.0 * 72, 0.55 * 72, 1.0 * 72, 1.75 * 72,
        0.5 * 72, 0.75 * 72, 1.0 * 72, 1.0 * 72, 1.0 * 72, 1.0 * 72, 0.35 * 72,
    ]
    return _export_generic_pdf(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        report_title="Relatorio de Acessos de Terceiros",
        report_subject="Acessos de Terceiros",
        headers=headers,
        row_getters=row_getters,
        base_col_widths=base_col_widths,
    )


def export_acessos_terceiros_excel(request, queryset):
    headers = [
        "Entrada", "Empresa", "Nome", "Documento", "P1", "Saida", "Descricao",
        "Anexos", "Placa", "Criado em", "Criado por", "Modificado em", "Modificado por", "ID",
    ]
    row_getters = [
        lambda o: _fmt_dt(o.entrada),
        lambda o: o.empresa or "",
        lambda o: o.nome or "",
        lambda o: o.documento or "",
        lambda o: o.p1 or "",
        lambda o: _fmt_dt(o.saida),
        lambda o: o.descricao or "",
        _anexos_total,
        lambda o: o.placa_veiculo or "",
        lambda o: _fmt_dt(o.criado_em),
        lambda o: _user_display(getattr(o, "criado_por", None)),
        lambda o: _fmt_dt(o.modificado_em),
        lambda o: _user_display(getattr(o, "modificado_por", None)),
        lambda o: o.id,
    ]
    return _export_generic_excel(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        sheet_title="Acessos Terceiros",
        document_title="Relatorio de Acessos de Terceiros",
        document_subject="Acessos de Terceiros",
        headers=headers,
        row_getters=row_getters,
    )


def export_acessos_terceiros_csv(request, queryset):
    headers = [
        "Entrada", "Empresa", "Nome", "Documento", "P1", "Saida", "Descricao",
        "Anexos", "Placa", "Criado em", "Criado por", "Modificado em", "Modificado por", "ID",
    ]
    row_getters = [
        lambda o: _fmt_dt(o.entrada),
        lambda o: o.empresa or "",
        lambda o: o.nome or "",
        lambda o: o.documento or "",
        lambda o: o.p1 or "",
        lambda o: _fmt_dt(o.saida),
        lambda o: o.descricao or "",
        _anexos_total,
        lambda o: o.placa_veiculo or "",
        lambda o: _fmt_dt(o.criado_em),
        lambda o: _user_display(getattr(o, "criado_por", None)),
        lambda o: _fmt_dt(o.modificado_em),
        lambda o: _user_display(getattr(o, "modificado_por", None)),
        lambda o: o.id,
    ]
    return _export_generic_csv(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        headers=headers,
        row_getters=row_getters,
    )


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": _format_datetime(anexo.criado_em),
        "download_url": f"/anexos/{anexo.id}/download/",
    }


def serialize_acesso_list_item(acesso):
    return {
        "id": acesso.id,
        "entrada": _format_datetime(acesso.entrada),
        "saida": _format_datetime(acesso.saida),
        "nome": acesso.pessoa.nome if acesso.pessoa_id else "",
        "documento": acesso.pessoa.documento if acesso.pessoa_id else "",
        "empresa": acesso.empresa,
        "placa_veiculo": acesso.placa_veiculo,
        "p1": acesso.p1,
        "total_anexos": acesso.total_anexos,
    }


def serialize_acesso_detail(acesso):
    anexos = [serialize_anexo(a) for a in acesso.anexos.all()]
    return {
        "id": acesso.id,
        "entrada": _format_datetime(acesso.entrada),
        "saida": _format_datetime(acesso.saida),
        "nome": acesso.pessoa.nome if acesso.pessoa_id else "",
        "documento": acesso.pessoa.documento if acesso.pessoa_id else "",
        "empresa": acesso.empresa,
        "placa_veiculo": acesso.placa_veiculo,
        "p1": acesso.p1,
        "descricao": acesso.descricao_acesso,
        "anexos": anexos,
        "anexos_total": len(anexos),
        "criado_em": _format_datetime(acesso.criado_em),
        "criado_por": _display_user(acesso.criado_por),
        "modificado_em": _format_datetime(acesso.modificado_em),
        "modificado_por": _display_user(acesso.modificado_por),
    }


def apply_acesso_search(queryset, query, scope="default"):
    termo = (query or "").strip()
    if not termo:
        return queryset

    if scope == "descricao":
        return queryset.filter(descricao_acesso__icontains=termo)

    filtros = (
        Q(pessoa__nome__icontains=termo)
        | Q(pessoa__documento__icontains=termo)
        | Q(empresa__icontains=termo)
        | Q(placa_veiculo__icontains=termo)
        | Q(p1__icontains=termo)
    )

    if termo.isdigit():
        filtros |= Q(id=int(termo))

    data_term = _parse_date_term(termo)
    if data_term:
        filtros |= Q(entrada__date=data_term) | Q(saida__date=data_term)

    return queryset.filter(filtros)


def apply_acesso_ordering(queryset, sort_field=None, sort_dir="desc"):
    allowed = {
        "id": "id",
        "entrada": "entrada",
        "saida": "saida",
        "nome": "pessoa__nome",
        "documento": "pessoa__documento",
        "empresa": "empresa",
        "placa_veiculo": "placa_veiculo",
        "p1": "p1",
        "anexo": "total_anexos",
    }

    field = allowed.get((sort_field or "").strip().lower())
    direction = "asc" if (sort_dir or "").lower() == "asc" else "desc"
    if not field:
        return queryset.order_by("-entrada", "-id"), "", "desc"

    order = field if direction == "asc" else f"-{field}"
    return queryset.order_by(order, "-id"), sort_field, direction


def apply_acesso_filters(queryset, params):
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    empresa = (params.get("empresa") or "").strip()
    placa_veiculo = (params.get("placa_veiculo") or "").strip()
    p1 = (params.get("p1") or params.get("pessoa") or "").strip()

    entrada_inicio = (params.get("entrada_inicio") or params.get("data_inicio") or "").strip()
    entrada_fim = (params.get("entrada_fim") or params.get("data_fim") or "").strip()
    saida_inicio = (params.get("saida_inicio") or "").strip()
    saida_fim = (params.get("saida_fim") or "").strip()

    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(pessoa__documento__icontains=documento)
    if empresa:
        queryset = queryset.filter(empresa__icontains=empresa)
    if placa_veiculo:
        queryset = queryset.filter(placa_veiculo__icontains=placa_veiculo)
    if p1:
        queryset = queryset.filter(p1__icontains=p1)

    dt = _parse_dt_local(entrada_inicio)
    if dt:
        queryset = queryset.filter(entrada__gte=dt)
    dt = _parse_dt_local(entrada_fim)
    if dt:
        queryset = queryset.filter(entrada__lte=dt)

    dt = _parse_dt_local(saida_inicio)
    if dt:
        queryset = queryset.filter(saida__gte=dt)
    dt = _parse_dt_local(saida_fim)
    if dt:
        queryset = queryset.filter(saida__lte=dt)

    return queryset


def has_acesso_export_filters(params):
    filter_keys = (
        "nome",
        "documento",
        "empresa",
        "placa_veiculo",
        "p1",
        "pessoa",
        "entrada_inicio",
        "entrada_fim",
        "data_inicio",
        "data_fim",
        "saida_inicio",
        "saida_fim",
        "q",
    )
    return any((params.get(key) or "").strip() for key in filter_keys)


def _extract_request_payload(request):
    json_data, json_error = parse_json_body(request)
    if json_error:
        return None, None, json_error

    if json_data is not None:
        return json_data, [], None

    return request.POST, request.FILES.getlist("anexos"), None


def _service_error_response(exc):
    return api_error(
        code=exc.code,
        message=exc.message,
        status=exc.status,
        details=exc.details,
    )


def _unexpected_error_response(log_message, **extra):
    logger.exception(log_message, extra=extra or None)
    return api_error(
        code="internal_error",
        message="Erro interno ao processar a solicitação.",
        status=500,
    )


@login_required
def acesso_terceiro(request):
    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"

    qs = AcessoTerceiros.objects.select_related("pessoa").annotate(total_anexos=Count("anexos"))
    qs = apply_acesso_filters(qs, request.GET)
    qs = apply_acesso_search(qs, query, scope)
    qs, sort_field, sort_dir = apply_acesso_ordering(qs, sort_field, sort_dir)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "acesso_terceiros/acesso_terceiros.html",
        {"page_obj": page_obj, "q": query, "scope": scope, "sort": sort_field, "dir": sort_dir},
    )


@require_GET
@login_required
def acesso_terceiros_list(request):
    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"

    qs = AcessoTerceiros.objects.select_related("pessoa").annotate(total_anexos=Count("anexos"))
    qs = apply_acesso_filters(qs, request.GET)
    qs = apply_acesso_search(qs, query, scope)
    qs, _, _ = apply_acesso_ordering(qs, sort_field, sort_dir)

    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )

    total = qs.count()
    if limit is not None:
        qs = qs[offset: offset + limit]

    data = [serialize_acesso_list_item(item) for item in qs]
    return api_success(
        data={"acessos_terceiros": data},
        message="Acessos de terceiros carregados com sucesso.",
        meta={
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(data),
            }
        },
    )


@require_GET
@login_required
def acesso_terceiros_list_partial(request):
    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"

    qs = AcessoTerceiros.objects.select_related("pessoa").annotate(total_anexos=Count("anexos"))
    qs = apply_acesso_filters(qs, request.GET)
    qs = apply_acesso_search(qs, query, scope)
    qs, sort_field, sort_dir = apply_acesso_ordering(qs, sort_field, sort_dir)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "acesso_terceiros/list.html",
        {"page_obj": page_obj, "q": query, "scope": scope, "sort": sort_field, "dir": sort_dir},
    )


@require_GET
@login_required
def acesso_terceiros_view(request, pk):
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    return api_success(
        data=serialize_acesso_detail(acesso),
        message="Acesso de terceiros carregado com sucesso.",
    )


@login_required
def acesso_terceiros_export_view_pdf(request, pk):
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)

    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    NumberedCanvas = build_numbered_canvas_class(width)
    c = NumberedCanvas(buffer, pagesize=A4)
    c.setTitle(f"Relatório de Acesso de Terceiros #{acesso.id}")
    c.setAuthor(_display_user(request.user))
    c.setSubject("Relatório de Acesso de Terceiros")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=c,
            page_width=width,
            page_height=height,
            generated_by=_display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
        )

    draw_page_chrome()

    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 140, f"Relatório de Acesso de Terceiros: #{acesso.id}")

    c.setFont("Helvetica", 10)
    info_block_w = 430
    info_x = (width - info_block_w) / 2
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    draw_pdf_label_value(c, info_x, info_y, "Data/Hora de entrada", _format_datetime(acesso.entrada))
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Data/Hora de saída", _format_datetime(acesso.saida))
    info_y -= (line_h + block_gap)

    draw_pdf_label_value(c, info_x, info_y, "Nome completo", acesso.nome or "-")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Documento", acesso.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "P1", acesso.p1 or "-")
    info_y -= (line_h + block_gap)

    draw_pdf_label_value(c, info_x, info_y, "Empresa", acesso.empresa or "-")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Placa do veículo", acesso.placa_veiculo or "-")
    info_y -= (line_h + block_gap)

    draw_pdf_label_value(c, info_x, info_y, "Criado por", _display_user(acesso.criado_por))
    draw_pdf_label_value(c, right_x, info_y, "Modificado por", _display_user(acesso.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Criado em", _format_datetime(acesso.criado_em))
    draw_pdf_label_value(c, right_x, info_y, "Modificado em", _format_datetime(acesso.modificado_em))

    min_y = 72
    page_content_top = height - 120

    anexos_y = info_y - 18
    if anexos_y < min_y:
        c.showPage()
        draw_page_chrome()
        anexos_y = page_content_top

    anexos_x = info_x
    c.setFont("Helvetica-Bold", 10)
    c.drawString(anexos_x, anexos_y, "Anexos:")
    c.setFont("Helvetica", 9)
    anexos = list(acesso.anexos.all())
    y = anexos_y - 14
    if anexos:
        for idx, anexo in enumerate(anexos, start=1):
            if y < min_y:
                c.showPage()
                draw_page_chrome()
                c.setFillColorRGB(*dark_text)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(anexos_x, page_content_top, "Anexos (continuação):")
                c.setFont("Helvetica", 9)
                y = page_content_top - 14
            c.drawString(anexos_x + 4, y, f"{idx}. {anexo.nome_arquivo}")
            y -= 12
    else:
        c.drawString(anexos_x + 4, y, "Nenhum anexo.")
        y -= 12

    desc_title_y = y - 12
    if desc_title_y < min_y:
        c.showPage()
        draw_page_chrome()
        desc_title_y = page_content_top

    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(info_x, desc_title_y, "Descrição do Acesso de Terceiros")

    desc_lines = wrap_pdf_text_lines(acesso.descricao or "-", width - (info_x * 2))
    c.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            c.showPage()
            draw_page_chrome()
            c.setFillColorRGB(*dark_text)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(info_x, page_content_top, "Descrição do Acesso de Terceiros (continuação)")
            c.setFont("Helvetica", 10)
            y = page_content_top - 18
        c.drawString(info_x, y, line)
        y -= 13

    c.showPage()
    c.save()
    buffer.seek(0)

    filename = f"acesso_terceiros_{acesso.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def acesso_terceiros_new(request):
    if request.method == "POST":
        try:
            data, files, payload_error = _extract_request_payload(request)
            if payload_error:
                return payload_error

            acesso = create_acesso_terceiros(
                data=data,
                files=files,
                user=request.user,
            )

            return api_success(
                data={"id": acesso.id},
                message="Acesso de terceiros cadastrado com sucesso.",
                status=ApiStatus.CREATED,
            )
        except ServiceError as exc:
            return _service_error_response(exc)
        except Exception:
            return _unexpected_error_response(
                "Erro inesperado ao criar acesso de terceiros",
                user_id=getattr(request.user, "id", None),
            )

    return acesso_terceiro(request)


@login_required
def acesso_terceiros_edit(request, pk):
    acesso = get_object_or_404(AcessoTerceiros, pk=pk)

    if request.method != "POST":
        return api_error(
            code="method_not_allowed",
            message="Método não permitido.",
            status=405,
        )

    try:
        data, files, payload_error = _extract_request_payload(request)
        if payload_error:
            return payload_error

        edit_acesso_terceiros(
            acesso=acesso,
            data=data,
            files=files,
            user=request.user,
        )

        return api_success(
            data={"id": acesso.id},
            message="Acesso de terceiros alterado com sucesso.",
        )
    except ServiceError as exc:
        return _service_error_response(exc)
    except Exception:
        return _unexpected_error_response(
            "Erro inesperado ao editar acesso de terceiros",
            acesso_id=pk,
            user_id=getattr(request.user, "id", None),
        )


@require_GET
@login_required
def acesso_terceiros_export(request, formato):
    formato = (formato or "").strip().lower()
    if not has_acesso_export_filters(request.GET):
        params = urlencode({"export_error": "Aplique ao menos um filtro para exportar os registros."})
        return redirect(f"{reverse('acesso_terceiro')}?{params}")

    qs = AcessoTerceiros.objects.select_related("pessoa").annotate(total_anexos=Count("anexos"))
    qs = apply_acesso_filters(qs, request.GET)

    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    if scope not in ("default", "descricao"):
        scope = "default"
    qs = apply_acesso_search(qs, query, scope)

    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    qs, _, _ = apply_acesso_ordering(qs, sort_field, sort_dir)

    if formato == "csv":
        return export_acessos_terceiros_csv(request, qs)
    if formato in ("xlsx", "excel"):
        return export_acessos_terceiros_excel(request, qs)
    if formato == "pdf":
        return export_acessos_terceiros_pdf(request, qs)

    return api_error(
        code="invalid_export_format",
        message="Formato de exportação inválido. Use csv, xlsx ou pdf.",
        status=400,
    )
