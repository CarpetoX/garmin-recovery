# Política de mantenimiento — Garmin Recovery V5.7

Revisión: 17/10/2026 · Europe/Madrid. Complementa `README.md` (qué hace la app) y `OPERACION_Y_VALIDACION.md` (operación y trazabilidad).

## Workflows permanentes (ocho)

| Workflow | Disparo | Función |
|---|---|---|
| `sync.yml` (Garmin Recovery Sync) | Apps Script firmado (`repository_dispatch`), cron de respaldo diario (08:30, llega ~13:00), manual | Intervals.icu y RPE; inicia la cadena |
| `garmin-heart-rate.yml` | tras Sync | Garmin: FC, HRV, sueño, estrés, Body Battery |
| `advanced-analytics-rpe.yml` | tras Heart Rate | Recuperación v2, calidad de datos, instantánea de RPE |
| `crossfit-insights.yml` | tras Advanced | Fuerza/WOD, certificado del ciclo, **app V5** (`garmin_recovery`), validación y publicación |
| `monitor-monthly.yml` | watchdog 11:05/19:20/01:20 y dispatch | Salud de la cadena, origen, resumen mensual |
| `garmin-ci.yml` | push/PR | Tests, compilación y validación de topología de workflows |
| `garmin-shadow-publish-v296.yml` | dispatch del monitor, manual | Copia verificada en la rama `garmin-v296-shadow` |
| `garmin-certified-reports.yml` | manual | Verificación de informes certificados |

Los cron usan `timezone: Europe/Madrid`. GitHub los retrasa 2–5 h: Apps Script es el disparador de las tres franjas (código en `apps_script/`) y el cron de Sync queda como un único respaldo diario.

## Invariantes

1. Un cambio de código va en rama + PR, con CI verde antes de fusionar, y se comprueba con un Sync real después.
2. Los IDs de actividad y las marcas temporales de medición se conservan. No se borran filas de `history/*.csv`, sesiones, sueño ni certificados: una sesión eliminada en Intervals se marca `removed=1`.
3. `report_cycles.json` guarda snapshots con SHA-256: conservar todos. No truncar, comprimir ni archivar sin prueba de reconstrucción y reversión.
4. `training_feedback.json` es una instantánea de RPE: en Advanced → CrossFit se usa una sola vez, validada por huella, run ID y frescura.
5. No estimar 1RM desde el RPE de la sesión ni completar repeticiones de WOD con lo prescrito.
6. Un informe generado no es un aviso recibido: sin acuse externo, la entrega a ChatGPT es "no verificada".
7. El origen de un `repository_dispatch` o `workflow_dispatch` requiere evidencia (firma HMAC de Apps Script); no deducirlo del tipo de evento.
8. La decisión del día es siempre `decision.guidance` (la más conservadora de v2, híbrido y v3); `readiness.guidance` es solo del v3 en pruebas. Un rojo prevalece; si falta un modelo o es de otro día, queda pendiente.
9. La app nunca publica salidas sin validar: si `python -m garmin_recovery validate` falla, se restauran `app/` e `history/` anteriores y el motivo queda en `app/validation.json`.
10. Los archivos generados (`app/`, `history/`) solo los escribe la cadena; no se suben a mano.
11. El repositorio es público por decisión del propietario (ChatGPT lo lee). No es un hallazgo de calidad; lo obligatorio es que no haya secretos en el código ni en los datos.

## Código obsoleto

`sync.yml` ya no tiene código Python en línea: `garmin_recovery/sync_fetch_wellness.py`, `garmin_recovery/sync_fetch_activities.py` y `garmin_recovery/sync_daily_analysis.py` (salida idéntica comprobada byte a byte; tests `test_garmin_recovery/sync_daily_analysis.py` y `test_structure_v59.py`).

`garmin_recovery/garmin_metrics.py`, `garmin_recovery/garmin_activity_metrics.py` y `garmin_recovery/validate_pipeline.py` ya no se ejecutan al importarlos (`main()` + `if __name__ == "__main__"`); misma salida al ejecutarlos.

Un número de versión en el nombre (`recovery_v231.py`, `monitor_v231.py`…) no significa que sobre: muchos siguen importados. Antes de borrar un módulo, comprobar que ningún workflow lo ejecuta y que ningún módulo en uso lo importa (análisis de imports desde los scripts que ejecutan los workflows), y quitar sus tests y referencias en los YAML en el mismo PR.

## Validación local

```bash
python -m compileall -q .
python -m unittest discover -p 'test_*.py'      # batería completa (~700 tests)
python -m garmin_recovery run --dry-run         # calcula sin escribir
python -m garmin_recovery validate              # contrato y coherencia de app/ e history/
```

## Vigilancia continua

- Tamaño del repositorio. Medido el 17/10/2026 (historial completo): 6,4 MB comprimidos tras 11 días y 1.232 commits, unos 0,5 MB/día (~180 MB/año). Git comprime bien las versiones sucesivas de los JSON grandes (165 versiones de `garmin_stress.json` ocupan 282 KB), así que **no hace falta compactar todavía**; revisar al superar ~500 MB.
- Retraso real del cron de GitHub: en 60 ejecuciones llegó entre 2,3 y 5,7 h tarde. El disparador fiable es Apps Script; un vigilante basado en cron de GitHub no recuperaría a tiempo una franja perdida.
- Duración de los workflows.
- Frescura de datos por marca temporal de cada muestra, no por `generated_at`.
- Fallos del disparador de Apps Script (huecos entre ciclos firmados).
- Cobertura de RPE: la monotonía, el strain y el ACWR solo se calculan con ≥ 75 % de sesiones con RPE.
- El v3 sigue en sombra (`model_validated: false`) hasta contrastarlo 4–6 semanas con RPE y rendimiento reales.

La puntuación de calidad fisiológica de Garmin no es el porcentaje de CI de GitHub. Un historial de HRV/sueño inmaduro requiere más mediciones, no estimaciones.

## Plan de migración al paquete `garmin_recovery`

Hoy conviven la cadena antigua (≈ 40 scripts ejecutados por los workflows, más sus dependencias) y el paquete V5, que genera el informe vigente. Se migra **una pieza por PR**, siempre con una prueba de salida idéntica sobre datos reales y sin cambiar los JSON que leen ChatGPT o Apps Script (`report_ready.json`, `recovery_assessment.json`, `shift_calendar.json`, `morning_sleep_status.json`, `app/*`).

| Paso | Qué | Estado |
|---|---|---|
| 0 | `sync.yml` sin código en línea; scripts sin efectos al importarlos | Hecho (V5.9) |
| 1 | Retirar del monitor los informes previos que solo generaban artefactos (V3.9.2.2 enriquecido, V4.0.2 visual) | Hecho (V5.9); sus 9 módulos y 8 tests, borrados en V6.0 |
| 2 | Calcular el v2 dentro del paquete, con pruebas *golden*; el archivo se sigue publicando igual | Hecho (V6.2): `advanced.py`, `reliability.py`, `recovery_v23.py`, `recovery_v231.py` y `convergence_domains.py` viven en `garmin_recovery/`; los nombres antiguos son alias del mismo módulo. Pruebas de salida idéntica sobre el día congelado |
| 3 | Pasar al paquete la extracción de fuerza y WOD de `garmin_recovery/crossfit.py` (mismas reglas de unidades e implementos) | Hecho (V6.2): `crossfit.py`, `garmin_recovery/muscle_load.py`, `garmin_recovery/data_quality.py`, `garmin_recovery/training_extensions.py`, `report_audit.py` y `garmin_recovery/rpe_cycle_snapshot.py` viven en `garmin_recovery/`; los nombres antiguos son alias. Prueba de salida idéntica con 18 ejercicios de fuerza |
| 4 | Unificar certificados y monitor (`report_cycles.json`, `report_ready.json`) en el paquete, conservando el historial con SHA-256 | Hecho (V6.4): 4a informe opcional V3.6 retirado (`cycle_observation_v373.json` pierde `standalone_report` y `report_v36_link`); 4b `delivery_gate.py` y `sleep_integration.py`; 4c monitor (`monitor`, `monitor_v231`, `ops_metrics`, `origin_monitor`, `origin_integration`, `report_monitor`, `cycle_observer`, `cycle_integration`, `cycle_guard`, `monitor_clarity`, `reliability_history`). Los nombres antiguos son alias del mismo módulo; pruebas de salida idéntica con la API de GitHub simulada |
| 5 | Borrar los módulos que ya no ejecute ningún workflow ni importe ningún módulo en uso, con sus tests | En curso: 15 módulos borrados en V6.0, 7 alias en V6.4 y 10 alias más en V6.7 (`monitor_monthly`, `monitor_v231`, `monitor_origin_integration_v292`, `report_monitor_v34`, `cycle_observer_v373`, `monitor_clarity_v297`, `reliability_history_v294`, `report_delivery_gate`, `report_sleep_integration`, `convergence_domains_v242`): los workflows llaman ya a `python -m garmin_recovery.<módulo>`. Siguen 7 alias (`advanced_analytics`, `recovery_reliability`, `crossfit_insights`, `data_quality`, `muscle_load`, `training_extensions`, `rpe_cycle_snapshot`) porque scripts antiguos que aún no están en el paquete los importan; caerán cuando se migren ellos |

Regla: si una salida pública cambia, aunque sea un campo, el PR lo declara y se valida antes con un Sync real.

## V6.5 — Informe completo

`fullreport.py` genera `app/informe_completo.md` desde `report.write_report`; `site.build_site` lo publica como HTML (`mdhtml.py`); `validate.py` exige su estructura. Si cambia un campo de los JSON de origen, ajustar `fullreport.py` y `test_fullreport_v65.py`.

## Registro de entrenamientos

`REGISTRO_ENTRENAMIENTOS.md` fija cómo Claude apunta en la hoja (pestaña `RPE`, columnas A–H) lo que el atleta cuenta. El pipeline solo lee filas con fecha, ID de actividad y RPE válidos; el resto se ignora, así que cambiar el esquema de la hoja exige cambiar `garmin_recovery/rpe_enrichment.py`.

## V6.10 — Vigilante del despertar (Apps Script v2.9.5)

Si te levantas tarde, el informe definitivo ya no espera a una hora fija. Entre las 08:50 y las 18:29:

- Sueño sin confirmar: un Sync cada 30 min (cada 60 min tras un TN).
- Despertar confirmado: se pide el Sync en cuanto se cumple el margen de 30 min (`earliest_definitive_at`), a más tardar en el siguiente paso del activador de 5 min.
- Sueño confirmado pero recuperación sin sincronizar: reintento a los 15 min.
- Tope de 10 solicitudes al día.

Para activarlo hay que pegar `apps_script/GarminPostSueno.gs` en el archivo del proyecto de Apps Script que ya define `vigilarPostSuenoGarmin` (sustituyendo su contenido; no crear un segundo archivo ni tocar los activadores). Después, ejecutar una vez `diagnosticarPostSuenoGarmin` para ver la decisión sin lanzar nada. La lógica de decisión (`_postSuenoPlan_`) se comprueba en `test_postsueno_v69.py` (requiere Node).

El cron de GitHub llega horas tarde (el de las 08:30 de ayer arrancó a las 13:01), por eso no sirve como respaldo de las franjas: el respaldo es Apps Script.

### Sueño provisional tras un turno de noche

Si ayer fue TN y el sueño de hoy acaba antes de las 10:00 con menos de 5 h (`sleep_hours`), `garmin_recovery/morning_sleep_gate.py` lo marca
`post_night_shift_short_sleep_pending`: no es definitivo, no autoriza intensidad alta y el vigilante sigue consultando
(cada 60 min) por si Garmin añade el descanso principal. Si no hay `sleep_hours`, no bloquea. Un episodio que acaba antes de
las 07:00 ya se trataba así (`post_night_shift_early_sleep_pending`). Los umbrales (5 h, 10:00) están en el propio archivo.
Aún no está comprobado cómo registra Garmin un segundo sueño del mismo día: cuando ocurra, conviene revisar los datos reales.

## V6.12 — Limpieza de estructura

- Ya no queda ningún script en la raíz: todo vive en `garmin_recovery/` y los workflows ejecutan `python -m garmin_recovery.<módulo>`. Los alias antiguos (`advanced_analytics.py`, `crossfit_insights.py`…) se han borrado.
- `advanced.py` (antes 2.519 líneas) conserva lo que depende de la hora (`NOW`, `TODAY`) y `main`; las funciones puras están en `advanced_core` (constantes y estadística), `advanced_context`, `advanced_hrr` y `advanced_models`, y `advanced` las reexporta, así que `advanced.<nombre>` sigue funcionando. Los tests dorados sustituyen `advanced.NOW/TODAY`, por eso esos módulos no pueden leer el reloj (lo comprueba `test_advanced_split_v69.py`).
- Cobertura de tests medida en CI: 70 %; mínimo exigido 68 % (`pyproject.toml`).
- Las comprobaciones de estructura del CI buscan el nombre del módulo en el `run` de cada paso (`garmin_recovery.<módulo>`): si renombras un módulo, actualiza también `garmin-ci.yml`.

## V6.13 — Ingesta resistente y estado de fuentes

- `garmin_recovery/ingest.py`: Intervals.icu se descarga con hasta 3 intentos (esperas de 2 y 6 s) ante 429, 5xx o fallo de red. Si sigue fallando y ya hay datos previos, el Sync continúa con ellos y lo anota en `intervals_status.json` (tipo de fallo, HTTP, fallos seguidos). Los fallos de acceso (401/403) o de petición no se toleran: el Sync falla como antes y salta el aviso enseguida.
- Tras 3 fallos seguidos de una fuente de Intervals se abre/actualiza el aviso de GitHub («intervals»).
- El informe completo tiene en la sección 1 una tabla «Fuentes de datos» con el último dato y el estado de cada fuente (la fecha de la última actividad no cuenta como salud de la fuente: puede no haber entrenado).
- Pendiente (no hecho): importar desde archivos FIT/CSV de Garmin como respaldo si Intervals dejara de recibir datos de Garmin. Hoy el sueño y la FC se leen de Garmin Connect directamente (`GARMIN_TOKENS_B64`), así que solo dependen de Intervals el bienestar (HRV, FC en reposo) y las actividades.

## V6.14 — Mejoras de análisis y robustez

Bloques nuevos del informe completo (todos opcionales: si fallan, el informe sigue):

- **Necesidad y deuda de sueño** (`sleep_need.py`, sección 3): base 7,5 h + recargo por la carga de ayer (≤ 0,5 h) + recargo por la deuda de las últimas 3 noches (≤ 1 h) − siesta de hoy. Heurística sin validar. Las siestas salen de `garmin_extended.json → sleep_detail.nap_minutes`. La deuda de 7 noches también alimenta `improvement._sleep`.
- **Qué ha cambiado desde ayer** (`why_changed.py`, sección 2): diferencias observadas de HRV, FC en reposo, FC nocturna, sueño, puntuación de sueño y estrés; sin causalidad.
- **Diario de correlaciones** (`correlations.py`, sección 4): HRV de la noche siguiente según sesión, TN o noche corta del día anterior; exige ≥ 5 días con y ≥ 5 sin en 90 días.
- **Calibración de la zona** (`zone_calibration.py`, sección 4): HRV posterior por zona de decisión; solo descriptivo, no cambia umbrales.
- **Carga de fuerza por patrón** (`strength_patterns.py`, sección 6): bloques, series y volumen de barra (solo barra con carga total y volumen completo).
- **Contraste Garmin ↔ Intervals** (`activity_crosscheck.py`, sección 5): actividades de Garmin (±2 min de inicio) que aún no constan en Intervals. Es el respaldo de visibilidad si Intervals falla; no crea actividades.

Aviso al móvil: `notify.night_shift_tip` añade una línea de consejo de sueño/siesta los días de TN antes de las 15:00, sin cifras fisiológicas.

Calidad: la cobertura medida en CI es del 79 % y `fail_under` es 77.

### Plan de 7 días, progresión de fuerza, aviso de token y copia de seguridad

- **Plan orientativo de 7 días** (`week_plan.py`, dentro del apartado 8): reglas explícitas con turnos (`shift_calendar.json`), sesiones duras recientes (RPE ≥ 8) y la decisión del día.
- **Progresión por ejercicio** (`strength_progress.py`, sección 6): mejor serie y 1RM mínimo por semana ISO, solo barra con carga total.
- **Caducidad del acceso a Garmin** (`token_health.py`): `garmin_status.json → token_expiry` guarda solo la fecha hallada (nunca el token); si queda ≤ 14 días abre el aviso `garmin_token`. Con el token actual solo consta la caducidad de un token de acceso corto (`access_token_only`), así que hoy no avisa.
- **Copia de seguridad mensual** (`backup.py` + `.github/workflows/backup-monthly.yml`, día 1 a las 03:20 UTC): `tar.gz` con manifiesto SHA-256 de una lista cerrada de archivos de datos (sin secretos ni código), publicada como Release `backup-AAAA-MM`; se conservan las últimas 12. Como el repositorio es público, los Releases también lo son.
- CI: el paso de cobertura anota los 12 módulos menos cubiertos.

## V7.0 — Panel web
- Tarjetas «Qué ha cambiado», «Esta noche» y «Próximos 7 días» (`site._live_extras`: `why_changed`, `sleep_need`, `improvement._plan`), navegación fija y secciones plegables.
- **Días anteriores:** `site.day_snapshots` toma de Git el último `readiness_v3.json` de cada uno de los 14 días previos y `build_site` genera `dia/AAAA-MM-DD.html` (solo en la web, no en el repositorio). Requiere `fetch-depth: 0` en `pages.yml`.
- El registro de RPE sigue haciéndose por el chat (ver `REGISTRO_ENTRENAMIENTOS.md`); se descartó el formulario web con endpoint de Apps Script.
- **Deuda de sueño (etiquetas):** la tarjeta «Esta noche» y el informe muestran la deuda de 3 y de 7 noches (con sueño diurno y siestas) y aclaran que el modelo v3 cuenta solo 3 noches sin descontar siestas (`debt_3n_model_h`). Las definiciones siguen siendo dos, pero ya no se contradicen a la vista.
- **Aviso de RPE pendiente:** `notify.rpe_pending_tip` añade a la notificación de cada ciclo las sesiones de hoy sin RPE (a partir de las 12:00) o las de ayer (por la mañana). No hay disparador propio a las 21:00 porque Apps Script solo lanza las tres franjas de Sync; el aviso viaja en la notificación de las 17:10 y de las 09:05.

## V7.1 — Auditoría (18-10-2026)
- **Bloques opcionales:** `optional_blocks.failed(bloque, exc)` sustituye a los `except … pass` del informe completo y de la web: anota el fallo en Actions (`::warning::`) y el informe añade «Bloques opcionales no disponibles en este ciclo: …». Todo bloque opcional nuevo debe registrar así su fallo.
- **Certificación:** un Sync lanzado a mano fuera de franja marca el ciclo con «Sync fuera de franja». No se lanzan Sync de verificación salvo que un cambio de producción lo exija (probar con la suite y simulaciones).
- **Acciones de GitHub:** versiones mezcladas (`checkout`/`setup-python` v4–v5 y v7 en `sync.yml` y `advanced-analytics-rpe.yml`) y sin fijar por hash: no se unifican sin poder verificar los hashes desde el entorno de desarrollo; `dependabot.yml` propone las actualizaciones semanalmente. Los permisos ya son mínimos (escritura solo donde se hace commit o se abren avisos).
- **Pendiente:** relleno histórico de 60–90 días de sueño/HRV desde Garmin (cobertura de 28 días: HRV 46 %, sueño 43 %, puntuación 36 %).

## V7.2 — Estado final del ciclo
- `garmin_recovery/cycle_delivery.py` (paso «V7.2» del monitor, solo con `repository_dispatch`, `continue-on-error`) escribe `delivery_status.json`: etapas del certificado (Sync, FC, analítica, CrossFit) + **web publicada** (primer despliegue de `pages.yml` posterior al inicio de CrossFit, esperando hasta 5 min) + **notificación** (lee la línea `{"notify": …}` del registro del paso ntfy del job de CrossFit).
- Estados: `complete`, `complete_without_notification` (sin tema o sin informe nuevo que avisar), `pending`, `failed`, `unconfirmed`.
- **Alcance:** «notificación enviada» = ntfy aceptó el mensaje (HTTP 2xx); no hay acuse de lectura. El registro del paso se descarga sin enviar el token a la URL firmada; si no se puede leer, la etapa queda `unknown` (→ `unconfirmed`), nunca «ok».
- La web lo muestra en la tarjeta «Ciclo …» (chips ✓ … ✗). `delivery_status.json` está en los `paths` de `pages.yml`: el commit del monitor republica la web con el estado ya calculado.
- Primer ciclo real con esta función: verificar `delivery_status.json` y, si la descarga del registro falla, ajustar `api_text`.
- **Tonelaje (18-10-2026):** `crossfit.sets_volume` suma solo ejercicios `kg_total_barra` (o sin unidad, registros antiguos). Antes sumaba también máquinas, mancuernas y cargas por lado, y el informe llamaba «volumen de barra» a 12.943 kg cuando la barra eran 5.415 kg. Los volúmenes semanales y de 28 días bajan en consecuencia; los hashes golden de `report_cycles.json` se actualizaron por este cambio de datos heredados (`training_feedback.json`).
- **Margen de piernas (18-10-2026):** `muscle_recovery.compute` busca ejercicios de tren inferior (squat, hinge, lunge, flexión/extensión de rodilla, olímpicos) con RPE de ejercicio ≥ 9 (bloquea piernas pesadas 48 h) o 8–8,9 (24 h), tomados de `detail_json` (el RPE global de la sesión puede ser menor). Alimenta una recomendación en la sección 7 del informe y el plan de 7 días (`week_plan.plan(..., legs)`: los días libres dentro del margen pasan de «exigente» a «moderada»). Regla heurística sin validar; la decisión del día sigue mandando.

## V7.3 — Panel por pestañas (fase 1)
- El panel se organiza en cuatro pestañas con barra inferior: **Hoy** (decisión, qué ha cambiado, esta noche, próximos 7 días, indicadores y factores), **Tendencias** (calendario, semana, gráficas), **Entrenos** (sesiones, fuerza) y **Sistema** (estado del ciclo, puntualidad, días e informes anteriores, calidad, modelos). `dashboard._extra_sections` devuelve un diccionario con las partes de cada pestaña y la plantilla las coloca con `{{HOY}}`, `{{TEND}}`, `{{ENT}}`, `{{SIS}}` y `{{BANNER}}`.
- Sin JavaScript se ven todas las secciones seguidas (la clase `js` solo se añade con JS). Los enlaces antiguos (`#plan`, `#noche`, `#calidad`…) activan su pestaña. Las gráficas se dibujan al mostrarse la pestaña (ResizeObserver).
- Fase 2 pendiente: tres indicadores (Recuperación, Sueño, Carga), una sola puntuación arriba y vocabulario simplificado.

### V7.3 fase 2 · Hoy en dos pantallas
- Hoy: puntuación única, tres indicadores (Recuperación y Sueño en anillo; Carga 7 días con barras de sRPE, sin comparar semanas), «Por qué esta puntuación» (drivers y notas), luego tarjetas de cambios, esta noche y plan.
- Etiqueta «Los modelos discrepan» solo si `decision.agreement != 'total'`. Los chips por modelo y los medidores v3 pasan a Sistema; los indicadores clave (tiles) pasan a Tendencias.
- Sin cambios en decisión, reglas de seguridad ni cifras; TSB/CTL se muestran como «carga reciente vs. habitual».

### V7.3 fase 3 · Informe completo ordenado
- Solo «Resumen ejecutivo» abierto; el resto de secciones plegadas, con un subtítulo de una línea (`webreport.SUBTITLES`). Botón «Expandir todo» y chips cortos (`SHORT`). El Markdown sigue siendo la fuente de verdad: no cambia ninguna cifra.
- Altura en móvil: de ~18 200 px a ~1 950 px al abrir.
- Orden de lectura (`webreport.ORDER`): Balance y orientación (qué hacer), Recuperación, Sueño, CrossFit, Mejora, FC, Fuerza, Resumen, Calidad y Conclusión; abiertas por defecto Balance y Recuperación (`OPEN`). Los títulos se muestran sin número porque el orden ya no es el del Markdown, que no cambia.

### V7.3 fase 4 · Vocabulario sin v2/v3
- En panel, informe y avisos: v2 → «oficial», v3 → «experimental» (híbrido se mantiene). Solo cambian los textos mostrados; nombres de archivo, claves JSON (`v2_score`, `readiness_v3`…) y el motor no cambian.

### V7.3 fase 5 · FC por sesión
- `hr_curves.py` (puro, sin red ni reloj): `refresh` guarda en `activity_hr_curves.json` la curva de FC de cada sesión de los últimos 28 días (stream de Intervals.icu, un punto cada 10 s, máx. 10 descargas por ejecución, más recientes primero; sin FC → `available: false`; fallo de red → se reintenta). Se ejecuta en Advanced (envuelto en try/except con `::warning::`) y el workflow lo versiona.
- Web: en Entrenos, las filas con curva llevan ♥ y se abren con detalle (gráfica con zonas, valores al tocar, tiempo por zona). `icu_hr_zones` son límites superiores de zona. Solo visualización: no entra en ninguna puntuación ni en la decisión.

### V7.4 · Retoque visual
- Hoy: anillo grande de la puntuación con tinte de zona; mini-curvas de 14 días en los indicadores clave; líneas suavizadas y área bajo la puntuación; iconos SVG propios en la barra inferior; plan de 7 días como tira horizontal; sesiones como tarjetas en móvil (≤640 px, `data-l` en las celdas); animación de entrada y del anillo (desactivada con `prefers-reduced-motion`).
- Informe completo: icono por sección (`webreport.ICONS`), KPI más grandes y filas alternas en tablas. Solo presentación: no cambia ninguna cifra ni la decisión.

### V7.5 · Hoy: cambios arriba y explicación breve
- Orden de Hoy: puntuación → «Qué ha cambiado desde ayer» (recuperación oficial y lista de indicadores) → «Hoy en breve» → anillos (Sueño, HRV, Carga) → «Por qué» → informe → esta noche → plan. La recuperación ya no se repite en los anillos.
- `brief.py` (puro): redacta por reglas 2-3 frases con veredicto, lo que conviene vigilar (peor factor y nota del día) y la recomendación de esta noche; solo cifras de los datos, sin IA ni causalidad.

### V7.6 · «En breve» de Claude en Hoy
- `ai_analysis.lead` extrae el párrafo `**En breve:** …` del análisis (solo ciclo vigente); el panel lo muestra en Hoy («Análisis de Claude») y en el informe completo la sección «Análisis de Claude» sube tras «Balance y orientación» y se abre por defecto. Instrucciones actualizadas en `INSTRUCCIONES_INFORME.md` y `RUTINA_INFORME_CLAUDE.md`.

### V7.7 · Héroe compacto
- La puntuación oficial es un anillo más pequeño junto a la decisión; los cambios frente a ayer pasan a tarjetas pequeñas dentro del héroe (recuperación oficial primero, luego cada indicador que cambia; ↑ favorable / ↓ desfavorable). Sin cambios de cifras ni de reglas.

### V7.8 · Sin gráfica de 1RM
- Retirada la gráfica «Progresión de fuerza» (1RM mínimo estimado) del panel, del informe completo y del informe base; ya no se genera `charts/strength.svg`. Se conserva la tabla de fuerza y `report.chart_strength` por si se quisiera recuperar. Foto e2e actualizada (`--update`) porque desaparece ese archivo.
