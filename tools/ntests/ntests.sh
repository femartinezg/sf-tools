#!/bin/bash

# Variables
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
declare -A EXCEPTIONS
while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue
    value=$(echo "$value" | tr -d '\r')
    EXCEPTIONS["$key"]="$value"
done < "$SCRIPT_DIR/ntests_exceptions.conf"

source=
target=
copy=1
format="pr"

# Funciones
function ctrl_c() {
    echo
    echo "Saliendo..."
    cleanup
    exit 1
}

function help() {
    echo
    echo "Uso: $0 [-s source_branch] [-t target_branch] [-l] [-f formato]"
    echo "  -s  Especifica la rama origen para comparar. Si no se especifica se utilza la rama actual. Si no se especifca ni -s ni -t se obtiene el diff local."
    echo "  -t  Especifica la rama destino para comparar. Si no se especifica se utiliza la rama actual. Si no se especifca ni -s ni -t se obtiene el diff local."
    echo "  -l  Muestra los resultados por la salida estándar en lugar de copiar al portapapeles."
    echo "  -f  Especifica el formato de salida de los resultados. Opciones disponibles: pr (por defecto), list, sf."
    echo
    echo "Ejemplos:"
    echo "  $0 -s origin/feature/US123456"
    echo "  $0 -s feature/US654321 -t origin/master -l -f list"
    echo
}

function cleanup() {
    if [[ -n "$tempDir" ]]; then
        rm -rf "$tempDir"
    fi
}

function parse_args() {
    local opt
    while getopts "s:t:lf:h" opt; do
        case $opt in
            s) source=$OPTARG ;;
            t) target=$OPTARG ;;
            l) copy= ;;
            f) format=$OPTARG ;;
            h) help; exit 0 ;;
            ?) help; exit 1 ;;
        esac
    done

    if [[ "$format" != "pr" && "$format" != "list" && "$format" != "sf" ]]; then
        echo "Formato no válido."
        help
        exit 1
    fi
}

function check_dependencies() {
    local missing=0
    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Error: El comando '$cmd' no está instalado o no está en el PATH."
            missing=1
        fi
    done
    if [[ $missing -gt 0 ]]; then
        echo "Por favor, instala los comandos faltantes antes de continuar."
        exit 1
    fi
}

function branch_exists() {
    git show-ref --verify --quiet "refs/heads/$1" || git show-ref --verify --quiet "refs/remotes/$1"
}

function check_branches_exist() {
    if [[ -n "$source" ]] && ! branch_exists "$source"; then
    echo "Error: La rama source '$source' no existe."
    exit 1
    fi

    if [[ -n "$target" ]] && ! branch_exists "$target"; then
        echo "Error: La rama target '$target' no existe."
        exit 1
    fi
}

function create_temp_dir() {
    tempDir=$(mktemp -d)
    if [[ $? -ne 0 ]]; then
        echo "Error al crear directorio temporal"
        exit 1
    fi
    if [[ ! -w "$tempDir" ]]; then
        echo "Error: No tienes permisos de escritura en el directorio temporal."
        exit 1
    fi
}

function get_apex_tests() {
    ls --format single-column force-app/main/default/classes | grep '\.cls$' | grep -i test | sed 's|force-app/main/default/classes/||;s/\.cls//g' > "$tempDir/apex_tests"
}

function get_apex_diff() {
    local arg=
    if [[ ! -z "$target" && ! -z "$source" ]]; then
        arg="$target...$source"
    elif [[ ! -z "$target" ]]; then
        arg="$target..."
    elif [[ ! -z "$source" ]]; then
        arg="...$source"
    fi
    # echo "DEBUG: git diff --name-only "$arg" 2>/dev/null"
    if [[ -z "$arg" ]]; then
        git diff --name-only 2>/dev/null | grep '^.*\.cls$' | sed 's/force-app\/main\/default\/classes\///g' | sed 's/\.cls//g' > "$tempDir/apex_diff"
        git ls-files --others --exclude-standard 2>/dev/null | grep '^.*\.cls$' | sed 's/force-app\/main\/default\/classes\///g' | sed 's/\.cls//g' >> "$tempDir/apex_diff"
    else
        git diff --name-only "$arg" 2>/dev/null | grep '\.cls$' | sed 's/force-app\/main\/default\/classes\///g' | sed 's/\.cls//g' > "$tempDir/apex_diff"
    fi
    # cat "$tempDir/apex_diff"

    if [[ $? -ne 0 ]]; then
        echo "Error al obtener diff"
        exit 1
    fi

    if [[ ! -s "$tempDir/apex_diff" ]]; then
        echo "No hay diferencias para comparar."
        cleanup
        exit 0
    fi
}

function find_tests() {
    local line
    while IFS= read -r line; do
        if [[ "${EXCEPTIONS[$line]}" == "/" ]]; then
            :
        elif [[ ! -z ${EXCEPTIONS[$line]} ]]; then
            echo "${EXCEPTIONS[$line]}" >> "$tempDir/output_tests"
        else
            grep "$line" "$tempDir/apex_tests" >> "$tempDir/output_tests"
            if [[ $? -ne 0 ]]; then
                echo "$line" >> "$tempDir/missing_tests"
            fi
        fi
    done < "$tempDir/apex_diff"

    # Terminar si no se requiere ningún test
    if [[ ! -f "$tempDir/output_tests" ]]; then
        echo
        echo "No se requiere ningún test"
        cleanup
        exit 0
    fi

    # Eliminar los duplicados
    awk -i inplace '!seen[$0]++' "$tempDir/output_tests"
}

function get_output() {
    case $format in
        pr)
            if [[ -z "$copy" ]]; then
                echo "\`\`\`testsToBeRun" && cat "$tempDir/output_tests" && echo "\`\`\`"
            else
                (echo "\`\`\`testsToBeRun" && cat "$tempDir/output_tests" && echo "\`\`\`") | clip
            fi
            ;;
        list)
            if [[ -z "$copy" ]]; then
                cat "$tempDir/output_tests"
            else
                cat "$tempDir/output_tests" | clip
            fi
            ;;
        sf)
            if [[ -z "$copy" ]]; then
                echo
                tr '\n' ' ' < "$tempDir/output_tests"
                echo
            else
                tr '\n' ' ' < "$tempDir/output_tests" | clip
            fi
            ;;
        *)
            echo "Formato no válido."
            help
            exit 1
            ;;
    esac

    if [[ ! -z "$copy" ]]; then
        echo
        echo "Copiado al portapapeles!"
    fi

    if [[ -f "$tempDir/missing_tests" ]]; then
        echo
        echo "Missing tests:"
        cat "$tempDir/missing_tests"
    fi
}

# Main script
trap ctrl_c SIGINT
trap 'cleanup; exit' EXIT SIGTERM

parse_args "$@"

check_dependencies git grep sed awk mktemp clip tr ls cat
check_branches_exist

create_temp_dir
get_apex_tests
get_apex_diff
find_tests
get_output

cleanup
exit 0