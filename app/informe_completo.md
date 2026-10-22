# Garmin Recovery · Cierre matinal

Jueves, 22 de octubre de 2026 · 08:33 · `GR-2026-10-22-0833-481d3c`

```cards
Decisión|Entrenar con control|RPE máx. 7|yellow
Recuperación oficial|60/100|confianza high|yellow
HRV|51 ms|-11 % vs mediana|red
Sueño|6 h 23 min|puntuación 63|unavailable
FC en reposo|58 lpm|mediana 56|unavailable
Carga 7 días|7 sesiones|sRPE 793|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-22-0830 validado; 4 de 4 procesos finalizados correctamente.
- 🟡 **Recuperación:** 60/100 (oficial, confianza high). Híbrido: 67/100. **Decisión: Entrenar con control**, RPE máx. 7.
- 🌙 **Sueño:** 6 h 23 min, puntuación 63/100.
- ❤️ **Principal alerta:** HRV 51 ms, 10,5 % por debajo de tu mediana de 28 días; FC nocturna 66,6 lpm (4,1 sobre la mediana).
- 🏋️ **Qué hacer:** Mantén técnica y fuerza submáxima; reduce volumen un 20–30 % y evita series al fallo y WOD máximos.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-22-0830 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 08:33:14 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 89/100 (good) |

⚠️ Franjas de Sync sin ejecutar o recuperadas tarde: 10-21 08:30, 10-21 16:45, 10-21 22:45.

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-22 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-20 | 🟢 descarga correcta (2026-10-22) |
| Garmin · FC diurna y nocturna | 2026-10-22 | 🟢 al día |
| Garmin · estrés | 2026-10-22 | 🟢 al día |
| Garmin · Body Battery | 2026-10-22 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-22 | 🟢 al día |
| Garmin · sueño | 2026-10-22 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 51 ms | 57 ms | 26 |
| FC en reposo | 58 lpm | 56 lpm | 28 |
| FC nocturna | 66,6 lpm | 62,5 lpm | 27 |
| Duración del sueño | 6 h 23 min | 7 h 16 min | 27 |
| Puntuación de sueño | 63 | 77 | 25 |

Las referencias son medianas históricas, no objetivos.

La HRV está 11 % por debajo de su mediana; la FC en reposo está 2 lpm por encima.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🟡 60/100 | oficial |
| Híbrido Garmin + local | 🟡 67/100 | salvaguarda |
| Modelo experimental | 🟡 59/100 | sombra |
| Modelo de compatibilidad | 🟡 74/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 50/100 | contexto |
| Tiempo de recuperación Garmin | 0,0 h | contexto |
| Índice personal experimental | 46/100 | provisional |

**Qué ha cambiado desde ayer**

Modelo experimental: 44 → 59 (red → yellow). Cambios notables frente a ayer:

- HRV: 31 → 51 ms (favorable)
- FC en reposo: 61 → 58 lpm (favorable)
- FC nocturna: 75,8 → 66,6 lpm (favorable)
- Puntuación de sueño: 39 → 63 (favorable)
- Estrés medio: 58 → 28 (favorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 22 de octubre de 2026, 00:17 → 22 de octubre de 2026, 07:15.

| Dato | Valor |
|---|---|
| Duración efectiva | 6 h 23 min |
| Puntuación | 63/100 |
| Sueño profundo | 56 min |
| Sueño REM | 21 min |

El REM representa un 5 % y el sueño profundo un 15 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,0 |
| Recargo por deuda de las últimas 3 noches | +0,8 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,3 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 1,6 h |
| Deuda de 7 noches (siestas descontadas) | 7,1 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (2,9 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 73,8 lpm | 66,6 lpm |
| 3 días | 88,4 lpm | 67,1 lpm |
| 7 días | 84,2 lpm | 65,9 lpm |
| 28 días | 83,4 lpm | 63,5 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 26/28 días |
| Sueño | 27/28 días |
| Puntuación de sueño | 25/28 días |
| FC en reposo | 28/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 28, máximo 75.
- Body Battery: último valor 47/100, medido a las 07:21.
- Recuperación de FC a 1 min tras el ejercicio: 3 observaciones recientes, mediana 16,0 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 10 | 17 | 49,6 / 57,5 ms | **-7,9 ms** |
| Día anterior con turno de noche (TN) | 4 | 4 | — | datos insuficientes (mín. 5 y 5) |
| Noche anterior de menos de 6,5 h | 9 | 17 | 50,8 / 56,4 ms | **-5,6 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (56,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 2 | datos insuficientes (mín. 5) |
| 🟡 Amarillo | 1 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 2 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 20 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 7 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 7 |
| Días con actividad | 3 |
| RPE medio | 8,12 |
| Sesiones de RPE ≥ 8 | 3 |
| Minutos grabados (Garmin) | 183,4 min |
| sRPE por duración registrada | 794 |
| TRIMP | 155,2 |
| Carga de actividades (Intervals) | 95 |
| Volumen externo mínimo verificado | 6765 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 24 sesiones, RPE medio 7,33, TRIMP 539,4 y 616,7 minutos grabados.

### sRPE diario registrado

```
16 oct —             sin registro
17 oct —             sin registro
18 oct ████████████  491
19 oct █████         196
20 oct ███           106
21 oct —             sin registro
22 oct —             sin registro
```

El 18 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,7 · strain 531 (descriptores de contexto, sin umbral médico).

## 6. Fuerza, halterofilia y metcons

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
- **18 oct — Fuerza - pierna: sentadilla trasera, péndulo y femorales** · RPE 7,5 · volumen de barra cuantificado 5415 kg · FC media 113 / máx. 148 lpm · TRIMP 38
  Sentadilla trasera: 2x10 barra vacía (20 kg), 8x40, 8x70, 5x90, 3x110, 1x130, 1x150, 1x160, 1x170, 1x180, 1x185, 3x150, 8x110, 15x70 kg; volumen verificado 5.415 kg; RPE 9,5 de la repetición más pesada (185 kg), no de la sesión completa. Sentadilla péndulo 4x8 60 kg, RPE 7. Curl femoral tumbado 1x10 60 kg y 3x8 67 kg, RPE 6. Curl femoral unilateral de pie 4x10 con 42,5 kg en cada pierna, RPE 6. Cargas de máquina no…

RPE frente a FC: se marcan las sesiones cuyo esfuerzo relativo, ln(sRPE / carga de FC) frente a tu historial del mismo tipo, se aleja ±1,5 desviaciones robustas. Es descriptivo y no cambia la decisión del día.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Pecho (aislamiento) | — | — | 1 · 4 | — |
| Core | — | — | 1 · 0 | — |
| Bisagra de cadera | — | — | 1 · 2 | 0 (parcial) |
| Empuje horizontal | — | — | 4 · 16 | — |
| Flexión de rodilla | 2 · 12 | — | 4 · 24 | — |
| other | 1 · 0 | — | 1 · 0 | — |
| Sentadilla | 6 · 36 | 6.765 | 10 · 67 | 14.318 |
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

Turno: hoy MT, mañana TN.
- Señales adversas: HRV baja respecto a tu historial; FC nocturna elevada.

### Recomendaciones

1. **Entrenar con control** — Mantén técnica y fuerza submáxima; reduce volumen un 20–30 % y evita series al fallo y WOD máximos.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | HRV | HRV media de los últimos 7 días: 50 ms frente a una referencia de 58 ms (-14 %). | Baja la intensidad unos días, protege el sueño y reevalúa en una semana. |
| 2 | Sueño | Media de 7 noches: 7,9 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 7,1 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Recupera la deuda poco a poco: 30–45 min más cada noche, no una sola noche larga. |
| 3 | FC en reposo | FC en reposo de los últimos 7 días: 58,1 lpm frente a 55,0 de referencia (+3,1 lpm). | Vigila sueño y estrés; evita encadenar esfuerzos máximos. |

### Detalle por área

- 🔴 **HRV.** HRV media de los últimos 7 días: 50 ms frente a una referencia de 58 ms (-14 %). Una HRV sostenida por debajo de tu referencia suele acompañar a más fatiga o menos descanso.
- ⚠️ **FC en reposo.** FC en reposo de los últimos 7 días: 58,1 lpm frente a 55,0 de referencia (+3,1 lpm). Algo más alta que tu referencia.
- 🔴 **Sueño.** Media de 7 noches: 7,9 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 7,1 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:14) con una variación típica de ±43 min en 14 noches; 2 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 12 de 20 sesiones con RPE registrado fueron de RPE ≥ 8 (60 %); 4 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 47 ms tras sesión de RPE ≥ 8 (n=7) frente a 55 ms tras las demás (n=3); diferencia -8 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 4 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 28/09 | — | — | — |
| 05/10 | 9 | 5 | 1420 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 6 | 2 | 301 |

_«—»: semanas anteriores al inicio del historial de sesiones._

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 12/10) frente a la anterior (lunes 05/10). La semana en curso (4 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 05/10 | Sem. 12/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 51 (7 d) | 58 (6 d) | ✅ +7 ms | 49 (4 d) | `█▃█▁` |
| FC en reposo | 57,1 (7 d) | 56,6 (7 d) | ≈ −0,6 lpm | 57,8 (4 d) | `▁▆▅█` |
| Sueño | 7,1 (7 d) | 6,6 (7 d) | ≈ −0,5 h | 6,8 (4 d) | `▄█▁▄` |
| Puntuación de sueño | 73 (7 d) | 76 (5 d) | ≈ +3 | 62 (4 d) | `▃▇█▁` |
| Sesiones | 9 | 9 | ±0 | 6 |  |
| Días con actividad | 5 | 4 | −1 | 2 |  |
| sRPE total | 1420 | 1694 | +274 (+19 %) | 301 | `▁▇█▂` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| jue 22/10 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| vie 23/10 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| sáb 24/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| dom 25/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| lun 26/10 | free | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |
| mar 27/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| mié 28/10 | free | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |

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

Traza: cierre matinal · ciclo 2026-10-22-0830 · generado 22/10/2026 08:33 Europe/Madrid · certificado READY · sync_run_id 39734523531.
