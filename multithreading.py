"""
Entregable 1: Implementación de Multithreading en PyQuil
Computación Cuántica - Sesión 14
Basado en el problema del Tramposo con múltiples instancias paralelas
"""

from pyquil import Program, get_qc
from pyquil.gates import H, X, CNOT, MEASURE
from pyquil.quilbase import Declare
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def crear_circuito_juego(tipo_juego='justo', num_qubits=2):
    """
    Crea un circuito cuántico según el tipo de juego
    
    Args:
        tipo_juego: 'justo', 'tramposo', o 'contraataque'
        num_qubits: número de qubits a usar
    
    Returns:
        Program: circuito cuántico compilado
    """
    p = Program()
    ro = p.declare('ro', 'BIT', num_qubits)
    
    if tipo_juego == 'justo':
        # Ambos jugadores aleatorios
        p += H(0)
        p += H(1)
    
    elif tipo_juego == 'tramposo':
        # Jugador 1 no aplica nada (siempre 0)
        # Jugador 2 aleatorio
        p += H(1)
    
    elif tipo_juego == 'contraataque':
        # Jugador 1: siempre 0
        # Jugador 2: aleatorio
        # Jugador 3: siempre 1
        p += H(1)
        p += X(2)
    
    # Mediciones
    for i in range(num_qubits):
        p += MEASURE(i, ro[i])
    
    return p


def ejecutar_simulacion_single(qc, programa, num_shots, thread_id):
    """
    Ejecuta una simulación en un thread
    
    Args:
        qc: quantum computer instance
        programa: circuito cuántico
        num_shots: número de ejecuciones
        thread_id: identificador del thread
    
    Returns:
        dict con resultados y metadatos
    """
    start_time = time.time()
    
    # Wrap del programa con el número de shots
    p_wrapped = programa.copy()
    p_wrapped.wrap_in_numshots_loop(num_shots)
    
    # Compilar y ejecutar
    executable = qc.compile(p_wrapped)
    results = qc.run(executable)
    
    end_time = time.time()
    
    return {
        'thread_id': thread_id,
        'results': results,
        'execution_time': end_time - start_time,
        'num_shots': num_shots
    }


def analizar_resultados_juego(results, num_jugadores=2):
    """
    Analiza los resultados del juego
    
    Args:
        results: array de resultados
        num_jugadores: número de jugadores
    
    Returns:
        dict con estadísticas
    """
    num_shots = len(results)
    
    if num_jugadores == 2:
        j1_gana = sum(1 for r in results if r[0] == 0 and r[1] == 1)
        j2_gana = sum(1 for r in results if r[0] == 1 and r[1] == 0)
        empates = sum(1 for r in results if r[0] == r[1])
        
        return {
            'jugador1_gana': j1_gana,
            'jugador2_gana': j2_gana,
            'empates': empates,
            'total': num_shots
        }
    
    elif num_jugadores == 3:
        j1_gana = sum(1 for r in results if r[0] == 0 and r[1] == 1)
        j2_gana = sum(1 for r in results if r[0] == 1 and r[1] == 0)
        j3_siempre_cruz = all(r[2] == 1 for r in results)
        empates = sum(1 for r in results if r[0] == r[1])
        
        return {
            'jugador1_gana': j1_gana,
            'jugador2_gana': j2_gana,
            'jugador3_siempre_cruz': j3_siempre_cruz,
            'empates': empates,
            'total': num_shots
        }


def ejecutar_multithreading(tipo_juego='justo', num_threads=4, shots_por_thread=50):
    """
    Ejecuta múltiples simulaciones en paralelo usando multithreading
    
    Args:
        tipo_juego: tipo de juego a simular
        num_threads: número de threads a usar
        shots_por_thread: número de shots por thread
    """
    print(f"\n{'='*70}")
    print(f"EJECUCIÓN MULTITHREADING: {tipo_juego.upper()}")
    print(f"{'='*70}")
    print(f"Configuración:")
    print(f"  - Número de threads: {num_threads}")
    print(f"  - Shots por thread: {shots_por_thread}")
    print(f"  - Total de simulaciones: {num_threads * shots_por_thread}")
    print(f"{'='*70}\n")
    
    # Determinar número de qubits
    num_qubits = 3 if tipo_juego == 'contraataque' else 2
    qc_name = f'{num_qubits}q-qvm'
    
    # Crear el quantum computer (se comparte entre threads)
    qc = get_qc(qc_name)
    
    # Crear el circuito (se comparte entre threads)
    programa = crear_circuito_juego(tipo_juego, num_qubits)
    
    print("Circuito cuántico a ejecutar:")
    print(programa)
    print()
    
    # Iniciar timer global
    start_global = time.time()
    
    # Ejecutar en paralelo usando ThreadPoolExecutor
    resultados_threads = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Enviar tareas a los threads
        futures = {
            executor.submit(
                ejecutar_simulacion_single, 
                qc, 
                programa, 
                shots_por_thread, 
                i
            ): i for i in range(num_threads)
        }
        
        # Recoger resultados a medida que se completan
        for future in as_completed(futures):
            thread_id = futures[future]
            try:
                result = future.result()
                resultados_threads.append(result)
                print(f"✓ Thread {result['thread_id']} completado en "
                      f"{result['execution_time']:.3f}s")
            except Exception as e:
                print(f"✗ Thread {thread_id} falló: {str(e)}")
    
    end_global = time.time()
    tiempo_total = end_global - start_global
    
    # Consolidar y analizar todos los resultados
    print(f"\n{'='*70}")
    print("ANÁLISIS DE RESULTADOS")
    print(f"{'='*70}")
    
    todos_los_resultados = []
    for r in resultados_threads:
        # Convertir QAMExecutionResult a lista de resultados usando el método recomendado
        resultados = r['results'].get_register_map().get('ro')
        todos_los_resultados.extend(resultados)
    
    estadisticas = analizar_resultados_juego(
        np.array(todos_los_resultados), 
        num_jugadores=num_qubits
    )
    
    print(f"\nEstadísticas agregadas ({estadisticas['total']} simulaciones):")
    print(f"  - Jugador 1 gana: {estadisticas['jugador1_gana']} veces "
          f"({100*estadisticas['jugador1_gana']/estadisticas['total']:.1f}%)")
    print(f"  - Jugador 2 gana: {estadisticas['jugador2_gana']} veces "
          f"({100*estadisticas['jugador2_gana']/estadisticas['total']:.1f}%)")
    print(f"  - Empates: {estadisticas['empates']} veces "
          f"({100*estadisticas['empates']/estadisticas['total']:.1f}%)")
    
    if num_qubits == 3:
        print(f"  - Jugador 3 siempre cruz: {estadisticas['jugador3_siempre_cruz']}")
    
    print(f"\nRendimiento:")
    print(f"  - Tiempo total: {tiempo_total:.3f}s")
    print(f"  - Tiempo promedio por thread: "
          f"{np.mean([r['execution_time'] for r in resultados_threads]):.3f}s")
    print(f"  - Simulaciones por segundo: "
          f"{estadisticas['total']/tiempo_total:.1f}")
    
    print(f"{'='*70}\n")
    
    return resultados_threads, estadisticas


def comparar_con_sin_multithreading():
    """
    Compara el rendimiento con y sin multithreading
    """
    print(f"\n{'='*70}")
    print("COMPARACIÓN: SECUENCIAL VS MULTITHREADING")
    print(f"{'='*70}\n")
    
    num_threads = 4
    shots_totales = 200
    shots_por_thread = shots_totales // num_threads
    
    # Ejecución secuencial (1 thread)
    print("Ejecutando versión SECUENCIAL...")
    start_seq = time.time()
    qc = get_qc('2q-qvm')
    programa = crear_circuito_juego('justo', 2)
    _ = ejecutar_simulacion_single(qc, programa, shots_totales, 0)
    tiempo_secuencial = time.time() - start_seq
    print(f"Tiempo secuencial: {tiempo_secuencial:.3f}s\n")
    
    # Ejecución paralela
    print("Ejecutando versión MULTITHREADING...")
    start_par = time.time()
    _, _ = ejecutar_multithreading('justo', num_threads, shots_por_thread)
    tiempo_paralelo = time.time() - start_par
    
    # Comparación
    speedup = tiempo_secuencial / tiempo_paralelo
    print(f"{'='*70}")
    print("RESULTADO DE LA COMPARACIÓN:")
    print(f"{'='*70}")
    print(f"  - Tiempo secuencial: {tiempo_secuencial:.3f}s")
    print(f"  - Tiempo paralelo: {tiempo_paralelo:.3f}s")
    print(f"  - Speedup: {speedup:.2f}x")
    print(f"  - Mejora: {(speedup-1)*100:.1f}%")
    print(f"{'='*70}\n")


def main():
    """
    Función principal que ejecuta todas las demostraciones
    """
    print("\n" + "="*70)
    print("ENTREGABLE 1: MULTITHREADING EN PYQUIL")
    print("Computación Cuántica - Sesión 14")
    print("="*70)
    
    # Ejecutar diferentes tipos de juego con multithreading
    ejecutar_multithreading(tipo_juego='justo', num_threads=4, shots_por_thread=50)
    ejecutar_multithreading(tipo_juego='tramposo', num_threads=4, shots_por_thread=50)
    ejecutar_multithreading(tipo_juego='contraataque', num_threads=4, shots_por_thread=50)
    
    # Comparación de rendimiento
    comparar_con_sin_multithreading()
    
    print("\n" + "="*70)
    print("CONCLUSIONES:")
    print("="*70)
    print("✓ Los objetos del quantum computer se comparten entre threads")
    print("✓ Multithreading permite ejecutar múltiples simulaciones en paralelo")
    print("✓ Mejora significativa en el rendimiento para grandes volúmenes")
    print("✓ Útil para análisis estadísticos o exploración de parámetros")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()