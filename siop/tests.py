from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AcessoTerceiros, Ocorrencia, Pessoa


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
