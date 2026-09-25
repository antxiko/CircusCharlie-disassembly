# omsx_arranque.tcl - Los PRIMEROS CUADROS de cada atraccion: RAM y VRAM.
#
# tools/omsx_montaje.tcl vuelca en 0x4C3C, con el decorado recien montado y
# sin nadie en pista. Este guion sigue adelante con el mismo tipo forzado y
# vuelca en 0x4CA9 -el vuelco de los 128 bytes de sprites de 0xE0B0 a 0x3B00-
# en los cuadros que diga CUADROS, para ver que pone el juego en pista y en
# que orden: el jugador, su animal y los obstaculos.
#
#   "C:/Program Files/openMSX/openmsx.exe" -machine Philips_VG_8020 #       -cart circus.rom -script tools/omsx_arranque.tcl
#
# Deja en work/arranque/ tipo_N_cK.vram (16 KB) y tipo_N_cK.ram (0xE000..0xE3FF).

proc opcion {nombre porDefecto} {
    global env
    if {[info exists env($nombre)]} { return $env($nombre) }
    return $porDefecto
}

set ::SALIDA [opcion PP_SALIDA {C:/Users/Antxiko/Documents/DES_ASM/CIRCUS_DISAM/work/arranque}]
file mkdir $::SALIDA
set ::bp_fuerza {}
set ::bp_vuelca {}
set ::tipo_pedido 0

proc fuerza_el_tipo {} {
    debug write memory 0xE052 $::tipo_pedido
    if {$::bp_fuerza ne {}} { debug remove_bp $::bp_fuerza; set ::bp_fuerza {} }
}

set ::CUADROS [opcion PP_CUADROS {1 2 3 5 10 25 50 100 200}]
set ::cuadro 0

proc empieza_a_contar {} {
    set ::cuadro 0
    if {$::bp_vuelca ne {}} { debug remove_bp $::bp_vuelca; set ::bp_vuelca {} }
    set ::bp_vuelca [debug set_bp 0x4CA9 {} {cuenta_cuadro}]
}

proc vuelca {nombre} {
    set f [open $::SALIDA/$nombre.vram w]
    fconfigure $f -translation binary
    puts -nonewline $f [debug read_block VRAM 0 16384]
    close $f
    set f [open $::SALIDA/$nombre.ram w]
    fconfigure $f -translation binary
    puts -nonewline $f [debug read_block memory 0xE000 1024]
    close $f
}

proc cuenta_cuadro {} {
    incr ::cuadro
    if {[lsearch $::CUADROS $::cuadro] >= 0} {
        vuelca [format {tipo_%d_c%03d} $::tipo_pedido $::cuadro]
        puts [format {tipo %d cuadro %d t=%s} $::tipo_pedido $::cuadro [machine_info time]]
    }
    if {$::cuadro >= [lindex $::CUADROS end]} {
        debug remove_bp $::bp_vuelca; set ::bp_vuelca {}
    }
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
        exit
    }
    set ::tipo_pedido [lindex $::tipos $::i]
    incr ::i
    reset
    # los dos puntos de ruptura, puestos antes de que nadie pulse nada
    after time 1.0 {
        set ::bp_fuerza [debug set_bp 0x4C39 {} {fuerza_el_tipo}]
        set ::bp_montado [debug set_bp 0x4C3C {} {vuelca tipo_${::tipo_pedido}_c000; debug remove_bp $::bp_montado; empieza_a_contar}]
    }
    after time 16.0 { pulsa }
    after time 18.0 { pulsa }
    after time 20.0 { pulsa }
    after time 30.0 { siguiente }
}

after time 1.0 { siguiente }

after realtime 600 {
    puts {PERRO GUARDIAN a los 600 s reales}
    exit
}
