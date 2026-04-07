from .models import Categoria, FAIXA_CHOICES


PESOS_MASCULINO = [
    ("Galo", None, 57.50),
    ("Pluma", 57.51, 64.00),
    ("Pena", 64.01, 70.00),
    ("Leve", 70.01, 76.00),
    ("Medio", 76.01, 82.30),
    ("Meio-Pesado", 82.31, 88.30),
    ("Pesado", 88.31, 94.30),
    ("Super Pesado", 94.31, 100.50),
    ("Pesadissimo", 100.51, None),
]

PESOS_FEMININO = [
    ("Galo", None, 48.50),
    ("Pluma", 48.51, 53.50),
    ("Pena", 53.51, 58.50),
    ("Leve", 58.51, 64.00),
    ("Medio", 64.01, 69.00),
    ("Meio-Pesado", 69.01, 74.00),
    ("Pesado", 74.01, 79.30),
    ("Super Pesado", 79.31, None),
]

PESOS_JUVENIL_MASCULINO = [
    ("Galo", None, 53.50),
    ("Pluma", 53.51, 58.50),
    ("Pena", 58.51, 64.00),
    ("Leve", 64.01, 69.00),
    ("Medio", 69.01, 74.00),
    ("Meio-Pesado", 74.01, 79.30),
    ("Pesado", 79.31, 84.30),
    ("Super Pesado", 84.31, 89.30),
    ("Pesadissimo", 89.31, None),
]

PESOS_JUVENIL_FEMININO = [
    ("Galo", None, 44.30),
    ("Pluma", 44.31, 48.30),
    ("Pena", 48.31, 52.50),
    ("Leve", 52.51, 56.50),
    ("Medio", 56.51, 60.50),
    ("Meio-Pesado", 60.51, 65.50),
    ("Pesado", 65.51, 70.00),
    ("Super Pesado", 70.01, None),
]

RULE_PRESETS = {
    "cbjj_juvenil": {
        "label": "CBJJ Juvenil (16-17)",
        "prefix": "Juvenil",
        "idade_min": 16,
        "idade_max": 17,
        "masculino": PESOS_JUVENIL_MASCULINO,
        "feminino": PESOS_JUVENIL_FEMININO,
    },
    "cbjj_adulto": {
        "label": "CBJJ Adulto (18-29)",
        "prefix": "Adulto",
        "idade_min": 18,
        "idade_max": 29,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_master_1": {
        "label": "CBJJ Master 1 (30-35)",
        "prefix": "Master 1",
        "idade_min": 30,
        "idade_max": 35,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_master_2": {
        "label": "CBJJ Master 2 (36-40)",
        "prefix": "Master 2",
        "idade_min": 36,
        "idade_max": 40,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_master_3": {
        "label": "CBJJ Master 3 (41-45)",
        "prefix": "Master 3",
        "idade_min": 41,
        "idade_max": 45,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_nogi_adulto": {
        "label": "CBJJ No-Gi Adulto (18-29)",
        "prefix": "No-Gi Adulto",
        "idade_min": 18,
        "idade_max": 29,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_nogi_master_1": {
        "label": "CBJJ No-Gi Master 1 (30-35)",
        "prefix": "No-Gi Master 1",
        "idade_min": 30,
        "idade_max": 35,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_nogi_master_2": {
        "label": "CBJJ No-Gi Master 2 (36-40)",
        "prefix": "No-Gi Master 2",
        "idade_min": 36,
        "idade_max": 40,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
    "cbjj_nogi_master_3": {
        "label": "CBJJ No-Gi Master 3 (41-45)",
        "prefix": "No-Gi Master 3",
        "idade_min": 41,
        "idade_max": 45,
        "masculino": PESOS_MASCULINO,
        "feminino": PESOS_FEMININO,
    },
}

BELT_GROUPS = {
    "todas": {
        "label": "Todas as faixas",
        "values": [faixa for faixa, _ in FAIXA_CHOICES],
    },
    "adulto_coloridas": {
        "label": "Somente coloridas (Azul a Preta)",
        "values": ["azul", "roxa", "marrom", "preta"],
    },
    "iniciante": {
        "label": "Somente Branca",
        "values": ["branca"],
    },
}

SEX_SCOPE = {
    "ambos": {"label": "Masculino e Feminino", "values": ["M", "F"]},
    "masculino": {"label": "Somente Masculino", "values": ["M"]},
    "feminino": {"label": "Somente Feminino", "values": ["F"]},
}


def get_category_parameter_options():
    return {
        "rule_presets": [(k, v["label"]) for k, v in RULE_PRESETS.items()],
        "belt_groups": [(k, v["label"]) for k, v in BELT_GROUPS.items()],
        "sex_scopes": [(k, v["label"]) for k, v in SEX_SCOPE.items()],
    }


def seed_default_categories(campeonato, rule_preset="cbjj_adulto", belt_group="todas", sex_scope="ambos", clear_existing=False):
    """Cria categorias padrão parametrizadas com base nas regras selecionadas."""
    if campeonato is None:
        raise ValueError("campeonato inválido")
    if rule_preset not in RULE_PRESETS:
        raise ValueError("rule_preset inválido")
    if belt_group not in BELT_GROUPS:
        raise ValueError("belt_group inválido")
    if sex_scope not in SEX_SCOPE:
        raise ValueError("sex_scope inválido")

    preset = RULE_PRESETS[rule_preset]
    faixas = BELT_GROUPS[belt_group]["values"]
    sexos = SEX_SCOPE[sex_scope]["values"]

    created_count = 0
    deleted_count = 0

    for faixa in faixas:
        for sexo in sexos:
            pesos = preset["masculino"] if sexo == "M" else preset["feminino"]

            for nome_base, peso_min, peso_max in pesos:
                nome_categoria = f"{preset['prefix']} {nome_base}"

                if clear_existing:
                    deleted_count += Categoria.objects.filter(
                        campeonato=campeonato,
                        nome=nome_categoria,
                        faixa=faixa,
                        sexo=sexo,
                        idade_min=preset["idade_min"],
                        idade_max=preset["idade_max"],
                    ).delete()[0]

                _, created = Categoria.objects.get_or_create(
                    campeonato=campeonato,
                    nome=nome_categoria,
                    faixa=faixa,
                    sexo=sexo,
                    peso_min=peso_min,
                    peso_max=peso_max,
                    idade_min=preset["idade_min"],
                    idade_max=preset["idade_max"],
                )
                if created:
                    created_count += 1

    return {
        "created_count": created_count,
        "deleted_count": deleted_count,
        "rule_label": preset["label"],
        "belt_label": BELT_GROUPS[belt_group]["label"],
        "sex_label": SEX_SCOPE[sex_scope]["label"],
    }