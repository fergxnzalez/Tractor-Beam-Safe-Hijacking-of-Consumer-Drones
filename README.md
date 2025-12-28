# Tractor Beam: Safe-Hijacking of Consumer Drones 🚁🛰️

Este repositorio contiene una implementación funcional de las estrategias de secuestro de drones mediante el engaño de señales GPS (**GPS Spoofing**), basada en la investigación: *"Tractor Beam: Safe-hijacking of Consumer Drones with Adaptive GPS Spoofing"*.

El proyecto utiliza el simulador **ArduPilot (SITL)** y la librería **DroneKit** para demostrar cómo un atacante puede manipular la trayectoria de drones de **Tipo I** y **Tipo II** de forma segura y precisa.

## 📋 Contenido del Repositorio

* `web_hijack.py`: Servidor backend desarrollado en Flask que gestiona la conexión con el dron, el cálculo de vectores y la inyección de parámetros de simulación.
* `templates/index.html`: Interfaz web interactiva diseñada con CSS moderno para introducir coordenadas de objetivo ($p_{target}$) y monitorear el estado del ataque.

---

## 🚀 Estrategias de Secuestro Implementadas

### Estrategia A: Contra Drones Tipo I (Estáticos)
Dirigida a drones que utilizan el GPS para mantener una posición fija (ej. DJI Phantom en modo Loiter o PosHold).
* **Mecánica**: Se inyecta un desplazamiento gradual en los parámetros de error GPS (`SIM_GPS1_GLTCH_X/Y`).
* **Efecto**: El dron intenta compensar el error percibido volando físicamente en la dirección opuesta al glitch, permitiendo "arrastrarlo" hacia una ubicación deseada.

### Estrategia B: Contra Drones Tipo II (Autopiloto)
Diseñada para drones que ejecutan misiones autónomas siguiendo waypoints (ej. Parrot Bebop 2).
* **Mecánica**: Manipulación del algoritmo de seguimiento de ruta (*path-following*).
* **Fórmula de Secuestro**: El script calcula la posición falsa ($a$) mediante la ecuación vectorial del paper:
  $$a = p_{waypoint} + k \cdot (p_{target} - p_{init})$$
  donde $k$ es un parámetro negativo que proyecta la mentira GPS al lado opuesto del objetivo real.
* **Actualización Dinámica**: El backend utiliza un hilo de ejecución para recalcular el glitch en tiempo real, corrigiendo la deriva y mejorando la precisión del secuestro.



---

## 🛠️ Requisitos e Instalación

1.  **ArduPilot SITL**: Entorno de simulación configurado.
2.  **Dependencias de Python**:
    ```bash
    pip install flask dronekit
    ```
3.  **Compatibilidad**: El script incluye un parche automático para el error `AttributeError: module 'collections' has no attribute 'MutableMapping'` común en Python 3.10+.

---

## 💻 Instrucciones de Uso

1.  **Iniciar SITL**:
    ```bash
    sim_vehicle.py -v ArduCopter --console --map
    ```
2.  **Preparar el Dron**: 
    * Carga una misión con waypoints en Mission Planner y pulsa **"Escribir WPs"**.
    * Despega el dron y cámbialo a modo `AUTO` para que comience la misión.
3.  **Lanzar el Servidor**:
    ```bash
    python3 web_hijack.py
    ```
4.  **Interfaz de Control**: Accede a `http://localhost:5000` en tu navegador.
    * Introduce las coordenadas de destino.
    * Pulsa **EJECUTAR SECUESTRO**.
    * Usa **DESHACER GLITCH** para liberar el dron, volver a modo `GUIDED` y ver el reporte de precisión final.

---

## 📊 Validación de Resultados

Al finalizar el ataque, el sistema utiliza la **fórmula de Haversine** para calcular la distancia entre la posición real del dron y el objetivo solicitado. 
* El ataque se marca como **LOGRADO** si la distancia final es menor a 15 metros, cumpliendo con los estándares de precisión reportados en el estudio (error angular promedio de $5.13^{\circ}$).

---

## ⚠️ Descargo de Responsabilidad
Este proyecto tiene fines estrictamente educativos y de investigación en ciberseguridad. El uso de técnicas de GPS Spoofing en entornos reales puede ser ilegal y peligroso.

---

## ⚖️ Licencia, Privacidad y Uso Ético

### Licencia
Este proyecto está bajo la Licencia **MIT**. Esto significa que puedes usar, copiar y modificar el software libremente, siempre que se mantenga el aviso de copyright y la renuncia de responsabilidad. Para más detalles, consulta el archivo `LICENSE` en este repositorio.

### Uso Ético y Responsabilidad
Este software ha sido desarrollado con fines exclusivamente **académicos y de investigación**. El objetivo es ayudar a la comunidad de ciberseguridad a entender las vulnerabilidades de los drones comerciales y desarrollar mejores sistemas de defensa (como detección de spoofing y navegación inercial robusta).

* **Prohibición de Uso Malicioso:** El autor no se hace responsable del mal uso de este código en entornos reales.
* **Legalidad:** El GPS Spoofing y la interferencia de señales son actividades reguladas y, en muchos casos, ilegales. Este código debe ejecutarse **únicamente en entornos de simulación (SITL)**.

### Privacidad y Seguridad
Este proyecto no recopila datos personales. Sin embargo, al trabajar con sistemas de telemetría y drones:
1.  **Seguridad de Red:** Se recomienda ejecutar el servidor Flask en una red local segura o aislada.
2.  **Logs de Vuelo:** Asegúrate de no subir archivos de telemetría (`.tlog` o `.bin`) que puedan contener coordenadas reales de tu ubicación física si realizas pruebas fuera de la simulación.
