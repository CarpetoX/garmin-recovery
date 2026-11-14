# Garmin Recovery · Cierre matinal

Sábado, 14 de noviembre de 2026 · 08:34 · `GR-2026-11-14-0834-d59e7f`

```cards
Decisión|Pendiente de datos|RPE máx. 6|unavailable
Recuperación oficial|—/100|confianza low|unavailable
HRV|— ms|sin dato hoy|unavailable
Sueño|—|puntuación —|unavailable
FC en reposo|57 lpm|mediana 57|unavailable
Carga 7 días|11 sesiones|sRPE 1759|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-11-14-0830 validado; 4 de 4 procesos finalizados correctamente.
- ⚪ **Recuperación:** —/100 (oficial, confianza low). Híbrido: 74/100. **Decisión: Pendiente de datos**, RPE máx. 6.
- 🌙 **Sueño:** —, puntuación —/100.
- 🏋️ **Qué hacer:** Faltan datos de hoy: no se autoriza intensidad alta. Reevaluar tras sincronizar el sueño.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-11-14-0830 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 08:34:40 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | low |
| Calidad fisiológica de los datos | 74/100 (usable) |

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-11-14 | 🟢 al día |
| Intervals.icu · actividades | 2026-11-13 | 🟢 descarga correcta (2026-11-14) |
| Garmin · FC diurna y nocturna | 2026-11-14 | 🟢 al día |
| Garmin · estrés | 2026-11-14 | 🟢 al día |
| Garmin · Body Battery | 2026-11-14 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-11-14 | 🟢 al día |
| Garmin · sueño | 2026-11-13 | 🟠 1 día atrasado |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | — | 51 ms | 28 |
| FC en reposo | 57 lpm | 57 lpm | 28 |
| FC nocturna | — | 63,0 lpm | 28 |
| Duración del sueño | — | 7 h 37 min | 28 |
| Puntuación de sueño | — | 77 | 28 |

Las referencias son medianas históricas, no objetivos.

la FC en reposo coincide con su mediana.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | — | oficial |
| Híbrido Garmin + local | 🟡 74/100 | salvaguarda |
| Modelo experimental | — | sombra |
| Modelo de compatibilidad | 🟡 74/100 | compatibilidad |
| Garmin Training Readiness | — | contexto |
| Tiempo de recuperación Garmin | — | contexto |
| Índice personal experimental | 62/100 | provisional |

**Qué ha cambiado frente a tu última noche comparable (12/11)**

Cambios notables frente a tu última noche comparable (12/11):

- FC en reposo: 55 → 57 lpm (desfavorable)
- Estrés medio: 34 → 19 (favorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 13 de noviembre de 2026, 08:45 → 13 de noviembre de 2026, 13:47.

| Dato | Valor |
|---|---|
| Duración efectiva | 4 h 50 min |
| Puntuación | 58/100 |
| Sueño profundo | 1 h 35 min |
| Sueño REM | 22 min |

El REM representa un 8 % y el sueño profundo un 33 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,1 |
| Recargo por deuda de las últimas 3 noches | +1,0 |
| Siesta de hoy | sin dato |
| **Necesidad estimada esta noche** | **8,6 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 3,0 h |
| Deuda de 7 noches (siestas descontadas) | 4,7 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (3,0 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 62,7 lpm | — |
| 3 días | 78,9 lpm | 60,9 lpm |
| 7 días | 77,8 lpm | 61,8 lpm |
| 28 días | 80,4 lpm | 63,9 lpm |

\* La FC diurna de hoy es de un día parcial: no es FC en reposo.

Cobertura histórica fusionada (días con dato de 28):

| Indicador | Datos disponibles |
|---|---|
| HRV | 28/28 días |
| Sueño | 28/28 días |
| Puntuación de sueño | 28/28 días |
| FC en reposo | 28/28 días |

![FC en reposo y nocturna](charts/rhr.svg)

### Estrés y Body Battery

- Estrés medio: 19, máximo 42.
- Body Battery: último valor 48/100, medido a las 03:39 (hace 4 h 56 min: no es una medición nueva).
- Recuperación de FC a 1 min tras el ejercicio: 7 observaciones recientes, mediana 24,0 lpm.

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 24 | 25 | 48,8 / 57,0 ms | **-8,2 ms** |
| Día anterior con turno de noche (TN) | 9 | 8 | 50,8 / 64,1 ms | **-13,3 ms** |
| Noche anterior de menos de 6,5 h | 14 | 34 | 48,6 / 54,6 ms | **-6 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (53,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 8 | -2,1 ms |
| 🟡 Amarillo | 8 | -4,4 ms |
| 🔴 Rojo | 11 | +0,5 ms |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 13 nov. Descansos confirmados por ti: 1 en 7 días y 3 en 28. Un día sin registro y sin confirmar no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 11 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 11 |
| Días con actividad | 4 |
| RPE medio | 7,56 |
| Sesiones de RPE ≥ 8 | 4 |
| Minutos grabados (Garmin) | 332,9 min |
| sRPE por duración registrada | 1759 |
| TRIMP | 306,6 |
| Carga de actividades (Intervals) | 185 |
| Volumen externo mínimo verificado | 13.000 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 45 sesiones, RPE medio 7,45, TRIMP 1227,6 y 1419,6 minutos grabados.

### sRPE diario registrado

```
8 nov  —             sin registro
9 nov  ████          350
10 nov ████████████  1063
11 nov —             descanso
12 nov █             105
13 nov ███           241
14 nov —             sin registro
```

El 10 nov concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,66 · strain 1154 (descriptores de contexto, sin umbral médico).

### Carrera

| Fecha | km | Tiempo | Ritmo (min/km) | FC media / máx. | m/latido | Cadencia (ppm) | Desnivel + | RPE |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 28/10 | 8,02 | 41:13 | 5:09 | 157 / 177 | 1,24 | 163 | 54 m | 7,0 |
| 04/10 | 8,09 | 42:58 | 5:19 | 154 / 173 | 1,22 | 164 | 69 m | 8,0 |

Frente a la del 04/10 (8,09 km): 10 s/km más rápido, FC media +3 lpm; eficiencia parecida.

Metros por latido = velocidad (m/min) ÷ FC media. Comparaciones descriptivas entre carreras de distancia parecida (±25 %); el calor, el desnivel, el cansancio previo y el sensor también influyen.

## 6. Fuerza, halterofilia y metcons

- **13 nov — WOD EMOM 12' - chest to bar / double unders / V-sit** · RPE 8 · FC media 156 / máx. 179 lpm · TRIMP 22
  EMOM 12' (3 vueltas de 4 min): min 1 15 chest-to-bar, min 2 40 double unders, min 3 21 V-sits, min 4 descanso. Adaptado respecto a la pizarra (10 bar muscle-ups y 80 double unders). Totales: 45 C2B, 120 DU, 63 V-sits (no se indica ningún fallo). RPE 8 con muy malas sensaciones y mucha fatiga (día tras TN). Garmin 12,0 min.
- **13 nov — Fuerza - chin up lastrado 7x2 (EMOM)** · RPE 7 · FC media 111 / máx. 158 lpm · TRIMP 11
  Calentamiento (incluye 3 muscle-ups sueltos, sin enlazar) + chin up EMOM subiendo carga. Series previas 4x2: 3 con peso corporal y 1 con +5 kg. Trabajo 7x2 con lastre: +10, +15, +20, +25, +30, +35, +37,5 kg (máximo 2 reps con +37,5 kg). Reparto confirmado por el atleta. RPE 7. Garmin 20,7 min.
- **12 nov — WOD AMRAP 12' - Echo bike / HSPU / DB goblet lunges** · RPE 8 · FC media 158 / máx. 182 lpm · TRIMP 26 · ⚠️ RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste
  AMRAP 12': 500 m Echo bike + 9 handstand push-ups con kipping sobre esterilla, sin abmat + 15 DB goblet lunges con 22,5 kg. Resultado: 4 rondas completas + 500 m Echo bike + 3 HSPU. Totales: 2.500 m Echo bike, 39 HSPU, 60 goblet lunges (1.350 kg). RPE 8. Garmin 13,1 min.
- **12 nov — Fuerza - DB split squat / ring row pies elevados** · FC media 114 / máx. 155 lpm · TRIMP 20
  Calentamiento + fuerza cada 2' (cada ejercicio cada 2 min, 4 series): DB split squat 4x10 en total (5 por pierna) con 30 kg en cada mano (60 kg en total); feet elevated ring row 4x10 con pies a 60 cm. Volumen split squat 2.400 kg. Sin RPE: sesión no puntuada por decisión del atleta. Garmin 32,6 min.
- **10 nov — Fuerza - pecho: press banca, inclinados, aperturas, bíceps y abdominales** · RPE 7 · volumen de barra cuantificado 6030 kg · FC media 112 / máx. 140 lpm · TRIMP 39
  Press banca: 50x20 (barra vacía), 30x40, 23x60, 15x70, 8x80, 6x90, 4x95, 2x100, 8x80 kg; volumen de barra 6.030 kg sin la serie de barra vacía (7.030 kg con ella). Press inclinado mancuernas 1x8 con 31 kg y 3x8 con 33,5 kg por mancuerna. Press superinclinado isolateral 1x12 con 20 kg y 3x8 con 25 kg por lado. Aperturas en máquina sentado 2x10 a 45 kg y 2x10 a 50 kg. Curl bíceps máquina unilateral (por brazo): 15x10,…
- **10 nov — Fuerza - pierna: sentadilla trasera, sentadilla búlgara y peso muerto piernas rígidas** · RPE 6 · volumen de barra cuantificado 5720 kg · FC media 128 / máx. 161 lpm · TRIMP 43 · ⚠️ RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste
  Sentadilla trasera: 12x20 (barra vacía), 12x40, 10x60, 10x80, 10x100, 8x120, 8x130, 6x140 kg; volumen 5.720 kg sin barra vacía (5.960 con ella). Sentadilla búlgara 5x12 por pierna con peso corporal. Peso muerto piernas rígidas con mancuernas (kg por mancuerna): 12x25, 12x27,5, 12x30, 12x32,5; volumen 2.760 kg. RPE 6 de toda la sesión. Garmin 47,4 min.
- **10 nov — WOD E2MO2M - remo / sit-ups / swing americano / SkiErg / box jump over / wall ball** · RPE 9 · FC media 156 / máx. 176 lpm · TRIMP 60
  E2MO2M, 4 rondas de 4 intervalos de 2 min (32 min): 450 m remo; 20 sit-ups + 20 swing americano con kettlebell de 24 kg; 450 m SkiErg; 20 box jump over 60 cm + 20 wall balls 9 kg. Todo completado salvo el último SkiErg (400 m). Totales: 1.800 m remo, 1.750 m SkiErg, 80 sit-ups, 80 swing americano (1.920 kg), 80 box jump over, 80 wall balls. RPE 9. Garmin 32,2 min.
  Para comparar: parecido el 31 oct (AMRAP, RPE 7, 3 rondas). Orientativo.
- **10 nov — Calentamiento - previo al WOD** · FC media 120 / máx. 172 lpm · TRIMP 10
  Calentamiento sin desglose antes del WOD E2MO2M. Garmin 14,7 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **9 nov — Técnica - handstand push-ups en déficit** · FC media 108 / máx. 139 lpm · TRIMP 22
  Técnica de handstand push-ups: hasta 5 repeticiones en déficit de un disco de 20 kg + un disco de 5 kg (el déficit se mide en discos, no en cm; series no desglosadas). Sin RPE: sesión no puntuada por decisión del atleta. Garmin 42,2 min.
- **9 nov — WOD 20-15-10-5 - power snatch / chest to bar** · RPE 8,5 · FC media 157 / máx. 188 lpm · TRIMP 17
  20-15-10-5 de power snatch 35 kg + chest-to-bar pull-ups (time cap 10 min): completado en 7:59 con chest to bar; 50 snatches (1.750 kg) y 50 C2B. RPE 8,5. El WOD empieza hacia el segundo 40 de la grabación Garmin (grabación 8:51).
  Para comparar: parecido el 13 oct (AMRAP, RPE 9, 5 rondas + 5 reps · 155 reps en total). Orientativo.
- **9 nov — Fuerza - power snatch 5x5** · RPE 7 · volumen de barra cuantificado 1250 kg · FC media 128 / máx. 171 lpm · TRIMP 37
  Calentamiento + power snatch 5x5 cada 1'30": progresión barra vacía (20 kg) x5 y 30 kg x5; series de trabajo 5x40, 5x45, 5x50, 5x55, 5x60 kg (volumen de trabajo 1.250 kg). RPE 7. Garmin 39,2 min.

RPE frente a FC: se marcan las sesiones cuyo esfuerzo relativo, ln(sRPE / carga de FC) frente a tu historial del mismo tipo, se aleja ±1,5 desviaciones robustas. Es descriptivo y no cambia la decisión del día.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Bíceps (aislamiento) | 1 · 4 | — | 3 · 12 | — |
| Pecho (aislamiento) | 1 · 4 | — | 3 · 12 | — |
| Core | 1 · 4 | — | 3 · 12 | — |
| Bisagra de cadera | 1 · 4 | — | 1 · 4 | — |
| Tirón horizontal | 1 · 4 | — | 3 · 11 | — |
| Empuje horizontal | 3 · 16 | 6.030 | 9 · 46 | 16.420 |
| Flexión de rodilla | — | — | 4 · 24 | — |
| Halterofilia | 1 · 5 | 1.250 | 12 · 97 | 9.671 |
| Otros | — | — | 1 · 4 | — |
| Sentadilla | 3 · 21 | 5.720 | 11 · 65 | 17.610 |
| Tirón vertical | 1 · 7 | — | 5 · 25 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

**Progresión por ejercicio (barra)**

| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |
|---|---|---|---|---|
| clean pull | 2026-S45 | 90 kg × 1 | 90 kg | 1 |
| front squat | 2026-S44 | 70 kg × 1 | 70 kg | 1 |
| hang power clean | 2026-S45 | 90 kg × 1 | 90 kg | 1 |
| peso muerto | 2026-S41 | 170 kg × 5 | 198,3 kg | 1 |
| power clean | 2026-S45 | 90 kg × 1 | 90 kg | 1 |
| power clean + squat clean (complex 1+1) | 2026-S43 | 90 kg × 1 | 90 kg | 1 |
| power snatch | 2026-S46 | 60 kg × 5 | 70 kg | 1 |
| press banca | 2026-S44 | 90 kg × 6 | 108 kg | 1 |
| press banca | 2026-S45 | 90 kg × 6 | 108 kg | 1 |
| press banca | 2026-S46 | 90 kg × 6 | 108 kg | 1 |
| sentadilla con safety bar | 2026-S45 | 133 kg × 8 | 168,5 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |
| sentadilla trasera | 2026-S46 | 140 kg × 6 | 168 kg | 1 |
| split jerk | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| split jerk | 2026-S45 | 103 kg × 1 | 103 kg | 1 |
| squat clean | 2026-S43 | 110 kg × 1 | 110 kg | 1 |
| squat clean | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| squat clean | 2026-S45 | 103 kg × 1 | 103 kg | 1 |
| squat snatch | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| squat snatch | 2026-S44 | 75 kg × 1 | 75 kg | 1 |

Diferencias entre las dos últimas semanas con datos: press banca: 1RM mínimo 0 kg entre 2026-S45 y 2026-S46; sentadilla trasera: 1RM mínimo -17 kg entre 2026-S42 y 2026-S46; split jerk: 1RM mínimo +3 kg entre 2026-S44 y 2026-S45; squat clean: 1RM mínimo +3 kg entre 2026-S44 y 2026-S45; squat snatch: 1RM mínimo +7 kg entre 2026-S42 y 2026-S44.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy libre, mañana libre.

### Recomendaciones

1. **Pendiente de datos** — Faltan datos de hoy: no se autoriza intensidad alta. Reevaluar tras sincronizar el sueño.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | Sueño | Media de 7 noches: 8,2 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 4,7 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Adelanta la hora de acostarte 30–45 min esta semana, sobre todo antes de un turno. |
| 2 | Distribución de la intensidad | 14 de 29 sesiones con RPE registrado fueron de RPE ≥ 8 (48 %); 6 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 3 | Registro de sensaciones | Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. | Apunta cada mañana en Intervals 1–5 de fatiga, agujetas y ánimo (20 segundos). |

### Detalle por área

- ✅ **HRV.** HRV media de los últimos 7 días: 55 ms frente a una referencia de 51 ms (+8 %). Tendencia por encima de tu referencia: buena señal de recuperación.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 56,0 lpm frente a 57,0 de referencia (-1,0 lpm). En línea con tu referencia.
- ⚠️ **Sueño.** Media de 7 noches: 8,2 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 4,7 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 23:52) con una variación típica de ±24 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 14 de 29 sesiones con RPE registrado fueron de RPE ≥ 8 (48 %); 6 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ✅ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 49 ms tras sesión de RPE ≥ 8 (n=12) frente a 46 ms tras las demás (n=5); diferencia +2 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; sentadilla con safety bar 168 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 0 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 19/10 | 8 | 3 | 396 |
| 26/10 | 16 | 6 | 2195 |
| 02/11 | 9 | 4 | 1114 |
| 09/11 | 11 | 4 | 1759 |

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 02/11) frente a la anterior (lunes 26/10). La semana en curso (6 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 26/10 | Sem. 02/11 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 53 (7 d) | 50 (7 d) | ⚠️ −3 ms (−5 %) | 54 (5 d) | `▁▆▄█` |
| FC en reposo | 56,4 (7 d) | 57,4 (7 d) | ≈ +1,0 lpm | 56,0 (6 d) | `▇▃█▁` |
| Sueño | 7,7 (7 d) | 7,4 (7 d) | ≈ −0,3 h | 7,5 (5 d) | `▁█▆▇` |
| Puntuación de sueño | 73 (7 d) | 73 (7 d) | ≈ −1 | 78 (5 d) | `▁▆▆█` |
| Sesiones | 16 | 9 | −7 | 11 |  |
| Días con actividad | 6 | 4 | −2 | 4 |  |
| sRPE total | 2195 | 1114 | −1081 (−49 %) | 1759 | `▁█▄▆` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| sáb 14/11 | libre | 🟢 Suave / movilidad | la decisión de hoy limita la intensidad |
| dom 15/11 | libre | 🟡 Moderada | día libre; ya hay 3 sesiones duras en los últimos 7 días |
| lun 16/11 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| mar 17/11 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| mié 18/11 | tras TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| jue 19/11 | libre | 🔥 Exigente | día libre con margen para una sesión exigente |
| vie 20/11 | libre | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |

Plan orientativo por reglas (máx. 3 sesiones con RPE ≥ 8 por semana, separadas ≥ 48 h, solo en días libres). Se recalcula en cada informe y la decisión del día manda sobre él.

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

Traza: cierre matinal · ciclo 2026-11-14-0830 · generado 14/11/2026 08:34 Europe/Madrid · certificado READY · sync_run_id 43571631290.
