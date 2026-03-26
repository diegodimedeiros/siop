from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from core.api import api_error

from .models import Ocorrencia
from .view.vw_acesso_terceiros import (
    acesso_terceiro,
    acesso_terceiros_edit,
    acesso_terceiros_export,
    acesso_terceiros_export_view_pdf,
    acesso_terceiros_list,
    acesso_terceiros_list_partial,
    acesso_terceiros_new,
    acesso_terceiros_view,
)
from .view.vw_controle_bc import (
    atendimento,
    chamado_export_view_pdf,
    chamados,
    chamados_manejo,
    controle_bc,
    flora,
    catalogo_especies_por_classe,
    manejo,
    manejo_export_view_pdf,
)
from .view.vw_ocorrencia import (
    anexo_download,
    catalogo_areas,
    catalogo_encaminhamentos,
    catalogo_locais_por_area,
    catalogo_naturezas,
    catalogo_p1,
    catalogo_primeiros_socorros,
    catalogo_sexos,
    catalogo_tipos_ocorrencia,
    catalogo_tipos_pessoa,
    catalogo_tipos_por_natureza,
    catalogo_transportes,
    ocorrencia,
    ocorrencia_edit,
    ocorrencia_export,
    ocorrencia_export_view_pdf,
    ocorrencia_list,
    ocorrencia_list_partial,
    ocorrencia_new,
    ocorrencia_view,
)


@login_required
def home_view(request):
    queryset = Ocorrencia.objects.all()
    total_ocorrencias = queryset.count()
    total_abertas = queryset.filter(status=False).count()
    total_finalizadas = queryset.filter(status=True).count()
    total_bombeiro_civil = queryset.filter(bombeiro_civil=True).count()
    taxa_finalizacao = round((total_finalizadas / total_ocorrencias) * 100, 1) if total_ocorrencias else 0
    taxa_bombeiro_civil = round((total_bombeiro_civil / total_ocorrencias) * 100, 1) if total_ocorrencias else 0

    top_areas = list(
        queryset.values("area")
        .annotate(total=Count("id"))
        .order_by("-total", "area")[:5]
    )
    top_naturezas = list(
        queryset.values("natureza")
        .annotate(total=Count("id"))
        .order_by("-total", "natureza")[:5]
    )
    recentes = queryset.order_by("-data_ocorrencia")[:6]

    return render(
        request,
        "home/home.html",
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


@login_required
def api_ocorrencias(request):
    if request.method == "GET":
        return ocorrencia_list(request)
    if request.method == "POST":
        return ocorrencia_new(request)
    return api_error(
        code="method_not_allowed",
        message="Método não permitido.",
        status=405,
    )


@login_required
def api_ocorrencia_detail(request, pk):
    if request.method == "GET":
        return ocorrencia_view(request, pk)
    if request.method in {"PATCH", "POST"}:
        return ocorrencia_edit(request, pk)
    return api_error(
        code="method_not_allowed",
        message="Método não permitido.",
        status=405,
    )


@login_required
def api_acessos_terceiros(request):
    if request.method == "GET":
        return acesso_terceiros_list(request)
    if request.method == "POST":
        return acesso_terceiros_new(request)
    return api_error(
        code="method_not_allowed",
        message="Método não permitido.",
        status=405,
    )


@login_required
def api_acesso_terceiros_detail(request, pk):
    if request.method == "GET":
        return acesso_terceiros_view(request, pk)
    if request.method in {"PATCH", "POST"}:
        return acesso_terceiros_edit(request, pk)
    return api_error(
        code="method_not_allowed",
        message="Método não permitido.",
        status=405,
    )
