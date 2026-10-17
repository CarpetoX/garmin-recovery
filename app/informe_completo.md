# Garmin Recovery · Cierre nocturno

Domingo, 18 de octubre de 2026 · 01:47 · `GR-2026-10-18-0147-00c66e`

```cards
Decisión|Pendiente de datos|RPE máx. 6|unavailable
Recuperación v2|—/100|confianza low|unavailable
HRV|— ms|sin dato hoy|unavailable
Sueño|—|puntuación —|unavailable
FC en reposo|— lpm|mediana 56|unavailable
Carga 7 días|8 sesiones|sRPE 1203|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-17-2245 validado; 4 de 4 procesos finalizados correctamente.
- ⚪ **Recuperación:** —/100 (v2, confianza low). Híbrido: 65/100. **Decisión: Pendiente de datos**, RPE máx. 6.
- 🌙 **Sueño:** —, puntuación —/100.
- 🏋️ **Qué hacer:** Faltan datos de hoy: no se autoriza intensidad alta. Reevaluar tras sincronizar el sueño.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-17-2245 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 22:48:02 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | low |
| Calidad fisiológica de los datos | 74/100 (usable) |

⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: 10-17 08:30, 10-17 16:45, 10-17 22:45.

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | — | 57 ms | 22 |
| FC en reposo | — | 56 lpm | 24 |
| FC nocturna | — | 62,5 lpm | 23 |
| Duración del sueño | — | 7 h 16 min | 23 |
| Puntuación de sueño | — | 77 | 21 |

Las referencias son medianas históricas, no objetivos.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a v3](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación v2 (oficial) | — | oficial |
| Híbrido Garmin + local | 🟡 65/100 | salvaguarda |
| Disponibilidad v3 (en pruebas) | — | sombra |
| Modelo de compatibilidad | 🟡 74/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 50/100 | contexto |
| Tiempo de recuperación Garmin | 17,7 h | contexto |
| Índice personal experimental | 56/100 | provisional |

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre v2 (oficial), híbrido y v3; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 16 de octubre de 2026, 23:20 → 17 de octubre de 2026, 07:36.

| Dato | Valor |
|---|---|
| Duración efectiva | 7 h 50 min |
| Puntuación | 62/100 |
| Sueño profundo | 1 h 06 min |
| Sueño REM | 44 min |

El REM representa un 9 % y el sueño profundo un 14 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | — | — |
| 3 días | 85,5 lpm | 69,7 lpm |
| 7 días | 85,2 lpm | 63,0 lpm |
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

- Estrés medio: —, máximo —.
- Recuperación de FC a 1 min tras el ejercicio: 2 observaciones recientes, mediana 17,5 lpm (insuficientes para una tendencia robusta).

## 5. Rendimiento CrossFit

Última actividad registrada: 15 oct. Un día sin registro no demuestra que fuera de descanso.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 8 |
| Días con actividad | 3 |
| RPE medio | 7,19 |
| Sesiones de RPE ≥ 8 | 5 |
| Minutos grabados (Garmin) | 171,0 min |
| sRPE por duración registrada | 1203 |
| TRIMP | 188,3 |
| Carga de actividades (Intervals) | 118 |
| Volumen externo mínimo verificado | 578 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 17 sesiones, RPE medio 6,76, TRIMP 384,2 y 433,3 minutos grabados.

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

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy TN, mañana sin dato.

### Recomendaciones

1. **Pendiente de datos** — Faltan datos de hoy: no se autoriza intensidad alta. Reevaluar tras sincronizar el sueño.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

![Progresión de fuerza](charts/strength.svg)

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | HRV | HRV media de los últimos 7 días: 53 ms frente a una referencia de 58 ms (-8 %). | Evita acumular días muy exigentes seguidos y vigila el sueño. |
| 2 | Distribución de la intensidad | 9 de 17 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 3 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 3 | Registro de sensaciones | Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. | Apunta cada mañana en Intervals 1–5 de fatiga, agujetas y ánimo (20 segundos). |

### Detalle por área

- ⚠️ **HRV.** HRV media de los últimos 7 días: 53 ms frente a una referencia de 58 ms (-8 %). Tendencia algo por debajo de tu referencia.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 57,0 lpm frente a 55,0 de referencia (+2,0 lpm). En línea con tu referencia.
- ✅ **Sueño.** Media de 7 noches: 7,8 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 0,7 h. El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:11) con una variación típica de ±41 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 9 de 17 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 3 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ℹ️ **Respuesta a las sesiones duras.** Datos insuficientes: 5 días tras sesión dura y 2 tras otras (hacen falta 3 de cada). Sin más días no se puede ver cómo responde tu HRV.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 181 kg; Fuerza - Squat snatch EMOM 8 min 68 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 0 sesiones de 28 días sin RPE y HRV con dato en 12 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 21/09 | — | — | — |
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1458 |
| 12/10 | 8 | 3 | 1203 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Reglas para los próximos 7 días

1. **Hoy:** respeta la decisión del día (Pendiente de datos, RPE máx. 6).
2. **Esfuerzos máximos:** como mucho 2–3 sesiones de RPE ≥ 8 en la semana y separadas ≥ 48 h.
3. **Sueño:** suma 30–45 min cada noche en lugar de una sola noche larga; antes de un turno de noche, siesta corta.
4. **Registro:** fatiga, agujetas y ánimo cada mañana en Intervals; RPE de cada sesión el mismo día.
5. **Reevaluación:** dentro de 7 días compara tu HRV media y tu FC en reposo con la referencia de 28 días.

_Los puntos 2 y 3 son criterios generales de entrenamiento y descanso, no una prescripción personalizada._

## Conclusión

Datos insuficientes para evaluar la recuperación de hoy: la decisión es **⚪ Pendiente de datos**. No es un diagnóstico médico. Que el informe esté publicado no prueba que se haya leído una notificación.

---

Traza: cierre nocturno · ciclo 2026-10-17-2245 · generado 18/10/2026 01:47 Europe/Madrid · certificado READY · sync_run_id 39068162128.
