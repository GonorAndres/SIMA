"""
a13: Cierre de la cola de mortalidad a edades avanzadas (modelo de Kannisto).

Por que existe este modulo
--------------------------
La mortalidad proyectada por Lee-Carter deja de ser creible arriba de los ~94
anios, y no por culpa del modelo: la sensibilidad estimada b_x se dispara
alrededor de siete veces en las edades 95-100 porque las tasas crudas m_x de
esas edades cayeron de forma implausible entre 1990 y 2019 (en logaritmos,
-1.61 a la edad 100 contra -0.44 a la edad 85). Eso es casi con certeza un
artefacto de denominador -- las estimaciones de poblacion de CONAPO a edades
extremas y el registro de defunciones a los 100 anios cambiaron durante la
ventana -- y no una mejora real. Lee-Carter lo lee como tendencia y lo
extrapola dos decadas mas, de modo que la q_x proyectada *baja* con la edad
arriba de 94: a 2049 pasaba de 0.1708 a los 94 a 0.1358 a los 98.

Una fuerza de mortalidad no puede decrecer con la edad a los 95 anios. La cola
si se aplana -- esa desaceleracion tardia es un hecho demografico bien
documentado -- pero se aplana creciendo, no cayendo.

El modelo
---------
Kannisto (1994) es la eleccion estandar para cerrar la cola, y es la que usa la
propia Human Mortality Database. Modela la fuerza de mortalidad como logistica:

    mu(x) = a * exp(b*x) / (1 + a * exp(b*x))

Dos propiedades la hacen la herramienta correcta aqui:

1. Es monotona creciente en x siempre que b > 0, asi que el cierre no puede
   reproducir el defecto que viene a corregir.
2. Su tasa de crecimiento se desacelera: mu tiende a 1 en vez de explotar como
   lo haria una extrapolacion de Gompertz. Esa es precisamente la cola larga
   que se observa a edades avanzadas.

El ajuste es lineal, no iterativo, porque la logistica se endereza en la escala
logit:

    logit(mu(x)) = ln(a) + b*x

de modo que basta una regresion por minimos cuadrados de logit(m_x) sobre x en
una ventana de edades creible. Sobre el ajuste unisex de Mexico proyectado a
2049, la ventana 80-93 reproduce la q_x observada dentro de 0.006 en toda la
ventana (b = 0.1013) y luego extrapola de forma suave: 0.191 a los 95 y 0.265 a
los 100, en lugar de la caida a 0.136.

Alcance deliberado
------------------
El cierre se aplica a las tablas *proyectadas*, no a las tasas de entrada. Los
parametros Lee-Carter (a_x, b_x, k_t, drift, varianza explicada) quedan
intactos: la decision fue corregir el defecto visible sin invalidar las cifras
ya publicadas del ajuste. La consecuencia que hay que tener presente es que
b_x sigue mostrando el pico artificial en la grafica de parametros; el cierre
impide que ese pico llegue a la q_x proyectada, pero no lo borra del ajuste.
"""

import numpy as np

from backend.engine.exceptions import ActuarialValidationError

# Ventana de ajuste por defecto. El limite inferior deja fuera las edades donde
# la curva aun no entra en regimen logistico; el superior (93) se detiene justo
# antes de que empiece la contaminacion de b_x, que arranca alrededor de 94.
DEFAULT_FIT_AGES = (80, 93)

# Edad desde la cual se sustituyen las tasas por el cierre.
DEFAULT_CLOSURE_AGE = 94


def fit_kannisto(
    ages: np.ndarray,
    mx: np.ndarray,
    fit_ages: tuple[int, int] = DEFAULT_FIT_AGES,
) -> tuple[float, float]:
    """Ajusta Kannisto por minimos cuadrados en escala logit.

    Parameters
    ----------
    ages, mx
        Edades y tasas centrales de mortalidad correspondientes.
    fit_ages
        Ventana de edades (inclusiva) sobre la que se ajusta.

    Returns
    -------
    (a, b)
        Parametros de mu(x) = a*exp(b*x) / (1 + a*exp(b*x)).
    """
    lo, hi = fit_ages
    sel = (ages >= lo) & (ages <= hi)
    if sel.sum() < 3:
        raise ActuarialValidationError(
            f"Kannisto fit window {fit_ages} covers {int(sel.sum())} ages; need at least 3",
            field="fit_ages",
            constraint="at least 3 ages inside the fitting window",
        )

    m = np.asarray(mx, dtype=float)[sel]
    # logit() exige 0 < m < 1. Una m_x >= 1 significa mas de una muerte esperada
    # por persona-anio, que a estas edades solo aparece con exposiciones rotas.
    if np.any(m <= 0) or np.any(m >= 1):
        raise ActuarialValidationError(
            "Kannisto fit needs 0 < m_x < 1 across the fitting window",
            field="mx",
            constraint="0 < m_x < 1 for ages in fit_ages",
        )

    logit = np.log(m / (1.0 - m))
    b, ln_a = np.polyfit(ages[sel], logit, 1)

    if b <= 0:
        raise ActuarialValidationError(
            f"Kannisto slope b={b:.4f} is not positive; the closure would not be "
            f"monotone increasing, which defeats its purpose",
            field="b",
            constraint="b > 0",
        )
    return float(np.exp(ln_a)), float(b)


def kannisto_mx(a: float, b: float, ages: np.ndarray) -> np.ndarray:
    """Fuerza de mortalidad de Kannisto evaluada en `ages`."""
    z = a * np.exp(b * np.asarray(ages, dtype=float))
    return z / (1.0 + z)


def close_qx(
    ages: np.ndarray,
    qx: np.ndarray,
    fit_ages: tuple[int, int] = DEFAULT_FIT_AGES,
    closure_age: int = DEFAULT_CLOSURE_AGE,
    force_terminal: bool = True,
) -> np.ndarray:
    """Sustituye la cola de `qx` por el cierre de Kannisto.

    Las edades por debajo de `closure_age` se devuelven intactas. La edad
    terminal se fuerza a q = 1.0 cuando `force_terminal` es True, que es la
    convencion de una tabla cerrada (omega = ultima edad).

    Se ajusta sobre m_x, no sobre q_x: la relacion m -> q no es lineal, asi que
    ajustar en la escala equivocada sesgaria la pendiente.
    """
    ages = np.asarray(ages)
    qx = np.asarray(qx, dtype=float).copy()

    if closure_age > int(ages[-1]):
        return qx  # nada que cerrar

    # q -> m bajo fuerza constante dentro del anio, que es la misma hipotesis
    # que usa to_life_table() en la direccion contraria.
    mx = -np.log(np.clip(1.0 - qx, 1e-12, None))

    a, b = fit_kannisto(ages, mx, fit_ages)

    tail = ages >= closure_age
    qx[tail] = 1.0 - np.exp(-kannisto_mx(a, b, ages[tail]))

    if force_terminal:
        qx[-1] = 1.0

    # np.clip is typed as returning Any, which `mypy --strict` rejects against
    # this function's declared ndarray return. Bind it first so the array type
    # is stated once, here, rather than inferred from the stub.
    closed: np.ndarray = np.clip(qx, 0.0, 1.0)
    return closed
