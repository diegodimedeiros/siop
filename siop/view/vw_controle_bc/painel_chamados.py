import io

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.utils.exports import (
    export_generic_csv,
    export_generic_excel,
    export_generic_pdf,
)
from core.utils.exports.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)
from core.utils.formatters import as_dt_local, bool_ptbr, fmt_dt, user_display
from core.utils.helpers import anexos_total, assinatura_status, build_rows, first_geolocalizacao_text
from siop.models import ControleAtendimento, Manejo


ATENDIMENTO_EXPORT_HEADERS = [
    "ID",
    "Data/Hora",
    "Tipo de Pessoa",
    "Nome Completo",
    "Documento",
    "Área",
    "Local",
    "Tipo de Ocorrência",
    "Primeiros Socorros",
    "Responsável",
    "Atendimento Realizado",
    "Recusa de Atendimento",
    "Seguiu para o Passeio",
    "Houve Remoção",
    "Geolocalização",
    "Assinatura",
    "Criado em",
    "Criado por",
    "Modificado em",
    "Modificado por",
]

ATENDIMENTO_EXPORT_BASE_COL_WIDTHS = [
    0.35 * 72,
    0.75 * 72,
    0.80 * 72,
    1.20 * 72,
    0.95 * 72,
    0.80 * 72,
    0.80 * 72,
    1.05 * 72,
    0.95 * 72,
    1.05 * 72,
    0.80 * 72,
    0.85 * 72,
    0.90 * 72,
    0.85 * 72,
    1.10 * 72,
    0.70 * 72,
    0.85 * 72,
    0.90 * 72,
    0.85 * 72,
    0.90 * 72,
]

MANEJO_EXPORT_HEADERS = [
    "ID",
    "Data/Hora",
    "Classe",
    "Nome Científico",
    "Nome Popular",
    "Estágio de Desenvolvimento",
    "Importância Médica",
    "Área de Captura",
    "Local de Captura",
    "Responsável",
    "Manejo Realizado",
    "Área de Soltura",
    "Local de Soltura",
    "Órgão Público Acionado",
    "Órgão Público",
    "Boletim de Ocorrência",
    "Geolocalização da Captura",
    "Geolocalização da Soltura",
    "Fotos",
    "Anexos",
    "Criado em",
    "Criado por",
    "Modificado em",
    "Modificado por",
]

MANEJO_EXPORT_BASE_COL_WIDTHS = [
    0.35 * 72,
    0.75 * 72,
    0.65 * 72,
    1.15 * 72,
    1.00 * 72,
    0.90 * 72,
    0.75 * 72,
    0.85 * 72,
    0.85 * 72,
    1.00 * 72,
    0.85 * 72,
    0.85 * 72,
    0.85 * 72,
    0.90 * 72,
    0.95 * 72,
    0.90 * 72,
    1.10 * 72,
    1.10 * 72,
    0.55 * 72,
    0.55 * 72,
    0.85 * 72,
    0.90 * 72,
    0.85 * 72,
    0.90 * 72,
]


def _resolve_active_tab(requested_tab, selected_item):
    active_tab = requested_tab if requested_tab in {"list", "export"} else "list"
    if requested_tab == "view" and selected_item is not None:
        active_tab = "view"
    return active_tab


def _build_atendimento_export_filters(request):
    return {
        "area_atendimento": (request.GET.get("area_atendimento") or "").strip(),
        "local": (request.GET.get("local") or "").strip(),
        "tipo_ocorrencia": (request.GET.get("tipo_ocorrencia") or "").strip(),
        "primeiros_socorros": (request.GET.get("primeiros_socorros") or "").strip(),
        "atendimento": (request.GET.get("atendimento") or "").strip().lower(),
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
    }


def _apply_atendimento_export_filters(queryset, filters):
    if filters["area_atendimento"]:
        queryset = queryset.filter(area_atendimento=filters["area_atendimento"])
    if filters["local"]:
        queryset = queryset.filter(local=filters["local"])
    if filters["tipo_ocorrencia"]:
        queryset = queryset.filter(tipo_ocorrencia=filters["tipo_ocorrencia"])
    if filters["primeiros_socorros"]:
        queryset = queryset.filter(primeiros_socorros=filters["primeiros_socorros"])
    if filters["atendimento"] == "sim":
        queryset = queryset.filter(atendimentos=True)
    elif filters["atendimento"] == "nao":
        queryset = queryset.filter(atendimentos=False)
    if filters["data_inicio"]:
        queryset = queryset.filter(data_atendimento__gte=as_dt_local(filters["data_inicio"]))
    if filters["data_fim"]:
        queryset = queryset.filter(data_atendimento__lte=as_dt_local(filters["data_fim"]))
    return queryset


def _get_atendimento_export_row_getters():
    return [
        lambda item: item.id,
        lambda item: fmt_dt(item.data_atendimento),
        lambda item: item.tipo_pessoa or "",
        lambda item: item.pessoa.nome if item.pessoa_id else "",
        lambda item: item.pessoa.documento if item.pessoa_id else "",
        lambda item: item.area_atendimento or "",
        lambda item: item.local or "",
        lambda item: item.tipo_ocorrencia or "",
        lambda item: item.primeiros_socorros or "",
        lambda item: item.responsavel_atendimento or "",
        lambda item: bool_ptbr(item.atendimentos),
        lambda item: bool_ptbr(item.recusa_atendimento),
        lambda item: bool_ptbr(item.seguiu_passeio),
        lambda item: bool_ptbr(item.houve_remocao),
        first_geolocalizacao_text,
        assinatura_status,
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]


def _export_atendimento_csv(request, queryset):
    return export_generic_csv(
        request,
        queryset,
        filename_prefix="controlebc_atendimentos",
        headers=ATENDIMENTO_EXPORT_HEADERS,
        row_getters=_get_atendimento_export_row_getters(),
    )


def _export_atendimento_excel(request, queryset):
    return export_generic_excel(
        request,
        queryset,
        filename_prefix="controlebc_atendimentos",
        sheet_title="Atendimentos",
        document_title="Relatório de Atendimentos - Controle BC",
        document_subject="Atendimentos Controle BC",
        headers=ATENDIMENTO_EXPORT_HEADERS,
        row_getters=_get_atendimento_export_row_getters(),
    )


def _export_atendimento_pdf(request, queryset):
    return export_generic_pdf(
        request,
        queryset,
        filename_prefix="controlebc_atendimentos",
        report_title="Relatório de Atendimentos - Controle BC",
        report_subject="Atendimentos Controle BC",
        headers=ATENDIMENTO_EXPORT_HEADERS,
        row_getters=_get_atendimento_export_row_getters(),
        base_col_widths=ATENDIMENTO_EXPORT_BASE_COL_WIDTHS,
        nowrap_indices={0, 1, 4},
        build_rows=build_rows,
    )


def _build_manejo_export_filters(request):
    return {
        "classe": (request.GET.get("classe") or "").strip(),
        "area_captura": (request.GET.get("area_captura") or "").strip(),
        "local_captura": (request.GET.get("local_captura") or "").strip(),
        "status": (request.GET.get("status") or "").strip().lower(),
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
    }


def _apply_manejo_export_filters(queryset, filters):
    if filters["classe"]:
        queryset = queryset.filter(classe=filters["classe"])
    if filters["area_captura"]:
        queryset = queryset.filter(area_captura=filters["area_captura"])
    if filters["local_captura"]:
        queryset = queryset.filter(local_captura=filters["local_captura"])
    if filters["status"] == "sim":
        queryset = queryset.filter(realizado_manejo=True)
    elif filters["status"] == "nao":
        queryset = queryset.filter(realizado_manejo=False)
    if filters["data_inicio"]:
        queryset = queryset.filter(data_hora__gte=as_dt_local(filters["data_inicio"]))
    if filters["data_fim"]:
        queryset = queryset.filter(data_hora__lte=as_dt_local(filters["data_fim"]))
    return queryset


def _manejo_geolocalizacao_text(item, tipo):
    geo = item.geolocalizacoes.filter(tipo=tipo).order_by("criado_em").first()
    if not geo:
        return ""
    return f"{geo.latitude}, {geo.longitude}"


def _get_manejo_export_row_getters():
    return [
        lambda item: item.id,
        lambda item: fmt_dt(item.data_hora),
        lambda item: item.classe or "",
        lambda item: item.nome_cientifico or "",
        lambda item: item.nome_popular or "",
        lambda item: item.estagio_desenvolvimento or "",
        lambda item: bool_ptbr(item.importancia_medica),
        lambda item: item.area_captura or "",
        lambda item: item.local_captura or "",
        lambda item: item.responsavel_manejo or "",
        lambda item: bool_ptbr(item.realizado_manejo),
        lambda item: item.area_soltura or "",
        lambda item: item.local_soltura or "",
        lambda item: bool_ptbr(item.acionado_orgao_publico),
        lambda item: item.orgao_publico or "",
        lambda item: item.numero_boletim_ocorrencia or "",
        lambda item: _manejo_geolocalizacao_text(item, "captura"),
        lambda item: _manejo_geolocalizacao_text(item, "soltura"),
        lambda item: item.fotos.count(),
        anexos_total,
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]


def _export_manejo_csv(request, queryset):
    return export_generic_csv(
        request,
        queryset,
        filename_prefix="controlebc_manejos",
        headers=MANEJO_EXPORT_HEADERS,
        row_getters=_get_manejo_export_row_getters(),
    )


def _export_manejo_excel(request, queryset):
    return export_generic_excel(
        request,
        queryset,
        filename_prefix="controlebc_manejos",
        sheet_title="Manejos",
        document_title="Relatório de Manejos - Controle BC",
        document_subject="Manejos Controle BC",
        headers=MANEJO_EXPORT_HEADERS,
        row_getters=_get_manejo_export_row_getters(),
    )


def _export_manejo_pdf(request, queryset):
    return export_generic_pdf(
        request,
        queryset,
        filename_prefix="controlebc_manejos",
        report_title="Relatório de Manejos - Controle BC",
        report_subject="Manejos Controle BC",
        headers=MANEJO_EXPORT_HEADERS,
        row_getters=_get_manejo_export_row_getters(),
        base_col_widths=MANEJO_EXPORT_BASE_COL_WIDTHS,
        nowrap_indices={0, 1},
        build_rows=build_rows,
    )


@login_required
def chamados(request):
    q = (request.GET.get("q") or "").strip()
    page_number = request.GET.get("page") or 1
    selected_id = (request.GET.get("id") or "").strip()
    requested_tab = (request.GET.get("tab") or "").strip()
    export = (request.GET.get("export") or "").strip().lower()

    queryset = (
        ControleAtendimento.objects.select_related("pessoa", "criado_por", "modificado_por")
        .prefetch_related("anexos", "geolocalizacoes", "assinaturas")
        .order_by("-data_atendimento", "-id")
    )

    if q:
        queryset = queryset.filter(
            Q(pessoa__nome__icontains=q)
            | Q(pessoa__documento__icontains=q)
            | Q(area_atendimento__icontains=q)
            | Q(local__icontains=q)
            | Q(tipo_ocorrencia__icontains=q)
            | Q(descricao__icontains=q)
        )

    export_filters = _build_atendimento_export_filters(request)
    export_queryset = _apply_atendimento_export_filters(queryset, export_filters)

    if export == "csv":
        return _export_atendimento_csv(request, export_queryset)
    if export == "xlsx":
        return _export_atendimento_excel(request, export_queryset)
    if export == "pdf":
        return _export_atendimento_pdf(request, export_queryset)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(page_number)

    selected_chamado = None
    if selected_id.isdigit():
        selected_chamado = queryset.filter(pk=int(selected_id)).first()
    if selected_chamado is None:
        selected_chamado = page_obj.object_list[0] if page_obj.object_list else None

    export_chamados = list(export_queryset[:200])
    export_areas = list(
        queryset.exclude(area_atendimento__isnull=True)
        .exclude(area_atendimento__exact="")
        .values_list("area_atendimento", flat=True)
        .distinct()
        .order_by("area_atendimento")
    )
    export_locais = list(
        queryset.exclude(local__isnull=True)
        .exclude(local__exact="")
        .values_list("local", flat=True)
        .distinct()
        .order_by("local")
    )
    export_tipos = list(
        queryset.exclude(tipo_ocorrencia__isnull=True)
        .exclude(tipo_ocorrencia__exact="")
        .values_list("tipo_ocorrencia", flat=True)
        .distinct()
        .order_by("tipo_ocorrencia")
    )
    export_primeiros_socorros = list(
        queryset.exclude(primeiros_socorros__isnull=True)
        .exclude(primeiros_socorros__exact="")
        .values_list("primeiros_socorros", flat=True)
        .distinct()
        .order_by("primeiros_socorros")
    )

    return render(
        request,
        "controle_bc/atendimento/chamados.html",
        {
            "q": q,
            "active_tab": _resolve_active_tab(requested_tab, selected_chamado),
            "page_obj": page_obj,
            "selected_chamado": selected_chamado,
            "export_filters": export_filters,
            "export_chamados": export_chamados,
            "export_areas": export_areas,
            "export_locais": export_locais,
            "export_tipos_ocorrencia": export_tipos,
            "export_primeiros_socorros": export_primeiros_socorros,
            "total_chamados": queryset.count(),
            "total_realizados": queryset.filter(atendimentos=True).count(),
            "total_pendentes": queryset.filter(atendimentos=False).count(),
            "total_export_chamados": export_queryset.count(),
        },
    )


@require_GET
@login_required
def chamado_export_view_pdf(request, pk):
    chamado = get_object_or_404(
        ControleAtendimento.objects.select_related(
            "pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"
        ).prefetch_related("anexos", "fotos", "fotos__geolocalizacoes", "geolocalizacoes", "assinaturas", "testemunhas"),
        pk=pk,
    )

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    def display_user(user):
        if not user:
            return "Não registrado"
        return user.get_full_name() or user.username

    def format_datetime(value):
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else "-"

    def calc_age_on_attendance(birth_date, attendance_dt):
        if not birth_date or not attendance_dt:
            return "-"
        attendance_date = timezone.localtime(attendance_dt).date()
        years = attendance_date.year - birth_date.year
        if (attendance_date.month, attendance_date.day) < (birth_date.month, birth_date.day):
            years -= 1
        return str(years)

    buffer = io.BytesIO()
    width, height = A4
    numbered_canvas = build_numbered_canvas_class(width)
    pdf = numbered_canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Relatório do Atendimento #{chamado.id}")
    pdf.setAuthor(display_user(request.user))
    pdf.setSubject("Relatório de Atendimento")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=pdf,
            page_width=width,
            page_height=height,
            generated_by=display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
            hash_cadastro=chamado.hash_atendimento,
            footer_suffix="- Módulo Controle BC",
            footer_on_two_lines=True,
            header_subtitle="Módulo BC",
        )

    draw_page_chrome()
    pdf.setFillColorRGB(*dark_text)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(width / 2, height - 140, f"Relatório do Atendimento: #{chamado.id}")

    info_block_w = 430
    info_x = (width - info_block_w) / 2
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    contato = chamado.contato
    pessoa = chamado.pessoa
    assinatura = chamado.assinaturas.order_by("criado_em").first()
    geolocalizacao_principal = chamado.geolocalizacoes.order_by("criado_em").first()
    fotos = list(chamado.fotos.all())
    testemunhas = list(chamado.testemunhas.all())
    acompanhante = chamado.acompanhante_pessoa

    def ensure_space(current_y, needed=80, title=None):
        if current_y >= min_y + needed:
            return current_y
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        if title:
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(info_x, page_content_top, title)
            return page_content_top - 18
        return page_content_top

    draw_pdf_label_value(pdf, info_x, info_y, "Data/Hora", format_datetime(chamado.data_atendimento))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Status", "Realizado" if chamado.atendimentos else "Pendente")
    draw_pdf_label_value(pdf, right_x, info_y, "Recusa de Atendimento", "Sim" if chamado.recusa_atendimento else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Criado por", display_user(chamado.criado_por))
    draw_pdf_label_value(pdf, right_x, info_y, "Modificado por", display_user(chamado.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Criado em", format_datetime(chamado.criado_em))
    draw_pdf_label_value(pdf, right_x, info_y, "Modificado em", format_datetime(chamado.modificado_em))
    info_y -= (line_h + block_gap)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Dados do Atendido:")
    info_y -= 18

    draw_pdf_label_value(pdf, info_x, info_y, "Tipo de Pessoa", chamado.tipo_pessoa or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Nome completo", getattr(pessoa, "nome", "-"))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Documento", getattr(pessoa, "documento", "-"))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Sexo", getattr(pessoa, "sexo", "-"))
    info_y -= line_h
    nascimento = getattr(pessoa, "data_nascimento", None)
    draw_pdf_label_value(pdf, info_x, info_y, "Nascimento", nascimento.strftime("%d/%m/%Y") if nascimento else "-")
    draw_pdf_label_value(pdf, right_x, info_y, "Idade", calc_age_on_attendance(nascimento, chamado.data_atendimento))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Telefone", getattr(contato, "telefone", "-"))
    draw_pdf_label_value(pdf, right_x, info_y, "Email", getattr(contato, "email", "-"))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Cidade", getattr(contato, "cidade", "-"))
    draw_pdf_label_value(pdf, right_x, info_y, "País", getattr(contato, "pais", "-"))
    info_y -= (line_h + block_gap)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Dados do Atendimento:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Área", chamado.area_atendimento or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Local", chamado.local or "-")
    info_y -= line_h
    geo_text = "-"
    if geolocalizacao_principal:
        geo_text = f"{geolocalizacao_principal.latitude}, {geolocalizacao_principal.longitude}"
    draw_pdf_label_value(pdf, info_x, info_y, "Coordenadas", geo_text)
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Tipo de Ocorrência", chamado.tipo_ocorrencia or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Responsável", chamado.responsavel_atendimento or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Atendimento Realizado", "Sim" if chamado.atendimentos else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Primeiros Socorros", chamado.primeiros_socorros or "-")
    info_y -= (line_h + block_gap)

    min_y = 72
    page_content_top = height - 120

    info_y = ensure_space(info_y, 110, "Saúde:")
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Saúde:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Doença Preexistente", "Sim" if chamado.doenca_preexistente else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Descrição da Doença", chamado.descricao_doenca or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Alergia", "Sim" if chamado.alergia else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Descrição da Alergia", chamado.descricao_alergia or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Plano de Saúde", "Sim" if chamado.plano_saude else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Nome do Plano", chamado.nome_plano_saude or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Número da Carteirinha", chamado.numero_carteirinha or "-")
    info_y -= (line_h + block_gap)

    info_y = ensure_space(info_y, 95, "Remoção e Encaminhamento:")
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Remoção e Encaminhamento:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Seguiu para o Passeio", "Sim" if chamado.seguiu_passeio else "Não")
    draw_pdf_label_value(pdf, right_x, info_y, "Houve Remoção", "Sim" if chamado.houve_remocao else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Transporte", chamado.transporte or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Encaminhamento", chamado.encaminhamento or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Hospital", chamado.hospital or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Médico Responsável", chamado.medico_responsavel or "-")
    draw_pdf_label_value(pdf, right_x, info_y, "CRM", chamado.crm or "-")
    info_y -= (line_h + block_gap)

    info_y = ensure_space(info_y, 95)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Acompanhante:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Possui Acompanhante", "Sim" if chamado.possui_acompanhante else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Nome", getattr(acompanhante, "nome", "-"))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Documento", getattr(acompanhante, "documento", "-"))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Sexo", getattr(acompanhante, "sexo", "-"))
    draw_pdf_label_value(pdf, right_x, info_y, "Grau de Parentesco", chamado.grau_parentesco or "-")
    info_y -= (line_h + block_gap)

    if testemunhas:
        info_y = ensure_space(info_y, 60 + (len(testemunhas) * 40), "Testemunhas:")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(info_x, info_y, "Testemunhas:")
        info_y -= 18
        for index, testemunha in enumerate(testemunhas, start=1):
            draw_pdf_label_value(pdf, info_x, info_y, f"Testemunha {index}", testemunha.nome or "-")
            info_y -= line_h
            draw_pdf_label_value(pdf, info_x, info_y, "Documento", testemunha.documento or "-")
            draw_pdf_label_value(pdf, right_x, info_y, "Nascimento", testemunha.data_nascimento.strftime("%d/%m/%Y") if testemunha.data_nascimento else "-")
            info_y -= line_h
            draw_pdf_label_value(pdf, info_x, info_y, "Telefone", getattr(getattr(testemunha, "contato", None), "telefone", "-"))
            info_y -= (line_h + 4)

    desc_title_y = info_y - 18
    if desc_title_y < min_y:
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        desc_title_y = page_content_top

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, desc_title_y, "Descrição do Atendimento")

    desc_lines = wrap_pdf_text_lines(chamado.descricao or "-", width - (info_x * 2))
    pdf.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            pdf.showPage()
            draw_page_chrome()
            pdf.setFillColorRGB(*dark_text)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(info_x, page_content_top, "Descrição do Atendimento (continuação)")
            pdf.setFont("Helvetica", 10)
            y = page_content_top - 18
        pdf.drawString(info_x, y, line)
        y -= 13

    assinatura_title_y = y - 12
    if assinatura_title_y < min_y + 110:
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        assinatura_title_y = page_content_top

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, assinatura_title_y, "Assinatura do Atendido")

    signature_box_y = assinatura_title_y - 96
    signature_box_w = 260
    signature_box_h = 80
    pdf.rect(info_x, signature_box_y, signature_box_w, signature_box_h, stroke=1, fill=0)

    if assinatura and assinatura.arquivo:
        try:
            signature_reader = ImageReader(io.BytesIO(bytes(assinatura.arquivo)))
            img_w, img_h = signature_reader.getSize()
            scale = min(signature_box_w / float(img_w), signature_box_h / float(img_h))
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = info_x + ((signature_box_w - draw_w) / 2)
            draw_y = signature_box_y + ((signature_box_h - draw_h) / 2)
            pdf.drawImage(signature_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
        except Exception:
            pdf.setFont("Helvetica", 9)
            pdf.drawString(info_x + 10, signature_box_y + 34, "Assinatura indisponível para visualização.")
    else:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(info_x + 10, signature_box_y + 34, "Assinatura não capturada.")

    hash_y = signature_box_y - 18
    if hash_y < min_y + 40:
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        hash_y = page_content_top

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(info_x, hash_y, "Hash da Assinatura:")
    hash_lines = wrap_pdf_text_lines(
        assinatura.hash_assinatura if assinatura and assinatura.hash_assinatura else "-",
        width - (info_x * 2),
        font_size=9,
    )
    pdf.setFont("Helvetica", 9)
    y = hash_y - 14
    for line in hash_lines:
        if y < min_y:
            pdf.showPage()
            draw_page_chrome()
            pdf.setFillColorRGB(*dark_text)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(info_x, page_content_top, "Hash da Assinatura (continuação)")
            pdf.setFont("Helvetica", 9)
            y = page_content_top - 14
        pdf.drawString(info_x + 4, y, line)
        y -= 12

    if fotos:
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, height - 140, f"Fotos do Atendimento: #{chamado.id}")

        grid_left = 48
        grid_top = height - 178
        card_w = 240
        card_h = 150
        photo_w = 220
        photo_h = 105
        col_gap = 24
        row_gap = 24
        cols = 2
        current_y = grid_top

        for index, foto in enumerate(fotos):
            col = index % cols
            if index > 0 and col == 0:
                current_y -= (card_h + row_gap)

            if current_y - card_h < min_y:
                pdf.showPage()
                draw_page_chrome()
                pdf.setFillColorRGB(*dark_text)
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawCentredString(width / 2, height - 140, f"Fotos do Atendimento: #{chamado.id}")
                current_y = grid_top

            card_x = grid_left + (col * (card_w + col_gap))
            card_y = current_y - card_h
            photo_x = card_x + 10
            photo_y = card_y + 34

            pdf.roundRect(card_x, card_y, card_w, card_h, 8, stroke=1, fill=0)

            try:
                foto_reader = ImageReader(io.BytesIO(bytes(foto.arquivo)))
                img_w, img_h = foto_reader.getSize()
                scale = min(photo_w / float(img_w), photo_h / float(img_h))
                draw_w = img_w * scale
                draw_h = img_h * scale
                draw_x = photo_x + ((photo_w - draw_w) / 2)
                draw_y = photo_y + ((photo_h - draw_h) / 2)
                pdf.drawImage(foto_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
            except Exception:
                pdf.setFont("Helvetica", 9)
                pdf.drawString(photo_x, photo_y + 42, "Foto indisponível para visualização.")

            pdf.setFont("Helvetica-Bold", 9)
            nome_foto = foto.nome_arquivo or f"Foto {index + 1}"
            nome_lines = wrap_pdf_text_lines(nome_foto, card_w - 20, font_size=8)
            label_y = card_y + 22
            for nome_line in nome_lines[:2]:
                pdf.drawString(card_x + 10, label_y, nome_line)
                label_y -= 9

            geo = foto.geolocalizacoes.order_by("criado_em").first()
            geo_text = "-"
            if geo:
                geo_text = f"{geo.latitude}, {geo.longitude}"

            geo_lines = wrap_pdf_text_lines(geo_text, card_w - 20, font_size=8)
            pdf.setFont("Helvetica", 8)
            line_y = card_y + 8
            for geo_line in geo_lines[:2]:
                pdf.drawString(card_x + 10, line_y, geo_line)
                line_y -= 9

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = f"controlebc_chamado_{chamado.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@require_GET
@login_required
def manejo_export_view_pdf(request, pk):
    manejo = get_object_or_404(
        Manejo.objects.prefetch_related("anexos", "fotos", "geolocalizacoes"),
        pk=pk,
    )

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    def display_user(user):
        if not user:
            return "Não registrado"
        return user.get_full_name() or user.username

    def format_datetime(value):
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else "-"

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    pdf = numbered_canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Relatório do Manejo #{manejo.id}")
    pdf.setAuthor(display_user(request.user))
    pdf.setSubject("Relatório de Manejo")

    dark_text = (0.15, 0.15, 0.15)

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=pdf,
            page_width=width,
            page_height=height,
            generated_by=display_user(request.user),
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle="Módulo BC - Fauna",
        )

    draw_page_chrome()
    pdf.setFillColorRGB(*dark_text)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(width / 2, height - 140, f"Relatório do Manejo: #{manejo.id}")

    info_block_w = 430
    info_x = (width - info_block_w) / 2
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)
    min_y = 72
    page_content_top = height - 120

    def ensure_space(current_y, needed=80, title=None):
        if current_y >= min_y + needed:
            return current_y
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        if title:
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(info_x, page_content_top, title)
            return page_content_top - 18
        return page_content_top

    draw_pdf_label_value(pdf, info_x, info_y, "Data/Hora", format_datetime(manejo.data_hora))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Status", "Realizado" if manejo.realizado_manejo else "Pendente")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Criado por", display_user(manejo.criado_por))
    draw_pdf_label_value(pdf, right_x, info_y, "Modificado por", display_user(manejo.modificado_por))
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Criado em", format_datetime(manejo.criado_em))
    draw_pdf_label_value(pdf, right_x, info_y, "Modificado em", format_datetime(manejo.modificado_em))
    info_y -= (line_h + block_gap)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Dados do Animal:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Classe", manejo.classe or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Nome Científico", manejo.nome_cientifico or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Nome Popular", manejo.nome_popular or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Estágio de Desenvolvimento", manejo.estagio_desenvolvimento or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Importância Médica", "Sim" if manejo.importancia_medica else "Não")
    info_y -= (line_h + block_gap)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Captura:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Área", manejo.area_captura or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Local", manejo.local_captura or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Descrição do Local", manejo.descricao_local or "-")
    info_y -= line_h
    geo_captura = manejo.geolocalizacao_captura
    draw_pdf_label_value(
        pdf,
        info_x,
        info_y,
        "Coordenadas",
        f"{geo_captura.latitude}, {geo_captura.longitude}" if geo_captura else "-",
    )
    info_y -= (line_h + block_gap)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Manejo:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Manejo Realizado", "Sim" if manejo.realizado_manejo else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Responsável", manejo.responsavel_manejo or "-")
    info_y -= (line_h + block_gap)

    info_y = ensure_space(info_y, 95)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Soltura:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Área de Soltura", manejo.area_soltura or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Local de Soltura", manejo.local_soltura or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Descrição do Local de Soltura", manejo.descricao_local_soltura or "-")
    info_y -= line_h
    geo_soltura = manejo.geolocalizacao_soltura
    draw_pdf_label_value(
        pdf,
        info_x,
        info_y,
        "Coordenadas",
        f"{geo_soltura.latitude}, {geo_soltura.longitude}" if geo_soltura else "-",
    )
    info_y -= (line_h + block_gap)

    info_y = ensure_space(info_y, 95)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, info_y, "Órgão Público:")
    info_y -= 18
    draw_pdf_label_value(pdf, info_x, info_y, "Acionado", "Sim" if manejo.acionado_orgao_publico else "Não")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Órgão Público", manejo.orgao_publico or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Número do Boletim", manejo.numero_boletim_ocorrencia or "-")
    info_y -= line_h
    draw_pdf_label_value(pdf, info_x, info_y, "Motivo do Acionamento", manejo.motivo_acionamento or "-")
    info_y -= (line_h + block_gap)

    desc_title_y = ensure_space(info_y - 6, 100)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, desc_title_y, "Observações")
    desc_lines = wrap_pdf_text_lines(manejo.observacoes or "-", width - (info_x * 2))
    pdf.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            pdf.showPage()
            draw_page_chrome()
            pdf.setFillColorRGB(*dark_text)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(info_x, page_content_top, "Observações (continuação)")
            pdf.setFont("Helvetica", 10)
            y = page_content_top - 18
        pdf.drawString(info_x, y, line)
        y -= 13

    anexos_y = y - 12
    if anexos_y < min_y:
        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        anexos_y = page_content_top

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(info_x, anexos_y, "Anexos")
    pdf.setFont("Helvetica", 9)
    anexos = list(manejo.anexos.all())
    fotos = list(manejo.fotos.all().order_by("criado_em", "id"))
    y = anexos_y - 14
    if anexos:
        for idx, anexo in enumerate(anexos, start=1):
            if y < min_y:
                pdf.showPage()
                draw_page_chrome()
                pdf.setFillColorRGB(*dark_text)
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(info_x, page_content_top, "Anexos (continuação)")
                pdf.setFont("Helvetica", 9)
                y = page_content_top - 14
            pdf.drawString(info_x + 4, y, f"{idx}. {anexo.nome_arquivo}")
            y -= 12
    else:
        pdf.drawString(info_x + 4, y, "Nenhum anexo.")

    def build_image_reader(foto):
        raw = io.BytesIO(bytes(foto.arquivo))
        try:
            return ImageReader(raw)
        except Exception:
            try:
                from PIL import Image as PILImage
                raw.seek(0)
                pil_img = PILImage.open(raw)
                if pil_img.mode not in ("RGB", "RGBA"):
                    pil_img = pil_img.convert("RGB")
                return ImageReader(pil_img)
            except Exception:
                return None

    def draw_photo_section(title, fotos_list):
        if not fotos_list:
            return

        pdf.showPage()
        draw_page_chrome()
        pdf.setFillColorRGB(*dark_text)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, height - 140, title)

        grid_left = 48
        grid_top = height - 178
        card_w = 240
        card_h = 150
        photo_w = 220
        photo_h = 105
        col_gap = 24
        row_gap = 24
        cols = 2
        current_y = grid_top

        for index, foto in enumerate(fotos_list):
            col = index % cols
            if index > 0 and col == 0:
                current_y -= (card_h + row_gap)

            if current_y - card_h < min_y:
                pdf.showPage()
                draw_page_chrome()
                pdf.setFillColorRGB(*dark_text)
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawCentredString(width / 2, height - 140, title)
                current_y = grid_top

            card_x = grid_left + (col * (card_w + col_gap))
            card_y = current_y - card_h
            photo_x = card_x + 10
            photo_y = card_y + 34

            pdf.roundRect(card_x, card_y, card_w, card_h, 8, stroke=1, fill=0)

            foto_reader = build_image_reader(foto)
            if foto_reader is not None:
                try:
                    img_w, img_h = foto_reader.getSize()
                    scale = min(photo_w / float(img_w), photo_h / float(img_h))
                    draw_w = img_w * scale
                    draw_h = img_h * scale
                    draw_x = photo_x + ((photo_w - draw_w) / 2)
                    draw_y = photo_y + ((photo_h - draw_h) / 2)
                    pdf.drawImage(foto_reader, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
                except Exception:
                    foto_reader = None

            if foto_reader is None:
                pdf.setFont("Helvetica", 9)
                pdf.drawString(photo_x, photo_y + 42, "Imagem não pôde ser renderizada.")

            pdf.setFont("Helvetica-Bold", 9)
            nome_foto = foto.nome_arquivo or f"Foto {index + 1}"
            nome_lines = wrap_pdf_text_lines(nome_foto, card_w - 20, font_size=8)
            label_y = card_y + 22
            for nome_line in nome_lines[:2]:
                pdf.drawString(card_x + 10, label_y, nome_line)
                label_y -= 9

            geo = foto.geolocalizacoes.order_by("criado_em").first()
            geo_text = "-"
            if geo:
                geo_text = f"{geo.latitude}, {geo.longitude}"

            geo_lines = wrap_pdf_text_lines(geo_text, card_w - 20, font_size=8)
            pdf.setFont("Helvetica", 8)
            line_y = card_y + 8
            for geo_line in geo_lines[:2]:
                pdf.drawString(card_x + 10, line_y, geo_line)
                line_y -= 9

    draw_photo_section(f"Fotos do Manejo: #{manejo.id}", fotos)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    filename = f"manejo_{manejo.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def chamados_manejo(request):
    q = (request.GET.get("q") or "").strip()
    page_number = request.GET.get("page") or 1
    selected_id = (request.GET.get("id") or "").strip()
    requested_tab = (request.GET.get("tab") or "").strip()
    export = (request.GET.get("export") or "").strip().lower()

    queryset = Manejo.objects.prefetch_related("anexos", "fotos", "geolocalizacoes").order_by("-data_hora", "-id")

    if q:
        queryset = queryset.filter(
            Q(classe__icontains=q)
            | Q(nome_popular__icontains=q)
            | Q(nome_cientifico__icontains=q)
            | Q(area_captura__icontains=q)
            | Q(local_captura__icontains=q)
            | Q(responsavel_manejo__icontains=q)
            | Q(observacoes__icontains=q)
        )

    export_filters = _build_manejo_export_filters(request)
    export_queryset = _apply_manejo_export_filters(queryset, export_filters)

    if export == "csv":
        return _export_manejo_csv(request, export_queryset)
    if export == "xlsx":
        return _export_manejo_excel(request, export_queryset)
    if export == "pdf":
        return _export_manejo_pdf(request, export_queryset)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(page_number)

    selected_manejo = None
    if selected_id.isdigit():
        selected_manejo = queryset.filter(pk=int(selected_id)).first()
    if selected_manejo is None:
        selected_manejo = page_obj.object_list[0] if page_obj.object_list else None

    export_manejos = list(export_queryset[:200])
    export_classes = list(
        queryset.exclude(classe__isnull=True)
        .exclude(classe__exact="")
        .values_list("classe", flat=True)
        .distinct()
        .order_by("classe")
    )
    export_areas = list(
        queryset.exclude(area_captura__isnull=True)
        .exclude(area_captura__exact="")
        .values_list("area_captura", flat=True)
        .distinct()
        .order_by("area_captura")
    )
    export_locais = list(
        queryset.exclude(local_captura__isnull=True)
        .exclude(local_captura__exact="")
        .values_list("local_captura", flat=True)
        .distinct()
        .order_by("local_captura")
    )

    return render(
        request,
        "controle_bc/manejo/chamados.html",
        {
            "q": q,
            "active_tab": _resolve_active_tab(requested_tab, selected_manejo),
            "page_obj": page_obj,
            "selected_manejo": selected_manejo,
            "export_filters": export_filters,
            "export_manejos": export_manejos,
            "export_classes": export_classes,
            "export_areas": export_areas,
            "export_locais": export_locais,
            "total_manejos": queryset.count(),
            "total_realizados": queryset.filter(realizado_manejo=True).count(),
            "total_pendentes": queryset.filter(realizado_manejo=False).count(),
            "total_export_manejos": export_queryset.count(),
        },
    )
