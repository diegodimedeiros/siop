import hashlib

from decimal import Decimal
from django.db import models
from django.db.models import F, Q
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from core.utils.validators import validation_size

User = get_user_model()


class BaseModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    modificado_em = models.DateTimeField(auto_now=True, verbose_name="Modificado em")
    criado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_criados",
        verbose_name="Criado por",
    )
    modificado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_modificados",
        verbose_name="Modificado por",
    )

    class Meta:
        abstract = True


class GenericRelationModel(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="siop_%(class)s_set",
    )
    object_id = models.PositiveBigIntegerField()
    objeto = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["content_type", "object_id"])
        ]


class BaseArquivo(BaseModel, GenericRelationModel):
    nome_arquivo = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    tamanho = models.PositiveIntegerField(default=0)
    arquivo = models.BinaryField(validators=[validation_size], verbose_name="Arquivo")
    hash_arquivo = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    hash_arquivo_atual = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def gerar_hash(self, conteudo):
        return hashlib.sha256(conteudo).hexdigest()

    def save(self, *args, **kwargs):
        if self.arquivo:
            conteudo = bytes(self.arquivo)
            self.tamanho = len(conteudo)
            self.hash_arquivo_atual = self.gerar_hash(conteudo)

            if not self.hash_arquivo:
                self.hash_arquivo = self.hash_arquivo_atual

        return super().save(*args, **kwargs)


class Geolocalizacao(BaseModel, GenericRelationModel):
    tipo = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Tipo da Geolocalização",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    hash_geolocalizacao = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        unique=True,
    )

    class Meta:
        verbose_name = "Geolocalização"
        verbose_name_plural = "Geolocalizações"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "tipo", "latitude", "longitude"],
                name="unique_geolocalizacao_por_objeto",
            ),
            models.UniqueConstraint(
                fields=["content_type", "object_id", "tipo"],
                condition=Q(tipo__isnull=False),
                name="unique_geolocalizacao_tipo_por_objeto",
            ),
        ]

    def __str__(self):
        return f"Lat: {self.latitude}, Lon: {self.longitude}"

    def clean(self):
        super().clean()

        errors = {}

        if self.latitude is None:
            errors["latitude"] = "Latitude é obrigatória."
        elif not (Decimal("-90") <= self.latitude <= Decimal("90")):
            errors["latitude"] = "Latitude inválida. Deve estar entre -90 e 90."

        if self.longitude is None:
            errors["longitude"] = "Longitude é obrigatória."
        elif not (Decimal("-180") <= self.longitude <= Decimal("180")):
            errors["longitude"] = "Longitude inválida. Deve estar entre -180 e 180."

        if errors:
            raise ValidationError(errors)

    def gerar_hash_geolocalizacao(self):
        payload = f"{self.content_type_id}|{self.object_id}|{self.tipo or ''}|{self.latitude}|{self.longitude}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.full_clean()
        self.hash_geolocalizacao = self.gerar_hash_geolocalizacao()
        return super().save(*args, **kwargs)


class Anexo(BaseArquivo):
    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_arquivo


class Foto(BaseArquivo):
    TIPO_CAPTURA = "captura"
    TIPO_SOLTURA = "soltura"
    TIPO_CHOICES = (
        (TIPO_CAPTURA, "Captura"),
        (TIPO_SOLTURA, "Soltura"),
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_CAPTURA,
        db_index=True,
        verbose_name="Tipo da Foto",
    )
    geolocalizacoes = GenericRelation(Geolocalizacao)

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_arquivo


class Assinatura(BaseArquivo):
    hash_assinatura = models.CharField(
        max_length=64,
        verbose_name="Hash da Assinatura",
        null=True,
        blank=True,
        db_index=True,
        unique=True,
    )
    geolocalizacoes = GenericRelation(Geolocalizacao)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="siop_assinatura_unique_objeto",
            )
        ]

    def __str__(self):
        return self.nome_arquivo

    def clean(self):
        super().clean()

        errors = {}

        if not self.arquivo:
            errors["arquivo"] = "O arquivo da assinatura é obrigatório."

        if not self.content_type_id:
            errors["content_type"] = "O tipo do objeto relacionado é obrigatório."

        if not self.object_id:
            errors["object_id"] = "O objeto relacionado é obrigatório."

        if errors:
            raise ValidationError(errors)

    def gerar_hash_assinatura(self, conteudo: bytes) -> str:
        return hashlib.sha256(conteudo).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"__all__": "Assinatura não pode ser alterada após criada."}
            )

        self.full_clean()
        conteudo = bytes(self.arquivo)
        self.tamanho = len(conteudo)
        self.hash_arquivo_atual = self.gerar_hash(conteudo)
        self.hash_arquivo = self.hash_arquivo_atual
        self.hash_assinatura = self.gerar_hash_assinatura(conteudo)
        return super().save(*args, **kwargs)


class Pessoa(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome Completo", blank=False, null=False)
    documento = models.CharField(max_length=50, verbose_name="Documento", blank=False, null=False)
    orgao_emissor = models.CharField(max_length=50, verbose_name="Órgão Emissor", blank=True, null=True)
    sexo = models.CharField(max_length=10, verbose_name="Sexo", blank=True, null=True)
    data_nascimento = models.DateField(verbose_name="Data de Nascimento", blank=True, null=True)
    nacionalidade = models.CharField(max_length=50, verbose_name="Nacionalidade", blank=True, null=True)

    class Meta:
        verbose_name = "Pessoa"
        verbose_name_plural = "Pessoas"

    def __str__(self):
        return f"{self.nome} ({self.documento})"


class Contato(models.Model):
    telefone = models.CharField(max_length=20, verbose_name="Telefone", blank=True, null=True)
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    endereco = models.CharField(max_length=255, verbose_name="Endereço", blank=True, null=True)
    bairro = models.CharField(max_length=100, verbose_name="Bairro", blank=True, null=True)
    cidade = models.CharField(max_length=100, verbose_name="Cidade", blank=True, null=True)
    estado = models.CharField(max_length=100, verbose_name="Estado", blank=True, null=True)
    provincia = models.CharField(max_length=100, verbose_name="Província", blank=True, null=True)
    pais = models.CharField(max_length=100, verbose_name="País", blank=True, null=True)

    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"

    def __str__(self):
        return self.email or self.telefone or "Contato"


class Testemunha(Pessoa):
    contato = models.OneToOneField(Contato, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Testemunha"
        verbose_name_plural = "Testemunhas"

    def __str__(self):
        return self.nome
    

class ControleAtendimento(BaseModel):
    tipo_pessoa = models.CharField(
        max_length=50,
        verbose_name="Tipo de Pessoa",
        null=False,
        blank=False,
        db_index=True,
    )
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="controles_atendimento")
    contato = models.ForeignKey(
        Contato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="controles_atendimento",
    )
    area_atendimento = models.CharField(
        max_length=50,
        verbose_name="Área de Atendimento",
        null=False,
        blank=False,
        db_index=True,
    )
    local = models.CharField(max_length=50, verbose_name="Local de Atendimento", null=False, blank=False, db_index=True)
    data_atendimento = models.DateTimeField(verbose_name="Data e Hora do Atendimento", db_index=True)
    tipo_ocorrencia = models.CharField(max_length=50, verbose_name="Tipo de Ocorrência", null=False, blank=False, db_index=True)
    possui_acompanhante = models.BooleanField(verbose_name="Acompanhante?", default=False)
    acompanhante_pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atendimentos_como_acompanhante",
        verbose_name="Nome do Acompanhante",
    )
    grau_parentesco = models.CharField(max_length=100, verbose_name="Grau de Parentesco", null=True, blank=True)
    doenca_preexistente = models.BooleanField(verbose_name="Doença Preexistente?", default=False)
    descricao_doenca = models.TextField(verbose_name="Descrição da Doença", null=True, blank=True)
    alergia = models.BooleanField(verbose_name="Alergia?", default=False)
    descricao_alergia = models.TextField(verbose_name="Descrição da Alergia", null=True, blank=True)
    plano_saude = models.BooleanField(verbose_name="Possui Plano de Saúde?", default=False)
    nome_plano_saude = models.CharField(max_length=255, verbose_name="Nome do Plano de Saúde", null=True, blank=True)
    numero_carteirinha = models.CharField(max_length=100, verbose_name="Número da Carteirinha", null=True, blank=True)
    primeiros_socorros = models.CharField(max_length=50, verbose_name="Primeiros Socorros", null=True, blank=True)
    atendimentos = models.BooleanField(verbose_name="Atendimento Realizado?", default=False, db_index=True)
    responsavel_atendimento = models.CharField(max_length=255, verbose_name="Responsável pelo Atendimento", null=True, blank=True)
    seguiu_passeio = models.BooleanField(verbose_name="Seguiu para o Passeio?", default=False)
    houve_remocao = models.BooleanField(verbose_name="Remoção?", default=False)
    transporte = models.CharField(max_length=100, verbose_name="Transporte Utilizado", null=True, blank=True)
    encaminhamento = models.CharField(max_length=255, verbose_name="Encaminhamento", null=True, blank=True)
    hospital = models.CharField(max_length=255, verbose_name="Hospital", null=True, blank=True)
    medico_responsavel = models.CharField(max_length=255, verbose_name="Médico Responsável", null=True, blank=True)
    crm = models.CharField(max_length=100, verbose_name="CRM do Médico", null=True, blank=True)
    descricao = models.TextField(verbose_name="Descrição do Atendimento", blank=False, null=False)
    testemunhas = models.ManyToManyField(
        Testemunha,
        blank=True,
        related_name="atendimentos_como_testemunha",
        verbose_name="Testemunhas",
    )
    anexos = GenericRelation(Anexo)
    fotos = GenericRelation(Foto)
    geolocalizacoes = GenericRelation(Geolocalizacao)
    assinaturas = GenericRelation(Assinatura)
    hash_atendimento = models.CharField(max_length=64, verbose_name="Hash do Atendimento", null=True, blank=True, db_index=True, unique=True)

    class Meta:
        verbose_name = "Controle de Atendimento"
        verbose_name_plural = "Controles de Atendimento"
        ordering = ["-data_atendimento", "-criado_em"]
        indexes = [
            models.Index(fields=["pessoa", "-data_atendimento"]),
            models.Index(fields=["tipo_ocorrencia", "-data_atendimento"]),
            models.Index(fields=["area_atendimento", "-data_atendimento"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        self.tipo_pessoa = (self.tipo_pessoa or "").strip()
        self.area_atendimento = (self.area_atendimento or "").strip()
        self.local = (self.local or "").strip()
        self.tipo_ocorrencia = (self.tipo_ocorrencia or "").strip()
        self.grau_parentesco = (self.grau_parentesco or "").strip() or None
        self.descricao_doenca = (self.descricao_doenca or "").strip() or None
        self.descricao_alergia = (self.descricao_alergia or "").strip() or None
        self.nome_plano_saude = (self.nome_plano_saude or "").strip() or None
        self.numero_carteirinha = (self.numero_carteirinha or "").strip() or None
        self.primeiros_socorros = (self.primeiros_socorros or "").strip() or None
        self.responsavel_atendimento = (self.responsavel_atendimento or "").strip() or None
        self.transporte = (self.transporte or "").strip() or None
        self.encaminhamento = (self.encaminhamento or "").strip() or None
        self.hospital = (self.hospital or "").strip() or None
        self.medico_responsavel = (self.medico_responsavel or "").strip() or None
        self.crm = (self.crm or "").strip() or None
        self.descricao = (self.descricao or "").strip()
        if not self.tipo_pessoa: errors["tipo_pessoa"] = "O tipo de pessoa é obrigatório."
        if not self.pessoa_id: errors["pessoa"] = "A pessoa é obrigatória."
        if not self.area_atendimento: errors["area_atendimento"] = "A área de atendimento é obrigatória."
        if not self.local: errors["local"] = "O local de atendimento é obrigatório."
        if not self.data_atendimento: errors["data_atendimento"] = "A data e hora do atendimento são obrigatórias."
        if not self.tipo_ocorrencia: errors["tipo_ocorrencia"] = "O tipo de ocorrência é obrigatório."
        if not self.descricao: errors["descricao"] = "A descrição do atendimento é obrigatória."
        if self.possui_acompanhante and not self.acompanhante_pessoa_id: errors["acompanhante_pessoa"] = "Informe o acompanhante."
        if self.houve_remocao and not self.transporte: errors["transporte"] = "Informe o transporte quando houver remoção."
        if self.doenca_preexistente and not self.descricao_doenca: errors["descricao_doenca"] = "Informe a descrição da doença preexistente."
        if self.alergia and not self.descricao_alergia: errors["descricao_alergia"] = "Informe a descrição da alergia."
        if self.plano_saude and not self.nome_plano_saude: errors["nome_plano_saude"] = "Informe o nome do plano de saúde."
        if errors: raise ValidationError(errors)

    def _build_hash_atendimento(self):
        documento = self.pessoa.documento if self.pessoa_id else ""
        data_atendimento = self.data_atendimento.isoformat() if self.data_atendimento else ""
        payload = f"{self.pk}|{documento}|{data_atendimento}|{self.atendimentos}|{self.descricao}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        novo_hash = self._build_hash_atendimento()
        if self.hash_atendimento != novo_hash:
            self.hash_atendimento = novo_hash
            super().save(update_fields=["hash_atendimento"])

    def __str__(self):
        when = self.data_atendimento.strftime("%d/%m/%Y %H:%M") if self.data_atendimento else "sem data"
        pessoa_nome = self.pessoa.nome if self.pessoa_id else "sem pessoa"
        pessoa_documento = self.pessoa.documento if self.pessoa_id else "sem documento"
        return f"{pessoa_nome} ({pessoa_documento}) - {when}"


class Ocorrencia(BaseModel):
    tipo_pessoa = models.CharField(max_length=20, verbose_name="Tipo Pessoa", blank=False, null=False, db_index=True)
    data_ocorrencia = models.DateTimeField(verbose_name="Data e Hora da Ocorrência", db_index=True)
    natureza = models.CharField(max_length=50, verbose_name="Natureza", null=False, blank=False, db_index=True)
    tipo = models.CharField(max_length=50, verbose_name="Tipo", null=False, blank=False, db_index=True)
    area = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    local = models.CharField(max_length=50, verbose_name="Local", null=False, blank=False, db_index=True)
    cftv = models.BooleanField(verbose_name="Possui imagens CFTV?", default=False)
    bombeiro_civil = models.BooleanField(verbose_name="Acionou BC?", default=False, db_index=True)
    anexos = GenericRelation(Anexo)
    status = models.BooleanField(verbose_name="Ocorrência Finalizada?", default=False, db_index=True)
    descricao = models.TextField(verbose_name="Descrição da Ocorrência", blank=True, null=True)

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ["-data_ocorrencia"]

    def clean(self):
        super().clean()
        errors = {}
        self.tipo_pessoa = (self.tipo_pessoa or "").strip()
        self.natureza = (self.natureza or "").strip()
        self.tipo = (self.tipo or "").strip()
        self.area = (self.area or "").strip()
        self.local = (self.local or "").strip()
        self.descricao = (self.descricao or "").strip() or None

        if not self.tipo_pessoa:
            errors["tipo_pessoa"] = "O tipo de pessoa é obrigatório."
        if not self.data_ocorrencia:
            errors["data_ocorrencia"] = "A data e hora da ocorrência são obrigatórias."
        if not self.natureza:
            errors["natureza"] = "A natureza é obrigatória."
        if not self.tipo:
            errors["tipo"] = "O tipo é obrigatório."
        if not self.area:
            errors["area"] = "A área é obrigatória."
        if not self.local:
            errors["local"] = "O local é obrigatório."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.natureza} - {self.tipo} - {self.local} ({self.data_ocorrencia.strftime('%d/%m/%Y %H:%M')})"


class AcessoTerceiros(BaseModel):
    entrada = models.DateTimeField(verbose_name="Data e Hora da Entrada", db_index=True, null=False, blank=False)
    saida = models.DateTimeField(verbose_name="Data e Hora da Saída", db_index=True, null=True, blank=True)
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="acessos_terceiros")
    empresa = models.CharField(max_length=255, verbose_name="Empresa", null=True, blank=True)
    placa_veiculo = models.CharField(max_length=20, verbose_name="Placa do Veículo", null=True, blank=True)
    p1 = models.CharField(max_length=50, verbose_name="P1", db_index=True)
    anexos = GenericRelation(Anexo)
    descricao_acesso = models.TextField(verbose_name="Descrição de Acesso Terceiros", blank=True)

    class Meta:
        verbose_name = "Acesso de Terceiros"
        verbose_name_plural = "Acessos de Terceiros"
        ordering = ["-entrada", "-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=Q(saida__isnull=True) | Q(saida__gte=F("entrada")),
                name="acesso_terceiros_saida_maior_ou_igual_entrada",
            )
        ]
        indexes = [
            models.Index(fields=["pessoa", "-entrada"]),
            models.Index(fields=["p1", "-entrada"]),
        ]

    def clean(self):
        super().clean()

        errors = {}

        self.p1 = (self.p1 or "").strip()
        self.empresa = (self.empresa or "").strip() or None
        self.placa_veiculo = (self.placa_veiculo or "").strip().upper() or None
        self.descricao_acesso = (self.descricao_acesso or "").strip()

        if not self.pessoa_id:
            errors["pessoa"] = "A pessoa é obrigatória."

        if not self.entrada:
            errors["entrada"] = "A data/hora de entrada é obrigatória."

        if not self.p1:
            errors["p1"] = "O campo P1 é obrigatório."

        if self.entrada and self.saida and self.saida < self.entrada:
            errors["saida"] = "A data/hora de saída não pode ser anterior à entrada."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def nome(self):
        return self.pessoa.nome if self.pessoa_id else ""

    @property
    def documento(self):
        return self.pessoa.documento if self.pessoa_id else ""

    @property
    def descricao(self):
        return self.descricao_acesso

    def __str__(self):
        when = self.entrada.strftime("%d/%m/%Y %H:%M") if self.entrada else "sem entrada"
        pessoa_nome = self.pessoa.nome if self.pessoa_id else "sem pessoa"
        pessoa_documento = self.pessoa.documento if self.pessoa_id else "sem documento"
        return f"{pessoa_nome} ({pessoa_documento}) - {when}"

class Manejo(BaseModel):
    data_hora = models.DateTimeField(verbose_name="Data e Hora do Manejo", null=False, blank=False, db_index=True)
    
    classe = models.CharField(max_length=25, verbose_name="Classe", null=False, blank=False, db_index=True)
    nome_cientifico = models.CharField(max_length=255, verbose_name="Nome Científico", null=True, blank=True)
    nome_popular = models.CharField(max_length=255, verbose_name="Nome Popular", null=True, blank=True)
    estagio_desenvolvimento = models.CharField(max_length=50, verbose_name="Estágio de Desenvolvimento", null=True, blank=True)
    
    area_captura = models.CharField(max_length=50, verbose_name="Área", null=False, blank=False, db_index=True)
    local_captura = models.CharField(max_length=50, verbose_name="Local", null=False, blank=False, db_index=True)
    descricao_local = models.TextField(verbose_name="Descrição do Local", blank=True)

    importancia_medica = models.BooleanField(verbose_name="Importância Médica?", default=False)
    realizado_manejo = models.BooleanField(verbose_name="Manejo Realizado?", default=False, db_index=True)
    responsavel_manejo = models.CharField(max_length=255, verbose_name="Responsável pelo Manejo", null=True, blank=True)
    
    area_soltura = models.CharField(max_length=50, verbose_name="Área de Soltura", null=True, blank=True, db_index=True)
    local_soltura = models.CharField(max_length=50, verbose_name="Local de Soltura", null=True, blank=True, db_index=True)
    descricao_local_soltura = models.TextField(verbose_name="Descrição do Local de Soltura", blank=True)

    acionado_orgao_publico = models.BooleanField(verbose_name="Acionou Órgão Público?", default=False)
    orgao_publico = models.CharField(max_length=255, verbose_name="Órgão Público", null=True, blank=True)
    numero_boletim_ocorrencia = models.CharField(max_length=100, verbose_name="Número do Boletim de Ocorrência", null=True, blank=True)
    motivo_acionamento = models.TextField(verbose_name="Motivo do Acionamento", blank=True)

    observacoes = models.TextField(verbose_name="Observações", blank=True)

    geolocalizacoes = GenericRelation(Geolocalizacao)
    fotos = GenericRelation(Foto)        
    anexos = GenericRelation(Anexo)

    class Meta:
        verbose_name = "Manejo"
        verbose_name_plural = "Manejos"
        ordering = ["-data_hora", "-criado_em"]
        indexes = [
            models.Index(fields=["classe", "-data_hora"]),
            models.Index(fields=["area_captura", "-data_hora"]),
            models.Index(fields=["local_captura", "-data_hora"]),
        ]

    @property
    def geolocalizacao_captura(self):
        return self.geolocalizacoes.filter(tipo="captura").first()

    @property
    def geolocalizacao_soltura(self):
        return self.geolocalizacoes.filter(tipo="soltura").first()

    @property
    def fotos_captura(self):
        return self.fotos.filter(tipo=Foto.TIPO_CAPTURA)

    @property
    def fotos_soltura(self):
        return self.fotos.filter(tipo=Foto.TIPO_SOLTURA)

    def clean(self):
        super().clean()

        errors = {}

        self.classe = (self.classe or "").strip()
        self.nome_cientifico = (self.nome_cientifico or "").strip() or None
        self.nome_popular = (self.nome_popular or "").strip() or None
        self.estagio_desenvolvimento = (self.estagio_desenvolvimento or "").strip() or None
        self.area_captura = (self.area_captura or "").strip()
        self.local_captura = (self.local_captura or "").strip()
        self.descricao_local = (self.descricao_local or "").strip()
        self.responsavel_manejo = (self.responsavel_manejo or "").strip() or None
        self.area_soltura = (self.area_soltura or "").strip() or None
        self.local_soltura = (self.local_soltura or "").strip() or None
        self.descricao_local_soltura = (self.descricao_local_soltura or "").strip()
        self.orgao_publico = (self.orgao_publico or "").strip() or None
        self.numero_boletim_ocorrencia = (self.numero_boletim_ocorrencia or "").strip() or None
        self.motivo_acionamento = (self.motivo_acionamento or "").strip()
        self.observacoes = (self.observacoes or "").strip()

        if not self.data_hora:
            errors["data_hora"] = "A data e hora do manejo são obrigatórias."
        if not self.classe:
            errors["classe"] = "A classe é obrigatória."
        if not self.area_captura:
            errors["area_captura"] = "A área de captura é obrigatória."
        if not self.local_captura:
            errors["local_captura"] = "O local de captura é obrigatório."
        if self.realizado_manejo and not self.responsavel_manejo:
            errors["responsavel_manejo"] = "Informe o responsável quando o manejo for realizado."

        informou_soltura = any(
            [
                self.area_soltura,
                self.local_soltura,
                self.descricao_local_soltura,
            ]
        )
        if informou_soltura:
            if not self.area_soltura:
                errors["area_soltura"] = "Informe a área de soltura."
            if not self.local_soltura:
                errors["local_soltura"] = "Informe o local de soltura."

        if self.acionado_orgao_publico and not self.orgao_publico:
            errors["orgao_publico"] = "Informe o órgão público acionado."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        when = self.data_hora.strftime("%d/%m/%Y %H:%M") if self.data_hora else "sem data"
        especie = self.nome_popular or self.nome_cientifico or self.classe
        return f"{especie} - {self.local_captura} ({when})"
