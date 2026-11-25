# Cierre diario · 25/11/2026

`GR-2026-11-25-2247-b9ba6a` · cita este identificador al reenviar el informe.

> ⚠️ Certificado con avisos: mediciones no recientes: heart_rate_live, body_battery_live.

> **Hoy: 🔴 rojo — Prioriza recuperar.** RPE ≤ 4 · volumen 0–50 %.
>
> **Por qué:** lo marca Híbrido Garmin + local (49); señales: Forma -110 % (riesgo_alto) · Sueño 7,2 h, puntuación 84, deuda 2,2 h en 3 noches.
>
> **Qué hacer:** Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.

## 🔴 Decisión: rojo — Prioriza recuperar

| RPE máximo | Volumen | HRV | FC reposo | Sueño | Garmin Readiness |
|--:|--:|--:|--:|--:|--:|
| 4 | 0–50 % | 71 ms | 50 lpm | 7,21 h | 20/100 |

<details><summary>Cómo se decide (modelos)</summary>

| Modelo | Puntuación | Zona | Papel |
|---|--:|---|---|
| Recuperación oficial | 88 | verde | oficial |
| Híbrido Garmin + local | 49 | rojo | salvaguarda |
| Modelo experimental | 78 | verde | sombra |
| Modelo de compatibilidad | 91 | verde | compatibilidad |
| Garmin Training Readiness | 20 | — | contexto |

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

Frente al informe GR-2026-11-25-1947-27e73d (25/11 19:47):
- Sesiones con RPE: 13 → 16.

## Balance del día

| Fecha | Tipo | Sesión | Min | Carga | FC media / máx. | RPE | sRPE |
|---|---|---|--:|--:|--:|--:|--:|
| 25/11 15:12 | Fuerza | Fuerza - pierna: sentadilla trasera, sentadilla péndulo, extensión de cuádriceps, curl femoral y sit-ups | 71 | 32 | 118 / 150 | 6,0 | 425 |
| 25/11 10:19 | Halterofilia | Halterofilia - complex clean pull + hang power clean + power clean / power clean 3x3 / push press 3x5 | 54 | 26 | 122 / 153 | 7,0 | 381 |
| 25/11 09:19 | Calentamiento | Calentamiento - WOD + WOD EMOM 28' - max cal SkiErg-remo / devil press / burpee box jump | 38 | 33 | 144 / 187 | 8,0 | 224 |

## Balance de la semana

- Carga 7 días: **215** en 11 sesiones (+39 % vs. semana previa).
- sRPE 7 días 1.722 · monotonía 0,68 · strain 1.169.
- Fatiga acumulada: ATL 32,3, CTL 15,4, TSB -16,9.

## Previsión orientativa para mañana

- Objetivo de sueño esta noche: **8,2 h** (necesidad + parte de la deuda de 2,2 h).
- Mañana turno **MT**.
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
| Oficial v2 | -0,13 | -0,47 a 0,25 | 22 |
| Híbrido | -0,15 | -0,49 a 0,22 | 22 |
| v3 (en pruebas) | -0,16 | -0,50 a 0,21 | 22 |
| Decisión operativa | -0,14 | -0,48 a 0,24 | 22 |

- Días entrenados con predicción: 23; por encima del RPE máximo del día: 14.

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
| 25/11 | sentadilla trasera | barra | 150,0 kg con barra | 140 × 6 | 168,0 kg | 6.290 kg | 8/8 | 6,0 |
| 25/11 | sentadilla péndulo | máquina de placas | 70,0 kg indicados en máquina | — | — | 1.940 kg | 4/4 | 6,0 |
| 25/11 | extensión de cuádriceps sentado unilateral | máquina de placas | 30,0 kg indicados en máquina | — | — | 1.125 kg | 3/3 | 6,0 |
| 25/11 | curl femoral tumbado | máquina de placas | 74,0 kg indicados en máquina | — | — | 2.384 kg | 4/4 | 6,0 |
| 25/11 | curl femoral de pie unilateral | máquina de placas | 30,0 kg indicados en máquina | — | — | 720 kg | 3/3 | 6,0 |
| 25/11 | sit-ups | peso corporal | peso corporal | — | — | — | —/4 | 6,0 |
| 25/11 | clean pull + hang power clean + power clean | barra | 75,0 kg con barra | 75 × 3 | 82,5 kg | 630 kg | 3/3 | 7,0 |
| 25/11 | power clean | barra | 90,0 kg con barra | 90 × 3 | 99,0 kg | 735 kg | 3/3 | 7,0 |
| 25/11 | push press | barra | 78,0 kg con barra | 78 × 5 | 91,0 kg | 1.115 kg | 3/3 | 7,0 |
| 23/11 | power snatch | barra | 60,0 kg con barra | 60 × 5 | 70,0 kg | 1.340 kg | 5/5 | 7,0 |
| 20/11 | chin up lastrado | sin especificar | 42,5 kg (unidad sin especificar) | — | — | 335 kg | 8/8 | — |
| 19/11 | DB split squat | mancuernas (par) | 65,0 kg total (2 × 32,5 kg) | 65 × 8 | 82,3 kg | 2.080 kg | 4/4 | 6,0 |

_1RM mín. = Epley con tu mejor serie (kg × repeticiones, hasta 10). Si la serie no fue al fallo, tu 1RM real es igual o mayor: es un mínimo, no un máximo. No usa el RPE de la sesión._
_Volumen = kg × repeticiones de las series con carga conocida. No se comparan implementos distintos (barra, mancuernas, máquinas); las máquinas no son comparables con peso libre; el RPE es de la sesión, no de cada serie._

</details>

## Certificado

- **Identificador del informe:** `GR-2026-11-25-2247-b9ba6a`

<details><summary>Detalle del certificado</summary>

- **Ciclo:** 2026-11-25-2245 · datos sincronizados a las 22:46
- **Antigüedad:** fin del sueño hace 14,5 h ✓ · última HRV hace 14,6 h ✓ · última FC hace 3,2 h ! · último Body Battery hace 3,4 h !
- **Integridad:** coherencia experimental/oficial ✓ · sesiones con RPE 16/16 (+5 sin RPE por diseño: calentamiento/técnica)
- **Ejecución:** 0 franja(s) de Sync perdidas
- **Estado:** con avisos · fuentes con huella SHA-256: 17 · entrega: no verificable desde los datos

</details>

_Herramienta de entrenamiento basada en tendencias personales; no es un diagnóstico médico. Generado 2026-11-25 22:47 · app 6.1.0 · modelo readiness-v3.2. Fuente única: `app/readiness_v3.json`._
