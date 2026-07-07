"""Persistência e validação das configurações de experimento (.config = JSON).

Sem dependências externas. Reaproveita os caminhos cross-platform de `src.utils.paths`.
As mensagens de erro são específicas por campo (em português) para serem exibidas direto
ao usuário.
"""

import os
import re
import json

from . import config_logger
from src.utils import (ENCODING_FORMAT, APP_NAME, EXPERIMENT_FILES_DIRNAME, PREFS_FILENAME,
                      get_documents_dir, get_app_data_dir)

CONFIG_VERSION = 1

REQUIRED_KEYS = [
    "music_folder",
    "music_quantity",
    "noise_quantity",
    "factors_file",
    "data_save_path",
    "bitalino_channel",
    "bitalino_mac",
]

# Chaves opcionais: gravadas no `.config`, mas ausentes nos arquivos antigos. NÃO entram em
# REQUIRED_KEYS para não invalidar `.config`s salvos antes de sua introdução (compat retroativa);
# são default-adas na leitura.
OPTIONAL_KEYS = [
    "pre_stimulus_seconds",
]

# Faixa aceita para o tempo pré-estímulo (contagem regressiva antes de cada faixa), em segundos.
PRE_STIMULUS_MIN = 5
PRE_STIMULUS_MAX = 120
PRE_STIMULUS_DEFAULT = 5

CHANNEL_OPTIONS = ["A1", "A2", "A3", "A4", "A5", "A6"]

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:\s]){5}[0-9A-Fa-f]{2}$")

# rótulos amigáveis para as mensagens de validação
_FIELD_LABELS = {
    "music_folder": "Pasta de músicas",
    "music_quantity": "Quantidade de músicas",
    "noise_quantity": "Quantidade de ruído",
    "factors_file": "Arquivo de fatores",
    "data_save_path": "Pasta de salvamento dos dados",
    "bitalino_channel": "Canal ativo do BITalino",
    "bitalino_mac": "Endereço MAC do BITalino",
    "pre_stimulus_seconds": "Tempo pré-estímulo",
}


def get_experiment_files_dir():
    """Pasta padrão dos arquivos de configuração: ``Documentos/ComPasso/Experiment files``."""
    return get_documents_dir() / APP_NAME / EXPERIMENT_FILES_DIRNAME


def get_prefs_path():
    """Arquivo de preferências do app: ``<app-data>/ComPasso/prefs.json``."""
    return get_app_data_dir() / APP_NAME / PREFS_FILENAME


def default_config() -> dict:
    """Retorna uma configuração vazia com a versão de schema atual."""
    return {
        "config_version": CONFIG_VERSION,
        "music_folder": "",
        "music_quantity": 0,
        "noise_quantity": 0,
        "factors_file": "",
        "data_save_path": "",
        "bitalino_channel": "",
        "bitalino_mac": "",
        "pre_stimulus_seconds": PRE_STIMULUS_DEFAULT,
    }


def _is_int(value, minimum: int) -> bool:
    """True se `value` (int ou str) é um inteiro >= minimum."""
    try:
        text = str(value).strip()
        if not text.lstrip("-").isdigit():
            return False
        return int(text) >= minimum
    except (TypeError, ValueError):
        return False


def validate_values(values: dict) -> list:
    """Valida os valores de uma configuração; retorna lista de mensagens de erro (vazia se OK).

    Regras: todos os campos preenchidos; pasta de músicas e de salvamento existem; arquivo de
    fatores existe e é .xlsx/.xls; MAC no formato correto; canal em A1–A6; quantidade de músicas
    >= 1 e de ruído >= 0.
    """
    errors = []

    music_folder = str(values.get("music_folder") or "").strip()
    if not music_folder:
        errors.append("Pasta de músicas: campo obrigatório.")
    elif not os.path.isdir(music_folder):
        errors.append(f"Pasta de músicas: diretório não encontrado ({music_folder}).")

    if not _is_int(values.get("music_quantity"), 1):
        errors.append("Quantidade de músicas: deve ser um número inteiro maior ou igual a 1.")

    if not _is_int(values.get("noise_quantity"), 0):
        errors.append("Quantidade de ruído: deve ser um número inteiro maior ou igual a 0.")

    factors_file = str(values.get("factors_file") or "").strip()
    if not factors_file:
        errors.append("Arquivo de fatores: campo obrigatório.")
    elif not os.path.isfile(factors_file):
        errors.append(f"Arquivo de fatores: arquivo não encontrado ({factors_file}).")
    elif not factors_file.lower().endswith((".xlsx", ".xls")):
        errors.append("Arquivo de fatores: deve ser um arquivo .xlsx ou .xls.")

    data_save_path = str(values.get("data_save_path") or "").strip()
    if not data_save_path:
        errors.append("Pasta de salvamento dos dados: campo obrigatório.")
    elif not os.path.isdir(data_save_path):
        errors.append(f"Pasta de salvamento dos dados: diretório não encontrado ({data_save_path}).")

    channel = str(values.get("bitalino_channel") or "").strip()
    if not channel:
        errors.append("Canal ativo do BITalino: campo obrigatório.")
    elif channel not in CHANNEL_OPTIONS:
        errors.append(f"Canal ativo do BITalino: selecione um valor entre {CHANNEL_OPTIONS[0]} e {CHANNEL_OPTIONS[-1]}.")

    mac = str(values.get("bitalino_mac") or "").strip()
    if not mac:
        errors.append("Endereço MAC do BITalino: campo obrigatório.")
    elif not MAC_REGEX.match(mac):
        errors.append("Endereço MAC do BITalino: formato inválido (use XX:XX:XX:XX:XX:XX).")

    # Chave opcional: só valida quando presente (arquivos antigos não a possuem).
    if "pre_stimulus_seconds" in values:
        pre_stimulus = str(values.get("pre_stimulus_seconds")).strip()
        if not (_is_int(pre_stimulus, PRE_STIMULUS_MIN)
                and int(pre_stimulus) <= PRE_STIMULUS_MAX):
            errors.append(
                f"Tempo pré-estímulo: informe um inteiro entre {PRE_STIMULUS_MIN} e "
                f"{PRE_STIMULUS_MAX} segundos.")

    return errors


def save_config(path: str, values: dict) -> None:
    """Grava `values` como JSON no caminho `.config`, injetando a versão de schema."""
    data = {"config_version": CONFIG_VERSION}
    for key in REQUIRED_KEYS:
        data[key] = values.get(key, "")
    defaults = default_config()
    for key in OPTIONAL_KEYS:
        data[key] = values.get(key, defaults.get(key))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding=ENCODING_FORMAT) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    config_logger.logger.info(f"Configuração salva: {path}")


def load_config(path: str):
    """Carrega e valida um arquivo `.config`.

    :return: (data, errors). `data` é o dict carregado (ou None se o JSON for inválido);
        `errors` é uma lista de mensagens específicas por campo (vazia em caso de sucesso).
    """
    try:
        with open(path, "r", encoding=ENCODING_FORMAT) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        config_logger.logger.error(f"Falha ao ler configuração {path}: {e}")
        return None, ["Arquivo de configuração inválido ou ilegível (JSON malformado)."]

    if not isinstance(data, dict):
        return None, ["Arquivo de configuração inválido (estrutura inesperada)."]

    errors = []
    if "config_version" not in data:
        errors.append("Campo ausente: versão da configuração (config_version).")

    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Campo ausente: {_FIELD_LABELS.get(key, key)}.")
        elif str(data.get(key)).strip() == "":
            errors.append(f"Campo vazio: {_FIELD_LABELS.get(key, key)}.")

    # Chaves opcionais ausentes (arquivos antigos) caem no default silenciosamente.
    defaults = default_config()
    for key in OPTIONAL_KEYS:
        if key not in data:
            data[key] = defaults.get(key)

    # validação de valores apenas se todas as chaves obrigatórias estão presentes
    if not any(msg.startswith("Campo ausente") for msg in errors):
        errors.extend(validate_values(data))

    return data, errors


def _read_prefs() -> dict:
    try:
        with open(get_prefs_path(), "r", encoding=ENCODING_FORMAT) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_prefs(prefs: dict) -> None:
    """Grava o dict de preferências em `prefs.json`, criando a pasta se necessário."""
    prefs_path = get_prefs_path()
    try:
        os.makedirs(os.path.dirname(str(prefs_path)), exist_ok=True)
        with open(prefs_path, "w", encoding=ENCODING_FORMAT) as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except OSError as e:
        config_logger.logger.error(f"Falha ao gravar preferências: {e}")


def set_last_config(path: str) -> None:
    """Registra, nas preferências, o caminho do último `.config` salvo/aberto."""
    prefs = _read_prefs()
    prefs["last_config"] = str(path)
    _write_prefs(prefs)


def get_last_config_path():
    """Retorna o caminho do último `.config` usado, ou None se não houver."""
    path = _read_prefs().get("last_config")
    return path if path else None


def set_theme_pref(name: str) -> None:
    """Registra, nas preferências, o nome da paleta de tema selecionada."""
    prefs = _read_prefs()
    prefs["theme"] = str(name)
    _write_prefs(prefs)


def get_theme_pref():
    """Retorna o nome da paleta de tema salva, ou None se não houver."""
    name = _read_prefs().get("theme")
    return name if name else None


# Configurações de exibição do gráfico do sinal em tempo real (ver
# src/gui/frames/signal_plot.py). Os defaults são exatamente os valores hardcoded
# atuais do gráfico; são usados na primeira execução e sempre que uma chave estiver
# ausente ou inválida no prefs.json.
DEFAULT_GRAPH_SETTINGS = {
    "y_scale": 30,               # escala Y simétrica (µV): ±20/±30/±40/±50
    "smoothing_enabled": True,   # média móvel de exibição ligada?
    "smoothing_window": 5,       # janela da média móvel (colunas de exibição, 1–15)
    "fps": 60,                   # quadros por segundo do gráfico: 10/15/30/60
    "line_width": 1.5,           # espessura da linha do sinal (px)
    "grid_visible": True,        # mostrar linhas de grade?
    "axis_labels_visible": True, # mostrar rótulos dos eixos?
    "value_mode": "raw",         # modo do rótulo de valor: "raw" (bruto) ou "mean" (média)
}

# Valores aceitos para configurações de gráfico do tipo string (validação em get_graph_prefs).
GRAPH_ENUM_OPTIONS = {
    "value_mode": {"raw", "mean"},
}


def get_graph_prefs() -> dict:
    """Retorna as configurações do gráfico, mesclando os defaults com o que houver salvo.

    Parte de uma cópia de ``DEFAULT_GRAPH_SETTINGS`` e sobrepõe apenas as chaves
    conhecidas presentes (e do tipo esperado) em ``prefs["graph"]`` — assim chaves
    ausentes na primeira execução caem no default e valores inesperados são ignorados.
    """
    result = dict(DEFAULT_GRAPH_SETTINGS)
    stored = _read_prefs().get("graph")
    if isinstance(stored, dict):
        for key, default_value in DEFAULT_GRAPH_SETTINGS.items():
            if key not in stored:
                continue
            value = stored[key]
            if isinstance(default_value, bool):
                if isinstance(value, bool):        # bool antes de int (bool é subclasse de int)
                    result[key] = value
            elif isinstance(default_value, (int, float)):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    result[key] = value
            elif isinstance(default_value, str):
                # chaves-enumeração: só aceita string dentro do conjunto permitido
                if isinstance(value, str) and value in GRAPH_ENUM_OPTIONS.get(key, {value}):
                    result[key] = value
    return result


def set_graph_prefs(settings: dict) -> None:
    """Persiste as configurações do gráfico em ``prefs["graph"]`` (preserva tema/last_config).

    Grava somente as chaves de ``DEFAULT_GRAPH_SETTINGS``, caindo no default quando
    uma delas estiver ausente em ``settings``.
    """
    prefs = _read_prefs()
    prefs["graph"] = {key: settings.get(key, default_value)
                      for key, default_value in DEFAULT_GRAPH_SETTINGS.items()}
    _write_prefs(prefs)
