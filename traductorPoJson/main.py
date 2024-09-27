
import json
import sys

class JsonPo:

    def __init__(self):
        pass

    def traduccion_a_po(self, fichero_in_traduccion, fichero_in_po):
        """
        Esta función toma un fichero .json con las traducciones de openai y un fichero .po con las líneas a traducir y
        genera un fichero .po con las traducciones de openai. La función asume que el fichero .po tiene el formato
        correcto, es decir, que las líneas de los msgid y msgstr están correctamente formateadas. Si una traducción no
        está en el fichero json, se incluye lo que tenga el archivo po. No se incluyen traducciones de plurales,
        no se sabe el formato que tiene que tener el json en ese caso.
        :param fichero_in_traduccion:
        :param fichero_in_po:
        :return:
        """
        # cargamos el fichero con las traducciones de openai en el json
        with open(fichero_in_traduccion, "r", encoding='utf-8') as file_in:
            dict_traducciones = json.load(file_in)
        # cargamos las líneas del fichero .po (solo nos van a interesar las primeras lineas hasta el primer msgid y las de
        # los msgid siguientes, las de los msgstr las vamos a sustituir, y los comentarios los vamos a mantener
        traducciones = dict_traducciones['locale_data']['superset']
        fichero_po = open(fichero_in_po, 'r', encoding='utf-8')
        lineas_po = fichero_po.readlines()
        fichero_po.close()
        lineas_para_traducir = [line.rstrip('\n') for line in lineas_po]
        # abrimos el fichero de salida
        with open(fichero_in_po[:-3]+'_opcion1_out.po', 'w', encoding='utf-8') as file:
            index = 0
            # hasta el segundo msgid incluimos todas las líneas
            while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
                file.write(lineas_para_traducir[index]+ '\n')
                index += 1
            file.write(lineas_para_traducir[index]+ '\n')
            index+=1
            while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
                file.write(lineas_para_traducir[index]+ '\n')
                index += 1
            # a partir del segundo msgid, incluimos las líneas de los msgid y los comentarios, y asociamos a msgstr
            # la traducción de openai
            # la traducción de openai
            dict_ids_traducciones_resto = {}
            while index < len(lineas_para_traducir):
                # cogemos las lineas asociadas a msgid y generamos el identificador que van a usar
                lines_id = [lineas_para_traducir[index]]
                index += 1
                while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgstr'):
                    lines_id.append(lineas_para_traducir[index])
                    index += 1
                lines_id[0] = lines_id[0].replace('msgid', '')
                index_lines = 0
                id_concatenado = ""
                es_plural = False
                while index_lines < len(lines_id):
                    esta_linea = lines_id[index_lines].strip()
                    esta_linea = esta_linea.replace('\\n', '\n')
                    if esta_linea.startswith('"'):
                        esta_linea = esta_linea[1:-1]
                    id_concatenado += esta_linea
                    if 'msgid_plural' in esta_linea:
                        es_plural = True
                    index_lines += 1
                # guardamos el msgid asociado (se hace así en vez de requerir al id_concatenado para no perder la información de msgid_plural si está definida
                msg_id = "msgid" + lines_id[0] + "\n"
                for linea_id in lines_id[1:]:
                    msg_id += linea_id + '\n'

                resto = ""
                if id_concatenado in traducciones:
                    lista_traduccion_aux = traducciones[id_concatenado]
                    lista_traduccion = []
                    for elem in lista_traduccion_aux:
                        if len(elem) > 0 and elem[0] == '"' and elem[-1] == '"':
                            lista_traduccion.append(elem[1:-1].replace('\n', '\\n'))
                        else:
                            lista_traduccion.append(elem.replace('\n', '\\n'))
                    #generamos el msgstr
                    if len(lista_traduccion) == 1:
                        msg_str = 'msgstr "' + lista_traduccion[0] + '"\n'
                    elif len(lista_traduccion) == 2:
                        msg_str = 'msgstr[0] "' + lista_traduccion[0] + '"\n' + 'msgstr[1] "' + lista_traduccion[1] + '"\n'
                    else:
                        if not es_plural:
                            msg_str = 'msgstr ""\n'
                        else:
                            msg_str = 'msgstr[0] ""\nmsgstr[1] ""\n'
                else:
                    if es_plural:
                        msg_str = 'msgstr[0] ""\nmsgstr[1] ""\n'
                    else: #si la traduccion no esta en el json, guardamos hasta el siguiente msgid, para mantener traducciones
                        #antiguas cuando hay que combinar jsons más cortos con pocas traducciones mandados a openAI
                        msg_str = ""
                        while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
                            resto += lineas_para_traducir[index] + '\n'
                            index += 1

                # ahora tenemos que coger todas las líneas hasta el siguiente msgid y guardar los comentarios en resto

                while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
                    if lineas_para_traducir[index].startswith('#') or len(lineas_para_traducir[index].strip()) == 0:
                        resto += lineas_para_traducir[index]+ '\n'
                    index+=1
                # se guarda la información en el diccionario
                dict_ids_traducciones_resto[id_concatenado] = {'msg_id': msg_id, 'msg_str': msg_str, 'resto': resto}
            # se escribe la información del diccionario en fichero
            dict_ids_traducciones_resto = dict(sorted(dict_ids_traducciones_resto.items()))
            for msg_id in dict_ids_traducciones_resto:
                file.write(dict_ids_traducciones_resto[msg_id]['msg_id'])
                file.write(dict_ids_traducciones_resto[msg_id]['msg_str'])
                file.write(dict_ids_traducciones_resto[msg_id]['resto'])

    def po_a_json(self, fichero_in_po):
        """
        Función que toma un fichero .po traducido y genera un fichero .json con las traducciones. No se incluyen
        traducciones de plurales, no se sabe el formato que tiene que tener el json en ese caso.
        :param fichero_in_po:
        :return:
        """
        fichero_po = open(fichero_in_po, 'r', encoding='utf-8')
        lineas_po = fichero_po.readlines()
        fichero_po.close()
        lineas_para_incluir = [line.rstrip('\n') for line in lineas_po]
        json_traducciones = {"domain": "superset",
            "locale_data":{'superset': {}}}
        superset_json = {
            "22": [
                "22"
            ],
            "": {
                "domain": "superset",
                "plural_forms": "nplurals=2; plural=(n != 1)",
                "lang": "es"
            }}

        index = 0
        # hasta el segundo msgid incluimos todas las líneas
        while index < len(lineas_para_incluir) and not lineas_para_incluir[index].startswith('msgid'):
            index += 1
        index += 1
        while index < len(lineas_para_incluir) and not lineas_para_incluir[index].startswith('msgid'):
            index += 1
        # a partir del segundo msgid, tenemos que coger la linea a traducir (asociada al msgid) y la traduccion (del
        # msgstr) y añadirlo al json
        while index < len(lineas_para_incluir):
            # cogemos las lineas asociadas a msgid y generamos el identificador que van a usar
            lines_id = [lineas_para_incluir[index]]
            index += 1
            while index < len(lineas_para_incluir) and not lineas_para_incluir[index].startswith('msgstr'):
                lines_id.append(lineas_para_incluir[index])
                index += 1
            lines_id[0] = lines_id[0].replace('msgid', '')
            index_lines = 0
            id_concatenado = ""
            es_plural = False
            while index_lines < len(lines_id):
                esta_linea = lines_id[index_lines].strip()
                esta_linea = esta_linea.replace('\\n', '\n')
                if esta_linea.startswith('"'):
                    esta_linea = esta_linea[1:-1]
                if 'msgid_plural' in esta_linea:
                    es_plural = True
                if not es_plural:
                    id_concatenado += esta_linea
                index_lines += 1
            # tenemos que coger la traduccion, de momento solo se hace en el caso de no tener plural definido (habria
            # que buscar ejemplos de como incluye el po en un json si es plural)
            if not es_plural:
                lineas_traduccion = [lineas_para_incluir[index].replace('msgstr','')]
                index += 1
                while index < len(lineas_para_incluir) and not lineas_para_incluir[index].startswith('msgid'):
                    if not(lineas_para_incluir[index].startswith('#') or len(lineas_para_incluir[index].strip()) == 0):
                        lineas_traduccion.append(lineas_para_incluir[index])
                    index += 1
                traduccion = ""
                for linea in lineas_traduccion:
                    linea = linea.strip()
                    if linea.startswith('"'):
                        linea = linea[1:-1]
                    linea = linea.replace('\\n', '\n')
                    traduccion += linea
                superset_json[id_concatenado] = [traduccion]
            else:
                while index < len(lineas_para_incluir) and not lineas_para_incluir[index].startswith('msgid'):
                    index += 1
        json_traducciones['locale_data']['superset'] = superset_json
        with open(fichero_in_po[:-3]+'_opcion2_out.json', 'w', encoding='utf-8') as file:
            json.dump(json_traducciones, file, ensure_ascii=False)

    def diferencias_po_po(self, fichero_in_po_revisado, fichero_in_po_para_traducir, nombre_json_salida):
        """
        Función que compara dos ficheros po y crea un fichero json donde solo se incluyan las sentencias a traducir del
        segundo que no estén traducidas en el primero.
        :param fichero_in_po_revisado:
        :param fichero_in_po_para_traducir:
        :param nombre_json_salida:
        :return:
        """
        fichero_po1 = open(fichero_in_po_revisado, 'r', encoding='utf-8')
        lineas_po1 = fichero_po1.readlines()
        fichero_po1.close()
        lineas_para_revisar = [line.rstrip('\n') for line in lineas_po1]
        # hasta el segundo msgid no haceos nada (por estructura de los .po del superset, el primer msgid es de descripción
        index = 0
        while index < len(lineas_para_revisar) and not lineas_para_revisar[index].startswith('msgid'):
            index += 1
        index += 1
        while index < len(lineas_para_revisar) and not lineas_para_revisar[index].startswith('msgid'):
            index += 1
        # a partir del segundo msgid, tenemos que coger la linea a traducir (asociada al msgid)
        claves_ya_traducidas = []
        while index < len(lineas_para_revisar):
            # cogemos las lineas asociadas a msgid y generamos el identificador que van a usar
            lines_id = [lineas_para_revisar[index]]
            index += 1
            while index < len(lineas_para_revisar) and not lineas_para_revisar[index].startswith('msgstr'):
                lines_id.append(lineas_para_revisar[index])
                index += 1
            lines_id[0] = lines_id[0].replace('msgid', '')
            index_lines = 0
            id_concatenado = ""
            es_plural = False
            while index_lines < len(lines_id):
                esta_linea = lines_id[index_lines].strip()
                esta_linea = esta_linea.replace('\\n', '\n')
                if esta_linea.startswith('"'):
                    esta_linea = esta_linea[1:-1]
                if 'msgid_plural' in esta_linea:
                    es_plural = True
                if not es_plural:
                    id_concatenado += esta_linea
                index_lines += 1
            if id_concatenado != "":
                claves_ya_traducidas.append(id_concatenado)
            while index < len(lineas_para_revisar) and not lineas_para_revisar[index].startswith('msgid'):
                index += 1

        # hacemos el mismo procedimiento pero para obtener las sentencias para traducir que hay asociadas a msgid en el
        # segundo fichero po, y comparamos que no se haya traducido ya (las que estan en el primero se han ido almacenando
        # en la estructura claves_ya_introducidas)
        fichero_po2 = open(fichero_in_po_para_traducir, 'r', encoding='utf-8')
        lineas_po2 = fichero_po2.readlines()
        fichero_po2.close()
        lineas_para_traducir = [line.rstrip('\n') for line in lineas_po2]
        index = 0
        while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
            index += 1
        index += 1
        while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
            index += 1
        claves_para_traducir = []
        while index < len(lineas_para_traducir):
            # cogemos las lineas asociadas a msgid y generamos el identificador que van a usar
            lines_id = [lineas_para_traducir[index]]
            index += 1
            while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgstr'):
                lines_id.append(lineas_para_traducir[index])
                index += 1
            lines_id[0] = lines_id[0].replace('msgid', '')
            index_lines = 0
            id_concatenado = ""
            es_plural = False
            while index_lines < len(lines_id):
                esta_linea = lines_id[index_lines].strip()
                esta_linea = esta_linea.replace('\\n', '\n')
                if esta_linea.startswith('"'):
                    esta_linea = esta_linea[1:-1]
                if 'msgid_plural' in esta_linea:
                    es_plural = True
                if not es_plural:
                    id_concatenado += esta_linea
                index_lines += 1
            if id_concatenado not in claves_ya_traducidas:
                claves_para_traducir.append(id_concatenado)
            while index < len(lineas_para_traducir) and not lineas_para_traducir[index].startswith('msgid'):
                index += 1

        # guardamos en el json las claves del segundo po que no están en el primero
        with open(nombre_json_salida, 'w', encoding='utf-8') as file:
            json.dump(claves_para_traducir, file, ensure_ascii=False)

    def combina_jsons(self, json_principal, json_para_incluir, nombre_json_salida):
        """
        Función que combina un primer fichero json con traducciones antiguas revisadas, con un segundo fichero json con
        traducciones nuevas. Lo almacena ordenado alfabéticamente.
        :param json_principal:
        :param json_para_incluir:
        :param nombre_json_salida:
        :return:
        """
        with open(json_principal, "r", encoding='utf-8') as file_in:
            dict_principal = json.load(file_in)
        with open(json_para_incluir, "r", encoding='utf-8') as file_in:
            dict_para_incluir = json.load(file_in)
        traducciones_principal = dict_principal['locale_data']['superset']
        traducciones_nuevas = dict_para_incluir['locale_data']['superset']
        todas_traducciones = traducciones_principal.copy()
        for traduccion in traducciones_nuevas.keys():
            if not traduccion in traducciones_principal:
                todas_traducciones[traduccion] = traducciones_nuevas[traduccion]
        claves_ordenadas = sorted(todas_traducciones)
        nuevo_json_traducciones = {}
        for clave in claves_ordenadas:
            nuevo_json_traducciones[clave] = todas_traducciones[clave]
        json_total = {
            "domain": "superset",
            "locale_data": {'superset': nuevo_json_traducciones}
        }
        with open(nombre_json_salida, 'w', encoding='utf-8') as file:
            json.dump(dict_principal, file, ensure_ascii=False)



if __name__ == '__main__':
    print(f"Elige qué quieres hacer:\n"
          f" 1. Crear un fichero .po a partir de un fichero .json de traducciones y otro fichero .po con los campos que se quieren traducir.\n"
          f" 2. Crear un fichero json a partir de un fichero po traducido.\n"
          f" 3. Comparar dos ficheros po y crear un fichero json donde solo se incluyan las sentencias a traducir del segundo que no estén traducidas en el primero.\n"
          f" 4. Combina un primer fichero json con traducciones antiguas revisadas, con un segundo fichero json con traducciones nuevas, y da un json con el total.\n"
          f" 5. Combinación de 3 + 4 + 1. Orden de argumentos: fichero po revisado, fichero json revisado, fichero po para traducir.\n"
          f" 6. Salir.\n")

    opcion = input("¿Opción deseada?: ")
    try:
        opcion = int(opcion)
    except ValueError:
        print("Opción no válida. ¡Hasta luego!")
        sys.exit(1)

    jsonpo = JsonPo()
    if opcion == 1:
        if len(sys.argv) != 3:
            print("No has introducido un número correcto de argumentos. Esta opción requiere un fichero json con la "
                  "traducción de openAI y otro fichero .po de salida en el que se rellenarán los msgid que estén "
                  "traducidos en el .json.")
            sys.exit(1)
        else:
            jsonpo.traduccion_a_po(sys.argv[1], sys.argv[2])
    elif opcion == 2:
        if len(sys.argv) != 2:
            print("No has introducido un número correcto de argumentos. Esta opción requiere un fichero .po de entrada.")
            sys.exit(1)
        else:
            jsonpo.po_a_json(sys.argv[1])
    elif opcion == 3:
        if len(sys.argv) != 3:
            print("No has introducido un número correcto de argumentos. Esta opción requiere dos ficheros .po de entrada.")
            sys.exit(1)
        else:
            jsonpo.diferencias_po_po(sys.argv[1], sys.argv[2], 'ficheros/claves_para_traducir.json')
    elif opcion == 4:
        if len(sys.argv) != 3:
            print("No has introducido un número correcto de argumentos. Esta opción requiere dos ficheros .json de entrada.")
            sys.exit(1)
        else:
            jsonpo.combina_jsons(sys.argv[1], sys.argv[2], 'ficheros/json_combinado.json')
    elif opcion == 5:
        if len(sys.argv) != 4:
            print("No has introducido un número correcto de argumentos. Esta opción requiere tres ficheros .po de entrada.")
            sys.exit(1)
        else:
            jsonpo.diferencias_po_po(sys.argv[1], sys.argv[3], 'ficheros/claves_para_traducir.json')
            jsonpo.combina_jsons(sys.argv[2], 'ficheros/traducciones.json', 'ficheros/json_combinado.json')
            jsonpo.traduccion_a_po('ficheros/json_combinado.json', sys.argv[3])
    elif opcion == 6:
        print("Has elegido salir. ¡Hasta luego!")
        sys.exit(0)
    else:
        print("Opción no válida. ¡Hasta luego!")
        sys.exit(1)
