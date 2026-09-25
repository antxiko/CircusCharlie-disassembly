# Circus Charlie (Konami, MSX1) - desensamblado
#
# El orden de las cosas: trazar el flujo -> generar el listado -> comprobar que
# vuelve a dar la ROM byte a byte -> las comprobaciones que el reensamblado NO
# cubre.
#
# El cartucho no se distribuye: hace falta en la raiz como circus.rom, y
# `make comprueba` verifica su sha256.

ROM      = circus.rom
SHA      = 89e1badac10e65886590d55e735ed794e5ca3c41142e6637b3e7ac6b25d042c0
SRC      = src
WORK     = work
ORG      = 0x4000
TITULO   = CIRCUS CHARLIE - Konami - MSX1 - cartucho RC-712 de 16 KB en la pagina 1

all: listado verify sanity test

$(ROM):
	@echo "=================================================================="
	@echo " Falta $(ROM), y este repositorio NO lo distribuye."
	@echo ""
	@echo " Es Circus Charlie (Konami, RC-712) para MSX, 16384 bytes exactos."
	@echo " Ponlo aqui con ese nombre. Para comprobar que es el mismo:"
	@echo "     shasum -a 256 $(ROM)"
	@echo "     $(SHA)"
	@echo "=================================================================="
	@false

comprueba: $(ROM)
	@echo "$(SHA)  $(ROM)" | shasum -a 256 -c -

# El trazado sigue el flujo desde los puntos de entrada. Los que no se pueden
# deducir estaticamente -ganchos de interrupcion, destinos de saltos
# indirectos- estan declarados en el .entries, cada uno con su justificacion.
$(WORK)/circus.trace.json: $(ROM) $(SRC)/circus.entries $(SRC)/circus.nocode
	@mkdir -p $(WORK)
	python3 tools/z80trace.py $(ROM) $(ORG) $(SRC)/circus.entries \
	        $(WORK)/circus $(SRC)/circus.nocode

trace: $(WORK)/circus.trace.json

listado: $(WORK)/circus.trace.json $(SRC)/circus.notes
	python3 tools/mkasm.py $(ROM) $(ORG) $(WORK)/circus.trace.json \
	        $(SRC)/circus.notes work/msx.sym $(SRC)/circus.asm "$(TITULO)"

# La prueba que decide si el desensamblado es fiable.
verify: $(SRC)/circus.asm $(ROM)
	@sh tools/verify_build.sh $(SRC)/circus.asm $(ROM) $(ORG)

# Lo que el reensamblado NO puede cazar: que unos datos se esten leyendo como
# codigo. El binario sale identico igual, porque los bytes no cambian; lo unico
# que cambia es lo que decimos de ellos.
sanity: $(WORK)/circus.trace.json
	@echo "=================================================================="
	@echo " ningun byte declarado como datos puede salir como codigo"
	@echo "=================================================================="
	@python3 tools/check_trace.py $(WORK)/circus.trace.json $(SRC)/circus.nocode
	@python3 tools/check_datos_como_codigo.py $(WORK) $(SRC)
	@echo "=================================================================="
	@echo " ningun punto de entrada puede caer dentro de una zona de datos"
	@echo "=================================================================="
	@python3 tools/check_entradas.py $(SRC)/circus.entries $(SRC)/circus.notes \
	        $(SRC)/circus.nocode
	@echo "=================================================================="
	@echo " ni un byte del cartucho sin asignar"
	@echo "=================================================================="
	@python3 tools/presupuesto.py $(WORK) $(SRC)

densidad:
	@python3 tools/densidad.py $(SRC)/circus.asm

test:
	@echo "=================================================================="
	@echo " Tests"
	@echo "=================================================================="
	@python3 -m unittest discover -s tests -v

# Dibuja los bloques de datos graficos declarados en el .notes, para MIRARLOS.
imagenes: $(ROM)
	@mkdir -p docs/imagenes
	python3 tools/graficos.py $(ROM) $(ORG) docs/imagenes

# EL COTEJO CONTRA LA MAQUINA DE VERDAD, en dos pasos.
#
#   1. `pares`  deja correr el cartucho en openMSX y, en cada una de las cinco
#               atracciones, dispara una foto y vuelca la VRAM de los trece
#               cuadros de alrededor. Tarda un par de minutos y necesita el
#               emulador, asi que no va en `make all`.
#   2. `coteja` dibuja cada volcado con tools/vram.py y lo compara con la foto
#               PUNTO POR PUNTO. La foto va un cuadro por detras de la lectura
#               de la VRAM -medido-, y es ese cuadro el que tiene que dar cero.
OPENMSX  ?= C:/Program Files/openMSX/openmsx.exe
SERIE    ?= $(WORK)/serie
# El segundo de cada atraccion en que se dispara la foto. Se puede mover: si un
# punto suelto no casa, es que el juego estaba reescribiendo esa celda mientras
# el VDP barria la linea, y con la foto en otro instante desaparece.
INSTANTE ?= 27.9

pares: $(ROM)
	PP_SALIDA="$(CURDIR)/$(SERIE)" PP_INSTANTE=$(INSTANTE) \
	    "$(OPENMSX)" -machine Philips_VG_8020 -cart $(ROM) \
	                 -script tools/omsx_cuadro.tcl

coteja:
	@python3 tools/coteja_pixels.py --serie $(SERIE)

# LAS CINCO ATRACCIONES DESDE LA ROM, cotejadas contra la VRAM en el instante
# justo. `montaje` deja correr el cartucho y vuelca la VRAM en 0x4C3C -la
# instruccion que sigue al montaje del decorado- con el tipo de fase forzado
# ANTES del primer montaje, uno por tipo; `coteja_montaje` compara byte a byte
# lo que monta tools/graficos.py con cada volcado: tiene que dar CERO en color,
# patrones, patrones de sprite y tabla de nombres, marcador incluido.
MONTAJE  ?= $(WORK)/montaje

montaje: $(ROM)
	PP_SALIDA="$(CURDIR)/$(MONTAJE)" 	    "$(OPENMSX)" -machine Philips_VG_8020 -cart $(ROM) 	                 -script tools/omsx_montaje.tcl

coteja_montaje: $(ROM)
	@python3 tools/coteja_montaje.py $(ROM) $(MONTAJE)

# EL CARTUCHO EN MARCHA: tools/corre_circus.py contra los volcados de
# tools/omsx_arranque.tcl (work/arranque), cuadro a cuadro, a cero bytes.
ARRANQUE = work/arranque
coteja_arranque: $(ROM)
	@python3 tools/coteja_arranque.py $(ROM) $(ARRANQUE)

# LA WEB
#
# Bilingue: el ingles en docs/ y el castellano en docs/es/. Las paginas se
# escriben en markdown y se convierten con md2html.py; la portada la monta
# make_web.py, que declara las cifras medidas de ESTE cartucho.
web: $(ROM)
	python3 tools/md2html.py docs en
	python3 tools/md2html.py docs/es es
	python3 tools/make_web.py docs/imagenes docs/index.html en
	python3 tools/make_web.py docs/imagenes docs/es/index.html es
	python3 tools/check_enlaces.py docs

clean:
	rm -rf $(WORK)/circus.trace.json $(WORK)/circus.blocks

.PHONY: all comprueba trace listado verify sanity test densidad imagenes \
        pares coteja web clean montaje coteja_montaje coteja_arranque
