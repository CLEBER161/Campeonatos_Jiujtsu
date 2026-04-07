import uuid
from django.db import models
from django.contrib.auth.models import User


FAIXA_CHOICES = [
    ('branca', 'Branca'),
    ('cinza', 'Cinza'),
    ('amarela', 'Amarela'),
    ('laranja', 'Laranja'),
    ('verde', 'Verde'),
    ('azul', 'Azul'),
    ('roxa', 'Roxa'),
    ('marrom', 'Marrom'),
    ('preta', 'Preta'),
]

SEXO_CHOICES = [
    ('M', 'Masculino'),
    ('F', 'Feminino'),
]

RESULTADO_CHOICES = [
    ('pontos', 'Por Pontos'),
    ('finalizacao', 'Por Finalização'),
    ('desclassificacao', 'Desclassificação'),
    ('bye', 'BYE (Passagem)'),
    ('pendente', 'Pendente'),
    ('em_andamento', 'Em Andamento'),
]

STATUS_LUTA_CHOICES = [
    ('aguardando', 'Aguardando'),
    ('em_andamento', 'Em Andamento'),
    ('finalizada', 'Finalizada'),
]

MODALIDADE_INSCRICAO_CHOICES = [
    ('regular', 'Regular'),
    ('bolsa', 'Condição Especial / Bolsa'),
]


class Campeonato(models.Model):
    nome = models.CharField(max_length=200)
    local = models.CharField(max_length=200, blank=True)
    data_evento = models.DateField(null=True, blank=True)
    quantidade_tatames = models.PositiveIntegerField(default=4)
    inscricoes_abertas = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Prazos de pagamento e pesagem
    prazo_pagamento_dias = models.PositiveIntegerField(
        default=3,
        help_text='Quantos dias antes do evento fecha o pagamento (ex: 3)',
    )
    pesagem_inicio_dias = models.PositiveIntegerField(
        default=2,
        help_text='Abertura da janela de pesagem: X dias antes do evento (ex: 2)',
    )
    pesagem_fim_dias = models.PositiveIntegerField(
        default=1,
        help_text='Encerramento da janela de pesagem: X dias antes do evento (ex: 1)',
    )

    class Meta:
        verbose_name = 'Campeonato'
        verbose_name_plural = 'Campeonatos'
        ordering = ['-data_evento', '-criado_em', 'nome']

    def __str__(self):
        if self.data_evento:
            return f'{self.nome} ({self.data_evento:%d/%m/%Y})'
        return self.nome

    @property
    def prazo_pagamento_ok(self):
        """True se ainda está dentro do prazo para pagar."""
        from datetime import date, timedelta
        if not self.data_evento:
            return True
        return date.today() <= self.data_evento - timedelta(days=self.prazo_pagamento_dias)

    @property
    def janela_pesagem_ativa(self):
        """True se hoje está dentro da janela de pesagem."""
        from datetime import date, timedelta
        if not self.data_evento:
            return False
        inicio = self.data_evento - timedelta(days=self.pesagem_inicio_dias)
        fim = self.data_evento - timedelta(days=self.pesagem_fim_dias)
        return inicio <= date.today() <= fim


class Categoria(models.Model):
    campeonato = models.ForeignKey('Campeonato', on_delete=models.CASCADE, related_name='categorias', null=True, blank=True)
    nome = models.CharField(max_length=100)
    faixa = models.CharField(max_length=20, choices=FAIXA_CHOICES)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    peso_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    peso_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    idade_min = models.PositiveIntegerField(null=True, blank=True)
    idade_max = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['faixa', 'nome']

    def __str__(self):
        campeonato_nome = self.campeonato.nome if self.campeonato else 'Sem campeonato'
        return f'{self.nome} - {self.get_faixa_display()} ({self.get_sexo_display()}) - {campeonato_nome}'


class Baia(models.Model):
    """Área de espera/chamada antes do atleta entrar no tatame."""
    campeonato = models.ForeignKey('Campeonato', on_delete=models.CASCADE, related_name='baias', null=True, blank=True)
    nome = models.CharField(max_length=50)
    numero = models.PositiveIntegerField()
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Baia'
        verbose_name_plural = 'Baias'
        ordering = ['numero']
        constraints = [
            models.UniqueConstraint(fields=['campeonato', 'numero'], name='unique_baia_numero_por_campeonato'),
        ]

    def __str__(self):
        return f'Baia {self.numero} — {self.nome}'


class Tatame(models.Model):
    """Local da luta e da mesa do arbitro."""
    campeonato = models.ForeignKey('Campeonato', on_delete=models.CASCADE, related_name='tatames', null=True, blank=True)
    nome = models.CharField(max_length=50)
    numero = models.PositiveIntegerField()
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tatame'
        verbose_name_plural = 'Tatames'
        ordering = ['numero']
        constraints = [
            models.UniqueConstraint(fields=['campeonato', 'numero'], name='unique_tatame_numero_por_campeonato'),
        ]

    def __str__(self):
        return f'Tatame {self.numero} — {self.nome}'


class Arbitro(models.Model):
    FUNCAO_MESARIO = 'mesario'
    FUNCAO_ARBITRO = 'arbitro'
    FUNCAO_CHOICES = [
        (FUNCAO_MESARIO, 'Mesário'),
        (FUNCAO_ARBITRO, 'Árbitro'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_arbitro')
    nome = models.CharField(max_length=200)
    funcao = models.CharField(max_length=20, choices=FUNCAO_CHOICES, default=FUNCAO_MESARIO)
    senha_acesso = models.CharField(max_length=128, blank=True, default='')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Árbitro'
        verbose_name_plural = 'Árbitros'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def eh_mesario(self):
        return self.funcao == self.FUNCAO_MESARIO

    @property
    def eh_arbitro(self):
        return self.funcao == self.FUNCAO_ARBITRO


class ArbitroTatame(models.Model):
    arbitro = models.ForeignKey('Arbitro', on_delete=models.CASCADE, related_name='vinculos_tatame')
    campeonato = models.ForeignKey('Campeonato', on_delete=models.CASCADE, related_name='vinculos_arbitros')
    tatame = models.ForeignKey('Tatame', on_delete=models.CASCADE, related_name='vinculos_arbitros')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vínculo Árbitro x Tatame'
        verbose_name_plural = 'Vínculos Árbitro x Tatame'
        ordering = ['tatame__numero', 'arbitro__nome']
        constraints = [
            models.UniqueConstraint(fields=['arbitro', 'campeonato', 'tatame'], name='unique_vinculo_arbitro_tatame'),
        ]

    def __str__(self):
        return f'{self.arbitro.nome} - {self.tatame}'


class Atleta(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='perfil_atleta')
    nome = models.CharField(max_length=200)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    faixa = models.CharField(max_length=20, choices=FAIXA_CHOICES)
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    academia = models.CharField(max_length=200)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='atletas')
    foto = models.ImageField(upload_to='atletas/', null=True, blank=True)
    # Credencial / QR Code
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Atleta'
        verbose_name_plural = 'Atletas'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.academia})'

    @property
    def idade(self):
        from datetime import date
        hoje = date.today()
        return hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

    @property
    def check_in_realizado(self):
        return hasattr(self, 'checkin')

    def gerar_qr_code(self, base_url=''):
        """Gera e salva o QR Code da credencial do atleta."""
        import qrcode
        from io import BytesIO
        from django.core.files import File

        url = f"{base_url}/apoio/validar/{self.codigo}/"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_{self.codigo}.png'
        self.qr_code.save(filename, File(buffer), save=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self.gerar_qr_code()


class InscricaoCampeonato(models.Model):
    atleta = models.ForeignKey(Atleta, on_delete=models.CASCADE, related_name='inscricoes')
    campeonato = models.ForeignKey(Campeonato, on_delete=models.CASCADE, related_name='inscricoes')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscricoes')
    modalidade_inscricao = models.CharField(max_length=20, choices=MODALIDADE_INSCRICAO_CHOICES, default='regular')
    comprovante_pagamento = models.FileField(upload_to='comprovantes_pagamento/', null=True, blank=True)
    documento_bolsa = models.FileField(upload_to='documentos_bolsa/', null=True, blank=True)
    pagamento_confirmado = models.BooleanField(default=False)
    pagamento_confirmado_em = models.DateTimeField(null=True, blank=True)
    pesagem_confirmada = models.BooleanField(default=False)
    peso_aferido = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pesagem_realizada_em = models.DateTimeField(null=True, blank=True)
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='qrcodes_inscricoes/', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inscrição no Campeonato'
        verbose_name_plural = 'Inscrições no Campeonato'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(fields=['atleta', 'campeonato'], name='unique_atleta_por_campeonato'),
        ]

    def __str__(self):
        return f'{self.atleta.nome} - {self.campeonato.nome}'

    @property
    def documentacao_ok(self):
        if self.modalidade_inscricao == 'bolsa':
            return bool(self.documento_bolsa)
        return bool(self.comprovante_pagamento)

    @property
    def pendencia_documental(self):
        if self.modalidade_inscricao == 'bolsa':
            return 'Envie o documento da academia comprovando a bolsa.' if not self.documento_bolsa else ''
        return 'Envie o comprovante de pagamento para liberar a credencial.' if not self.comprovante_pagamento else ''

    def gerar_qr_code(self, base_url=''):
        """Gera e salva o QR Code da inscrição do atleta no campeonato."""
        if not self.documentacao_ok:
            return

        import qrcode
        from io import BytesIO
        from django.core.files import File

        url = f"{base_url}/apoio/validar/{self.codigo}/"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_inscricao_{self.codigo}.png'
        self.qr_code.save(filename, File(buffer), save=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.documentacao_ok and not self.qr_code:
            self.gerar_qr_code()


class CheckIn(models.Model):
    """Registro de check-in do atleta na entrada do campeonato."""
    atleta = models.ForeignKey(Atleta, on_delete=models.CASCADE, related_name='checkins', null=True, blank=True)
    inscricao = models.OneToOneField(InscricaoCampeonato, on_delete=models.CASCADE, related_name='checkin', null=True, blank=True)
    baia = models.ForeignKey(Baia, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkins')
    realizado_em = models.DateTimeField(auto_now_add=True)
    validado_por = models.CharField(max_length=100, blank=True, default='Apoio')

    class Meta:
        verbose_name = 'Check-In'
        verbose_name_plural = 'Check-Ins'
        ordering = ['-realizado_em']

    def __str__(self):
        atleta_nome = self.atleta.nome if self.atleta else self.inscricao.atleta.nome
        return f'Check-in: {atleta_nome} — {self.realizado_em:%d/%m/%Y %H:%M}'


class Chave(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='chaves')
    nome = models.CharField(max_length=100, default='Chave Principal')
    baia = models.ForeignKey(Baia, on_delete=models.SET_NULL, null=True, blank=True, related_name='chaves')
    tatame = models.ForeignKey(Tatame, on_delete=models.SET_NULL, null=True, blank=True, related_name='chaves')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chave'
        verbose_name_plural = 'Chaves'

    def __str__(self):
        return f'{self.nome} - {self.categoria}'


class Luta(models.Model):
    chave = models.ForeignKey(Chave, on_delete=models.CASCADE, related_name='lutas')
    baia = models.ForeignKey(Baia, on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas')
    tatame = models.ForeignKey(Tatame, on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas')
    arbitro = models.ForeignKey('Arbitro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas_arbitradas')
    iniciada_por = models.ForeignKey('Arbitro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas_iniciadas')
    finalizada_por = models.ForeignKey('Arbitro', on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas_finalizadas')
    atleta1 = models.ForeignKey(Atleta, on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas_como_atleta1')
    atleta2 = models.ForeignKey(Atleta, on_delete=models.SET_NULL, null=True, blank=True, related_name='lutas_como_atleta2')
    vencedor = models.ForeignKey(Atleta, on_delete=models.SET_NULL, null=True, blank=True, related_name='vitorias')
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default='pendente')
    status = models.CharField(max_length=20, choices=STATUS_LUTA_CHOICES, default='aguardando')
    pontos_atleta1 = models.PositiveIntegerField(default=0)
    pontos_atleta2 = models.PositiveIntegerField(default=0)
    vantagens_atleta1 = models.PositiveIntegerField(default=0)
    vantagens_atleta2 = models.PositiveIntegerField(default=0)
    penalizacoes_atleta1 = models.PositiveIntegerField(default=0)
    penalizacoes_atleta2 = models.PositiveIntegerField(default=0)
    rodada = models.PositiveIntegerField(default=1)
    ordem = models.PositiveIntegerField(default=1)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    realizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Luta'
        verbose_name_plural = 'Lutas'
        ordering = ['rodada', 'ordem']

    def __str__(self):
        a1 = self.atleta1.nome if self.atleta1 else 'BYE'
        a2 = self.atleta2.nome if self.atleta2 else 'BYE'
        return f'Rodada {self.rodada} - {a1} vs {a2}'


# ── Ações durante a luta (posições, finalizações, penalizações) ─────────────

CATEGORIA_ACAO_CHOICES = [
    ('pontos', 'Pontos'),
    ('vantagem', 'Vantagem'),
    ('penalizacao', 'Penalização'),
    ('finalizacao', 'Finalização'),
]


class TipoAcao(models.Model):
    """Catálogo de ações/posições que geram pontuação durante uma luta."""
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_ACAO_CHOICES)
    pontos = models.PositiveIntegerField(
        default=0,
        help_text='Pontos gerados. Para vantagem=1, penalização=0 (arbitro controla), finalização=0.',
    )
    descricao = models.CharField(max_length=300, blank=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0, help_text='Ordem de exibição na mesa do árbitro.')

    class Meta:
        verbose_name = 'Tipo de Ação'
        verbose_name_plural = 'Tipos de Ação'
        ordering = ['categoria', 'ordem', 'nome']

    def __str__(self):
        label = f'{self.pontos}pts' if self.pontos else self.get_categoria_display()
        return f'{self.nome} ({label})'


class AcaoLuta(models.Model):
    """Registro de cada ação/posição que ocorreu durante uma luta."""
    luta = models.ForeignKey(Luta, on_delete=models.CASCADE, related_name='acoes')
    atleta = models.ForeignKey(
        Atleta, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acoes_realizadas',
        help_text='Atleta que executou a ação.',
    )
    tipo_acao = models.ForeignKey(TipoAcao, on_delete=models.PROTECT, related_name='registros')
    registrado_por = models.ForeignKey(
        'Arbitro', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acoes_registradas',
    )
    registrado_em = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Ação na Luta'
        verbose_name_plural = 'Ações na Luta'
        ordering = ['registrado_em']

    def __str__(self):
        atleta_nome = self.atleta.nome if self.atleta else '?'
        return f'{self.luta} | {atleta_nome} — {self.tipo_acao.nome}'

