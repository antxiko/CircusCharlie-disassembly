# omsx_atracciones.tcl - Vuelca la VRAM de LAS CINCO ATRACCIONES, una por una.
#
# EL FALLO QUE ESTO ARREGLA, y que costo una tanda de imagenes malas:
# forzar la escena 10 una vez tras otra SIN REINICIAR deja en la VRAM lo que
# habia pintado la atraccion anterior. El decorado nuevo se monta encima, pero
# las celdas que ese decorado NO toca siguen con lo de antes: en la cuerda
# floja salia basura entre el protagonista y el mono. Se veia a simple vista, y
# el cotejo byte a byte no lo habria cazado porque el volcado era "de verdad":
# de verdad, pero de un estado que el juego nunca alcanza.
#
# Asi que entre atraccion y atraccion se REINICIA la maquina. Es mas lento y es
# lo unico honesto: cada volcado sale de un arranque limpio.
#
# El resto del truco sale del listado, no de probar: la ESCENA 10 (0x41A7) es
# la que llama a monta_la_fase (0x41B2), y monta_el_decorado_de_la_fase lee el
# tipo de (0xE052) sin recalcularlo. O sea:
#
#   1. escribir el tipo en 0xE052
#   2. poner el plazo de 0xE004 a 1, que es lo que la escena 10 espera
#      (`dec (hl) / ret nz`)
#   3. poner 0xE000 a 10 y dejar correr un par de segundos
#
# Que ha salido en cada volcado lo dice el info_NN.txt, que guarda el (0xE052)
# leido DESPUES. No se decide mirando el dibujo.

proc opcion {nombre porDefecto} {
    global env
    if {[info exists env($nombre)]} { return $env($nombre) }
    return $porDefecto
}

set ::SALIDA [opcion PP_SALIDA {C:/Users/Antxiko/Documents/DES_ASM/CIRCUS_DISAM/work/actos}]
file mkdir $::SALIDA
set ::n 0

proc vuelca {etiqueta} {
    set i [format %02d $::n]
    incr ::n
    set datos [debug read_block VRAM 0 16384]
    set f [open $::SALIDA/vram_$i.bin w]
    fconfigure $f -translation binary
    puts -nonewline $f $datos
    close $f
    set r {}
    for {set k 0} {$k < 8} {incr k} {
        lappend r [format %02X [debug read {VDP regs} $k]]
    }
    set f [open $::SALIDA/info_$i.txt w]
    puts $f [format {etiqueta %s} $etiqueta]
    puts $f [format {tiempo %s} [machine_info time]]
    puts $f [format {regs %s} [join $r { }]]
    foreach {nombre dir} {escena 0xE000 modo 0xE002 reloj 0xE003
                          tipo_de_fase 0xE052 numero_de_fase 0xE056
                          tanda 0xE05B} {
        puts $f [format {%s %d} $nombre [debug read memory $dir]]
    }
    close $f
    catch { screenshot -raw $::SALIDA/pant_$i.png }
}

proc pulsa {} {
    keymatrixdown 8 0x01
    after time 0.4 suelta
}
proc suelta {} {
    keymatrixup 8 0x01
}

proc monta_tipo {tipo} {
    # LA ESCENA 9, NO LA 10. Este es el fallo que dejaba basura en pantalla:
    # la que monta la fase es la 10 (0x41A7 -> monta_la_fase), pero la que
    # LIMPIA es la 9 (0x4165 -> limpia_la_pantalla), y ademas encadena sola a
    # la 10 con su `jr` de 0x417F. Saltando a la 10 se salta la limpieza, y lo
    # que la fase nueva no repinta se queda de la anterior.
    debug write memory 0xE052 $tipo
    debug write memory 0xE004 1
    debug write memory 0xE000 9
}

# --- calendario -------------------------------------------------------------
# Un ciclo completo por atraccion: reset, arranque, partida, se fuerza el tipo
# y se vuelca. Los tiempos son de reloj EMULADO.
set ::tipos {0 1 2 3 4}
set ::i 0

proc siguiente {} {
    if {$::i >= [llength $::tipos]} { exit }
    set tipo [lindex $::tipos $::i]
    incr ::i
    reset
    after time 16.0 { pulsa }
    after time 18.0 { pulsa }
    after time 20.0 { pulsa }
    after time 24.0 [list monta_tipo $tipo]
    after time 27.5 [list vuelca acto_$tipo]
    after time 29.0 { siguiente }
}

after time 1.0 { siguiente }

after realtime 600 {
    puts {PERRO GUARDIAN a los 600 s reales}
    exit
}
