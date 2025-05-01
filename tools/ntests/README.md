# ntests tool

Herramienta que automatiza la **búsqueda de clases tests** para la diferencia entre 2 ramas.

Esta herramienta, aunque es generizable, está diseñada para un proyecto específico y para ser usada en Windows.

## Uso

### Prerequisitos
- **Windows**
- Tener instalado **Git** (siendo usado en el proyecto)
- Tener instalado **GitBash**

### Instalación

```sh
git clone https://github.com/femartinezg/sf-tools.git
```

### Uso

En **GitBash**:
```sh
./ntests.sh -h
```

La herramienta debe ejeuctarse en el directorio principal del proyecto SF y las clases deben estar contenidas en *./force-app/main/default/classes/* para que el script funcione correctamente.

### Aliases (recomendable crear ambos)

Para crear alias en GitBash:

1. Ir a tu carpeta personal (C:\Users\\\<user>) y mostrar archivos ocultos.
2. Editar el archivo .bashrc (crearlo si no existe)
3. Añadir la siguiente linea: alias nt='\<path>/\<to>/\<tool>/ntests.sh'

Para crear en cmd:

1. Ir a tu carpeta personal (C:\Users\\\<user>).
2. Editar el archivo macros.doskey (crearlo si no existe)
3. Añadir la siguiente linea: nt="C:\Program Files\Git\bin\bash.exe" -c "\<path>/\<to>/\<tool>/ntests.sh $*"
4. Ejecutar el siguiente comando en cmd: C:\WINDOWS\system32\cmd.exe /k "DOSKEY /macrofile=C:\Users\\\<user>\macros.doskey"

### Excepciones a la convención de nombres de clases test

Se pueden añadir excepciones a la convención de clases test <nombre_clase>Test.
Para ello, se debe modificar el archivo **ntests_exceptions.conf** con las clases
que no requieran test y con las que no siguan la convención.

## Limitaciones

- Si una clase está cubierta por varias clases tests, la herramienta encotrará todas las que hagan match con la convención de nombres, sin embargo, no se puede añadir la misma clase varias veces al archivo de excepciones.
- Si se usan ambos parámetros -s y -t es posible que la herramienta no devuelva todos los tests. Esto se debe a que utiliza los archivos locales para buscar las clases test por lo que depende de la rama actual en la que te encuentres. El uso habitual será únicamente con el parámetro -t por lo que no ocurrirá este problema.
- No se ha probado en otros sistemas fuera de Windows ni con otros clientes Bash fuera de GitBash.