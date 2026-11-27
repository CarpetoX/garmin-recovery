# Cierre diario · 27/11/2026

`GR-2026-11-27-2247-c5ba8f` · cita este identificador al reenviar el informe.

> **Hoy: 🔴 rojo — Prioriza recuperar.** RPE ≤ 4 · volumen 0–50 %.
>
> **Por qué:** lo marca Híbrido Garmin + local (49); señales: Forma -88 % (riesgo_alto).
>
> **Qué hacer:** Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.

## 🔴 Decisión: rojo — Prioriza recuperar

| RPE máximo | Volumen | HRV | FC reposo | Sueño | Garmin Readiness |
|--:|--:|--:|--:|--:|--:|
| 4 | 0–50 % | 71 ms | 52 lpm | 7,97 h | 32/100 |

<details><summary>Cómo se decide (modelos)</summary>

| Modelo | Puntuación | Zona | Papel |
|---|--:|---|---|
| Recuperación oficial | 88 | verde | oficial |
| Híbrido Garmin + local | 49 | rojo | salvaguarda |
| Modelo experimental | 79 | verde | sombra |
| Modelo de compatibilidad | 91 | verde | compatibilidad |
| Garmin Training Readiness | 32 | — | contexto |

_Las puntuaciones no son equivalentes entre sí. Zona operativa = la más conservadora entre el modelo oficial, el híbrido y el experimental. Un rojo prevalece siempre; si no hay rojo y algún modelo está pendiente, sin datos o es de otro día, queda pendiente. Un rojo de otro día sigue limitando hasta que llegue el dato de hoy._

</details>

## En el box hoy

- Sin WOD ni cargas pesadas: movilidad, técnica con PVC o barra vacía.
- Si te mueves, zona 2 suave en remo, bici o caminata (30–40 min, poder hablar).

## Cómo ajustar tu sesión de hoy

<details><summary>Reglas por tipo de sesión</summary>

Aplica la regla del tipo de sesión que decidas hacer (sobre tu prescripción habitual):

| Tipo | Ajuste de hoy | RPE máx. |
|---|---|--:|
| Fuerza | **Sustituir:** Técnica del patrón con barra vacía o PVC (15–20 min) + movilidad. Sin cargas. | 4 |
| Halterofilia | **Sustituir:** Técnica con PVC o barra vacía (15–20 min): posiciones y recepciones. Sin cargas. | 4 |
| WOD | **Sustituir:** Zona 2 suave 30–40 min (remo, bici o caminata), pudiendo hablar. | 4 |
| Técnica | **Reducir:** Técnica ligera ≤ 15 min, sin fatiga. | 4 |
| Aeróbico | **Reducir:** Zona 2 suave ≤ 40 min. | 4 |
| Movilidad | **Mantener:** Movilidad tal como está planificada. | 4 |

_Ejemplo en ámbar: sentadilla 5 × 3 a 150–160 kg → 4 × 3 a 135–142,5 kg. Para ajustar una sesión concreta, pregunta con este informe._

</details>

## Qué ha cambiado desde el informe anterior

Frente al informe GR-2026-11-27-1647-99d45f (27/11 16:47):
- Sin cambios en los datos.

## Balance del día

| Fecha | Tipo | Sesión | Min | Carga | FC media / máx. | RPE | sRPE |
|---|---|---|--:|--:|--:|--:|--:|
| 27/11 11:29 | Fuerza | Fuerza - pecho: press banca y press inclinado con mancuernas | 21 | 7 | 110 / 140 | 5,0 | 106 |
| 27/11 10:57 | WOD | WOD For Time 20-16-12-8 - thruster / toes to bar | 9 | 11 | 157 / 184 | 7,5 | 67 |
| 27/11 10:21 | Fuerza | Fuerza - front squat (+ calentamiento) | 36 | 16 | 119 / 170 | 7,0 | 249 |

- ⚠️ WOD For Time 20-16-12-8 - thruster / toes to bar: RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste.

_RPE frente a FC: esfuerzo relativo frente a tu historial del mismo tipo de sesión; descriptivo, no cambia la decisión._

## Balance de la semana

- Carga 7 días: **192** en 10 sesiones (+18 % vs. semana previa).
- sRPE 7 días 1.903 · monotonía 0,73 · strain 1.382.
- Fatiga acumulada: ATL 28,8, CTL 15,3, TSB -13,5.

## Previsión orientativa para mañana

- Objetivo de sueño esta noche: **8,0 h** (necesidad + parte de la deuda de 1,4 h).
- La decisión de mañana dependerá del sueño y la HRV de esta noche; no se anticipa.

## Gráficas

![RPE frente al máximo del día](charts/rpe.svg)

_Barras: RPE de la sesión más dura de cada día, por tipo. Raya gris: máximo que permitía la decisión de ese día (verde 9, ámbar 7, rojo 4, pendiente 6); en días verdes un WOD a RPE 8–9 está dentro. Punto rojo: por encima del máximo. Franja superior: decisión del día._

![Carga](charts/load.svg)

![Disponibilidad](charts/readiness.svg)

## Validación de modelos

_¿La puntuación de la mañana anticipa cuánto te cuesta entrenar? Se compara con tu esfuerzo relativo (RPE × duración frente a la carga cardiaca, dentro de cada tipo de sesión). Un modelo útil tiene correlación negativa: puntuación baja → el mismo trabajo te cuesta más._

**El v3 todavía no muestra relación clara con el esfuerzo: se mantiene el v2.**

| Modelo | ρ esfuerzo | IC 90 % | Días |
|---|--:|---|--:|
| Oficial v2 | -0,12 | -0,46 a 0,24 | 23 |
| Híbrido | -0,16 | -0,49 a 0,20 | 23 |
| v3 (en pruebas) | -0,16 | -0,49 a 0,20 | 23 |
| Decisión operativa | -0,14 | -0,47 a 0,22 | 23 |

- Días entrenados con predicción: 24; por encima del RPE máximo del día: 15.

## Recuperación: tendencias de 28 días

<details><summary>HRV, FC y sueño</summary>

![HRV](charts/hrv.svg)

![FC](charts/rhr.svg)

![Sueño](charts/sleep.svg)

</details>

## Acciones pendientes

- Registra en Intervals.icu fatiga, agujetas, estrés, ánimo y motivación (1 = mejor, 4 = peor).

## Fuerza (últimos 28 días)

<details><summary>Tabla y progresión</summary>

| Fecha | Ejercicio | Implemento | Carga máx. | Mejor serie | 1RM mín. | Volumen verificado | Series | RPE sesión |
|---|---|---|---|--:|--:|--:|--:|--:|
| 27/11 | press banca | barra | 80,0 kg con barra | 80 × 8 | 101,3 kg | 3.840 kg | 5/5 | 5,0 |
| 27/11 | press inclinado con mancuernas | mancuernas (par) | 60,0 kg total (2 × 30,0 kg) | 60 × 8 | 76,0 kg | 1.630 kg | 3/3 | 5,0 |
| 27/11 | front squat | barra | 125,0 kg con barra | 125 × 3 | 137,5 kg | 2.585 kg | 6/6 | 7,0 |
| 25/11 | sentadilla trasera | barra | 150,0 kg con barra | 140 × 6 | 168,0 kg | 6.290 kg | 8/8 | 6,0 |
| 25/11 | sentadilla péndulo | máquina de placas | 70,0 kg indicados en máquina | — | — | 1.940 kg | 4/4 | 6,0 |
| 25/11 | extensión de cuádriceps sentado unilateral | máquina de placas | 30,0 kg indicados en máquina | — | — | 1.125 kg | 3/3 | 6,0 |
| 25/11 | curl femoral tumbado | máquina de placas | 74,0 kg indicados en máquina | — | — | 2.384 kg | 4/4 | 6,0 |
| 25/11 | curl femoral de pie unilateral | máquina de placas | 30,0 kg indicados en máquina | — | — | 720 kg | 3/3 | 6,0 |
| 25/11 | sit-ups | peso corporal | peso corporal | — | — | — | —/4 | 6,0 |
| 25/11 | clean pull + hang power clean + power clean | barra | 75,0 kg con barra | 75 × 3 | 82,5 kg | 630 kg | 3/3 | 7,0 |
| 25/11 | power clean | barra | 90,0 kg con barra | 90 × 3 | 99,0 kg | 735 kg | 3/3 | 7,0 |
| 25/11 | push press | barra | 78,0 kg con barra | 78 × 5 | 91,0 kg | 1.115 kg | 3/3 | 7,0 |

_1RM mín. = Epley con tu mejor serie (kg × repeticiones, hasta 10). Si la serie no fue al fallo, tu 1RM real es igual o mayor: es un mínimo, no un máximo. No usa el RPE de la sesión._
_Volumen = kg × repeticiones de las series con carga conocida. No se comparan implementos distintos (barra, mancuernas, máquinas); las máquinas no son comparables con peso libre; el RPE es de la sesión, no de cada serie._

</details>

## Certificado

- **Identificador del informe:** `GR-2026-11-27-2247-c5ba8f`

<details><summary>Detalle del certificado</summary>

- **Ciclo:** 2026-11-27-2245 · datos sincronizados a las 22:46
- **Antigüedad:** fin del sueño hace 13,8 h ✓ · última HRV hace 13,8 h ✓ · última FC hace 2,1 h ✓ · último Body Battery hace 2,1 h ✓
- **Integridad:** coherencia experimental/oficial ✓ · sesiones con RPE 16/16 (+4 sin RPE por diseño: calentamiento/técnica)
- **Ejecución:** 0 franja(s) de Sync perdidas
- **Estado:** sin avisos · fuentes con huella SHA-256: 17 · entrega: no verificable desde los datos

</details>

_Herramienta de entrenamiento basada en tendencias personales; no es un diagnóstico médico. Generado 2026-11-27 22:47 · app 6.1.0 · modelo readiness-v3.2. Fuente única: `app/readiness_v3.json`._
