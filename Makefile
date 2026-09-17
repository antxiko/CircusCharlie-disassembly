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

.PHONY: all comprueba trace listado verify sanity test densidad imagenes web clean
