# Instrucciones del informe de Claude (versión detallada)

Estas son las instrucciones que sigue la tarea programada «Informe Garmin Recovery» (09:05, 17:10 y 23:10, hora de Madrid). Se mantienen en el repositorio para poder mejorarlas sin tocar la tarea: la tarea solo dice «lee este archivo y síguelo».

## Reglas

- Solo lectura: no modifiques archivos ni hagas commits. Responde en español.
- Usa únicamente cifras presentes en los archivos; nunca inventes ni extrapoles. Si falta un dato, dilo.
- La decisión del día es `app/readiness_v3.json → decision` (`zone`, `guidance`, `registry`, `divergence`): la más conservadora entre v2 oficial, híbrido y v3. Nunca uses `readiness.guidance` como decisión.
- Si `readiness.state` es `pending` o el sueño no está confirmado (`morning_sleep_status.json`), dilo y no autorices intensidad alta.
- La frescura se mide por las marcas de tiempo de las muestras, no por `generated_at`. Un día de FC parcial no es FC en reposo; un Body Battery con retraso no es una medición nueva.
- No hay causalidad en las comparaciones; no presentes variaciones porcentuales entre semanas si la cobertura no está completa. Una sesión sin registro no demuestra un día de descanso.
- Si el informe tiene más de 90 minutos o la cadena falló (`report_ready.json`, `workflow_health.json`), empieza indicándolo.
- No es un diagnóstico médico. La publicación del informe no prueba que se haya recibido una notificación.

## Fuentes (rama `main`)

| Para | Archivo y campo |
|---|---|
| Decisión, modelos, carga, sesiones | `app/readiness_v3.json` (`decision`, `readiness`, `load`, `recent_sessions`, `sessions_28d`, `trend_28d`, `certificate`) |
| Informe ya redactado y gráficas | `app/informe.md`, `app/informe_semanal.md`, `app/charts/` |
| Certificado y cadena | `report_ready.json`, `report_cycles.json`, `workflow_health.json` |
| Modelo v2, valores de hoy y referencias 28 d | `recovery_assessment.json` (`current`, `baseline_28d`, `score`, `confidence`) |
| Híbrido, índice personal, carga semanal, recuperación de FC | `advanced_analytics.json` (`readiness_hybrid`, `personal_recovery_index`, `weekly_load`, `heart_rate_recovery`, `recovery_data_coverage`) |
| Calidad y cobertura | `data_quality.json` (`score`, `status`, `coverage_28d`) |
| Sueño y fases | `garmin_sleep_history.json` (`days`: horas, puntuación, `deep_minutes`, `rem_minutes`), `morning_sleep_status.json` |
| FC diurna/nocturna y ventanas 3/7/28 d | `garmin_heart_rate.json` (`days`, `rolling`) |
| Training Readiness y tiempo de recuperación Garmin | `garmin_extended.json` (`days → training_readiness`, `recovery_time`) |
| Estrés y Body Battery | `garmin_stress.json`, `garmin_body_battery.json` |
| Entrenamientos, RPE, fuerza y WOD con detalle | `crossfit_insights.json` (`activities → manual_blocks → detail_json`, `weekly_report`, `muscle_load`, `training_extensions`) |
| Turno de hoy y de mañana | `shift_calendar.json` (MT 08–22, TN 15–08) |

Opcional: `python -m garmin_recovery run --dry-run` recalcula sin escribir.

## Formato

Título: **Garmin Recovery · <Cierre matinal | Informe de tarde | Cierre nocturno>**, día y hora de la consulta. Según la hora: 09:05 plan del día (RPE máx., volumen, qué evitar, turno); 17:10 sesiones de hoy y si encajan; 23:10 balance del día y de la semana, consejo de sueño (sobre todo antes de un TN).

**Resumen ejecutivo** (5–6 líneas con emoji): certificación del ciclo; recuperación v2 y híbrido con confianza; sueño (duración y puntuación); principal alerta con su cifra; decisión práctica.

1. **Certificación y calidad.** Tabla: ciclo, estado del certificado, las cuatro etapas (Sync, Heart Rate, Advanced, CrossFit), hora del certificado, instantánea inmutable, confianza de recuperación, calidad de datos. Aclara que la calidad describe los datos, no el software, y que no se usan mediciones posteriores al ciclo. Si hay franjas de Sync sin ejecutar, dilo.
2. **Recuperación fisiológica.** Tabla Hoy vs. referencia fusionada de 28 días (HRV, FC en reposo, FC nocturna, duración y puntuación del sueño) con una interpretación de 2 líneas. Tabla de modelos (v2, híbrido, v3 en pruebas, Garmin Training Readiness, tiempo de recuperación Garmin, índice personal experimental) con su papel; explica divergencias.
3. **Sueño.** Episodio confirmado (inicio → fin), fases (profundo, REM, ligero y vigilia si constan; si no constan, no las calcules) y lectura breve. Sin siestas no confirmadas.
4. **Frecuencia cardíaca y tendencias.** Tabla FC diurna/nocturna hoy, 3, 7 y 28 días (marca el día parcial). Cobertura histórica fusionada (HRV, sueño, puntuación, FC reposo, en días de 28). Estrés medio y máximo; Body Battery último valor con su hora y si tiene retraso.
5. **Rendimiento CrossFit.** Última actividad registrada y huecos. Resumen de 7 días (sesiones, días con actividad, RPE medio, sesiones de RPE alto, minutos grabados, sRPE, TRIMP, carga, volumen mínimo verificado) y de 28 días. Gráfico de barras de texto con el sRPE diario de la semana (`—` sin registro). Cita el día de mayor carga.
6. **Fuerza, halterofilia y metcons.** Por sesión de los últimos 7 días, con fecha, RPE y lo confirmado en `detail_json` (ejercicios, series, cargas); volumen de barra cuantificado; 1RM mínimo estimado solo si consta. Metcons: formato, RPE, resultado y tiempos tal cual constan; no atribuyas desgloses no confirmados y conserva la diferencia entre cronómetro oficial y reloj.
7. **Balance y orientación.** Contexto laboral de hoy y de mañana, señales favorables y adversas, tres recomendaciones concretas según la hora y la decisión.

**Conclusión** (2–3 líneas) y, al final, una línea de traza: franja, `cycle_id`, hora de la consulta, estado del certificado, `sync_run_id`.

Enlaza el panel https://carpetox.github.io/garmin-recovery/ y el informe base https://github.com/CarpetoX/garmin-recovery/blob/main/app/informe.md.


## Sección 8 — Análisis de mejora

`app/informe_completo.md` incluye al final de las siete secciones un «Análisis de mejora física y recuperación» calculado por reglas (`garmin_recovery/improvement.py`): prioridades, detalle por área, constancia semanal y reglas para 7 días. Al redactar tu análisis, parte de esa sección, no la contradigas y no añadas cifras que no estén en los datos. Aporta lo que las reglas no hacen: interpretar el conjunto, priorizar según el turno y el momento, y proponer un plan concreto de 7 días (sesiones suaves y duras, sueño) respetando `decision.guidance`.


## Análisis publicado en la app — apertura «En breve»

El primer párrafo de `app/analisis_ia.md` (justo debajo de la línea `<!-- cycle_id: … -->`) debe empezar por `**En breve:**` y explicar, en 3–4 frases de lenguaje llano y sin jerga (di «oficial» y «experimental», no v2/v3): cómo está hoy la persona, qué ha cambiado frente a ayer (diferencia observada, sin causas), qué conviene hacer hoy y por qué. Solo cifras presentes en los datos. La pestaña Hoy de la app muestra ese párrafo; el resto del análisis (qué explica la puntuación, carga reciente, 3 prioridades, plan de 7 días; máx. 300 palabras en total) va en el informe completo.
