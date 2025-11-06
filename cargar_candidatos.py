import re
from datetime import date
from django.core.exceptions import ValidationError
from django.db import transaction
from candidatos.models import Candidato, Sede, TipoDocumento 

# ==============================================================================
# CONFIGURACIÓN DE LA FECHA BASE Y SEDE POR DEFECTO
# ==============================================================================

FECHA_REGISTRO_BASE = date(2025, 10, 1)
SEDE_DEFECTO_ID = 1 
# Asumimos que el DNI es el TipoDocumento con PK=1 (creado en el shell)
TIPO_DOCUMENTO_DNI_ID = 1 

DATA_RAW = [
    # Candidatos extraídos de tus imágenes de listados
    {'DNI': '75397940', 'nombres_completos': 'Manuel Benites Sernaque', 'telefono_whatsapp': '918123563', 'origen_estado': 'REGISTRADO'},
    {'DNI': '71485812', 'nombres_completos': 'Elizabeth brisset cumpa Velasquez', 'telefono_whatsapp': '926070719', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77923286', 'nombres_completos': 'Luz Mery Guevara Guerrero', 'telefono_whatsapp': '944827911', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77043352', 'nombres_completos': 'Lizeth Breyli López Silva', 'telefono_whatsapp': '931677308', 'origen_estado': 'REGISTRADO'},
    {'DNI': '71312168', 'nombres_completos': 'Priscila Bermuy Medina', 'telefono_whatsapp': '930766032', 'origen_estado': 'REGISTRADO'},
    {'DNI': '60812771', 'nombres_completos': 'Jayro Antonio Villegas García', 'telefono_whatsapp': '939232234', 'origen_estado': 'REGISTRADO'},
    {'DNI': '75782704', 'nombres_completos': 'Carlos Aaron Custodio Lluen', 'telefono_whatsapp': '952426911', 'origen_estado': 'REGISTRADO'},
    {'DNI': '60986235', 'nombres_completos': 'NAYDELYN CELINDA OLIVERA BERNILLA', 'telefono_whatsapp': '942814251', 'origen_estado': 'REGISTRADO'},
    {'DNI': '61512024', 'nombres_completos': 'ANGIE DEL MILAGROS OLIVERA BERNILLA', 'telefono_whatsapp': '931722099', 'origen_estado': 'REGISTRADO'},
    {'DNI': '47868874', 'nombres_completos': 'Yoselin patricia soriano olazabal', 'telefono_whatsapp': '988302543', 'origen_estado': 'REGISTRADO'}, 
    {'DNI': '71782572', 'nombres_completos': 'José Maria cabrejos Purizaca', 'telefono_whatsapp': '960394904', 'origen_estado': 'REGISTRADO'}, 
    {'DNI': '75558313', 'nombres_completos': 'Irania yatsury soriano olazabal', 'telefono_whatsapp': '947595251', 'origen_estado': 'REGISTRADO'}, 
    {'DNI': '73485502', 'nombres_completos': 'Malek Adrian Jara Farias', 'telefono_whatsapp': '954471245', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77240865', 'nombres_completos': 'Eddy David Cervera León', 'telefono_whatsapp': '947906405', 'origen_estado': 'REGISTRADO'},
    {'DNI': '74661312', 'nombres_completos': 'Franz Anthony Misael Villalobos Perez', 'telefono_whatsapp': '990513712', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77285686', 'nombres_completos': 'JUNIOR LORENZO PALACIOS SANDOVAL', 'telefono_whatsapp': '900069759', 'origen_estado': 'REGISTRADO'},
    {'DNI': '60986167', 'nombres_completos': 'Angel Santiago Cuyate Melendez', 'telefono_whatsapp': '943942493', 'origen_estado': 'REGISTRADO'},
    {'DNI': '72914769', 'nombres_completos': 'Jeremy Fernández Arrascue', 'telefono_whatsapp': '900755252', 'origen_estado': 'REGISTRADO'},
    {'DNI': '73689220', 'nombres_completos': 'Dana Carolay Barrantes Barrantes', 'telefono_whatsapp': '978351982', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77294914', 'nombres_completos': 'JAMIR JOSUE BANCES CABRERA', 'telefono_whatsapp': '935959053', 'origen_estado': 'REGISTRADO'},
    {'DNI': '74384386', 'nombres_completos': 'Karina del milagro Solís cepeda', 'telefono_whatsapp': '907156808', 'origen_estado': 'REGISTRADO'},
    {'DNI': '71204725', 'nombres_completos': 'HILLARY LOURDES CASTILLO SALAZAR', 'telefono_whatsapp': '922757414', 'origen_estado': 'REGISTRADO'},
    {'DNI': '75194619', 'nombres_completos': 'Lucia Carhuapoma Toro', 'telefono_whatsapp': '982491707', 'origen_estado': 'REGISTRADO'},
    {'DNI': '75782678', 'nombres_completos': 'Ana Sofia Eca Roa', 'telefono_whatsapp': '984699684', 'origen_estado': 'REGISTRADO'},
    {'DNI': '72487303', 'nombres_completos': 'María José Piscoya Sánchez', 'telefono_whatsapp': '945779034', 'origen_estado': 'REGISTRADO'},
    {'DNI': '47428301', 'nombres_completos': 'Ines Huertas Dominguez', 'telefono_whatsapp': '920213205', 'origen_estado': 'REGISTRADO'},
    {'DNI': '74770041', 'nombres_completos': 'Luis cristofer cumpa Velásquez', 'telefono_whatsapp': '905706071', 'origen_estado': 'REGISTRADO'},
    {'DNI': '76872866', 'nombres_completos': 'Patricia Antonella Castillo Vallejos', 'telefono_whatsapp': '902591191', 'origen_estado': 'REGISTRADO'},
    {'DNI': '72918887', 'nombres_completos': 'Gino Jhordano Chicoma Sotero', 'telefono_whatsapp': '943361757', 'origen_estado': 'REGISTRADO'},
    {'DNI': '77689394', 'nombres_completos': 'Jorge Yair Cerro Mija', 'telefono_whatsapp': '991723694', 'origen_estado': 'REGISTRADO'},
    {'DNI': '76839112', 'nombres_completos': 'MARIA FÉ RUIZ VELÁSQUEZ', 'telefono_whatsapp': '932247793', 'origen_estado': 'REGISTRADO'},
    {'DNI': '75906949', 'nombres_completos': 'Miguel Rodrigo Morales Calderón', 'telefono_whatsapp': '995251636', 'origen_estado': 'REGISTRADO'},
    {'DNI': '60806671', 'nombres_completos': 'Aaron Obed Guevara Davila', 'telefono_whatsapp': '977861951', 'origen_estado': 'REGISTRADO'},
    {'DNI': '60282414', 'nombres_completos': 'ERICK WILGER ROJAS DAVILA', 'telefono_whatsapp': '903164622', 'origen_estado': 'REGISTRADO'},
    {'DNI': '75546442', 'nombres_completos': 'Alexis Joaquín CUSTODIO Ballena', 'telefono_whatsapp': '989658073', 'origen_estado': 'REGISTRADO'},
    {'DNI': '73463417', 'nombres_completos': 'Brandon Jordhy Saavedra Ramón', 'telefono_whatsapp': '904874533', 'origen_estado': 'REGISTRADO'},
    {'DNI': '49031690', 'nombres_completos': 'Cesar Alejandro salas Rivero', 'telefono_whatsapp': '925227109', 'origen_estado': 'REGISTRADO'},
    {'DNI': '76592054', 'nombres_completos': 'Elar Jhon Herrera coronado', 'telefono_whatsapp': '962620987', 'origen_estado': 'REGISTRADO'},
    {'DNI': '70926381', 'nombres_completos': 'Jose miguel mego silva', 'telefono_whatsapp': '930586074', 'origen_estado': 'REGISTRADO'},
]

# ==============================================================================
# LÓGICA DE LIMPIEZA Y CARGA
# ==============================================================================

def clean_dni(dni):
    """Limpia el DNI y asegura que tenga 8 dígitos (para esta carga)."""
    if dni is None: return None
    dni = re.sub(r'\D', '', str(dni).strip()) 
    return dni if len(dni) == 8 else None

def clean_phone(phone):
    """Limpia el número de teléfono, mantiene los últimos 9 dígitos."""
    if phone is None: return ''
    phone = re.sub(r'\D', '', str(phone)) 
    
    return phone[-9:] if len(phone) >= 9 else phone

def run_data_upload():
    """Función principal para cargar y actualizar los candidatos."""
    print("--- INICIANDO CARGA DE CANDIDATOS (REGISTRADOS 01/10/2025) ---")
    
    try:
        # Recuperar objetos FK (Sede y TipoDocumento)
        sede_defecto = Sede.objects.get(pk=SEDE_DEFECTO_ID)
        tipo_documento_dni = TipoDocumento.objects.get(pk=TIPO_DOCUMENTO_DNI_ID)
    except Sede.DoesNotExist:
        print(f"ERROR: No se encontró la Sede con PK={SEDE_DEFECTO_ID}. ¡Correr el shell para crearla!")
        return
    except TipoDocumento.DoesNotExist:
        print(f"ERROR: No se encontró el TipoDocumento DNI con PK={TIPO_DOCUMENTO_DNI_ID}. ¡Correr el shell para crearlo!")
        return

    candidatos_a_crear = []
    dnies_validos = set()
    total_registros = 0
    
    # 1. Unificar y limpiar los datos
    print("1. Limpiando y unificando datos...")
    
    for data in DATA_RAW:
        dni = clean_dni(data['DNI'])
        telefono = clean_phone(data['telefono_whatsapp'])
        total_registros += 1

        if not dni:
            print(f"Advertencia: DNI inválido (no 8 dígitos) para {data['nombres_completos']}")
            continue

        if dni not in dnies_validos:
            dnies_validos.add(dni)
            candidatos_a_crear.append({
                'DNI': dni,
                'nombres_completos': data['nombres_completos'].strip(),
                'telefono_whatsapp': telefono,
                'estado_actual': 'REGISTRADO',
                'fecha_registro': FECHA_REGISTRO_BASE, 
                'sede_registro': sede_defecto,
                'tipo_documento': tipo_documento_dni, # <<-- CAMBIO CLAVE
                'email': None,
            })
            
    print(f"Registros únicos y válidos a procesar: {len(candidatos_a_crear)}")
    
    # 2. Iterar y hacer el Create/Update final
    created_count = 0
    updated_count = 0
    error_count = 0
    
    print("\n2. Actualizando/Creando en la Base de Datos...")

    with transaction.atomic():
        for data in candidatos_a_crear:
            try:
                # Intentar obtener el candidato (usando DNI como PK)
                candidato = Candidato.objects.filter(pk=data['DNI']).first()
                
                if candidato:
                    # Candidato existe (por DNI/PK)
                    update_fields = {}
                    
                    if candidato.nombres_completos != data['nombres_completos']:
                        update_fields['nombres_completos'] = data['nombres_completos']
                        
                    if candidato.telefono_whatsapp != data['telefono_whatsapp']:
                        update_fields['telefono_whatsapp'] = data['telefono_whatsapp']
                        
                    if update_fields:
                        Candidato.objects.filter(pk=data['DNI']).update(**update_fields)
                        updated_count += 1
                        
                else:
                    # El candidato no existe, se crea
                    Candidato.objects.create(
                        DNI=data['DNI'],
                        nombres_completos=data['nombres_completos'],
                        telefono_whatsapp=data['telefono_whatsapp'],
                        estado_actual='REGISTRADO',
                        fecha_registro=FECHA_REGISTRO_BASE,
                        sede_registro=data['sede_registro'],
                        tipo_documento=data['tipo_documento'], # <<-- CAMBIO CLAVE
                        email=None
                    )
                    created_count += 1
                    
            except ValidationError as e:
                print(f"ERROR de validación para DNI {data['DNI']}: {e.message_dict}")
                error_count += 1
            except Exception as e:
                print(f"ERROR inesperado al procesar DNI {data['DNI']}: {e}")
                error_count += 1

    print("\n--- RESUMEN DE LA CARGA ---")
    print(f"Registros leídos (total): {total_registros}")
    print(f"Candidatos CREADOS: {created_count}")
    print(f"Candidatos ACTUALIZADOS (datos de contacto): {updated_count}")
    print(f"Registros con ERRORES: {error_count}")
    print("¡Proceso de carga finalizado con éxito!")

if __name__ == '__main__':
    run_data_upload()