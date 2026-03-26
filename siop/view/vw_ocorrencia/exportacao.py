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
from core.utils.formatters import (
    bool_ptbr as bool_ptbr,
    fmt_dt as fmt_dt,
    status_ptbr as status_ptbr,
    user_display as user_display,
)
from core.utils.helpers import anexos_total, build_rows
from ...models import Ocorrencia
from .common import display_user, format_datetime
from .query import build_ocorrencia_filtered_qs, has_ocorrencia_export_filters

OCORRENCIAS_EXPORT_HEADERS = [
    "ID", "Data/Hora", "Natureza", "Tipo", "Área", "Local", "Pessoa", "CFTV",
    "Bombeiro Civil", "Status", "Anexos", "Descrição", "Criado em", "Criado por", "Modificado em", "Modificado por",
]

OCORRENCIAS_EXPORT_PDF_HEADERS = [
    "ID", "Data/Hora", "Natureza", "Tipo", "Área", "Local", "Pessoa", "CFTV",
    "Bombeiro Civil", "Status", "Anexos", "Criado em", "Criado por", "Modificado em", "Modificado por",
]

OCORRENCIAS_EXPORT_BASE_COL_WIDTHS = [
    0.26 * 72, 0.95 * 72, 0.62 * 72, 0.85 * 72, 0.8 * 72, 1.2 * 72, 0.8 * 72, 0.5 * 72,
    0.75 * 72, 0.54 * 72, 0.45 * 72, 0.95 * 72, 0.95 * 72, 0.95 * 72, 0.95 * 72,
]


def get_ocorrencias_export_row_getters(include_description=False):
    getters = [
        lambda ocorrencia: ocorrencia.id,
        lambda ocorrencia: fmt_dt(ocorrencia.data_ocorrencia),
        lambda ocorrencia: ocorrencia.natureza or "",
        lambda ocorrencia: ocorrencia.tipo or "",
        lambda ocorrencia: ocorrencia.area or "",
        lambda ocorrencia: ocorrencia.local or "",
        lambda ocorrencia: ocorrencia.tipo_pessoa or "",
        lambda ocorrencia: bool_ptbr(ocorrencia.cftv),
        lambda ocorrencia: bool_ptbr(ocorrencia.bombeiro_civil),
        lambda ocorrencia: status_ptbr(ocorrencia.status),
        anexos_total,
    ]
    if include_description:
        getters.append(lambda ocorrencia: ocorrencia.descricao or "")
    getters.extend(
        [
            lambda ocorrencia: fmt_dt(ocorrencia.criado_em),
            lambda ocorrencia: user_display(getattr(ocorrencia, "criado_por", None)),
            lambda ocorrencia: fmt_dt(ocorrencia.modificado_em),
            lambda ocorrencia: user_display(getattr(ocorrencia, "modificado_por", None)),
        ]
    )
    return getters


def export_ocorrencias_pdf(request, queryset):
    return export_generic_pdf_impl(
        request,
        queryset,
        filename_prefix="ocorrencias",
        report_title="Relatório de Ocorrências",
        report_subject="Ocorrências",
        headers=OCORRENCIAS_EXPORT_PDF_HEADERS,
        row_getters=get_ocorrencias_export_row_getters(),
        base_col_widths=OCORRENCIAS_EXPORT_BASE_COL_WIDTHS,
        nowrap_indices={5},
        build_rows=build_rows,
    )


def export_ocorrencias_excel(request, queryset):
    return export_generic_excel_impl(
        request,
        queryset,
        filename_prefix="ocorrencias",
        sheet_title="Ocorrências",
        document_title="Relatório de Ocorrências",
        document_subject="Ocorrências",
        headers=OCORRENCIAS_EXPORT_HEADERS,
        row_getters=get_ocorrencias_export_row_getters(include_description=True),
    )


def export_ocorrencias_csv(request, queryset):
    return export_generic_csv_impl(
        request,
        queryset,
        filename_prefix="ocorrencias",
        headers=OCORRENCIAS_EXPORT_HEADERS,
        row_getters=get_ocorrencias_export_row_getters(include_description=True),
    )


def ocorrencia_export(request, formato):
    formato = (formato or "").strip().lower()

    if not has_ocorrencia_export_filters(request.GET):
        params = urlencode({"export_error": "Aplique ao menos um filtro para exportar os registros."})
        return redirect(f"{reverse('ocorrencia')}?{params}")

    queryset, _, _, _, _ = build_ocorrencia_filtered_qs(request)

    if formato == "pdf":
        return export_ocorrencias_pdf(request, queryset)
    if formato in ("xlsx", "excel"):
        return export_ocorrencias_excel(request, queryset)
    if formato == "csv":
        return export_ocorrencias_csv(request, queryset)

    return api_error(
        code="invalid_export_format",
        message="Formato de exportação inválido. Use csv, xlsx ou pdf.",
        status=400,
    )


def ocorrencia_export_view_pdf(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)

    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório da Ocorrência #{ocorrencia.id}")
    canvas.setAuthor(display_user(request.user))
    canvas.setSubject("Relatório de Ocorrência")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            generated_by=display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle="Módulo Ocorrências",
        )

    draw_page_chrome()

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, f"Relatório da Ocorrência: #{ocorrencia.id}")

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

    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora", format_datetime(ocorrencia.data_ocorrencia))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Status", "Finalizada" if ocorrencia.status else "Em aberto")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", display_user(ocorrencia.criado_por))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", display_user(ocorrencia.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", format_datetime(ocorrencia.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", format_datetime(ocorrencia.modificado_em))
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados da Ocorrência:")
    info_y -= 18

    draw_pdf_label_value(canvas, info_x, info_y, "Tipo de Pessoa", ocorrencia.tipo_pessoa or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Natureza da Ocorrência", ocorrencia.natureza or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Tipo de Ocorrência", ocorrencia.tipo or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Área", ocorrencia.area or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Local", ocorrencia.local or "-")
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Informações Complementares:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Imagens CFTV", "Sim" if ocorrencia.cftv else "Não")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Bombeiro Civil", "Sim" if ocorrencia.bombeiro_civil else "Não")
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
    canvas.drawString(info_x, desc_title_y, "Descrição da Ocorrência")

    desc_lines = wrap_pdf_text_lines(ocorrencia.descricao or "-", width - (info_x * 2))
    canvas.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, "Descrição da Ocorrência (continuação)")
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
    anexos = list(ocorrencia.anexos.all())
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

    filename = f"ocorrencia_{ocorrencia.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)
