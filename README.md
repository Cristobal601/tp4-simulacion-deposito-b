# TP4 Simulación – Depósito B (4K4, UTN FRC)

Simulación por eventos discretos del caso **Depósito B**, con una interfaz gráfica en PySide6.

## Cómo correrlo

```bash
pip install -r requirements.txt
python main.py
```

Pruebas automáticas:

```bash
python -m unittest discover tests
```

## Estructura (¿qué hace cada archivo?)

| Archivo | Qué tiene |
|---|---|
| `simulacion/generador.py` | Generador congruencial mixto (el único Rnd del programa) |
| `simulacion/modelo.py` | **El corazón:** parámetros, objetos (Técnico, Supervisor, Depósito), eventos y el vector de estado |
| `simulacion/exportar.py` | Exporta el vector a Excel |
| `interfaz.py` | Ventana: parámetros, tabla del vector, panel de la fila, resultados y generador |
| `main.py` | Arranca la aplicación |
| `tests/` | Pruebas (generador, primeras filas, invariantes) |
| `docs/analisis.md` | Análisis del sistema: objetos, eventos, colas, variables aleatorias y supuestos |

## Cómo leer `modelo.py` (para la exposición)

1. `Parametros`: todos los valores en rojo del enunciado, con sus valores por defecto.
2. `Tecnico`, `Supervisor` y `Deposito`: los objetos y sus atributos.
3. `Simulacion.ejecutar()`: el bucle principal. Busca el próximo evento (`proximo_evento`), avanza el reloj y llama al método del evento.
4. Hay un método por evento: `fin_tarea`, `llegada_tecnico`, `llegada_supervisor`, `fin_revision` y `regreso_supervisor`.
5. `iniciar_tarea`: es el único lugar donde se generan las demoras con Rnd.
6. `foto()`: arma una fila del vector de estado.

## Cómo trabajar en grupo

```bash
git clone <url-del-repo>
git checkout -b mi-cambio      # trabajá en una rama propia
# ... cambios ...
python -m unittest discover tests
git commit -am "Descripción del cambio"
git push -u origin mi-cambio   # y abrí un Pull Request en GitHub
```
