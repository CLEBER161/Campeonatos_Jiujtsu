from django import forms
import re
import unicodedata
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Atleta, Categoria, Chave, Luta, CheckIn, Baia, Tatame, Campeonato, InscricaoCampeonato, Arbitro, ArbitroTatame


def normalizar_username(valor):
    """Converte texto livre em username compatível com Django."""
    texto = unicodedata.normalize('NFKD', (valor or '')).encode('ascii', 'ignore').decode('ascii')
    texto = texto.strip().lower()
    texto = re.sub(r'\s+', '_', texto)
    texto = re.sub(r'[^\w.@+-]', '', texto)
    return texto


class CampeonatoForm(forms.ModelForm):
    class Meta:
        model = Campeonato
        fields = ['nome', 'local', 'data_evento', 'quantidade_tatames', 'inscricoes_abertas', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Open Jiu-Jitsu 2026'}),
            'local': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ginásio Municipal'}),
            'data_evento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade_tatames': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '50'}),
            'inscricoes_abertas': forms.CheckboxInput(attrs={'style': 'width:18px;height:18px;'}),
            'ativo': forms.CheckboxInput(attrs={'style': 'width:18px;height:18px;'}),
        }


class CadastroAtletaForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'seuemail@dominio.com'}))
    nome = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}))
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    sexo = forms.ChoiceField(choices=Atleta._meta.get_field('sexo').choices, widget=forms.Select(attrs={'class': 'form-control'}))
    faixa = forms.ChoiceField(choices=Atleta._meta.get_field('faixa').choices, widget=forms.Select(attrs={'class': 'form-control'}))
    peso = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Ex: 70.5'}))
    academia = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da academia'}))
    foto = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuário de acesso'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'E-mail para recuperação de senha'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Senha'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirme a senha'})

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        username_normalizado = normalizar_username(username)
        if not username_normalizado:
            raise forms.ValidationError('Informe um nome de usuário válido.')
        return username_normalizado

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe um usuário com este e-mail.')
        return email


class CadastroArbitroForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@dominio.com'}))
    nome = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do árbitro'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Usuário de acesso do árbitro'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'E-mail para recuperação de senha'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Senha'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirme a senha'})

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        username_normalizado = normalizar_username(username)
        if not username_normalizado:
            raise forms.ValidationError('Informe um nome de usuário válido.')
        return username_normalizado

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe um usuário com este e-mail.')
        return email


class ArbitroTatameForm(forms.ModelForm):
    class Meta:
        model = ArbitroTatame
        fields = ['arbitro', 'tatame']
        widgets = {
            'arbitro': forms.Select(attrs={'class': 'form-control'}),
            'tatame': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        campeonato = kwargs.pop('campeonato', None)
        funcao = kwargs.pop('funcao', None)
        super().__init__(*args, **kwargs)
        qs = Arbitro.objects.filter(ativo=True)
        if funcao:
            qs = qs.filter(funcao=funcao)
        self.fields['arbitro'].queryset = qs.order_by('nome')
        self.fields['tatame'].queryset = Tatame.objects.filter(campeonato=campeonato, ativo=True).order_by('numero') if campeonato else Tatame.objects.none()


class InscricaoCampeonatoForm(forms.ModelForm):
    class Meta:
        model = InscricaoCampeonato
        fields = ['modalidade_inscricao', 'comprovante_pagamento', 'documento_bolsa']
        widgets = {
            'modalidade_inscricao': forms.Select(attrs={'class': 'form-control'}),
            'comprovante_pagamento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'documento_bolsa': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        modalidade = cleaned_data.get('modalidade_inscricao')
        comprovante = cleaned_data.get('comprovante_pagamento') or getattr(self.instance, 'comprovante_pagamento', None)
        documento_bolsa = cleaned_data.get('documento_bolsa') or getattr(self.instance, 'documento_bolsa', None)

        if modalidade == 'bolsa':
            if not documento_bolsa:
                self.add_error('documento_bolsa', 'Envie o documento da academia comprovando a bolsa.')
            cleaned_data['comprovante_pagamento'] = None
        else:
            if not comprovante:
                self.add_error('comprovante_pagamento', 'Envie o comprovante de pagamento para concluir a inscrição.')
            cleaned_data['documento_bolsa'] = None

        return cleaned_data


class AtletaForm(forms.ModelForm):
    class Meta:
        model = Atleta
        fields = ['nome', 'data_nascimento', 'sexo', 'faixa', 'peso', 'academia', 'foto']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'faixa': forms.Select(attrs={'class': 'form-control'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Ex: 70.5'}),
            'academia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da academia'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'faixa', 'sexo', 'peso_min', 'peso_max', 'idade_min', 'idade_max']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Adulto Leve'}),
            'faixa': forms.Select(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'peso_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'peso_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'idade_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'idade_max': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class LutaResultadoForm(forms.ModelForm):
    class Meta:
        model = Luta
        fields = [
            'vencedor',
            'resultado',
            'pontos_atleta1',
            'pontos_atleta2',
            'vantagens_atleta1',
            'vantagens_atleta2',
            'penalizacoes_atleta1',
            'penalizacoes_atleta2',
        ]
        widgets = {
            'vencedor': forms.Select(attrs={'class': 'form-control'}),
            'resultado': forms.Select(attrs={'class': 'form-control'}),
            'pontos_atleta1': forms.NumberInput(attrs={'class': 'form-control'}),
            'pontos_atleta2': forms.NumberInput(attrs={'class': 'form-control'}),
            'vantagens_atleta1': forms.NumberInput(attrs={'class': 'form-control'}),
            'vantagens_atleta2': forms.NumberInput(attrs={'class': 'form-control'}),
            'penalizacoes_atleta1': forms.NumberInput(attrs={'class': 'form-control'}),
            'penalizacoes_atleta2': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        luta = self.instance
        atletas = []
        if luta.atleta1:
            atletas.append(luta.atleta1)
        if luta.atleta2:
            atletas.append(luta.atleta2)
        from .models import Atleta
        self.fields['vencedor'].queryset = Atleta.objects.filter(pk__in=[a.pk for a in atletas])
        self.fields['vencedor'].empty_label = '--- Selecione o vencedor ---'


class CheckInForm(forms.ModelForm):
    class Meta:
        model = CheckIn
        fields = ['baia', 'validado_por']
        widgets = {
            'baia': forms.Select(attrs={'class': 'form-control'}),
            'validado_por': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do responsável'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['baia'].queryset = Baia.objects.filter(ativa=True)
        self.fields['baia'].empty_label = '--- Selecione a baia (opcional) ---'
        self.fields['baia'].required = False
        self.fields['validado_por'].required = False


class BaiaForm(forms.ModelForm):
    class Meta:
        model = Baia
        fields = ['numero', 'nome', 'ativa']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Chamada Principal'}),
            'ativa': forms.CheckboxInput(attrs={'style': 'width:18px;height:18px;'}),
        }


class TatameForm(forms.ModelForm):
    arbitro_existente = forms.ModelChoiceField(
        queryset=Arbitro.objects.none(),
        required=False,
        empty_label='--- Criar novo árbitro para este tatame ---',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    arbitro_nome = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do árbitro responsável'}),
    )
    arbitro_username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuário de login do árbitro'}),
    )
    arbitro_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email do árbitro'}),
    )
    arbitro_password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha do árbitro'}),
    )
    arbitro_password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirme a senha do árbitro'}),
    )

    class Meta:
        model = Tatame
        fields = ['numero', 'nome', 'ativo']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Area Central'}),
            'ativo': forms.CheckboxInput(attrs={'style': 'width:18px;height:18px;'}),
        }

    def __init__(self, *args, **kwargs):
        campeonato = kwargs.pop('campeonato', None)
        super().__init__(*args, **kwargs)
        self.fields['arbitro_existente'].queryset = Arbitro.objects.filter(ativo=True).order_by('nome')
        self.campeonato = campeonato

    def clean(self):
        cleaned_data = super().clean()
        arbitro_existente = cleaned_data.get('arbitro_existente')
        arbitro_nome = (cleaned_data.get('arbitro_nome') or '').strip()
        arbitro_username = (cleaned_data.get('arbitro_username') or '').strip()
        arbitro_email = (cleaned_data.get('arbitro_email') or '').strip().lower()
        arbitro_password1 = cleaned_data.get('arbitro_password1') or ''
        arbitro_password2 = cleaned_data.get('arbitro_password2') or ''

        if arbitro_existente:
            return cleaned_data

        if not arbitro_nome:
            self.add_error('arbitro_nome', 'Informe o árbitro responsável pela mesa.')
        if not arbitro_username:
            self.add_error('arbitro_username', 'Informe o usuário de login do árbitro.')
        elif User.objects.filter(username=arbitro_username).exists():
            self.add_error('arbitro_username', 'Já existe um usuário com este nome.')
        if not arbitro_email:
            self.add_error('arbitro_email', 'Informe o e-mail do árbitro para recuperação de senha.')
        elif User.objects.filter(email__iexact=arbitro_email).exists():
            self.add_error('arbitro_email', 'Já existe um usuário com este e-mail.')
        if not arbitro_password1:
            self.add_error('arbitro_password1', 'Informe a senha do árbitro.')
        if not arbitro_password2:
            self.add_error('arbitro_password2', 'Confirme a senha do árbitro.')
        if arbitro_password1 and arbitro_password2 and arbitro_password1 != arbitro_password2:
            self.add_error('arbitro_password2', 'As senhas do árbitro não coincidem.')

        return cleaned_data

