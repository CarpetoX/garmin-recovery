# Garmin Recovery · Informe de tarde

Martes, 27 de octubre de 2026 · 16:48 · `GR-2026-10-27-1648-a00393`

```cards
Decisión|Listo para entrenar|RPE máx. 9|green
Recuperación oficial|88/100|confianza high|green
HRV|65 ms|+16 % vs mediana|green
Sueño|8 h 14 min|puntuación 89|unavailable
FC en reposo|56 lpm|mediana 56|unavailable
Carga 7 días|8 sesiones|sRPE 914|unavailable
```

## Resumen ejecutivo

- 🟢 **Certificación:** ciclo 2026-10-27-1645 validado; 4 de 4 procesos finalizados correctamente.
- 🟢 **Recuperación:** 88/100 (oficial, confianza high). Híbrido: 87/100. **Decisión: Listo para entrenar**, RPE máx. 9.
- 🌙 **Sueño:** 8 h 14 min, puntuación 89/100.
- ❤️ **Principal alerta:** HRV 65 ms, 16,1 % por encima de tu mediana de 28 días.
- 🏋️ **Qué hacer:** Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.

## 1. Certificación y calidad

| Comprobación | Resultado |
|---|---|
| Ciclo | 2026-10-27-1645 |
| Estado del certificado | READY |
| Sync | Correcto |
| Heart Rate | Correcto |
| Advanced Analytics | Correcto |
| CrossFit Insights | Correcto (publicando en este mismo ciclo) |
| Certificado generado | 16:48:26 |
| Instantánea inmutable (SHA-256) | Disponible |
| Confianza de recuperación | high |
| Calidad fisiológica de los datos | 100/100 (good) |

La calidad describe los datos disponibles, no el software. No se han incorporado mediciones posteriores al ciclo.

### Fuentes de datos

| Fuente | Último dato | Estado |
|---|---|---|
| Intervals.icu · bienestar (HRV, FC reposo, sueño) | 2026-10-27 | 🟢 al día |
| Intervals.icu · actividades | 2026-10-27 | 🟢 descarga correcta (2026-10-27) |
| Garmin · FC diurna y nocturna | 2026-10-27 | 🟢 al día |
| Garmin · estrés | 2026-10-27 | 🟢 al día |
| Garmin · Body Battery | 2026-10-27 | 🟢 al día |
| Garmin · Training Readiness y tiempo de recuperación | 2026-10-27 | 🟢 al día |
| Garmin · sueño | 2026-10-27 | 🟢 al día |

_Un retraso de un día es normal a primera hora; se avisa por GitHub si Intervals falla tres veces seguidas._

## 2. Recuperación fisiológica

| Indicador | Hoy | Mediana fusionada 28 días | Días |
|---|---|---|---|
| HRV | 65 ms | 56 ms | 27 |
| FC en reposo | 56 lpm | 56 lpm | 28 |
| FC nocturna | 58,7 lpm | 62,2 lpm | 28 |
| Duración del sueño | 8 h 14 min | 7 h 18 min | 28 |
| Puntuación de sueño | 89 | 70 | 26 |

Las referencias son medianas históricas, no objetivos.

La HRV está 16 % por encima de su mediana; la FC en reposo coincide con su mediana.

![HRV nocturna con tu rango normal](charts/hrv.svg)

![Disponibilidad: oficial frente a experimental](charts/readiness.svg)

### Modelos de recuperación

| Modelo | Resultado | Papel |
|---|---|---|
| Recuperación oficial | 🟢 88/100 | oficial |
| Híbrido Garmin + local | 🟢 87/100 | salvaguarda |
| Modelo experimental | 🟢 78/100 | sombra |
| Modelo de compatibilidad | 🟢 100/100 | compatibilidad |
| Garmin Training Readiness | ⚪ 67/100 | contexto |
| Tiempo de recuperación Garmin | 10,1 h | contexto |
| Índice personal experimental | 97/100 | provisional |

**Qué ha cambiado desde ayer**

Modelo experimental: 76 → 78 (green → green). Cambios notables frente a ayer:

- HRV: 84 → 65 ms (desfavorable)
- FC en reposo: 51 → 56 lpm (desfavorable)

Son diferencias observadas, no causas.

Las puntuaciones no son equivalentes entre sí. La decisión es la zona más conservadora entre el modelo oficial, el híbrido y el experimental; un rojo prevalece. El índice personal es provisional y no es una medida clínica.

## 3. Sueño y recuperación nocturna

Episodio confirmado: 26 de octubre de 2026, 23:54 → 27 de octubre de 2026, 08:10.

| Dato | Valor |
|---|---|
| Duración efectiva | 8 h 14 min |
| Puntuación | 89/100 |
| Sueño profundo | 57 min |
| Sueño REM | 1 h 39 min |

El REM representa un 20 % y el sueño profundo un 12 % del episodio.

![Sueño por noche frente a tu necesidad](charts/sleep.svg)

![Sueño por fases](charts/sleep_stages.svg)

**Necesidad y deuda de sueño**

| Componente | Horas |
|---|---|
| Base configurada | 7,5 |
| Recargo por carga de ayer | +0,5 |
| Recargo por deuda de las últimas 3 noches | +0,0 |
| Siesta de hoy | −0,0 |
| **Necesidad estimada esta noche** | **8,0 h** |
| Deuda de las últimas 3 noches (siestas descontadas) | 0,0 h |
| Deuda de 7 noches (siestas descontadas) | 3,9 h |

Es una estimación heurística, no validada; los recargos tienen tope y no sustituyen tu percepción. Solo cuentan siestas registradas por Garmin. El modelo experimental usa solo las últimas 3 noches y no descuenta siestas: por eso su deuda (0,0 h) puede ser mayor que la de 3 noches de esta tabla.

No se incorporan siestas no confirmadas.

## 4. Frecuencia cardíaca y tendencias

| Ventana | FC diurna | FC nocturna |
|---|---|---|
| Hoy* | 102,1 lpm | 58,7 lpm |
| 3 días | 81,3 lpm | 64,9 lpm |
| 7 días | 79,6 lpm | 65,6 lpm |
| 28 días | 83,4 lpm | 64,0 lpm |

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

- Estrés medio: 18, máximo 96.
- Body Battery: último valor 54/100, medido a las 14:51 (hace 1 h 57 min: no es una medición nueva).
- Recuperación de FC a 1 min tras el ejercicio: 4 observaciones recientes, mediana 17,5 lpm (insuficientes para una tendencia robusta).

**Diario de correlaciones (HRV del día siguiente)**

| Factor | Con | Sin | HRV siguiente día (con / sin) | Diferencia |
|---|---|---|---|---|
| Día anterior con sesión registrada | 12 | 20 | 51,0 / 57,1 ms | **-6,1 ms** |
| Día anterior con turno de noche (TN) | 5 | 5 | 56,6 / 66,4 ms | **-9,8 ms** |
| Noche anterior de menos de 6,5 h | 11 | 20 | 48,9 / 57,9 ms | **-9 ms** |

Son asociaciones en tus propios datos de los últimos 90 días, sin causalidad ni prueba estadística; con pocos días pueden ser casualidad.

**Calibración de la zona del día**

HRV de la noche siguiente frente a tu mediana de 90 días (57,0 ms):

| Zona del día | Días | HRV siguiente noche vs mediana |
|---|---|---|
| 🟢 Verde | 4 | datos insuficientes (mín. 5) |
| 🟡 Amarillo | 3 | datos insuficientes (mín. 5) |
| 🔴 Rojo | 3 | datos insuficientes (mín. 5) |

Solo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales.

## 5. Rendimiento CrossFit

Última actividad registrada: 27 oct. Un día sin registro no demuestra que fuera de descanso.

Contraste Garmin ↔ Intervals: las 8 actividades de Garmin de los últimos 7 días constan también en Intervals.

![Sesiones de los últimos 14 días](charts/sessions.svg)

![RPE frente al máximo del día](charts/rpe.svg)

![Carga diaria, ATL y CTL](charts/load.svg)

### Últimos 7 días

| Métrica | Resultado |
|---|---|
| Sesiones registradas | 8 |
| Días con actividad | 2 |
| RPE medio | 7,62 |
| Sesiones de RPE ≥ 8 | 2 |
| Minutos grabados (Garmin) | 247,0 min |
| sRPE por duración registrada | 913 |
| TRIMP | 208,2 |
| Carga de actividades (Intervals) | 128 |
| Volumen externo mínimo verificado | 6339 kg |

El volumen es un mínimo cuantificable, no un tonelaje comparable entre barra, mancuernas y máquinas.

Últimos 28 días: 32 sesiones, RPE medio 7,38, TRIMP 747,6 y 863,7 minutos grabados.

### sRPE diario registrado

```
21 oct —             sin registro
22 oct —             sin registro
23 oct █             94
24 oct —             sin registro
25 oct —             sin registro
26 oct ████████████  820
27 oct —             sin registro
```

El 26 oct concentra la mayor carga sRPE de la semana. La relación con las señales de recuperación es descriptiva, no causal.

## 6. Fuerza, halterofilia y metcons

- **26 oct — Fuerza - pecho: press banca, inclinados, aperturas, bíceps y abdominales** · RPE 7 · volumen de barra cuantificado 5220 kg · FC media 109 / máx. 135 lpm · TRIMP 39
  Press banca: 30x20 (barra vacía), 15x40, 15x60, 10x60, 10x70, 8x80, 6x90, 8x80 kg; volumen de barra 5.220 kg. Press inclinado mancuernas 2x8 con 31 kg y 2x7 con 33,5 kg por mancuerna. Press superinclinado isolateral 1x10 20 kg, 2x8 25 kg y 1x10 20 kg por lado. Aperturas en banco inclinado 1x10 y 3x8 con 16 kg por mancuerna. Curl bíceps máquina unilateral 1x8 10 kg y 3x8 15 kg por lado. Isolateral y curl con ambos br…
- **26 oct — Técnica - toes to bar** · FC media 119 / máx. 160 lpm · TRIMP 36
  Técnica de toes to bar de 47 min. Series y repeticiones no indicadas. Garmin 47,1 min. Sin RPE: sesión no puntuada por decisión del atleta.
- **26 oct — WOD AMRAP 12 min - squat snatch / burpee over bar / toes to bar** · RPE 8 · FC media 143 / máx. 176 lpm · TRIMP 28
  AMRAP 12': 6 squat snatch 50 kg + 9 burpees over the barbell + 12 toes to bar. Resultado 4 rondas + 6 squat snatch + 4 burpees = 118 repeticiones (30 snatch, 40 burpees, 48 T2B). RPE 8. Dictado como «emom» y con Garmin 12:10; Intervals registra 19,9 min (emparejado por orden: segunda actividad del día). Registrado como AMRAP según la pizarra.
- **26 oct — Fuerza - Squat snatch** · RPE 7 · volumen de barra cuantificado 1119 kg · FC media 125 / máx. 159 lpm · TRIMP 22
  Calentamiento general + halterofilia. Aproximación 5 min de barra vacía (20 kg) a 50 kg, sin desglose. EMOM 9' 3x3/3x2/3x1: 3x50, 3x55, 3x60, 2x65, 2x68, 2x70, 1x70, 1x73, 1x75 kg. 18 repeticiones, volumen 1.119 kg. RPE 7 de todo el bloque. Garmin 24,5 min.
- **23 oct — WOD AMRAP 10 min - deadlift / HSPU / box jump** · RPE 8,5 · FC media 149 / máx. 194 lpm · TRIMP 17
  AMRAP 10': 10 deadlift 80 kg + 10 handstand push-ups + 10 box jumps a 60 cm. Resultado 5 rondas + 2 deadlift = 152 repeticiones. 80 kg en todas las rondas. RPE 8,5. Garmin 11,1 min.
- **23 oct — Fuerza - chin up lastrado 4x5 + isometric pull up 4x10"** · FC media 114 / máx. 156 lpm · TRIMP 21
  Calentamiento + fuerza cada 1'30": chin up 4x5 con lastre de 5, 10, 15 y 15 kg; isometric pull up 4x10" con el mismo lastre que los chin up (5, 10, 15 y 15 kg). Tiempo Garmin 35,1 min (incluye calentamiento). Sin RPE: sesión no puntuada por decisión del atleta.

**Carga de fuerza por patrón**

| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |
|---|---|---|---|---|
| Pecho (aislamiento) | — | — | 1 · 4 | — |
| Core | 1 · 0 | — | 2 · 0 | — |
| Bisagra de cadera | — | — | 1 · 2 | 0 (parcial) |
| Empuje horizontal | 3 · 16 | 5.220 | 7 · 32 | 5.220 |
| Flexión de rodilla | — | — | 4 · 24 | — |
| other | 4 · 12 | — | 5 · 12 | — |
| Sentadilla | 1 · 9 | 1.119 | 11 · 76 | 15.437 |
| Tríceps (aislamiento) | — | — | 1 · 4 | — |

Solo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.

**Progresión por ejercicio (barra)**

| Ejercicio | Semana | Mejor serie | 1RM mínimo | Sesiones |
|---|---|---|---|---|
| peso muerto | 2026-S41 | 170 kg × 5 | 198,3 kg | 1 |
| power clean + squat clean (complex 1+1) | 2026-S43 | 90 kg × 1 | 90 kg | 1 |
| press banca | 2026-S44 | 90 kg × 6 | 108 kg | 1 |
| sentadilla trasera | 2026-S41 | 170 kg × 2 | 181,3 kg | 2 |
| sentadilla trasera | 2026-S42 | 185 kg × 1 | 185 kg | 1 |
| squat clean | 2026-S43 | 110 kg × 1 | 110 kg | 1 |
| squat snatch | 2026-S42 | 68 kg × 1 | 68 kg | 1 |
| squat snatch | 2026-S44 | 75 kg × 1 | 75 kg | 1 |

Diferencias entre las dos últimas semanas con datos: sentadilla trasera: 1RM mínimo +3,7 kg entre 2026-S41 y 2026-S42; squat snatch: 1RM mínimo +7 kg entre 2026-S42 y 2026-S44.

Solo barra con carga total. El 1RM es un límite inferior (Epley sin RIR) y no se deduce del RPE; las semanas sin registro no implican que no se entrenara ese ejercicio.

No se atribuyen desgloses no confirmados ni se comparan récords no equivalentes; se conserva la diferencia entre cronómetro oficial y reloj.

## 7. Balance y orientación

Turno: hoy sin dato, mañana sin dato.
- Señales favorables: duración del sueño igual o superior a tu referencia; HRV en rango respecto a tu historial.

### Recomendaciones

1. **Listo para entrenar** — Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien.
2. Ajusta la sesión de hoy con las reglas por tipo del informe del ciclo (`app/informe.md`).
3. Registra sensaciones y fatiga percibida en Intervals: ayudan a contextualizar la recuperación tras varios entrenamientos exigentes.

## 8. Análisis de mejora física y recuperación

Reglas explícitas sobre tus últimos 28 días, sin IA. Son criterios generales de entrenamiento y descanso, no un diagnóstico médico. Cuando los datos no bastan, lo dice y no concluye.

### Prioridades

| # | Área | Qué muestran tus datos | Qué hacer |
|---|---|---|---|
| 1 | HRV | HRV media de los últimos 7 días: 52 ms frente a una referencia de 57 ms (-9 %). | Evita acumular días muy exigentes seguidos y vigila el sueño. |
| 2 | Sueño | Media de 7 noches: 8,0 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 3,9 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). | Adelanta la hora de acostarte 30–45 min esta semana, sobre todo antes de un turno. |
| 3 | Distribución de la intensidad | 14 de 24 sesiones con RPE registrado fueron de RPE ≥ 8 (58 %); 4 veces hubo dos días duros seguidos. | Intercala sesiones de RPE 5–6 entre las duras y deja ≥ 48 h entre dos esfuerzos máximos. |

### Detalle por área

- ⚠️ **HRV.** HRV media de los últimos 7 días: 52 ms frente a una referencia de 57 ms (-9 %). Tendencia algo por debajo de tu referencia.
- ✅ **FC en reposo.** FC en reposo de los últimos 7 días: 56,4 lpm frente a 56,0 de referencia (+0,4 lpm). En línea con tu referencia.
- ⚠️ **Sueño.** Media de 7 noches: 8,0 h (necesidad configurada 7,5 h); 1 de 7 noches más de media hora por debajo; deuda acumulada 3,9 h (cuenta también el sueño diurno tras turno y descuenta las siestas registradas). El sueño es el principal factor de recuperación y de adaptación al entrenamiento.
- ✅ **Regularidad del sueño.** Hora de acostarte (mediana 00:16) con una variación típica de ±61 min en 14 noches; 2 turnos TN en los últimos 14 días. Un horario irregular reduce la calidad del sueño; con turnos rotativos es difícil, pero el ancla (hora de despertar o de la siesta) ayuda.
- ⚠️ **Distribución de la intensidad.** 14 de 24 sesiones con RPE registrado fueron de RPE ≥ 8 (58 %); 4 veces hubo dos días duros seguidos. Una parte alta de sesiones muy duras, sobre todo en días consecutivos, deja poco margen de recuperación y limita la mejora.
- ⚠️ **Respuesta a las sesiones duras.** HRV la mañana siguiente: 50 ms tras sesión de RPE ≥ 8 (n=9) frente a 55 ms tras las demás (n=3); diferencia -5 ms. Es una relación descriptiva con pocos días, no demuestra causa.
- ✅ **Fuerza.** Mejor valor registrado en 28 días: peso muerto 198 kg; sentadilla trasera 185 kg; squat clean 110 kg. Es un mínimo estimado (Epley sin RIR) o la carga máxima declarada: solo se comparan series con las mismas repeticiones.
- ⚠️ **Registro de sensaciones.** Sensaciones (fatiga, agujetas, estrés, ánimo, motivación) registradas en 0 de los últimos 14 días. Las sensaciones son el contraste más barato frente a los números del reloj: sin ellas, la app solo ve la parte objetiva. Además: 2 sesiones de 28 días sin RPE y HRV con dato en 13 de 14 días.

### Constancia semanal (últimas 4 semanas)

| Semana (lunes) | Sesiones | Días con actividad | sRPE |
|---|---|---|---|
| 05/10 | 9 | 5 | 1420 |
| 12/10 | 9 | 4 | 1694 |
| 19/10 | 8 | 3 | 396 |
| 26/10 | 6 | 2 | 820 |

_La semana en curso está incompleta; compara solo semanas completas._

### Semana a semana

Última semana completa (lunes 19/10) frente a la anterior (lunes 12/10). La semana en curso (2 de 7 días, hoy incluido) se muestra aparte y no se compara. Son diferencias descriptivas, no explican causas.

| Métrica | Sem. 12/10 | Sem. 19/10 | Cambio | En curso | 4 semanas |
|---|---|---|---|---|---|
| HRV nocturna | 58 (6 d) | 47 (7 d) | ⚠️ −11 ms | 74 (2 d) | `▂▄▁█` |
| FC en reposo | 56,6 (7 d) | 57,1 (7 d) | ≈ +0,6 lpm | 53,5 (2 d) | `█▇█▁` |
| Sueño | 6,6 (7 d) | 6,8 (7 d) | ≈ +0,2 h | 8,3 (2 d) | `▃▁▂█` |
| Puntuación de sueño | 76 (5 d) | 62 (7 d) | ⚠️ −14 | 92 (2 d) | `▄▄▁█` |
| Sesiones | 9 | 8 | −1 | 6 |  |
| Días con actividad | 4 | 3 | −1 | 2 |  |
| sRPE total | 1694 | 396 | −1298 (−77 %) | 820 | `▇█▁▃` |

_Barras: ▁ valor más bajo, █ más alto de las últimas 4 semanas; «·» sin datos suficientes._

### Plan orientativo de 7 días

| Día | Turno | Sesión sugerida | Motivo |
|---|---|---|---|
| mar 27/10 | free | 🟢 Suave / movilidad | ya has entrenado hoy |
| mié 28/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente (mañana TN: acuéstate pronto) |
| jue 29/10 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |
| vie 30/10 | post-TN | 🛌 Descanso | día posterior a una TN: prioriza dormir |
| sáb 31/10 | free | 🔥 Exigente | día libre con margen para una sesión exigente |
| dom 01/11 | MT | 🟢 Suave / movilidad | turno largo: movilidad o descanso |
| lun 02/11 | TN | 🟡 Moderada | TN por la tarde: si entrenas, por la mañana y moderado |

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

Traza: informe de tarde · ciclo 2026-10-27-1645 · generado 27/10/2026 16:48 Europe/Madrid · certificado READY · sync_run_id 40534383345.
