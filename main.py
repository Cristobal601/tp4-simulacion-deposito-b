"""Punto de entrada: python main.py"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from interfaz import VentanaPrincipal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)   # tema claro aunque Windows este en modo oscuro
    app.setStyle("Fusion")   # con este estilo se ven los colores de los encabezados
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())
