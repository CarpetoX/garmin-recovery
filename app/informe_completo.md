# Garmin Recovery · Cierre matinal

Domingo, 18 de octubre de 2026 · 11:58 · `GR-2026-10-18-1158-5bdf6d`

```cards
Decisión|Listo para entrenar|RPE máx. 9|green
Recuperación v2|88/100|confianza high|green
HRV|69 ms|+21 % vs mediana|green
Sueño|7 h 50 min|puntuación 87|unavailable
FC en reposo|56 lpm|mediana 56|unavailable
Carga 7 días|9 sesiones|sRPE 1203|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-18-0830-post-sleep validado; 4 de 4 procesos finalizados correctamente.
- 🟢 **Recuperación:** 88/100 (v2, confianza high). Híbrido: 77/100. **Decisión: Listo para entrenar**, RPE máx. 9.
- 🌙 **Sueño:** 7 h 50 min, puntuación 87/100.
- ❤️ **Principal alerta:** HRV 69 ms, 21,1 % por encima de tu mediana de 28 días.
- 🏋️ **Qué hacer:** Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-18-0830-post-sleep |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 09:49:05 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 84/100 (usable) |

⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: 10-17 08:30, 10-17 16:45, 10-17 22:45, 10-18 08:30.

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-18 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-18 | 🟢 descarga correcta (2026-10-18) |
| Garmin · FC diurna y nocturna | 2026-10-18 | 🟢 al día |
| Garmin · estrés | 2026-10-18 | 🟢 al día |
| Garmin · Body Battery | 2026-10-18 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-18 | 🟢 al día |
| Garmin · sueño | 2026-10-18 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 69 ms | 57 ms | 22 |
| FC en reposo | 56 lpm | 56 lpm | 24 |
| FC nocturna | 61,2 lpm | 62,5 lpm | 23 |
| Duración del sueño | 7 h 50 min | 7 h 16 min | 23 |
| Puntuación de sueño | 87 | 77 | 21 |

Las referencias son medianas históricas, no objetivos.

La HRV está 21 % por encima de su mediana; la FC en reposo coincide con su mediana.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a v3](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación v2 (oficial) | 🟢 88/100 | oficial |
| Híbrido Garmin + local | 🟢 77/100 | salvaguarda |
| Disponibilidad v3 (en pruebas) | 🟢 77/100 | sombra |
| Modelo de compatibilidad | 🟢 100/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 59/100 | contexto |
| Tiempo de recuperación Garmin | 9,6 h | contexto |
| Índice personal experimental | 86/100 | provisional |

**Qué ha cambiado desde ayer**

Puntuación v3: 52 → 77 (yellow → green). Cambios notables frente a ayer:

- HRV: 46 → 69 ms (favorable)
- FC en reposo: 60 → 56 lpm (favorable)
- FC nocturna: 68,1 → 61,2 lpm (favorable)
- Puntuación de sueño: 62 → 87 (favorable)
- Estrés medio: 38 → 19 (favorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre v2 (oficial), híbrido y v3; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 18 de octubre de 2026, 01:02 → 18 de octubre de 2026, 09:00.

| Dato | Valor |
|---|---|
| Duración efectiva | 7 h 50 min |
| Puntuación | 87/100 |
| Sueño profundo | 52 min |
| Sueño REM | 1 h 51 min |

El REM representa un 24 % y el sueño profundo un 11 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,0 |
| Recargo por deuda de las últimas 3 noches | +0,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **7,5 h** |
| Deuda de 7 noches (siestas descontadas) | 0,7 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 86,7 lpm | 61,2 lpm |
| 3 días | 85,5 lpm | 66,3 lpm |
| 7 días | 85,2 lpm | 62,7 lpm |
| 28 días | 83,3 lpm | 63,2 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 22/28 días |
| Sueño | 23/28 días |
| Puntuación de sueño | 21/28 días |
| FC en reposo | 24/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 19, máximo 81.
- Body Battery: último valor 59/100, medido a las 11:48.
- Recuperación de FC a 1 min tras el ejercicio: 2 observaciones recientes, mediana 17,5 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 7 | 16 | 50,3 / 57,9 ms | **-7,6 ms** |
| Día anterior con turno de noche (TN) | 3 | 4 | — | datos insuficientes (mín. 5 y 5) |
| Noche anterior de menos de 6,5 h | 7 | 15 | 50,4 / 57,8 ms | **-7,4 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (58,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 0 | datos insuficientes (mín. 5) |
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
| Días con actividad | 3 |
| RPE medio | 7,19 |
| Sesiones de RPE ≥ 8 | 5 |
| Minutos grabados (Garmin) | 236,5 min |
| sRPE por duración registrada | 1203 |
| TRIMP | 226,6 |
| Carga de actividades (Intervals) | 142 |
| Volumen externo mínimo verificado | 578 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 18 sesiones, RPE medio 6,76, TRIMP 422,5 y 498,8 minutos grabados.

### sRPE diario registrado

```
12 oct —             sin registro
13 oct █████         285
14 oct ████████████  695
15 oct ████          223
16 oct —             sin registro
17 oct —             sin registro
18 oct —             sin registro
```

El 14 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,7 · strain 854 (descriptores de contexto, sin umbral médico).

## 6. Fuerza, halterofilia y metcons

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
| Flexión de rodilla | — | — | 2 · 12 | — |
| Sentadilla | 1 · 8 | 578 | 4 · 31 | 7.553 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy TN, mañana sin dato.
- Señales favorables: duración del sueño igual o superior a tu referencia; HRV en rango respecto a tu historial.

### Recomendaciones

1. **Listo para entrenar** — Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

![Progresión de fuerza](charts/strength.svg)

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | Distribución de la intensidad | 9 de 17 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 3 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 2 | Registro de sensaciones | Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. | Apunta cada mañana en Intervals 1–5 de fatiga, agujetas y ánimo (20 segundos). |

### Detalle por área

- ✅ **HRV.** HRV media de los últimos 7 días: 55 ms frente a una referencia de 58 ms (-4 %). Estable respecto a tu referencia.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 56,6 lpm frente a 55,5 de referencia (+1,1 lpm). En línea con tu referencia.
- ✅ **Sueño.** Media de 7 noches: 7,8 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 0,7 h (siestas registradas descontadas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:14) con una variación típica de ±41 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 9 de 17 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 3 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ℹ️ **Respuesta a las sesiones duras.** Datos insuficientes: 5 días tras sesión dura y 2 tras otras (hacen falta 3 de cada). Sin más días no se puede ver cómo responde tu HRV.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 181 kg; Fuerza - Squat snatch EMOM 8 min 68 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 1 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 21/09 | — | — | — |
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1458 |
| 12/10 | 9 | 4 | 1203 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 05/10) frente a la anterior (lunes 28/09). La semana en curso (7 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 28/09 | Sem. 05/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 58 (7 d) | 51 (7 d) | ⚠️ −6 ms (−11 %) | 58 (6 d) | `·▇▁█` |
| FC en reposo | 55,0 (7 d) | 57,1 (7 d) | ⚠️ +2,1 lpm | 56,6 (7 d) | `·▁█▆` |
| Sueño | 6,8 (7 d) | 7,1 (7 d) | ≈ +0,3 h | 6,6 (7 d) | `·▄█▁` |
| Puntuación de sueño | 66 (7 d) | 73 (7 d) | ✅ +8 | 76 (5 d) | `·▁▆█` |
| Carga (sesiones, sRPE) | — | — | no comparable | — | — |

_Carga sin comparar: una de las semanas es anterior al inicio del historial de sesiones. Una sesión sin registro no demuestra un día de descanso._

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

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

Traza: cierre matinal · ciclo 2026-10-18-0830-post-sleep · generado 18/10/2026 11:58 Europe/Madrid · certificado READY · sync_run_id 39109018293.
