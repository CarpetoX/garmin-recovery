# Garmin Recovery · Informe de tarde

Domingo, 25 de octubre de 2026 · 16:48 · `GR-2026-10-25-1648-3b4cf4`

```cards
Decisión|Prioriza recuperar|RPE máx. 4|red
Recuperación oficial|34/100|confianza high|red
HRV|19 ms|-66 % vs mediana|red
Sueño|7 h 38 min|puntuación 42|unavailable
FC en reposo|61 lpm|mediana 56|unavailable
Carga 7 días|8 sesiones|sRPE 396|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-25-1645 validado; 4 de 4 procesos finalizados correctamente.
- 🔴 **Recuperación:** 34/100 (oficial, confianza high). Híbrido: 37/100. **Decisión: Prioriza recuperar**, RPE máx. 4.
- 🌙 **Sueño:** 7 h 38 min, puntuación 42/100.
- ❤️ **Principal alerta:** HRV 19 ms, 66,1 % por debajo de tu mediana de 28 días; FC nocturna 79,4 lpm (17,7 sobre la mediana).
- 🏋️ **Qué hacer:** Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-25-1645 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 16:48:02 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 89/100 (good) |

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-25 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-23 | 🟢 descarga correcta (2026-10-25) |
| Garmin · FC diurna y nocturna | 2026-10-25 | 🟢 al día |
| Garmin · estrés | 2026-10-25 | 🟢 al día |
| Garmin · Body Battery | 2026-10-25 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-25 | 🟢 al día |
| Garmin · sueño | 2026-10-25 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 19 ms | 56 ms | 27 |
| FC en reposo | 61 lpm | 56 lpm | 28 |
| FC nocturna | 79,4 lpm | 61,7 lpm | 28 |
| Duración del sueño | 7 h 38 min | 7 h 16 min | 28 |
| Puntuación de sueño | 42 | 76 | 26 |

Las referencias son medianas históricas, no objetivos.

La HRV está 66 % por debajo de su mediana; la FC en reposo está 5 lpm por encima.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🔴 34/100 | oficial |
| Híbrido Garmin + local | 🔴 37/100 | salvaguarda |
| Modelo experimental | 🔴 47/100 | sombra |
| Modelo de compatibilidad | 🔴 49/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 25/100 | contexto |
| Tiempo de recuperación Garmin | 5,2 h | contexto |
| Índice personal experimental | 12/100 | provisional |

**Qué ha cambiado desde ayer**

Modelo experimental: 66 → 47 (yellow → red). Cambios notables frente a ayer:

- HRV: 51 → 19 ms (desfavorable)
- FC en reposo: 56 → 61 lpm (desfavorable)
- FC nocturna: 61,9 → 79,4 lpm (desfavorable)
- Sueño: 5,5 → 7,6 h (favorable)
- Puntuación de sueño: 60 → 42 (desfavorable)
- Estrés medio: 41 → 67 (desfavorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 25 de octubre de 2026, 03:33 → 25 de octubre de 2026, 11:55.

| Dato | Valor |
|---|---|
| Duración efectiva | 7 h 38 min |
| Puntuación | 42/100 |
| Sueño profundo | 1 h 28 min |
| Sueño REM | 7 min |

El REM representa un 2 % y el sueño profundo un 19 % del episodio.
La duración supera tu referencia, pero la puntuación queda por debajo: más horas no se acompañan de una recuperación igual de favorable.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,0 |
| Recargo por deuda de las últimas 3 noches | +1,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,5 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 2,3 h |
| Deuda de 7 noches (siestas descontadas) | 6,3 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (2,3 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 86,1 lpm | 79,4 lpm |
| 3 días | 80,3 lpm | 68,6 lpm |
| 7 días | 80,6 lpm | 66,9 lpm |
| 28 días | 83,3 lpm | 64,2 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 27/28 días |
| Sueño | 28/28 días |
| Puntuación de sueño | 26/28 días |
| FC en reposo | 28/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 67, máximo 99.
- Body Battery: último valor 8/100, medido a las 15:06 (hace 1 h 42 min: no es una medición nueva).
- Recuperación de FC a 1 min tras el ejercicio: 3 observaciones recientes, mediana 16,0 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 11 | 19 | 49,7 / 55,7 ms | **-6 ms** |
| Día anterior con turno de noche (TN) | 5 | 5 | 56,6 / 66,4 ms | **-9,8 ms** |
| Noche anterior de menos de 6,5 h | 11 | 18 | 48,9 / 56,1 ms | **-7,1 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (56,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 3 | datos insuficientes (mín. 5) |
| 🟡 Amarillo | 3 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 2 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 23 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 8 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 8 |
| Días con actividad | 3 |
| RPE medio | 8,38 |
| Sesiones de RPE ≥ 8 | 4 |
| Minutos grabados (Garmin) | 164,1 min |
| sRPE por duración registrada | 396 |
| TRIMP | 155,5 |
| Carga de actividades (Intervals) | 97 |
| Volumen externo mínimo verificado | 1350 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 26 sesiones, RPE medio 7,38, TRIMP 578,0 y 662,9 minutos grabados.

### sRPE diario registrado

```
19 oct ████████████  196
20 oct ██████        106
21 oct —             sin registro
22 oct —             sin registro
23 oct ██████        94
24 oct —             sin registro
25 oct —             sin registro
```

El 19 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,8 · strain 313 (descriptores de contexto, sin umbral médico).

## 6. Fuerza, halterofilia y metcons

- **23 oct — WOD AMRAP 10 min - deadlift / HSPU / box jump** · RPE 8,5 · FC media 149 / máx. 194 lpm · TRIMP 17
  AMRAP 10': 10 deadlift 80 kg + 10 handstand push-ups + 10 box jumps a 60 cm. Resultado 5 rondas + 2 deadlift = 152 repeticiones. 80 kg en todas las rondas. RPE 8,5. Garmin 11,1 min.
- **23 oct — Fuerza - chin up lastrado 4x5 + isometric pull up 4x10"** · FC media 114 / máx. 156 lpm · TRIMP 21
  Calentamiento + fuerza cada 1'30": chin up 4x5 con lastre de 5, 10, 15 y 15 kg; isometric pull up 4x10" con el mismo lastre que los chin up (5, 10, 15 y 15 kg). Tiempo Garmin 35,1 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta.
- **20 oct — WOD 5 Rounds For Time - wall ball / double unders / WB step up** · RPE 8 · FC media 159 / máx. 178 lpm · TRIMP 26 · ⚠️ RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste
  5 rondas por tiempo con time cap de 13 min (no completado): 3 rondas + 20 wall ball + 30 double unders. Wall ball y WB step up con 9 kg. Garmin 13,2 min. Actividad emparejada por duración con el segundo HIIT del día (el primero, de 16 min, sin dictar).
- **20 oct — Fuerza - EMOM 8 min: DB split squat / ring row pies elevados** · FC media 120 / máx. 151 lpm · TRIMP 11
  EMOM 8 min: DB split squat 4x10 por pierna con 22,5 kg por mano (45 kg en total) y ring row con pies elevados 4x10 a peso corporal, alternando los ejercicios minuto a minuto (confirmado). Garmin 16,1 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta (21/10/2026; antes figuraba RPE 1).
- **19 oct — Técnica - toes to bar** · FC media 118 / máx. 140 lpm · TRIMP 34
  Técnica de toes to bar de 47 min. Series, repeticiones y progresiones no indicadas. Tiempo Garmin 47,7 min. Sin RPE: sesión no puntuada por decisión del atleta (21/10/2026; antes figuraba RPE 1).
- **19 oct — EMOM 12 min - echo bike / squat clean** · RPE 9 · FC media 155 / máx. 186 lpm · TRIMP 22
  EMOM de 12 min según pizarra: 16 cal Echo Bike + máximas repeticiones de squat clean con 70 kg y 1 min de descanso; 4 rondas. Squat clean por ronda: 9, 6, 5 y 4 (total 24). RPE 9. Tiempo Garmin 11:49 min (en movimiento).
- **19 oct — Fuerza - power clean + squat clean y squat clean EMOM** · RPE 8 · volumen de barra cuantificado 1200 kg · FC media 142 / máx. 167 lpm · TRIMP 15
  EMOM cada minuto (según pizarra: complex power clean + squat clean touch & go 2/2/1/1/1 y squat clean drop & go 2/2/1/1/1, 5 min cada uno). Complex: 2x60, 2x70, 1x80, 1x85, 1x90 kg; squat clean: 2x90, 2x95, 1x100, 1x105, 1x110 kg. RPE de la sesión 8. Tiempo Garmin 11,3 min.
- **19 oct — Calentamiento previo a power clean y squat clean** · volumen de barra cuantificado 150 kg · FC media 105 / máx. 145 lpm · TRIMP 9
  Calentamiento de 17 min previo al bloque de fuerza: ejercicios con barra vacía (sin desglose) y 5 min de complex power clean + squat clean, 3 series de 1 con 40, 50 y 60 kg. Tiempo Garmin 17,9 min. Sin RPE: sesión no puntuada por decisión del atleta (21/10/2026; antes figuraba RPE 1).

RPE frente a FC: se marcan las sesiones cuyo esfuerzo relativo, ln(sRPE / carga de FC) frente a tu historial del mismo tipo, se aleja ±1,5 desviaciones robustas. Es descriptivo y no cambia la decisión del día.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Pecho (aislamiento) | — | — | 1 · 4 | — |
| Core | — | — | 1 · 0 | — |
| Bisagra de cadera | — | — | 1 · 2 | 0 (parcial) |
| Empuje horizontal | — | — | 4 · 16 | — |
| Flexión de rodilla | — | — | 4 · 24 | — |
| other | 3 · 4 | — | 3 · 4 | — |
| Sentadilla | 4 · 17 | 1.350 | 10 · 67 | 14.318 |
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
- Señales adversas: HRV baja respecto a tu historial; FC nocturna elevada; Training Readiness de Garmin bajo (25/100); Body Battery bajo (8/100).

### Recomendaciones

1. **Prioriza recuperar** — Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | HRV | HRV media de los últimos 7 días: 47 ms frente a una referencia de 59 ms (-21 %). | Baja la intensidad unos días, protege el sueño y reevalúa en una semana. |
| 2 | Sueño | Media de 7 noches: 7,9 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 6,3 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Adelanta la hora de acostarte 30–45 min esta semana, sobre todo antes de un turno. |
| 3 | Distribución de la intensidad | 13 de 21 sesiones con RPE registrado fueron de RPE ≥ 8 (62 %); 4 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |

### Detalle por área

- 🔴 **HRV.** HRV media de los últimos 7 días: 47 ms frente a una referencia de 59 ms (-21 %). Una HRV sostenida por debajo de tu referencia suele acompañar a más fatiga o menos descanso.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 57,6 lpm frente a 56,0 de referencia (+1,6 lpm). En línea con tu referencia.
- ⚠️ **Sueño.** Media de 7 noches: 7,9 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 6,3 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:28) con una variación típica de ±62 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 13 de 21 sesiones con RPE registrado fueron de RPE ≥ 8 (62 %); 4 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 48 ms tras sesión de RPE ≥ 8 (n=8) frente a 55 ms tras las demás (n=3); diferencia -7 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 5 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1420 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 8 | 3 | 396 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 12/10) frente a la anterior (lunes 05/10). La semana en curso (7 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 05/10 | Sem. 12/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 51 (7 d) | 58 (6 d) | ✅ +7 ms | 47 (7 d) | `█▄█▁` |
| FC en reposo | 57,1 (7 d) | 56,6 (7 d) | ≈ −0,6 lpm | 57,6 (7 d) | `▁▇▅█` |
| Sueño | 7,1 (7 d) | 6,6 (7 d) | ≈ −0,5 h | 6,8 (7 d) | `▄█▁▄` |
| Puntuación de sueño | 73 (7 d) | 76 (5 d) | ≈ +3 | 62 (7 d) | `▃▇█▁` |
| Sesiones | 9 | 9 | ±0 | 8 |  |
| Días con actividad | 5 | 4 | −1 | 3 |  |
| sRPE total | 1420 | 1694 | +274 (+19 %) | 396 | `▁▇█▃` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| dom 25/10 | free | 🟢 Suave / movilidad | la decisión de hoy limita la intensidad |
| lun 26/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| mar 27/10 | free | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |
| mié 28/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente (mañana TN: acuéstate pronto) |
| jue 29/10 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| vie 30/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| sáb 31/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |

Plan orientativo por reglas (máx. 3 sesiones con RPE ≥ 8 por semana, separadas ≥ 48 h, solo en días libres). Se recalcula en cada informe y la decisión del día manda sobre él.

### Reglas para los próximos 7 días

1. **Hoy:** respeta la decisión del día (Prioriza recuperar, RPE máx. 4).
2. **Esfuerzos máximos:** como mucho 2–3 sesiones de RPE ≥ 8 en la semana y separadas ≥ 48 h.
3. **Sueño:** suma 30–45 min cada noche en lugar de una sola noche larga; antes de un turno de noche, siesta corta.
4. **Registro:** fatiga, agujetas y ánimo cada mañana en Intervals; RPE de cada sesión el mismo día.
5. **Reevaluación:** dentro de 7 días compara tu HRV media y tu FC en reposo con la referencia de 28 días.

_Los puntos 2 y 3 son criterios generales de entrenamiento y descanso, no una prescripción personalizada._

## Conclusión

Datos suficientes para evaluar la recuperación de hoy: la decisión es **🔴 Prioriza recuperar**. No es un diagnóstico médico. Que el informe esté publicado no prueba que se haya leído una notificación.

---

Traza: informe de tarde · ciclo 2026-10-25-1645 · generado 25/10/2026 16:48 Europe/Madrid · certificado READY · sync_run_id 40208558443.
