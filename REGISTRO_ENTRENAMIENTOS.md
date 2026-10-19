# Registro de entrenamientos y RPE (para Claude)

Cómo se apuntan los entrenamientos que el atleta cuenta hablando o por escrito, para que todos los informes los lean igual.
Los datos objetivos (tiempo, FC, carga) llegan solos desde Garmin e Intervals.icu; lo que se registra aquí es lo que el reloj no sabe:
**qué se hizo, con qué cargas, qué resultado y qué RPE**.

## Dónde

Hoja de Google «RPE CrossFit - Registro», pestaña **`RPE`**, columnas A–H (una fila por actividad):

| Col. | Campo | Contenido |
|---|---|---|
| A | Fecha | `AAAA-MM-DD` de la actividad |
| B | ID actividad | ID exacto de Intervals (`i197499385`). Sin ID la fila se ignora |
| C | Actividad | Nombre corto: `Tipo - ejercicio o formato` (p. ej. `WOD AMRAP 12 min - carrera / swing`) |
| D | RPE | Número de 0 a 10; admite medios (`8,5`). Solo el que dice el atleta |
| E | Sensaciones | Lo que cuenta antes de entrenar (`Cansado antes; sin dolor`). Vacío si no dice nada |
| F | Notas | 1–3 frases: formato, cargas, resultado, tiempo Garmin y, si hay, tiempo oficial |
| G | Registrado | Fecha en que se apunta (hoy) |
| H | Detalle JSON | Estructura de la sesión (ver abajo); vacío si no hay detalle |

## Flujo cuando el atleta cuenta un entrenamiento

1. **Identificar la actividad.** Busca las actividades de ese día (Intervals / `activities.csv` / `app/readiness_v3.json → sessions_28d`) y propón qué dictado corresponde a cada ID (hora, duración, tipo). Si hay duda, pregunta antes de escribir. Sin actividad sincronizada no se escribe: se espera al siguiente Sync.
2. **Montar la fila** con las ocho columnas. El calentamiento, la técnica y cada bloque con RPE propio son filas aparte si Garmin los registra como actividades distintas.
3. **Añadir al final** de la pestaña. Si ya existe una fila con ese ID, se actualiza esa fila tras avisar; nunca se borran filas.
4. **Releer la fila escrita** y confirmar al atleta con un resumen de una línea. Recordar que entra en el informe del siguiente ciclo (Sync de las 08:30, 16:45 o 22:45; para el cierre nocturno, antes de las 22:45).

## Reglas de calidad

- **No inventar.** Carga que no se dijo = `null` en el JSON y se anota en las notas. Series por carga sin confirmar se dejan como «pendientes».
- **Marcar interpretaciones** del dictado («167,5 kg interpretado de transcripción oral») y lo no confirmado («desglose de las 35 repeticiones extra no confirmado»).
- **No mezclar medidas:** cronómetro oficial del WOD y tiempo grabado por el reloj se guardan los dos.
- **Unidad de carga explícita:** `kg_total_barra`, `kg_total_dos_mancuernas` (con `load_per_dumbbell_kg`), `kg_indicado_maquina`, `peso_corporal`. Las cargas de máquina no son comparables con la barra.
- **RPE:** solo el que dice el atleta; si lo da por bloque, cada bloque con el suyo y en la columna D el del bloque principal. No estimar 1RM desde el RPE.
- **Unilaterales:** confirmar con el atleta si la carga y las repeticiones son por pierna/brazo y si se hicieron ambos lados.
- **Sensaciones diarias** (fatiga, agujetas, ánimo, estrés) no van a esta hoja: se registran en Intervals.icu (bienestar). La columna E es solo para lo previo a esa sesión.

## Detalle JSON (esquema v1)

Siempre `"schema_version":1`, `"source":"user_in_chat"`, `"type"` (`strength`, `metcon`, `mixed_strength`, `warmup`, `skill`), `"garmin_activity_id"`, `"rpe"` y `"recorded_garmin_minutes"` cuando se conozcan.

- **strength:** `exercises:[{name, load_unit, sets:[{reps, load_kg, interval_seconds?}]}]`; series repetidas con `count`. Opcional: `total_sets`, `total_reps`, `bodyweight_kg_morning`, `notes`.
- **metcon:** `format` (AMRAP, EMOM, For Time, 21-15-9…), `duration_minutes` o `time_cap_*`, `prescribed_round:[{name, reps, load_kg}]`, `performed:{rounds_complete, extra_reps, totals}`; en For Time, `finish_time_seconds`.
- **mixed_strength:** `blocks:[{name, rpe, exercises|working_sets}]`.
- **warmup / skill:** `exercise`, `rpe`, `notes`.

Ejemplo mínimo (metcon):

```json
{"schema_version":1,"source":"user_in_chat","type":"metcon","format":"AMRAP","garmin_activity_id":"i197353076","duration_minutes":12,"rpe":9,"prescribed_round":[{"name":"carrera","distance_m":200},{"name":"kettlebell swing americano","reps":20,"load_kg":24},{"name":"sit-ups","reps":20}],"performed":{"rounds_complete":4,"extra_distance_m":200}}
```

## Texto para las instrucciones del Proyecto

```
Registro de entrenamientos: cuando el usuario cuente un entrenamiento o un RPE, apúntalo en la hoja «RPE CrossFit - Registro», pestaña RPE (columnas Fecha, ID actividad, Actividad, RPE, Sensaciones, Notas, Registrado, Detalle JSON), siguiendo REGISTRO_ENTRENAMIENTOS.md del repositorio. Primero empareja el dictado con la actividad por su ID exacto (pregunta si hay duda), añade una fila por actividad sin borrar nada, no inventes cargas ni RPE, marca lo no confirmado, relee la fila y confirma en una línea.
```

## Peso corporal

Cuando el atleta dicte o muestre una pesada: añade una fila en la pestaña **`Peso`** (Fecha, Hora, Peso kg, Grasa %, Músculo kg, Agua %, Fuente, Notas) y una entrada en `peso_registro.json` del repositorio (la app lee de ahí). Solo valores reales; lo calculado a partir de diferencias se marca como `derivado`.
