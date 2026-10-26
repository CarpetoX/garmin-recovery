# Garmin Recovery — plataforma de recuperación y CrossFit

Registro Garmin/Intervals + RPE de Google Sheets y resúmenes reproducibles. Zona horaria operativa: **Europe/Madrid**. Arquitectura conservadora: **seis workflows permanentes**; no añadir automatizaciones permanentes por cada actualización.

## Arquitectura y ejecución

| Orden | Workflow | Función |
|---|---|---|
| 1 | `sync.yml` | Actividades Intervals y resumen diario/semanal |
| 2 | `garmin-heart-rate.yml` | FC, HRV y sueño Garmin |
| 3 | `advanced-analytics-rpe.yml` | RPE, recuperación y calidad de datos |
| 4 | `crossfit-insights.yml` | Fuerza, WOD, informes y certificados de datos preparados |
| Independiente | `monitor-monthly.yml` | Control de salud y vigilancia de sincronizaciones |
| Independiente | `garmin-ci.yml` | Pruebas, sin sincronizar datos personales |
| Auxiliar | `garmin-shadow-publish-v296.yml` | Espejo de publicación (V2.9.6), disparo manual o `repository_dispatch` |
| Auxiliar | `garmin-certified-reports.yml` | Informes certificados bajo demanda (V3.9) |

> Nota: en `.github/workflows` hay hoy **ocho** archivos: los seis permanentes y dos auxiliares sin `schedule` ni `workflow_run`.

## App de seguimiento V5 (nuevo, en modo sombra)

Paquete `garmin_recovery/` que se ejecuta dentro de *Advanced Analytics* (paso no bloqueante, `continue-on-error`) y genera:

| Salida | Contenido |
|---|---|
| `history/daily.csv` | Registro diario canónico persistente (HRV, FC, sueño, estrés, carga, sensaciones, turno, fuente por métrica). Upsert por fecha; nunca borra datos. |
| `history/sessions.csv` | Sesiones por ID de actividad con duración, carga, FC, RPE y sRPE (Foster). |
| `app/readiness_v3.json` | Disponibilidad de hoy, componentes, factores, carga (ATL/CTL/TSB de Intervals; monotonía, strain y ACWR sobre sRPE) y tendencia de 28 días. |
| `app/dashboard.html` | Panel autocontenido (claro/oscuro, móvil) para abrir en el navegador. |

**Modelo readiness v3** (`garmin_recovery/readiness.py`):

- HRV en ln(rMSSD): media de 7 días frente a tu línea base (mediana de hasta 60 días previos a esa semana) con banda de cambio mínimo relevante ±0,5 σ robusta (MAD). Una noche mala pesa menos que una semana mala, y una lectura aislada anómala no ensancha el rango normal.
- FC en reposo y nocturna en desviaciones robustas (mediana/MAD); sueño frente a la necesidad configurada y deuda de 3 noches; carga solo cuando la CTL permite interpretar la forma; sensaciones de Intervals.icu (1 = mejor, 4 = peor).
- Puntuaciones continuas (`75 + 12,5·z`), ponderadas y renormalizadas. Zonas: verde ≥ 70, ámbar 50–69, rojo < 50, con RPE máximo y volumen recomendados.
- Salvaguardas: sin HRV/sueño/FC de hoy o sueño sin confirmar → `pending` (no autoriza intensidad alta); línea base < 7 noches → sin puntuación; < 14 (`provisional_below_n`) → `provisional`, nunca verde; sueño < 5 h nunca verde.
- Avisos según turno (TN y post-TN) desde `shift_calendar.json`.
- **Dos confianzas separadas** (V5.1): *datos* (completos y cubiertos 7 días) y *recomendación* (histórico mínimo: media ≥ 14 noches, alta ≥ 28; nunca alta mientras `model_validated` sea `false`).

**Informe del ciclo** (V5.3, `app/informe.md` + `app/charts/*.svg`): GitHub lo muestra con sus gráficas, también en el móvil, y ChatGPT o Claude lo pueden leer y citar. Tiene tres variantes según la hora del Sync: *mañana* (qué cambió frente a tu línea base, señales coincidentes, incertidumbre y plan), *tarde* (actividad de hoy y si encaja con la decisión) y *noche* (balance del día y la semana y previsión orientativa). Lleva hasta 7 gráficas: disponibilidad oficial frente a v3 con franja de decisión, HRV con rango normal, FC en reposo y nocturna, sueño (nocturno frente a diurno/post-TN), carga con ATL/CTL, carga por sesión y tipo (WOD, fuerza, halterofilia, técnica) y progresión de fuerza. Termina con el certificado. La app se ejecuta al final de *CrossFit Insights*, tras el certificado del ciclo, y guarda cada día en `history/daily.csv` las puntuaciones de v2, el híbrido y v3 y la zona de decisión.

**V5.6, validación antes de publicar:** después de generar el informe, `python -m garmin_recovery validate` comprueba 30 puntos, entre ellos:
- el contrato de `readiness_v3.json`;
- que la decisión sea la más conservadora de los modelos;
- que ningún ajuste del plan supere el RPE máximo;
- que las fechas estén ordenadas y lleguen hasta hoy;
- que el identificador GR sea correcto en la cabecera, el certificado y `reports.csv`, sin duplicados;
- que la recomendación del Markdown coincida con `decision.guidance`;
- que las gráficas enlazadas existan y sean SVG válidos, y que el historial no tenga duplicados.

Si alguna comprobación falla, CrossFit Insights restaura el `app/` y el `history/` anteriores, de modo que nunca se publica un informe roto, y guarda el motivo en `app/validation.json`.

**V6.1, web instalable:** el panel se publica en **https://carpetox.github.io/garmin-recovery/** después de cada ciclo (workflow `pages.yml`, que se lanza con el mismo aviso que el monitor). Se puede añadir a la pantalla de inicio del móvil y abre a pantalla completa, con el último panel disponible aunque no haya red. Incluye:
- el resumen de tres líneas;
- un **calendario de 4 semanas** con la decisión de cada día, el RPE máximo y un anillo rojo si se superó; al tocar un día se ven el sueño, la HRV, la FC y las sesiones;
- el **RPE frente al máximo del día**, con valores al pasar el dedo o el ratón;
- la semana frente a la anterior, la progresión de fuerza (1RM mínimo) y la puntualidad;
- el **histórico de informes**: cada informe publicado en los últimos 30 días, tal como salió y con sus gráficas.

Se genera con `python -m garmin_recovery site`.

**V6.1, fiabilidad:**
- **Avisos de fuentes desconectadas:** si Garmin o Intervals.icu dejan de aportar datos nuevos (más de un día), se avisa en el mismo issue de GitHub. Si el error de Garmin es de acceso, el aviso pide renovar `GARMIN_TOKENS_B64`; si falla Intervals, revisar `INTERVALS_API_KEY`.
- **Fuentes de reserva visibles:** si la HRV, el sueño o la FC de hoy vienen de Intervals.icu porque Garmin no los trajo, el informe de la mañana lo dice. La reserva ya existía; ahora se ve.
- **Prueba de extremo a extremo** (`test_e2e_frozen_v61.py`): ejecuta la app completa sobre un día real congelado (`tests_fixtures/`) y compara la decisión, las puntuaciones, la carga, las secciones y las gráficas con la foto esperada.

**V6.0, avisos y seguimiento:**
- **Aviso en GitHub** (issue «⚠️ Garmin Recovery: atención necesaria», con mención al propietario). Lo abre la cadena si CrossFit Insights falla antes de publicar o si el informe no pasa la validación. Lo abre la vigilancia programada, después de calcular `workflow_health.json`, si no hay informe en 11 h o se perdió una franja en las últimas 12 h. Cada uno solo cierra sus propios avisos: un fallo de la cadena solo lo cierra un ciclo que publique bien. Comenta solo cuando cambian los avisos, se cierra solo y nunca bloquea la cadena.
- **Puntualidad en el resumen semanal:** hora del Sync y hora del informe de cada franja, frente a las 09:05, 17:10 y 23:10.
- **Fuerza:** mejor serie y **1RM mínimo** (Epley con kg × repeticiones, hasta 10 repeticiones) en el informe, en el semanal y en la gráfica de progresión. Si la serie no fue al fallo, el 1RM real es igual o mayor. No usa el RPE de la sesión, y el 1RM con RIR explícito sigue siendo `estimated_1rm_kg`.
- **Panel (`app/dashboard.html`):** el resumen de tres líneas, la gráfica de RPE frente al máximo y la semana frente a la anterior.
- **CI:** revisión de estilo con `ruff` del paquete de la app y sus tests.

**V5.9, informes más claros:**
- **Arriba del todo, tres líneas:** la decisión con su RPE máximo, por qué se ha tomado (qué modelos la marcan y las dos señales que más pesan) y qué hacer.
- **Una sola decisión visible.** La comparación entre v2, híbrido y v3 queda en un desplegable "Cómo se decide".
- **Secciones repetidas plegadas** (`<details>`): tendencias de 28 días (abiertas solo por la mañana), reglas por tipo de sesión, fuerza y detalle del certificado.
- **Gráfica de RPE frente al máximo del día** (`charts/rpe.svg`, 14 días; informes de la tarde, de la noche y semanal). Las barras son el RPE de la sesión más dura de cada día, coloreadas por tipo. Una raya gris marca el máximo que permitía la decisión ese día (verde 9, ámbar 7, rojo 4, pendiente 6) y un punto rojo señala cuando se superó. En días verdes, un WOD a RPE 8–9 queda dentro.
- **Nuevo `app/informe_semanal.md`:** los últimos 7 días frente a los 7 anteriores, con sesiones, minutos, carga y sRPE; días por encima del RPE máximo; HRV, FC y sueño; fuerza de la semana; calidad de los datos; y validación. Se regenera en cada ciclo, y el del domingo por la noche es el cierre de la semana.

**V5.9, estructura:** `sync.yml` ya no tiene código en línea (tres scripts con salida idéntica comprobada). Los scripts antiguos ya no se ejecutan al importarlos. El monitor deja de generar los informes previos V3.9.2.2 y V4.0.2, que solo producían artefactos. Plan de migración en `MAINTENIMIENTO.md`.

**V5.8, validación de modelos** (`garmin_recovery/backtest.py`): cada día se guarda en `history/model_predictions.csv` lo que dijo cada modelo (v2, híbrido, v3 y decisión) **antes de la primera sesión**. La fila se actualiza mientras no entrenes y se congela en cuanto aparece una sesión, y no se reconstruye nada hacia atrás. Después se compara con tu **esfuerzo relativo**: ln(sRPE / carga de FC), estandarizado dentro de cada tipo de sesión con tu propio historial. Si el mismo trabajo cardiaco te cuesta más de lo habitual, sale positivo, así que un modelo útil tiene correlación negativa. También se comparan las sensaciones de la mañana siguiente, si las registras en Intervals, y los días entrenados por encima del RPE máximo. Se usa Spearman con IC 90 % y no hay veredicto hasta tener 20 días con entrenamiento, RPE y predicción (`min_validation_days`). El resultado está en `model_validation` de `readiness_v3.json` y en el informe de la noche. Promover el v3 sigue siendo una decisión manual (`model_validated`).

**V5.7, correcciones de la auditoría de calidad** (un test por corrección en `test_audit_fixes_v57.py`):
- **Decisión:** un rojo prevalece sobre un modelo pendiente (antes daba "pendiente" con RPE 6); v2 e híbrido de otro día cuentan como desactualizados: no autorizan nada y su puntuación no se guarda como de hoy, pero un rojo de ayer sigue limitando hasta que llegue el dato de hoy.
- **Publicación segura:** el paso de validación ya no puede saltarse la restauración si la app falla; el aviso a la rutina solo sale si la validación pasa. El validador comprueba además que la pauta corresponda a la zona, que el JSON, el Markdown y `reports.csv` sean del mismo ciclo y que la salida tenga menos de 60 min.
- **Modelo:** línea base de HRV robusta (mediana/MAD); monotonía, strain y ACWR sobre sRPE (Foster), solo con ≥ 75 % de sesiones con RPE (`min_srpe_coverage_pct`) y, el ACWR, por medias 7/28 días con 28 días de historial de RPE; EWMA propia sin sesgo de arranque.
- **Informe:** la gráfica de sesiones usa los 14 días completos (antes, como mucho 12 sesiones); halterofilia en ámbar al ≤ 80 % en todo el informe.
- **Plan:** entiende `80 % 1RM`, `2x20` (kg por implemento), `150,160`, `167,5` y `RPE 7-8`; en ámbar quita al menos una serie (2 × → 1 ×).
- **Historial:** las sesiones borradas en Intervals se marcan `removed=1` (no se borra ninguna fila) y dejan de contar en la carga; `--now` con otra zona horaria usa la fecha de Madrid.

**V5.5, plan ajustado (opcional, no activado):** sin `PLANNED_CSV_URL` el informe muestra la tabla de reglas por tipo de sesión según la zona del día. Si se activase, la app leería la pestaña `Planificados` de la hoja RPE CrossFit (secreto `PLANNED_CSV_URL`, con la pestaña publicada como CSV; también vale un `planned_sessions.csv` en la raíz) y ajustaría cada sesión de hoy a la decisión del día:
- **Verde:** se mantiene.
- **Ámbar:** 75 % de las series; fuerza al 90 % y halterofilia al 80 % de la carga prevista, redondeadas a 2,5 kg; WOD al 75 % del tiempo.
- **Rojo o pendiente:** técnica con PVC o barra vacía, o zona 2.

Nunca supera el RPE máximo de la decisión. Por la tarde compara lo planificado con lo hecho (por ID de actividad) y por la noche avisa de lo planificado para mañana. Columnas de `Planificados`: Fecha, Hora, Actividad, Formato (p. ej. `5 × 3`), Carga prevista (kg) (p. ej. `150–160`), Estado (vacío o `PREVISTO`; `REALIZADO…` lo excluye), RPE real, Notas, Tipo (Fuerza/Halterofilia/WOD/Técnica/Aeróbico/Movilidad), Ejercicio principal, RPE objetivo, Duración (min), Unidad de carga, ID actividad. Las actividades marcadas en la hoja como calentamiento o técnica "sin RPE" ya no cuentan como RPE pendiente.

**V5.4, calidad de datos del informe:** cada informe lleva un identificador (`GR-AAAA-MM-DD-HHMM-xxxxxx`) para poder citarlo y rastrearlo. Incluye "Qué ha cambiado desde el informe anterior", calculado a partir de `history/reports.csv`, una foto por ciclo. Las cargas de fuerza se muestran con su unidad real: total y por mancuerna, con barra, indicada en máquina o en máquina de discos. Hay una sección de acciones pendientes: RPE que faltan por ID exacto, ejercicios con la unidad sin especificar y sensaciones sin registrar. Se añaden pautas específicas para el box según la zona y las gráficas de recuperación con medias de 7 días en todas las franjas.

**Decisión operativa y registro de modelos** (`decision`, V5.2): conviven varias puntuaciones (v2 oficial, híbrido Garmin + local, v3 en pruebas, compatibilidad V2.2 y Garmin Training Readiness). `decision.registry` declara versión, rol, escala y regla de cada una, y la **zona operativa es la más conservadora entre v2, híbrido y v3**: un rojo prevalece siempre; si no hay rojo y alguno está pendiente, sin datos o es de otro día, la decisión queda pendiente. La recomendación del día es `decision.guidance`, nunca `readiness.guidance`. El v3 incluye desde V5.2 el estrés de Garmin del día anterior (completo) frente a tu línea base.

**Certificado del informe** (`certificate` en `app/readiness_v3.json`, V5.1): ciclo y runs de la cadena, hora real de sincronización (detecta Sync fuera de franja), antigüedad de cada medición por su marca temporal, huellas SHA-256 de las fuentes, coherencia v3/v2 de los valores de hoy y estado de entrega declarado como no verificable desde los datos. **Integridad del entrenamiento** (`training_integrity`): sesiones ↔ RPE emparejadas por ID exacto, RPE sin actividad, fechas discrepantes y sesiones sin RPE (no se rellenan ni estiman).

Uso local:

```bash
python -m garmin_recovery run              # escribe history/ y app/
python -m garmin_recovery run --dry-run    # solo calcula e imprime el resumen
python -m unittest discover -p 'test_*.py' # toda la batería, incluida test_app_readiness_v5
```

Umbrales en `garmin_recovery/config.py`; para personalizarlos crear `app_config.json` en la raíz con solo las claves a cambiar (p. ej. `{"sleep_need_hours": 8}`).

El modelo v3 **no sustituye** `recovery_assessment.json` ni los informes: corre en paralelo para compararlo con el v2 antes de promoverlo.

**Visibilidad (decisión del propietario, 17/10/2026):** el repositorio es **público a propósito**, porque ChatGPT lo lee para elaborar los informes. Contiene datos fisiológicos, el calendario de turnos e identificadores, pero ningún secreto: tokens y claves solo están en GitHub Secrets y en las Propiedades de Apps Script. Que sea público **no se considera un defecto de calidad** y no se penaliza en auditorías ni revisiones.

**Sync:** 08:30, 16:45, 22:45. **Objetivos de informe:** 09:05, 17:10, 23:10. **Watchdog:** 11:05, 19:20, 01:20. Los cron no prueban por sí solos que GitHub haya iniciado una ejecución. Los horarios deben evaluarse en Europe/Madrid y con marcas de tiempo reales.

## Fuente de datos y trazabilidad

- Garmin/Intervals aporta mediciones y sesiones; Google Sheets pestaña `RPE` aporta ejercicios detallados y RPE por **ID exacto** de actividad. No emparejar sólo por fecha.
- Advanced Analytics recupera el CSV y lo deja en `training_feedback.json` con huella SHA-256 y su `GITHUB_RUN_ID`.
- CrossFit Insights activado por la ejecución anterior lee **esa misma fotografía** y verifica ID, huella, hora y conteos usando GITHUB_EVENT_PATH, sin modificar YAML. Nunca debe hacer una segunda descarga independiente en un ciclo encadenado. Una ejecución manual independiente mantiene la lectura en vivo.
- `report_ready.json` acredita datos preparados, **no** entrega de una notificación en ChatGPT. Las muestras recientes se evalúan por su timestamp real, no por la fecha del archivo.
- No comparar kilos de barra, polea o máquina entre sí; el RPE general no es RIR de cada serie.

## Cómo operar y mantener

1. Para actualizar todo: ejecutar `Garmin Recovery Sync` en `main` y **esperar los cuatro workflows** en verde. No ejecutar Advanced Analytics aisladamente tras más de 60 minutos de la última Sync.
2. Confirmar que `training_feedback.json` y `crossfit_insights.json` contienen la misma actividad e ID; revisar el origen del RPE y las fechas.
3. Si falla una etapa, leer el paso concreto y conservar los últimos archivos válidos. No aumentar el límite de frescura simplemente para pintar el workflow de verde.
4. Tras editar Python o YAML, verificar `Garmin Recovery CI` en el commit; luego probar una cadena completa. No se deben borrar scripts históricos por el número que llevan en el nombre.
5. Los cambios en Google Apps Script requieren ver el `Code.gs` real y comprobar su trigger. Un `workflow_dispatch` no prueba quién lo activó.
6. Antes de declarar autonomía: tres ciclos automáticos consecutivos verificados y seguimiento mensual de la fiabilidad.

Ver [MAINTENIMIENTO.md](MAINTENIMIENTO.md) y [OPERACION_Y_VALIDACION.md](OPERACION_Y_VALIDACION.md).

## V6.3 — Aviso al móvil con ntfy

Cada ciclo que publica un informe válido envía una notificación al móvil («Informe nuevo · HH:MM», la decisión del día y el RPE máximo, con enlace al panel). No lleva datos fisiológicos.

Configuración (una vez): instala la app **ntfy** (Android/iOS), suscríbete a un tema con un nombre largo y difícil de adivinar (quien lo conozca puede leer los avisos) y guárdalo en GitHub → Settings → Secrets and variables → Actions → secreto `NTFY_TOPIC`. Sin ese secreto no se envía nada. Opcional: `NTFY_SERVER` si usas un servidor propio. Un fallo del aviso nunca bloquea la cadena.

## V6.5 — Informe completo en la app

Cada ciclo escribe además `app/informe_completo.md` (`garmin_recovery/fullreport.py`): resumen ejecutivo, siete secciones
(certificación, recuperación, sueño, FC y tendencias, CrossFit, fuerza y metcons, balance) y conclusión con traza. Sale solo de
los archivos de datos ya publicados, sin IA ni estimaciones nuevas; si falta un dato, la línea muestra «—». Se publica en la web como
`informe_completo.html` (renderizador propio en `mdhtml.py`), se enlaza desde el panel, lo comprueba `validate` y la notificación
ntfy lo abre al tocarla. `test_fullreport_v65.py` verifica estructura, cifras frente a los datos y que no se inventen fases de sueño.

## V6.8 — Informe visual y análisis de mejora

El informe completo incluye tarjetas de estado, las gráficas del ciclo (HRV con rango normal, FC, sueño y fases, carga, RPE, fuerza) y la sección 8 «Análisis de mejora física y recuperación» (`improvement.py`): tendencia de HRV y FC en reposo, cantidad y regularidad del sueño, distribución de la intensidad, respuesta a las sesiones duras, fuerza y huecos de registro, con prioridades y reglas para 7 días. Todo por reglas sobre los datos publicados; si no hay datos suficientes, lo dice y no concluye.

## V7.20 — FC en cada entrenamiento y RPE frente a FC

- **Entrenos:** cada tarjeta de fuerza, halterofilia y metcon lleva la curva de FC de la sesión (Intervals.icu, un punto cada 10 s) con la FC media y máxima. Al tocarla se abre, bajo la tarjeta, la curva completa y el tiempo por zona. La pestaña «Sesiones» sigue funcionando igual.
- **RPE frente a FC** (`garmin_recovery/session_effort.py`): el mismo esfuerzo relativo de la validación de modelos, ln(sRPE / carga de FC) estandarizado por tipo de sesión con tu historial (mediana/MAD, mínimo 5 sesiones del tipo). Con |z| ≥ 1,5 la sesión se marca «RPE alto para tu FC» o «RPE bajo para tu FC» en la app, el informe del ciclo y la sección 6 del informe completo. Es descriptivo y no cambia la decisión del día.
- **Informes:** la tabla de sesiones muestra FC media / máxima; la sección 6 del informe completo añade FC y TRIMP por sesión.
- **Sesiones sin RPE a propósito:** si la hoja deja el RPE vacío y la fila dice «sin RPE» (o es calentamiento/técnica), el historial borra el RPE que tuviera esa sesión. Solo ocurre si la instantánea de la hoja se cargó; si falla la descarga, se conserva lo anterior.

## V7.21 — Animaciones

Las gráficas de Hoy, Tendencias y Entrenos se dibujan al entrar en pantalla (líneas que se trazan, barras que crecen, puntos que aparecen después). Al abrir la FC de una sesión, la curva se traza y el anillo de zonas se rellena de Z1 a Z5. El ♥ de cada sesión late a su FC media (60 / FC segundos por latido). Con «reducir movimiento» activado en el móvil no se anima nada; los datos no cambian.

## V8.0 — Rediseño oscuro tipo WHOOP

Tema oscuro por defecto (fondo casi negro, cifras grandes, colores de zona vivos) con selector Oscuro / Claro / Automático en Sistema (se guarda en el móvil). Para tener menos letra sin perder información, las explicaciones de cada tarjeta (subtítulos, notas, lecturas, metodología) se pliegan bajo «Ver detalle» y las notas de cada sesión o día se abren al tocarlo («+ detalle»). Comprobado nodo a nodo: ningún texto desaparece, solo cambia de sitio. Palabras a la vista: Hoy 610 → 402, Tendencias 628 → 471, Entrenos 787 → 665.

## V8.1 — Más datos de Garmin y explicaciones

`garmin_recovery/garmin_insights.py` usa datos que ya se descargaban (`garmin_extended.json`) y no se mostraban:
- **Respiración nocturna** (Hoy): valor de anoche frente a tu mediana; ≥ +2 resp/min se marca, y con HRV ≥ 15 % baja, aviso combinado. Informativa: no cambia la puntuación.
- **Equilibrio de carga · 4 semanas** (Tendencias): aeróbica baja, alta y anaeróbica de Garmin con sus bandas objetivo; «cerca del techo» al 90 %.
- **VO2max** (Tendencias) y su tendencia.
- **Efecto de entrenamiento** aeróbico y anaeróbico (0–5) en cada tarjeta de Entrenos, enlazado por `external_id` de Garmin o por hora.

Cada tarjeta tiene en «Ver detalle» un «Qué mide y cómo leerlo», y Sistema incluye el glosario «Qué significa cada dato». Connect+ no añade datos fisiológicos (solo presentación, IA y nutrición); el SpO2 nocturno no está activado en el reloj.
