from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from siop import views

urlpatterns = [
    path("admin/", admin.site.urls),   
    path("login/", auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.home_view, name="home"),    

    # Catálogo
    path("api/catalogos/naturezas/", views.catalogo_naturezas),
    path("api/catalogos/naturezas/tipos/", views.catalogo_tipos_por_natureza),
    path("api/catalogos/areas/", views.catalogo_areas),
    path("api/catalogos/areas/locais/", views.catalogo_locais_por_area),
    path("api/catalogos/fauna/especies/", views.catalogo_especies_por_classe),
    path("api/catalogos/p1/", views.catalogo_p1),
    path("api/catalogos/tipos-pessoa/", views.catalogo_tipos_pessoa),
    path("api/catalogos/sexos/", views.catalogo_sexos),
    path("api/catalogos/tipos-ocorrencia/", views.catalogo_tipos_ocorrencia),
    path("api/catalogos/transportes/", views.catalogo_transportes),
    path("api/catalogos/encaminhamentos/", views.catalogo_encaminhamentos),
    path("api/catalogos/primeiros-socorros/", views.catalogo_primeiros_socorros),
    path("api/ocorrencias/", views.api_ocorrencias, name="api_ocorrencia_list"),
    path("api/ocorrencias/<int:pk>/", views.api_ocorrencia_detail, name="api_ocorrencia_view"),
    path("api/acessos-terceiros/", views.api_acessos_terceiros, name="api_acesso_terceiros_list"),
    path("api/acessos-terceiros/<int:pk>/", views.api_acesso_terceiros_detail, name="api_acesso_terceiros_view"),

    # Ocorrências
    path("ocorrencias/", views.ocorrencia, name="ocorrencia"),
    path("ocorrencias/list/", views.ocorrencia_list, name="ocorrencia_list"),
    path("ocorrencias/list/partial/", views.ocorrencia_list_partial, name="ocorrencia_list_partial"),
    path("ocorrencias/export/<str:formato>/", views.ocorrencia_export, name="ocorrencia_export"),
    path("ocorrencias/<int:pk>/export/pdf-view/", views.ocorrencia_export_view_pdf, name="ocorrencia_export_view_pdf"),
    path("ocorrencias/new/", views.ocorrencia_new, name="ocorrencia_new"),
    path("ocorrencias/<int:pk>/edit/", views.ocorrencia_edit, name="ocorrencia_edit"),
    path("ocorrencias/<int:pk>/json/", views.ocorrencia_view, name="ocorrencia_view"),

    # Acesso de Terceiros
    path("acesso-terceiros/", views.acesso_terceiro, name="acesso_terceiro"),
    path("acesso-terceiros/list/", views.acesso_terceiros_list, name="acesso_terceiros_list"),
    path("acesso-terceiros/list/partial/", views.acesso_terceiros_list_partial, name="acesso_terceiros_list_partial"),
    path("acesso-terceiros/export/<str:formato>/", views.acesso_terceiros_export, name="acesso_terceiros_export"),
    path("acesso-terceiros/<int:pk>/export/pdf-view/", views.acesso_terceiros_export_view_pdf, name="acesso_terceiros_export_view_pdf"),
    path("acesso-terceiros/new/", views.acesso_terceiros_new, name="acesso_terceiros_new"),
    path("acesso-terceiros/<int:pk>/edit/", views.acesso_terceiros_edit, name="acesso_terceiros_edit"),
    path("acesso-terceiros/<int:pk>/json/", views.acesso_terceiros_view, name="acesso_terceiros_view"),

    # Controle BC
    path("controlebc/", views.controle_bc, name="controle_bc"),
    path("controlebc/chamados/", views.chamados, name="chamados"),
    path("controlebc/chamados/<int:pk>/export/pdf-view/", views.chamado_export_view_pdf, name="chamado_export_view_pdf"),
    path("controlebc/chamados-manejo/", views.chamados_manejo, name="chamados_manejo"),
    path("controlebc/chamados-manejo/<int:pk>/export/pdf-view/", views.manejo_export_view_pdf, name="manejo_export_view_pdf"),
    path("controlebc/atendimento/", views.atendimento, name="atendimento"),
    path("controlebc/manejo/", views.manejo, name="manejo"),
    path("controlebc/flora/", views.flora, name="flora"),

    # Anexos
    path("anexos/<int:pk>/download/", views.anexo_download, name="anexo_download"),
]
