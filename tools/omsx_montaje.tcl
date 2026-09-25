# omsx_montaje.tcl - La VRAM de cada atraccion JUSTO AL ACABAR EL MONTAJE.
#
# Los volcados de tools/omsx_cuadro.tcl son de la partida en marcha: llevan el
# marcador, el trampolin o las bolas alli donde el juego los tenga en ese
# instante, y el aro ya subido. Contra eso, un dibujo desde la ROM no puede
# dar cero aunque este bien. Este guion vuelca la VRAM en 0x4C3C, que es la
# instruccion que sigue al `call monta_el_decorado_de_la_fase` de 0x4C39: el
# decorado esta entero y el juego todavia no ha movido nada. Es el estado con
# el que tools/graficos.py tiene que dar CERO bytes de diferencia.
#
# Y EL TIPO SE FUERZA ANTES DEL PRIMER MONTAJE, no despues. Forzar la escena 9
# con la partida ya en marcha (como hace tools/omsx_atracciones.tcl) deja en el
# tercio 1 de patrones y de color lo que pinto el primer numero, en las celdas
# que el decorado forzado no toca: medido, cientos de bytes que ni son del
# decorado ni los pinta nadie. Aqui, un punto de ruptura en 0x4C39 -justo
# antes del `call`- escribe el tipo en (0xE052), de modo que el PRIMER montaje
# de la partida ya es el del tipo pedido y la VRAM viene limpia del menu. Un
# ciclo por tipo, con REINICIO entre uno y otro.
#
#   "C:/Program Files/openMSX/openmsx.exe" -machine Philips_VG_8020 \
#       -cart circus.rom -script tools/omsx_montaje.tcl
#
# Deja en work/montaje/ vram_tipo_N.bin e info_tipo_N.txt, N de 0 a 4; y en la
# carpeta de openMSX un savestate circus_tipo_N por numero y el replay
# circus_cinco_numeros, para no tener que rearrancar el emulador nunca mas.

proc opcion {nombre porDefecto} {
    global env
    if {[info exists env($nombre)]} { return $env($nombre) }
    return $porDefecto
}

set ::SALIDA [opcion PP_SALIDA {C:/Users/Antxiko/Documents/DES_ASM/CIRCUS_DISAM/work/montaje}]
file mkdir $::SALIDA
set ::bp_fuerza {}
set ::bp_vuelca {}
set ::tipo_pedido 0

proc fuerza_el_tipo {} {
    debug write memory 0xE052 $::tipo_pedido
    if {$::bp_fuerza ne {}} { debug remove_bp $::bp_fuerza; set ::bp_fuerza {} }
}

proc vuelca_montaje {} {
    set tipo [debug read memory 0xE052]
    set datos [debug read_block VRAM 0 16384]
    set f [open $::SALIDA/vram_tipo_$tipo.bin w]
    fconfigure $f -translation binary
    puts -nonewline $f $datos
    close $f
    set r {}
    for {set k 0} {$k < 8} {incr k} {
        lappend r [format %02X [debug read {VDP regs} $k]]
    }
    set f [open $::SALIDA/info_tipo_$tipo.txt w]
    puts $f [format {pc %04X} [reg PC]]
    puts $f [format {tiempo %s} [machine_info time]]
    puts $f [format {regs %s} [join $r { }]]
    foreach {nombre dir} {escena 0xE000 modo 0xE002 vidas 0xE050 fase_bcd 0xE051
                          tipo_de_fase 0xE052 numero_de_fase 0xE056
                          bonificacion_bajo 0xE057 bonificacion_alto 0xE058
                          tanda 0xE05B} {
        puts $f [format {%s %d} $nombre [debug read memory $dir]]
    }
    close $f
    puts [format {volcado tipo %d en 0x4C3C, t=%s} $tipo [machine_info time]]
    if {$::bp_vuelca ne {}} { debug remove_bp $::bp_vuelca; set ::bp_vuelca {} }
    # Y UN SAVESTATE, para no volver a arrancar el emulador por esto: cualquier
    # medida posterior sobre este numero parte de `loadstate circus_tipo_N`.
    catch { savestate circus_tipo_$tipo }
}

proc pulsa {} {
    keymatrixdown 8 0x01
    after time 0.4 suelta
}
proc suelta {} {
    keymatrixup 8 0x01
}

set ::tipos {0 1 2 3 4}
set ::i 0

proc siguiente {} {
    if {$::i >= [llength $::tipos]} {
        # el replay entero, con los cinco numeros seguidos: se puede recorrer
        # con `reverse goto <segundos>` sin rearrancar nada
        catch { reverse savereplay circus_cinco_numeros }
        exit
    }
    set ::tipo_pedido [lindex $::tipos $::i]
    incr ::i
    reset
    # los dos puntos de ruptura, puestos antes de que nadie pulse nada
    after time 1.0 {
        set ::bp_fuerza [debug set_bp 0x4C39 {} {fuerza_el_tipo}]
        set ::bp_vuelca [debug set_bp 0x4C3C {} {vuelca_montaje}]
    }
    after time 16.0 { pulsa }
    after time 18.0 { pulsa }
    after time 20.0 { pulsa }
    after time 24.0 { siguiente }
}

catch { reverse start }
after time 1.0 { siguiente }

after realtime 600 {
    puts {PERRO GUARDIAN a los 600 s reales}
    exit
}
