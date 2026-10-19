# Garmin Recovery · Informe de tarde

Lunes, 19 de octubre de 2026 · 16:48 · `GR-2026-10-19-1648-0b8480`

```cards
Decisión|Entrenar con control|RPE máx. 7|yellow
Recuperación oficial|64/100|confianza high|yellow
HRV|60 ms|+3 % vs mediana|green
Sueño|5 h 07 min|puntuación 64|unavailable
FC en reposo|53 lpm|mediana 56|unavailable
Carga 7 días|9 sesiones|sRPE 1694|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-19-1645 validado; 4 de 4 procesos finalizados correctamente.
- 🟡 **Recuperación:** 64/100 (oficial, confianza high). Híbrido: 67/100. **Decisión: Entrenar con control**, RPE máx. 7.
- 🌙 **Sueño:** 5 h 07 min, puntuación 64/100.
- ❤️ **Principal alerta:** HRV 60 ms, 3,4 % por encima de tu mediana de 28 días.
- 🏋️ **Qué hacer:** Mantén técnica y fuerza submáxima; reduce volumen un 20–30 % y evita series al fallo y WOD máximos.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-19-1645 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 16:48:20 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 84/100 (usable) |

⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: 10-18 16:45, 10-18 22:45, 10-19 08:30.

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-19 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-18 | 🟢 descarga correcta (2026-10-19) |
| Garmin · FC diurna y nocturna | 2026-10-19 | 🟢 al día |
| Garmin · estrés | 2026-10-19 | 🟢 al día |
| Garmin · Body Battery | 2026-10-19 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-19 | 🟢 al día |
| Garmin · sueño | 2026-10-19 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 60 ms | 58 ms | 23 |
| FC en reposo | 53 lpm | 56 lpm | 25 |
| FC nocturna | 59,6 lpm | 62,0 lpm | 24 |
| Duración del sueño | 5 h 07 min | 7 h 19 min | 24 |
| Puntuación de sueño | 64 | 78 | 22 |

Las referencias son medianas históricas, no objetivos.

La HRV está 3 % por encima de su mediana; la FC en reposo está 3 lpm por debajo.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🟡 64/100 | oficial |
| Híbrido Garmin + local | 🟡 67/100 | salvaguarda |
| Modelo experimental | 🟢 72/100 | sombra |
| Modelo de compatibilidad | 🟡 74/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 54/100 | contexto |
| Tiempo de recuperación Garmin | 0,0 h | contexto |
| Índice personal experimental | 70/100 | provisional |

_Divergencia entre modelos:_ El modelo experimental (verde) es más permisivo que la decisión (ámbar); se aplica la más conservadora.

**Qué ha cambiado desde ayer**

Cambios respecto a ayer: El día anterior no tiene una medición completa.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 19 de octubre de 2026, 06:41 → 19 de octubre de 2026, 12:19.

| Dato | Valor |
|---|---|
| Duración efectiva | 5 h 07 min |
| Puntuación | 64/100 |
| Sueño profundo | 1 h 16 min |
| Sueño REM | 52 min |

El REM representa un 17 % y el sueño profundo un 25 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,5 |
| Recargo por deuda de las últimas 3 noches | +1,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **9,0 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 2,4 h |
| Deuda de 7 noches (siestas descontadas) | 8,4 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (2,4 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 72,6 lpm | 59,6 lpm |
| 3 días | 77,5 lpm | 63,4 lpm |
| 7 días | 86,1 lpm | 63,0 lpm |
| 28 días | 83,2 lpm | 63,0 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 23/28 días |
| Sueño | 24/28 días |
| Puntuación de sueño | 22/28 días |
| FC en reposo | 25/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 27, máximo 84.
- Body Battery: último valor 60/100, medido a las 12:15 (hace 4 h 33 min: no es una medición nueva).
- Recuperación de FC a 1 min tras el ejercicio: 2 observaciones recientes, mediana 17,5 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 8 | 16 | 51,5 / 57,9 ms | **-6,4 ms** |
| Día anterior con turno de noche (TN) | 4 | 4 | — | datos insuficientes (mín. 5 y 5) |
| Noche anterior de menos de 6,5 h | 7 | 16 | 50,4 / 57,9 ms | **-7,5 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (58,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 1 | datos insuficientes (mín. 5) |
| 🟡 Amarillo | 0 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 1 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 18 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 9 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 9 |
| Días con actividad | 4 |
| RPE medio | 7,22 |
| Sesiones de RPE ≥ 8 | 5 |
| Minutos grabados (Garmin) | 236,5 min |
| sRPE por duración registrada | 1694 |
| TRIMP | 226,6 |
| Carga de actividades (Intervals) | 142 |
| Volumen externo mínimo verificado | 5993 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 18 sesiones, RPE medio 6,81, TRIMP 422,5 y 498,8 minutos grabados.

### sRPE diario registrado

```
13 oct █████         285
14 oct ████████████  695
15 oct ████          223
16 oct —             sin registro
17 oct —             sin registro
18 oct ████████      491
19 oct —             sin registro
```

El 14 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 1,0 · strain 1626 (descriptores de contexto, sin umbral médico).

## 6. Fuerza, halterofilia y metcons

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
- **13 oct — WOD AMRAP 10 min - Hang power snatch / butterfly / wall balls** · RPE 9
  AMRAP 10': 5 hang power snatch 45 kg, 10 butterfly pull-ups, 15 wall balls 9 kg. 5 rondas + 5 snatch = 155 reps. RPE 9. Garmin 12:14.
- **13 oct — Fuerza - Squat snatch EMOM 8 min** · RPE 6 · volumen de barra cuantificado 578 kg
  EMOM 8': 2x30, 2x40, 2x45, 2x50, 1x55, 1x60, 1x65, 1x68 kg. 12 repeticiones, volumen 578 kg. RPE 6. Garmin 29:10.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Pecho (aislamiento) | — | — | 1 · 4 | — |
| Core | — | — | 1 · 0 | — |
| Bisagra de cadera | — | — | 1 · 2 | 0 (parcial) |
| Empuje horizontal | — | — | 4 · 16 | — |
| Flexión de rodilla | 2 · 12 | — | 4 · 24 | — |
| Sentadilla | 3 · 27 | 5.993 | 6 · 50 | 12.968 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

**Progresión por ejercicio (barra)**

| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |
|---|---|---|---|---|
| fuerza - squat snatch emom 8 min | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| peso muerto | 2026-S41 | 170 kg × 5 | 198,3 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |

Diferencias entre las dos últimas semanas con datos: sentadilla trasera: 1RM mínimo +3,7 kg entre 2026-S41 y 2026-S42.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy sin dato, mañana sin dato.
- Señales favorables: HRV en rango respecto a tu historial.

### Recomendaciones

1. **Entrenar con control** — Mantén técnica y fuerza submáxima; reduce volumen un 20–30 % y evita series al fallo y WOD máximos.
2. **Piernas.** Sentadilla trasera a RPE 9,5 el 18/10: evita otra sesión pesada de piernas hasta el 20/10 (margen orientativo de 48 h, sin validar). Tren superior, técnica o aeróbico suave sí encajan.
3. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
4. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | Sueño | Media de 7 noches: 7,8 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 8,4 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Recupera la deuda poco a poco: 30–45 min más cada noche, no una sola noche larga. |
| 2 | Distribución de la intensidad | 9 de 18 sesiones con RPE registrado fueron de RPE ≥ 8 (50 %); 3 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 3 | Respuesta a las sesiones duras | HRV la mañana siguiente: 49 ms tras sesión de RPE ≥ 8 (n=5) frente a 55 ms tras las demás (n=3); diferencia -6 ms. | Tras un día muy duro, planifica el siguiente suave. |

### Detalle por área

- ✅ **HRV.** HRV media de los últimos 7 días: 58 ms frente a una referencia de 58 ms (+1 %). Estable respecto a tu referencia.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 56,6 lpm frente a 55,0 de referencia (+1,6 lpm). En línea con tu referencia.
- 🔴 **Sueño.** Media de 7 noches: 7,8 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 8,4 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:14) con una variación típica de ±41 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 9 de 18 sesiones con RPE registrado fueron de RPE ≥ 8 (50 %); 3 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 49 ms tras sesión de RPE ≥ 8 (n=5) frente a 55 ms tras las demás (n=3); diferencia -6 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; Fuerza - Squat snatch EMOM 8 min 68 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 0 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1458 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 0 | 0 | 0 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 12/10) frente a la anterior (lunes 05/10). La semana en curso (1 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 05/10 | Sem. 12/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 51 (7 d) | 58 (6 d) | ✅ +7 ms | 60 (1 d) | `▆▁▇█` |
| FC en reposo | 57,1 (7 d) | 56,6 (7 d) | ≈ −0,6 lpm | 53,0 (1 d) | `▄█▇▁` |
| Sueño | 7,1 (7 d) | 6,6 (7 d) | ≈ −0,5 h | 5,1 (1 d) | `▇█▆▁` |
| Puntuación de sueño | 73 (7 d) | 76 (5 d) | ≈ +3 | 64 (1 d) | `▂▆█▁` |
| Sesiones | 9 | 9 | ±0 | 0 |  |
| Días con actividad | 5 | 4 | −1 | 0 |  |
| sRPE total | 1458 | 1694 | +236 (+16 %) | 0 | `▁▇█▁` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| lun 19/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir · sin piernas pesadas hasta el 20/10 |
| mar 20/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| mié 21/10 | free | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |
| jue 22/10 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| vie 23/10 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| sáb 24/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| dom 25/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |

Plan orientativo por reglas (máx. 3 sesiones con RPE ≥ 8 por semana, separadas ≥ 48 h, solo en días libres). Se recalcula en cada informe y la decisión del día manda sobre él.

### Reglas para los próximos 7 días

1. **Hoy:** respeta la decisión del día (Entrenar con control, RPE máx. 7).
2. **Esfuerzos máximos:** como mucho 2–3 sesiones de RPE ≥ 8 en la semana y separadas ≥ 48 h.
3. **Sueño:** suma 30–45 min cada noche en lugar de una sola noche larga; antes de un turno de noche, siesta corta.
4. **Registro:** fatiga, agujetas y ánimo cada mañana en Intervals; RPE de cada sesión el mismo día.
5. **Reevaluación:** dentro de 7 días compara tu HRV media y tu FC en reposo con la referencia de 28 días.

_Los puntos 2 y 3 son criterios generales de entrenamiento y descanso, no una prescripción personalizada._

## Conclusión

Datos suficientes para evaluar la recuperación de hoy: la decisión es **🟡 Entrenar con control**. No es un diagnóstico médico. Que el informe esté publicado no prueba que se haya leído una notificación.

---

Traza: informe de tarde · ciclo 2026-10-19-1645 · generado 19/10/2026 16:48 Europe/Madrid · certificado READY · sync_run_id 39272051858.
