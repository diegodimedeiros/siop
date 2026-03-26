import io
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.utils.catalogos import (
    catalogo_areas_data,
    catalogo_locais_por_area_data,
    catalogo_responsaveis_atendimento_data,
    catalogo_responsaveis_atendimento_display_map,
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
    as_dt_local as _as_dt_local,
    bool_ptbr as _bool_ptbr,
    fmt_dt as _fmt_dt,
    user_display as _user_display,
)
from core.utils.helpers import (
    anexos_total as _anexos_total,
    assinatura_status as _assinatura_status,
    build_rows as _build_rows,
    first_geolocalizacao_text as _first_geolocalizacao_text,
)
from controlebc.models import ControleAtendimento

CHAMADOS_EXPORT_HEADERS = [
    "ID", "Data/Hora", "Tipo de Pessoa", "Nome", "Documento", "Orgao Expedidor", "Idade", "Sexo", "Estado",
    "Ocorrencia", "Area", "Local", "Atendimento", "Acompanhante", "Grau de Parentesco",
    "Documento do Acompanhante", "Doenca Preexistente", "Alergia", "Plano de Saude", "Nome do Plano",
    "Numero da Carteirinha", "Primeiros Socorros", "Responsavel", "Seguiu Passeio", "Remocao",
    "Geolocalizacao", "Assinatura", "Criado em", "Criado por", "Modificado em", "Modificado por",
]

CHAMADOS_EXPORT_BASE_COL_WIDTHS = [
    0.35 * 72, 0.75 * 72, 0.80 * 72, 1.00 * 72, 0.90 * 72, 0.80 * 72, 0.40 * 72, 0.45 * 72, 0.40 * 72,
    0.55 * 72, 0.80 * 72, 0.65 * 72, 0.70 * 72, 0.55 * 72, 0.55 * 72, 0.75 * 72, 0.85 * 72, 0.55 * 72,
    0.45 * 72, 0.55 * 72, 0.80 * 72, 0.80 * 72, 0.80 * 72, 0.95 * 72, 0.55 * 72, 0.50 * 72, 1.10 * 72,
    0.60 * 72, 0.85 * 72, 0.85 * 72, 0.85 * 72, 0.85 * 72,
]


def _format_datetime(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else ""


def _display_user(user):
    if not user:
        return "Não registrado"
    return user.get_full_name() or user.username


def _get_chamados_export_row_getters():
    return [
        lambda c: c.id,
        lambda c: _fmt_dt(c.data_atendimento),
        lambda c: c.tipo_pessoa or "",
        lambda c: c.nome or "",
        lambda c: c.documento or "",
        lambda c: c.orgao_expedidor or "",
        lambda c: c.idade if c.idade is not None else "",
        lambda c: c.sexo or "",
        lambda c: c.estado or "",
        lambda c: c.tipo_ocorrencia or "",
        lambda c: c.area_atendimento or "",
        lambda c: c.local or "",
        lambda c: _bool_ptbr(c.atendimentos),
        lambda c: _bool_ptbr(c.acompanhante),
        lambda c: c.grau_parentesco or "",
        lambda c: c.documento_acompanhante or "",
        lambda c: _bool_ptbr(c.doenca_preexistente),
        lambda c: _bool_ptbr(c.alergia),
        lambda c: _bool_ptbr(c.plano_saude),
        lambda c: c.nome_plano_saude or "",
        lambda c: c.numero_carteirinha or "",
        lambda c: c.primeiros_socorros or "",
        lambda c: c.responsavel_atendimento or "",
        lambda c: _bool_ptbr(c.seguiu_passeio),
        lambda c: _bool_ptbr(c.remocao),
        _first_geolocalizacao_text,
        _assinatura_status,
        lambda c: _fmt_dt(c.criado_em),
        lambda c: _user_display(getattr(c, "criado_por", None)),
        lambda c: _fmt_dt(c.modificado_em),
        lambda c: _user_display(getattr(c, "modificado_por", None)),
    ]


def _build_chamados_export_filters(request):
    return {
        "registro_id": (request.GET.get("registro_id") or "").strip(),
        "tipo_pessoa": (request.GET.get("tipo_pessoa") or "").strip(),
        "tipo_ocorrencia": (request.GET.get("tipo_ocorrencia") or "").strip(),
        "area_atendimento": (request.GET.get("area_atendimento") or "").strip(),
        "local": (request.GET.get("local") or "").strip(),
        "nome": (request.GET.get("nome") or "").strip(),
        "atendimento": (request.GET.get("atendimento") or "").strip().lower(),
        "responsavel_atendimento": (request.GET.get("responsavel_atendimento") or "").strip(),
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
    }


def _apply_chamados_search(queryset, query):
    if not query:
        return queryset

    filtros = (
        Q(nome__icontains=query)
        | Q(documento__icontains=query)
        | Q(tipo_ocorrencia__icontains=query)
        | Q(area_atendimento__icontains=query)
        | Q(local__icontains=query)
        | Q(responsavel_atendimento__icontains=query)
    )
    if query.isdigit():
        filtros |= Q(id=int(query))
    return queryset.filter(filtros)


def _apply_chamados_export_filters(queryset, filters):
    if filters["registro_id"].isdigit():
        queryset = queryset.filter(id=int(filters["registro_id"]))
    if filters["tipo_pessoa"]:
        queryset = queryset.filter(tipo_pessoa=filters["tipo_pessoa"])
    if filters["tipo_ocorrencia"]:
        queryset = queryset.filter(tipo_ocorrencia__icontains=filters["tipo_ocorrencia"])
    if filters["area_atendimento"]:
        queryset = queryset.filter(area_atendimento=filters["area_atendimento"])
    if filters["local"]:
        queryset = queryset.filter(local=filters["local"])
    if filters["nome"]:
        queryset = queryset.filter(nome__icontains=filters["nome"])
    if filters["atendimento"] == "nao":
        queryset = queryset.filter(atendimentos=False)
    elif filters["atendimento"] == "sim":
        queryset = queryset.filter(atendimentos=True)
    if filters["responsavel_atendimento"]:
        queryset = queryset.filter(responsavel_atendimento__icontains=filters["responsavel_atendimento"])
    if filters["data_inicio"]:
        queryset = queryset.filter(data_atendimento__gte=_as_dt_local(filters["data_inicio"]))
    if filters["data_fim"]:
        queryset = queryset.filter(data_atendimento__lte=_as_dt_local(filters["data_fim"]))
    return queryset


def _build_chamado_file_entry(arquivo, tipo, url):
    return {
        "id": arquivo.id,
        "nome_arquivo": arquivo.nome_arquivo or "-",
        "tipo": tipo,
        "data": _format_datetime(arquivo.criado_em) or "-",
        "url": url,
    }


def _decorate_chamados_for_view(chamados, responsaveis_display_map):
    for chamado in chamados:
        chamado.responsavel_atendimento_display = responsaveis_display_map.get(
            chamado.responsavel_atendimento,
            chamado.responsavel_atendimento or "-",
        )
        chamado.anexos_view_json = json.dumps(
            [
                _build_chamado_file_entry(anexo, "Anexo", f"/controlebc/arquivos/anexo/{anexo.id}/")
                for anexo in chamado.anexos.all()
            ],
            ensure_ascii=True,
        )
        chamado.fotos_view_json = json.dumps(
            [
                _build_chamado_file_entry(foto, "Foto", f"/controlebc/arquivos/foto/{foto.id}/")
                for foto in chamado.fotos.all()
            ],
            ensure_ascii=True,
        )


def _decorate_chamados_for_export(chamados, responsaveis_display_map):
    for chamado in chamados:
        chamado.responsavel_atendimento_display = responsaveis_display_map.get(
            chamado.responsavel_atendimento,
            chamado.responsavel_atendimento or "-",
        )


def export_controlebc_chamados_pdf(request, queryset):
    return _export_generic_pdf(
        request,
        queryset,
        filename_prefix="controlebc_chamados",
        report_title="Relatorio de Chamados - ControleBC",
        report_subject="Chamados ControleBC",
        headers=CHAMADOS_EXPORT_HEADERS,
        row_getters=_get_chamados_export_row_getters(),
        base_col_widths=CHAMADOS_EXPORT_BASE_COL_WIDTHS,
        nowrap_indices={0, 1, 4},
        build_rows=_build_rows,
    )


def export_controlebc_chamados_excel(request, queryset):
    return _export_generic_excel(
        request,
        queryset,
        filename_prefix="controlebc_chamados",
        sheet_title="Controle BC",
        document_title="Relatorio de Chamados - Controle BC",
        document_subject="Chamados Controle BC",
        headers=CHAMADOS_EXPORT_HEADERS,
        row_getters=_get_chamados_export_row_getters(),
    )


def export_controlebc_chamados_csv(request, queryset):
    return _export_generic_csv(
        request,
        queryset,
        filename_prefix="controlebc_chamados",
        headers=CHAMADOS_EXPORT_HEADERS,
        row_getters=_get_chamados_export_row_getters(),
    )


def chamados(request):
    q = (request.GET.get("q") or "").strip()
    scope = (request.GET.get("scope") or "").strip()
    page_number = request.GET.get("page") or 1
    export = (request.GET.get("export") or "").strip().lower()
    active_tab = (request.GET.get("tab") or "list").strip().lower()
    areas = catalogo_areas_data()
    locais_por_area = {area: catalogo_locais_por_area_data(area) for area in areas}
    responsaveis_display_map = catalogo_responsaveis_atendimento_display_map()
    base_qs = (
        ControleAtendimento.objects.select_related("criado_por")
        .prefetch_related("anexos", "fotos", "geolocalizacoes", "assinaturas")
        .order_by("-data_atendimento", "-id")
    )
    chamados_qs = _apply_chamados_search(base_qs, q)
    export_filters = _build_chamados_export_filters(request)
    has_export_filters = any(export_filters.values())
    export_qs = _apply_chamados_export_filters(base_qs, export_filters)

    if export == "csv":
        return export_controlebc_chamados_csv(request, export_qs)
    if export == "xlsx":
        return export_controlebc_chamados_excel(request, export_qs)
    if export == "pdf":
        return export_controlebc_chamados_pdf(request, export_qs)

    paginator = Paginator(chamados_qs, 20)
    page_obj = paginator.get_page(page_number)
    chamados_data = list(page_obj.object_list)
    _decorate_chamados_for_view(chamados_data, responsaveis_display_map)

    export_chamados_data = list(export_qs)
    _decorate_chamados_for_export(export_chamados_data, responsaveis_display_map)

    return render(
        request,
        "controlebc/chamados.html",
        {
            "active_tab": active_tab if active_tab in {"list", "view", "export"} else "list",
            "chamados": chamados_data,
            "page_obj": page_obj,
            "export_chamados": export_chamados_data,
            "export_filters": export_filters,
            "has_export_filters": has_export_filters,
            "q": q,
            "scope": scope,
            "areas": areas,
            "locais_por_area": locais_por_area,
            "responsaveis_atendimento": catalogo_responsaveis_atendimento_data(),
            "total_chamados": chamados_qs.count(),
            "total_realizados": chamados_qs.filter(atendimentos=True).count(),
            "total_pendentes": chamados_qs.filter(atendimentos=False).count(),
        },
    )


@require_GET
@login_required
def chamado_export_view_pdf(request, pk):
    chamado = get_object_or_404(
        ControleAtendimento.objects.select_related("criado_por", "modificado_por").prefetch_related(
            "anexos",
            "fotos",
            "geolocalizacoes",
            "assinaturas",
            "testemunhas",
        ),
        pk=pk,
    )

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase.pdfmetrics import stringWidth
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    NumberedCanvas = build_numbered_canvas_class(width)
    c = NumberedCanvas(buffer, pagesize=A4)
    c.setTitle(f"Relatório do Atendimento #{chamado.id}")
    c.setAuthor(_display_user(request.user))
    c.setSubject("Relatório de Atendimento - ControleBC")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page():
        draw_pdf_page_chrome(
            canvas=c,
            page_width=width,
            page_height=height,
            generated_by=_display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
            hash_cadastro=chamado.hash_cadastro,
        )

    draw_page()

    geolocalizacao = chamado.geolocalizacoes.order_by("criado_em").first()
    assinatura = chamado.assinaturas.order_by("criado_em").first()

    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 140, f"Relatório do Atendimento: #{chamado.id}")

    c.setFont("Helvetica", 10)
    info_x = 48
    info_block_w = width - (info_x * 2)
    info_y = height - 190
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)
    min_y = 72
    page_content_top = height - 120
    section_padding_x = 12
    section_padding_y = 12
    section_gap = 14
    section_content_top_gap = 8
    section_bottom_padding = 0
    min_label_col_w = 64
    max_label_col_w = 120

    def get_label_layout(items, font_size=10):
        label_widths = [stringWidth(f"{label}:", "Helvetica-Bold", font_size) for label, _ in items]
        label_col_w = min(max(max(label_widths, default=0) + 8, min_label_col_w), max_label_col_w)
        value_col_x = info_x + section_padding_x + label_col_w
        value_wrap_w = info_block_w - (section_padding_x * 2) - label_col_w - 8
        return label_col_w, value_col_x, value_wrap_w

    def next_page_if_needed(y, title=None):
        if y >= min_y:
            return y
        c.showPage()
        draw_page()
        c.setFillColorRGB(*dark_text)
        if title:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(info_x, page_content_top, title)
            return page_content_top - 18
        return page_content_top

    def ensure_space(y, required_height, title=None):
        if y - required_height >= min_y:
            return y
        return next_page_if_needed(min_y - 1, title)

    def section_height(items):
        _, _, value_wrap_w = get_label_layout(items)
        height = section_padding_y + 18 + section_content_top_gap + section_bottom_padding
        for index, (_, value) in enumerate(items):
            text = str(value or "-")
            lines = wrap_pdf_text_lines(text, value_wrap_w, font_size=10)
            height += max(len(lines), 1) * 12
            if index < len(items) - 1:
                height += 2
        return height

    def draw_section(title, items, y):
        _, value_col_x, value_wrap_w = get_label_layout(items)
        required_height = section_height(items)
        if y - required_height < min_y:
            y = next_page_if_needed(min_y - 1)

        title_y = y - section_padding_y
        box_top_y = title_y - 10
        bottom_y = box_top_y - required_height
        c.roundRect(info_x, bottom_y, info_block_w, required_height, 8, stroke=1, fill=0)

        c.setFillColorRGB(*dark_text)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, title_y, title)
        y = box_top_y - section_padding_y - section_content_top_gap
        for index, (label, value) in enumerate(items):
            text = str(value or "-")
            lines = wrap_pdf_text_lines(text, value_wrap_w, font_size=10)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(info_x + section_padding_x, y, f"{label}:")
            c.setFont("Helvetica", 10)
            c.drawString(value_col_x, y, lines[0] if lines else "-")
            for continuation in lines[1:]:
                y -= 12
                c.drawString(value_col_x, y, continuation)
            if index < len(items) - 1:
                y -= 12
                y -= 2
        return bottom_y - section_gap

    def draw_list_section(title, lines, y, font_size=10):
        content_lines = lines or ["Nenhum anexo."]
        required_height = section_padding_y * 2 + 18 + (len(content_lines) * 12)
        y = ensure_space(y, required_height, title)
        title_y = y - section_padding_y
        box_top_y = title_y - 10
        bottom_y = box_top_y - required_height
        c.roundRect(info_x, bottom_y, info_block_w, required_height, 8, stroke=1, fill=0)

        c.setFillColorRGB(*dark_text)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, title_y, title)
        line_y = box_top_y - section_padding_y
        c.setFont("Helvetica", font_size)
        for line in content_lines:
            c.drawString(info_x + section_padding_x, line_y, line)
            line_y -= 12
        return bottom_y - section_gap

    def draw_text_section(title, lines, y, font_size=10):
        content_lines = lines or ["-"]
        required_height = section_padding_y * 2 + 18 + (len(content_lines) * 13)
        y = ensure_space(y, required_height, title)
        title_y = y - section_padding_y
        box_top_y = title_y - 10
        bottom_y = box_top_y - required_height
        c.roundRect(info_x, bottom_y, info_block_w, required_height, 8, stroke=1, fill=0)

        c.setFillColorRGB(*dark_text)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, title_y, title)
        line_y = box_top_y - section_padding_y
        c.setFont("Helvetica", font_size)
        for line in content_lines:
            c.drawString(info_x + section_padding_x, line_y, line)
            line_y -= 13
        return bottom_y - section_gap

    assinatura_title_y = next_page_if_needed(info_y)
    signature_box_h = 80
    signature_box_w = 260
    signature_box_x = (width - signature_box_w) / 2
    signature_center_x = width / 2
    c.setFillColorRGB(*dark_text)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(signature_center_x, assinatura_title_y, "Assinatura")
    assinatura_bottom_y = assinatura_title_y - 14
    if assinatura:
        try:
            signature_reader = ImageReader(io.BytesIO(bytes(assinatura.arquivo)))
            img_w, img_h = signature_reader.getSize()
            scale = min(signature_box_w / float(img_w), signature_box_h / float(img_h))
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = signature_box_x + ((signature_box_w - draw_w) / 2)
            draw_y = assinatura_bottom_y - draw_h
            c.rect(
                signature_box_x,
                assinatura_bottom_y - signature_box_h,
                signature_box_w,
                signature_box_h,
                stroke=1,
                fill=0,
            )
            c.drawImage(signature_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
        except Exception:
            c.setFont("Helvetica", 9)
            c.drawCentredString(
                signature_center_x,
                assinatura_bottom_y - 16,
                "Assinatura indisponível para visualização.",
            )
            c.rect(
                signature_box_x,
                assinatura_bottom_y - signature_box_h,
                signature_box_w,
                signature_box_h,
                stroke=1,
                fill=0,
            )
    else:
        c.setFont("Helvetica", 9)
        c.drawCentredString(signature_center_x, assinatura_bottom_y - 16, "Assinatura não capturada.")
        c.rect(
            signature_box_x,
            assinatura_bottom_y - signature_box_h,
            signature_box_w,
            signature_box_h,
            stroke=1,
            fill=0,
        )

    nome_y = assinatura_bottom_y - signature_box_h - 14
    nome_y = ensure_space(nome_y, 12)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(signature_center_x, nome_y, chamado.nome or "-")

    details_y = ensure_space(nome_y - 24, line_h * 3 + 28, "Detalhes da Assinatura (continuação)")
    geo_text = "-"
    if geolocalizacao:
        geo_text = f"{geolocalizacao.latitude}, {geolocalizacao.longitude}"
    c.setFont("Helvetica", 9)
    draw_pdf_label_value(c, info_x, details_y, "Geolocalização", geo_text, font_size=9)
    details_y -= line_h

    signature_hash_label = "Hash da Assinatura: "
    signature_hash_offset = stringWidth(signature_hash_label, "Helvetica-Bold", 9) + 4
    signature_hash_lines = wrap_pdf_text_lines(
        assinatura.hash_assinatura if assinatura and assinatura.hash_assinatura else "-",
        width - (info_x * 2) - signature_hash_offset,
        font_size=9,
    )
    c.setFont("Helvetica-Bold", 9)
    c.drawString(info_x, details_y, signature_hash_label)
    c.setFont("Helvetica", 9)
    first_hash_y = ensure_space(
        details_y,
        max(len(signature_hash_lines), 1) * 11 + 6,
        "Detalhes da Assinatura (continuação)",
    )
    for idx, line in enumerate(signature_hash_lines):
        line_y = first_hash_y - (idx * 11)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + (signature_hash_offset if idx == 0 else 0), line_y, line)
    details_y = first_hash_y - max(len(signature_hash_lines), 1) * 11 - 4

    atendimento_hash_label = "Hash do Atendimento: "
    atendimento_hash_offset = stringWidth(atendimento_hash_label, "Helvetica-Bold", 9) + 4
    chamado_hash_lines = wrap_pdf_text_lines(
        chamado.hash_cadastro or "-",
        width - (info_x * 2) - atendimento_hash_offset,
        font_size=9,
    )
    c.setFont("Helvetica-Bold", 9)
    c.drawString(info_x, details_y, atendimento_hash_label)
    c.setFont("Helvetica", 9)
    first_chamado_hash_y = ensure_space(
        details_y,
        max(len(chamado_hash_lines), 1) * 11 + 6,
        "Detalhes da Assinatura (continuação)",
    )
    for idx, line in enumerate(chamado_hash_lines):
        line_y = first_chamado_hash_y - (idx * 11)
        c.setFont("Helvetica", 9)
        c.drawString(info_x + (atendimento_hash_offset if idx == 0 else 0), line_y, line)
    details_y = first_chamado_hash_y - max(len(chamado_hash_lines), 1) * 11 - 8

    metadata_y = next_page_if_needed(details_y - 10)
    c.setFont("Helvetica", 9)
    draw_pdf_label_value(c, info_x, metadata_y, "Criado por", _display_user(chamado.criado_por), font_size=9)
    draw_pdf_label_value(c, right_x, metadata_y, "Modificado por", _display_user(chamado.modificado_por), font_size=9)
    metadata_y -= line_h
    draw_pdf_label_value(c, info_x, metadata_y, "Criado em", _format_datetime(chamado.criado_em), font_size=9)
    draw_pdf_label_value(c, right_x, metadata_y, "Modificado em", _format_datetime(chamado.modificado_em), font_size=9)
    details_y = metadata_y - block_gap

    info_y = draw_section(
        "Dados Gerais",
        [
            ("Data/Hora", _format_datetime(chamado.data_atendimento)),
            ("Atendimento", "Realizado" if chamado.atendimentos else "Não realizado"),
            ("Tipo de Pessoa", chamado.tipo_pessoa),
            ("Nome", chamado.nome),
            ("Documento", chamado.documento),
            ("Órgão Expedidor", chamado.orgao_expedidor),
            ("Nacionalidade", chamado.nacionalidade),
            ("Idade", chamado.idade),
            ("Sexo", chamado.sexo),
        ],
        details_y - 10,
    )

    info_y = draw_section(
        "Contato",
        [
            ("Endereço", chamado.endereco),
            ("Bairro", chamado.bairro),
            ("Cidade", chamado.cidade),
            ("UF", chamado.uf),
            ("Estado", chamado.estado),
            ("País", chamado.pais),
            ("Telefone", chamado.telefone),
            ("Email", chamado.email),
        ],
        info_y,
    )

    info_y = draw_section(
        "Atendimento",
        [
            ("Área", chamado.area_atendimento),
            ("Local", chamado.local),
            ("Tipo de Ocorrência", chamado.tipo_ocorrencia),
            ("Bombeiro Civil", chamado.responsavel_atendimento),
            ("Primeiros Socorros", chamado.primeiros_socorros),
            ("Seguiu Passeio", "Sim" if chamado.seguiu_passeio else "Não"),
            ("Remoção", "Sim" if chamado.remocao else "Não"),
            ("Transporte", chamado.transporte),
            ("Encaminhamento", chamado.encaminhamento),
            ("Hospital", chamado.hospital),
            ("Médico Responsável", chamado.medico_responsavel),
            ("CRM", chamado.crm),
        ],
        info_y,
    )

    info_y = draw_section(
        "Acompanhante",
        [
            ("Acompanhante", "Sim" if chamado.acompanhante else "Não"),
            ("Nome", chamado.nome_acompanhante),
            ("Grau de Parentesco", chamado.grau_parentesco),
            ("Documento", chamado.documento_acompanhante),
        ],
        info_y,
    )

    info_y = draw_section(
        "Saúde",
        [
            ("Doença Preexistente", "Sim" if chamado.doenca_preexistente else "Não"),
            ("Descrição da Doença", chamado.descricao_doenca),
            ("Alergia", "Sim" if chamado.alergia else "Não"),
            ("Descrição da Alergia", chamado.descricao_alergia),
            ("Plano de Saúde", "Sim" if chamado.plano_saude else "Não"),
            ("Nome do Plano", chamado.nome_plano_saude),
            ("Número da Carteirinha", chamado.numero_carteirinha),
        ],
        info_y,
    )

    testemunhas = list(chamado.testemunhas.all())
    if testemunhas:
        details_y = next_page_if_needed(info_y - 10)
        for idx, testemunha in enumerate(testemunhas, start=1):
            details_y = draw_section(
                f"Testemunha {idx}",
                [
                    ("Nome", testemunha.nome),
                    ("Idade", testemunha.idade),
                    ("Documento", testemunha.documento),
                    ("Telefone", testemunha.telefone),
                    ("Endereço", testemunha.endereco),
                ],
                details_y,
            )
    else:
        details_y = info_y

    anexos = list(chamado.anexos.all()) + list(chamado.fotos.all())
    anexos_lines = [f"{idx}. {anexo.nome_arquivo}" for idx, anexo in enumerate(anexos, start=1)]
    y = draw_list_section("Anexos", anexos_lines, details_y - 10, font_size=9)

    desc_lines = wrap_pdf_text_lines(
        chamado.descricao or "-",
        width - (info_x * 2) - (section_padding_x * 2),
        font_size=10,
    )
    draw_text_section("Descrição do Atendimento", desc_lines, y - 12, font_size=10)

    c.showPage()
    c.save()
    buffer.seek(0)

    filename = (
        f"controlebc_chamado_{chamado.id}_view_"
        f"{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    return FileResponse(buffer, as_attachment=True, filename=filename)
