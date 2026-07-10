"""Logica pura da calibracao de volume de som (sem hardware/GUI, testavel).

A calibracao toca uma faixa dedicada enquanto o volume principal do sistema sobe em degraus
(``step_pct`` a cada ``step_seg`` segundos) de um minimo ate um maximo, mantendo o maximo por
``CALIB_HOLD_SEGUNDOS`` antes de parar. Este modulo concentra as constantes de dominio, a
validacao dos parametros e o calculo da rampa; a orquestracao por temporizador e a reproducao
ficam na janela de calibracao (``compasso.gui.calibration_window``).
"""

import math

# Limites do volume principal do sistema (escala 0-100, como em audio.set_system_volume).
VOL_MIN = 0
VOL_MAX = 100

# Volume minimo/maximo padrao da rampa de calibracao, em % do volume do sistema.
CALIB_VOL_MIN_DEFAULT = 30
CALIB_VOL_MAX_DEFAULT = 50

# Passo de aumento do volume a cada degrau (%). Faixa aceita: 1 a 5.
CALIB_STEP_PCT_DEFAULT = 1
CALIB_STEP_PCT_MIN = 1
CALIB_STEP_PCT_MAX = 5

# Intervalo entre degraus (s). Faixa aceita: 1 a 5.
CALIB_STEP_SEG_DEFAULT = 1
CALIB_STEP_SEG_MIN = 1
CALIB_STEP_SEG_MAX = 5

# Diferenca maxima permitida entre o volume maximo e o minimo (%). Evita saltos grandes demais.
CALIB_DIFF_MAX = 40

# Tempo mantido no volume maximo antes de encerrar a rampa (s).
CALIB_HOLD_SEGUNDOS = 2


def _para_inteiro(valor):
    """Converte ``valor`` (int ou str de digitos) para int; retorna None se nao for inteiro.

    Aceita string com espacos ao redor. Nao aceita sinal, ponto decimal ou texto — a
    calibracao trabalha com percentuais inteiros nao negativos.
    """
    try:
        texto = str(valor).strip()
    except (TypeError, ValueError):
        return None
    if not texto.isdigit():
        return None
    return int(texto)


def validar_parametros(vol_min, vol_max, step_pct, step_seg) -> list:
    """Valida os parametros da rampa; retorna lista de mensagens de erro (vazia se OK).

    Regras: volumes sao inteiros em ``[VOL_MIN, VOL_MAX]``; ``vol_min <= vol_max``; a diferenca
    ``vol_max - vol_min`` nao passa de ``CALIB_DIFF_MAX``; ``step_pct``/``step_seg`` estao dentro
    das faixas aceitas. As mensagens sao em portugues e especificas por campo.
    """
    erros = []

    minimo = _para_inteiro(vol_min)
    maximo = _para_inteiro(vol_max)

    if minimo is None or not (VOL_MIN <= minimo <= VOL_MAX):
        erros.append(f"Volume minimo: informe um numero inteiro entre {VOL_MIN} e {VOL_MAX}%.")
    if maximo is None or not (VOL_MIN <= maximo <= VOL_MAX):
        erros.append(f"Volume maximo: informe um numero inteiro entre {VOL_MIN} e {VOL_MAX}%.")

    # Comparacoes entre minimo/maximo so fazem sentido se ambos forem numeros validos.
    if minimo is not None and maximo is not None:
        if minimo > maximo:
            erros.append("Volume minimo nao pode ser maior que o volume maximo.")
        elif maximo - minimo > CALIB_DIFF_MAX:
            erros.append(
                f"A diferenca entre o volume maximo e o minimo nao pode passar de "
                f"{CALIB_DIFF_MAX}% (recebido: {maximo - minimo}%).")

    passo = _para_inteiro(step_pct)
    if passo is None or not (CALIB_STEP_PCT_MIN <= passo <= CALIB_STEP_PCT_MAX):
        erros.append(
            f"Passo de volume: informe um inteiro entre {CALIB_STEP_PCT_MIN} e "
            f"{CALIB_STEP_PCT_MAX}%.")

    intervalo = _para_inteiro(step_seg)
    if intervalo is None or not (CALIB_STEP_SEG_MIN <= intervalo <= CALIB_STEP_SEG_MAX):
        erros.append(
            f"Intervalo de aumento: informe um inteiro entre {CALIB_STEP_SEG_MIN} e "
            f"{CALIB_STEP_SEG_MAX} segundos.")

    return erros


def numero_de_incrementos(vol_min, vol_max, step_pct) -> int:
    """Numero de degraus necessarios para ir de ``vol_min`` ate ``vol_max`` com passo ``step_pct``.

    Arredonda para cima: um resto (ex.: 30->50 com passo 3) ainda exige um ultimo degrau que e
    limitado ao maximo. Retorna 0 se os volumes forem iguais.
    """
    minimo = int(vol_min)
    maximo = int(vol_max)
    passo = int(step_pct)
    if maximo <= minimo or passo <= 0:
        return 0
    return math.ceil((maximo - minimo) / passo)


def duracao_estimada_segundos(vol_min, vol_max, step_pct, step_seg,
                              hold_seg=CALIB_HOLD_SEGUNDOS) -> float:
    """Duracao total estimada do teste, em segundos.

    Cada degrau consome ``step_seg`` segundos ate o volume chegar ao maximo; depois o maximo e
    mantido por ``hold_seg`` segundos antes de parar. Usado para bloquear o inicio quando a
    faixa de audio for mais curta que o teste.
    """
    return numero_de_incrementos(vol_min, vol_max, step_pct) * int(step_seg) + float(hold_seg)


def volume_no_incremento(indice, vol_min, vol_max, step_pct) -> int:
    """Volume (limitado ao maximo) no degrau ``indice`` da rampa (indice 0 = ``vol_min``)."""
    return min(int(vol_min) + int(indice) * int(step_pct), int(vol_max))
