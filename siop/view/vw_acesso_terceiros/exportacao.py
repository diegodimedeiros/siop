import io
from urllib.parse import urlencode

from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from core.api import api_error
from core.utils.exports import (
    export_generic_csv as export_generic_csv_impl,
    export_generic_excel as export_generic_excel_impl,
    export_generic_pdf as export_generic_pdf_impl,
)
from core.utils.exports.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)
from core.utils.formatters import fmt_dt, user_display
from core.utils.helpers import anexos_total, build_rows

from ...models import AcessoTerceiros
from .common import display_user, format_datetime
from .query import apply_acesso_filters, apply_acesso_ordering, apply_acesso_search, build_acesso_base_qs, has_acesso_export_filters


def _headers():
    return [
        "Entrada", "Empresa", "Nome", "Documento", "P1", "Saida", "Descricao",
        "Anexos", "Placa", "Criado em", "Criado por", "Modificado em", "Modificado por", "ID",
    ]


def _row_getters():
    return [
        lambda acesso: fmt_dt(acesso.entrada),
        lambda acesso: acesso.empresa or "",
        lambda acesso: acesso.nome or "",
        lambda acesso: acesso.documento or "",
        lambda acesso: acesso.p1 or "",
        lambda acesso: fmt_dt(acesso.saida),
        lambda acesso: acesso.descricao or "",
        anexos_total,
        lambda acesso: acesso.placa_veiculo or "",
        lambda acesso: fmt_dt(acesso.criado_em),
        lambda acesso: user_display(getattr(acesso, "criado_por", None)),
        lambda acesso: fmt_dt(acesso.modificado_em),
        lambda acesso: user_display(getattr(acesso, "modificado_por", None)),
        lambda acesso: acesso.id,
    ]


def export_acessos_terceiros_pdf(request, queryset):
    base_col_widths = [
        1.0 * 72, 1.15 * 72, 1.2 * 72, 1.0 * 72, 0.55 * 72, 1.0 * 72, 1.75 * 72,
        0.5 * 72, 0.75 * 72, 1.0 * 72, 1.0 * 72, 1.0 * 72, 1.0 * 72, 0.35 * 72,
    ]
    return export_generic_pdf_impl(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        report_title="Relatorio de Acessos de Terceiros",
        report_subject="Acessos de Terceiros",
        headers=_headers(),
        row_getters=_row_getters(),
        base_col_widths=base_col_widths,
        build_rows=build_rows,
    )


def export_acessos_terceiros_excel(request, queryset):
    return export_generic_excel_impl(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        sheet_title="Acessos Terceiros",
        document_title="Relatorio de Acessos de Terceiros",
        document_subject="Acessos de Terceiros",
        headers=_headers(),
        row_getters=_row_getters(),
    )


def export_acessos_terceiros_csv(request, queryset):
    return export_generic_csv_impl(
        request,
        queryset,
        filename_prefix="acessos_terceiros",
        headers=_headers(),
        row_getters=_row_getters(),
    )


def acesso_terceiros_export_view_pdf(request, pk):
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)

    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório de Acesso de Terceiros #{acesso.id}")
    canvas.setAuthor(display_user(request.user))
    canvas.setSubject("Relatório de Acesso de Terceiros")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            generated_by=display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle="Módulo Acesso Terceiros",
        )

    draw_page_chrome()

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, f"Relatório de Acesso de Terceiros: #{acesso.id}")

    info_block_w = 430
    info_x = (width - info_block_w) / 2
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    def ensure_space(current_y, needed=80, title=None):
        if current_y >= min_y + needed:
            return current_y
        canvas.showPage()
        draw_page_chrome()
        canvas.setFillColorRGB(*dark_text)
        if title:
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, title)
            return page_content_top - 18
        return page_content_top

    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora de entrada", format_datetime(acesso.entrada))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora de saída", format_datetime(acesso.saida))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", display_user(acesso.criado_por))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", display_user(acesso.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", format_datetime(acesso.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", format_datetime(acesso.modificado_em))
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados da Pessoa:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Nome completo", acesso.nome or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Documento", acesso.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "P1", acesso.p1 or "-")
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados do Acesso:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Empresa", acesso.empresa or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Placa do veículo", acesso.placa_veiculo or "-")
    info_y -= (line_h + block_gap)

    min_y = 72
    page_content_top = height - 120

    desc_title_y = info_y - 8
    if desc_title_y < min_y:
        canvas.showPage()
        draw_page_chrome()
        desc_title_y = page_content_top

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, desc_title_y, "Descrição do Acesso de Terceiros")

    desc_lines = wrap_pdf_text_lines(acesso.descricao or "-", width - (info_x * 2))
    canvas.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, "Descrição do Acesso de Terceiros (continuação)")
            canvas.setFont("Helvetica", 10)
            y = page_content_top - 18
        canvas.drawString(info_x, y, line)
        y -= 13

    anexos_y = y - 12
    if anexos_y < min_y:
        canvas.showPage()
        draw_page_chrome()
        canvas.setFillColorRGB(*dark_text)
        anexos_y = page_content_top

    anexos_x = info_x
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(anexos_x, anexos_y, "Anexos")
    canvas.setFont("Helvetica", 9)
    anexos = list(acesso.anexos.all())
    y = anexos_y - 14
    if anexos:
        for idx, anexo in enumerate(anexos, start=1):
            if y < min_y:
                canvas.showPage()
                draw_page_chrome()
                canvas.setFillColorRGB(*dark_text)
                canvas.setFont("Helvetica-Bold", 11)
                canvas.drawString(anexos_x, page_content_top, "Anexos (continuação)")
                canvas.setFont("Helvetica", 9)
                y = page_content_top - 14
            canvas.drawString(anexos_x + 4, y, f"{idx}. {anexo.nome_arquivo}")
            y -= 12
    else:
        canvas.drawString(anexos_x + 4, y, "Nenhum anexo.")
        y -= 12

    canvas.showPage()
    canvas.save()
    buffer.seek(0)

    filename = f"acesso_terceiros_{acesso.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


def acesso_terceiros_export(request, formato):
    formato = (formato or "").strip().lower()
    if not has_acesso_export_filters(request.GET):
        params = urlencode({"export_error": "Aplique ao menos um filtro para exportar os registros."})
        return redirect(f"{reverse('acesso_terceiro')}?{params}")

    queryset = build_acesso_base_qs()
    queryset = apply_acesso_filters(queryset, request.GET)

    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    if scope not in ("default", "descricao"):
        scope = "default"
    queryset = apply_acesso_search(queryset, query, scope)

    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    queryset, _, _ = apply_acesso_ordering(queryset, sort_field, sort_dir)

    if formato == "csv":
        return export_acessos_terceiros_csv(request, queryset)
    if formato in ("xlsx", "excel"):
        return export_acessos_terceiros_excel(request, queryset)
    if formato == "pdf":
        return export_acessos_terceiros_pdf(request, queryset)

    return api_error(
        code="invalid_export_format",
        message="Formato de exportação inválido. Use csv, xlsx ou pdf.",
        status=400,
    )
