# Garmin Recovery · Informe de tarde

Martes, 20 de octubre de 2026 · 16:48 · `GR-2026-10-20-1648-7f0c37`

```cards
Decisión|Listo para entrenar|RPE máx. 9|green
Recuperación oficial|80/100|confianza high|green
HRV|53 ms|-9 % vs mediana|yellow
Sueño|10 h 09 min|puntuación 82|unavailable
FC en reposo|59 lpm|mediana 56|unavailable
Carga 7 días|13 sesiones|sRPE 1670|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-20-1645 validado; 4 de 4 procesos finalizados correctamente.
- 🟢 **Recuperación:** 80/100 (oficial, confianza high). Híbrido: 85/100. **Decisión: Listo para entrenar**, RPE máx. 9.
- 🌙 **Sueño:** 10 h 09 min, puntuación 82/100.
- ❤️ **Principal alerta:** HRV 53 ms, 8,6 % por debajo de tu mediana de 28 días.
- 🏋️ **Qué hacer:** Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-20-1645 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 16:48:32 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 89/100 (good) |

⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: 10-19 16:45, 10-19 22:45, 10-20 08:30.

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-20 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-20 | 🟢 descarga correcta (2026-10-20) |
| Garmin · FC diurna y nocturna | 2026-10-20 | 🟢 al día |
| Garmin · estrés | 2026-10-20 | 🟢 al día |
| Garmin · Body Battery | 2026-10-20 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-20 | 🟢 al día |
| Garmin · sueño | 2026-10-20 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 53 ms | 58 ms | 24 |
| FC en reposo | 59 lpm | 56 lpm | 26 |
| FC nocturna | 62,6 lpm | 61,5 lpm | 25 |
| Duración del sueño | 10 h 09 min | 7 h 16 min | 25 |
| Puntuación de sueño | 82 | 77 | 23 |

Las referencias son medianas históricas, no objetivos.

La HRV está 9 % por debajo de su mediana; la FC en reposo está 3 lpm por encima.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🟢 80/100 | oficial |
| Híbrido Garmin + local | 🟢 85/100 | salvaguarda |
| Modelo experimental | 🟢 71/100 | sombra |
| Modelo de compatibilidad | 🟢 100/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 73/100 | contexto |
| Tiempo de recuperación Garmin | 3,6 h | contexto |
| Índice personal experimental | 87/100 | provisional |

**Qué ha cambiado desde ayer**

Modelo experimental: 72 → 71 (green → green). Cambios notables frente a ayer:

- HRV: 60 → 53 ms (desfavorable)
- FC en reposo: 53 → 59 lpm (desfavorable)
- FC nocturna: 59,6 → 62,6 lpm (desfavorable)
- Sueño: 5,1 → 10,2 h (favorable)
- Puntuación de sueño: 64 → 82 (favorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 19 de octubre de 2026, 23:30 → 20 de octubre de 2026, 10:09.

| Dato | Valor |
|---|---|
| Duración efectiva | 10 h 09 min |
| Puntuación | 82/100 |
| Sueño profundo | 1 h 33 min |
| Sueño REM | 2 h 03 min |

El REM representa un 20 % y el sueño profundo un 15 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,3 |
| Recargo por deuda de las últimas 3 noches | +1,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,8 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 2,4 h |
| Deuda de 7 noches (siestas descontadas) | 8,4 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (2,4 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 92,1 lpm | 62,6 lpm |
| 3 días | 79,1 lpm | 61,4 lpm |
| 7 días | 85,5 lpm | 64,1 lpm |
| 28 días | 83,0 lpm | 63,0 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 24/28 días |
| Sueño | 25/28 días |
| Puntuación de sueño | 23/28 días |
| FC en reposo | 26/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 27, máximo 98.
- Body Battery: último valor 52/100, medido a las 15:21.
- Recuperación de FC a 1 min tras el ejercicio: 3 observaciones recientes, mediana 16,0 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 9 | 16 | 51,7 / 57,9 ms | **-6,2 ms** |
| Día anterior con turno de noche (TN) | 4 | 4 | — | datos insuficientes (mín. 5 y 5) |
| Noche anterior de menos de 6,5 h | 8 | 16 | 50,8 / 57,9 ms | **-7,2 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (58,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 1 | datos insuficientes (mín. 5) |
| 🟡 Amarillo | 1 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 1 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 20 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 13 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 13 |
| Días con actividad | 4 |
| RPE medio | 6,27 |
| Sesiones de RPE ≥ 8 | 6 |
| Minutos grabados (Garmin) | 313,0 min |
| sRPE por duración registrada | 1671 |
| TRIMP | 296,4 |
| Carga de actividades (Intervals) | 182 |
| Volumen externo mínimo verificado | 6765 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 24 sesiones, RPE medio 6,43, TRIMP 539,4 y 616,7 minutos grabados.

### sRPE diario registrado

```
14 oct ████████████  695
15 oct ████          223
16 oct —             sin registro
17 oct —             sin registro
18 oct ████████      491
19 oct █████         261
20 oct —             sin registro
```

El 14 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,9 · strain 1587 (descriptores de contexto, sin umbral médico).

## 6. Fuerza, halterofilia y metcons

- **19 oct — Técnica - toes to bar** · RPE 1
  Técnica de toes to bar de 47 min. Series, repeticiones y progresiones no indicadas. RPE 1. Tiempo Garmin 47,7 min.
- **19 oct — EMOM 12 min - echo bike / squat clean** · RPE 9
  EMOM de 12 min según pizarra: 16 cal Echo Bike + máximas repeticiones de squat clean con 70 kg y 1 min de descanso; 4 rondas. Squat clean por ronda: 9, 6, 5 y 4 (total 24). RPE 9. Tiempo Garmin 11:49 min (en movimiento).
- **19 oct — Fuerza - power clean + squat clean y squat clean EMOM** · RPE 8 · volumen de barra cuantificado 1200 kg
  EMOM cada minuto (según pizarra: complex power clean + squat clean touch & go 2/2/1/1/1 y squat clean drop & go 2/2/1/1/1, 5 min cada uno). Complex: 2x60, 2x70, 1x80, 1x85, 1x90 kg; squat clean: 2x90, 2x95, 1x100, 1x105, 1x110 kg. RPE de la sesión 8. Tiempo Garmin 11,3 min.
- **19 oct — Calentamiento previo a power clean y squat clean** · RPE 1 · volumen de barra cuantificado 150 kg
  Calentamiento de 17 min previo al bloque de fuerza: ejercicios con barra vacía (sin desglose) y 5 min de complex power clean + squat clean, 3 series de 1 con 40, 50 y 60 kg. RPE 1. Tiempo Garmin 17,9 min.
- **18 oct — Fuerza - pierna: sentadilla trasera, péndulo y femorales** · RPE 7,5 · volumen de barra cuantificado 5415 kg
  Sentadilla trasera: 2x10 barra vacía (20 kg), 8x40, 8x70, 5x90, 3x110, 1x130, 1x150, 1x160, 1x170, 1x180, 1x185, 3x150, 8x110, 15x70 kg; volumen verificado 5.415 kg; RPE 9,5 de la repetición más pesada (185 kg), no de la sesión completa. Sentadilla péndulo 4x8 60 kg, RPE 7. Curl femoral tumbado 1x10 60 kg y 3x8 67 kg, RPE 6. Curl femoral unilateral de pie 4x10 con 42,5 kg en cada pierna, RPE 6. Cargas de máquina no…
- **15 oct — WOD parejas - 3 Rounds For Time** · RPE 8
  WOD parejas 3 RFT, 13:28 (cap 18:00; 4:32 antes). 3 rondas: 40 cal compartidas en SkiErg, remo y Assault Bike respectivamente; en cada ronda 20 burpees no jump no clap sincronizados + 20 dumbbell snatch sincronizados con 25 kg. Total por equipo: 120 cal compartidas, 60 burpees sync y 60 snatches sync. RPE 8. Garmin 10:03, 13:15, FC 144/176 lpm y 192 kcal; diferencia con tiempo oficial -13 s.
- **15 oct — Técnica - Handstand push-ups (semana 3)** · RPE 4
  HSPU técnica. Garmin 09:21, 29:22, FC media 108 lpm, máxima 143 lpm, 219 kcal. RPE 4 declarado posteriormente por el atleta (17/10/2026). Sesión independiente del WOD.
- **14 oct — WOD 2 - AMRAP 12 min V-sits / box jump / high pull** · RPE 9,5
  AMRAP 12': 15 V-sits + 20 box jumps + 20 kettlebell sumo deadlift high pull a 24 kg. Resultado 3 rondas completas + 35 repeticiones (200 reps en total), extras sin desglose confirmado. RPE 9,5.
- **14 oct — WOD 1 - AMRAP 12 min carrera / swing / sit-ups** · RPE 9
  AMRAP 12': 200 m carrera + 20 kettlebell swing americano 24 kg + 20 sit-ups. Resultado 4 rondas completas + 200 m carrera: 1000 m carrera, 80 swings, 80 sit-ups. RPE 9; 3 min descanso antes de WOD 2.
- **14 oct — Calentamiento previo al WOD** · RPE 4
  7 min 55 s de calentamiento Garmin antes de dos AMRAP de 12 min. RPE 4 declarado posteriormente por el atleta (17/10/2026); no atribuir el RPE del WOD.
- **14 oct — Halterofilia + sentadilla tempo** · RPE 8
  Halterofilia RPE 8. Barra vacía; preparación con 40/45/50 kg. 4 complejos 1 squat clean + 1 front squat + 1 split jerk: 55/60/65/70 kg EMOM. 5 complejos 2 squat cleans + 1 split jerk: 70/75/80/85/90 kg cada 2 min. Sentadilla trasera tempo 3 s bajada: calentamiento 60/80/90/100 kg (series exactas por carga pendientes); trabajo 3x4 a 100/110/120 kg cada 90 s, RPE 5. Garmin 54:59.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Pecho (aislamiento) | — | — | 1 · 4 | — |
| Core | — | — | 1 · 0 | — |
| Bisagra de cadera | — | — | 1 · 2 | 0 (parcial) |
| Empuje horizontal | — | — | 4 · 16 | — |
| Flexión de rodilla | 2 · 12 | — | 4 · 24 | — |
| Sentadilla | 5 · 32 | 6.765 | 9 · 63 | 14.318 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

**Progresión por ejercicio (barra)**

| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |
|---|---|---|---|---|
| fuerza - squat snatch emom 8 min | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| peso muerto | 2026-S41 | 170 kg × 5 | 198,3 kg | 1 |
| power clean + squat clean (complex 1+1) | 2026-S43 | 90 kg × 1 | 90 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |
| squat clean | 2026-S43 | 110 kg × 1 | 110 kg | 1 |

Diferencias entre las dos últimas semanas con datos: sentadilla trasera: 1RM mínimo +3,7 kg entre 2026-S41 y 2026-S42.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy sin dato, mañana sin dato.
- Señales favorables: duración del sueño igual o superior a tu referencia.

### Recomendaciones

1. **Listo para entrenar** — Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | Sueño | Media de 7 noches: 8,0 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 8,4 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Recupera la deuda poco a poco: 30–45 min más cada noche, no una sola noche larga. |
| 2 | Distribución de la intensidad | 11 de 22 sesiones con RPE registrado fueron de RPE ≥ 8 (50 %); 3 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 3 | Respuesta a las sesiones duras | HRV la mañana siguiente: 50 ms tras sesión de RPE ≥ 8 (n=6) frente a 55 ms tras las demás (n=3); diferencia -5 ms. | Tras un día muy duro, planifica el siguiente suave. |

### Detalle por área

- ✅ **HRV.** HRV media de los últimos 7 días: 57 ms frente a una referencia de 58 ms (-2 %). Estable respecto a tu referencia.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 57,7 lpm frente a 55,0 de referencia (+2,7 lpm). En línea con tu referencia.
- 🔴 **Sueño.** Media de 7 noches: 8,0 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 8,4 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:11) con una variación típica de ±43 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 11 de 22 sesiones con RPE registrado fueron de RPE ≥ 8 (50 %); 3 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 50 ms tras sesión de RPE ≥ 8 (n=6) frente a 55 ms tras las demás (n=3); diferencia -5 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 2 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1458 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 6 | 2 | 261 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 12/10) frente a la anterior (lunes 05/10). La semana en curso (2 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 05/10 | Sem. 12/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 51 (7 d) | 58 (6 d) | ✅ +7 ms | 56 (2 d) | `▇▁█▆` |
| FC en reposo | 57,1 (7 d) | 56,6 (7 d) | ≈ −0,6 lpm | 56,0 (2 d) | `▁█▆▄` |
| Sueño | 7,1 (7 d) | 6,6 (7 d) | ≈ −0,5 h | 7,6 (2 d) | `▂▄▁█` |
| Puntuación de sueño | 73 (7 d) | 76 (5 d) | ≈ +3 | 73 (2 d) | `▁▆█▆` |
| Sesiones | 9 | 9 | ±0 | 6 |  |
| Días con actividad | 5 | 4 | −1 | 2 |  |
| sRPE total | 1458 | 1694 | +236 (+16 %) | 261 | `▁▇█▂` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| mar 20/10 | free | 🟢 Suave / movilidad | ya has entrenado hoy |
| mié 21/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| jue 22/10 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| vie 23/10 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| sáb 24/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| dom 25/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| lun 26/10 | free | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |

Plan orientativo por reglas (máx. 3 sesiones con RPE ≥ 8 por semana, separadas ≥ 48 h, solo en días libres). Se recalcula en cada informe y la decisión del día manda sobre él.

### Reglas para los próximos 7 días

1. **Hoy:** respeta la decisión del día (Listo para entrenar, RPE máx. 9).
2. **Esfuerzos máximos:** como mucho 2–3 sesiones de RPE ≥ 8 en la semana y separadas ≥ 48 h.
3. **Sueño:** suma 30–45 min cada noche en lugar de una sola noche larga; antes de un turno de noche, siesta corta.
4. **Registro:** fatiga, agujetas y ánimo cada mañana en Intervals; RPE de cada sesión el mismo día.
5. **Reevaluación:** dentro de 7 días compara tu HRV media y tu FC en reposo con la referencia de 28 días.

_Los puntos 2 y 3 son criterios generales de entrenamiento y descanso, no una prescripción personalizada._

## Conclusión

Datos suficientes para evaluar la recuperación de hoy: la decisión es **🟢 Listo para entrenar**. No es un diagnóstico médico. Que el informe esté publicado no prueba que se haya leído una notificación.

---

Traza: informe de tarde · ciclo 2026-10-20-1645 · generado 20/10/2026 16:48 Europe/Madrid · certificado READY · sync_run_id 39442374603.
