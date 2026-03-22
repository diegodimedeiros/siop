import io
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q

from datetime import datetime

import logging

from core.api import (
    ApiStatus,
    api_error,
    api_success,
    is_json_request,
    parse_json_body,
    parse_limit_offset,
)
from core.services import ServiceError
from core.utils.catalogos import (
    catalogo_areas_data,
    catalogo_encaminhamentos_data,
    catalogo_locais_por_area_data,
    catalogo_naturezas_data,
    catalogo_p1_data,
    catalogo_primeiros_socorros_data,
    catalogo_sexos_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
    catalogo_tipos_por_natureza_data,
    catalogo_transportes_data,
)
from core.utils.exports import (
    export_generic_csv as _export_generic_csv,
    export_generic_excel as _export_generic_excel,
    export_generic_pdf as _export_generic_pdf,
)
from core.utils.exports.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)
from core.utils.formatters import (
    bool_ptbr as _bool_ptbr,
    fmt_dt as _fmt_dt,
    status_ptbr as _status_ptbr,
    user_display as _user_display,
)
from core.utils.helpers import anexos_total as _anexos_total
from ..models import Ocorrencia, Anexo
from ..services import create_ocorrencia, edit_ocorrencia
logger = logging.getLogger(__name__)

OCORRENCIAS_EXPORT_HEADERS = [
    "ID", "Data/Hora", "Natureza", "Tipo", "Area", "Local", "Pessoa", "CFTV",
    "Bombeiro Civil", "Status", "Anexos", "Descricao", "Criado em", "Criado por", "Modificado em", "Modificado por",
]

OCORRENCIAS_EXPORT_PDF_HEADERS = [
    "ID", "Data/Hora", "Natureza", "Tipo", "Area", "Local", "Pessoa", "CFTV",
    "Bombeiro Civil", "Status", "Anexos", "Criado em", "Criado por", "Modificado em", "Modificado por",
]

OCORRENCIAS_EXPORT_BASE_COL_WIDTHS = [
    0.26 * 72, 0.95 * 72, 0.62 * 72, 0.85 * 72, 0.8 * 72, 1.2 * 72, 0.8 * 72, 0.5 * 72,
    0.75 * 72, 0.54 * 72, 0.45 * 72, 0.95 * 72, 0.95 * 72, 0.95 * 72, 0.95 * 72,
]


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


def _get_ocorrencias_export_row_getters(include_description=False):
    getters = [
        lambda o: o.id,
        lambda o: _fmt_dt(o.data_ocorrencia),
        lambda o: o.natureza or "",
        lambda o: o.tipo or "",
        lambda o: o.area or "",
        lambda o: o.local or "",
        lambda o: o.tipo_pessoa or "",
        lambda o: _bool_ptbr(o.cftv),
        lambda o: _bool_ptbr(o.bombeiro_civil),
        lambda o: _status_ptbr(o.status),
        _anexos_total,
    ]
    if include_description:
        getters.append(lambda o: o.descricao or "")
    getters.extend(
        [
            lambda o: _fmt_dt(o.criado_em),
            lambda o: _user_display(getattr(o, "criado_por", None)),
            lambda o: _fmt_dt(o.modificado_em),
            lambda o: _user_display(getattr(o, "modificado_por", None)),
        ]
    )
    return getters


def export_ocorrencias_pdf(request, queryset):
    return _export_generic_pdf(
        request,
        queryset,
        filename_prefix="ocorrencias",
        report_title="Relatorio de Ocorrencias",
        report_subject="Ocorrencias",
        headers=OCORRENCIAS_EXPORT_PDF_HEADERS,
        row_getters=_get_ocorrencias_export_row_getters(),
        base_col_widths=OCORRENCIAS_EXPORT_BASE_COL_WIDTHS,
        nowrap_indices={5},
    )


def export_ocorrencias_excel(request, queryset):
    return _export_generic_excel(
        request,
        queryset,
        filename_prefix="ocorrencias",
        sheet_title="Ocorrencias",
        document_title="Relatorio de Ocorrencias",
        document_subject="Ocorrencias",
        headers=OCORRENCIAS_EXPORT_HEADERS,
        row_getters=_get_ocorrencias_export_row_getters(include_description=True),
    )


def export_ocorrencias_csv(request, queryset):
    return _export_generic_csv(
        request,
        queryset,
        filename_prefix="ocorrencias",
        headers=OCORRENCIAS_EXPORT_HEADERS,
        row_getters=_get_ocorrencias_export_row_getters(include_description=True),
    )


def _format_datetime(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else ""


def _display_user(user):
    if not user:
        return "Não registrado"
    return user.get_full_name() if user.get_full_name() else user.username


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": _format_datetime(anexo.criado_em),
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
        "data": _format_datetime(ocorrencia.data_ocorrencia),
        "status": ocorrencia.status,
    }


def _serialize_ocorrencia_audit_fields(ocorrencia):
    return {
        "criado_em": _format_datetime(ocorrencia.criado_em),
        "criado_por": _display_user(ocorrencia.criado_por),
        "modificado_em": _format_datetime(ocorrencia.modificado_em),
        "modificado_por": _display_user(ocorrencia.modificado_por),
    }


def serialize_ocorrencia_list_item(ocorrencia):
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "tem_anexo": ocorrencia.total_anexos > 0,
        "total_anexos": ocorrencia.total_anexos,
    }


def serialize_ocorrencia_detail(ocorrencia):
    anexos = [serialize_anexo(a) for a in ocorrencia.anexos.all()]
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "descricao": ocorrencia.descricao,
        "cftv": ocorrencia.cftv,
        "bombeiro_civil": ocorrencia.bombeiro_civil,
        "anexos": anexos,
        "anexos_total": len(anexos),
        **_serialize_ocorrencia_audit_fields(ocorrencia),
    }


def _build_ocorrencias_base_qs():
    return Ocorrencia.objects.annotate(total_anexos=Count("anexos"))


def _parse_date_term(term):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(term, fmt).date()
        except ValueError:
            continue
    return None


def apply_ocorrencia_search(queryset, query, scope="default"):
    termo = (query or "").strip()
    if not termo:
        return queryset

    if scope == "descricao":
        return queryset.filter(descricao__icontains=termo)

    filtros = (
        Q(natureza__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(area__icontains=termo)
        | Q(local__icontains=termo)
        | Q(tipo_pessoa__icontains=termo)
    )
    if termo.isdigit():
        filtros |= Q(id=int(termo))

    termo_lower = termo.lower()
    if termo_lower in ("finalizada", "finalizado", "finalizada.", "final"):
        filtros |= Q(status=True)
    if termo_lower in ("aberto", "aberta", "em aberto"):
        filtros |= Q(status=False)

    if termo_lower in ("sim", "com anexo", "com anexos", "anexo", "anexos"):
        filtros |= Q(total_anexos__gt=0)
    if termo_lower in ("não", "nao", "sem anexo", "sem anexos"):
        filtros |= Q(total_anexos=0)

    data_term = _parse_date_term(termo)
    if data_term:
        filtros |= Q(data_ocorrencia__date=data_term)

    return queryset.filter(filtros)


def apply_ocorrencia_ordering(queryset, sort_field=None, sort_dir="desc"):
    allowed = {
        "id": "id",
        "data": "data_ocorrencia",
        "natureza": "natureza",
        "tipo": "tipo",
        "area": "area",
        "local": "local",
        "anexo": "total_anexos",
        "status": "status",
    }

    field = allowed.get((sort_field or "").strip().lower())
    direction = "asc" if (sort_dir or "").lower() == "asc" else "desc"
    if not field:
        # Mantém o comportamento padrão atual.
        return queryset.order_by("-criado_em", "-id"), "", "desc"

    order = field if direction == "asc" else f"-{field}"
    return queryset.order_by(order, "-id"), sort_field, direction


def apply_ocorrencia_export_filters(queryset, params):
    natureza = (params.get("natureza") or "").strip()
    tipo = (params.get("tipo") or "").strip()
    area = (params.get("area") or "").strip()
    local = (params.get("local") or "").strip()
    pessoa = (params.get("pessoa") or "").strip()
    status = (params.get("status") or "").strip().lower()
    bombeiro_civil = (params.get("bombeiro_civil") or "").strip().lower()
    cftv = (params.get("cftv") or "").strip().lower()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()

    if natureza:
        queryset = queryset.filter(natureza=natureza)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if area:
        queryset = queryset.filter(area=area)
    if local:
        queryset = queryset.filter(local=local)
    if pessoa:
        queryset = queryset.filter(tipo_pessoa=pessoa)

    if status == "aberto":
        queryset = queryset.filter(status=False)
    elif status == "finalizada":
        queryset = queryset.filter(status=True)

    if bombeiro_civil in ("sim", "true", "1"):
        queryset = queryset.filter(bombeiro_civil=True)
    elif bombeiro_civil in ("nao", "não", "false", "0"):
        queryset = queryset.filter(bombeiro_civil=False)

    if cftv in ("sim", "true", "1"):
        queryset = queryset.filter(cftv=True)
    elif cftv in ("nao", "não", "false", "0"):
        queryset = queryset.filter(cftv=False)

    tz = timezone.get_current_timezone()
    if data_inicio:
        try:
            dt_inicio = timezone.make_aware(datetime.strptime(data_inicio, "%Y-%m-%dT%H:%M"), tz)
            queryset = queryset.filter(data_ocorrencia__gte=dt_inicio)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = timezone.make_aware(datetime.strptime(data_fim, "%Y-%m-%dT%H:%M"), tz)
            queryset = queryset.filter(data_ocorrencia__lte=dt_fim)
        except ValueError:
            pass

    return queryset


def has_ocorrencia_export_filters(params):
    filter_keys = (
        "natureza",
        "tipo",
        "area",
        "local",
        "pessoa",
        "status",
        "bombeiro_civil",
        "cftv",
        "data_inicio",
        "data_fim",
        "q",
    )
    return any((params.get(key) or "").strip() for key in filter_keys)


def _normalize_ocorrencia_search_params(request):
    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"
    return query, scope, sort_field, sort_dir


def _build_ocorrencia_filtered_qs(request):
    query, scope, sort_field, sort_dir = _normalize_ocorrencia_search_params(request)
    queryset = _build_ocorrencias_base_qs()
    queryset = apply_ocorrencia_export_filters(queryset, request.GET)
    queryset = apply_ocorrencia_search(queryset, query, scope)
    queryset, sort_field, sort_dir = apply_ocorrencia_ordering(queryset, sort_field, sort_dir)
    return queryset, query, scope, sort_field, sort_dir


def _build_ocorrencia_page_context(request):
    queryset, query, scope, sort_field, sort_dir = _build_ocorrencia_filtered_qs(request)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "q": query,
        "scope": scope,
        "sort": sort_field,
        "dir": sort_dir,
    }


def _render_ocorrencia_page(request, template_name="ocorrencias/ocorrencia.html"):
    return render(request, template_name, _build_ocorrencia_page_context(request))


# ==============================
# VIEWS DE CATÁLOGO
# ==============================

@login_required
def catalogo_naturezas(request):
    return api_success(
        data={"naturezas": catalogo_naturezas_data()},
        message="Naturezas carregadas com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_por_natureza(request):
    natureza = request.GET.get("natureza")
    return api_success(
        data={"natureza": natureza, "tipos": catalogo_tipos_por_natureza_data(natureza)},
        message="Tipos carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_areas(request):
    return api_success(
        data={"areas": catalogo_areas_data()},
        message="Áreas carregadas com sucesso.",
    )


@require_GET
@login_required
def catalogo_locais_por_area(request):
    area = request.GET.get("area")
    return api_success(
        data={"area": area, "locais": catalogo_locais_por_area_data(area)},
        message="Locais carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_p1(request):
    return api_success(
        data={"p1": catalogo_p1_data()},
        message="P1 carregado com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_pessoa(request):
    return api_success(
        data={"tipos_pessoa": catalogo_tipos_pessoa_data()},
        message="Tipos de pessoa carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_sexos(request):
    return api_success(
        data={"sexos": catalogo_sexos_data()},
        message="Sexos carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_ocorrencia(request):
    return api_success(
        data={"tipos_ocorrencia": catalogo_tipos_ocorrencia_data()},
        message="Tipos de ocorrência carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_transportes(request):
    return api_success(
        data={"transportes": catalogo_transportes_data()},
        message="Transportes carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_encaminhamentos(request):
    return api_success(
        data={"encaminhamentos": catalogo_encaminhamentos_data()},
        message="Encaminhamentos carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_primeiros_socorros(request):
    return api_success(
        data={"primeiros_socorros": catalogo_primeiros_socorros_data()},
        message="Primeiros socorros carregados com sucesso.",
    )


# ==============================
# VIEWS DE PÁGINAS
# ==============================

@login_required
def home_view(request):
    qs = Ocorrencia.objects.all()
    total_ocorrencias = qs.count()
    total_abertas = qs.filter(status=False).count()
    total_finalizadas = qs.filter(status=True).count()
    total_bombeiro_civil = qs.filter(bombeiro_civil=True).count()
    taxa_finalizacao = round((total_finalizadas / total_ocorrencias) * 100, 1) if total_ocorrencias else 0
    taxa_bombeiro_civil = round((total_bombeiro_civil / total_ocorrencias) * 100, 1) if total_ocorrencias else 0

    top_areas = list(
        qs.values("area")
        .annotate(total=Count("id"))
        .order_by("-total", "area")[:5]
    )
    top_naturezas = list(
        qs.values("natureza")
        .annotate(total=Count("id"))
        .order_by("-total", "natureza")[:5]
    )
    recentes = qs.order_by("-data")[:6]

    return render(
        request,
        "home.html",
        {
            "total_ocorrencias": total_ocorrencias,
            "total_abertas": total_abertas,
            "total_finalizadas": total_finalizadas,
            "total_bombeiro_civil": total_bombeiro_civil,
            "taxa_finalizacao": taxa_finalizacao,
            "taxa_bombeiro_civil": taxa_bombeiro_civil,
            "top_areas": top_areas,
            "top_naturezas": top_naturezas,
            "ocorrencias_recentes": recentes,
        },
    )


# ==============================
# VIEWS OCORRÊNCIAS
# ==============================

@login_required
def ocorrencia(request):
    return _render_ocorrencia_page(request)


@require_GET
@login_required
def ocorrencia_list(request):
    """
    Retorna JSON (corrigido: return não pode ficar dentro do for)
    """
    ocorrencias, _, _, _, _ = _build_ocorrencia_filtered_qs(request)

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
        ocorrencias = ocorrencias[offset: offset + limit]

    data = [serialize_ocorrencia_list_item(o) for o in ocorrencias]
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
    """
    Retorna o HTML do include "ocorrencias/list.html"
    (pra atualizar a aba Listar via fetch sem dar F5)
    """
    return _render_ocorrencia_page(request, template_name="ocorrencias/list.html")


@require_GET
@login_required
def ocorrencia_export(request, formato):
    formato = (formato or "").strip().lower()
    if not has_ocorrencia_export_filters(request.GET):
        params = urlencode({"export_error": "Aplique ao menos um filtro para exportar os registros."})
        return redirect(f"{reverse('ocorrencia')}?{params}")

    qs, _, _, _, _ = _build_ocorrencia_filtered_qs(request)

    if formato == "pdf":
        return export_ocorrencias_pdf(request, qs)
    if formato in ("xlsx", "excel"):
        return export_ocorrencias_excel(request, qs)
    if formato == "csv":
        return export_ocorrencias_csv(request, qs)

    return api_error(
        code="invalid_export_format",
        message="Formato de exportação inválido. Use csv, xlsx ou pdf.",
        status=400,
    )


@login_required
def ocorrencia_export_view_pdf(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)

    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    NumberedCanvas = build_numbered_canvas_class(width)
    c = NumberedCanvas(buffer, pagesize=A4)
    c.setTitle(f"Relatório da Ocorrência #{ocorrencia.id}")
    c.setAuthor(_display_user(request.user))
    c.setSubject("Relatório de Ocorrência")

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

    # Infos gerais (área superior do corpo)
    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 140, f"Relatório da Ocorrência: #{ocorrencia.id}")

    c.setFont("Helvetica", 10)
    info_block_w = 430
    info_x = (width - info_block_w) / 2
    info_y = height - 195
    line_h = 14
    block_gap = 14
    draw_pdf_label_value(c, info_x, info_y, "Data/Hora", _format_datetime(ocorrencia.data_ocorrencia))
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Status", "Finalizada" if ocorrencia.status else "Em aberto")
    info_y -= (line_h + block_gap)

    draw_pdf_label_value(c, info_x, info_y, "Natureza da Ocorrência", ocorrencia.natureza or "-")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Tipo de Ocorrência", ocorrencia.tipo or "-")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Área e Local da Ocorrência", f"{(ocorrencia.area or '-')} - {(ocorrencia.local or '-')}")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Tipo Pessoa Envolvido", ocorrencia.tipo_pessoa or "-")
    info_y -= (line_h + block_gap)

    draw_pdf_label_value(c, info_x, info_y, "Imagens CFTV", "Sim" if ocorrencia.cftv else "Não")
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Bombeiro Civil", "Sim" if ocorrencia.bombeiro_civil else "Não")
    info_y -= (line_h + block_gap)

    right_x = info_x + (info_block_w / 2)
    draw_pdf_label_value(c, info_x, info_y, "Criado por", _display_user(ocorrencia.criado_por))
    draw_pdf_label_value(c, right_x, info_y, "Modificado por", _display_user(ocorrencia.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(c, info_x, info_y, "Criado em", _format_datetime(ocorrencia.criado_em))
    draw_pdf_label_value(c, right_x, info_y, "Modificado em", _format_datetime(ocorrencia.modificado_em))

    min_y = 72
    page_content_top = height - 120

    # Anexos logo abaixo do bloco de informações
    anexos_y = info_y - 18
    if anexos_y < min_y:
        c.showPage()
        draw_page_chrome()
        anexos_y = page_content_top

    anexos_x = info_x
    c.setFont("Helvetica-Bold", 10)
    c.drawString(anexos_x, anexos_y, "Anexos:")
    c.setFont("Helvetica", 9)
    anexos = list(ocorrencia.anexos.all())
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

    # Descrição inicia somente após anexos
    desc_title_y = y - 12
    if desc_title_y < min_y:
        c.showPage()
        draw_page_chrome()
        desc_title_y = page_content_top

    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(info_x, desc_title_y, "Descrição da Ocorrência")

    desc_lines = wrap_pdf_text_lines(ocorrencia.descricao or "-", width - (info_x * 2))
    c.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            c.showPage()
            draw_page_chrome()
            c.setFillColorRGB(*dark_text)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(info_x, page_content_top, "Descrição da Ocorrência (continuação)")
            c.setFont("Helvetica", 10)
            y = page_content_top - 18
        c.drawString(info_x, y, line)
        y -= 13

    c.showPage()
    c.save()
    buffer.seek(0)

    filename = f"ocorrencia_{ocorrencia.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def ocorrencia_view(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    return api_success(
        data=serialize_ocorrencia_detail(ocorrencia),
        message="Ocorrência carregada com sucesso.",
    )


@login_required
def ocorrencia_new(request):
    if request.method == "POST":
        try:
            data, files, payload_error = _extract_request_payload(request)
            if payload_error:
                return payload_error

            ocorrencia = create_ocorrencia(
                data=data,
                files=files,
                user=request.user,
            )

            return api_success(
                data={"id": ocorrencia.id},
                message="Ocorrência cadastrada com sucesso.",
                status=ApiStatus.CREATED,
            )
        except ServiceError as exc:
            return _service_error_response(exc)
        except Exception:
            return _unexpected_error_response(
                "Erro inesperado ao criar ocorrência",
                user_id=getattr(request.user, "id", None),
            )

    # GET normal (se alguém abrir /ocorrencias/new/ no navegador)
    return _render_ocorrencia_page(request)

@login_required
def ocorrencia_edit(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)

    if request.method not in {"POST", "PATCH"}:
        return api_error(
            code="method_not_allowed",
            message="Método não permitido.",
            status=405,
        )

    try:
        data, files, payload_error = _extract_request_payload(request)
        if payload_error:
            return payload_error

        edit_ocorrencia(
            ocorrencia=ocorrencia,
            data=data,
            files=files,
            user=request.user,
            strict_required=is_json_request(request),
        )

        return api_success(
            data={"id": ocorrencia.id},
            message="Ocorrência alterada com sucesso.",
        )

    except ServiceError as exc:
        return _service_error_response(exc)
    except Exception:
        return _unexpected_error_response(
            "Erro inesperado ao editar ocorrência",
            ocorrencia_id=pk,
        )

@login_required
def anexo_download(request, pk):
    anexo = get_object_or_404(Anexo, pk=pk)

    resp = HttpResponse(
        anexo.arquivo,
        content_type=anexo.mime_type or "application/octet-stream"
    )
    resp["Content-Disposition"] = f'attachment; filename="{anexo.nome_arquivo}"'
    return resp
