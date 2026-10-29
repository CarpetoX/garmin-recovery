# Garmin Recovery · Cierre matinal

Jueves, 29 de octubre de 2026 · 08:33 · `GR-2026-10-29-0833-89bae5`

```cards
Decisión|Prioriza recuperar|RPE máx. 4|red
Recuperación oficial|39/100|confianza high|red
HRV|35 ms|-38 % vs mediana|red
Sueño|7 h 05 min|puntuación 41|unavailable
FC en reposo|60 lpm|mediana 56|unavailable
Carga 7 días|12 sesiones|sRPE 1966|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-29-0830 validado; 4 de 4 procesos finalizados correctamente.
- 🔴 **Recuperación:** 39/100 (oficial, confianza high). Híbrido: 32/100. **Decisión: Prioriza recuperar**, RPE máx. 4.
- 🌙 **Sueño:** 7 h 05 min, puntuación 41/100.
- ❤️ **Principal alerta:** HRV 35 ms, 37,5 % por debajo de tu mediana de 28 días; FC nocturna 70,6 lpm (8,4 sobre la mediana).
- 🏋️ **Qué hacer:** Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-29-0830 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 08:33:29 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 100/100 (good) |

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-29 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-28 | 🟢 descarga correcta (2026-10-29) |
| Garmin · FC diurna y nocturna | 2026-10-29 | 🟢 al día |
| Garmin · estrés | 2026-10-29 | 🟢 al día |
| Garmin · Body Battery | 2026-10-29 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-29 | 🟢 al día |
| Garmin · sueño | 2026-10-29 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 35 ms | 56 ms | 27 |
| FC en reposo | 60 lpm | 56 lpm | 28 |
| FC nocturna | 70,6 lpm | 62,2 lpm | 28 |
| Duración del sueño | 7 h 05 min | 7 h 25 min | 28 |
| Puntuación de sueño | 41 | 76 | 26 |

Las referencias son medianas históricas, no objetivos.

La HRV está 38 % por debajo de su mediana; la FC en reposo está 4 lpm por encima.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🔴 39/100 | oficial |
| Híbrido Garmin + local | 🔴 32/100 | salvaguarda |
| Modelo experimental | — | sombra |
| Modelo de compatibilidad | 🔴 49/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 1/100 | contexto |
| Tiempo de recuperación Garmin | 66,7 h | contexto |
| Índice personal experimental | 0/100 | provisional |

_Divergencia entre modelos:_ El modelo experimental (pendiente) es más permisivo que la decisión (rojo); se aplica la más conservadora.

**Qué ha cambiado desde ayer**

Modelo experimental: 68 → 56 (yellow → yellow). Cambios notables frente a ayer:

- HRV: 43 → 35 ms (desfavorable)
- FC nocturna: 65,7 → 70,6 lpm (desfavorable)
- Sueño: 8,6 → 7,1 h (desfavorable)
- Puntuación de sueño: 75 → 41 (desfavorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 29 de octubre de 2026, 00:07 → 29 de octubre de 2026, 08:10.

| Dato | Valor |
|---|---|
| Duración efectiva | 7 h 05 min |
| Puntuación | 41/100 |
| Sueño profundo | 30 min |
| Sueño REM | 0 min |

El REM representa un 0 % y el sueño profundo un 7 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,5 |
| Recargo por deuda de las últimas 3 noches | +0,2 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,2 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 0,4 h |
| Deuda de 7 noches (siestas descontadas) | 2,7 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (0,4 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 69,5 lpm | 70,6 lpm |
| 3 días | 95,3 lpm | 65,0 lpm |
| 7 días | 84,5 lpm | 65,1 lpm |
| 28 días | 83,4 lpm | 63,6 lpm |

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

- Estrés medio: 37, máximo 73.
- Body Battery: último valor 29/100, medido a las 08:18.
- Recuperación de FC a 1 min tras el ejercicio: 4 observaciones recientes, mediana 17,5 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 14 | 20 | 49,3 / 57,1 ms | **-7,8 ms** |
| Día anterior con turno de noche (TN) | 5 | 5 | 56,6 / 66,4 ms | **-9,8 ms** |
| Noche anterior de menos de 6,5 h | 11 | 22 | 48,9 / 56,2 ms | **-7,3 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (56,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 5 | -6,0 ms |
| 🟡 Amarillo | 4 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 3 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 28 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 12 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 12 |
| Días con actividad | 4 |
| RPE medio | 7,75 |
| Sesiones de RPE ≥ 8 | 4 |
| Minutos grabados (Garmin) | 382,5 min |
| sRPE por duración registrada | 1966 |
| TRIMP | 382,1 |
| Carga de actividades (Intervals) | 232 |
| Volumen externo mínimo verificado | 8268 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 36 sesiones, RPE medio 7,45, TRIMP 921,5 y 999,2 minutos grabados.

### sRPE diario registrado

```
23 oct █             94
24 oct —             sin registro
25 oct —             sin registro
26 oct ███████████   820
27 oct ██            123
28 oct ████████████  929
29 oct —             sin registro
```

El 28 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,69 · strain 1348 (descriptores de contexto, sin umbral médico).

### Carrera

| Fecha | km | Tiempo | Ritmo (min/km) | FC media / máx. | m/latido | Cadencia (ppm) | Desnivel + | RPE |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 28/10 | 8,02 | 41:13 | 5:09 | 157 / 177 | 1,24 | 163 | 54 m | 7,0 |
| 04/10 | 8,09 | 42:58 | 5:19 | 154 / 173 | 1,22 | 164 | 69 m | — |

Frente a la del 04/10 (8,09 km): 10 s/km más rápido, FC media +3 lpm; eficiencia parecida.

Metros por latido = velocidad (m/min) ÷ FC media. Comparaciones descriptivas entre carreras de distancia parecida (±25 %); el calor, el desnivel, el cansancio previo y el sensor también influyen.

## 6. Fuerza, halterofilia y metcons

- **28 oct — Carrera - 8 km** · RPE 7 · FC media 157 / máx. 177 lpm · TRIMP 77
  Carrera de 8 km (Garmin 8,02 km en 41,3 min, ritmo medio 5:09 min/km calculado). RPE 7. Cuarta sesión del día, tras el WOD y la halterofilia de la mañana.
- **28 oct — Halterofilia - complex squat clean + front squat + split jerk / complex 2 squat clean + s…** · RPE 7,5 · volumen de barra cuantificado 2529 kg · FC media 123 / máx. 153 lpm · TRIMP 41
  Halterofilia después del WOD. Calentamiento con barra vacía. Aproximación: 3 series del complex squat clean + front squat + split jerk con 40, 50 y 60 kg en 3 minutos. Complex squat clean + front squat + split jerk (4 x 1, cada 1'): 60, 65, 68 y 70 kg. Complex 2 squat clean + split jerk (3 x 1, cada 1'30"): 75, 80 y 85 kg. Complex squat clean + split jerk (3 x 1, cada 1'30"): 90, 95 y 100 kg. 36 repeticiones y 2.529…
- **28 oct — WOD E3MO3M x8 - SkiErg/Assault Bike / DB hang clean + S2OH / box jump** · RPE 9 · FC media 157 / máx. 192 lpm · TRIMP 46
  E3MO3M de 8 rondas (una cada 3'): 15 cal alternando SkiErg y Assault Bike según la ronda + 20 DB hang clean + shoulder to overhead con una mancuerna de 22,5 kg alternando brazos + 15 box jumps a 60 cm. 8 rondas completas (confirmado): 120 cal, 160 hang clean + S2OH y 120 box jumps. RPE 9. Garmin 24,6 min.
- **28 oct — Calentamiento - WOD E3MO3M** · FC media 122 / máx. 162 lpm · TRIMP 10
  Calentamiento para el WOD E3MO3M, sin desglose. Garmin 13,8 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **27 oct — WOD AMRAP 15 min - carrera / wall ball / pull-ups** · RPE 8 · FC media 157 / máx. 179 lpm · TRIMP 29
  AMRAP 15': 200 m carrera + 12 wall balls 9 kg + 9 pull-ups. Resultado 6 rondas + 200 m + 10 wall balls (1.400 m de carrera, 82 wall balls, 54 pull-ups). RPE 8. Garmin 15,4 min.
- **27 oct — Fuerza - DB split squat / ring row feet elevated** · FC media 115 / máx. 162 lpm · TRIMP 15
  Calentamiento + fuerza cada 2'30" x 3 series: DB split squat 3x12 (6 con cada pierna, confirmado) con 30 kg por mancuerna (60 kg en total) y ring row feet elevated 3x12 con peso corporal. Garmin 24,0 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta.
- **26 oct — Fuerza - pecho: press banca, inclinados, aperturas, bíceps y abdominales** · RPE 7 · volumen de barra cuantificado 4620 kg · FC media 109 / máx. 135 lpm · TRIMP 39
  Press banca: 30x20 (barra vacía), 15x40, 15x60, 10x60, 10x70, 8x80, 6x90, 8x80 kg; volumen de barra 4.620 kg sin la serie de barra vacía (5.220 kg con ella). Press inclinado mancuernas 2x8 con 31 kg y 2x7 con 33,5 kg por mancuerna. Press superinclinado isolateral 1x10 20 kg, 2x8 25 kg y 1x10 20 kg por lado. Aperturas en banco inclinado 1x10 y 3x8 con 16 kg por mancuerna. Curl bíceps máquina unilateral 1x8 10 kg y 3x…
- **26 oct — Técnica - toes to bar** · FC media 119 / máx. 160 lpm · TRIMP 36
  Técnica de toes to bar de 47 min. Series y repeticiones no indicadas. Garmin 47,1 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **26 oct — WOD AMRAP 12 min - squat snatch / burpee over bar / toes to bar** · RPE 8 · FC media 143 / máx. 176 lpm · TRIMP 28 · ⚠️ RPE alto para tu FC: te costó más de lo habitual en este tipo de sesión
  AMRAP 12': 6 squat snatch 50 kg + 9 burpees over the barbell + 12 toes to bar. Resultado 4 rondas + 6 squat snatch + 4 burpees = 118 repeticiones (30 snatch, 40 burpees, 48 T2B). RPE 8. Dictado como «emom» y con Garmin 12:10; Intervals registra 19,9 min (emparejado por orden: segunda actividad del día). Registrado como AMRAP según la pizarra.
- **26 oct — Fuerza - Squat snatch** · RPE 7 · volumen de barra cuantificado 1119 kg · FC media 125 / máx. 159 lpm · TRIMP 22
  Calentamiento general + halterofilia. Aproximación 5 min de barra vacía (20 kg) a 50 kg, sin desglose. EMOM 9' 3x3/3x2/3x1: 3x50, 3x55, 3x60, 2x65, 2x68, 2x70, 1x70, 1x73, 1x75 kg. 18 repeticiones, volumen 1.119 kg. RPE 7 de todo el bloque. Garmin 24,5 min.
- **23 oct — WOD AMRAP 10 min - deadlift / HSPU / box jump** · RPE 8,5 · FC media 149 / máx. 194 lpm · TRIMP 17
  AMRAP 10': 10 deadlift 80 kg + 10 handstand push-ups + 10 box jumps a 60 cm. Resultado 5 rondas + 2 deadlift = 152 repeticiones. 80 kg en todas las rondas. RPE 8,5. Garmin 11,1 min.
- **23 oct — Fuerza - chin up lastrado 4x5 + isometric pull up 4x10"** · FC media 114 / máx. 156 lpm · TRIMP 21
  Calentamiento + fuerza cada 1'30": chin up 4x5 con lastre de 5, 10, 15 y 15 kg; isometric pull up 4x10" con el mismo lastre que los chin up (5, 10, 15 y 15 kg). Tiempo Garmin 35,1 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta.

RPE frente a FC: se marcan las sesiones cuyo esfuerzo relativo, ln(sRPE / carga de FC) frente a tu historial del mismo tipo, se aleja ±1,5 desviaciones robustas. Es descriptivo y no cambia la decisión del día.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Bíceps (aislamiento) | 1 · 4 | — | 1 · 4 | — |
| Pecho (aislamiento) | 1 · 4 | — | 2 · 8 | — |
| Core | 1 · 4 | — | 2 · 8 | — |
| Bisagra de cadera | — | — | 1 · 4 | 0 (parcial) |
| Tirón horizontal | 1 · 3 | — | 2 · 7 | — |
| Empuje horizontal | 3 · 15 | 4.620 | 7 · 35 | 4.620 |
| Flexión de rodilla | — | — | 4 · 24 | — |
| Halterofilia | 3 · 35 | 3.235 | 7 · 56 | 5.163 |
| Sentadilla | 2 · 10 | 413 | 8 · 54 | 12.403 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |
| Tirón vertical | 2 · 8 | — | 2 · 8 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

**Progresión por ejercicio (barra)**

| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |
|---|---|---|---|---|
| front squat | 2026-S44 | 70 kg × 1 | 70 kg | 1 |
| peso muerto | 2026-S41 | 170 kg × 5 | 198,3 kg | 1 |
| power clean + squat clean (complex 1+1) | 2026-S43 | 90 kg × 1 | 90 kg | 1 |
| press banca | 2026-S44 | 90 kg × 6 | 108 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |
| split jerk | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| squat clean | 2026-S43 | 110 kg × 1 | 110 kg | 1 |
| squat clean | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| squat snatch | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| squat snatch | 2026-S44 | 75 kg × 1 | 75 kg | 1 |

Diferencias entre las dos últimas semanas con datos: sentadilla trasera: 1RM mínimo +3,7 kg entre 2026-S41 y 2026-S42; squat clean: 1RM mínimo -10 kg entre 2026-S43 y 2026-S44; squat snatch: 1RM mínimo +7 kg entre 2026-S42 y 2026-S44.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy TN (15–08), mañana libre tras la noche.
- Señales adversas: HRV baja respecto a tu historial; FC nocturna elevada; Training Readiness de Garmin bajo (1/100).

### Recomendaciones

1. **Prioriza recuperar** — Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | HRV | HRV media de los últimos 7 días: 46,8 ms frente a tu base de 56 ms (-16 %); tu rango normal es 51,9–60,4 ms. Es la misma media (logarítmica) que usa la puntuación. | Baja la intensidad unos días, protege el sueño y reevalúa en una semana. |
| 2 | Distribución de la intensidad | 16 de 28 sesiones con RPE registrado fueron de RPE ≥ 8 (57 %); 6 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |
| 3 | Respuesta a las sesiones duras | HRV la mañana siguiente: 48 ms tras sesión de RPE ≥ 8 (n=11) frente a 55 ms tras las demás (n=3); diferencia -7 ms. | Tras un día muy duro, planifica el siguiente suave. |

### Detalle por área

- 🔴 **HRV.** HRV media de los últimos 7 días: 46,8 ms frente a tu base de 56 ms (-16 %); tu rango normal es 51,9–60,4 ms. Es la misma media (logarítmica) que usa la puntuación. Una HRV sostenida por debajo de tu referencia suele acompañar a más fatiga o menos descanso.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 56,7 lpm frente a 57,0 de referencia (-0,3 lpm). En línea con tu referencia.
- ✅ **Sueño.** Media de 7 noches: 7,6 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 2,7 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:12) con una variación típica de ±62 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 16 de 28 sesiones con RPE registrado fueron de RPE ≥ 8 (57 %); 6 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 48 ms tras sesión de RPE ≥ 8 (n=11) frente a 55 ms tras las demás (n=3); diferencia -7 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 0 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 05/10 | 9 | 5 | 1420 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 8 | 3 | 396 |
| 26/10 | 10 | 3 | 1872 |

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 19/10) frente a la anterior (lunes 12/10). La semana en curso (4 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 12/10 | Sem. 19/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 58 (6 d) | 47 (7 d) | ⚠️ −11 ms | 57 (4 d) | `▄█▁▇` |
| FC en reposo | 56,6 (7 d) | 57,1 (7 d) | ≈ +0,6 lpm | 56,8 (4 d) | `█▁█▃` |
| Sueño | 6,6 (7 d) | 6,8 (7 d) | ≈ +0,2 h | 8,1 (4 d) | `▃▁▂█` |
| Puntuación de sueño | 76 (5 d) | 62 (7 d) | ⚠️ −14 | 75 (4 d) | `▇█▁▇` |
| Sesiones | 9 | 8 | −1 | 10 |  |
| Días con actividad | 4 | 3 | −1 | 3 |  |
| sRPE total | 1694 | 396 | −1298 (−77 %) | 1872 | `▆▇▁█` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| jue 29/10 | TN | 🟢 Suave / movilidad | la decisión de hoy limita la intensidad |
| vie 30/10 | tras TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| sáb 31/10 | libre | 🟡 Moderada | día libre; ya hay 3 sesiones duras en los últimos 7 días |
| dom 01/11 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| lun 02/11 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| mar 03/11 | tras TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| mié 04/11 | libre | 🔥 Exigente | día libre con margen para una sesión exigente |

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

Traza: cierre matinal · ciclo 2026-10-29-0830 · generado 29/10/2026 08:33 Europe/Madrid · certificado READY · sync_run_id 40836050839.
