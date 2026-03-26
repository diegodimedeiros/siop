from django.contrib.auth import get_user_model
import json
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AcessoTerceiros, ControleAtendimento, Geolocalizacao, Manejo, Ocorrencia, Pessoa


class CriticalFlowSmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="senha-forte-123",
        )
        self.pessoa = Pessoa.objects.create(
            nome="Pessoa Teste",
            documento="12345678900",
        )
        self.ocorrencia = Ocorrencia.objects.create(
            tipo_pessoa="TERCEIRO",
            data_ocorrencia=timezone.now(),
            natureza="TESTE",
            tipo="TESTE",
            area="AREA 1",
            local="LOCAL 1",
            descricao="Ocorrencia de teste",
            criado_por=self.user,
            modificado_por=self.user,
        )
        self.acesso = AcessoTerceiros.objects.create(
            entrada=timezone.now(),
            pessoa=self.pessoa,
            empresa="Empresa Teste",
            p1="P1",
            descricao_acesso="Acesso de teste",
            criado_por=self.user,
            modificado_por=self.user,
        )

    def test_login_required_pages_redirect_when_anonymous(self):
        protected_urls = [
            reverse("home"),
            reverse("ocorrencia"),
            reverse("acesso_terceiro"),
            reverse("atendimento"),
            reverse("manejo"),
        ]

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def test_authenticated_pages_render_successfully(self):
        self.client.force_login(self.user)

        protected_urls = [
            reverse("home"),
            reverse("ocorrencia"),
            reverse("acesso_terceiro"),
            reverse("atendimento"),
            reverse("manejo"),
        ]

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_ajax_endpoints_return_structured_error_for_invalid_payload(self):
        self.client.force_login(self.user)

        ajax_endpoints = [
            reverse("ocorrencia_new"),
            reverse("acesso_terceiros_new"),
            reverse("manejo"),
            reverse("atendimento"),
        ]

        for url in ajax_endpoints:
            with self.subTest(url=url):
                response = self.client.post(
                    url,
                    data={},
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
                self.assertGreaterEqual(response.status_code, 400)
                self.assertLess(response.status_code, 500)

                payload = response.json()
                self.assertIn("ok", payload)
                self.assertFalse(payload["ok"])
                self.assertIn("error", payload)
                self.assertIn("message", payload["error"])

    def test_json_list_endpoints_return_success_contract(self):
        self.client.force_login(self.user)

        endpoints = [
            reverse("api_ocorrencia_list"),
            reverse("api_acesso_terceiros_list"),
        ]

        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url, {"limit": 10, "offset": 0})
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                self.assertTrue(payload["ok"])
                self.assertIn("data", payload)
                self.assertIn("message", payload)
                self.assertIn("meta", payload)
                self.assertIn("pagination", payload["meta"])

    def test_invalid_pagination_returns_standard_error(self):
        self.client.force_login(self.user)

        endpoints = [
            reverse("api_ocorrencia_list"),
            reverse("api_acesso_terceiros_list"),
        ]

        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url, {"limit": "abc", "offset": "xyz"})
                self.assertEqual(response.status_code, 422)

                payload = response.json()
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["error"]["code"], "invalid_pagination")

    def test_edit_endpoint_rejects_get_with_method_not_allowed(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("acesso_terceiros_edit", args=[self.acesso.id]))
        self.assertEqual(response.status_code, 405)

        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "method_not_allowed")

    def test_ocorrencia_create_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ocorrencia_new"),
            data={
                "data": "2026-03-22T14:30",
                "natureza": "OPERACIONAL",
                "tipo": "REGISTRO",
                "area": "AREA 2",
                "local": "LOCAL 2",
                "pessoa": "VISITANTE",
                "descricao": "Nova ocorrencia criada via teste.",
                "cftv": "on",
                "bombeiro_civil": "",
                "status": "",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("id", payload["data"])

        created = Ocorrencia.objects.get(pk=payload["data"]["id"])
        self.assertEqual(created.natureza, "OPERACIONAL")
        self.assertEqual(created.tipo, "REGISTRO")
        self.assertEqual(created.area, "AREA 2")
        self.assertEqual(created.local, "LOCAL 2")
        self.assertEqual(created.tipo_pessoa, "VISITANTE")
        self.assertEqual(created.criado_por, self.user)

    def test_ocorrencia_edit_returns_success_and_updates(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("ocorrencia_edit", args=[self.ocorrencia.id]),
            data={
                "descricao": "Descricao alterada via teste.",
                "cftv": "on",
                "bombeiro_civil": "on",
                "status": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], self.ocorrencia.id)

        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.descricao, "Descricao alterada via teste.")
        self.assertTrue(self.ocorrencia.cftv)
        self.assertTrue(self.ocorrencia.bombeiro_civil)
        self.assertTrue(self.ocorrencia.status)
        self.assertEqual(self.ocorrencia.modificado_por, self.user)

    def test_ocorrencia_edit_finalized_returns_conflict(self):
        self.client.force_login(self.user)
        self.ocorrencia.status = True
        self.ocorrencia.save(update_fields=["status"])

        response = self.client.post(
            reverse("ocorrencia_edit", args=[self.ocorrencia.id]),
            data={
                "descricao": "Nao deve editar",
                "cftv": "",
                "bombeiro_civil": "",
                "status": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "business_rule_violation")

    def test_acesso_create_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("acesso_terceiros_new"),
            data={
                "data": "2026-03-22T15:00",
                "nome": "Novo Visitante",
                "documento": "98765432100",
                "p1": "PORTARIA 1",
                "empresa": "Empresa Nova",
                "placa_veiculo": "ABC1234",
                "descricao": "Novo acesso criado via teste.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("id", payload["data"])

        created = AcessoTerceiros.objects.get(pk=payload["data"]["id"])
        self.assertEqual(created.nome, "Novo Visitante")
        self.assertEqual(created.documento, "98765432100")
        self.assertEqual(created.empresa, "Empresa Nova")
        self.assertEqual(created.p1, "PORTARIA 1")
        self.assertEqual(created.criado_por, self.user)

    def test_acesso_edit_returns_success_and_updates(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("acesso_terceiros_edit", args=[self.acesso.id]),
            data={
                "entrada": "2026-03-22T15:10",
                "saida": "2026-03-22T16:00",
                "nome": "Pessoa Editada",
                "documento": "12345678900",
                "p1": "PORTARIA 2",
                "empresa": "Empresa Editada",
                "placa_veiculo": "XYZ9876",
                "descricao": "Descricao alterada via teste.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["id"], self.acesso.id)

        self.acesso.refresh_from_db()
        self.assertEqual(self.acesso.nome, "Pessoa Editada")
        self.assertEqual(self.acesso.empresa, "Empresa Editada")
        self.assertEqual(self.acesso.p1, "PORTARIA 2")
        self.assertEqual(self.acesso.placa_veiculo, "XYZ9876")
        self.assertEqual(self.acesso.descricao, "Descricao alterada via teste.")
        self.assertEqual(self.acesso.modificado_por, self.user)

    def test_detail_endpoints_return_success_contract(self):
        self.client.force_login(self.user)

        endpoints = [
            (reverse("api_ocorrencia_view", args=[self.ocorrencia.id]), self.ocorrencia.id),
            (reverse("api_acesso_terceiros_view", args=[self.acesso.id]), self.acesso.id),
        ]

        for url, expected_id in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                self.assertTrue(payload["ok"])
                self.assertIn("data", payload)
                self.assertIn("message", payload)
                self.assertEqual(payload["data"]["id"], expected_id)

    def test_export_endpoints_require_filter(self):
        self.client.force_login(self.user)

        endpoints = [
            reverse("ocorrencia_export", args=["csv"]),
            reverse("acesso_terceiros_export", args=["csv"]),
        ]

        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("export_error=", response.url)

    def test_export_endpoints_return_file_when_filtered(self):
        self.client.force_login(self.user)

        test_cases = [
            (reverse("ocorrencia_export", args=["csv"]), {"area": "AREA 1"}, "ocorrencias_"),
            (reverse("acesso_terceiros_export", args=["csv"]), {"empresa": "Empresa Teste"}, "acessos_terceiros_"),
        ]

        for url, params, filename_hint in test_cases:
            with self.subTest(url=url):
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/csv", response["Content-Type"])
                self.assertIn(filename_hint, response["Content-Disposition"])

    def test_restful_api_create_endpoints_return_success(self):
        self.client.force_login(self.user)

        payloads = [
            (
                reverse("api_ocorrencia_list"),
                {
                    "data": "2026-03-22T17:00",
                    "natureza": "REST",
                    "tipo": "CREATE",
                    "area": "AREA API",
                    "local": "LOCAL API",
                    "pessoa": "TERCEIRO",
                    "descricao": "Criacao via endpoint canonico.",
                },
            ),
            (
                reverse("api_acesso_terceiros_list"),
                {
                    "data": "2026-03-22T17:10",
                    "nome": "API Create",
                    "documento": "55544433322",
                    "p1": "P1 API",
                    "empresa": "Empresa API",
                    "descricao": "Criacao via endpoint canonico.",
                },
            ),
        ]

        for url, payload in payloads:
            with self.subTest(url=url):
                response = self.client.post(
                    url,
                    data=json.dumps(payload),
                    content_type="application/json",
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
                self.assertEqual(response.status_code, 201)
                body = response.json()
                self.assertTrue(body["ok"])
                self.assertIn("id", body["data"])

    def test_restful_api_patch_endpoints_return_success(self):
        self.client.force_login(self.user)

        updates = [
            (
                reverse("api_ocorrencia_view", args=[self.ocorrencia.id]),
                {
                    "descricao": "Atualizacao via PATCH.",
                    "cftv": True,
                    "bombeiro_civil": False,
                    "status": False,
                },
            ),
            (
                reverse("api_acesso_terceiros_view", args=[self.acesso.id]),
                {
                    "entrada": "2026-03-22T18:00",
                    "saida": "2026-03-22T18:30",
                    "nome": "API Patch",
                    "documento": "12345678900",
                    "p1": "P1 PATCH",
                    "empresa": "Empresa Patch",
                    "descricao": "Atualizacao via PATCH.",
                },
            ),
        ]

        for url, payload in updates:
            with self.subTest(url=url):
                response = self.client.patch(
                    url,
                    data=json.dumps(payload),
                    content_type="application/json",
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertTrue(body["ok"])
                self.assertIn("id", body["data"])

    def test_restful_api_detail_rejects_delete(self):
        self.client.force_login(self.user)

        endpoints = [
            reverse("api_ocorrencia_view", args=[self.ocorrencia.id]),
            reverse("api_acesso_terceiros_view", args=[self.acesso.id]),
        ]

        for url in endpoints:
            with self.subTest(url=url):
                response = self.client.delete(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(response.status_code, 405)
                body = response.json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"], "method_not_allowed")

    def test_atendimento_create_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("atendimento"),
            data={
                "tipo_pessoa": "VISITANTE",
                "pessoa_nome": "Atendido Teste",
                "pessoa_documento": "11122233344",
                "pessoa_orgao_emissor": "SSP",
                "pessoa_sexo": "M",
                "pessoa_data_nascimento": "1990-05-10",
                "pessoa_nacionalidade": "Brasileira",
                "data_atendimento": "2026-03-22T19:00",
                "area_atendimento": "AREA 3",
                "local": "LOCAL 3",
                "tipo_ocorrencia": "MAL ESTAR",
                "responsavel_atendimento": "Equipe BC",
                "descricao": "Atendimento criado via teste.",
                "atendimentos": "on",
                "primeiros_socorros": "Curativo",
                "doenca_preexistente": "false",
                "alergia": "false",
                "plano_saude": "false",
                "contato_endereco": "Rua Teste",
                "contato_bairro": "Centro",
                "contato_cidade": "Penha",
                "contato_estado": "SC",
                "contato_pais": "Brasil",
                "contato_telefone": "47999990000",
                "contato_email": "atendido@example.com",
                "geo_latitude": "-26.7688890",
                "geo_longitude": "-48.6452780",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("id", payload["data"])

        created = ControleAtendimento.objects.select_related("pessoa", "contato").get(pk=payload["data"]["id"])
        self.assertEqual(created.tipo_pessoa, "VISITANTE")
        self.assertEqual(created.pessoa.nome, "Atendido Teste")
        self.assertEqual(created.pessoa.documento, "11122233344")
        self.assertEqual(created.area_atendimento, "AREA 3")
        self.assertEqual(created.local, "LOCAL 3")
        self.assertEqual(created.tipo_ocorrencia, "MAL ESTAR")
        self.assertEqual(created.responsavel_atendimento, "Equipe BC")
        self.assertTrue(created.atendimentos)
        self.assertEqual(created.primeiros_socorros, "Curativo")
        self.assertIsNotNone(created.contato)
        self.assertEqual(created.contato.bairro, "Centro")
        self.assertEqual(created.criado_por, self.user)
        self.assertTrue(
            Geolocalizacao.objects.filter(object_id=created.id).exists()
        )

    def test_atendimento_create_returns_validation_error_when_required_fields_missing(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("atendimento"),
            data={
                "tipo_pessoa": "VISITANTE",
                "pessoa_nome": "Sem Dados",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "validation_error")
        self.assertIn("pessoa_documento", payload["error"]["details"])
        self.assertIn("area_atendimento", payload["error"]["details"])
        self.assertIn("descricao", payload["error"]["details"])

    def test_manejo_create_returns_success_and_persists(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("manejo"),
            data={
                "data_hora": "2026-03-22T20:00",
                "classe": "REPTIL",
                "nome_popular": "Jiboia",
                "area_captura": "AREA 4",
                "local_captura": "LOCAL 4",
                "descricao_local": "Próximo à trilha",
                "realizado_manejo": "on",
                "responsavel_manejo": "Equipe Fauna",
                "descricao_local_soltura": "",
                "motivo_acionamento": "Animal em área de circulação",
                "observacoes": "Manejo criado via teste.",
                "latitude_captura": "-26.768889",
                "longitude_captura": "-48.645278",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("id", payload["data"])

        created = Manejo.objects.get(pk=payload["data"]["id"])
        self.assertEqual(created.classe, "REPTIL")
        self.assertEqual(created.nome_popular, "Jiboia")
        self.assertEqual(created.area_captura, "AREA 4")
        self.assertEqual(created.local_captura, "LOCAL 4")
        self.assertTrue(created.realizado_manejo)
        self.assertEqual(created.responsavel_manejo, "Equipe Fauna")
        self.assertEqual(created.criado_por, self.user)
        self.assertTrue(Geolocalizacao.objects.filter(object_id=created.id, tipo="captura").exists())

    def test_manejo_create_requires_responsavel_when_realizado(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("manejo"),
            data={
                "data_hora": "2026-03-22T20:10",
                "classe": "MAMIFERO",
                "area_captura": "AREA 5",
                "local_captura": "LOCAL 5",
                "descricao_local": "Base da trilha",
                "realizado_manejo": "on",
                "motivo_acionamento": "Animal em risco",
                "observacoes": "Sem responsável.",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "validation_error")
        self.assertIn("responsavel_manejo", payload["error"]["details"])
