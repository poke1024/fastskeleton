import sys
import io
import time
import PIL.Image
import numpy as np
import networkx as nx
import shapely.geometry

from PySide2 import QtGui, QtCore, QtWidgets

from skeleton import FastSkeleton


class Canvas(QtWidgets.QWidget):
	def __init__(self):
		super(Canvas, self).__init__()

		self._pixmap = QtGui.QPixmap(512, 512)
		self._pixmap.fill()

		self._last_pos = None
		self._pen_width = 3

		self.setMinimumSize(QtCore.QSize(512, 512))

		self._graph = None
		self._graph_simplify = 0
		self._graph_thick = True

	def set_graph(self, graph):
		self._graph = graph
		self.update()
		self.repaint()  # workaround for macOS

	def set_graph_simplify(self, simplify):
		self._graph_simplify = simplify
		self.update()
		self.repaint()  # workaround for macOS

	def set_graph_thick(self, thick_lines):
		self._graph_thick = thick_lines
		self.update()
		self.repaint()  # workaround for macOS

	@property
	def pixels(self):
		array = QtCore.QByteArray()
		buffer = QtCore.QBuffer(array)
		buffer.open(QtCore.QIODevice.WriteOnly)
		self._pixmap.save(buffer, "PNG")
		return np.array(PIL.Image.open(io.BytesIO(array.data())).convert("L"))

	def invert(self):
		self._graph = None
		im = self._pixmap.toImage()
		im.invertPixels()
		self._pixmap.convertFromImage(im)
		self.update()
		self.repaint()  # workaround for macOS

	@property
	def pen_width(self):
		return self._pen_width

	def set_pen_width(self, width):
		self._pen_width = width

	def clear(self):
		self._graph = None
		self._pixmap.fill()
		self.update()
		self.repaint()  # workaround for macOS

	def _create_pen(self):
		pen = QtGui.QPen()
		pen.setWidth(self._pen_width)
		pen.setColor(QtGui.QColor("black"))
		pen.setCapStyle(QtCore.Qt.RoundCap)
		return pen

	def paintEvent(self, e):
		qp = QtGui.QPainter()
		qp.begin(self)
		qp.drawPixmap(QtCore.QPoint(0, 0), self._pixmap)

		if self._graph is not None:
			node_pen = QtGui.QPen()
			node_pen.setWidth(2)
			node_pen.setColor(QtGui.QColor("indianred"))
			node_pen.setCapStyle(QtCore.Qt.RoundCap)

			edge_pen = QtGui.QPen()
			edge_pen.setColor(QtGui.QColor("skyblue"))
			edge_pen.setCapStyle(QtCore.Qt.RoundCap)

			for _, _, attr in self._graph.edges.data():
				line = shapely.geometry.LineString(attr["path"])
				p = line.simplify(self._graph_simplify).coords
				for u, v, t in zip(p, p[1:], attr["time"]):
					edge_pen.setWidth(t if self._graph_thick else 2)
					qp.setPen(edge_pen)

					qp.drawLine(
						QtCore.QPoint(*u),
						QtCore.QPoint(*v))

			attr = nx.get_node_attributes(self._graph, "time")
			for x, y in self._graph.nodes:
				t = attr[(x, y)]
				qp.setPen(node_pen)
				qp.drawEllipse(QtCore.QPoint(x, y), t, t)

		qp.end()

	def mousePressEvent(self, e):
		p = e.pos()
		self._last_pos = p

		qp = QtGui.QPainter()
		qp.begin(self._pixmap)
		qp.setPen(self._create_pen())
		qp.drawPoint(p.x(), p.y())
		qp.end()

		self._graph = None
		self.update()

	def mouseReleaseEvent(self, e):
		pass

	def mouseMoveEvent(self, e):
		p = e.pos()

		qp = QtGui.QPainter()
		qp.begin(self._pixmap)
		qp.setPen(self._create_pen())
		qp.drawLine(self._last_pos.x(), self._last_pos.y(), p.x(), p.y())
		qp.end()

		self._last_pos = p

		self.update()


class QHLine(QtWidgets.QFrame):
	def __init__(self):
		super(QHLine, self).__init__()
		self.setFrameShape(QtWidgets.QFrame.HLine)
		self.setFrameShadow(QtWidgets.QFrame.Sunken)


class Demo(QtWidgets.QWidget):

	def __init__(self):
		super(Demo, self).__init__()

		self._skeleton = FastSkeleton()
		self._first_run = True

		self._canvas = None
		self.initUI()

	def initUI(self):
		canvas = Canvas()
		self._canvas = canvas

		toolbar = QtWidgets.QVBoxLayout()

		clear_button = QtWidgets.QPushButton("Clear")
		toolbar.addWidget(clear_button)
		clear_button.clicked.connect(canvas.clear)

		invert_button = QtWidgets.QPushButton("Invert")
		toolbar.addWidget(invert_button)
		invert_button.clicked.connect(canvas.invert)

		pen_label = QtWidgets.QLabel()
		pen_label.setText("pen width")
		toolbar.addWidget(pen_label)

		pen_slider = QtWidgets.QSlider()
		pen_slider.setOrientation(QtCore.Qt.Horizontal)
		pen_slider.setTickInterval(1)
		pen_slider.setMinimum(1)
		pen_slider.setMaximum(30)
		pen_slider.setValue(canvas.pen_width)
		toolbar.addWidget(pen_slider)
		pen_slider.valueChanged.connect(canvas.set_pen_width)

		toolbar.addWidget(QHLine())

		skeleton_button = QtWidgets.QPushButton("Find Skeleton")
		toolbar.addWidget(skeleton_button)
		skeleton_button.clicked.connect(self._compute_skeleton)

		toolbar.addWidget(QHLine())

		resolution_label = QtWidgets.QLabel()
		resolution_label.setText("simplify")
		toolbar.addWidget(resolution_label)

		simplify_slider = QtWidgets.QSlider()
		simplify_slider.setOrientation(QtCore.Qt.Horizontal)
		simplify_slider.setTickInterval(1)
		simplify_slider.setMinimum(1)
		simplify_slider.setMaximum(30)
		simplify_slider.setValue(1)
		toolbar.addWidget(simplify_slider)
		simplify_slider.valueChanged.connect(canvas.set_graph_simplify)

		thick_lines_checkbox = QtWidgets.QCheckBox()
		thick_lines_checkbox.setText("Thick Lines")
		thick_lines_checkbox.setChecked(True)
		toolbar.addWidget(thick_lines_checkbox)
		thick_lines_checkbox.clicked.connect(
			lambda e: canvas.set_graph_thick(thick_lines_checkbox.isChecked()))

		toolbar.addStretch()
		info_label = QtWidgets.QLabel()
		info_label.setText("")
		toolbar.addWidget(info_label)
		self._info_label = info_label

		layout = QtWidgets.QHBoxLayout()

		canvas.setSizePolicy(QtWidgets.QSizePolicy(
			QtWidgets.QSizePolicy.Preferred,
			QtWidgets.QSizePolicy.Expanding))

		layout.addWidget(canvas)
		layout.addLayout(toolbar)

		self.setLayout(layout)

		self.setGeometry(300, 300, 768, 550)
		self.setWindowTitle('FastSkeleton Demo')
		self.show()

	def _compute_skeleton(self):
		t0 = time.time()
		graph = self._skeleton(self._canvas.pixels < 0xff, time=True)
		t1 = time.time()
		if not self._first_run:  # ignore numba compilation run
			self._info_label.setText("computation took %d ms." % (1000 * (t1 - t0)))
		self._first_run = False
		self._canvas.set_graph(graph)


def main():
	app = QtWidgets.QApplication(sys.argv)
	demo = Demo()
	sys.exit(app.exec_())


if __name__ == '__main__':
	main()
