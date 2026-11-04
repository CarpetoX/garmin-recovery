# Garmin Recovery · Informe de tarde

Miércoles, 4 de noviembre de 2026 · 17:32 · `GR-2026-11-04-1732-97c616`

```cards
Decisión|Prioriza recuperar|RPE máx. 4|red
Recuperación oficial|68/100|confianza high|yellow
HRV|44 ms|-14 % vs mediana|red
Sueño|9 h 06 min|puntuación 75|unavailable
FC en reposo|60 lpm|mediana 57|unavailable
Carga 7 días|14 sesiones|sRPE 1045|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-11-04-1645 validado; 4 de 4 procesos finalizados correctamente.
- 🔴 **Recuperación:** 68/100 (oficial, confianza high). Híbrido: 49/100. **Decisión: Prioriza recuperar**, RPE máx. 4.
- 🌙 **Sueño:** 9 h 06 min, puntuación 75/100.
- ❤️ **Principal alerta:** HRV 44 ms, 13,7 % por debajo de tu mediana de 28 días; FC nocturna 67,3 lpm (4,3 sobre la mediana).
- 🏋️ **Qué hacer:** Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-11-04-1645 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 16:48:32 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 100/100 (good) |

La calidad describe los datos disponibles, no el software. Incluye datos de un Sync posterior al ciclo (17:21), sin certificado de franja propio: sesiones, FC diurna y Body Battery pueden ser más recientes que el certificado.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-11-04 | 🟢 al día |
| Intervals.icu · actividades | 2026-11-04 | 🟢 descarga correcta (2026-11-04) |
| Garmin · FC diurna y nocturna | 2026-11-04 | 🟢 al día |
| Garmin · estrés | 2026-11-04 | 🟢 al día |
| Garmin · Body Battery | 2026-11-04 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-11-04 | 🟢 al día |
| Garmin · sueño | 2026-11-04 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 44 ms | 51 ms | 27 |
| FC en reposo | 60 lpm | 57 lpm | 28 |
| FC nocturna | 67,3 lpm | 63,0 lpm | 28 |
| Duración del sueño | 9 h 06 min | 7 h 26 min | 28 |
| Puntuación de sueño | 75 | 75 | 26 |

Las referencias son medianas históricas, no objetivos.

La HRV está 14 % por debajo de su mediana; la FC en reposo está 3 lpm por encima.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🟡 68/100 | oficial |
| Híbrido Garmin + local | 🔴 49/100 | salvaguarda |
| Modelo experimental | 🟡 68/100 | sombra |
| Modelo de compatibilidad | 🟡 74/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 1/100 | contexto |
| Tiempo de recuperación Garmin | 55,9 h | contexto |
| Índice personal experimental | 42/100 | provisional |

_Divergencia entre modelos:_ El modelo experimental (ámbar) es más permisivo que la decisión (rojo); se aplica la más conservadora.

**Qué ha cambiado frente a tu última noche comparable (02/11)**

Modelo experimental: 71 → 68 (green → yellow). Cambios notables frente a tu última noche comparable (02/11):

- HRV: 49 → 44 ms (desfavorable)
- FC en reposo: 57 → 60 lpm (desfavorable)
- FC nocturna: 63,3 → 67,3 lpm (desfavorable)
- Sueño: 7,5 → 9,1 h (favorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 3 de noviembre de 2026, 23:23 → 4 de noviembre de 2026, 08:46.

| Dato | Valor |
|---|---|
| Duración efectiva | 9 h 06 min |
| Puntuación | 75/100 |
| Sueño profundo | 1 h 17 min |
| Sueño REM | 2 h 01 min |

El REM representa un 22 % y el sueño profundo un 14 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,1 |
| Recargo por deuda de las últimas 3 noches | +1,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,6 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 2,4 h |
| Deuda de 7 noches (siestas descontadas) | 5,8 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (2,4 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 96,7 lpm | 67,3 lpm |
| 3 días | 82,0 lpm | 66,1 lpm |
| 7 días | 79,5 lpm | 66,2 lpm |
| 28 días | 82,3 lpm | 64,3 lpm |

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

- Estrés medio: 32, máximo 94.
- Body Battery: último valor 30/100, medido a las 16:57.
- Recuperación de FC a 1 min tras el ejercicio: 7 observaciones recientes, mediana 21,0 lpm.

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 19 | 21 | 48,2 / 56,7 ms | **-8,6 ms** |
| Día anterior con turno de noche (TN) | 7 | 6 | 51,0 / 63,5 ms | **-12,5 ms** |
| Noche anterior de menos de 6,5 h | 13 | 26 | 48,5 / 54,5 ms | **-6 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (54,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 5 | -4,0 ms |
| 🟡 Amarillo | 6 | -8,0 ms |
| 🔴 Rojo | 7 | -1,0 ms |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 4 nov. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 14 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 14 |
| Días con actividad | 6 |
| RPE medio | 6,81 |
| Sesiones de RPE ≥ 8 | 3 |
| Minutos grabados (Garmin) | 460,6 min |
| sRPE por duración registrada | 1045 |
| TRIMP | 349,4 |
| Carga de actividades (Intervals) | 221 |
| Volumen externo mínimo verificado | 9606 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 48 sesiones, RPE medio 7,38, TRIMP 1217,7 y 1403,4 minutos grabados.

### sRPE diario registrado

```
29 oct █             20
30 oct ██            88
31 oct █████         215
1 nov  —             sin registro
2 nov  ██            82
3 nov  ███           144
4 nov  ████████████  496
```

El 4 nov concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

Monotonía 0,88 · strain 922 (descriptores de contexto, sin umbral médico).

### Carrera

| Fecha | km | Tiempo | Ritmo (min/km) | FC media / máx. | m/latido | Cadencia (ppm) | Desnivel + | RPE |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 28/10 | 8,02 | 41:13 | 5:09 | 157 / 177 | 1,24 | 163 | 54 m | 7,0 |
| 04/10 | 8,09 | 42:58 | 5:19 | 154 / 173 | 1,22 | 164 | 69 m | — |

Frente a la del 04/10 (8,09 km): 10 s/km más rápido, FC media +3 lpm; eficiencia parecida.

Metros por latido = velocidad (m/min) ÷ FC media. Comparaciones descriptivas entre carreras de distancia parecida (±25 %); el calor, el desnivel, el cansancio previo y el sensor también influyen.

## 6. Fuerza, halterofilia y metcons

- **4 nov — Fuerza - pecho: press banca, inclinados, aperturas, bíceps y abdominales** · RPE 4 · volumen de barra cuantificado 5770 kg · FC media 103 / máx. 134 lpm · TRIMP 28
  Press banca: 40x20 (barra vacía), 20x40, 20x60, 15x60, 15x70, 8x80, 6x90, 8x80 kg; volumen de barra 5.770 kg sin la serie de barra vacía (6.570 kg con ella). Press inclinado mancuernas 1x8 con 31 kg y 3x8 con 33,5 kg por mancuerna. Press superinclinado isolateral 1x15 20 kg y 3x8 25 kg por lado. Aperturas en banco inclinado 4x10 con 16 kg por mancuerna. Curl bíceps máquina unilateral 1x15 10 kg y 3x8 15 kg por lado.…
- **4 nov — Halterofilia - complex squat clean + split jerk** · volumen de barra cuantificado 1961 kg · FC media 117 / máx. 151 lpm · TRIMP 43
  Calentamiento sin desglose. Complex 1 squat clean + 2 split jerk cada 1'30" (4 series): 60, 70, 75 y 80 kg. Complex 1 squat clean + 1 split jerk cada 2' (4 series): 80, 85, 90 y 95 kg. RM 1+1 en 15': 100 y 103 kg conseguidos, fallo en 105 kg. 24 repeticiones y 1.961 kg de volumen de trabajo. Garmin 70,3 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **4 nov — WOD 4 x AMRAP 6 min - swing americano / sumo deadlift high pull** · RPE 6,5 · FC media 148 / máx. 194 lpm · TRIMP 46
  4 x AMRAP 6' con 2' de descanso, acumulando rondas entre bloques: 20 cal (alternando assault bike y remo, empezando en bike) + 15 swing americano + 10 sumo deadlift high pull, ambos con 24 kg. 8 rondas + 10 cal de assault bike (90 cal bike, 80 cal remo, 120 swings, 80 sumo deadlift high pull). RPE 6,5 con sensación de fatiga. Garmin 31,3 min.
- **4 nov — Calentamiento - previo al WOD** · FC media 111 / máx. 146 lpm · TRIMP 8
  Calentamiento con los ejercicios del WOD y menos peso, sin contar repeticiones. Garmin 14,9 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **3 nov — WOD AMRAP 15 min - carrera / DB snatch / burpee over DB** · RPE 8,5 · FC media 152 / máx. 178 lpm · TRIMP 28
  AMRAP 15': 200 m carrera + 20 dumbbell snatch con 22,5 kg + 10 burpees over DB. Resultado: 5 rondas completas (1.000 m de carrera, 100 DB snatch, 50 burpees over DB); repeticiones extra tras la 5.ª ronda no indicadas. RPE 8,5. Garmin 16,9 min.
- **3 nov — Técnica - comba: double unders, crossover single unders y crossover double unders** · FC media 125 / máx. 161 lpm · TRIMP 23
  Calentamiento + técnica de comba: double unders, crossover single unders y crossover double unders. Primera vez que consigue crossover single unders y crossover double unders. Series y repeticiones no indicadas; los single unders de la pizarra no se mencionaron. Garmin 28,8 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **2 nov — Técnica - handstand push-up** · FC media 107 / máx. 139 lpm · TRIMP 24
  Técnica de handstand push-up, toda la sesión. Series y repeticiones no indicadas. Garmin 50,5 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **2 nov — Halterofilia - complex clean pull + hang power clean + power clean** · volumen de barra cuantificado 1875 kg · FC media 131 / máx. 177 lpm · TRIMP 43 · ⚠️ RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste
  Calentamiento y aproximación desde barra vacía hasta 60 kg, sin desglose. Complex 1+1+1 EMOM 4' (4 x 1): 60, 70, 75 y 80 kg. Mismo complex cada 1'15" (4 x 1): 80, 85, 85 y 90 kg. 24 repeticiones y 1.875 kg de volumen de trabajo. Tramo 0:00–32:30 de la actividad de Garmin. Sin RPE: sesión no puntuada por decisión del atleta.
- **2 nov — WOD 4 Rounds For Time - double under / med ball sit-up / hang power clean** · RPE 7,5
  4 RFT, time cap 11': 50 double unders + 20 sit-ups con balón 9 kg + 15 hang power clean 45 kg. No completado: 3 rondas + 31 double unders = 286 repeticiones (181 DU, 60 sit-ups, 45 HPC). RPE 7,5. Tramo 32:30–43:30 de la actividad de Garmin (confirmado por el atleta).
- **31 oct — WOD parejas AMRAP 14 min - carrera / farmer carry / burpee to plate** · RPE 8 · FC media 155 / máx. 170 lpm · TRIMP 25
  Parejas, AMRAP 14': 400 m carrera juntos + 160 m farmer carry con 32 kg en cada mano (64 kg total) a repartir + 40 burpees to plate a repartir. 2 rondas + 400 m + 160 m farmer + 10 burpees (1200 m carrera cada uno; pareja: 480 m farmer, 90 burpees). Reparto individual no indicado. RPE 8. Garmin 14,2 min.
- **31 oct — WOD parejas AMRAP 14 min - SkiErg / wall ball / sit-up** · RPE 7 · FC media 149 / máx. 172 lpm · TRIMP 22
  Parejas, AMRAP 14': 500 m SkiErg + 24 wall ball 9 kg + 24 sit-ups con balón 9 kg, todo a repartir. 3 rondas + 500 m SkiErg + 24 WB + 2 sit-ups (pareja: 2000 m ski, 96 WB, 74 sit-ups). Reparto individual no indicado. RPE 7. Garmin 14,5 min.
- **31 oct — Calentamiento - previo al WOD por parejas** · FC media 104 / máx. 145 lpm · TRIMP 9
  Calentamiento suave antes del WOD. Garmin 22,3 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **30 oct — WOD 4 Rounds For Time - DB snatch / step up DB / burpee over DB** · RPE 8 · FC media 157 / máx. 182 lpm · TRIMP 21
  4 RFT, time cap 10': 18 dumbbell snatch alternos 22,5 kg + 15 step ups con mancuerna de 22,5 kg a cajón de 60 cm + 12 burpees over DB. No completado: 3 rondas + 18 DB snatch al time cap = 153 repeticiones (72 snatch, 45 step ups, 36 burpees). RPE 8. Garmin 11,0 min.
- **30 oct — Fuerza - chin up lastrado 5x4 + isometric pull up 5x10"** · FC media 111 / máx. 146 lpm · TRIMP 14
  Calentamiento + fuerza. Aproximación chin up 4x2 con lastre de 5, 10, 15 y 20 kg. Series efectivas chin up 5x4 con lastre de 15, 15, 10, 5 y 10 kg, terminando cada serie con isometric pull up de 10" con el mismo lastre (confirmado). Garmin 24,7 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta.
- **29 oct — Técnica - handstand push-up déficit** · FC media 101 / máx. 179 lpm · TRIMP 16
  Técnica de handstand push-up progresando hasta HSPU en déficit con un disco de 20 y otro de 10 por lado. Minutos 0:00–40:20 de la actividad de Garmin (grabada junto al WOD). Sin RPE: sesión no puntuada por decisión del atleta.
- **29 oct — WOD 21-15-9 - push press 50 kg / butterfly pull-up** · RPE 5
  For Time, cap 9': 21 push press 50 kg + 18 butterfly pull-ups, 15 + 12, 9 + 6. Completado en 3:54 (oficial). 81 repeticiones (45 push press, 36 butterfly). Tramo 40:20–44:16 de la actividad de Garmin. RPE 5.
- **29 oct — Hito - primer bar muscle up**
  Primer bar muscle up conseguido: 4 en total, sin enlazar (singles). Hecho fuera del WOD y del resto del entrenamiento; misma actividad de Garmin, sin tramo propio. Sin RPE: no puntuado.

RPE frente a FC: se marcan las sesiones cuyo esfuerzo relativo, ln(sRPE / carga de FC) frente a tu historial del mismo tipo, se aleja ±1,5 desviaciones robustas. Es descriptivo y no cambia la decisión del día.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Bíceps (aislamiento) | 1 · 4 | — | 2 · 8 | — |
| Pecho (aislamiento) | 1 · 4 | — | 3 · 12 | — |
| Core | 1 · 4 | — | 3 · 12 | — |
| Bisagra de cadera | — | — | 1 · 4 | 0 (parcial) |
| Tirón horizontal | — | — | 2 · 7 | — |
| Empuje horizontal | 3 · 15 | 5.770 | 10 · 50 | 10.390 |
| Flexión de rodilla | — | — | 4 · 24 | — |
| Halterofilia | 5 · 44 | 3.836 | 12 · 100 | 8.999 |
| Sentadilla | — | — | 8 · 54 | 12.403 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |
| Tirón vertical | 2 · 10 | — | 4 · 18 | — |

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
| press banca | 2026-S44 | 90 kg × 6 | 108 kg | 1 |
| press banca | 2026-S45 | 90 kg × 6 | 108 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |
| split jerk | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| split jerk | 2026-S45 | 103 kg × 1 | 103 kg | 1 |
| squat clean | 2026-S43 | 110 kg × 1 | 110 kg | 1 |
| squat clean | 2026-S44 | 100 kg × 1 | 100 kg | 1 |
| squat clean | 2026-S45 | 103 kg × 1 | 103 kg | 1 |
| squat snatch | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| squat snatch | 2026-S44 | 75 kg × 1 | 75 kg | 1 |

Diferencias entre las dos últimas semanas con datos: press banca: 1RM mínimo 0 kg entre 2026-S44 y 2026-S45; sentadilla trasera: 1RM mínimo +3,7 kg entre 2026-S41 y 2026-S42; split jerk: 1RM mínimo +3 kg entre 2026-S44 y 2026-S45; squat clean: 1RM mínimo +3 kg entre 2026-S44 y 2026-S45; squat snatch: 1RM mínimo +7 kg entre 2026-S42 y 2026-S44.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy libre, mañana libre.
- Señales favorables: duración del sueño igual o superior a tu referencia.
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
| 1 | HRV | HRV media de los últimos 7 días: 43,4 ms frente a tu base de 56 ms (-22 %); tu rango normal es 50,7–61,8 ms. Es la misma media (logarítmica) que usa la puntuación. | Baja la intensidad unos días, protege el sueño y reevalúa en una semana. |
| 2 | Sueño | Media de 7 noches: 8,2 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 5,8 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Adelanta la hora de acostarte 30–45 min esta semana, sobre todo antes de un turno. |
| 3 | Distribución de la intensidad | 18 de 34 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 7 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |

### Detalle por área

- 🔴 **HRV.** HRV media de los últimos 7 días: 43,4 ms frente a tu base de 56 ms (-22 %); tu rango normal es 50,7–61,8 ms. Es la misma media (logarítmica) que usa la puntuación. Una HRV sostenida por debajo de tu referencia suele acompañar a más fatiga o menos descanso.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 57,9 lpm frente a 57,0 de referencia (+0,9 lpm). En línea con tu referencia.
- ⚠️ **Sueño.** Media de 7 noches: 8,2 h (necesidad configurada 7,5 h); 0 de 7 noches más de media hora por debajo; deuda acumulada 5,8 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:00) con una variación típica de ±63 min en 14 noches; 3 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 18 de 34 sesiones con RPE registrado fueron de RPE ≥ 8 (53 %); 7 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ✅ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 49 ms tras sesión de RPE ≥ 8 (n=13) frente a 48 ms tras las demás (n=5); diferencia +1 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 0 sesiones de 28 días sin RPE y HRV con dato en 14 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 8 | 3 | 396 |
| 26/10 | 16 | 6 | 2195 |
| 02/11 | 8 | 3 | 722 |

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 26/10) frente a la anterior (lunes 19/10). La semana en curso (3 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 19/10 | Sem. 26/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 47 (7 d) | 53 (7 d) | ✅ +6 ms (+13 %) | 44 (3 d) | `█▂▅▁` |
| FC en reposo | 57,1 (7 d) | 56,4 (7 d) | ≈ −0,7 lpm | 59,0 (3 d) | `▁▃▁█` |
| Sueño | 6,8 (7 d) | 7,7 (7 d) | ✅ +0,8 h | 7,2 (3 d) | `▁▂█▅` |
| Puntuación de sueño | 62 (7 d) | 73 (7 d) | ✅ +12 | 66 (3 d) | `█▁▇▃` |
| Sesiones | 8 | 16 | +8 | 8 |  |
| Días con actividad | 3 | 6 | +3 | 3 |  |
| sRPE total | 396 | 2195 | +1799 (+454 %) | 722 | `▆▁█▂` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| mié 04/11 | libre | 🟢 Suave / movilidad | ya has entrenado hoy |
| jue 05/11 | libre | 🟡 Moderada | día libre; ya hay 3 sesiones duras en los últimos 7 días |
| vie 06/11 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| sáb 07/11 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| dom 08/11 | tras TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| lun 09/11 | libre | 🔥 Exigente | día libre con margen para una sesión exigente |
| mar 10/11 | libre | 🟡 Moderada | día libre; sesión moderada para respetar el espaciado |

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

Traza: informe de tarde · ciclo 2026-11-04-1645 · generado 04/11/2026 17:32 Europe/Madrid · certificado READY · sync_run_id 41861302847.
