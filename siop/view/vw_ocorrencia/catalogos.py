from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from core.api import api_success
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
