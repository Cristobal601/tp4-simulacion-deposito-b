"""Interfaz grafica (PySide6) del TP4 - Deposito B."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QScrollArea, QSpinBox, QSplitter,
                               QTableView, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from simulacion.exportar import exportar_excel
from simulacion.generador import GeneradorCongruencial
from simulacion.modelo import CLAVES, COLUMNAS, Parametros, Simulacion, formatear_dia_hora

# ---------------------------------------------------------------------------
# Colores
# ---------------------------------------------------------------------------

COLOR_ESTADO = {
    "En tarea": "#c8e6c9",
    "Trasladándose": "#bbdefb",
    "En cola": "#fff59d",
    "Interrumpido": "#ef9a9a",
    "Revisando": "#ce93d8",
    "Fuera del predio": "#e0e0e0",
    "Libre": "#f5f5f5",
    "Control temperatura": "#ffcc80",
    "Control iluminación": "#81d4fa",
    "Supervisión": "#ce93d8",
}

COLOR_GRUPO = {
    "General": "#eceff1",
    "Técnico T - tarea": "#ffe0b2", "Técnico T - traslado": "#ffe0b2", "Técnico T": "#ffe0b2",
    "Técnico I - tarea": "#b3e5fc", "Técnico I - traslado": "#b3e5fc", "Técnico I": "#b3e5fc",
    "Supervisor - eventos": "#e1bee7", "Supervisor": "#e1bee7",
    "Depósito 1": "#dcedc8", "Depósito 2": "#c5e1a5", "Depósito 3": "#aed581",
    "Estadísticas": "#fff9c4",
}

# Titulo (2 renglones: grupo + columna) y grupo de cada columna
TITULOS = [f"{grupo}\n{titulo}" for grupo, columnas in COLUMNAS for clave, titulo in columnas]
GRUPOS = [grupo for grupo, columnas in COLUMNAS for clave, titulo in columnas]


def formatear(valor):
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


# ---------------------------------------------------------------------------
# Campos de parametros: (grupo, [(atributo de Parametros, etiqueta), ...])
# Son los valores en rojo del enunciado (y los de la simulacion/generador).
# ---------------------------------------------------------------------------

CAMPOS = [
    ("Simulación", [("tiempo_x", "Tiempo a simular X (min)"),
                    ("max_iteraciones", "Máximo de iteraciones"),
                    ("desde_hora_j", "Mostrar desde la hora j (min)"),
                    ("filas_i", "Cantidad de filas i")]),
    ("Generador congruencial mixto", [("semilla", "Semilla X0"),
                                      ("a", "Constante multiplicativa a"),
                                      ("c", "Constante aditiva c"),
                                      ("m", "Módulo m")]),
    ("Técnico T (temperatura)", [("t_min", "Demora U[a;b): a"), ("t_max", "Demora U[a;b): b"),
                                 ("t_prob_extra", "Prob. de tiempo extra (Dep 1 y 2)"),
                                 ("t_extra", "Tiempo extra (min)"),
                                 ("t_tras_12", "Traslado Dep 1 → 2"), ("t_tras_23", "Traslado Dep 2 → 3"),
                                 ("t_tras_31", "Traslado Dep 3 → 1")]),
    ("Técnico I (iluminación)", [("i_demora", "Demora (min)"),
                                 ("i_tras_12", "Traslado Dep 1 → 2"), ("i_tras_23", "Traslado Dep 2 → 3"),
                                 ("i_tras_31", "Traslado Dep 3 → 1")]),
    ("Supervisor", [("s_demora", "Demora revisión (min)"), ("s_traslado", "Traslado entre depósitos"),
                    ("s_regreso", "Regresa después de (min)"),
                    ("s_prob_1", "Prob. empezar por Dep 1"), ("s_prob_2", "Prob. empezar por Dep 2"),
                    ("s_prob_3", "Prob. empezar por Dep 3")]),
    ("Depósito inicial (1ra pasada)", [("inicio_t", "Técnico T"), ("inicio_i", "Técnico I"),
                                       ("inicio_s", "Supervisor")]),
]

# Parametros que son numeros enteros (el resto admite 2 decimales)
ENTEROS = ("max_iteraciones", "filas_i", "semilla", "a", "c", "m")


# ---------------------------------------------------------------------------
# Modelo de la tabla del vector de estado
# (Qt solo pide los datos de las celdas que se ven: por eso no parpadea
#  aunque haya miles de filas)
# ---------------------------------------------------------------------------

class ModeloVector(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.filas = []

    def cargar(self, filas):
        self.beginResetModel()
        self.filas = filas
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.filas)

    def columnCount(self, parent=QModelIndex()):
        return len(CLAVES)

    def data(self, index, role=Qt.DisplayRole):
        fila = self.filas[index.row()]
        valor = fila.get(CLAVES[index.column()])
        if role == Qt.DisplayRole:
            return formatear(valor)
        if role == Qt.BackgroundRole and valor in COLOR_ESTADO:
            return QColor(COLOR_ESTADO[valor])
        if role == Qt.FontRole and fila.get("es_ultima"):
            fuente = QFont()
            fuente.setBold(True)
            return fuente
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def headerData(self, seccion, orientacion, role=Qt.DisplayRole):
        if orientacion != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return TITULOS[seccion]
        if role == Qt.BackgroundRole:
            return QColor(COLOR_GRUPO[GRUPOS[seccion]])
        return None


# ---------------------------------------------------------------------------
# Panel que dibuja la fila seleccionada: los 3 depositos y quien esta en cada uno
# ---------------------------------------------------------------------------

class PanelFila(QWidget):
    def __init__(self):
        super().__init__()
        self.titulo = QLabel("Seleccioná una fila del vector para ver el estado del sistema.")
        self.titulo.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.cajas = {}
        fila_cajas = QHBoxLayout()
        for numero in (1, 2, 3):
            caja = QLabel()
            caja.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            caja.setMinimumHeight(150)
            caja.setTextFormat(Qt.RichText)
            fila_cajas.addWidget(caja)
            self.cajas[numero] = caja
        self.supervisor = QLabel()
        self.supervisor.setTextFormat(Qt.RichText)

        layout = QVBoxLayout(self)
        layout.addWidget(self.titulo)
        layout.addLayout(fila_cajas)
        layout.addWidget(self.supervisor)

    def mostrar(self, f):
        self.titulo.setText(f"Fila {f['fila']}  ·  Reloj {formatear(f['reloj'])} min "
                            f"({f['dia_hora']})  ·  Evento: {f['evento']}")

        for numero, caja in self.cajas.items():
            estado = f[f"d{numero}_estado"]
            lineas = [f"<b style='font-size:14px'>Depósito {numero}</b>", f"Estado: <b>{estado}</b>"]
            if f[f"d{numero}_interrumpido"]:
                lineas.append(f"⏸ Interrumpido: Técnico {f[f'd{numero}_interrumpido']}")
            if f[f"d{numero}_cola"]:
                lineas.append(f"⏳ En cola: Técnico {f[f'd{numero}_cola']}")
            # Quien viene en camino a este deposito
            for nombre in ("T", "I"):
                pre = nombre.lower()
                if f[f"{pre}_estado"] == "Trasladándose" and f[f"{pre}_deposito"] == numero:
                    lineas.append(f"🚶 Viene Técnico {nombre} (llega {formatear(f[f'{pre}_llegada'])})")
            if f["s_estado"] == "Trasladándose" and f["s_deposito"] == numero:
                lineas.append(f"🚶 Viene el Supervisor (llega {formatear(f['s_llegada'])})")
            lineas.append(f"Controles: T = {f[f't_ctrl_{numero}']}  ·  I = {f[f'i_ctrl_{numero}']}")

            color = COLOR_ESTADO.get(estado, "#ffffff")
            caja.setStyleSheet(f"background:{color}; color:black; border:2px solid #555; "
                               f"border-radius:6px; padding:6px;")
            caja.setText("<br>".join(lineas))

        if f["s_estado"] == "Fuera del predio":
            texto = f"Supervisor: fuera del predio, regresa a los {formatear(f['s_regreso'])} min"
        else:
            texto = f"Supervisor: {f['s_estado']} (Dep {f['s_deposito']}), revisados en esta pasada: {f['s_revisados']}"
        self.supervisor.setText(f"{texto}  ·  <b>Reinicios hasta ahora: {f['reinicios_total']}</b>")


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TP4 Simulación - Depósito B")
        self.resize(1400, 850)
        self.filas = []

        # --- Panel izquierdo: parametros (quedan visibles despues de simular) ---
        self.campos = {}
        panel_parametros = QWidget()
        layout_parametros = QVBoxLayout(panel_parametros)
        for grupo, campos in CAMPOS:
            caja = QGroupBox(grupo)
            formulario = QFormLayout(caja)
            for atributo, etiqueta in campos:
                self.campos[atributo] = self.crear_campo(atributo)
                formulario.addRow(etiqueta, self.campos[atributo])
            layout_parametros.addWidget(caja)

        boton_simular = QPushButton("▶ Simular")
        boton_simular.setStyleSheet("font-size: 15px; padding: 8px; font-weight: bold;")
        boton_simular.clicked.connect(self.simular)
        boton_defecto = QPushButton("Valores por defecto")
        boton_defecto.clicked.connect(self.valores_por_defecto)
        boton_excel = QPushButton("Exportar vector a Excel")
        boton_excel.clicked.connect(self.exportar)
        for boton in (boton_simular, boton_defecto, boton_excel):
            layout_parametros.addWidget(boton)
        layout_parametros.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(panel_parametros)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(340)

        # --- Pestaña 1: vector de estado + panel de la fila ---
        self.modelo = ModeloVector()
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)   # selecciona la linea completa
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tabla.selectionModel().selectionChanged.connect(self.fila_seleccionada)

        self.panel_fila = PanelFila()
        division = QSplitter(Qt.Vertical)
        division.addWidget(self.tabla)
        division.addWidget(self.panel_fila)
        division.setSizes([550, 250])

        # --- Pestaña 2: resultados ---
        self.resultados = QLabel("Todavía no se simuló.")
        self.resultados.setTextFormat(Qt.RichText)
        self.resultados.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.resultados.setStyleSheet("font-size: 14px; padding: 12px;")

        # --- Pestaña 3: generador ---
        self.info_generador = QLabel()
        self.info_generador.setTextFormat(Qt.RichText)
        self.tabla_generador = QTableWidget(0, 3)
        self.tabla_generador.setHorizontalHeaderLabels(["i", "X", "Rnd"])
        self.tabla_generador.verticalHeader().setVisible(False)
        pestaña_generador = QWidget()
        layout_generador = QVBoxLayout(pestaña_generador)
        layout_generador.addWidget(self.info_generador)
        layout_generador.addWidget(self.tabla_generador)

        pestañas = QTabWidget()
        pestañas.addTab(division, "Vector de estado")
        pestañas.addTab(self.resultados, "Resultados")
        pestañas.addTab(pestaña_generador, "Generador")

        principal = QSplitter(Qt.Horizontal)
        principal.addWidget(scroll)
        principal.addWidget(pestañas)
        principal.setSizes([360, 1040])
        self.setCentralWidget(principal)

    # ---- Parametros -----------------------------------------------------------

    def crear_campo(self, atributo):
        """SpinBox entero o decimal segun el parametro."""
        valor = getattr(Parametros(), atributo)
        if atributo in ("inicio_t", "inicio_i", "inicio_s"):
            campo = QSpinBox()
            campo.setRange(1, 3)
        elif atributo in ENTEROS:
            campo = QSpinBox()
            campo.setRange(0, 10 ** 9)
        else:
            campo = QDoubleSpinBox()
            campo.setDecimals(2)
            campo.setRange(0, 10 ** 9)
        campo.setValue(valor)
        return campo

    def leer_parametros(self):
        valores = {atributo: campo.value() for atributo, campo in self.campos.items()}
        return Parametros(**valores)

    def valores_por_defecto(self):
        defecto = Parametros()
        for atributo, campo in self.campos.items():
            campo.setValue(getattr(defecto, atributo))

    # ---- Acciones -------------------------------------------------------------

    def simular(self):
        p = self.leer_parametros()
        errores = p.validar()
        if errores:
            QMessageBox.warning(self, "Parámetros inválidos", "\n".join(errores))
            return

        sim = Simulacion(p)
        sim.ejecutar()

        # Filas desde la hora j + la ultima fila (instante X)
        self.filas = list(sim.filas_mostradas)
        ultima = dict(sim.ultima_fila, es_ultima=True)
        if not self.filas or self.filas[-1]["fila"] != ultima["fila"]:
            self.filas.append(ultima)
        self.modelo.cargar(self.filas)
        self.tabla.resizeColumnsToContents()
        self.tabla.selectRow(0)

        self.mostrar_resultados(sim.resultados(), p)
        self.mostrar_generador(sim, p)

    def fila_seleccionada(self):
        filas = self.tabla.selectionModel().selectedRows()
        if filas:
            self.panel_fila.mostrar(self.filas[filas[0].row()])

    def mostrar_resultados(self, r, p):
        ct, ci = r["controles_t"], r["controles_i"]
        self.resultados.setText(f"""
            <h2>Resultados de la simulación</h2>
            <p>Tiempo simulado: <b>{formatear(r['tiempo_simulado'])} min</b>
               ({formatear_dia_hora(r['tiempo_simulado'])}) · Iteraciones: <b>{r['iteraciones']}</b>
               · Rnd usados: <b>{r['rnd_usados']}</b></p>

            <h3>1) ¿Cuántas veces algún servicio tuvo que reiniciar su tarea por el supervisor?</h3>
            <p style='font-size:20px'><b>{r['reinicios_total']}</b> reinicios
               (Técnico T: {r['reinicios_t']} · Técnico I: {r['reinicios_i']})</p>
            <p><i>Fórmula: contador que suma 1 cada vez que el supervisor llega a un depósito
               con un técnico trabajando adentro.</i></p>

            <h3>2) Total de controles de cada técnico en cada depósito</h3>
            <table border='1' cellpadding='6' cellspacing='0'>
              <tr><th></th><th>Depósito 1</th><th>Depósito 2</th><th>Depósito 3</th><th>Total</th></tr>
              <tr><th>Técnico T</th><td>{ct[1]}</td><td>{ct[2]}</td><td>{ct[3]}</td><td><b>{sum(ct.values())}</b></td></tr>
              <tr><th>Técnico I</th><td>{ci[1]}</td><td>{ci[2]}</td><td>{ci[3]}</td><td><b>{sum(ci.values())}</b></td></tr>
            </table>
            <p><i>Fórmula: contador por técnico y depósito que suma 1 en cada evento "Fin tarea"
               (una tarea interrumpida no cuenta hasta que se completa).</i></p>
        """)

    def mostrar_generador(self, sim, p):
        gen = sim.gen
        periodo = gen.periodo()
        aviso = ""
        if periodo < p.m:
            aviso = (f"<br><span style='color:#c62828'>⚠ El período ({periodo}) es menor que m ({p.m}): "
                     f"los Rnd se repiten cada {periodo} valores.</span>")
        self.info_generador.setText(
            f"<b>X(n+1) = ({p.a} · X(n) + {p.c}) mod {p.m}</b> · Semilla = {p.semilla} · "
            f"Rnd = X / m truncado a 2 decimales<br>"
            f"Período del generador: <b>{periodo}</b> · Rnd usados en esta simulación: <b>{gen.usados}</b>{aviso}")

        filas = gen.secuencia(min(max(gen.usados, periodo + 1), 5000))
        self.tabla_generador.setRowCount(len(filas))
        for numero, (i, x, rnd) in enumerate(filas):
            for columna, valor in enumerate((str(i), str(x), f"{rnd:.2f}")):
                self.tabla_generador.setItem(numero, columna, QTableWidgetItem(valor))

    def exportar(self):
        if not self.filas:
            QMessageBox.information(self, "Exportar", "Primero simulá.")
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar vector de estado",
                                              "vector_estado.xlsx", "Excel (*.xlsx)")
        if ruta:
            exportar_excel(ruta, self.filas)
            QMessageBox.information(self, "Exportar", f"Guardado en:\n{ruta}")
